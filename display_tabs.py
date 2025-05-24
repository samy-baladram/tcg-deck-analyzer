# display_tabs.py
"""Functions for rendering the tabs in the main content area"""

import streamlit as st
from formatters import format_deck_name, extract_pokemon_urls
from related_decks import find_related_decks
from image_processor import create_deck_header_images
from visualizations import create_usage_bar_chart, display_chart, create_variant_bar_chart, ENERGY_COLORS
from analyzer import build_deck_template
from card_renderer import render_deck_section, render_option_section
from energy_utils import get_archetype_from_deck_name, render_energy_icons
from config import TOURNAMENT_COUNT, POWER_INDEX_EXPLANATION, POKEMON_EXCEPTIONS, MIN_MATCHUP_MATCHES
from header_image_cache import get_header_image_cached
import pandas as pd
import base64
import os

def display_deck_header(deck_info, results):
    """Display the deck header with image and text that wraps properly"""
    header_image = get_header_image_cached(
        deck_info['deck_name'], 
        deck_info.get('set', 'A3'),
        results
    )
    
    # Check if this is the first time showing a deck header
    if 'first_deck_header_shown' not in st.session_state:
        st.session_state.first_deck_header_shown = True
        show_landing_message = True
    else:
        show_landing_message = False
    
    # Load and encode the featured image if it exists and we want to show it
    featured_image_base64 = None
    if show_landing_message:
        featured_image_path = "featured_banner.png"
        if os.path.exists(featured_image_path):
            with open(featured_image_path, "rb") as f:
                featured_image_base64 = base64.b64encode(f.read()).decode()
    
    if header_image:
        # Conditional max-width for deck header image
        deck_image_max_width = "800px" if show_landing_message and featured_image_base64 else "500px"
        
        # Simplified centered layout
        header_content = f"""
        <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@1,900&display=swap" rel="stylesheet">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 0rem; margin: 0.5rem 0 0.5rem 0; text-align: center;">
            <div>
                <img src="data:image/png;base64,{header_image}" style="max-width: {deck_image_max_width}; width: 100%; height: auto; border: 3px solid #57585F;border-radius: 10px;">
            </div>
            <div style="min-width: 200px; margin-left: 1rem;">"""
        
        # Add featured image if this is the first time and image exists
        if show_landing_message and featured_image_base64:
            header_content += f"""
                <div style="margin-top: 0.5rem; margin-bottom: -1rem;">
                    <img src="data:image/png;base64,{featured_image_base64}" style="max-width: 100%; max-height: 60px; border-radius: 10px;">
                </div>"""
        
        # Add the deck name
        header_content += f"""
                <h1 style="margin: 0; font-family: 'Nunito', sans-serif; font-weight: 900; font-style: italic; line-height: 1; word-wrap: break-word;">{format_deck_name(deck_info['deck_name'])}</h1>
            </div>
        </div>"""
        
        st.markdown(header_content, unsafe_allow_html=True)
        
    else:
        # No header image case
        st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@1,900&display=swap" rel="stylesheet">
        """, unsafe_allow_html=True)
        
        # Build content for no-image case
        if show_landing_message and featured_image_base64:
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 1rem;">
                <img src="data:image/png;base64,{featured_image_base64}" style="max-width: 100%; height: auto; max-height: 100px; border-radius: 10px;">
            </div>
            <h1 style="text-align: center; font-family: 'Nunito', sans-serif; font-weight: 900; font-style: italic; letter-spacing: -1px; line-height: 1.2; word-wrap: break-word;">{format_deck_name(deck_info['deck_name'])}</h1>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""<h1 style="text-align: center; font-family: 'Nunito', sans-serif; font-weight: 900; font-style: italic; letter-spacing: -1px; line-height: 1.2; word-wrap: break-word;">{format_deck_name(deck_info['deck_name'])}</h1>""", unsafe_allow_html=True)
            
# def display_deck_header(deck_info, results):
#     """Display the deck header with image and text that wraps properly"""
#     header_image = create_deck_header_images(deck_info, results)
    
#     # Check if this is the first time showing a deck header
#     if 'first_deck_header_shown' not in st.session_state:
#         st.session_state.first_deck_header_shown = True
#         show_landing_message = True
#     else:
#         show_landing_message = False
    
#     # Load and encode the featured image if it exists and we want to show it
#     featured_image_base64 = None
#     if show_landing_message:
#         featured_image_path = "featured_banner.png"
#         if os.path.exists(featured_image_path):
#             with open(featured_image_path, "rb") as f:
#                 featured_image_base64 = base64.b64encode(f.read()).decode()
    
#     if header_image:
#         # Build the header content with conditional featured image
#         header_content = f"""
#         <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@1,900&display=swap" rel="stylesheet">
#         <div style="display: flex; flex-wrap: wrap; align-items: center; margin-bottom: 1em; margin-top:0.25rem">
#             <div style="margin-right: 0rem; margin-left:0rem; margin-bottom: -1rem;">
#                 <img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 350px; height: auto; border-radius: 10px;">
#             </div>"""
        
#         # Conditional styling based on whether featured image is showing
#         if show_landing_message and featured_image_base64:
#             header_content = f"""
#             <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@1,900&display=swap" rel="stylesheet">
#             <div style="display: flex; flex-wrap: wrap; align-items: center; margin-bottom: 1em; margin-top:0rem">
#                 <div style="margin-right: 0rem; margin-left:0rem; margin-bottom: -1rem;">
#                     <img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 450px; height: auto; border-radius: 10px;">
#                 </div>"""
#             # When featured image is present, push content down
#             header_content += f"""
#             <div style="flex: 1; min-width: 200px; margin-left: 0.2rem; margin-right: 0.2rem;  align-self: flex-end; padding-bottom: 20px;">"""
#         else:
#             # When no featured image, keep normal centering
#             header_content += f"""
#             <div style="flex: 1; min-width: 200px; margin-left: 0.2rem; margin-right: 0.2rem; margin-top:1rem; margin-bottom:0.5rem;">"""
        
#         # Add featured image if this is the first time and image exists
#         if show_landing_message and featured_image_base64:
#             header_content += f"""
#                 <div style="margin-bottom: -1rem; text-align: center; margin-top: 1.5rem;">
#                     <img src="data:image/png;base64,{featured_image_base64}" style="max-width: 100%; width: auto; max-height: 60px; border-radius: 10px;">
#                 </div>"""
        
