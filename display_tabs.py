# display_tabs.py
"""Functions for rendering the tabs in the main content area"""

import streamlit as st
from formatters import format_deck_name
from related_decks import find_related_decks
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
            <h1 style="margin: 0rem 0 0 0;"><img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 350px; height: auto; margin-bottom:0.2em; margin-right:0.5em;border-radius: 4px;">{format_deck_name(deck_info['deck_name'])}</h1>
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
    """Display the Deck Template tab with revised layout"""
    # Import needed functions
    from energy_utils import get_energy_types_for_deck, get_archetype_from_deck_name
    
    # Use the updated function that returns deck_info
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    # Initialize empty energy types list
    energy_types = []
    is_typical = False
    
    # Look for energy_types in the session state for this deck
    if 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', '')
        set_name = st.session_state.analyze.get('set_name', '')
        
        # Get the most common energy combination
        energy_types, is_typical = get_energy_types_for_deck(deck_name, [])
    
    # Create outer columns: Sample Deck (2) and Template (3) - switched order and ratio
    outer_col1, outer_col2 = st.columns([2, 3])
    
    # Left column: Sample Deck
    with outer_col1:
        st.write("### Sample Deck")
        
        if 'analyze' in st.session_state:
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
                    card_width=70  # Slightly larger than sidebar
                )
                st.markdown(deck_html, unsafe_allow_html=True)
            else:
                st.info("No sample deck available")
        else:
            st.info("Select a deck to view a sample")
    
    # Right column: Core Cards and Flexible Slots in vertical layout
    with outer_col2:
        # Create header
        st.write("### Deck Composition", unsafe_allow_html=True)
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
        
        # Pokemon cards section
        st.write("###### Pokémon")
        pokemon_grid = CardGrid(card_width=70, gap=4)
        pokemon_grid.add_cards_from_dict(deck_info['Pokemon'], repeat_by_count=True)
        pokemon_grid.display()
        
        # Trainer cards section
        st.write("###### Trainer")
        trainer_grid = CardGrid(card_width=70, gap=4)
        trainer_grid.add_cards_from_dict(deck_info['Trainer'], repeat_by_count=True)
        trainer_grid.display()
        
        # Flexible slots section
        remaining = 20 - total_cards
        st.write("<br>", unsafe_allow_html=True)
        st.write(f"##### Flexible Slots ({remaining} cards)", unsafe_allow_html=True)
        
        # Sort options by usage percentage (descending) and split by type
        pokemon_options = options[options['type'] == 'Pokemon'].sort_values(by='display_usage', ascending=False)
        trainer_options = options[options['type'] == 'Trainer'].sort_values(by='display_usage', ascending=False)
        
        # Pokemon options in vertical layout
        st.write("###### Pokémon Options")
        pokemon_options_grid = CardGrid(card_width=70, gap=4, show_percentage=True)
        pokemon_options_grid.add_cards_from_dataframe(pokemon_options)
        pokemon_options_grid.display()
        
        # Trainer options in vertical layout
        st.write("###### Trainer Options")
        trainer_options_grid = CardGrid(card_width=70, gap=4, show_percentage=True)
        trainer_options_grid.add_cards_from_dataframe(trainer_options)
        trainer_options_grid.display()

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
    st.subheader("Tournament Performance Data")
    import pandas as pd
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
    
    # Calculate win rate for easier understanding
    display_df['win_rate'] = round((display_df['total_wins'] / (display_df['total_wins'] + display_df['total_losses'] + display_df['total_ties'])) * 100, 1)
    
    # Format columns for display
    display_df['share'] = display_df['share'].round(2)
    display_df['power_index'] = display_df['power_index'].round(2)
    
    # Add an indicator emoji for the current deck
    # display_df['displayed_name'] = display_df.apply(
    #     lambda row: f"➡️ {row['displayed_name']}" if row['deck_name'] == current_deck_name else row['displayed_name'], 
    #     axis=1
    # )
    
    # Select and rename columns for display
    display_cols = {
        'displayed_name': 'Deck',
        'win_rate': 'Win %',
        'total_wins': 'Wins',
        'total_losses': 'Losses',
        'total_ties': 'Ties',
        'tournaments_played': 'Best Finish Entries',
        'share': 'Meta Share %',
        'power_index': 'Power Index'
    }
    
    # Create indicator for highlighting
    display_df['is_current'] = display_df['deck_name'] == current_deck_name
    
    # Create final display dataframe
    final_df = display_df[list(display_cols.keys())].rename(columns=display_cols)
    
    # Create a styling function that works with DataFrame.style
    def highlight_current_deck(df):
        # Create an empty styles DataFrame with same shape as input
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        
        # Find the rows where deck_name matches current_deck_name
        is_current = display_df['is_current']
        
        # Apply background color to all cells in the matching rows
        for col in styles.columns:
            styles.loc[is_current, col] = 'background-color: rgba(0, 208, 255, 0.15)'
            
        return styles
    
    # Apply styling
    styled_df = final_df.style.apply(highlight_current_deck, axis=None)
    
    # Display with styling
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=800,
        column_config={
            "Power Index": st.column_config.NumberColumn(format="%.2f"),
            "Win %": st.column_config.NumberColumn(format="%.1f%%"),
            "Meta Share %": st.column_config.NumberColumn(format="%.2f%%")
        },
        hide_index=True
    )
    
    # Show note about current deck if one is selected
    # if current_deck_name and current_deck_name in display_df['deck_name'].values:
    #     selected_deck_name = display_df[display_df['deck_name'] == current_deck_name]['displayed_name'].values[0]
    #     selected_name = selected_deck_name.replace('➡️ ', '')
        
    #     st.markdown(f"""
    #     <div style="background-color: rgba(0, 160, 255, 0.1); padding: 12px; border-radius: 5px; 
    #                 border-left: 4px solid #00A0FF; margin-top: 10px; margin-bottom: 20px;">
    #         <span style="font-weight: bold;">➡️ Currently analyzing:</span> {selected_name}
    #     </div>
    #     """, unsafe_allow_html=True)
    
    # Add explanation
    from datetime import datetime
    current_month_year = datetime.now().strftime("%B %Y")
    
    st.markdown(f"""
    ### Understanding the Metrics
    
    **Win %**: Percentage of matches won out of total matches played.
    
    **Wins, Losses, Ties**: Total wins, losses, and ties from all recorded matches.
    
    **Best Finish Entries**: Number of tournament entries in the "Best Finishes" section.
    
    **Meta Share %**: Percentage representation of this deck in the competitive metagame.
    
    **Power Index**: Our key performance metric calculated as (Wins + 0.75×Ties - Losses) ÷ √(Total Games). Higher values indicate stronger performance.
    
    ---
    
    *Data is based on tournament results from {current_month_year} on Limitless TCG.*
    """)
    
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

