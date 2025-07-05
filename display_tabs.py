# display_tabs.py
"""Functions for rendering the tabs in the main content area"""

import streamlit as st
from formatters import format_deck_name, extract_pokemon_urls
from related_decks import find_related_decks
from visualizations import create_usage_bar_chart, display_chart, create_variant_bar_chart
from analyzer import build_deck_template
from datetime import datetime, timedelta
from card_renderer import render_energy_icons
from config import TOURNAMENT_COUNT, POWER_INDEX_EXPLANATION, MIN_MATCHUP_MATCHES
from header_image_cache import get_header_image_cached
import json
import pandas as pd
import base64
import os

def display_deck_header(deck_info, results):
    """Display the deck header with image - simplified version"""
    header_image = get_header_image_cached(
        deck_info['deck_name'], 
        deck_info.get('set', 'A3'),
        results
    )
    
    if header_image:
        # Simple centered deck image
        header_content = f"""
        <div style="display: flex; justify-content: center; align-items: center; margin: 0rem 0rem -3rem 0rem; text-align: center;">
            <div style="min-width: 200px;">
                <img src="data:image/png;base64,{header_image}" style="max-width: 500px; margin-top: -13rem; margin-bottom: -2rem; width: 80%; height: auto; border: 0px solid #57585F; border-radius: 10px;">
            </div>
        </div>"""
        
        st.markdown(header_content, unsafe_allow_html=True)
            
# In display_card_usage_tab function in display_tabs.py
def display_card_usage_tab(results, total_decks, variant_df):
    """Display the Card Usage tab with energy-colored charts based on deck energy types"""
    # Create two columns for Pokemon and Trainer
    st.write("##### Card Usage & Variants")
    col1, col2 = st.columns([2, 3])
    
    # Get energy types using our improved function from ui_helpers
    from ui_helpers import get_energy_types_for_deck
    
    # Initialize empty energy types list
    energy_types = []
    is_typical = False
    primary_energy = None
    
    # Get current deck info
    deck_info = {'deck_name': '', 'set_name': 'A3'}
    if 'analyze' in st.session_state:
        deck_info['deck_name'] = st.session_state.analyze.get('deck_name', '')
        deck_info['set_name'] = st.session_state.analyze.get('set_name', 'A3')
        
        # Get the most common energy combination
        energy_types, is_typical = get_energy_types_for_deck(deck_info['deck_name'])
        
        # Get primary energy (first one in the list)
        primary_energy = energy_types[0] if energy_types and len(energy_types) > 0 else None
      
    with col1:
        st.caption("Pokemon")
        type_cards = results[results['type'] == 'Pokemon']
        
        if not type_cards.empty:
            # Pass primary energy type to chart
            fig = create_usage_bar_chart(type_cards, 'Pokemon', primary_energy)
            display_chart(fig, key="usage_pokemon_chart")
        else:
            st.info("No Pokemon cards found")

        if not variant_df.empty:
            # Import variant renderer
            from card_renderer import render_variant_cards
            
            # Display variant analysis #({row['Total Decks']} decks)
            for _, row in variant_df.iterrows():
                with st.expander(f"{row['Card Name']} Versions", expanded=False): 
                    # Extract set codes and numbers
                    var1 = row['Var1']
                    var2 = row['Var2']
                    
                    var1_set = '-'.join(var1.split('-')[:-1])  # Everything except the last part
                    var1_num = var1.split('-')[-1]         # Just the last part
                    var2_set = '-'.join(var2.split('-')[:-1])
                    var2_num = var2.split('-')[-1]
                    
                    # Create the 2-column layout
                    var_col1, var_col2 = st.columns([2, 5])
                    
                    # Column 1: Both Variants side by side
                    with var_col1:
                        variant_html = render_variant_cards(var1_set, var1_num, var2_set, var2_num, var1, var2)
                        st.markdown(variant_html, unsafe_allow_html=True)
                    
                    # Column 2: Bar Chart
                    with var_col2:
                        # Create variant bar chart with primary energy type
                        fig_var = create_variant_bar_chart(row, primary_energy)
                        variant_key = f"usage_variant_{row['Card Name'].replace(' ', '_')}_{_}"
                        display_chart(fig_var, key=variant_key) 
        
        # Add Energy Table at the bottom of column 1
        # st.write("##### Energy Analysis")
        # Call the energy table generation - pass the deck_info
        generate_energy_analysis(deck_info)
    
    with col2:
        st.caption("Trainer")
        type_cards = results[results['type'] == 'Trainer']
        
        if not type_cards.empty:
            # Keep default colors for trainers
            fig = create_usage_bar_chart(type_cards, 'Trainer')
            display_chart(fig, key="usage_trainer_chart")
        else:
            st.info("No Trainer cards found")
    # ADD THIS: Calculate last_update inside the function
    from ui_helpers import display_deck_update_info
    
    # Get current deck info from session state
    if 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', '')
        set_name = st.session_state.analyze.get('set_name', 'A3')
        
        # Get the last update info
        # last_update = display_deck_update_info(deck_name, set_name)
        
        # if last_update:
        #     st.caption(f"Data of {total_decks} collected decks (with partial energy info). {last_update}")
        # else:
        st.caption(f"Data of {total_decks} collected decks (with partial energy info).")
    else:
        # Fallback if no deck is selected
        st.caption(f"Data of {total_decks} collected decks (with partial energy info).")


# Simplified energy analysis function that calls the parts from display_energy_debug_tab
def generate_energy_analysis(deck_info):
    """Generate the energy analysis table for the Card Usage tab"""
    deck_name = deck_info['deck_name']
    set_name = deck_info.get('set_name', 'A3')
    
    # First check if we have per-deck energy data
    if 'per_deck_energy' in st.session_state and deck_name in st.session_state.per_deck_energy:
        # We can still use the existing detailed energy table
        from energy_utils import display_detailed_energy_table
        st.markdown(display_detailed_energy_table(deck_name), unsafe_allow_html=True)
    else:
        # Create a simplified version that works directly with collected decks
        deck_key = f"{deck_name}_{set_name}"
        if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
            collected_data = st.session_state.collected_decks[deck_key]
            
            if 'decks' in collected_data and collected_data['decks']:
                # Get all unique energy types
                all_energies = set()
                energy_by_deck = {}
                
                for deck in collected_data['decks']:
                    if 'energy_types' in deck and deck['energy_types'] and 'deck_num' in deck:
                        deck_num = deck['deck_num']
                        energy_types = sorted(deck['energy_types'])
                        energy_by_deck[deck_num] = energy_types
                        all_energies.update(energy_types)
                
                # Create table directly if we have data
                if energy_by_deck and all_energies:
                    all_energies = sorted(all_energies)
                    
                    # Create table HTML directly
                    table_html = generate_energy_table_html(all_energies, energy_by_deck)
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.info("No energy data found in collected decks")
            else:
                st.info("No decks found in collected data")
        else:
            st.info("No collected decks found")

def display_deck_template_tab(results, variant_df=None):
    """Display the Deck Template tab with revised layout and two-column card sections"""
    # Import needed functions
    from ui_helpers import get_energy_types_for_deck
    
    # Use the updated function that returns deck_info
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    # Initialize empty energy types list
    energy_types = []
    is_typical = False
    
    # Look for energy_types in the session state for this deck
    if 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', '')
        
        # Get the most common energy combination
        energy_types, is_typical = get_energy_types_for_deck(deck_name)
    
    # Create outer columns: Sample Deck (2) and Template (3) - switched order and ratio
    outer_col1, _, outer_col2 = st.columns([8,1,12])
    
    # Left column: Sample Deck(s)
    with outer_col1:
        # Display standard sample deck and variant decks
        display_variant_decks(deck_info, energy_types, is_typical, options)
    
    # Right column: Core Cards and Flexible Slots in vertical layout
    with outer_col2:
        display_deck_composition(deck_info, energy_types, is_typical, total_cards, options, variant_df)

def display_variant_decks(deck_info, energy_types, is_typical, options):
    """Display the main sample deck and any variant decks containing other Pokémon options"""
    # Check if options is empty or None
    if options is None or options.empty:
        st.write("##### Current Top Deck")
        render_sample_deck(energy_types, is_typical)
        return
    
    # Get Pokemon options that have different names from core Pokemon
    pokemon_options = options[options['type'] == 'Pokemon'].copy()
    
    # If no Pokemon options, just show the sample deck
    if pokemon_options.empty:
        st.write("##### Current Top Deck")
        render_sample_deck(energy_types, is_typical)
        return
    
    # Get core Pokemon names for comparison
    core_pokemon_names = set()
    for card in deck_info.get('Pokemon', []):
        core_pokemon_names.add(card.get('name', '').lower())
    
    # Filter options to only include Pokemon with different names
    different_pokemon = pokemon_options[~pokemon_options['card_name'].str.lower().isin(core_pokemon_names)]
    
    # If no different Pokemon in options, just show the standard sample deck
    if different_pokemon.empty:
        st.write("##### Current Top Deck")
        render_sample_deck(energy_types, is_typical)
        return
    
    # Get the variant Pokemon names
    variant_pokemon_names = set(different_pokemon['card_name'].str.lower())
    
    # Ensure we have deck collection data before proceeding
    if 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', '')
        set_name = st.session_state.analyze.get('set_name', '')
        ensure_deck_collection_data(deck_name, set_name)
    
    # Display the original sample deck (without variants) in an expander
    with st.expander("Current Top Deck", expanded=True):
        render_clean_sample_deck(variant_pokemon_names, energy_types, is_typical)
    
    # Track decks we've already shown to avoid duplicates
    shown_deck_nums = set()
    
    # Track exact Pokemon names already shown to avoid duplicates
    shown_pokemon_names = set()
    
    # Limit the variants to show (to avoid overwhelming UI)
    max_variants = 5  # Show at most 5 variants
    variants_shown = 0  # Counter for actual variants shown
    
    # For each different Pokemon, check if we should show a variant
    for idx, (_, pokemon) in enumerate(different_pokemon.iterrows()):
        pokemon_name = pokemon['card_name']
        set_code = pokemon.get('set', '')
        num = pokemon.get('num', '')
        
        # Check if we've already shown enough variants
        if variants_shown >= max_variants:
            continue
            
        # Skip if we already showed this exact Pokemon name
        if pokemon_name.lower() in shown_pokemon_names:
            continue
        
        # Create a set of Pokemon to avoid (other variants)
        other_variants = set(name for name in variant_pokemon_names if name.lower() != pokemon_name.lower())
        
        # Pre-check if we can find a suitable deck BEFORE creating expander
        deck_num = render_optimal_variant_deck(pokemon, other_variants, shown_deck_nums, energy_types, is_typical, check_only=True)
        
        # ONLY create expander if we found a suitable deck
        if deck_num is not None:
            # Create a formatted title with set and number info
            variant_title = f"{pokemon_name} ({set_code}-{num}) Variant" if set_code and num else f"{pokemon_name} Variant"
            
            with st.expander(variant_title, expanded=False):
                # Now actually render the deck (we know it exists)
                actual_deck_num = render_optimal_variant_deck(pokemon, other_variants, shown_deck_nums, energy_types, is_typical)
                
                # Track this successful variant
                if actual_deck_num is not None:
                    shown_deck_nums.add(actual_deck_num)
                    shown_pokemon_names.add(pokemon_name.lower())
                    variants_shown += 1