#         # Add the deck name
#         header_content += f"""
#                 <h1 style="margin-bottom:-1rem; margin-top:-0.5rem; text-align: center; font-family: 'Nunito', sans-serif; font-weight: 900; font-style: italic; line-height: 1; word-wrap: break-word;">{format_deck_name(deck_info['deck_name'])}</h1>
#             </div>
#         </div>"""
        
#         st.markdown(header_content, unsafe_allow_html=True)
        
#     else:
#         # No header image case
#         st.markdown("""
#         <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@1,900&display=swap" rel="stylesheet">
#         """, unsafe_allow_html=True)
        
#         # Build content for no-image case
#         if show_landing_message and featured_image_base64:
#             st.markdown(f"""
#             <div style="text-align: center; margin-bottom: 1rem;">
#                 <img src="data:image/png;base64,{featured_image_base64}" style="max-width: 100%; height: auto; max-height: 100px; border-radius: 10px;">
#             </div>
#             <h1 style="font-family: 'Nunito', sans-serif; font-weight: 900; font-style: italic; letter-spacing: -1px; line-height: 1.2; word-wrap: break-word;">{format_deck_name(deck_info['deck_name'])}</h1>
#             """, unsafe_allow_html=True)
#         else:
#             st.markdown(f"""<h1 style="font-family: 'Nunito', sans-serif; font-weight: 900; font-style: italic; letter-spacing: -1px; line-height: 1.2; word-wrap: break-word;">{format_deck_name(deck_info['deck_name'])}</h1>""", unsafe_allow_html=True)            

# In display_card_usage_tab function in display_tabs.py
def display_card_usage_tab(results, total_decks, variant_df):
    """Display the Card Usage tab with energy-colored charts based on deck energy types"""
    # Create two columns for Pokemon and Trainer
    st.write("#### Card Usage & Variants")
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
        st.write("##### Pokemon")
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
        st.write("##### Trainer")
        type_cards = results[results['type'] == 'Trainer']
        
        if not type_cards.empty:
            # Keep default colors for trainers
            fig = create_usage_bar_chart(type_cards, 'Trainer')
            display_chart(fig, key="usage_trainer_chart")
        else:
            st.info("No Trainer cards found")

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

# def display_variant_decks(deck_info, energy_types, is_typical, options):
#     """Display the main sample deck and any variant decks containing other Pokémon options"""
#     # Check if options is empty or None
#     if options is None or options.empty:
#         st.write("#### Sample Deck")
#         render_sample_deck(energy_types, is_typical)
#         return
    
#     # Get Pokemon options that have different names from core Pokemon
#     pokemon_options = options[options['type'] == 'Pokemon'].copy()
    
#     # If no Pokemon options, just show the sample deck
#     if pokemon_options.empty:
#         st.write("#### Sample Deck")
#         render_sample_deck(energy_types, is_typical)
#         return
    
#     # Get core Pokemon names for comparison
#     core_pokemon_names = set()
#     for card in deck_info.get('Pokemon', []):
#         core_pokemon_names.add(card.get('name', '').lower())
    
#     # Filter options to only include Pokemon with different names
#     different_pokemon = pokemon_options[~pokemon_options['card_name'].str.lower().isin(core_pokemon_names)]
    
#     # If no different Pokemon in options, just show the standard sample deck
#     if different_pokemon.empty:
#         st.write("#### Sample Deck")
#         render_sample_deck(energy_types, is_typical)
#         return
    
#     # Get the variant Pokémon names
#     variant_pokemon_names = set(different_pokemon['card_name'].str.lower())
    
#     # Ensure we have deck collection data before proceeding
#     if 'analyze' in st.session_state:
#         deck_name = st.session_state.analyze.get('deck_name', '')
#         set_name = st.session_state.analyze.get('set_name', '')
#         ensure_deck_collection_data(deck_name, set_name)
    
#     # Display the original sample deck (without variants) in an expander
#     with st.expander("Sample Deck", expanded=True):
#         render_clean_sample_deck(variant_pokemon_names, energy_types, is_typical)
    
#     # Track decks we've already shown to avoid duplicates
#     shown_deck_nums = set()
    
#     # Limit the variants to show (to avoid overwhelming UI)
#     max_variants = 5  # Show at most 5 variants
    
#     # For each different Pokemon, show a variant deck in an expander
#     for idx, (_, pokemon) in enumerate(different_pokemon.iterrows()):
#         if idx >= max_variants:
#             break
            
#         pokemon_name = pokemon['card_name']
#         set_code = pokemon.get('set', '')
#         num = pokemon.get('num', '')
        
#         # Create a formatted title with set and number info
#         variant_title = f"{pokemon_name} ({set_code}-{num}) Variant" if set_code and num else f"{pokemon_name} Variant"
        
#         with st.expander(variant_title, expanded=False):
#             # Create a set of Pokémon to avoid (other variants)
#             other_variants = set(name for name in variant_pokemon_names if name.lower() != pokemon_name.lower())
            
#             # Render a deck with this Pokémon but preferably without other variants
#             deck_num = render_optimal_variant_deck(pokemon, other_variants, shown_deck_nums, energy_types, is_typical)
            
