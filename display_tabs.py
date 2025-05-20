# display_tabs.py
"""Functions for rendering the tabs in the main content area"""

import streamlit as st
from formatters import format_deck_name
from related_decks import find_related_decks
from image_processor import create_deck_header_images
from visualizations import create_usage_bar_chart, display_chart, create_variant_bar_chart, ENERGY_COLORS
from analyzer import build_deck_template
from card_renderer import render_deck_section, render_option_section
from energy_utils import get_archetype_from_deck_name, render_energy_icons
from config import TOURNAMENT_COUNT, POKEMON_EXCEPTIONS

def display_deck_header(deck_info, results):
    """Display the deck header with image"""
    header_image = create_deck_header_images(deck_info, results)
    
    if header_image:
        st.markdown(f"""
        <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@1,900&display=swap" rel="stylesheet">
        <div style="display: flex; flex-direction: column; align-items: flex-start; margin-bottom: 0rem; margin-top:-1rem">
            <h2 style="margin: 0rem 0 0 0; font-family: 'Nunito', sans-serif; font-weight: 900; font-style: italic;"><img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 350px; height: auto; margin-bottom:0.2em; margin-right:0.5em;border-radius: 10px;">{format_deck_name(deck_info['deck_name'])}</h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@1,900&display=swap" rel="stylesheet">
        """, unsafe_allow_html=True)
        st.markdown(f"""<h1 style="font-family: 'Nunito', sans-serif; font-weight: 900; font-style: italic; letter-spacing: -1px; line-height: 0.8;">{format_deck_name(deck_info['deck_name'])}</h1>""", unsafe_allow_html=True)

# In display_card_usage_tab function in display_tabs.py
def display_card_usage_tab(results, total_decks, variant_df):
    """Display the Card Usage tab with energy-colored charts based on deck energy types"""
    # Create two columns for Pokemon and Trainer
    st.write("#### Card Usage & Variants")
    col1, col2 = st.columns([1, 1])
    
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
            display_chart(fig)
        else:
            st.info("No Pokemon cards found")

        if not variant_df.empty:
            # Import variant renderer
            from card_renderer import render_variant_cards
            
            # Display variant analysis
            for _, row in variant_df.iterrows():
                with st.expander(f"{row['Card Name']} Variants ({row['Total Decks']} decks)", expanded=False):
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
                        display_chart(fig_var) 
        
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
            display_chart(fig)
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

def display_deck_template_tab(results):
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
        
        # No need to ensure collected decks since we're now caching everything
        # The data should already be in st.session_state.collected_decks if needed
    
    # Create outer columns: Sample Deck (2) and Template (3) - switched order and ratio
    outer_col1, _, outer_col2 = st.columns([6,1,10])
    
    # Left column: Sample Deck(s)
    with outer_col1:
        # Display standard sample deck and variant decks
        display_variant_decks(deck_info, energy_types, is_typical, options)
    
    # Right column: Core Cards and Flexible Slots in vertical layout
    with outer_col2:
        display_deck_composition(deck_info, energy_types, is_typical, total_cards, options)

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
    
    # Get the variant Pokémon names
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
    
    # Limit the variants to show (to avoid overwhelming UI)
    max_variants = 5  # Show at most 5 variants
    
    # For each different Pokemon, show a variant deck in an expander
    for idx, (_, pokemon) in enumerate(different_pokemon.iterrows()):
        if idx >= max_variants:
            break
            
        pokemon_name = pokemon['card_name']
        set_code = pokemon.get('set', '')
        num = pokemon.get('num', '')
        
        # Create a formatted title with set and number info
        variant_title = f"{pokemon_name} ({set_code}-{num}) Variant" if set_code and num else f"{pokemon_name} Variant"
        
        with st.expander(variant_title, expanded=False):
            # Create a set of Pokémon to avoid (other variants)
            other_variants = set(name for name in variant_pokemon_names if name.lower() != pokemon_name.lower())
            
            # Render a deck with this Pokémon but preferably without other variants
            deck_num = render_optimal_variant_deck(pokemon, other_variants, shown_deck_nums, energy_types, is_typical)
            
            # If we found a deck, add it to the shown list
            if deck_num is not None:
                shown_deck_nums.add(deck_num)

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