def ensure_deck_collection_data(deck_name, set_name):
    """Ensure deck collection data is available, efficiently using cache"""
    deck_key = f"{deck_name}_{set_name}"
    
    # Check if we already have collected decks in session state
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        # Data already in session, no need to do anything
        return True
    
    # Try to load from cache_manager
    import cache_manager
    
    # Try to load collected deck metadata directly
    metadata_loaded = cache_manager.load_collected_decks_metadata(deck_name, set_name)
    if metadata_loaded:
        # Successfully loaded from disk cache
        return True
    
    # If metadata loading failed, check if we have analyzed data
    try:
        # First check if deck is in analyzed cache
        cache_key = f"full_deck_{deck_name}_{set_name}"
        if 'analyzed_deck_cache' in st.session_state and cache_key in st.session_state.analyzed_deck_cache:
            # We have analyzed data but no collected decks - trigger a collection
            # Generate metadata from analyzed data if possible
            cache_manager.ensure_analyzed_deck_consistency(deck_name, set_name)
            
            # Check if that populated the collected_decks
            if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
                return True
    except Exception as e:
        # Log error but continue to direct collection
        print(f"Error ensuring analyzed deck consistency: {e}")
    
    # If we still don't have collected data, we need to collect directly
    with st.spinner("Loading deck data..."):
        from analyzer import collect_decks
        all_decks, all_energy_types, total_decks = collect_decks(deck_name, set_name)
        
        # Store in session state if not already there
        if deck_key not in st.session_state.collected_decks:
            st.session_state.collected_decks[deck_key] = {
                'decks': all_decks,
                'all_energy_types': all_energy_types,
                'total_decks': total_decks
            }
    
    # Final check
    has_data = 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks and st.session_state.collected_decks[deck_key]['decks']
    return has_data
    
def render_optimal_variant_deck(variant_pokemon, other_variants, shown_deck_nums, energy_types, is_typical, check_only=False):
    """Find and render the best deck for this variant Pokémon"""
    # Early exit if no analyzed deck
    if 'analyze' not in st.session_state:
        st.info("Select a deck to view a sample")
        return None
        
    # Get deck details from session state
    deck_name = st.session_state.analyze.get('deck_name', '')
    set_name = st.session_state.analyze.get('set_name', '')
    
    # Target card info
    target_name = variant_pokemon['card_name']
    target_set = variant_pokemon.get('set', '')
    target_num = variant_pokemon.get('num', '')
    
    # Call the ensure function to make sure we have collected decks
    has_data = ensure_deck_collection_data(deck_name, set_name)
    
    # Exit if we couldn't get any deck data
    if not has_data:
        st.warning("Unable to load variant deck data")
        return None
    
    # Get collected data
    deck_key = f"{deck_name}_{set_name}"
    collected_data = st.session_state.collected_decks[deck_key]
    all_decks = collected_data['decks']
    
    # Find decks with the target card
    exact_matches = []
    
    for deck_index, deck in enumerate(all_decks):
        # Skip if deck number already shown
        if 'deck_num' in deck and deck['deck_num'] in shown_deck_nums:
            continue
            
        # Skip if deck has no cards
        if 'cards' not in deck or not deck['cards']:
            # If cards missing, try to retrieve them
            try:
                from scraper import get_deck_by_player_tournament
                if 'tournament_id' in deck and 'player_id' in deck:
                    cards, deck_energy_types = get_deck_by_player_tournament(
                        deck['tournament_id'], 
                        deck['player_id']
                    )
                    deck['cards'] = cards
                    
                    # Also set energy types if needed
                    if not deck.get('energy_types') and deck_energy_types:
                        deck['energy_types'] = deck_energy_types
                        
                    # Save the updated deck back to session state
                    st.session_state.collected_decks[deck_key]['decks'][deck_index] = deck
            except Exception as e:
                # Couldn't retrieve cards, skip this deck
                continue
            
            # Double-check if cards retrieved successfully
            if 'cards' not in deck or not deck['cards']:
                continue
        
        # Check each card in this deck
        has_exact_match = False
        has_name_match = False
        other_variant_count = 0
        
        for card in deck['cards']:
            # Only check Pokémon cards
            if card.get('type') != 'Pokemon' or 'card_name' not in card:
                continue
                
            # Check for exact match on name, set, and number
            if (card['card_name'] == target_name and 
                card.get('set', '') == target_set and 
                str(card.get('num', '')) == str(target_num)):
                has_exact_match = True
                
            # Count other variants
            for other in other_variants:
                if other.lower() == card['card_name'].lower():
                    other_variant_count += 1
        
        # If we found a match in this deck, track it
        if has_exact_match:
            score = 10 - other_variant_count
            exact_matches.append((deck, score, deck.get('deck_num', deck_index)))
    
    # Choose best match
    best_deck = None
    best_deck_num = None
    
    if exact_matches:
        # Sort by score and take best
        best_match = sorted(exact_matches, key=lambda x: x[1], reverse=True)[0]
        best_deck, _, best_deck_num = best_match
    
    # NEW: If check_only mode, just return whether we found a deck
    if check_only:
        return best_deck_num
        
    # Render the chosen deck
    if best_deck:
        # Prepare cards for rendering
        pokemon_cards = []
        trainer_cards = []
        
        for card in best_deck['cards']:
            if card['type'] == 'Pokemon':
                pokemon_cards.append(card)
            else:
                trainer_cards.append(card)
        
        # Display energy types if available
        if energy_types:
            from energy_utils import render_energy_icons
            energy_html = render_energy_icons(energy_types, is_typical)
            st.markdown(energy_html, unsafe_allow_html=True)
        
        # Render the deck
        from card_renderer import render_sidebar_deck
        deck_html = render_sidebar_deck(
            pokemon_cards, 
            trainer_cards,
            card_width=70
        )
        st.markdown(deck_html, unsafe_allow_html=True)
        
        # Return the deck number so we can track that we've shown it
        return best_deck_num
    else:
        # No suitable deck found - use fallback
        import cache_manager
        sample_deck = cache_manager.get_or_load_sample_deck(deck_name, set_name)
        
        if sample_deck:
            # Display energy types if available
            if energy_types:
                from energy_utils import render_energy_icons
                energy_html = render_energy_icons(energy_types, is_typical)
                st.markdown(energy_html, unsafe_allow_html=True)
            
            # Render the sample deck
            from card_renderer import render_sidebar_deck
            deck_html = render_sidebar_deck(
                sample_deck['pokemon_cards'], 
                sample_deck['trainer_cards'],
                card_width=70
            )
            st.markdown(deck_html, unsafe_allow_html=True)
        
        return None

def render_clean_sample_deck(variant_pokemon_names, energy_types, is_typical):
    """Render a sample deck that doesn't contain any of the variant Pokémon"""
    if 'analyze' not in st.session_state:
        st.info("Select a deck to view a sample")
        return
        
    deck_name = st.session_state.analyze.get('deck_name', '')
    set_name = st.session_state.analyze.get('set_name', '')
    
    # Ensure deck collection data
    has_data = ensure_deck_collection_data(deck_name, set_name)
    
    deck_key = f"{deck_name}_{set_name}"
    
    # If we have collected data, try to find a clean deck
    clean_deck = None
    
    if has_data and deck_key in st.session_state.collected_decks:
        collected_data = st.session_state.collected_decks[deck_key]
        all_decks = collected_data.get('decks', [])
        
        # Try to find a deck without any variant Pokémon
        for deck in all_decks:
            if 'cards' not in deck:
                continue
                
            has_variant = False
            
            # Check if any variant Pokémon are in this deck
            for card in deck['cards']:
                if card.get('type') == 'Pokemon' and card.get('card_name', '').lower() in variant_pokemon_names:
                    has_variant = True
                    break
            
            # If no variant Pokémon found, use this deck
            if not has_variant:
                clean_deck = deck
                break
    
    # If we found a clean deck, display it
    if clean_deck and 'cards' in clean_deck:
        # Prepare cards for rendering
        pokemon_cards = []
        trainer_cards = []
        
        for card in clean_deck['cards']:
            if card.get('type') == 'Pokemon':
                pokemon_cards.append(card)
            else:
                trainer_cards.append(card)
        
        # Display energy types if available
        if energy_types:
            from energy_utils import render_energy_icons
            energy_html = render_energy_icons(energy_types, is_typical)
            st.markdown(energy_html, unsafe_allow_html=True)
        
        # Render the clean deck
        from card_renderer import render_sidebar_deck
        deck_html = render_sidebar_deck(
            pokemon_cards, 
            trainer_cards,
            card_width=65
        )
        st.markdown(deck_html, unsafe_allow_html=True)
    else:
        # Fall back to the standard sample deck
        render_sample_deck(energy_types, is_typical)

def render_variant_deck(variant_pokemon, energy_types, is_typical):
    """Find and render a deck containing the variant Pokemon"""
    if 'analyze' not in st.session_state:
        st.info("Select a deck to view a sample")
        return
        
    deck_name = st.session_state.analyze.get('deck_name', '')
    set_name = st.session_state.analyze.get('set_name', '')
    deck_key = f"{deck_name}_{set_name}"
    
    # Get the collected decks
    if 'collected_decks' not in st.session_state or deck_key not in st.session_state.collected_decks:
        st.info("No collected deck data available")
        return
    
    collected_data = st.session_state.collected_decks[deck_key]
    all_decks = collected_data['decks']
    
    # Find a deck containing this Pokemon
    pokemon_name = variant_pokemon['card_name']
    variant_deck = None
    
    for deck in all_decks:
        # Check if deck contains this Pokemon
        for card in deck['cards']:
            if card['card_name'] == pokemon_name and card['type'] == 'Pokemon':
                variant_deck = deck
                break
        if variant_deck:
            break
    
    if not variant_deck:
        st.info(f"No deck found containing {pokemon_name}")
        return
    
    # Prepare cards for rendering
    pokemon_cards = []
    trainer_cards = []
    
    for card in variant_deck['cards']:
        if card['type'] == 'Pokemon':
            pokemon_cards.append(card)
        else:
            trainer_cards.append(card)
    
    # Display energy types if available
    if energy_types:
        from energy_utils import render_energy_icons
        energy_html = render_energy_icons(energy_types, is_typical)
        st.markdown(energy_html, unsafe_allow_html=True)
    
    # Display a caption with deck info
    #st.caption(f"Deck containing {pokemon_name}")
    
    # Render the deck using CardGrid
    from card_renderer import render_sidebar_deck
    deck_html = render_sidebar_deck(
        pokemon_cards, 
        trainer_cards,
        card_width=65
    )
    st.markdown(deck_html, unsafe_allow_html=True)

def render_sample_deck(energy_types, is_typical):
    """Render the standard sample deck for the current archetype"""
    if 'analyze' not in st.session_state:
        st.info("Select a deck to view a sample")
        return
        
    deck_name = st.session_state.analyze.get('deck_name', '')
    set_name = st.session_state.analyze.get('set_name', '')
    
    # Import necessary functions
    import cache_manager
    from card_renderer import render_sidebar_deck
    
    # Get sample deck data
    sample_deck = cache_manager.get_or_load_sample_deck(deck_name, set_name)
    
    # Display energy types if available
    if energy_types:
        from energy_utils import render_energy_icons
        energy_html = render_energy_icons(energy_types, is_typical)
        st.markdown(energy_html, unsafe_allow_html=True)
    
    # Render the sample deck
    if sample_deck:
        deck_html = render_sidebar_deck(
            sample_deck['pokemon_cards'], 
            sample_deck['trainer_cards'],
            card_width=65
        )
        st.markdown(deck_html, unsafe_allow_html=True)
    else:
        st.info("No sample deck available")


