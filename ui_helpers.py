# ui_helpers.py
"""UI helper functions for TCG Deck Analyzer"""

import streamlit as st
from datetime import datetime
from formatters import format_deck_name, format_deck_option
from utils import calculate_time_ago
from scraper import get_deck_list
import cache_manager
from config import MIN_META_SHARE

def display_banner(img_path, max_width=800):
    """Display the app banner image"""
    from image_processor import get_base64_image
    
    img_base64 = get_base64_image(img_path)
    
    st.markdown(f"""
    <div style="display: flex; justify-content: center; width: 100%; margin-top:-2rem;">
        <img src="data:image/png;base64,{img_base64}" style="width: 100%; max-width: {max_width}px; height: auto;">
    </div>
    """, unsafe_allow_html=True)

def load_initial_data():
    """Load initial data required for the app"""
    # Show loading spinner
    with st.spinner("Loading app data..."):
        # Initialize caches
        cache_manager.init_caches()
        
        # Initialize deck list if not already loaded
        if 'deck_list' not in st.session_state:
            st.session_state.deck_list = get_deck_list()
            st.session_state.fetch_time = datetime.now()
        
        # Load or update tournament data
        performance_df, performance_timestamp = cache_manager.load_or_update_tournament_data()
        
        # Store in session state
        st.session_state.performance_data = performance_df
        st.session_state.performance_fetch_time = performance_timestamp
        
        # Initialize card usage data if not already loaded
        if 'card_usage_data' not in st.session_state:
            st.session_state.card_usage_data = cache_manager.aggregate_card_usage()
        
        # Initialize selected deck if not exists
        if 'selected_deck_index' not in st.session_state:
            st.session_state.selected_deck_index = None
            
        # Initialize deck_to_analyze if not exists
        if 'deck_to_analyze' not in st.session_state:
            st.session_state.deck_to_analyze = None

def create_deck_options():
    """Create deck options for dropdown from performance data or fallback to deck list"""
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        # Get top 30 decks from performance data
        top_performing_decks = st.session_state.performance_data.head(30)
        
        # Create dropdown options with the same format as sidebar
        deck_display_names = []
        deck_name_mapping = {}  # Maps display name to original name
        
        for _, deck in top_performing_decks.iterrows():
            power_index = round(deck['power_index'], 2)
            # Format: "Deck Name (Power Index)"
            display_name = f"{deck['displayed_name']} ({power_index})"
            deck_display_names.append(display_name)
            deck_name_mapping[display_name] = {
                'deck_name': deck['deck_name'],
                'set': deck['set']
            }
    else:
        # Fallback to original method if performance data isn't available
        popular_decks = st.session_state.deck_list[st.session_state.deck_list['share'] >= MIN_META_SHARE]
        
        # Create deck options with formatted names and store mapping
        deck_display_names = []
        deck_name_mapping = {}  # Maps display name to original name
        
        for _, row in popular_decks.iterrows():
            display_name = format_deck_option(row['deck_name'], row['share'])
            deck_display_names.append(display_name)
            deck_name_mapping[display_name] = {
                'deck_name': row['deck_name'],
                'set': row['set']
            }
    
    # Store mapping in session state
    st.session_state.deck_name_mapping = deck_name_mapping
    
    return deck_display_names, deck_name_mapping

def on_deck_change():
    """Handle deck dropdown selection change"""
    selection = st.session_state.deck_select
    if selection:
        st.session_state.selected_deck_index = st.session_state.deck_display_names.index(selection)
        
        # Set the deck to analyze
        deck_info = st.session_state.deck_name_mapping[selection]
        st.session_state.analyze = {
            'deck_name': deck_info['deck_name'],
            'set_name': deck_info['set'],
        }
    else:
        st.session_state.selected_deck_index = None

def create_deck_selector():
    """Create and display the deck selector dropdown"""
    # Get deck options
    deck_display_names, deck_name_mapping = create_deck_options()
    
    # Store for use in callback
    st.session_state.deck_display_names = deck_display_names
    
    # Calculate time ago
    time_str = calculate_time_ago(st.session_state.fetch_time)
    
    # Get current set from selected deck or default
    current_set = "-"  # Default
    if st.session_state.selected_deck_index is not None and st.session_state.selected_deck_index < len(deck_display_names):
        selected_deck_display = deck_display_names[st.session_state.selected_deck_index]
        deck_info = st.session_state.deck_name_mapping[selected_deck_display]
        current_set = deck_info['set'].upper()
    
    # Handle deck_to_analyze if set (e.g., from sidebar selection)
    if st.session_state.get('deck_to_analyze'):
        # Find the matching display name and index
        for i, display_name in enumerate(deck_display_names):
            deck_info = deck_name_mapping[display_name]
            if deck_info['deck_name'] == st.session_state.deck_to_analyze:
                st.session_state.selected_deck_index = i
                
                # Set the deck to analyze
                st.session_state.analyze = {
                    'deck_name': deck_info['deck_name'],
                    'set_name': deck_info['set'],
                }
                
                # Clear the deck_to_analyze for next time
                st.session_state.deck_to_analyze = None
                break
    
    # Create label and help text
    label_text = f"Current Set: {current_set}"
    help_text = f"Showing top performing decks. Updated {time_str}."
    
    # Display the selectbox
    selected_option = st.selectbox(
        label_text,
        deck_display_names,
        index=st.session_state.selected_deck_index,
        placeholder="Select a deck to analyze...",
        help=help_text,
        key="deck_select",
        on_change=on_deck_change
    )
    
    return selected_option

