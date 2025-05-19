# ui_helpers.py
"""UI helper functions for TCG Deck Analyzer"""

import streamlit as st
from datetime import datetime
from formatters import format_deck_name, format_deck_option
from utils import calculate_time_ago
from scraper import get_deck_list
import cache_manager
from config import MIN_META_SHARE, TOURNAMENT_COUNT
import pandas as pd
import base64
import os

ENERGY_CACHE_FILE = "cached_data/energy_types.json"

# Replace the existing get_energy_types_for_deck function with this one
def get_energy_types_for_deck(deck_name, deck_energy_types=None):
    """
    Get energy types for a deck, using dedicated energy cache
    
    Args:
        deck_name: The name of the deck
        deck_energy_types: Optional energy types to use instead of cache
        
    Returns:
        Tuple of (energy_types, is_typical) - energy_types is the most common combination
    """
    # If specific energy types provided, use them
    if deck_energy_types:
        return deck_energy_types, False
    
    # Get from dedicated energy cache
    import cache_manager
    set_name = "A3"  # Default set
    
    # If we're in analyze context, get the proper set name
    if 'analyze' in st.session_state:
        set_name = st.session_state.analyze.get('set_name', 'A3')
    
    # Ensure energy cache is initialized
    cache_manager.ensure_energy_cache()
    
    # Get from dedicated cache
    energy_types = cache_manager.get_cached_energy(deck_name, set_name)
    
    if energy_types:
        return energy_types, True
    
    # If no energy found in cache, try to force a new calculation
    # First ensure deck is collected
    cache_manager.ensure_deck_collected(deck_name, set_name)
    
    # Then recalculate 
    energy_types = cache_manager.calculate_and_cache_energy(deck_name, set_name)
    
    if energy_types:
        return energy_types, True
    
    # Fallback: Empty list
    return [], False

def render_energy_icons(energy_types, is_typical=False):
    """
    Generate HTML for energy icons
    
    Args:
        energy_types: List of energy type strings
        is_typical: Whether this is the typical/most common combination
        
    Returns:
        HTML string for displaying energy icons
    """
    if not energy_types:
        return ""
        
    energy_html = ""
    # Create image tags for each energy type
    for energy in energy_types:
        # Direct URL to the energy icon
        energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
        energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:20px; margin-right:4px; vertical-align:middle;">'
    
    # Add note if these are typical energy types
    archetype_note = ''
    
    energy_display = f"""<div style="margin-bottom: 10px;">
        <p style="margin-bottom:5px;"><strong>Energy:</strong> {energy_html} {archetype_note}</p>
    </div>"""
    return energy_display

# def initialize_energy_cache():
#     """Initialize energy combinations cache from disk if available"""
#     if 'energy_combinations' not in st.session_state:
#         st.session_state.energy_combinations = {}
        
#         # Try to load from disk
#         try:
#             import json
#             import os
#             if os.path.exists(ENERGY_CACHE_FILE):
#                 with open(ENERGY_CACHE_FILE, 'r') as f:
#                     data = json.load(f)
                
#                 # Load energy combinations statistics
#                 combo_data = data.get('archetype_energy_combos', {})
                
#                 # Convert string keys to tuples
#                 for archetype, combos in combo_data.items():
#                     st.session_state.energy_combinations[archetype] = {
#                         tuple(sorted(combo.split(','))): count 
#                         for combo, count in combos.items()
#                     }
#         except Exception as e:
#             print(f"Error loading energy types from disk: {e}")
            
def display_banner(img_path, max_width=900):
    """Display the app banner image"""
    from image_processor import get_base64_image
    
    img_base64 = get_base64_image(img_path)
    
    st.markdown(f"""<div style="display: flex; justify-content: center; width: 100%; margin-top:-68px; margin-bottom:5px;">
        <img src="data:image/png;base64,{img_base64}" style="width: 100%; max-width: {max_width}px; height: auto;">
    </div>
    """, unsafe_allow_html=True)

def load_initial_data():
    """Load initial data required for the app"""
    # Initialize caches - this now handles comprehensive updates
    cache_manager.init_caches()
    
    # Initialize deck list if not already loaded
    if 'deck_list' not in st.session_state:
        st.session_state.deck_list = get_deck_list()
        st.session_state.fetch_time = datetime.now()
    
    # Get the performance data from session state (already loaded by init_caches)
    if 'performance_data' not in st.session_state:
        # Only load if not already in session state
        performance_df, performance_timestamp = cache_manager.load_or_update_tournament_data()
        st.session_state.performance_data = performance_df
        st.session_state.performance_fetch_time = performance_timestamp
    
    # Initialize card usage data if not already loaded (similar approach)
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
        
        # Track player-tournament mapping for this deck to enable efficient updates
        cache_manager.track_player_tournament_mapping(
            deck_info['deck_name'], 
            deck_info['set']
        )
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