def display_deck_composition(deck_info, energy_types, is_typical, total_cards, options, variant_df=None):
    """Display the deck composition section"""
    # Create header
    # st.write("##### Deck Composition", unsafe_allow_html=True)
    if energy_types:
        # Render energy icons for header
        energy_html = ""
        for energy in energy_types:
            energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
            energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:20px; margin-right:4px; vertical-align:middle;">'
        
        # Create header with energy types
        archetype_note = '<span style="font-size: 0.8rem; color: #888; margin-left: 4px;">(most common)</span>' if is_typical else ""
        core_cards_header = f"""##### Meta Essentials ({total_cards} Cards)""" + f"""<span style="font-size: 1rem; font-weight: normal;">&emsp; Energy: {energy_html}</span>"""
    else:
        # Just "Core Cards" if no energy found
        core_cards_header = f"##### Meta Essentials ({total_cards} Cards):"
    
    # Display the header
    st.write(core_cards_header, unsafe_allow_html=True)
    #st.markdown(f"""<span style="font-size: 1rem; font-weight: normal;">Energy: {energy_html}{archetype_note}</span>""", unsafe_allow_html=True)
    
    # Create single column card grid renderer with larger card size
    from card_renderer import CardGrid
    
    # Core Cards: Pokemon and Trainer in columns with 1:2 ratio
    core_col1, core_col2 = st.columns([2, 3])
    
    with core_col1:
        # Pokemon cards section
        st.caption("Pokémon")
        pokemon_grid = CardGrid(card_width=65, gap=4)
        pokemon_grid.add_cards_from_dict(deck_info['Pokemon'], repeat_by_count=True)
        pokemon_grid.display()
    
    with core_col2:
        # Trainer cards section
        st.caption("Trainer")
        trainer_grid = CardGrid(card_width=65, gap=4)
        trainer_grid.add_cards_from_dict(deck_info['Trainer'], repeat_by_count=True)
        trainer_grid.display()
        
    # Flexible slots section
    remaining = 20 - total_cards
    st.write("<br>", unsafe_allow_html=True)
    st.write(f"##### Remaining {remaining} Slots:", unsafe_allow_html=True)
    
    # Sort options by usage percentage (descending) and split by type
    pokemon_options = options[options['type'] == 'Pokemon'].sort_values(by='display_usage', ascending=False)
    trainer_options = options[options['type'] == 'Trainer'].sort_values(by='display_usage', ascending=False)
    
    # Flexible Slots: Pokemon and Trainer options in columns with 1:2 ratio
    flex_options_available = not pokemon_options.empty or not trainer_options.empty
    
    if flex_options_available:
        flex_col1, flex_col2 = st.columns([2, 3])
        
        with flex_col1:
            # Only show Pokemon options if there are any
            if not pokemon_options.empty:
                st.caption("Pokémon Options")
                pokemon_options_grid = CardGrid(card_width=65, gap=4, show_percentage=True)
                pokemon_options_grid.add_cards_from_dataframe(pokemon_options)
                pokemon_options_grid.display()
                
                # Add variant expanders if we have variant data
                if variant_df is not None and not variant_df.empty:
                    # Import variant renderer
                    from card_renderer import render_variant_cards
                    from visualizations import create_variant_bar_chart, display_chart
                    
                    # Get energy types and primary energy for charts
                    primary_energy = None
                    if 'analyze' in st.session_state:
                        current_deck_name = st.session_state.analyze.get('deck_name', '')
                        current_set_name = st.session_state.analyze.get('set_name', 'A3')
                        
                        # Try to get energy from deck info directly instead of requesting it again
                        if energy_types and len(energy_types) > 0:
                            primary_energy = energy_types[0]
                    
                    #st.write("##### Card Versions")
                    
                    # Display variant analysis - without nested columns
                    for idx, row in variant_df.iterrows():
                        with st.expander(f"{row['Card Name']} Details", expanded=False):
                            # Extract set codes and numbers
                            var1 = row['Var1']
                            var2 = row['Var2']
                            
                            var1_set = '-'.join(var1.split('-')[:-1])  # Everything except the last part
                            var1_num = var1.split('-')[-1]         # Just the last part
                            var2_set = '-'.join(var2.split('-')[:-1])
                            var2_num = var2.split('-')[-1]
                            
                            # Display variants side by side with inline HTML
                            variant_html = render_variant_cards(var1_set, var1_num, var2_set, var2_num, var1, var2)
                            st.markdown(variant_html, unsafe_allow_html=True)
                            
                            # Display chart below without columns - with a unique key
                            fig_var = create_variant_bar_chart(row, primary_energy)
                            variant_key = f"template_variant_{row['Card Name'].replace(' ', '_')}_{idx}"  # Use idx from enumerate
                            display_chart(fig_var, key=variant_key)
        
        with flex_col2:
            # Only show Trainer options if there are any
            if not trainer_options.empty:
                st.caption("Trainer Options")
                trainer_options_grid = CardGrid(card_width=65, gap=4, show_percentage=True)
                trainer_options_grid.add_cards_from_dataframe(trainer_options)
                trainer_options_grid.display()
        st.caption("Meta Essentials: Cards appearing in 80%+ of competitive decks. Remaining Slots: Cards appearing in 5-80% of decks, offering flexibility for tech choices, with percentages show how often each card appears in top competitive decks.")
    else:
        st.info("No remaining slots available for this deck.")
        
def display_raw_data_tab(results, variant_df):
    """Display the Raw Data tab"""
    # Main analysis data
    st.write("##### Card Usage Data")
    st.dataframe(results, use_container_width=True)
    
    # Variant analysis data
    if not variant_df.empty:
        st.write("##### Variant Analysis Data")
        st.dataframe(variant_df, use_container_width=True)

# In display_tabs.py, fix the display_metagame_tab function
def display_metagame_tab():
    """Display the Metagame Overview tab with detailed performance data"""
    st.write("##### Tournament Performance Data")
    import pandas as pd
    import re
    
    # Get performance data
    if 'performance_data' not in st.session_state:
        st.error("No performance data available in session state.")
        return
        
    performance_df = st.session_state.performance_data
    
    if performance_df.empty:
        st.warning("No tournament performance data available.")
        return
    
    # Get the currently selected deck
    current_deck_name = None
    if 'analyze' in st.session_state:
        current_deck_name = st.session_state.analyze.get('deck_name', None)
    
    # Create a cleaned, displayable version of the data
    display_df = performance_df.copy()

    # Add rank column - FIX: Keep as integers initially
    display_df['rank_int'] = range(1, len(display_df) + 1)

    # Add an indicator for the current deck - FIX: Create separate column
    display_df['rank_display'] = display_df.apply(
        lambda row: f"➡️ {row['rank_int']}" if row['deck_name'] == current_deck_name else str(row['rank_int']), 
        axis=1
    )
    
    # Calculate win rate
    total_games = display_df['total_wins'] + display_df['total_losses'] + display_df['total_ties']
    display_df['win_rate'] = ((display_df['total_wins'] + 0.5 * display_df['total_ties']) / total_games * 100).fillna(0).round(1)
    
    # Format numerical columns
    display_df['share'] = display_df['share'].round(2)
    display_df['power_index'] = display_df['power_index'].round(2)

    # FIXED: Extract Pokémon names and create image URLs with proper error handling
    try:
        # Extract Pokemon URLs for each row
        pokemon_data = []
        for _, row in display_df.iterrows():
            try:
                url1, url2 = extract_pokemon_urls(row['deck_name'])
                pokemon_data.append({'pokemon_url1': url1, 'pokemon_url2': url2})
            except Exception as e:
                print(f"Error extracting Pokemon URLs for {row['deck_name']}: {e}")
                pokemon_data.append({'pokemon_url1': None, 'pokemon_url2': None})
        
        # Convert to DataFrame and join with display_df
        pokemon_df = pd.DataFrame(pokemon_data)
        display_df = pd.concat([display_df.reset_index(drop=True), pokemon_df], axis=1)
        
    except Exception as e:
        st.error(f"Error processing Pokemon URLs: {str(e)}")
        # Continue without Pokemon images
        display_df['pokemon_url1'] = None
        display_df['pokemon_url2'] = None
    
    # Select and rename columns for display - FIX: Use rank_display
    display_cols = {
        'rank_display': 'Rank',
        'displayed_name': 'Deck',
        'share': 'Meta Share %',
        'tournaments_played': 'Best Finishes',
        'total_wins': 'Wins',
        'total_losses': 'Losses',
        'total_ties': 'Ties',
        'win_rate': 'Win %',
        'power_index': 'Index',
    }
    
    # Create final display dataframe
    try:
        final_df = display_df[list(display_cols.keys())].rename(columns=display_cols)
        
        # Add Pokémon image columns
        final_df.insert(1, 'Icon1', display_df['pokemon_url1'])
        final_df.insert(2, 'Icon2', display_df['pokemon_url2'])
        
        # Display dataframe with column configuration
        st.dataframe(
            final_df,
            use_container_width=True,
            height=850,
            column_config={
                "Rank": st.column_config.TextColumn(
                    "Rank",
                    help="Position in the meta based on Power Index",
                    width="20px"
                ),
                "Icon1": st.column_config.ImageColumn(
                    "Icon 1",
                    help="First archetype Pokémon in the deck",
                    width="20px",
                ),
                "Icon2": st.column_config.ImageColumn(
                    "Icon 2",
                    help="Second archetype Pokémon in the deck",
                    width="20px",
                ),
                "Deck": st.column_config.TextColumn(
                    "Deck",
                    help="Deck archetype name"
                ),
                "Index": st.column_config.NumberColumn(
                    "Index",
                    help="Performance metric: The Wilson score (see sidebar for details). Higher values indicate stronger performance",
                    format="%.2f"
                ),
                "Meta Share %": st.column_config.NumberColumn(
                    "Meta Share %",
                    help="Percentage representation of this deck in the overall competitive metagame",
                    format="%.2f%%"
                ),
                "Best Finishes": st.column_config.NumberColumn(
                    "Best Finishes",
                    help="Number of recent tournament entries in the 'Best Finishes' section, decided by [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET)"
                ),
                "Win %": st.column_config.NumberColumn(
                    "Win %",
                    help="Percentage of matches won out of all recorded 'Best Finishes' matches",
                    format="%.1f%%"
                ),
                "Wins": st.column_config.NumberColumn(
                    "Wins",
                    help="Total number of wins from all recorded 'Best Finishes' matches"
                ),
                "Losses": st.column_config.NumberColumn(
                    "Losses",
                    help="Total number of losses from all recorded 'Best Finishes' matches"
                ),
                "Ties": st.column_config.NumberColumn(
                    "Ties",
                    help="Total number of ties from all recorded 'Best Finishes' matches"
                )
            },
            hide_index=True
        )
        
    except KeyError as e:
        st.error(f"Missing required column in data: {e}")
        st.write("Available columns:", list(display_df.columns))
        return
    except Exception as e:
        st.error(f"Error creating display table: {e}")
        return
    
    # Add a small footnote about data source
    current_month_year = datetime.now().strftime("%B %Y")
    st.caption(f"Data based on up to {TOURNAMENT_COUNT} most recent community tournaments on Limitless TCG.")