#             # If we found a deck, add it to the shown list
#             if deck_num is not None:
#                 shown_deck_nums.add(deck_num)
def display_variant_decks(deck_info, energy_types, is_typical, options):
    """Display the main sample deck and any variant decks containing other Pokémon options"""
    # Check if options is empty or None
    if options is None or options.empty:
        st.write("#### Sample Deck")
        render_sample_deck(energy_types, is_typical)
        return
    
    # Get Pokemon options that have different names from core Pokemon
    pokemon_options = options[options['type'] == 'Pokemon'].copy()
    
    # If no Pokemon options, just show the sample deck
    if pokemon_options.empty:
        st.write("#### Sample Deck")
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
        st.write("#### Sample Deck")
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
    with st.expander("Sample Deck", expanded=True):
        render_clean_sample_deck(variant_pokemon_names, energy_types, is_typical)
    
    # Track decks we've already shown to avoid duplicates
    shown_deck_nums = set()
    
    # Track exact Pokemon names already shown to avoid duplicates
    shown_pokemon_names = set()
    
    # Limit the variants to show (to avoid overwhelming UI)
    max_variants = 5  # Show at most 5 variants
    variants_shown = 0  # Counter for actual variants shown
    
    # For each different Pokemon, show a variant deck in an expander
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
        
        # Create a formatted title with set and number info
        variant_title = f"{pokemon_name} ({set_code}-{num}) Variant" if set_code and num else f"{pokemon_name} Variant"
        
        with st.expander(variant_title, expanded=False):
            # Create a set of Pokemon to avoid (other variants)
            other_variants = set(name for name in variant_pokemon_names if name.lower() != pokemon_name.lower())
            
            # Render a deck with this Pokemon but preferably without other variants
            deck_num = render_optimal_variant_deck(pokemon, other_variants, shown_deck_nums, energy_types, is_typical)
            
            # Only track and increment if deck was actually found
            if deck_num is not None:
                shown_deck_nums.add(deck_num)
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
    
def render_optimal_variant_deck(variant_pokemon, other_variants, shown_deck_nums, energy_types, is_typical):
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
            card_width=70
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
        card_width=70
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
            card_width=70
        )
        st.markdown(deck_html, unsafe_allow_html=True)
    else:
        st.info("No sample deck available")


def display_deck_composition(deck_info, energy_types, is_typical, total_cards, options, variant_df=None):
    """Display the deck composition section"""
    # Create header
    st.write("#### Deck Composition", unsafe_allow_html=True)
    if energy_types:
        # Render energy icons for header
        energy_html = ""
        for energy in energy_types:
            energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
            energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:20px; margin-right:4px; vertical-align:middle;">'
        
        # Create header with energy types
        archetype_note = '<span style="font-size: 0.8rem; color: #888; margin-left: 4px;">(most common)</span>' if is_typical else ""
        core_cards_header = f"""##### Meta Essentials ({total_cards} Cards)""" + f"""<span style="font-size: 1rem; font-weight: normal;">&emsp; Energy: {energy_html}{archetype_note}</span>"""
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
        st.write("###### Pokémon")
        pokemon_grid = CardGrid(card_width=65, gap=4)
        pokemon_grid.add_cards_from_dict(deck_info['Pokemon'], repeat_by_count=True)
        pokemon_grid.display()
    
    with core_col2:
        # Trainer cards section
        st.write("###### Trainer")
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
                st.write("###### Pokémon Options")
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
                st.write("###### Trainer Options")
                trainer_options_grid = CardGrid(card_width=65, gap=4, show_percentage=True)
                trainer_options_grid.add_cards_from_dataframe(trainer_options)
                trainer_options_grid.display()
        st.caption("Percentages show how often each card appears in top competitive decks. Higher values indicate more popular choices for your remaining slots.")
    else:
        st.info("No remaining slots available for this deck.")
        
def display_raw_data_tab(results, variant_df):
    """Display the Raw Data tab"""
    # Main analysis data
    st.write("#### Card Usage Data")
    st.dataframe(results, use_container_width=True)
    
    # Variant analysis data
    if not variant_df.empty:
        st.write("#### Variant Analysis Data")
        st.dataframe(variant_df, use_container_width=True)