# Modify the display_related_decks_tab function in display_tabs.py:

# Updated display_related_decks_tab function for display_tabs.py

def display_related_decks_tab(deck_info, results):
    """Display the Related Decks tab with header images"""
    st.subheader("Related Decks")
    
    # Get the current deck name
    current_deck_name = deck_info['deck_name']
    
    # Make sure we have the deck name mapping from the dropdown
    if 'deck_name_mapping' in st.session_state:
        # Find related decks from the deck selection dropdown list
        related_decks = find_related_decks(current_deck_name, st.session_state.deck_name_mapping)
        
        if related_decks.empty:
            st.info("No related decks found in the current meta.")
        else:
            # Display related decks in a card-like format
            st.write("Decks sharing Pokémon with this archetype:")
            
            # Create a 3-column layout
            cols = st.columns(3)
            
            # Display each related deck
            for i, (_, deck) in enumerate(related_decks.iterrows()):
                col_idx = i % 3
                
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
                    
                    # Create card with integrated button
                    with st.container():
                        # Card container with image at top
                        st.markdown(f"""
                        <div style="border: 1px solid #ddd; border-radius: 5px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                        """, unsafe_allow_html=True)
                        
                        # Add image at top of card
                        if header_image:
                            st.markdown(f"""
                            <div style="width: 100%; height: 70px; overflow: hidden; border-radius: 4px 4px 0 0;">
                                <img src="data:image/png;base64,{header_image}" style="width: 100%; object-fit: cover;">
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="width: 100%; height: 70px; background-color: #f0f0f0; border-radius: 4px 4px 0 0; display: flex; align-items: center; justify-content: center;">
                                <span style="color: #888;">No image</span>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Add deck info
                        st.markdown(f"""
                            <div style="padding: 10px;">
                                <h4 style="margin: 0 0 5px 0; font-size: 16px;">{formatted_name}</h4>
                                <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">Meta share: {deck.get('share', 0):.2f}%</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add button below card
                        if st.button(f"Analyze", key=f"btn_{deck['deck_name']}"):
                            # Set this deck to be analyzed
                            st.session_state.deck_to_analyze = deck['deck_name']
                            # Force rerun to trigger the analysis
                            st.rerun()
    else:
        st.info("Deck list not available. Unable to find related decks.")