def display_deck_composition(deck_info, energy_types, is_typical, total_cards, options):
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
        core_cards_header = f"""##### Core Cards <span style="font-size: 1rem; font-weight: normal;">(Energy: {energy_html}{archetype_note})</span>"""
    else:
        # Just "Core Cards" if no energy found
        core_cards_header = "##### Core Cards"
    
    # Display the header
    st.write(core_cards_header, unsafe_allow_html=True)
    
    # Create single column card grid renderer with larger card size
    from card_renderer import CardGrid
    
    # Core Cards: Pokemon and Trainer in columns with 1:2 ratio
    core_col1, core_col2 = st.columns([1, 2])
    
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
    st.write(f"##### Flexible Slots ({remaining} cards)", unsafe_allow_html=True)
    
    # Sort options by usage percentage (descending) and split by type
    pokemon_options = options[options['type'] == 'Pokemon'].sort_values(by='display_usage', ascending=False)
    trainer_options = options[options['type'] == 'Trainer'].sort_values(by='display_usage', ascending=False)
    
    # Flexible Slots: Pokemon and Trainer options in columns with 1:2 ratio
    flex_options_available = not pokemon_options.empty or not trainer_options.empty
    
    if flex_options_available:
        flex_col1, flex_col2 = st.columns([1, 2])
        
        with flex_col1:
            # Only show Pokemon options if there are any
            if not pokemon_options.empty:
                st.write("###### Pokémon Options")
                pokemon_options_grid = CardGrid(card_width=65, gap=4, show_percentage=True)
                pokemon_options_grid.add_cards_from_dataframe(pokemon_options)
                pokemon_options_grid.display()
        
        with flex_col2:
            # Only show Trainer options if there are any
            if not trainer_options.empty:
                st.write("###### Trainer Options")
                trainer_options_grid = CardGrid(card_width=65, gap=4, show_percentage=True)
                trainer_options_grid.add_cards_from_dataframe(trainer_options)
                trainer_options_grid.display()
    else:
        st.info("No flexible options available for this deck.")
        