def display_matchup_bar_chart(deck_name, set_name, working_df):
    """
    Display a bar chart showing win rate distribution with 5% bins
    
    Args:
        deck_name: Current deck name
        set_name: Current deck set  
        working_df: DataFrame with matchup data already processed
    """
    
    # Check if we have matchup data
    if working_df.empty:
        st.info("No matchup data available for bar chart.")
        return
    
    # Create 20 bins for win rates (0%, 5%, 10%, etc.)
    bins = list(range(0, 101, 5))  # [0, 5, 10, 15, ..., 95, 100]
    bin_labels = [f"{i}%" for i in range(0, 101, 5)]  # ["0%", "5%", "10%", ..., "95%"]
    
    # Round win rates to nearest 5% and assign to bins
    working_df = working_df.copy()
    working_df['win_rate_rounded'] = (working_df['win_pct'] / 5).round() * 5
    working_df['win_rate_rounded'] = working_df['win_rate_rounded'].clip(0, 100)  # Cap at 95%
    working_df['win_rate_bin'] = working_df['win_rate_rounded'].astype(int).astype(str) + "%"
    
    # Aggregate meta share by bin
    bin_data = working_df.groupby('win_rate_bin', observed=True).agg({
        'meta_share': 'sum',
        'opponent_name': 'count'  # Count of matchups in each bin
    }).reset_index()
    
    # Ensure all bins are represented (fill missing with 0)
    all_bins_df = pd.DataFrame({'win_rate_bin': bin_labels})
    bin_data = all_bins_df.merge(bin_data, on='win_rate_bin', how='left').fillna(0)
    
    # Create 20 colors by interpolating between adjacent colors
    def get_bin_color(bin_index):
        # Original 10 colors
        base_colors = [
            (220, 53, 69),     # Red (0%)
            (253, 126, 20),    # Red-Orange (10%)
            (255, 152, 0),     # Orange (20%)
            (255, 183, 77),    # Light Orange (30%)
            (255, 235, 59),    # Yellow (40%)
            (205, 220, 57),    # Yellow-Green (50%)
            (156, 204, 101),   # Light Green (60%)
            (139, 195, 74),    # Medium Green (70%)
            (102, 187, 106),   # Green (80%)
            (27, 94, 32),       # Very Dark Green (90-100%)
            (27, 94, 32)       # Very Dark Green (90-100%)
        ]
        
        # For 20 bins (0%, 5%, 10%, ..., 95%), we need interpolation
        if bin_index % 2 == 0:
            # Even indices (0%, 10%, 20%, etc.) use original colors
            original_index = bin_index // 2
            return f"rgb({base_colors[original_index][0]}, {base_colors[original_index][1]}, {base_colors[original_index][2]})"
        else:
            # Odd indices (5%, 15%, 25%, etc.) use interpolated colors
            left_index = bin_index // 2
            right_index = min(left_index + 1, len(base_colors) - 1)
            
            # Interpolate between adjacent colors
            left_color = base_colors[left_index]
            right_color = base_colors[right_index]
            
            # Average the RGB values
            avg_r = (left_color[0] + right_color[0]) // 2
            avg_g = (left_color[1] + right_color[1]) // 2
            avg_b = (left_color[2] + right_color[2]) // 2
            
            return f"rgb({avg_r}, {avg_g}, {avg_b})"
    
    # Create colors list for all bars
    bar_colors = [get_bin_color(i) for i in range(21)]
    
    # Create the bar chart
    import plotly.graph_objects as go
    
    fig = go.Figure(go.Bar(
        x=bin_data['win_rate_bin'],
        y=bin_data['meta_share'],
        marker_color=bar_colors,
        marker_line=dict(width=0),  # No outline
        text=bin_data['meta_share'].apply(lambda x: f"{x:.1f}" if x > 0 else ""),
        textposition='outside',
        textfont=dict(size=12),
        hovertemplate="<b>%{x}</b><br>Meta Share: %{y:.1f}%<br>Matchups: %{customdata}<extra></extra>",
        customdata=bin_data['opponent_name']
    ))

    # Add vertical line at 50% win rate
    fig.add_vline(
        x=50,  # Position at 50% bin
        line_dash="dot",
        line_color="rgba(128, 128, 128, 0.5)",
        line_width=1
    )

    fig.add_annotation(
        x=50,  # Same index position
        y=29,  # Slightly above the chart area
        text="50%",
        showarrow=False,
        font=dict(size=12, color="rgba(128, 128, 128, 0.9)")
    )

    # fig.add_annotation(
    #         x=0.5,  # Center horizontally
    #         y=-0.15,  # Position below the plot
    #         xref='paper',  # Use paper coordinates (0-1)
    #         yref='paper',
    #         text="Shows how much of the meta falls into each 5% win rate interval (win rates rounded to nearest 5%). Higher bars in green ranges = more favorable meta coverage.",
    #         showarrow=False,
    #         font=dict(color="rgb(163, 168, 184)", size=11),
    #         align="center",
    #         bgcolor="rgba(0,0,0,0)",
    #         bordercolor="rgba(0,0,0,0)"
    # )

    # Update layout - Clean and minimal
    fig.update_layout(
        height=300,
        margin=dict(t=0, l=0, r=0, b=0),
        
        # Transparent backgrounds
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        
        # Clean axes
        xaxis=dict(
            title="Win Rate (%)",
            title_font=dict(size=15),
            tickfont=dict(size=12),
            showgrid=False,
            showline=False,
            zeroline=False,
            # Show every 5% tick
            tickmode='array',
            tickvals=[f"{i}%" for i in range(0, 101, 5)],
            ticktext=[str(i) for i in range(0, 101, 5)]  # Show numbers without %
        ),
        yaxis=dict(
            title=None,
            #title="Meta Share %",
            title_font=dict(size=16),
            tickfont=dict(size=14),
            showgrid=False,
            showline=False,
            zeroline=False,
            range=[0, 29.9],
            ticksuffix='%'
        ),
        
        # Remove legend and other elements
        showlegend=False,
        font=dict(size=11)
    )
    
    custom_config = {
        'displayModeBar': False,
        'staticPlot': True,
        'displaylogo': False,
    }
    
    st.plotly_chart(fig, use_container_width=True, config=custom_config, key="matchup_bar_chart")
    
    # Add explanation
    st.caption(
        "Shows how much of the meta share falls into each 5% win rate interval."
    )
    
# Modify the display_related_decks_tab function in display_tabs.py:
def display_related_decks_tab(deck_info, results):
    """Display the Related Decks tab with banner images and simple buttons"""
    st.write("##### Related Decks")
    
    # Get the current deck name
    current_deck_name = deck_info['deck_name']
    
    # Make sure we have the deck name mapping from the dropdown
    if 'deck_name_mapping' in st.session_state:
        # Find related decks from the deck selection dropdown list
        related_decks = find_related_decks(current_deck_name, st.session_state.deck_name_mapping)
        
        if related_decks.empty:
            st.info("No related decks found in the current meta.")
        else:
            # Display related decks in a simple grid
            
            # Create a 3-column layout
            cols = st.columns(3)
            
            # Display each related deck
            for i, (_, deck) in enumerate(related_decks.iterrows()):
                col_idx = i % 3
                
                with cols[col_idx]:
                    # Format deck name
                    formatted_name = format_deck_name(deck['deck_name'])
                    
                    # FIX: Use cached header image function
                    header_image = get_header_image_cached(
                        deck['deck_name'], 
                        deck['set']
                    )
                    
                    # Simple tertiary button with the deck name
                    if st.button(formatted_name, key=f"btn_{deck['deck_name']}_{i}", type="tertiary"):
                        # Set this deck to be analyzed
                        st.session_state.deck_to_analyze = deck['deck_name']
                        # Force rerun to trigger the analysis
                        st.rerun()
                        
                    # Display the banner image
                    if header_image:
                        st.markdown(f"""
                        <div style="width: 100%; margin-top: -18px; margin-bottom: 12px; position: relative;">
                            <img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 300px; height: auto; border-radius: 4px; z-index:-2;">
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="width: 100%; margin-top: -18px; margin-bottom: 12px; background-color: #f0f0f0; border-radius: 6px 6px 0 0; display: flex; align-items: center; justify-content: center;">
                            <span style="color: #888;">No image</span>
                        </div>
                        """, unsafe_allow_html=True)
        #                 st.markdown(f"""
        # <div style="width: 100%; margin-top: -18px; margin-bottom: 12px; position: relative;">
        #     <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border-radius: 4px; z-index:-2;">
        #     <div style="position: absolute; bottom: 0px; right: 0px; background-color: rgba(0, 0, 0, 0.8); color: white; padding: 2px 4px; border-radius: 4px 0px 4px 0px; font-size: 0.6rem; font-weight: 700;">
        #         {stats_text}
        #     </div>
        # </div>
        # """, unsafe_allow_html=True)
                    
 
                        
            st.caption("Decks sharing featured Pokémon with this archetype.")
    else:
        st.info("Deck list not available. Unable to find related decks.")

def debug_deck_collection(deck_name, set_name):
    """Output debug information about deck collection status"""
    deck_key = f"{deck_name}_{set_name}"
    
    # Check if decks have been collected
    has_collected = 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks
    
    # Check cache
    cache_key = f"full_deck_{deck_name}_{set_name}"
    has_cache = cache_key in st.session_state.analyzed_deck_cache if 'analyzed_deck_cache' in st.session_state else False
    
    # Check disk
    safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
    base_path = os.path.join("cached_data/analyzed_decks", f"{safe_name}_{set_name}")
    has_disk = os.path.exists(f"{base_path}_results.csv")
    
    st.sidebar.write(f"**Debug: {deck_name}**")
    st.sidebar.write(f"- Collected: {'✓' if has_collected else '✗'}")
    st.sidebar.write(f"- Session Cache: {'✓' if has_cache else '✗'}")
    st.sidebar.write(f"- Disk Cache: {'✓' if has_disk else '✗'}")
    
    if has_collected:
        decks_count = len(st.session_state.collected_decks[deck_key]['decks'])
        st.sidebar.write(f"- Collected Decks: {decks_count}")

def display_energy_debug_tab(deck_info):
    """Display the Energy Debug tab with detailed analysis and diagnostic information"""
    
    deck_name = deck_info['deck_name']
    set_name = deck_info.get('set_name', 'A3')

    # First check if we have per-deck energy data
    if 'per_deck_energy' in st.session_state and deck_name in st.session_state.per_deck_energy:
        # We can still use the existing detailed energy table
        from energy_utils import display_detailed_energy_table
        st.markdown(display_detailed_energy_table(deck_name), unsafe_allow_html=True)
    else:
        # Create a simplified version that works directly with collected decks
        deck_key = f"{deck_name}_{set_name}"
        if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
            collected_data = st.session_state.collected_decks[deck_key]
            
            if 'decks' in collected_data and collected_data['decks']:
                # Get all unique energy types
                all_energies = set()
                energy_by_deck = {}
                
                for deck in collected_data['decks']:
                    if 'energy_types' in deck and deck['energy_types'] and 'deck_num' in deck:
                        deck_num = deck['deck_num']
                        energy_types = sorted(deck['energy_types'])
                        energy_by_deck[deck_num] = energy_types
                        all_energies.update(energy_types)
                
                # Create table directly if we have data
                if energy_by_deck and all_energies:
                    all_energies = sorted(all_energies)
                    
                    # Create table HTML directly
                    table_html = generate_energy_table_html(all_energies, energy_by_deck)
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.info("No energy data found in collected decks")
            else:
                st.info("No decks found in collected data")
        else:
            st.info("No collected decks found")
            
