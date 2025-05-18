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
    """Display the Deck Template tab with added sample deck column"""
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
    
    # Create outer columns: Template (2) and Sample Deck (1)
    outer_col1, outer_col2 = st.columns([2, 1])
    
    with outer_col1:
        # Create header
        if energy_types:
            # Render energy icons for header
            energy_html = ""
            for energy in energy_types:
                energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
                energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:20px; margin-right:4px; vertical-align:middle;">'
            
            # Create header with energy types
            archetype_note = '<span style="font-size: 0.8rem; color: #888; margin-left: 4px;">(most common)</span>' if is_typical else ""
            core_cards_header = f"""#### Core Cards <span style="font-size: 1rem; font-weight: normal;">(Energy: {energy_html}{archetype_note})</span>"""
        else:
            # Just "Core Cards" if no energy found
            core_cards_header = "#### Core Cards"
        
        # Display the header
        st.write(core_cards_header, unsafe_allow_html=True)
        
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
    
    with outer_col2:
        # Get sample deck data
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
            
            # Render the sample deck (using the sidebar function, but in the main area)
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
    display_df['displayed_name'] = display_df.apply(
        lambda row: f"➡️ {row['displayed_name']}" if row['deck_name'] == current_deck_name else row['displayed_name'], 
        axis=1
    )
    
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
    
    final_df = display_df[display_cols.keys()].rename(columns=display_cols)
    
    # Create a list to mark which rows have the current deck
    is_current_row = [deck_name == current_deck_name for deck_name in display_df['deck_name']]
    
    # Define a styling function to highlight the full row
    def highlight_current_row(df, is_current_list):
        styles = []
        for i in range(len(df)):
            if is_current_list[i]:
                styles.append(['background-color: rgba(0, 160, 255, 0.15)'] * len(df.columns))
            else:
                styles.append([''] * len(df.columns))
        return styles
    
    # Apply styling
    styled_df = final_df.style.apply(lambda _: highlight_current_row(final_df, is_current_row), axis=None)
    
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
    if current_deck_name and current_deck_name in display_df['deck_name'].values:
        selected_deck_name = display_df[display_df['deck_name'] == current_deck_name]['displayed_name'].values[0]
        selected_name = selected_deck_name.replace('➡️ ', '')
        
        st.markdown(f"""
        <div style="background-color: rgba(0, 160, 255, 0.1); padding: 12px; border-radius: 5px; 
                    border-left: 4px solid #00A0FF; margin-top: 10px; margin-bottom: 20px;">
            <span style="font-weight: bold;">➡️ Currently analyzing:</span> {selected_name}
        </div>
        """, unsafe_allow_html=True)
    
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