def display_raw_data_tab(results, variant_df):
    """Display the Raw Data tab"""
    # Main analysis data
    st.write("#### Card Usage Data")
    st.dataframe(results, height=1000, use_container_width=True)
    
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

    # Add rank column
    display_df.insert(0, 'rank', range(1, len(display_df) + 1))

    # Add an indicator emoji for the current deck
    display_df['rank'] = display_df.apply(
        lambda row: f"➡️ {row['rank']}" if row['deck_name'] == current_deck_name else row['rank'], 
        axis=1
    )
    
    # Calculate win rate
    display_df['win_rate'] = round((display_df['total_wins'] / (display_df['total_wins'] + display_df['total_losses'] + display_df['total_ties'])) * 100, 1)
    
    # Format numerical columns
    display_df['share'] = display_df['share'].round(2)
    display_df['power_index'] = display_df['power_index'].round(2)

    # Extract Pokémon names and create image URLs
    def extract_pokemon_urls(displayed_name):
        # Remove content in parentheses and clean
        clean_name = re.sub(r'\([^)]*\)', '', displayed_name).strip()
        
        # Split by spaces and slashes
        parts = re.split(r'[\s/]+', clean_name)
        
        # Filter out suffixes
        suffixes = ['ex', 'v', 'vmax', 'vstar', 'gx']
        pokemon_names = []
        
        for part in parts:
            part = part.lower()
            if part and part not in suffixes:
                # Apply exceptions
                if part in POKEMON_EXCEPTIONS:
                    part = POKEMON_EXCEPTIONS[part]
                
                pokemon_names.append(part)
                
                # Limit to 2 Pokémon
                if len(pokemon_names) >= 2:
                    break
        
        # Create URLs
        urls = []
        for name in pokemon_names:
            urls.append(f"https://r2.limitlesstcg.net/pokemon/gen9/{name}.png")
            
        # Ensure we have exactly 2 elements
        while len(urls) < 2:
            urls.append(None)
            
        return urls[0], urls[1]  # Return as separate values
    
    # Apply the function to extract Pokémon image URLs
    display_df[['pokemon_url1', 'pokemon_url2']] = display_df.apply(
        lambda row: pd.Series(extract_pokemon_urls(row['displayed_name'])), 
        axis=1
    )
    
    # Select and rename columns for display
    display_cols = {
        'rank': 'Rank',
        'displayed_name': 'Deck',
        'power_index': 'Power Index',
        'share': 'Meta Share %',
        'tournaments_played': 'Best Finish Entries',
        'win_rate': 'Win %',
        'total_wins': 'Wins',
        'total_losses': 'Losses',
        'total_ties': 'Ties'      
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
        height=800,
        column_config={
            # "Rank": st.column_config.NumberColumn(
            #     "Rank",
            #     help="Position in the meta based on Power Index",
            #     width="small"
            # ),
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
                help="Deck archetype name"
            ),
            "Power Index": st.column_config.NumberColumn(
                "Power Index",
                help="Performance metric: (Wins + 0.75×Ties - Losses) ÷ √(Total Games). Higher values indicate stronger performance",
                format="%.2f"
            ),
            "Meta Share %": st.column_config.NumberColumn(
                "Meta Share %",
                help="Percentage representation of this deck in the overall competitive metagame",
                format="%.2f%%"
            ),
            "Best Finish Entries": st.column_config.NumberColumn(
                "Best Finish Entries",
                help="Number of tournament entries in the 'Best Finishes' section"
            ),
            "Win %": st.column_config.NumberColumn(
                "Win %",
                help="Percentage of matches won out of total matches played",
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
            
            # Create a 4-column layout
            cols = st.columns(4)
            
            # Display each related deck
            for i, (_, deck) in enumerate(related_decks.iterrows()):
                col_idx = i % 4
                
                with cols[col_idx]:
                    # Format deck name
                    formatted_name = format_deck_name(deck['deck_name'])
                    
                    # Create related deck info for image generation
                    related_deck_info = {
                        'deck_name': deck['deck_name'],
                        'set': deck['set']
                    }
                    
                    # Generate header image using pre-loaded Pokémon info
                    header_image = create_deck_header_images(related_deck_info)
                    
                    # Display the banner image
                    if header_image:
                        st.markdown(f"""
                        <div style="width: 100%; height: auto; overflow: hidden; border-radius: 10px 0px 10px 0; margin-bottom: 0px;">
                            <img src="data:image/png;base64,{header_image}" style="width: 100%; max-width:250px; object-fit: cover;">
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
def fetch_matchup_data(deck_name, set_name="A3"):
    """
    Fetch matchup data for a specific deck from Limitless TCG.
    
    Args:
        deck_name: The name of the deck (e.g., "giratina-ex-a2b-greninja-a1")
        set_name: The set name (default: "A3")
        
    Returns:
        DataFrame containing matchup data or empty DataFrame if not found
    """
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
    import re
    from config import BASE_URL
    import streamlit as st
    
    # Construct the URL for matchups
    url = f"{BASE_URL}/decks/{deck_name}/matchups/?game=POCKET&format=standard&set={set_name}"
    
    try:
        # Fetch the webpage
        response = requests.get(url)
        if response.status_code != 200:
            return pd.DataFrame()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='striped')
        
        if not table:
            return pd.DataFrame()
        
        # Process each data row
        rows = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all(['td'])
            if len(cells) < 5:
                continue
            
            # Extract opponent deck display name
            opponent_display_name = cells[1].text.strip()
            
            # Extract opponent deck raw name from URL
            opponent_deck_name = ""
            opponent_link = cells[1].find('a')
            
            if opponent_link and 'href' in opponent_link.attrs:
                href = opponent_link['href']
                match = re.search(r'/matchups/([^/?]+)', href)
                if match:
                    opponent_deck_name = match.group(1)
                else:
                    match = re.search(r'/decks/([^/?]+)', href)
                    if match:
                        opponent_deck_name = match.group(1)
            
            # Extract matches played
            matches_played = 0
            try:
                matches_played = int(cells[2].text.strip())
            except ValueError:
                pass
            
            # Extract record
            record_text = cells[3].text.strip()
            wins, losses, ties = 0, 0, 0
            
            win_match = re.search(r'^(\d+)', record_text)
            loss_match = re.search(r'-\s*(\d+)\s*-', record_text)
            tie_match = re.search(r'-\s*(\d+)$', record_text)
            
            if win_match: wins = int(win_match.group(1))
            if loss_match: losses = int(loss_match.group(1))
            if tie_match: ties = int(tie_match.group(1))
            
            # Extract win percentage
            win_pct = 0.0
            try:
                win_pct = float(cells[4].text.strip().replace('%', ''))
            except ValueError:
                pass
            
            # Create row data
            row_data = {
                'opponent_name': opponent_display_name,
                'opponent_deck_name': opponent_deck_name,
                'wins': wins,
                'losses': losses,
                'ties': ties,
                'win_pct': win_pct,
                'matches_played': matches_played
            }
            
            rows.append(row_data)
        
        # Create DataFrame from all row data
        df = pd.DataFrame(rows)
        
        if not df.empty:
            df = df.sort_values('win_pct', ascending=False).reset_index(drop=True)
        
        return df
        
    except Exception as e:
        return pd.DataFrame()

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
    
    # Only apply filtering if we have meta decks and user wants filtering
    if meta_decks and not show_all:
        # Add lowercase versions for better matching
        working_df['deck_name_lower'] = working_df['opponent_deck_name'].str.lower()
        meta_decks_lower = [d.lower() for d in meta_decks]
        
        # Apply filter
        filtered_df = working_df[working_df['deck_name_lower'].isin(meta_decks_lower)]
        
        # Use filtered data if we found matches
        if not filtered_df.empty:
            #st.success(f"Showing {len(filtered_df)} meta deck matchups")
            working_df = filtered_df.drop(columns=['deck_name_lower'])
        else:
            st.warning("No matches found with current meta decks. Showing all matchups instead.")
            working_df = working_df.drop(columns=['deck_name_lower'])
       
    # Function to extract Pokémon names and create image URLs
    def extract_pokemon_urls(displayed_name):
        clean_name = re.sub(r'\([^)]*\)', '', displayed_name).strip()
        parts = re.split(r'[\s/]+', clean_name)
        suffixes = ['ex', 'v', 'vmax', 'vstar', 'gx']
        pokemon_names = []
        
        for part in parts:
            part = part.lower()
            if part and part not in suffixes:
                if part in POKEMON_EXCEPTIONS:
                    part = POKEMON_EXCEPTIONS[part]
                pokemon_names.append(part)
                if len(pokemon_names) >= 2:
                    break
        
        urls = []
        for name in pokemon_names:
            urls.append(f"https://r2.limitlesstcg.net/pokemon/gen9/{name}.png")
        
        # Ensure we have exactly 2 elements
        while len(urls) < 2:
            urls.append(None)
            
        return urls[0], urls[1]
    
    # Apply the function to extract Pokémon image URLs
    working_df[['pokemon_url1', 'pokemon_url2']] = working_df.apply(
        lambda row: pd.Series(extract_pokemon_urls(row['opponent_name'])), 
        axis=1
    )
    
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
    st.write("#### Matchup Data")
    
    try:
        # First try with styled dataframe and images
        styled_df = formatted_df.style.applymap(highlight_matchups, subset=['Matchup'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=600,
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
                    help="Favorable: ≥55%, Unfavorable: <45%, Even: 45-55%"
                )
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
            height=600,
            column_config={
                "Win %": st.column_config.NumberColumn(
                    "Win %",
                    format="%.1f%%",
                ),
            },
            hide_index=True
        )
    st.caption(f"Data based on the current compiled tournament data on [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET).")
    # Add explanation
    from formatters import format_deck_name
    formatted_deck_name = format_deck_name(deck_name)