def generate_energy_table_html(all_energies, energy_by_deck):
    """Generate HTML for energy table from collected decks data in two columns"""
    # Create the overall container with columns
    table_html = """<div style="margin-top: 15px; display: flex; gap: 20px;">
        <div style="flex: 1;">"""
    
    # First column: Energy by Deck table
    table_html += """<h6 style="margin-bottom: 10px;">Energy by Deck</h6>
            <table style="width: 100%; font-size: 1rem; margin-top:-15px; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #ddd;">
                    <th style="text-align: left; padding: 4px; font-size: 1rem;">Deck #</th>"""
    
    # Add energy type headers
    for energy in all_energies:
        energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
        table_html += f'<th style="text-align: center; padding: 4px;"><img src="{energy_url}" alt="{energy}" style="height:20px;"></th>'
    
    table_html += "</tr>"
    
    # Add a row for each deck
    for deck_num, energies in sorted(energy_by_deck.items()):
        table_html += f"""<tr style="border-bottom: 1px solid #eee;"><td style="text-align: left; padding: 4px;">{deck_num}</td>"""
        
        # For each possible energy type, check if this deck has it
        for energy in all_energies:
            has_energy = energy in energies
            check_mark = "✓" if has_energy else ""
            bg_color = "rgba(0, 160, 255, 0.1)" if has_energy else "transparent"
            
            table_html += f'<td style="text-align: center; padding: 4px; background-color: {bg_color};">{check_mark}</td>'
        
        table_html += "</tr>"
    
    # Close the first table and column
    table_html += """</table></div>"""
        
    # Second column: Energy Combinations
    table_html += """<div style="flex: 1;">"""
    
    # Calculate combinations for the second table
    combo_stats = {}
    for energies in energy_by_deck.values():
        combo = tuple(sorted(energies))
        combo_stats[combo] = combo_stats.get(combo, 0) + 1
    
    # Sort combinations by frequency
    sorted_combos = sorted(combo_stats.items(), key=lambda x: x[1], reverse=True)
    
    # Add combo statistics
    table_html += """<h6 style="margin-bottom: 10px;">Energy Combinations</h6>
            <table style="width: 100%; font-size: 1rem; margin-top:-15px; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #ddd;">
                    <th style="text-align: left; padding: 4px; font-size: 1rem;">Energy</th>
                    <th style="text-align: right; padding: 4px; width: 80px; font-size: 1rem;">Count</th>
                    <th style="text-align: right; padding: 4px; width: 80px; font-size: 1rem;">Ratio</th>
                </tr>"""
    
    total_decks = len(energy_by_deck)
    
    for combo, count in sorted_combos:
        # Generate energy icons
        energy_html = ""
        for energy in combo:
            energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
            energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:16px; margin-right:3px; vertical-align:middle;">'
        
        percentage = (count / total_decks * 100) if total_decks > 0 else 0
        
        table_html += f"""<tr style="border-bottom: 1px solid #eee;">
                    <td style="text-align: left; padding: 4px;">{energy_html}</td>
                    <td style="text-align: right; padding: 4px;">{count}</td>
                    <td style="text-align: right; padding: 4px;">{percentage:.1f}%</td>
                </tr>"""
    
    # Close the second table and both divs
    table_html += """</table>
        </div>
    </div>"""
    
    return table_html
    
def generate_energy_analysis(deck_info):
    """Generate the energy analysis table for the Card Usage tab"""
    deck_name = deck_info['deck_name']
    set_name = deck_info.get('set_name', 'A3')
    
    # First check if we have per-deck energy data
    if 'per_deck_energy' in st.session_state and deck_name in st.session_state.per_deck_energy:
        # We can still use the existing detailed energy table
        from energy_utils import display_detailed_energy_table
        st.markdown(display_detailed_energy_table(deck_name), unsafe_allow_html=True)
    else:
        # Create a simplified version that works directly with collected decks
        deck_key = f"{deck_name}_{set_name}"
        if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
            collected_data = st.session_state.collected_decks[deck_key]
            
            if 'decks' in collected_data and collected_data['decks']:
                # Get all unique energy types
                all_energies = set()
                energy_by_deck = {}
                
                for deck in collected_data['decks']:
                    if 'energy_types' in deck and deck['energy_types'] and 'deck_num' in deck:
                        deck_num = deck['deck_num']
                        energy_types = sorted(deck['energy_types'])
                        energy_by_deck[deck_num] = energy_types
                        all_energies.update(energy_types)
                
                # Create table directly if we have data
                if energy_by_deck and all_energies:
                    all_energies = sorted(all_energies)
                    
                    # Create table HTML directly
                    table_html = generate_energy_table_html(all_energies, energy_by_deck)
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.info("No energy data found in collected decks")
            else:
                st.info("No decks found in collected data")
        else:
            st.info("No collected decks found")

# Add these functions to display_tabs.py
# In display_tabs.py - Remove the circular reference
def fetch_matchup_data(deck_name, set_name="A3"):
    """
    Fetch matchup data for a specific deck from Limitless TCG.
    Uses cache_manager but doesn't create a circular reference.
    
    Args:
        deck_name: The name of the deck
        set_name: The set name (default: "A3")
        
    Returns:
        DataFrame containing matchup data or empty DataFrame if not found
    """
    import cache_manager
    
    # Direct call to get_or_fetch_matchup_data
    return cache_manager.get_or_fetch_matchup_data(deck_name, set_name)

# In display_tabs.py - Update the display_matchup_summary function