# In ui_helpers.py - Updated render_deck_in_sidebar function
def render_deck_in_sidebar(deck, expanded=False, rank=None):
    """Render a single deck in the sidebar"""
    # Format power index to 2 decimal places
    power_index = round(deck['power_index'], 2)
    
    # Unicode circled numbers: ①②③④⑤⑥⑦⑧⑨⑩⓪
    circled_numbers = ["⓪", "🥇", "🥈", "🥉", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
    
    # Get the appropriate circled number based on rank
    if rank is not None and 0 <= rank <= 10:
        rank_symbol = circled_numbers[rank]
    else:
        rank_symbol = ""
    
    # Create a plain text expander title with the rank and power index
    with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']} ({power_index})", expanded=expanded):
        # Get sample deck data
        deck_name = deck['deck_name']
        sample_deck = cache_manager.get_or_load_sample_deck(deck_name, deck['set'])
        
        # Get energy types from dedicated cache
        energy_types, is_typical = get_energy_types_for_deck(deck_name)
        
        # Display energy types if available
        if energy_types:
            energy_html = render_energy_icons(energy_types, is_typical)
            st.markdown(energy_html, unsafe_allow_html=True)
        
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
    with st.sidebar:
        # Load and encode the banner image if it exists
        banner_path = "sidebar_banner.png"
        if os.path.exists(banner_path):
            with open(banner_path, "rb") as f:
                banner_base64 = base64.b64encode(f.read()).decode()
            st.markdown(f"""
            <div style="width:100%; text-align:center; margin:-20px 0 5px 0;">
                <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px; margin-bottom:10px;">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.title("Top 10 Meta Decks")
        
        # Create progress bar and status message placeholders
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Initialize progress bar
        progress_bar = progress_placeholder.progress(0)
        status_placeholder.text("Loading meta data...")
        
        # Stage 1: Initialize energy cache (10%)
        import cache_manager
        cache_manager.ensure_energy_cache()
        progress_bar.progress(10)
        status_placeholder.text("Preparing deck data...")
        
        # Get current month and year for display
        from datetime import datetime
        current_month_year = datetime.now().strftime("%B %Y")  # Format: May 2025
        
        # Stage 2: Check performance data (20%)
        if st.session_state.performance_data.empty:
            progress_bar.progress(100)
            status_placeholder.empty()
            progress_placeholder.empty()
            st.info(f"No tournament performance data available for {current_month_year}")
            return
        
        # Update progress
        progress_bar.progress(20)
        status_placeholder.text("Processing top decks...")
        
        # Stage 3: Get top decks (30%)
        top_decks = st.session_state.performance_data.head(10)
        progress_bar.progress(30)
        status_placeholder.text("Loading deck data...")
        
        # Stage 4: Pre-load deck data (40%)
        # This helps ensure smooth rendering of each deck
        progress_bar.progress(40)
        
        # Stage 5: Render each deck (40% to 90%)
        # 5% progress per deck
        for idx, deck in top_decks.iterrows():
            rank = idx + 1
            current_progress = 40 + (idx * 5)
            progress_bar.progress(current_progress)
            status_placeholder.text(f"Loading deck {rank}/10: {deck['displayed_name']}")
            
            # Render the deck
            render_deck_in_sidebar(deck, rank=rank)
        
        # Stage 6: Finishing up (100%)
        progress_bar.progress(100)
        status_placeholder.empty()
        progress_placeholder.empty()
        
        # Add disclaimer with update time in one line
        performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0px; font-size: 0.85rem;">
            <div>Top performers from {current_month_year}</div>
            <div>Updated {performance_time_str}</div>
        </div>
        <div style="font-size: 0.75rem; margin-bottom: 5px; color: #777;">
            Based on up to {TOURNAMENT_COUNT} tournament results
        </div>
        """, unsafe_allow_html=True)
        
        # Add a divider
        st.markdown("<hr style='margin-top: 25px; margin-bottom: 15px; border: 0; border-top: 1px solid;'>", unsafe_allow_html=True)
        
        # Add expandable methodology section
        with st.expander("🔍 About the Power Index"):
            st.markdown(f"""
            #### Power Index: How We Rank the Best Decks
            
            **Where the Data Comes From**  
            Our Power Index uses the most recent community tournament results from the current month ({current_month_year}) on [Limitless TCG](https://play.limitlesstcg.com/tournaments/completed). This shows how decks actually perform in the most recent competitive play, not just how popular they are.
            
            **What the Power Index Measures**  
            The Power Index is calculated as:
            """)
            
            st.code("Power Index = (Wins + (0.75 × Ties) - Losses) / √(Total Games)", language="")
            
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
            """)
            
        # Add cache statistics at the bottom
        with st.expander("🔧 Cache Statistics", expanded=False):
            cache_stats = cache_manager.get_cache_statistics()
            st.markdown(f"""
            - **Decks Cached**: {cache_stats['decks_cached']}
            - **Sample Decks**: {cache_stats['sample_decks_cached']}
            - **Tournaments Tracked**: {cache_stats['tournaments_tracked']}
            - **Last Updated**: {cache_stats['last_update']}
            """)
            
        # Add update buttons
        st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Force Update Data", help="Force refresh all tournament data"):
                with st.spinner("Updating tournament data..."):
                    stats = cache_manager.update_all_caches()
                    st.success(f"Updated {stats['updated_decks']} decks from {stats['new_tournaments']} new tournaments")
                    # Instead add a button that says "Apply Updates":
                    if st.button("Apply Updates"):
                        st.rerun()
        
        with col2:
            if st.button("📊 Update Card Stats", help="Refresh card usage statistics"):
                with st.spinner("Updating card statistics..."):
                    cache_manager.aggregate_card_usage(force_update=True)
                    st.success("Card statistics updated")
                    # Instead add a button that says "Apply Updates":
                    if st.button("Apply Updates"):
                        st.rerun()
        
def display_deck_update_info(deck_name, set_name):
    """Display when the deck was last updated"""
    import os
    from cache_utils import ANALYZED_DECKS_DIR
    
    # Create a safe filename base
    safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
    base_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}_{set_name}")
    timestamp_path = f"{base_path}_timestamp.txt"
    
    if os.path.exists(timestamp_path):
        with open(timestamp_path, 'r') as f:
            timestamp_str = f.read().strip()
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                time_ago = calculate_time_ago(timestamp)
                return f"Last updated: {time_ago}"
            except:
                pass
    return None

def update_energy_cache(deck_name, energy_types):
    """
    Update the energy combinations cache for a deck
    
    Args:
        deck_name: The name of the deck
        energy_types: List of energy types
    """
    if not energy_types:
        return
        
    # Initialize if needed
    if 'energy_combinations' not in st.session_state:
        st.session_state.energy_combinations = {}
    
    # Initialize deck entry if needed
    if deck_name not in st.session_state.energy_combinations:
        st.session_state.energy_combinations[deck_name] = {}
    
    # Create a tuple from sorted energy types for consistency
    combo_key = tuple(sorted(energy_types))
    
    # Increment count for this combination
    if combo_key in st.session_state.energy_combinations[deck_name]:
        st.session_state.energy_combinations[deck_name][combo_key] += 1
    else:
        st.session_state.energy_combinations[deck_name][combo_key] = 1


# Add these new functions to ui_helpers.py

def load_initial_data(minimal=False):
    """
    Load initial data required for the app
    
    Args:
        minimal: If True, only load essential data needed for the main interface
    """
    # Initialize caches
    cache_manager.init_caches()
    
    # Initialize deck list if not already loaded - needed for basic UI
    if 'deck_list' not in st.session_state:
        st.session_state.deck_list = get_deck_list()
        st.session_state.fetch_time = datetime.now()
    
    # Load performance data if not already and not minimal
    if 'performance_data' not in st.session_state and not minimal:
        # Only load if not already in session state
        performance_df, performance_timestamp = cache_manager.load_or_update_tournament_data()
        st.session_state.performance_data = performance_df
        st.session_state.performance_fetch_time = performance_timestamp
    
    # For minimal load, we can skip the rest
    if minimal:
        return
        
    # Initialize card usage data if not already loaded
    if 'card_usage_data' not in st.session_state:
        st.session_state.card_usage_data = cache_manager.aggregate_card_usage()
    
    # Initialize selected deck if not exists
    if 'selected_deck_index' not in st.session_state:
        st.session_state.selected_deck_index = None
        
    # Initialize deck_to_analyze if not exists
    if 'deck_to_analyze' not in st.session_state:
        st.session_state.deck_to_analyze = None
        
    # Preload Pokemon data
    from image_processor import preload_all_deck_pokemon_info
    preload_all_deck_pokemon_info()

def load_sidebar_progressively(progress_bar, status_text):
    """Load sidebar data with incremental progress updates"""
    # Get current month and year for display
    from datetime import datetime
    current_month_year = datetime.now().strftime("%B %Y")
    
    # Stage 1: Ensure energy cache (10%)
    import cache_manager
    cache_manager.ensure_energy_cache()
    progress_bar.progress(10)
    status_text.text("Preparing deck data...")
    
    # Stage 2: Load performance data if needed (20%)
    if 'performance_data' not in st.session_state or st.session_state.performance_data.empty:
        # Load performance data
        performance_df, performance_timestamp = cache_manager.load_or_update_tournament_data()
        st.session_state.performance_data = performance_df
        st.session_state.performance_fetch_time = performance_timestamp
    
    progress_bar.progress(20)
    
    # Exit if no performance data
    if 'performance_data' not in st.session_state or st.session_state.performance_data.empty:
        progress_bar.progress(100)
        status_text.empty()
        st.info(f"No tournament performance data available for {current_month_year}")
        return
    
    # Stage 3: Get top decks (30%)
    status_text.text("Processing top decks...")
    top_decks = st.session_state.performance_data.head(10)
    progress_bar.progress(30)
    status_text.text("Loading deck data...")
    
    # Stage 4: Preload deck data (40%)
    # This is a placeholder for any preloading steps
    progress_bar.progress(40)
    
    # Stage 5: Render each deck (40% to 90%)
    # 5% progress per deck
    for idx, deck in enumerate(top_decks.iterrows()):
        _, deck_data = deck  # Unpack the tuple
        rank = idx + 1
        current_progress = 40 + (idx * 5)
        progress_bar.progress(current_progress)
        status_text.text(f"Loading deck {rank}/10: {deck_data['displayed_name']}")
        
        # Render the deck
        render_deck_in_sidebar(deck_data, rank=rank)
    
    # Stage 6: Finishing touches (100%)
    progress_bar.progress(95)
    status_text.text("Completing sidebar...")
    
    # Add disclaimer with update time
    performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0px; font-size: 0.85rem;">
        <div>Top performers from {current_month_year}</div>
        <div>Updated {performance_time_str}</div>
    </div>
    <div style="font-size: 0.75rem; margin-bottom: 5px; color: #777;">
        Based on up to {TOURNAMENT_COUNT} tournament results
    </div>
    """, unsafe_allow_html=True)
    
    # Add a divider
    st.markdown("<hr style='margin-top: 25px; margin-bottom: 15px; border: 0; border-top: 1px solid;'>", unsafe_allow_html=True)
    
    # Add expandable methodology section
    with st.expander("🔍 About the Power Index"):
        # Power Index content (same as before)
        st.markdown(f"... (Power Index content)")
    
    # Add cache statistics at the bottom
    with st.expander("🔧 Cache Statistics", expanded=False):
        cache_stats = cache_manager.get_cache_statistics()
        st.markdown(f"... (Cache stats content)")
    
    # Add update buttons
    st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # Force update button (same as before)
        st.button("🔄 Force Update Data", help="Force refresh all tournament data")
    
    with col2:
        # Update card stats button (same as before)
        st.button("📊 Update Card Stats", help="Refresh card usage statistics")
    
    # Final progress update
    progress_bar.progress(100)
    status_text.empty()

