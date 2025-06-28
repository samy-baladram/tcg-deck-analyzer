# deck_gallery.py
"""Functions for displaying all fetched decks in the Deck Gallery tab"""

import streamlit as st
import json
import os
from ui_helpers import get_energy_types_for_deck
from card_renderer import render_sidebar_deck
import cache_manager

def get_deck_record(tournament_id, player_id):
    """
    Get win-lose-tie record for a deck by matching tournament and player
    Returns tuple (wins, losses, ties) or (0, 0, 0) if not found
    """
    try:
        # Check if we have performance data in session state
        if 'performance_data' not in st.session_state:
            return (0, 0, 0)
        
        # For now, return placeholder record since we need to implement
        # the JSON matching logic based on your tournament data structure
        # This would need to be implemented based on your specific JSON format
        return (2, 1, 0)  # Placeholder
        
    except Exception as e:
        print(f"Error getting deck record: {e}")
        return (0, 0, 0)

def display_single_deck_expander(deck_data, deck_number, energy_types, is_typical):
    """
    Display a single deck in an expander format
    Similar to the existing expander in display_deck_template_tab
    """
    # Get record for this deck
    tournament_id = deck_data.get('tournament_id', '')
    player_id = deck_data.get('player_id', '')
    wins, losses, ties = get_deck_record(tournament_id, player_id)
    
    # Format record string
    record_str = f"{wins}-{losses}-{ties}"
    
    # Create expander title
    expander_title = f"Deck {deck_number}. Record {record_str}"
    
    # Create the expander
    with st.expander(expander_title, expanded=False):
        # Display energy types if available
        if energy_types:
            from card_renderer import render_energy_icons
            energy_html = render_energy_icons(energy_types, is_typical)
            st.markdown(energy_html, unsafe_allow_html=True)
        
        # Get deck cards
        cards = deck_data.get('cards', [])
        
        if cards:
            # Separate Pokemon and Trainer cards
            pokemon_cards = []
            trainer_cards = []
            
            for card in cards:
                if card.get('type', '').lower() == 'pokemon':
                    pokemon_cards.append({
                        'name': card.get('card_name', ''),
                        'set': card.get('set', ''),
                        'num': card.get('num', ''),
                        'amount': card.get('amount', 1)
                    })
                else:
                    trainer_cards.append({
                        'name': card.get('card_name', ''),
                        'set': card.get('set', ''),
                        'num': card.get('num', ''),
                        'amount': card.get('amount', 1)
                    })
            
            # Render the deck using CardGrid
            deck_html = render_sidebar_deck(
                pokemon_cards, 
                trainer_cards,
                card_width=65
            )
            st.markdown(deck_html, unsafe_allow_html=True)
        else:
            st.info("No deck data available")

def display_deck_gallery_tab():
    """
    Display the Deck Gallery tab with all collected decks in 3 columns
    """
    st.write("##### Deck Gallery - All Collected Decks")
    
    # Get current deck info
    if 'analyze' not in st.session_state:
        st.info("Select a deck to view the gallery")
        return
    
    deck_name = st.session_state.analyze.get('deck_name', '')
    set_name = st.session_state.analyze.get('set_name', 'A3')
    
    # Get energy types for the current archetype
    energy_types, is_typical = get_energy_types_for_deck(deck_name)
    
    # Get collected decks from session state
    deck_key = f"{deck_name}_{set_name}"
    
    if 'collected_decks' not in st.session_state or deck_key not in st.session_state.collected_decks:
        st.info("No collected decks found for this archetype")
        return
    
    collected_data = st.session_state.collected_decks[deck_key]
    all_decks = collected_data.get('decks', [])
    
    if not all_decks:
        st.info("No deck data available")
        return
    
    # Create 3 columns for layout
    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]
    
    # For now, display up to 20 decks as requested
    max_decks = min(20, len(all_decks))
    
    # Display decks in columns
    for i in range(max_decks):
        deck = all_decks[i]
        column_index = i % 3  # Distribute across 3 columns
        
        with columns[column_index]:
            display_single_deck_expander(
                deck, 
                deck.get('deck_num', i + 1), 
                energy_types, 
                is_typical
            )
    
    # Display summary info
    st.divider()
    st.caption(f"Showing {max_decks} of {len(all_decks)} collected decks for {deck_name}")

# Alternative function for testing/development
def display_deck_gallery_tab_simple():
    """
    Simplified version for testing - just copies the expander code 20 times
    This is what the user specifically requested for now
    """
    st.write("##### Deck Gallery - All Collected Decks")
    
    # Get current deck info
    if 'analyze' not in st.session_state:
        st.info("Select a deck to view the gallery")
        return
    
    deck_name = st.session_state.analyze.get('deck_name', '')
    set_name = st.session_state.analyze.get('set_name', 'A3')
    
    # Get energy types for the current archetype
    energy_types, is_typical = get_energy_types_for_deck(deck_name)
    
    # Create 3 columns for layout
    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]
    
    # Create 20 expanders as requested
    for i in range(20):
        column_index = i % 3  # Distribute across 3 columns
        deck_number = i + 1
        
        # Placeholder record for now
        record_str = f"{2}-{1}-{0}"  # Placeholder win-lose-tie
        expander_title = f"Deck {deck_number}. Record {record_str}"
        
        with columns[column_index]:
            with st.expander(expander_title, expanded=False):
                # Display energy types if available
                if energy_types:
                    from card_renderer import render_energy_icons
                    energy_html = render_energy_icons(energy_types, is_typical)
                    st.markdown(energy_html, unsafe_allow_html=True)
                
                # Get sample deck data (using the same logic as the original)
                sample_deck = cache_manager.get_or_load_sample_deck(deck_name, set_name)
                
                # Render the sample deck
                if sample_deck:
                    deck_html = render_sidebar_deck(
                        sample_deck['pokemon_cards'], 
                        sample_deck['trainer_cards'],
                        card_width=65
                    )
                    st.markdown(deck_html, unsafe_allow_html=True)
                else:
                    st.info(f"Sample deck {deck_number} - No data available")
    
    # Display summary info
    st.divider()
    st.caption(f"Showing 20 sample decks for {deck_name} archetype")