def display_matchup_summary(deck_name, set_name, working_df):
    """
    Display a summary of matchup distribution against the meta
    
    Args:
        deck_name: Current deck name
        set_name: Current deck set
        working_df: DataFrame with matchup data already processed
    """
    st.write("##### Meta Matchup Distribution")
    
    # Check if we have matchup data with meta share
    if working_df.empty or 'meta_share' not in working_df.columns:
        st.info("No matchup data with meta share available.")
        return

    win_upper = 55
    win_lower = 45
    
    # Classify each matchup
    working_df['matchup_type'] = working_df['win_pct'].apply(
        lambda wp: "Favorable" if wp >= win_upper else ("Unfavorable" if wp < win_lower else "Even")
    )
    
    # Calculate total meta share in each category
    favorable_share = working_df[working_df['matchup_type'] == 'Favorable']['meta_share'].sum()
    even_share = working_df[working_df['matchup_type'] == 'Even']['meta_share'].sum()
    unfavorable_share = working_df[working_df['matchup_type'] == 'Unfavorable']['meta_share'].sum()
    
    # Calculate total share of just these three categories
    total_known_share = favorable_share + even_share + unfavorable_share
    
    # Calculate Meta Win Rate (weighted average win rate by meta share)
    if total_known_share > 0:
        # Weight each matchup's win rate by its meta share
        weighted_win_rate = (working_df['win_pct'] * working_df['matches_played'] * working_df['meta_share']).sum() / (working_df['matches_played'] * working_df['meta_share']).sum()
        
        # Normalize values to sum to 100% (just the three known categories)
        favorable_share_norm = (favorable_share / total_known_share) * 100
        even_share_norm = (even_share / total_known_share) * 100
        unfavorable_share_norm = (unfavorable_share / total_known_share) * 100
    else:
        # If no data, set all to 0
        weighted_win_rate = 0
        favorable_share_norm = 0
        even_share_norm = 0
        unfavorable_share_norm = 0

    
    # Display the bar chart
    display_matchup_bar_chart(deck_name, set_name, working_df)
    
    # Create 4-column layout instead of 3
    col1, col2, col3, col4 = st.columns([1,1,1, 1])
    
    # Display unfavorable matchups
    with col1:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px; border-radius: 8px; height: 100px;">
            <div style="font-size: 0.7rem; font-weight: bold; ">Unfavorable</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: #fd6c6c; line-height: 0.8;">{unfavorable_share_norm:.1f}%</div>
            <div style="font-size: 0.7rem; ">of meta</div>
        </div>
        """, unsafe_allow_html=True)
        
    # Display even matchups
    with col2:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px;  border-radius: 8px; height: 100px;">
            <div style="font-size: 0.7rem; font-weight: bold;">Even</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: #E6CA00; line-height: 0.8;">{even_share_norm:.1f}%</div>
            <div style="font-size: 0.7rem;">of meta</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display favorable matchups
    with col3:
       st.markdown(f"""
       <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px;  border-radius: 8px; height: 100px;">
            <div style="font-size: 0.7rem; font-weight: bold; ">Favorable</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: #4FCC20; line-height: 0.8;">{favorable_share_norm:.1f}%</div>
            <div style="font-size: 0.7rem; ">of meta</div>
        </div>
        """, unsafe_allow_html=True)

    # NEW: Display Meta Win Rate
    with col4:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px; border-radius: 8px; height: 100px;">
            <div style="font-size: 0.7rem; font-weight: bold;">Meta Win Rate</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: #00A0FF; line-height: 0.8;">{weighted_win_rate:.1f}%</div>
            <div style="font-size: 0.7rem;">weighted avg</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.caption(f"This shows how much of the current meta (≥0.5% share) has favorable (≥{win_upper}% win rate), even ({win_lower}-{win_upper}% win rate), or unfavorable (<{win_lower}% win rate) matchups against this deck. Values are normalized to sum to 100%. (Raw data: Unfavorable {unfavorable_share:.1f}%, Even {even_share:.1f}%, Favorable {favorable_share:.1f}%).  Meta Win Rate is the average win rate weighted by match count and opponent meta share for reliability.")       
    
    # Add some space
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

def create_meta_trend_chart(deck_name):
    """
    Create a line chart showing meta percentage trend over time for a specific deck
    Modified to show last 30 days instead of from set release
    """
    import sqlite3
    import pandas as pd
    import plotly.graph_objects as go
    try:
        # Connect to SQLite database
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        # Calculate cutoff date for last 30 days
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Query to get daily aggregated data for the specific archetype in last 30 days
        query = """
        SELECT 
            t.date,
            COALESCE(SUM(aa.count), 0) as archetype_players,
            SUM(t.total_players) as total_players
        FROM tournaments t
        LEFT JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id 
            AND aa.archetype = ?
        WHERE t.date >= ?
        GROUP BY t.date
        HAVING total_players > 0
        ORDER BY t.date
        """
        
        # Execute query with deck name and 30-day cutoff
        df = pd.read_sql_query(query, conn, params=[deck_name, cutoff_date])
        conn.close()
        
        if df.empty:
            print(f"No data found for archetype: {deck_name} in last 30 days")
            return None
        
        # Calculate percentage for each date
        df['meta_percentage'] = (df['archetype_players'] / df['total_players']) * 100
        
        # Convert date strings to datetime for better plotting
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter out dates where archetype had 0% (optional - removes gaps)
        df_filtered = df[df['meta_percentage'] > 0].copy()
        
        if df_filtered.empty:
            print(f"No appearances found for archetype: {deck_name} in last 30 days")
            return None
        
        # Create the line chart
        fig = go.Figure()

        # Define color zones (every 2% with alpha 0.2)
        color_zones = [
            {"range": [0, 2], "color": "rgba(253, 231, 37, 0.6)"},    # FDE725
            {"range": [2, 4], "color": "rgba(159, 218, 58, 0.6)"},   # 9FDA3A
            {"range": [4, 6], "color": "rgba(73, 193, 109, 0.6)"},   # 49C16D
            {"range": [6, 8], "color": "rgba(32, 160, 135, 0.6)"},   # 20A087
            {"range": [8, 10], "color": "rgba(39, 127, 142, 0.6)"},  # 277F8E
            {"range": [10, 12], "color": "rgba(55, 91, 141, 0.6)"},  # 375B8D
            {"range": [12, 14], "color": "rgba(70, 51, 127, 0.6)"},  # 46337F
            {"range": [14, 100], "color": "rgba(69, 15, 84, 0.6)"},  # 450F54
        ]
        
        # Add background color zones
        for zone in color_zones:
            fig.add_hrect(
                y0=zone["range"][0], 
                y1=zone["range"][1],
                fillcolor=zone["color"],
                line_width=0,
                layer="below"
            )
            
        fig.add_trace(go.Scatter(
            x=df_filtered['date'],
            y=df_filtered['meta_percentage'],
            mode='lines+markers',
            name='Meta Share %',
            line=dict(color='#FFFFFF', width=2),
            marker=dict(size=8, color='#FFFFFF'),
            hovertemplate='<b>%{x}</b><br>Meta Share: %{y:.1f}%<br>Players: %{customdata[0]}<br>Total: %{customdata[1]}<extra></extra>',
            customdata=list(zip(df_filtered['archetype_players'], df_filtered['total_players']))
        ))
        
        # Update layout
        fig.update_layout(
            title=f"Meta Trend: {deck_name.replace('-', ' ').title()} (Last 30 Days)",
            xaxis_title="Date",
            yaxis_title="Meta Share (%)",
            height=400,
            margin=dict(t=10, l=10, r=10, b=10),
            hovermode='x unified',
            
            # Styling to match your app
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            showlegend=False,
            
            # Grid and axes styling
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.15)',
                showline=True,
                linecolor='rgba(128,128,128,0.3)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.15)',
                showline=True,
                linecolor='rgba(128,128,128,0.3)',
                range=[0, df_filtered['meta_percentage'].max() * 1.15],
                tickmode='linear',
                tick0=0,
                dtick=2,
                ticksuffix='%'
            )
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating meta trend chart: {e}")
        return None

def display_meta_trend_section(deck_name):
    """
    Display the meta trend section with line chart
    
    Args:
        deck_name: The internal deck name from the current selection
    """
    import streamlit as st
    
    st.write("##### Meta Share Trend")
    
    # Create the chart
    fig = create_meta_trend_chart(deck_name)
    
    if fig:
        # Display the chart
        config = {
        'displayModeBar': False,  # This hides the entire toolbar
        'staticPlot': False,      # Keep interactivity (zoom, pan, hover)
        'displaylogo': False,
        }       
        
        st.plotly_chart(fig, use_container_width=True, config=config, key="meta_trend_chart")
        
        # Add explanation
        st.caption(
            "Shows daily meta share percentage based on tournament data. "
            "Each point represents the combined percentage across all tournaments on that date."
        )
    else:
        st.info(f"No meta trend data available for this deck archetype.")
        
# In display_tabs.py, fix the display_matchup_tab function
def display_matchup_tab(deck_info=None):
    """
    Display the Matchup tab with detailed matchup data.
    
    Args:
        deck_info: Dictionary containing deck information (optional)
    """
    import pandas as pd
    import re
    
    # Use current deck if none provided
    if not deck_info and 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', '')
        set_name = st.session_state.analyze.get('set_name', 'A3')
    elif deck_info:
        deck_name = deck_info.get('deck_name', '')
        set_name = deck_info.get('set', 'A3')
    else:
        st.warning("No deck selected for matchup analysis.")
        return
    
    # Fetch matchup data
    matchup_df = fetch_matchup_data(deck_name, set_name)
    
    if matchup_df.empty:
        st.info(f"No matchup data available for {deck_name}.")
        return
    
    # Get list of top meta decks to filter by
    meta_decks = []
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        meta_decks = st.session_state.performance_data['deck_name'].tolist()
    
    # Always filter by default
    show_all = False
    
    # Create a copy to work with
    working_df = matchup_df.copy()

    # Filter out current deck from matchups
    #working_df = working_df[working_df['opponent_deck_name'] != deck_name]

    # Filter by minimum matches
    from config import MIN_MATCHUP_MATCHES
    original_count = len(working_df)
    working_df = working_df[working_df['matches_played'] >= MIN_MATCHUP_MATCHES]
    filtered_count = original_count - len(working_df)

    # FIXED: Initialize filtered_df properly
    filtered_df = working_df.copy()  # Initialize filtered_df here
    
    # Only apply meta deck filtering if we have meta decks and working_df is not empty
    if meta_decks and not show_all and not working_df.empty:
        # Add lowercase versions for better matching
        working_df['deck_name_lower'] = working_df['opponent_deck_name'].str.lower()
        meta_decks_lower = [d.lower() for d in meta_decks]
        
        # Apply filter
        filtered_df = working_df[working_df['deck_name_lower'].isin(meta_decks_lower)]
        
        # Use filtered data if we found matches
        if not filtered_df.empty:
            working_df = filtered_df.drop(columns=['deck_name_lower'])
        else:
            st.warning("No matches found with current meta decks. Showing all matchups instead.")
            working_df = working_df.drop(columns=['deck_name_lower'], errors='ignore')
            filtered_df = working_df.copy()  # Reset filtered_df to working_df
    
    # FIXED: Only proceed if we still have data after all filtering
    if working_df.empty:
        st.warning("No matchup data available after filtering.")
        return
    
    # FIXED: Apply Pokemon URL extraction with proper error handling
    try:
        # Extract Pokemon URLs for each row
        pokemon_data = []
        for _, row in working_df.iterrows():
            try:
                url1, url2 = extract_pokemon_urls(row['opponent_deck_name'])
                pokemon_data.append({'pokemon_url1': url1, 'pokemon_url2': url2})
            except Exception as e:
                print(f"Error extracting Pokemon URLs for {row['opponent_deck_name']}: {e}")
                pokemon_data.append({'pokemon_url1': None, 'pokemon_url2': None})
        
        # Convert to DataFrame and join with working_df
        pokemon_df = pd.DataFrame(pokemon_data)
        working_df = pd.concat([working_df.reset_index(drop=True), pokemon_df], axis=1)
        
    except Exception as e:
        st.error(f"Error processing Pokemon URLs: {str(e)}")
        # Continue without Pokemon images
        working_df['pokemon_url1'] = None
        working_df['pokemon_url2'] = None
    
    # Create a better formatted display version
    display_df = working_df.copy()
    
    # Add rank column
    display_df.insert(0, 'Rank', range(1, len(display_df) + 1))
    
    # Add matchup column 
    display_df['Matchup'] = display_df['win_pct'].apply(
        lambda wp: "Favorable" if wp >= 55 else ("Unfavorable" if wp < 45 else "Even")
    )
    
    # Format the record column
    display_df['Record'] = display_df.apply(
        lambda row: f"{row['wins']}-{row['losses']}-{row['ties']}", axis=1
    )
    
    # FIXED: Create formatted_df with proper error handling
    try:
        # Select and rename columns for display - now including the icon columns
        formatted_df = pd.DataFrame({
            'Icon1': display_df['pokemon_url1'],
            'Icon2': display_df['pokemon_url2'],
            'Deck': display_df['opponent_name'],
            #'Matchup': display_df['Matchup'],
            'Win %': display_df['win_pct'],
            'Record': display_df['Record'],
            #'Matches': display_df['matches_played'],
            #'Meta Share %': display_df['meta_share']
        })
    except KeyError as e:
        st.error(f"Missing required column: {str(e)}")
        st.write("Available columns:", list(display_df.columns))
        return
    
    # Display the enhanced data table with all rows
    # col1, col2 = st.columns([4,3], gap="medium")
    # with col1:
    #     display_matchup_summary(deck_name, set_name, working_df)

    # with col2:
    # Apply styling for matchups
    def highlight_matchups(val):
        """Apply colors to matchup column values"""
        if val == "Favorable":
            return 'background-color: rgba(100, 200, 100, 0.4)'  # Light green
        elif val == "Unfavorable":
            return 'background-color: rgba(255, 100, 100, 0.4)'  # Light red
        else:
            return 'background-color: rgba(255, 235, 100, 0.4)'  # Light yellow
    
    def highlight_row_by_win_percentage(row):
        """Apply colors to entire row based on Win % values"""
        win_pct = row['Win %']
        if win_pct >= 55:
            color = 'background-color: rgba(100, 200, 100, 0.2)'  # Light green (Favorable)
        elif win_pct < 45:
            color = 'background-color: rgba(255, 100, 100, 0.2)'  # Light red (Unfavorable)  
        else:
            color = 'background-color: rgba(255, 235, 100, 0.2)'  # Light yellow (Even)
        
        return [color] * len(row)
    
    try:
        # Apply row-level styling based on Win %
        styled_df = formatted_df.style.apply(highlight_row_by_win_percentage, axis=1)
        #styled_df = formatted_df.style.map(highlight_matchups, subset=['Matchup'])
        st.write("##### Matchup Data")
        st.dataframe(
            styled_df,
            use_container_width=True,
            column_config={
                "Icon1": st.column_config.ImageColumn(
                    "",
                    help="Primary Pokémon in the deck",
                    width=35,
                ),
                "Icon2": st.column_config.ImageColumn(
                    "", 
                    help="Secondary Pokémon in the deck",
                    width=35,
                ),
                "Deck": st.column_config.TextColumn(
                    "Deck",
                    help="Opponent deck archetype"
                ),
                "Win %": st.column_config.NumberColumn(
                    "Win %",
                    help="Percentage of matches won against this deck",
                    format="%.1f%%",
                ),
                "Record": st.column_config.TextColumn(
                    "Record",
                    help="Win-Loss-Tie record against this deck",
                    width=60
                ),
                # "Matches": st.column_config.NumberColumn(
                #     "Matches",
                #     help="Total number of matches played against this deck"
                # ),
                # "Matchup": st.column_config.TextColumn(
                #     "Matchup",
                #     help="Favorable: ≥55%, Unfavorable: <45%, Even: 45-55%"
                # ),
                #"Meta Share%": None
                # "Meta Share %": st.column_config.NumberColumn(
                #     "Meta Share %",
                #     help="Percentage representation of this deck in the overall competitive metagame",
                #     format="%.2f%%"
                # ),
            },
            hide_index=True,
            height=700
        )
    except Exception as e:
        # Fallback to simpler version if there's an issue
        st.error(f"Error displaying styled dataframe with images: {str(e)}")
        st.write("Showing basic version without styling and images:")
        
        # Remove image columns for fallback
        basic_df = formatted_df.drop(columns=['Icon1', 'Icon2'], errors='ignore')
        st.dataframe(
            basic_df,
            use_container_width=True,
            column_config={
                "Win %": st.column_config.NumberColumn(
                    "Win %",
                    format="%.1f%%",
                ),
            },
            hide_index=True
        )
    
    # Add some space between summary and table
    if filtered_count > 0:
        st.caption(f"Showing {len(working_df)} matchups with at least {MIN_MATCHUP_MATCHES} matches.  Green = Favorable (> 55% Win Rate), Yellow = Even (45-55% Win Rate), Red = Unfavorable (< 45% Win Rate)\n"
                f"Filtered out {filtered_count} matchups with insufficient data for reliability.")
        #st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
    #st.caption(f"Data based on the current compiled tournament data on [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET).")

def display_meta_trend_tab(deck_info=None):
    """
    Display the Meta Trend tab with enhanced line chart and smart format filters
    """
    import pandas as pd
    
    # Use current deck if none provided
    if not deck_info and 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', '')
        set_name = st.session_state.analyze.get('set_name', 'A3')
    elif deck_info:
        deck_name = deck_info.get('deck_name', '')
        set_name = deck_info.get('set', 'A3')
    else:
        st.warning("No deck selected for meta trend analysis.")
        return
    
    st.write("##### Meta Share Evolution & Performance Trend")
    
    # Display indicator badges first
    # display_meta_indicators(deck_name)
    
    # Check what formats are available for this specific deck
    deck_formats = get_deck_available_formats(deck_name)
    
    # Determine if we need to show format filters
    has_noex = any('NOEX' in fmt.upper() for fmt in deck_formats)
    
    if has_noex and len(deck_formats) > 1:
        # Show format filter options
        st.write("###### Format Filters")
        
        # Initialize session state for format selection
        if 'deck_format_selection' not in st.session_state:
            st.session_state.deck_format_selection = 'Standard'  # Default to Standard only
        
        # Create radio button for format selection
        format_option = st.radio(
            "Select tournament formats to include:",
            options=['Standard', 'Standard+NOEX'],
            index=0 if st.session_state.deck_format_selection == 'Standard' else 1,
            key="format_selection_radio",
            horizontal=True
        )
        
        # Update session state
        st.session_state.deck_format_selection = format_option
        
        # Map selection to actual format list
        if format_option == 'Standard':
            selected_formats = ['Standard', 'STANDARD']  # Include both Standard variants
        else:  # 'Standard+NOEX'
            selected_formats = deck_formats  # Include all available formats
        
        chart_subtitle = f" ({format_option})"
    else:
        # No filter needed - use all available formats (likely just Standard)
        selected_formats = deck_formats if deck_formats else ['Standard']
        chart_subtitle = ""
    
    # Create the chart
    fig = create_enhanced_meta_trend_chart_combined(deck_name, selected_formats, chart_subtitle)
    
    if fig:
        # Enable interactivity
        config = {
            'displayModeBar': False,
            'displaylogo': False,
            'staticPlot': False
        }
        
        st.plotly_chart(fig, use_container_width=True, config=config, key="enhanced_meta_trend_chart")
        
        # Add explanation
        # if has_noex and len(deck_formats) > 1:
        #     st.caption(
        #         "Shows daily meta share percentage. "
        #         "'Standard' shows only Standard format tournaments. "
        #         "'Standard+NOEX' combines data from all tournament formats. "
        #         "Vertical dashed lines indicate set releases."
        #     )
        # else:
            # st.caption(
            #     "Shows daily meta share percentage based on tournament data. "
            #     "Vertical dashed lines indicate set releases."
            # )
    else:
        st.info(f"No meta trend data available for this deck archetype.")
    
    # Add performance trend chart
    #st.write("##### Performance Trends")
    
    perf_fig = create_performance_trend_chart(deck_name, selected_formats)
    
    if perf_fig:
        config = {
            'displayModeBar': False,  # This hides the entire toolbar
            'staticPlot': False,      # Keep interactivity (zoom, pan, hover)
            'displaylogo': False,
        }
        st.plotly_chart(perf_fig, use_container_width=True, config=config, key="performance_trend_chart")

        st.caption(
            "Meta Evolution: Shows daily meta share percentage based on tournament data.  \n"
            "Performance Trend: Shows win rate trends over time. Green markers = above 50% win rate, Red markers = below 50% win rate. Dotted line shows 50% reference."
        )
    else:
        st.info(f"No performance trend data available for this deck archetype.")

def get_available_formats():
    """
    Get list of available formats from the database
    
    Returns:
        List of format strings available in the database
    """
    try:
        import sqlite3
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        cursor = conn.execute("""
            SELECT DISTINCT format 
            FROM tournaments 
            WHERE format IS NOT NULL 
            ORDER BY format
        """)
        
        formats = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return formats
        
    except Exception as e:
        print(f"Error getting available formats: {e}")
        return ['Standard']  # Fallback

def create_enhanced_meta_trend_chart(deck_name, selected_formats=None):
    """
    Create enhanced line chart with set markers, tier zones, and format filtering
    Modified to show last 30 days instead of from set release
    """
    import sqlite3
    import pandas as pd
    import plotly.graph_objects as go
    
    if selected_formats is None:
        selected_formats = ['Standard']
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        # Create format filter for SQL query
        format_placeholders = ','.join(['?' for _ in selected_formats])
        
        # Calculate cutoff date for last 30 days (replace the set release logic)
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Query to get daily data for the specific archetype and selected formats in last 30 days
        query = f"""
        SELECT 
            t.date,
            t.format,
            COALESCE(SUM(aa.count), 0) as archetype_players,
            SUM(t.total_players) as total_players
        FROM tournaments t
        LEFT JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id 
            AND aa.archetype = ?
        WHERE t.format IN ({format_placeholders})
        AND t.date >= ?
        GROUP BY t.date, t.format
        HAVING total_players > 0
        ORDER BY t.date
        """
        
        # Execute query with deck name, selected formats, and 30-day cutoff
        query_params = [deck_name] + selected_formats + [cutoff_date]
        df = pd.read_sql_query(query, conn, params=query_params)
        conn.close()
        
        # Rest of the function remains the same...
        # (continue with the existing logic for data processing and chart creation)
        
        if df.empty:
            print(f"No data found for archetype: {deck_name} in formats: {selected_formats}")
            return None
        
        # Calculate percentage for each date
        df['meta_percentage'] = (df['archetype_players'] / df['total_players']) * 100
        
        # Convert date strings to datetime for better plotting
        df['date'] = pd.to_datetime(df['date'])
        
        # Aggregate by date (sum across all selected formats for each date)
        df_aggregated = df.groupby('date').agg({
            'archetype_players': 'sum',
            'total_players': 'sum',
            'meta_percentage': 'mean'  # Average percentage across formats
        }).reset_index()
        
        # Recalculate percentage after aggregation
        df_aggregated['meta_percentage'] = (df_aggregated['archetype_players'] / df_aggregated['total_players']) * 100
        
        # Filter out dates where archetype had 0%
        df_filtered = df_aggregated[df_aggregated['meta_percentage'] > 0].copy()
        
        if df_filtered.empty:
            print(f"No appearances found for archetype: {deck_name} in formats: {selected_formats}")
            return None
        
        # Create the figure
        fig = go.Figure()
        
        # Add set release markers
        set_releases = get_set_release_dates()
        for release_date, set_name in set_releases:
            if pd.to_datetime(release_date) >= df_filtered['date'].min() and pd.to_datetime(release_date) <= df_filtered['date'].max():
                fig.add_vline(
                    x=release_date, 
                    line_dash="dot", 
                    line_color="rgba(0, 0, 0, 0.5)",
                    annotation_text=f"Set: {set_name}",
                    annotation_position="top"
                )
        
        # Add the main trend line
        fig.add_trace(go.Scatter(
            x=df_filtered['date'],
            y=df_filtered['meta_percentage'],
            mode='lines+markers',
            name='Meta Share %',
            line=dict(color='#00A0FF', width=2),
            marker=dict(size=8, color='#00A0FF'),
            hovertemplate='<b>%{x}</b><br>Meta Share: %{y:.1f}%<br>Players: %{customdata[0]}<br>Total: %{customdata[1]}<extra></extra>',
            customdata=list(zip(df_filtered['archetype_players'], df_filtered['total_players']))
        ))
        
        # Add peak annotation
        peak_idx = df_filtered['meta_percentage'].idxmax()
        peak_date = df_filtered.loc[peak_idx, 'date']
        peak_value = df_filtered.loc[peak_idx, 'meta_percentage']
        
        fig.add_annotation(
            x=peak_date,
            y=peak_value + (df_filtered['meta_percentage'].max() * 0.05),
            text=f"Peak: {peak_value:.1f}% share",
            showarrow=False,
            font=dict(size=12),
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="rgba(0,0,0,0)"
        )

        fig.add_annotation(
            x=0.5,  # Center horizontally
            y=-0.15,  # Position below the plot
            xref='paper',  # Use paper coordinates (0-1)
            yref='paper',
            text="Shows daily meta share percentage based on tournament data. Vertical dashed lines indicate set releases. Peak value is highlighted on the chart.",
            showarrow=False,
            font=dict(color="rgb(163, 168, 184)", size=11),
            align="center",
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)"
        )
        
        # Update layout
        fig.update_layout(
            #title=f"Meta Evolution",
            xaxis_title=None,  # Removed "Date" title
            yaxis_title=None,
            height=400,
            margin=dict(t=0, l=0, r=0, b=0),
            hovermode='x unified',
            
            # Styling to match your app
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            
            # Grid and axes styling
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.15)',
                showline=True,
                linecolor='rgba(128,128,128,0.3)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.15)',
                showline=True,
                linecolor='rgba(128,128,128,0.3)',
                range=[0, df_filtered['meta_percentage'].max() * 1.1]  # Dynamic range
            )
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating enhanced meta trend chart: {e}")
        return None

def get_set_release_dates():
    """
    Load set release dates from the sets index file
    
    Returns:
        List of tuples: [(release_date, set_code, set_name), ...]
    """
    with open("meta_analysis/sets_index.json", 'r') as f:
        sets_data = json.load(f)
    
    releases = []
    for set_info in sets_data['sets']:
        if set_info['release_date']:
            releases.append((
                set_info['release_date'],
                set_info['set_code'], 
                set_info['set_name']
            ))
    
    return sorted(releases)

def get_deck_available_formats(deck_name):
    """
    Get list of formats where this specific deck has appeared
    
    Args:
        deck_name: The deck archetype name
        
    Returns:
        List of format strings where this deck has appeared
    """
    try:
        import sqlite3
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        cursor = conn.execute("""
            SELECT DISTINCT t.format 
            FROM tournaments t
            JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id
            WHERE aa.archetype = ? AND t.format IS NOT NULL
            ORDER BY t.format
        """, (deck_name,))
        
        formats = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return formats
        
    except Exception as e:
        print(f"Error getting deck available formats: {e}")
        return ['Standard']  # Fallback

def get_latest_set_release_date():
    """
    Get the latest set release date from the sets index file
    
    Returns:
        str: ISO date string of latest release or None
    """
    try:
        with open("meta_analysis/sets_index.json", 'r') as f:
            sets_data = json.load(f)
        
        # Filter sets with release dates and sort by date (newest first)
        sets_with_dates = [s for s in sets_data['sets'] if s.get('release_date')]
        if sets_with_dates:
            latest_set = sorted(sets_with_dates, key=lambda x: x['release_date'], reverse=True)[0]
            return latest_set['release_date']
            
    except Exception as e:
        print(f"Error getting latest set release date: {e}")
    
    return None

def create_enhanced_meta_trend_chart_combined(deck_name, selected_formats=None, chart_subtitle=""):
    """
    Create enhanced line chart that combines formats into a single line
    """
    import sqlite3
    import pandas as pd
    import plotly.graph_objects as go
    
    if selected_formats is None:
        selected_formats = ['Standard']
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        # Create format filter for SQL query
        format_placeholders = ','.join(['?' for _ in selected_formats])
        
        # Calculate cutoff date for last 30 days
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Add date filter for last 30 days
        date_filter = "AND t.date >= ?"
        query_params = [deck_name] + selected_formats + [cutoff_date]
        
        # Query to get daily data for the specific archetype and selected formats
        query = f"""
        SELECT 
            t.date,
            t.format,
            COALESCE(SUM(aa.count), 0) as archetype_players,
            SUM(t.total_players) as total_players
        FROM tournaments t
        LEFT JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id 
            AND aa.archetype = ?
        WHERE t.format IN ({format_placeholders}) {date_filter}
        GROUP BY t.date, t.format
        HAVING total_players > 0
        ORDER BY t.date
        """
        
        # Execute query
        df = pd.read_sql_query(query, conn, params=query_params)
        conn.close()
        
        if df.empty:
            print(f"No data found for archetype: {deck_name} in formats: {selected_formats} since {latest_release}")
            return None
        
        # Calculate percentage for each date/format combination
        df['meta_percentage'] = (df['archetype_players'] / df['total_players']) * 100
        
        # Convert date strings to datetime for better plotting
        df['date'] = pd.to_datetime(df['date'])
        
        # Combine all formats for each date (aggregate by date)
        df_combined = df.groupby('date').agg({
            'archetype_players': 'sum',
            'total_players': 'sum'
        }).reset_index()
        
        # Recalculate percentage after combining formats
        df_combined['meta_percentage'] = (df_combined['archetype_players'] / df_combined['total_players']) * 100
        
        # Filter out dates where archetype had 0%
        df_filtered = df_combined[df_combined['meta_percentage'] > 0].copy()
        
        if df_filtered.empty:
            print(f"No appearances found for archetype: {deck_name} in formats: {selected_formats} since {latest_release}")
            return None
        
        # Create the figure
        fig = go.Figure()

        # Define color zones (every 2% with alpha 0.2)
        color_zones = [
            {"range": [0, 2], "color": "rgba(231, 208, 2, 1)"},    # FDE725
            {"range": [2, 4], "color": "rgba(150, 217, 34, 1)"},   # 9FDA3A
            {"range": [4, 6], "color": "rgba(62, 199, 103, 1)"},   # 49C16D
            {"range": [6, 8], "color": "rgba(32, 160, 135, 1)"},   # 20A087
            {"range": [8, 10], "color": "rgba(39, 127, 142, 1)"},  # 277F8E
            {"range": [10, 12], "color": "rgba(55, 91, 141, 1)"},  # 375B8D
            {"range": [12, 14], "color": "rgba(70, 51, 127, 1)"},  # 46337F
            {"range": [14, 16], "color": "rgba(69, 15, 84, 1)"},  # 450F54
            {"range": [16, 18], "color": "rgba(39, 0, 44, 1)"},  # 450F54
            {"range": [18, 100], "color": "rgba(9, 0, 4, 1)"},  # 450F54
        ]
        
        # Add background color zones
        for zone in color_zones:
            fig.add_hrect(
                y0=zone["range"][0], 
                y1=zone["range"][1],
                fillcolor=zone["color"],
                line_width=0,
                layer="below"
            )
            
        # Add set release markers with improved annotations
        set_releases = get_set_release_dates()
        min_date = df_filtered['date'].min()
        max_date = df_filtered['date'].max()
        max_percentage = df_filtered['meta_percentage'].max()
        
        for release_date, set_code, set_name in set_releases:
            release_dt = pd.to_datetime(release_date)
            if release_dt >= min_date and release_dt <= max_date:
                # Add vertical line
                fig.add_vline(
                    x=release_date, 
                    line_dash="dot", 
                    line_color="rgba(255, 255, 255, 0.6)",
                    line_width=1
                )
                
                # Add set code annotation at the top with hover info
                fig.add_annotation(
                    x=release_date,
                    y=max_percentage * 1.1,  # Position at top of chart
                    text=set_code,  # Add space at beginning
                    showarrow=False,
                    font=dict(size=10, color="#FFFFFF"),
                    align="left",
                    xshift=12,
                    hovertext=f"Set Release: {set_name}<br>Date: {release_date}",
                    hoverlabel=dict(
                        bgcolor="white",
                        bordercolor="gray",
                        font=dict(color="black")
                    )
                )
        
        # Add the main trend line
        fig.add_trace(go.Scatter(
            x=df_filtered['date'],
            y=df_filtered['meta_percentage'],
            mode='lines+markers',
            name='Meta Share %',
            line=dict(color='#FFFFFF', width=1),
            marker=dict(size=8, color='#FFFFFF'),
            hovertemplate='<b>%{x}</b><br>Meta Share: %{y:.1f}%<br>Players: %{customdata[0]}<br>Total: %{customdata[1]}<extra></extra>',
            customdata=list(zip(df_filtered['archetype_players'], df_filtered['total_players']))
        ))
        
        # Add peak annotation
        peak_idx = df_filtered['meta_percentage'].idxmax()
        peak_date = df_filtered.loc[peak_idx, 'date']
        peak_value = df_filtered.loc[peak_idx, 'meta_percentage']
        
        fig.add_annotation(
            x=peak_date,
            y=peak_value + (df_filtered['meta_percentage'].max() * 0.05),
            text=f"Peak: {peak_value:.1f}% share",
            showarrow=False,
            font=dict(size=12, color="#FFFFFF")
        )
        
        # Update layout
        fig.update_layout(
            #title=f"Meta Evolution: {deck_name.replace('-', ' ').title()}{chart_subtitle}",
            xaxis_title=None,
            yaxis_title=None,
            height=400,
            margin=dict(t=0, l=0, r=0, b=0),
            hovermode='x unified',
            
            # Styling to match your app
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            showlegend=False,
            
            # Grid and axes styling
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.15)',
                showline=True,
                linecolor='rgba(128,128,128,0.3)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.15)',
                showline=True,
                linecolor='rgba(128,128,128,0.3)',
                range=[0, df_filtered['meta_percentage'].max() * 1.15],
                tickmode='linear',
                tick0=0,
                dtick=2,
                ticksuffix='%'
            )
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating enhanced meta trend chart: {e}")
        return None

def create_performance_trend_chart(deck_name, selected_formats=None):
    """
    Create performance trend chart showing win percentage over time with background color zones
    Fixed to properly aggregate multiple formats per date
    """
    import sqlite3
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime, timedelta
    
    if selected_formats is None:
        selected_formats = ['Standard']
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        # Create format filter for SQL query
        format_placeholders = ','.join(['?' for _ in selected_formats])
        
        # Calculate cutoff date for last 30 days (if you want 30-day filter)
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Query to get daily performance data - GROUP BY date only, not format
        query = f"""
        SELECT 
            t.date,
            SUM(pp.wins) as total_wins,
            SUM(pp.losses) as total_losses,
            SUM(pp.ties) as total_ties,
            COUNT(pp.player_name) as total_players
        FROM tournaments t
        JOIN player_performance pp ON t.tournament_id = pp.tournament_id
        WHERE pp.archetype = ?
        AND t.format IN ({format_placeholders})
        AND t.date >= ?
        GROUP BY t.date
        ORDER BY t.date
        """
        
        # Execute query with parameters
        params = [deck_name] + selected_formats + [cutoff_date]
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            return None
        
        # Calculate win percentage and total games
        df['total_games'] = df['total_wins'] + df['total_losses'] + df['total_ties']
        df['win_percentage'] = (df['total_wins'] / df['total_games'] * 100).round(1)
        
        # Filter out days with too few games for reliability
        df_filtered = df[df['total_games'] >= 3].copy()
        
        if df_filtered.empty:
            return None
        
        # Create conditional marker colors based on win percentage
        marker_colors = []
        for win_rate in df_filtered['win_percentage']:
            if win_rate > 50:
                marker_colors.append('forestgreen')  # Light green for >50%
            else:
                marker_colors.append('tomato')  # Light red for <50%
        
        # Create the figure
        fig = go.Figure()
        
        # Set up y-axis range
        y_min = max(0, df_filtered['win_percentage'].min() - 5)
        y_max = min(100, df_filtered['win_percentage'].max() + 5)
        
        # Add 50% reference line
        fig.add_hline(
            y=50,
            line_dash="dot",
            line_color="rgba(255, 255, 255, 1)",
            line_width=1.5
        )
        
        # Add performance zone backgrounds
        color_zones = [
            {"range": [0, 10], "color": "rgba(165, 0, 38, 1)"},     # 0-10%
            {"range": [10, 20], "color": "rgba(215, 48, 39, 1)"},    # 10-20%
            {"range": [20, 30], "color": "rgba(244, 109, 67, 1)"},   # 20-30%
            {"range": [30, 40], "color": "rgba(255, 166, 79, 1)"},   # 30-40%
            {"range": [40, 50], "color": "rgba(255, 209, 79, 1)"},   # 40-50%
            {"range": [50, 60], "color": "rgba(184, 219, 59, 1)"},   # 50-60%
            {"range": [60, 70], "color": "rgba(135, 209, 47, 1)"},   # 60-70%
            {"range": [70, 80], "color": "rgba(83, 186, 79, 1)"},    # 70-80%
            {"range": [80, 90], "color": "rgba(26, 152, 80, 1)"},    # 80-90%
            {"range": [90, 100], "color": "rgba(0, 104, 55, 1)"},    # 90-100%
        ]
        
        # Add background color zones
        for zone in color_zones:
            # Only add zones that intersect with our y-axis range
            if zone["range"][1] > y_min and zone["range"][0] < y_max:
                fig.add_hrect(
                    y0=max(zone["range"][0], y_min),
                    y1=min(zone["range"][1], y_max),
                    fillcolor=zone["color"],
                    line_width=0,
                    layer="below"
                )
        
        # Add win percentage line with conditional marker colors and white outline
        fig.add_trace(go.Scatter(
            x=df_filtered['date'],
            y=df_filtered['win_percentage'],
            mode='lines+markers',
            name='Win %',
            line=dict(color='#FFFFFF', width=1),  # White line, width 1
            marker=dict(
                size=8, 
                color=marker_colors,  # Conditional colors (light green/red)
                line=dict(color='white', width=2)  # White outline, 2px width
            ),
            hovertemplate='<b>%{x}</b><br>Win Rate: %{y:.1f}%<br>Wins: %{customdata[0]}<br>Losses: %{customdata[1]}<br>Total Games: %{customdata[2]}<extra></extra>',
            customdata=list(zip(df_filtered['total_wins'], df_filtered['total_losses'], df_filtered['total_games']))
        ))

        # # Add set release markers with improved annotations
        # set_releases = get_set_release_dates()
        # min_date = df_filtered['date'].min()
        # max_date = df_filtered['date'].max()
        # max_percentage = df_filtered['meta_percentage'].max()
        
        # for release_date, set_code, set_name in set_releases:
        #     release_dt = pd.to_datetime(release_date)
        #     if release_dt >= min_date and release_dt <= max_date:
        #         # Add vertical line
        #         fig.add_vline(
        #             x=release_date, 
        #             line_dash="dot", 
        #             line_color="rgba(255, 255, 255, 0.6)",
        #             line_width=1
        #         )
                
        #         # Add set code annotation at the top with hover info
        #         fig.add_annotation(
        #             x=release_date,
        #             y=max_percentage * 1.1,  # Position at top of chart
        #             text=set_code,  # Add space at beginning
        #             showarrow=False,
        #             font=dict(size=10, color="#FFFFFF"),
        #             align="left",
        #             xshift=12,
        #             hovertext=f"Set Release: {set_name}<br>Date: {release_date}",
        #             hoverlabel=dict(
        #                 bgcolor="white",
        #                 bordercolor="gray",
        #                 font=dict(color="black")
        #             )
        #         )
                
        # Add peak annotation in white
        peak_idx = df_filtered['win_percentage'].idxmax()
        peak_date = df_filtered.loc[peak_idx, 'date']
        peak_value = df_filtered.loc[peak_idx, 'win_percentage']
        
        fig.add_annotation(
            x=peak_date,
            y=peak_value + (y_max - y_min) * 0.05,
            text=f"Peak: {peak_value:.1f}% win rate",
            showarrow=False,
            font=dict(size=12, color="#FFFFFF")  # White annotation
        )
        
        # Update layout
        fig.update_layout(
            #title=f"Performance Trend",
            xaxis_title=None,
            yaxis_title=None,  # Remove y-axis title
            height=400,
            margin=dict(t=0, l=0, r=0, b=0),
            hovermode='x unified',
            
            # Styling to match meta evolution chart
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            showlegend=False,
            
            # Grid and axes styling
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.15)',
                showline=True,
                linecolor='rgba(128,128,128,0.3)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.15)',
                showline=True,
                linecolor='rgba(128,128,128,0.3)',
                range=[y_min, y_max],
                tickmode='linear',
                tick0=0,
                dtick=10,  # Show ticks every 10%
                ticksuffix='%'  # Add percentage format like meta evolution chart
            )
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creating performance trend chart: {e}")
        return None