def render_loaded_sidebar():
    """Render the fully loaded sidebar (no progress indicators)"""
    # Get current month and year for display
    from datetime import datetime
    current_month_year = datetime.now().strftime("%B %Y")
    
    with st.sidebar:
        # Show banner or title
        banner_path = "sidebar_banner.png"
        if os.path.exists(banner_path):
            with open(banner_path, "rb") as f:
                banner_base64 = base64.b64encode(f.read()).decode()
            st.markdown(f"""
            <div style="width:100%; text-align:center; margin:-20px 0 5px 0;">
                <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px; margin-bottom:10px;">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.title("Top 10 Meta Decks")
        
        # Display top decks
        if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
            top_decks = st.session_state.performance_data.head(10)
            
            # Render each deck
            for idx, deck in top_decks.iterrows():
                rank = idx + 1
                render_deck_in_sidebar(deck, rank=rank)
            
            # Add disclaimer with update time
            performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0px; font-size: 0.85rem;">
                <div>Top performers from {current_month_year}</div>
                <div>Updated {performance_time_str}</div>
            </div>
            <div style="font-size: 0.75rem; margin-bottom: 5px; color: #777;">
                Based on up to {TOURNAMENT_COUNT} tournament results
            </div>
            """, unsafe_allow_html=True)
            
            # Add a divider
            st.markdown("<hr style='margin-top: 25px; margin-bottom: 15px; border: 0; border-top: 1px solid;'>", unsafe_allow_html=True)
            
            # Add expandable methodology section
            with st.expander("🔍 About the Power Index"):
                # Power Index content (same as before)
                st.markdown(f"... (Power Index content)")
            
            # Add cache statistics
            with st.expander("🔧 Cache Statistics", expanded=False):
                cache_stats = cache_manager.get_cache_statistics()
                st.markdown(f"... (Cache stats content)")
            
            # Add update buttons
            st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                # Force update button (same as before)
                st.button("🔄 Force Update Data", help="Force refresh all tournament data")
            
            with col2:
                # Update card stats button (same as before)
                st.button("📊 Update Card Stats", help="Refresh card usage statistics")
        else:
            st.info(f"No tournament performance data available for {current_month_year}")