def display_metagame_tab():
    """Display the Metagame Overview tab with detailed performance data"""
    st.write("#### Tournament Performance Data")
    import pandas as pd
    import re
    
    # Get performance data
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
    display_df['win_rate'] = round((display_df['total_wins'] / (display_df['total_wins'] + display_df['total_losses'] + display_df['total_ties'])) * 100, 1)
    
    # Format numerical columns
    display_df['share'] = display_df['share'].round(2)
    display_df['power_index'] = display_df['power_index'].round(2)

    # Extract Pokémon names and create image URLs
    display_df[['pokemon_url1', 'pokemon_url2']] = display_df.apply(
        lambda row: pd.Series(extract_pokemon_urls(row['deck_name'])), 
        axis=1
    )
    
    # Select and rename columns for display - FIX: Use rank_display
    display_cols = {
        'rank_display': 'Rank',  # Changed from 'rank'
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
            "Rank": st.column_config.TextColumn(  # FIX: Change to TextColumn
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
    
    # Add a small footnote about data source instead of the full explanation
    from datetime import datetime
    current_month_year = datetime.now().strftime("%B %Y")
    st.caption(f"Data based on up to {TOURNAMENT_COUNT} most recent community tournaments in {current_month_year} on Limitless TCG.")
    
    
def display_matchup_treemap(deck_name, set_name, working_df):
    """
    Display a treemap showing matchup distribution against the meta
    
    Args:
        deck_name: Current deck name
        set_name: Current deck set
        working_df: DataFrame with matchup data already processed
    """
    #st.write("#### Meta Matchup Distribution")
    
    # Check if we have matchup data with meta share
    if working_df.empty or 'meta_share' not in working_df.columns:
        st.info("No matchup data with meta share available.")
        return
    
    # Prepare data for treemap
    treemap_data = working_df.copy()

    # ADDED: Sort by win rate (color) first, then by meta share for secondary ordering
    treemap_data = treemap_data.sort_values(['win_pct', 'meta_share'], ascending=[False, False])
   
    # Clean opponent names for better display
    treemap_data['clean_name'] = treemap_data['opponent_name'].apply(
        lambda x: x.replace(' (', '<br>(') if len(x) > 15 else x
    )
    
    # Create hover text
    treemap_data['hover_text'] = treemap_data.apply(
        lambda row: f"<b>{row['opponent_name']}</b><br>" +
                   f"Win Rate: {row['win_pct']:.1f}%<br>" +
                   f"Record: {row['wins']}-{row['losses']}-{row['ties']}<br>" +
                   f"Meta Share: {row['meta_share']:.1f}%<br>" +
                   f"Matches: {row['matches_played']}",
        axis=1
    )
    
    # Create text for display on rectangles
    treemap_data['display_text'] = treemap_data.apply(
        lambda row: f"{row['clean_name']}<br>{row['win_pct']:.0f}%<br>({row['meta_share']:.1f}%)",
        axis=1
    )
    
    # Create the treemap
    import plotly.graph_objects as go
    
    fig = go.Figure(go.Treemap(
        labels=treemap_data['clean_name'],
        values=treemap_data['meta_share'],
        parents=[""] * len(treemap_data),  # All top-level rectangles
        
        # Color by win rate with custom colorscale - FIXED: use 'colors' not 'color'
        marker_colors=treemap_data['win_pct'],
        marker_colorscale=[
            [0.0, "rgb(220, 53, 69)"],     # Red (0% win)
            [0.1, "rgb(253, 126, 20)"],    # Red-Orange (10% win)
            [0.2, "rgb(255, 152, 0)"],     # Orange (20% win)
            [0.3, "rgb(255, 183, 77)"],    # Light Orange (30% win)
            [0.4, "rgb(255, 235, 59)"],    # Yellow (40% win)
            [0.5, "rgb(205, 220, 57)"],    # Yellow-Green (50% win)
            [0.6, "rgb(156, 204, 101)"],   # Light Green (60% win)
            [0.7, "rgb(139, 195, 74)"],    # Medium Green (70% win)
            [0.8, "rgb(102, 187, 106)"],   # Green (80% win)
            [0.9, "rgb(76, 175, 80)"],     # Dark Green (90% win)
            [1.0, "rgb(27, 94, 32)"]       # Very Dark Green (100% win)
        ],
        marker_cmid=50,  # Center colorscale at 50% win rate
        marker_colorbar=dict(
            title="Win Rate %",
            thickness=15,
            len=0.7,
            x=1.02
        ),
        
        # Text display
        text=treemap_data['display_text'],
        textinfo="text",
        textfont=dict(size=12, color="white"),
        textposition="middle center",
        
        # Hover information
        #customdata=treemap_data['hover_text'],
        #hovertemplate="%{customdata}<extra></extra>",
        
        # Styling
        # Styling - FIXED: Remove white outline
        marker_line=dict(width=0),  # Changed from width=2, color="white" to width=0
        pathbar_visible=False

    ))
    
    # Update layout - FIXED: Make background transparent
    fig.update_layout(
        height=500,
        margin=dict(t=0, l=10, r=60, b=10),
        font=dict(size=11),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        template="plotly_white",
        showlegend=False,
        xaxis=dict(
            visible=False,
            showgrid=False,
            showticklabels=False,
            showline=False,
            zeroline=False
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            showticklabels=False,
            showline=False,
            zeroline=False,
        )
    )
    
    # Override backgrounds again
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # Display the treemap
    from visualizations import display_chart
    display_chart(fig, key="matchup_treemap")
    
    # Add explanation
    st.caption(
        "Rectangle size = meta share (how often you'll face this deck). "
        "Color = win rate (red = unfavorable, yellow = even, green = favorable). "
    )

def display_matchup_bar_chart(deck_name, set_name, working_df):
    """
    Display a bar chart showing win rate distribution with 10 bins
    
    Args:
        deck_name: Current deck name
        set_name: Current deck set  
        working_df: DataFrame with matchup data already processed
    """
    
    # Check if we have matchup data
    if working_df.empty:
        st.info("No matchup data available for bar chart.")
        return
    
    # Create 10 bins for win rates (0-10%, 10-20%, etc.)
    bins = list(range(0, 101, 10))  # [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    bin_labels = [f"{i}-{i+9}%" for i in range(0, 100, 10)]
    
    # Assign each matchup to a bin and sum meta shares
    working_df['win_rate_bin'] = pd.cut(working_df['win_pct'], bins=bins, labels=bin_labels, include_lowest=True)
    
    # Aggregate meta share by bin
    bin_data = working_df.groupby('win_rate_bin', observed=True).agg({
        'meta_share': 'sum',
        'opponent_name': 'count'  # Count of matchups in each bin
    }).reset_index()
    
    # Ensure all bins are represented (fill missing with 0)
    all_bins_df = pd.DataFrame({'win_rate_bin': bin_labels})
    bin_data = all_bins_df.merge(bin_data, on='win_rate_bin', how='left').fillna(0)
    
    # Get colors for each bin using the same gradient
    def get_bin_color(bin_index):
        # Map bin index (0-9) to color scale position (0.0-1.0)
        position = bin_index / 9
        
        # Same RGB colors from the gradient
        colors = [
            (220, 53, 69),     # Red (0%)
            (253, 126, 20),    # Red-Orange (10%)
            (255, 152, 0),     # Orange (20%)
            (255, 183, 77),    # Light Orange (30%)
            (255, 235, 59),    # Yellow (40%)
            (205, 220, 57),    # Yellow-Green (50%)
            (156, 204, 101),   # Light Green (60%)
            (139, 195, 74),    # Medium Green (70%)
            (102, 187, 106),   # Green (80%)
            (27, 94, 32)       # Very Dark Green (90-100%)
        ]
        
        return f"rgb({colors[bin_index][0]}, {colors[bin_index][1]}, {colors[bin_index][2]})"
    
    # Create colors list for all bars
    bar_colors = [get_bin_color(i) for i in range(10)]
    
    # Create the bar chart
    import plotly.graph_objects as go
    
    fig = go.Figure(go.Bar(
        x=bin_data['win_rate_bin'],
        y=bin_data['meta_share'],
        marker_color=bar_colors,
        marker_line=dict(width=0),  # No outline
        text=bin_data['meta_share'].apply(lambda x: f"{x:.1f}%" if x > 0 else ""),
        textposition='outside',
        textfont=dict(size=15),
        hovertemplate="<b>%{x}</b><br>Meta Share: %{y:.1f}%<br>Matchups: %{customdata}<extra></extra>",
        customdata=bin_data['opponent_name']
    ))
    
    # Update layout - Clean and minimal
    fig.update_layout(
        height=300,
        margin=dict(t=0, l=10, r=0, b=30),
        
        # Transparent backgrounds
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        
        # Clean axes
        xaxis=dict(
            title="Win Rate Range",
            title_font=dict(size=16),
            tickfont=dict(size=16),
            showgrid=False,
            showline=False,
            zeroline=False
        ),
        yaxis=dict(
            title="Meta Share %",
            title_font=dict(size=16),
            tickfont=dict(size=16),
            showgrid=False,
            showline=False,
            zeroline=False,
            range=[0, 35]
        ),
        
        # Remove legend and other elements
        showlegend=False,
        font=dict(size=11)
    )
    
    # Display the chart
    import streamlit as st
    
    custom_config = {
        'displayModeBar': False,
        'staticPlot': True,
        'displaylogo': False,
    }
    
    st.plotly_chart(fig, use_container_width=True, config=custom_config, key="matchup_bar_chart")
    
    # Add explanation
    st.caption(
        "Shows how much of the meta falls into each win rate range. "
        "Higher bars in green ranges = more favorable meta coverage."
    )
    
# Modify the display_related_decks_tab function in display_tabs.py:
def display_related_decks_tab(deck_info, results):
    """Display the Related Decks tab with banner images and simple buttons"""
    st.write("#### Related Decks")
    
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
            st.write("Decks sharing Pokémon with this archetype:")
            
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
                    
                    # Display the banner image
                    if header_image:
                        st.markdown(f"""
                        <div style="width: 100%; height: auto; overflow: hidden; border-radius: 10px 10px 10px 0px; margin-bottom: 0px;">
                            <img src="data:image/png;base64,{header_image}" style="width: 100%; max-width:300px; object-fit: cover; border-radius: 10px;">
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="width: 100%; height: 80px; background-color: #f0f0f0; border-radius: 6px 6px 0 0; margin-bottom: 8px; display: flex; align-items: center; justify-content: center;">
                            <span style="color: #888;">No image</span>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Simple tertiary button with the deck name
                    if st.button(formatted_name, key=f"btn_{deck['deck_name']}_{i}", type="tertiary"):
                        # Set this deck to be analyzed
                        st.session_state.deck_to_analyze = deck['deck_name']
                        # Force rerun to trigger the analysis
                        st.rerun()
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

    # st.write("### Energy Type Analysis")
    
    # # Create columns for different data sources
    # col1, col2 = st.columns(2)
    
    # with col1:
    #     st.subheader("Cached Energy Data")
        
    #     # Check all possible sources of energy data
        
    #     # 1. Session energy cache (if it exists)
    #     if 'energy_cache' in st.session_state:
    #         cache_key = f"{deck_name}_{set_name}_energy"
    #         st.write("**Dedicated Energy Cache:**")
    #         if cache_key in st.session_state.energy_cache:
    #             energy = st.session_state.energy_cache[cache_key]
    #             st.write(f"Found: {energy}")
                
    #             # Show icons for this energy
    #             from ui_helpers import render_energy_icons
    #             energy_html = render_energy_icons(energy, True)
    #             st.markdown(energy_html, unsafe_allow_html=True)
    #         else:
    #             st.write("Not found in dedicated cache")
        
    #     # 2. Analyzed deck cache
    #     st.write("**Analyzed Deck Cache:**")
    #     analyzed_key = f"full_deck_{deck_name}_{set_name}"
    #     if 'analyzed_deck_cache' in st.session_state and analyzed_key in st.session_state.analyzed_deck_cache:
    #         analyzed_data = st.session_state.analyzed_deck_cache[analyzed_key]
            
    #         # Check for both fields
    #         energy_types = analyzed_data.get('energy_types', [])
    #         most_common = analyzed_data.get('most_common_energy', [])
            
    #         st.write(f"All energy types: {energy_types}")
    #         st.write(f"Most common energy: {most_common}")
            
    #         # Show icons for this energy
    #         from ui_helpers import render_energy_icons
    #         if most_common:
    #             st.markdown("Most common energy icons:")
    #             energy_html = render_energy_icons(most_common, True)
    #             st.markdown(energy_html, unsafe_allow_html=True)
    #     else:
    #         st.write("Not found in analyzed deck cache")
        
    #     # 3. Sample deck cache
    #     st.write("**Sample Deck Cache:**")
    #     sample_key = f"sample_deck_{deck_name}_{set_name}"
    #     if 'sample_deck_cache' in st.session_state and sample_key in st.session_state.sample_deck_cache:
    #         sample_data = st.session_state.sample_deck_cache[sample_key]
            
    #         # Check for both fields
    #         energy_types = sample_data.get('energy_types', [])
    #         most_common = sample_data.get('most_common_energy', [])
            
    #         st.write(f"All energy types: {energy_types}")
    #         st.write(f"Most common energy: {most_common}")
    #     else:
    #         st.write("Not found in sample deck cache")
    
    # with col2:
    #     st.subheader("Calculated Energy Data")
        
    #     # 4. Try to calculate from collected decks
    #     st.write("**From Collected Decks:**")
    #     deck_key = f"{deck_name}_{set_name}"
    #     if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
    #         collected_data = st.session_state.collected_decks[deck_key]
            
    #         if 'decks' in collected_data and collected_data['decks']:
    #             # Calculate combinations for display
    #             combinations = {}
    #             total_decks = 0
                
    #             for deck in collected_data['decks']:
    #                 if 'energy_types' in deck and deck['energy_types']:
    #                     total_decks += 1
    #                     combo = tuple(sorted(deck['energy_types']))
    #                     combinations[combo] = combinations.get(combo, 0) + 1
                
    #             # Display the combinations
    #             st.write(f"Total decks with energy: {total_decks}")
                
    #             if combinations:
    #                 # Find most common
    #                 most_common_combo = max(combinations.items(), key=lambda x: x[1])[0]
    #                 most_common_count = combinations[most_common_combo]
    #                 most_common_pct = (most_common_count / total_decks * 100) if total_decks > 0 else 0
                    
    #                 st.write(f"Most common: {list(most_common_combo)} ({most_common_count} decks, {most_common_pct:.1f}%)")
                    
    #                 # Show it with icons
    #                 from ui_helpers import render_energy_icons
    #                 st.markdown("Most common (calculated):")
    #                 energy_html = render_energy_icons(list(most_common_combo), True)
    #                 st.markdown(energy_html, unsafe_allow_html=True)
                    
    #                 # Show all combinations
    #                 st.write("All combinations:")
    #                 for combo, count in sorted(combinations.items(), key=lambda x: x[1], reverse=True):
    #                     pct = (count / total_decks * 100) if total_decks > 0 else 0
    #                     st.write(f"- {list(combo)}: {count} decks ({pct:.1f}%)")
    #             else:
    #                 st.write("No energy combinations found")
    #         else:
    #             st.write("No decks with energy data")
    #     else:
    #         st.write("No collected decks found")
        
    #     # 5. Energy from Energy Utils (for comparison/debugging)
    #     st.write("**From Energy Utils (Legacy):**")
    #     if 'archetype_energy_types' in st.session_state and deck_name in st.session_state.archetype_energy_types:
    #         st.write(f"All types: {list(st.session_state.archetype_energy_types[deck_name])}")
    #     else:
    #         st.write("Not found in archetype_energy_types")
            
    #     if 'archetype_energy_combos' in st.session_state and deck_name in st.session_state.archetype_energy_combos:
    #         combos = st.session_state.archetype_energy_combos[deck_name]
    #         if combos:
    #             most_common = max(combos.items(), key=lambda x: x[1])[0]
    #             st.write(f"Most common combo: {list(most_common)}")
                
    #             # Show with icons
    #             from ui_helpers import render_energy_icons
    #             st.markdown("Most common (from energy_utils):")
    #             energy_html = render_energy_icons(list(most_common), True)
    #             st.markdown(energy_html, unsafe_allow_html=True)
    #         else:
    #             st.write("No combinations found")
    #     else:
    #         st.write("Not found in archetype_energy_combos")
    
    # Add the detailed energy table at the bottom
    #st.write("##### Detailed Energy Data")
    
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

def display_matchup_summary(deck_name, set_name, working_df):
    """
    Display a summary of matchup distribution against the meta
    
    Args:
        deck_name: Current deck name
        set_name: Current deck set
        working_df: DataFrame with matchup data already processed
    """
    st.write("#### Meta Matchup Distribution")
    
    # Check if we have matchup data with meta share
    if working_df.empty or 'meta_share' not in working_df.columns:
        st.info("No matchup data with meta share available.")
        return

    win_upper = 57.5
    win_lower = 42.5
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
    
    # Normalize values to sum to 100% (just the three known categories)
    if total_known_share > 0:  # Avoid division by zero
        # Normalize each value
        favorable_share_norm = (favorable_share / total_known_share) * 100
        even_share_norm = (even_share / total_known_share) * 100
        unfavorable_share_norm = (unfavorable_share / total_known_share) * 100
    else:
        # If no data, set all to 0
        favorable_share_norm = 0
        even_share_norm = 0
        unfavorable_share_norm = 0
    
    # Columns
    col1, col2, col3 = st.columns([1,1,1])
    
    # Display favorable matchups
    with col1:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px; border-radius: 8px; height: 100px;">
            <div style="font-size: 1.1rem; font-weight: bold; ">Unfavorable</div>
            <div style="font-size: 2.5rem; font-weight: bold; color: #fd6c6c; line-height: 0.8;">{unfavorable_share_norm:.1f}%</div>
            <div style="font-size: 1rem; ">of meta</div>
        </div>
        """, unsafe_allow_html=True)
    # Display even matchups
    with col2:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px;  border-radius: 8px; height: 100px;">
            <div style="font-size: 1.1rem; font-weight: bold;">Even</div>
            <div style="font-size: 2.5rem; font-weight: bold; color: #E6CA00; line-height: 0.8;">{even_share_norm:.1f}%</div>
            <div style="font-size: 1rem;">of meta</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display unfavorable matchups
    with col3:
       st.markdown(f"""
       <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px;  border-radius: 8px; height: 100px;">
            <div style="font-size: 1.1rem; font-weight: bold; ">Favorable</div>
            <div style="font-size: 2.5rem; font-weight: bold; color: #4FCC20; line-height: 0.8;">{favorable_share_norm:.1f}%</div>
            <div style="font-size: 1rem; ">of meta</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.caption(f"This shows how much of the current meta (≥0.5% share) has favorable (≥{win_upper}% win rate), even ({win_lower}-{win_upper}% win rate), or unfavorable (<{win_lower}% win rate) matchups against this deck. Values are normalized to sum to 100%. (Raw data: Favorable {favorable_share:.1f}%, Even {even_share:.1f}%, Unfavorable {unfavorable_share:.1f}%)")       
    # # Add a more detailed note about the data
    # st.write("")
    # Display the bar chart
    display_matchup_bar_chart(deck_name, set_name, working_df)
    
    # Add some space
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # ADDED: Display the treemap
    #display_matchup_treemap(deck_name, set_name, working_df)
    
    
    # Add some space
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)


def display_matchup_tab(deck_info=None):
    """
    Display the Matchup tab with detailed matchup data.
    
    Args:
        deck_info: Dictionary containing deck information (optional)
    """
    #st.subheader("Matchup Analysis")
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
    
    # Show filter option - commented out as requested
    # show_all = st.checkbox("Show all matchups (unchecked = meta decks only)", value=False)
    # Always filter by default
    show_all = False
    
    # Create a copy to work with
    working_df = matchup_df.copy()

    # Filter out current deck from matchups (ADD THIS LINE)
    working_df = working_df[working_df['opponent_deck_name'] != deck_name]

    # ADD THIS: Filter by minimum matches
    from config import MIN_MATCHUP_MATCHES
    original_count = len(working_df)
    working_df = working_df[working_df['matches_played'] >= MIN_MATCHUP_MATCHES]
    filtered_count = original_count - len(working_df)

    # Only apply filtering if we have meta decks and user wants filtering
    if meta_decks and not show_all:
        # Add lowercase versions for better matching
        working_df['deck_name_lower'] = working_df['opponent_deck_name'].str.lower()
        meta_decks_lower = [d.lower() for d in meta_decks]
        
        # Apply filter
        filtered_df = working_df[working_df['deck_name_lower'].isin(meta_decks_lower)]
        if filtered_count > 0:
            st.info(f"Showing {len(filtered_df)} matchups with at least {MIN_MATCHUP_MATCHES} matches. "
                    f"Filtered out {filtered_count} matchups with insufficient data for reliability.")
        
        # Use filtered data if we found matches
        if not filtered_df.empty:
            #st.success(f"Showing {len(filtered_df)} meta deck matchups")
            working_df = filtered_df.drop(columns=['deck_name_lower'])
        else:
            st.warning("No matches found with current meta decks. Showing all matchups instead.")
            working_df = working_df.drop(columns=['deck_name_lower'])
       
    
    # Apply the function to extract Pokémon image URLs
    working_df[['pokemon_url1', 'pokemon_url2']] = working_df.apply(
        lambda row: pd.Series(extract_pokemon_urls(row['opponent_deck_name'])), 
        axis=1
    )
    
    # Create a better formatted display version
    display_df = working_df.copy()
    
    # Add rank column
    display_df.insert(0, 'Rank', range(1, len(display_df) + 1))
    
    # Add matchup column 
    display_df['Matchup'] = display_df['win_pct'].apply(
        lambda wp: "Favorable" if wp >= 57.5 else ("Unfavorable" if wp < 42.5 else "Even")
    )
    
    # Format the record column
    display_df['Record'] = display_df.apply(
        lambda row: f"{row['wins']}-{row['losses']}-{row['ties']}", axis=1
    )
    
    # Select and rename columns for display - now including the icon columns
    formatted_df = pd.DataFrame({
       # 'Rank': display_df['Rank'],
        'Icon1': display_df['pokemon_url1'],
        'Icon2': display_df['pokemon_url2'],
        'Deck': display_df['opponent_name'],
        'Matchup': display_df['Matchup'],
        'Win %': display_df['win_pct'],
        'Record': display_df['Record'],
        'Matches': display_df['matches_played'],
        'Meta Share %': display_df['meta_share']
    })
    
    # Apply styling for matchups
    def highlight_matchups(val):
        """Apply colors to matchup column values"""
        if val == "Favorable":
            return 'background-color: rgba(100, 200, 100, 0.4)'  # Light green
        elif val == "Unfavorable":
            return 'background-color: rgba(255, 100, 100, 0.4)'  # Light red
        else:
            return 'background-color: rgba(255, 235, 100, 0.4)'  # Light yellow
    
    # Display the enhanced data table with all rows
    display_matchup_summary(deck_name, set_name, working_df)
    
    try:
        # First try with styled dataframe and images
        styled_df = formatted_df.style.applymap(highlight_matchups, subset=['Matchup'])
        st.write("##### Matchup Data")
        st.dataframe(
            styled_df,
            use_container_width=True,
            #height=850,
            column_config={
                "Rank": st.column_config.NumberColumn(
                    "#",
                    help="Position in the list sorted by Win %",
                    width="8px",
                ),
                "Icon1": st.column_config.ImageColumn(
                    "Icon 1",
                    help="First Pokémon in the deck",
                    width="20px",
                ),
                "Icon2": st.column_config.ImageColumn(
                    "Icon 2", 
                    help="Second Pokémon in the deck",
                    width="20px",
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
                    help="Win-Loss-Tie record against this deck"
                ),
                "Matches": st.column_config.NumberColumn(
                    "Matches",
                    help="Total number of matches played against this deck"
                ),
                "Matchup": st.column_config.TextColumn(
                    "Matchup",
                    help="Favorable: ≥57.5%, Unfavorable: <42.5%, Even: 42.5-57.5%"
                ),
                "Meta Share %": st.column_config.NumberColumn(
                    "Meta Share %",
                    help="Percentage representation of this deck in the overall competitive metagame",
                    format="%.2f%%"
            ),
            },
            hide_index=True
        )
    except Exception as e:
        # Fallback to simpler version if there's an issue
        st.error(f"Error displaying styled dataframe with images: {str(e)}")
        st.write("Showing basic version without styling and images:")
        
        # Remove image columns for fallback
        basic_df = formatted_df.drop(columns=['Icon1', 'Icon2'])
        st.dataframe(
            basic_df,
            use_container_width=True,
            #height=850,
            column_config={
                "Win %": st.column_config.NumberColumn(
                    "Win %",
                    format="%.1f%%",
                ),
            },
            hide_index=True
        )
    # After working_df is prepared, display the matchup summary
    #display_matchup_summary(deck_name, set_name, working_df)
    # Add some space between summary and table
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    st.caption(f"Data based on the current compiled tournament data on [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET).")
    # Add explanation
    from formatters import format_deck_name
    formatted_deck_name = format_deck_name(deck_name)

# def display_counter_picker():
#     banner_path = "picker_banner.png"
#     if os.path.exists(banner_path):
#         with open(banner_path, "rb") as f:
#             banner_base64 = base64.b64encode(f.read()).decode()
#         st.markdown(f"""
#         <div style="width:100%; text-align:left; margin:0px 0 0px 0;">
#             <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px; margin-bottom:10px;">
#         </div>
#         """, unsafe_allow_html=True)
#     else:
#         st.subheader("Meta Counter Picker")
    
#     # Get list of top meta decks to choose from
#     meta_decks = []
#     meta_deck_info = {}
    
#     if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
#         performance_data = st.session_state.performance_data
        
#         for _, deck in performance_data.iterrows():
#             meta_decks.append(deck['displayed_name'])
#             meta_deck_info[deck['displayed_name']] = {
#                 'deck_name': deck['deck_name'],
#                 'set': deck['set']
#             }
        
#         # Limit to top 20 decks
#         meta_decks = meta_decks[:20]
    
#     if not meta_decks:
#         st.warning("No meta deck data available")
#         return
    
#     # Create 2-column layout for dropdown and button
#     col1, col2 = st.columns([3, 1])
    
#     with col1:
#         # Multi-select for decks to counter
#         selected_decks = st.multiselect(
#             "Select decks you want to counter:",
#             options=meta_decks,
#             default=meta_decks[:3] if len(meta_decks) >= 3 else meta_decks,
#             help="Choose the decks you want to counter in the meta"
#         )
    
#     with col2:
#         # Add vertical space to align with the dropdown
#         st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
#         # Button to trigger analysis
#         find_button = st.button("Find Counters", type="secondary", use_container_width=True)
    
#     # Only proceed if decks are selected
#     if not selected_decks:
#         st.info("Please select at least one deck to find counters")
#         return
    
#     # Only proceed if button clicked
#     if not find_button:
#         return
        
#     with st.spinner("Analyzing counters..."):
#         # This collects all matchup data for each meta deck
#         counter_data = []
        
#         # Convert from displayed names to internal deck names for matching
#         selected_internal_names = []
#         for displayed in selected_decks:
#             for _, meta_deck in st.session_state.performance_data.iterrows():
#                 if meta_deck['displayed_name'] == displayed:
#                     selected_internal_names.append(meta_deck['deck_name'])
        
#         # For each possible counter deck in the meta
#         for _, deck in st.session_state.performance_data.iterrows():
#             deck_name = deck['deck_name']
#             set_name = deck['set']
#             displayed_name = deck['displayed_name']
            
#             # Get this deck's matchups
#             matchups = fetch_matchup_data(deck_name, set_name)
            
#             if matchups.empty:
#                 continue
            
#             # Initialize variables for weighted average calculation
#             total_weighted_win_rate = 0
#             total_matches = 0
#             matched_decks = 0
            
#             # Look for matchups against selected decks
#             for _, matchup in matchups.iterrows():
#                 if matchup['opponent_deck_name'] in selected_internal_names:
#                     # Get the number of matches for this matchup
#                     match_count = matchup['matches_played']
                    
#                     # Add to weighted sum (win percentage × number of matches)
#                     total_weighted_win_rate += matchup['win_pct'] * match_count
                    
#                     # Add to total matches count
#                     total_matches += match_count
                    
#                     # Still track number of matched decks for filtering
#                     matched_decks += 1
            
#             # Only include if we found matchups against at least half the selected decks
#             if matched_decks >= len(selected_decks) / 2:
#                 # Calculate weighted average: total weighted sum divided by total matches
#                 avg_win_rate = total_weighted_win_rate / total_matches if total_matches > 0 else 0
                
#                 counter_data.append({
#                     'deck_name': deck_name,
#                     'displayed_name': displayed_name,
#                     'set': set_name,
#                     'average_win_rate': avg_win_rate,
#                     'meta_share': deck['share'],
#                     'power_index': deck['power_index'],
#                 })
        
#         # Create DataFrame and sort by average win rate
#         if counter_data:
#             counter_df = pd.DataFrame(counter_data)
#             counter_df = counter_df.sort_values('average_win_rate', ascending=False)
            
#             # Display top counters header
#             st.write("#### Top Counters to Selected Decks")
            
#             # Display top 5 counter decks
#             for i in range(min(5, len(counter_df))):
#                 deck = counter_df.iloc[i]
                
#                 # Create deck_info object for header image
#                 deck_info = {
#                     'deck_name': deck['deck_name'],
#                     'set': deck['set']
#                 }
                
#                 # Generate header image
#                 header_image = create_deck_header_images(deck_info, None)
                
#                 # Layout based on ranking
#                 if i < 3:  # Top 3 decks
#                     col1, col2, col3 = st.columns([1.5, 2, 1])
                    
#                     with col1:
#                         if header_image:
#                             st.markdown(f"""
#                             <div style="margin-right: 1rem; width: 100%; text-align: right;">
#                                 <img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 250px; height: auto; border-radius: 10px;">
#                             </div>
#                             """, unsafe_allow_html=True)
#                         else:
#                             st.markdown("""
#                             <div style="width: 100%; height: 80px; background-color: #f0f0f0; border-radius: 6px; 
#                                 display: flex; align-items: center; justify-content: center;">
#                                 <span style="color: #888;">No image</span>
#                             </div>
#                             """, unsafe_allow_html=True)
                    
#                     with col2:
#                         rank_emoji = ["🥇", "🥈", "🥉"][i]
#                         st.markdown(f"#### {rank_emoji} {deck['displayed_name']}")
                    
#                     with col3:
#                         win_rate = deck['average_win_rate']
#                         win_color = "#4FCC20" if win_rate >= 55 else "#fda700" if win_rate < 45 else "#fdc500"
#                         st.markdown(f"""
#                         <div style="text-align: center;">
#                             <span style="font-size: 2.2rem; font-weight: bold; color: {win_color};">{win_rate:.1f}%</span>
#                             <div style="font-size: 0.8rem; margin-top: -0.5rem;">win rate</div>
#                         </div>
#                         """, unsafe_allow_html=True)
#                 else:  # 4th and 5th place
#                     col1, col2, col3 = st.columns([1, 2, 0.8])
                    
#                     with col1:
#                         if header_image:
#                             st.markdown(f"""
#                             <div style="margin-right: 1rem; width: 100%; max-width: 250px; text-align: right;">
#                                 <img src="data:image/png;base64,{header_image}" style="width: 75%; height: auto; border-radius: 8px;">
#                             </div>
#                             """, unsafe_allow_html=True)
#                         else:
#                             st.markdown("""
#                             <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 6px; 
#                                 display: flex; align-items: center; justify-content: center;">
#                                 <span style="color: #888; font-size: 0.8rem;">No image</span>
#                             </div>
#                             """, unsafe_allow_html=True)
                    
#                     with col2:
#                         rank_num = f"#{i+1}"
#                         st.markdown(f"#### {rank_num} {deck['displayed_name']}")
                    
#                     with col3:
#                         win_rate = deck['average_win_rate']
#                         win_color = "#4FCC20" if win_rate >= 55 else "#fd6c6c" if win_rate < 45 else "#fdc500"
#                         st.markdown(f"""
#                         <div style="text-align: center;">
#                             <span style="font-size: 1.5rem; font-weight: bold; color: {win_color};">{win_rate:.1f}%</span>
#                         </div>
#                         """, unsafe_allow_html=True)
                
#                 # Add divider between decks
#                 if i < min(4, len(counter_df) - 1):
#                     divider_margin = "1rem" if i < 3 else "0.6rem"
#                     divider_style = "solid 1px"
#                     divider_color = "#ddd" if i < 3 else "#eee"
#                     st.markdown(f"<hr style='margin: {divider_margin} 0; border-top: {divider_style} {divider_color};'>", unsafe_allow_html=True)
            
#             # Add explanation caption
#             st.caption("Higher average win rate indicates better performance against your selected decks. Data is from the current aggregated tournament result in [Limitless TCG](https://play.limitlesstcg.com/decks?game=pocket)")
#         else:
#             st.warning("No counter data found for the selected decks")
