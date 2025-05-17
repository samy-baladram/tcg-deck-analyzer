# display_tabs.py
"""Functions for rendering the tabs in the main content area"""

import streamlit as st
from formatters import format_deck_name
from image_processor import create_deck_header_images
from visualizations import create_usage_bar_chart, display_chart, create_variant_bar_chart
from analyzer import build_deck_template
from card_renderer import render_deck_section, render_option_section
from energy_utils import get_archetype_from_deck_name, render_energy_icons

def display_deck_header(deck_info, results):
    """Display the deck header with image"""
    header_image = create_deck_header_images(deck_info, results)
    
    if header_image:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: flex-start; margin-bottom: 0rem; margin-top:-1rem">
            <h1 style="margin: 0rem 0 0 0;"><img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 200px; height: auto; margin-bottom:0.2em; margin-right:0.5em;border-radius: 4px;">{format_deck_name(deck_info['deck_name'])}</h1>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.header(format_deck_name(deck_info['deck_name']))

def display_card_usage_tab(results, total_decks, variant_df):
    """Display the Card Usage tab"""
    # Create two columns for Pokemon and Trainer
    st.write("#### Card Usage & Variants")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write("##### Pokemon")
        type_cards = results[results['type'] == 'Pokemon']
        
        if not type_cards.empty:
            fig = create_usage_bar_chart(type_cards, 'Pokemon')
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
                    
                    # # Create the 2-column layout
                    var_col1, var_col2 = st.columns([2, 5])
                    
                    # Column 1: Both Variants side by side
                    with var_col1:
                        variant_html = render_variant_cards(var1_set, var1_num, var2_set, var2_num, var1, var2)
                        st.markdown(variant_html, unsafe_allow_html=True)
                    
                    # Column 2: Bar Chart
                    with var_col2:
                        # Create variant bar chart with fixed height
                        fig_var = create_variant_bar_chart(row)
                        display_chart(fig_var) 
    
    with col2:
        st.write("##### Trainer")
        type_cards = results[results['type'] == 'Trainer']
        
        if not type_cards.empty:
            fig = create_usage_bar_chart(type_cards, 'Trainer')
            display_chart(fig)
        else:
            st.info("No Trainer cards found")

def display_deck_template_tab(results):
    """Display the Deck Template tab"""
    
    # Use the updated function that returns deck_info
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    # Initialize empty energy types list
    energy_types = []
    is_typical = False
    
    # Look for energy_types in the session state for this deck
    if 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', '')
        archetype = get_archetype_from_deck_name(deck_name)
        
        # Try to get energy from session state archetype mapping
        if hasattr(st.session_state, 'archetype_energy_types') and archetype in st.session_state.archetype_energy_types:
            energy_types = list(st.session_state.archetype_energy_types[archetype])
            is_typical = True
    
    # Create header
    if energy_types:
        # Render energy icons for header
        energy_html = ""
        for energy in energy_types:
            energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
            energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:20px; margin-right:4px; vertical-align:middle;">'
        
        # Create header with energy types
        archetype_note = '<span style="font-size: 0.8rem; color: #888; margin-left: 4px;">(typical)</span>' if is_typical else ""
        core_cards_header = f"""#### Core Cards <span style="font-size: 1rem; font-weight: normal;">(Energy: {energy_html}{archetype_note})</span>"""
    else:
        # Just "Core Cards" if no energy found
        core_cards_header = "#### Core Cards"
    
    # Display the header
    st.write(core_cards_header, unsafe_allow_html=True)
    
    # Rest of the function...
    # Display cards in columns
    col1, col2 = st.columns([2, 3])
    
    with col1:
        # Render Pokemon cards
        render_deck_section(deck_info['Pokemon'], "Pokemon")
    
    with col2:
        # Render Trainer cards
        render_deck_section(deck_info['Trainer'], "Trainer")
    
    # Display flexible slots section
    remaining = 20 - total_cards
    st.write("<br>", unsafe_allow_html=True)
    st.write(f"#### Flexible Slots ({remaining} cards)", unsafe_allow_html=True)
    
    # Sort options by usage percentage (descending) and split by type
    pokemon_options = options[options['type'] == 'Pokemon'].sort_values(by='display_usage', ascending=False)
    trainer_options = options[options['type'] == 'Trainer'].sort_values(by='display_usage', ascending=False)
    
    # Create two columns for flexible slots
    flex_col1, flex_col2 = st.columns([2, 3])
    
    with flex_col1:
        # Render Pokemon options
        render_option_section(pokemon_options, "Pokémon Options")
    
    with flex_col2:
        # Render Trainer options
        render_option_section(trainer_options, "Trainer Options")

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
    """Display the Metagame Overview tab"""
    st.subheader("Metagame Overview")
    st.write("Most played cards across top decks:")
    
    # Filter and display top cards
    pokemon_cards = st.session_state.card_usage_data[st.session_state.card_usage_data['type'] == 'Pokemon'].head(20)
    trainer_cards = st.session_state.card_usage_data[st.session_state.card_usage_data['type'] == 'Trainer'].head(20)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("#### Top Pokémon")
        st.dataframe(pokemon_cards[['card_name', 'weighted_usage', 'deck_count']], use_container_width=True)
    
    with col2:
        st.write("#### Top Trainers")
        st.dataframe(trainer_cards[['card_name', 'weighted_usage', 'deck_count']], use_container_width=True)

