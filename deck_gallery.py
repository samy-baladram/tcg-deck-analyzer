# deck_gallery.py
"""Deck Gallery display functions for showcasing all fetched decks"""

import streamlit as st
from card_renderer import CardRenderer, CardGrid
from ui_helpers import format_deck_name

def display_deck_gallery(deck_name=None, set_name=None):
    """
    Display all collected deck instances for the specified archetype in a three-column gallery format.
    Each deck shows in an expander with format: "Deck {number}. Record {record}"
    
    Args:
        deck_name: The deck archetype name (if None, gets from session state)
        set_name: The set name (if None, gets from session state)
    """
    
    # Get current deck from session state if not provided
    if deck_name is None or set_name is None:
        if 'analyze' in st.session_state:
            deck_name = st.session_state.analyze.get('deck_name')
            set_name = st.session_state.analyze.get('set_name', 'A3')
        else:
            st.info("No deck selected. Please select a deck from the dropdown first.")
            return
    
    # Check if we have collected decks data for this specific archetype
    deck_key = f"{deck_name}_{set_name}"
    
    if ('collected_decks' not in st.session_state or 
        deck_key not in st.session_state.collected_decks):
        st.info(f"No collected deck data found for {deck_name}. Please analyze this deck first.")
        return
    
    deck_data = st.session_state.collected_decks[deck_key]
    
    if 'decks' not in deck_data or not deck_data['decks']:
        st.info(f"No individual deck instances found for {deck_name}.")
        return
    
    # Get all individual deck instances for this archetype
    deck_instances = deck_data['decks']
    
    formatted_deck_name = format_deck_name(deck_name)
    st.write(f"### {formatted_deck_name} - Individual Decks ({len(deck_instances)} decks)")
    
    # Create three-column layout
    cols = st.columns(3)
    
    for i, deck_instance in enumerate(deck_instances):
        col_idx = i % 3
        
        with cols[col_idx]:
            # Extract record and deck number
            record = deck_instance.get('record', 'No record')
            deck_num = deck_instance.get('deck_num', i + 1)  # fallback to index + 1
            
            # Format expander title
            expander_title = f"Deck {deck_num}. Record {record}"
            
            with st.expander(expander_title, expanded=False):
                # Display this specific deck instance's cards
                if 'cards' in deck_instance and deck_instance['cards']:
                    
                    # Show deck metadata
                    if 'player_name' in deck_instance:
                        st.write(f"**Player:** {deck_instance['player_name']}")
                    
                    if 'tournament_name' in deck_instance:
                        st.write(f"**Tournament:** {deck_instance['tournament_name']}")
                    elif 'tournament_id' in deck_instance:
                        st.write(f"**Tournament ID:** {deck_instance['tournament_id']}")
                    
                    if 'placement' in deck_instance:
                        st.write(f"**Placement:** {deck_instance['placement']}")
                    
                    st.divider()
                    
                    # Separate cards by type
                    pokemon_cards = []
                    trainer_cards = []
                    
                    for card in deck_instance['cards']:
                        if card.get('type') == 'Pokemon':
                            pokemon_cards.append(card)
                        else:
                            trainer_cards.append(card)
                    
                    # Show energy types if available
                    if 'energy_types' in deck_instance and deck_instance['energy_types']:
                        st.write("**Energy Types:**")
                        energy_types = deck_instance['energy_types']
                        
                        # Use the energy renderer from the main system
                        try:
                            from energy_utils import render_energy_icons
                            energy_html = render_energy_icons(energy_types, is_typical=True)
                            st.markdown(energy_html, unsafe_allow_html=True)
                        except ImportError:
                            # Fallback display
                            energy_display = " • ".join(energy_types)
                            st.markdown(f"*{energy_display}*")
                        
                        st.divider()
                    
                    # Render Pokemon cards using Card Renderer
                    if pokemon_cards:
                        total_pokemon = sum(card.get('count', 1) for card in pokemon_cards)
                        CardRenderer.render_deck_section(
                            pokemon_cards, 
                            "Pokémon", 
                            card_count=total_pokemon
                        )
                    
                    # Render Trainer cards using Card Renderer  
                    if trainer_cards:
                        total_trainers = sum(card.get('count', 1) for card in trainer_cards)
                        CardRenderer.render_deck_section(
                            trainer_cards, 
                            "Trainer", 
                            card_count=total_trainers
                        )
                
                else:
                    st.info("Card list not available for this deck instance")

def display_deck_gallery_simplified():
    """
    Simplified display showing only analyzed deck archetypes (for quick overview)
    """
    
    # Check if we have collected decks data
    if 'collected_decks' not in st.session_state or not st.session_state.collected_decks:
        st.info("No deck data available. Please analyze some decks first.")
        return
    
    # Get only archetypes that have been analyzed
    analyzed_archetypes = []
    
    for deck_key, deck_data in st.session_state.collected_decks.items():
        # Parse deck_key format: "deck_name_set_name"
        parts = deck_key.rsplit('_', 1)
        if len(parts) == 2:
            deck_name, set_name = parts
        else:
            deck_name = deck_key
            set_name = 'A3'
        
        # Check if this archetype has been analyzed
        cache_key = f"full_deck_{deck_name}_{set_name}"
        if ('analyzed_deck_cache' in st.session_state and 
            cache_key in st.session_state.analyzed_deck_cache):
            
            deck_count = len(deck_data.get('decks', []))
            
            analyzed_archetypes.append({
                'deck_name': deck_name,
                'set_name': set_name,
                'deck_key': deck_key,
                'deck_count': deck_count
            })
    
    if not analyzed_archetypes:
        st.info("No analyzed deck archetypes found.")
        return
    
    # Sort by deck count
    analyzed_archetypes.sort(key=lambda x: x['deck_count'], reverse=True)
    
    st.write(f"### Analyzed Deck Archetypes ({len(analyzed_archetypes)} archetypes)")
    
    # Create three-column layout
    cols = st.columns(3)
    
    for i, archetype in enumerate(analyzed_archetypes):
        col_idx = i % 3
        
        with cols[col_idx]:
            # Format expander title
            formatted_name = format_deck_name(archetype['deck_name'])
            expander_title = f"{formatted_name} ({archetype['deck_count']} decks)"
            
            with st.expander(expander_title, expanded=False):
                # Get analyzed results for this deck archetype
                cache_key = f"full_deck_{archetype['deck_name']}_{archetype['set_name']}"
                analyzed_data = st.session_state.analyzed_deck_cache[cache_key]
                results = analyzed_data.get('results')
                variant_df = analyzed_data.get('variant_df')
                
                if results is not None and not results.empty:
                    # Display exactly like "Deck Info" tab
                    try:
                        from display_tabs import display_deck_template_tab
                        display_deck_template_tab(results, variant_df)
                    except Exception as e:
                        st.error(f"Error displaying deck template: {str(e)}")
                else:
                    st.info("No analysis results available")