def render_deck_in_sidebar(deck, expanded=False):
    """Render a single deck in the sidebar"""
    # Format power index to 2 decimal places
    power_index = round(deck['power_index'], 2)
    
    # Create a plain text expander title with the power index
    with st.sidebar.expander(f"{deck['displayed_name']} ({power_index})", expanded=expanded):
        # Determine the color class based on power index
        power_class = "positive-index" if power_index > 0 else "negative-index"
        
        # Get sample deck data
        deck_name = deck['deck_name']
        sample_deck = cache_manager.get_or_load_sample_deck(deck_name, deck['set'])
        
        # Get and store energy types
        from energy_utils import store_energy_types, get_energy_types_for_deck, render_energy_icons
        
        raw_energy_types = sample_deck.get('energy_types', [])
        store_energy_types(deck_name, raw_energy_types)
        
        # Get energy types for display (from deck or archetype)
        energy_types, is_typical = get_energy_types_for_deck(deck_name, raw_energy_types)
        
        # Display energy types if available
        if energy_types:
            energy_html = render_energy_icons(energy_types, is_typical)
            st.markdown(energy_html, unsafe_allow_html=True)
        
        # Display performance stats with colored power index inside
        # st.markdown(f"""
        # <div style="margin-bottom: 10px; font-size: 0.9rem;">
        #     <p style="margin-bottom: 5px;">Power Index: <span class="{power_class}">{power_index}</span></p>
        #     <p style="margin-bottom: 5px;"><strong>Record:</strong> {deck['total_wins']}-{deck['total_losses']}-{deck['total_ties']}</p>
        #     <p style="margin-bottom: 5px;"><strong>Tournaments:</strong> {deck['tournaments_played']}</p>
        # </div>
        # """, unsafe_allow_html=True)
        
        # Render deck view
        from card_renderer import render_sidebar_deck
        deck_html = render_sidebar_deck(
            sample_deck['pokemon_cards'], 
            sample_deck['trainer_cards'],
            card_width=61
        )
        
        # Display the deck
        st.markdown(deck_html, unsafe_allow_html=True)

def render_sidebar():
    """Render the sidebar with tournament performance data"""
    st.sidebar.title("Top 10 Tournament Performance")
    
    # Initialize energy types
    from energy_utils import initialize_energy_types
    initialize_energy_types()
    
    # Display performance data if it exists
    if not st.session_state.performance_data.empty:
        # Add disclaimer with update time in one line
        performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
        st.sidebar.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-size: 0.85rem;">
            <div>Top win rates, past 7 days</div>
            <div>Updated {performance_time_str}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Get the top 10 performing decks
        top_decks = st.session_state.performance_data.head(10)
        
        # Render each deck one by one
        for idx, deck in top_decks.iterrows():
            render_deck_in_sidebar(deck)
        
        # Add a divider
        st.sidebar.markdown("<hr style='margin-top: 25px; margin-bottom: 15px; border: 0; border-top: 1px solid;'>", unsafe_allow_html=True)
        
        # Add expandable methodology section
        with st.sidebar.expander("🔍 About the Power Index"):
            st.markdown("""
            #### Power Index: How We Rank the Best Decks
            
            **Where the Data Comes From**  
            Our Power Index uses real tournament results from "Best Finishes" data of the past 7 days on [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET). This means we're looking at how decks actually perform in competitive play, not just how popular they are.
            
            **What the Power Index Measures**  
            The Power Index is calculated as:
            """)
            
            st.code("Power Index = (Wins + (0.75 × Ties) - Losses) ÷ √(Total Games)", language="")
            
            st.markdown("""
            This formula captures three key things:
            * How many more wins than losses a deck achieves
            * The value of ties (counted as 75% of a win)
            * Statistical confidence (more games = more reliable data)
            
            **Why It's Better Than Other Methods**
            * **Better than Win Rate**: Accounts for both winning and avoiding losses
            * **Better than Popularity**: Measures actual performance, not just what people choose to play
            * **Better than Record Alone**: Balances impressive results against sample size
            
            **Reading the Numbers**
            * **Higher is Better**: The higher the Power Index, the stronger the deck has proven itself
            * **Positive vs Negative**: Positive numbers mean winning more than losing
            * **Comparing Decks**: A deck with a Power Index of 2.0 is performing significantly better than one with 1.0
            
            The Power Index gives you a clear picture of which decks are actually winning tournaments, not just which ones everyone is playing.
            """)
    else:
        st.sidebar.info("No tournament performance data available")