# Add this to display_tabs.py - Add a new tab for energy debugging

# In display_tabs.py (add this new function)
def display_energy_debug_tab(deck_info):
    """Display the Energy Debug tab with detailed analysis"""
    from energy_utils import get_archetype_from_deck_name, display_detailed_energy_table
    
    st.write("### Energy Type Analysis")
    
    deck_name = deck_info['deck_name']
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Add explanatory text
    st.write(f"""
    This tab provides detailed analysis of energy types found in the "{archetype}" archetype decks.
    It shows which energy types are present in each sample deck and summarizes the most common combinations.
    """)
    
    # Add energy visualization table (using the function we created earlier)
    st.markdown(display_detailed_energy_table(deck_name), unsafe_allow_html=True)
    
    # Raw data expander
    with st.expander("Raw Energy Storage Data", expanded=False):
        # Show all stored energy data for this archetype
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("##### All Energy Types")
            if 'archetype_energy_types' in st.session_state and archetype in st.session_state.archetype_energy_types:
                st.write(f"Archetype: {archetype}")
                st.write(f"Energy Types: {sorted(list(st.session_state.archetype_energy_types[archetype]))}")
            else:
                st.write("No stored energy types data")
                
            st.write("##### First Energy Combo")
            if 'archetype_first_energy_combo' in st.session_state and archetype in st.session_state.archetype_first_energy_combo:
                st.write(f"Archetype: {archetype}")
                st.write(f"First Combo: {st.session_state.archetype_first_energy_combo[archetype]}")
            else:
                st.write("No first energy combo data")
        
        with col2:
            st.write("##### Energy Combinations")
            if 'archetype_energy_combos' in st.session_state and archetype in st.session_state.archetype_energy_combos:
                combos = st.session_state.archetype_energy_combos[archetype]
                if combos:
                    # Convert to more readable format
                    combo_data = [{"Combination": ", ".join(combo), "Count": count} 
                                  for combo, count in sorted(combos.items(), key=lambda x: x[1], reverse=True)]
                    st.dataframe(combo_data)
                else:
                    st.write("No energy combination data")
            else:
                st.write("No energy combination data")
                
    # Add a utility section to help with debugging
    with st.expander("Energy Debugging Utilities", expanded=False):
        st.write("##### Force Refresh Energy Data")
        if st.button("Reload Energy Data"):
            # This will force re-analysis of the deck's energy types
            if 'analyzed_deck_cache' in st.session_state:
                # Remove cached analysis for this deck
                cache_key = f"full_deck_{deck_info['deck_name']}_{deck_info['set_name']}"
                if cache_key in st.session_state.analyzed_deck_cache:
                    del st.session_state.analyzed_deck_cache[cache_key]
                    st.success(f"Removed cached analysis for {deck_info['deck_name']}. Refresh the page to reanalyze.")
