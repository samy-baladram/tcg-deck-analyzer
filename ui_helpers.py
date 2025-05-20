# ui_helpers.py
"""UI helper functions for TCG Deck Analyzer"""
import time
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

# Add this at the top level (outside any function) in ui_helpers.py
# Add this at the top level of ui_helpers.py
# Add this at the top of ui_helpers.py if not already there
import threading
from datetime import datetime, timedelta
from config import CACHE_TTL

def check_and_update_tournament_data():
    """Check if tournament data needs updating and start background update if needed"""
    # Initialize last update time if not set
    if 'performance_fetch_time' not in st.session_state:
        # Set to current time to prevent immediate update on first load
        st.session_state.performance_fetch_time = datetime.now()
    
    # Calculate time until next update
    current_time = datetime.now()
    time_since_update = current_time - st.session_state.performance_fetch_time
    seconds_remaining = max(0, CACHE_TTL - time_since_update.total_seconds())
    
    # Display time until next update
    #st.text(f"Next update in: {int(seconds_remaining)} seconds")
    
    # Add a manual update button for testing
    # if st.sidebar.button("Force Update Now"):
    #     perform_update()
    #     return
    
    # Only proceed with automatic update if data is stale and not currently updating
    update_running = st.session_state.get('update_running', False)
    
    # Uncomment this for production to enable automatic updates
    # For initial testing, rely only on the manual button

    if (not update_running and seconds_remaining <= 0):
        perform_update()

    
def perform_update():
    """Perform the actual update"""
    with st.sidebar:
        with st.spinner("Updating data..."):
            try:
                # Set update flag
                st.session_state.update_running = True
                
                # Perform update
                performance_df, performance_timestamp = cache_manager.load_or_update_tournament_data(force_update=True)
                
                # Update session state with CURRENT time
                st.session_state.performance_fetch_time = datetime.now()
                st.session_state.performance_data = performance_df
                
                # Update card usage data
                card_usage_df = cache_manager.aggregate_card_usage()
                st.session_state.card_usage_data = card_usage_df
                
                # Success message
                st.success("✅ Data updated successfully!")
                
                # Trigger page refresh after a brief pause
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"Update error: {str(e)}")
                print(f"Update error: {e}")
            finally:
                # Always reset flag
                st.session_state.update_running = False
            
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
    """Load only essential initial data for fast app startup"""
    # Initialize session state variables
    if 'selected_deck_index' not in st.session_state:
        st.session_state.selected_deck_index = None
        
    if 'deck_to_analyze' not in st.session_state:
        st.session_state.deck_to_analyze = None
    
    # Initialize minimal caches first
    cache_manager.init_caches()
    
    # Initialize deck list if not already loaded
    if 'deck_list' not in st.session_state:
        st.session_state.deck_list = get_deck_list()
        st.session_state.fetch_time = datetime.now()

def create_deck_options():
    """Create deck options for dropdown from performance data or fallback to deck list"""
    # Initialize deck display names and mapping
    deck_display_names = []
    deck_name_mapping = {}
    
    # First try to use performance data
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        # Get top 30 decks from performance data
        top_performing_decks = st.session_state.performance_data.head(30)
        
        for _, deck in top_performing_decks.iterrows():
            power_index = round(deck['power_index'], 2)
            # Format: "Deck Name (Power Index)"
            display_name = f"{deck['displayed_name']} ({power_index})"
            deck_display_names.append(display_name)
            deck_name_mapping[display_name] = {
                'deck_name': deck['deck_name'],
                'set': deck['set']
            }
    # If no performance data, use deck list
    else:
        # Ensure deck_list exists in session state
        if 'deck_list' not in st.session_state:
            # Load deck list with spinner
            with st.spinner("Loading deck list..."):
                from scraper import get_deck_list
                st.session_state.deck_list = get_deck_list()
                st.session_state.fetch_time = datetime.now()
                
        # Now we're sure deck_list exists, use it
        try:
            from config import MIN_META_SHARE
            popular_decks = st.session_state.deck_list[st.session_state.deck_list['share'] >= MIN_META_SHARE]
            
            for _, row in popular_decks.iterrows():
                display_name = format_deck_option(row['deck_name'], row['share'])
                deck_display_names.append(display_name)
                deck_name_mapping[display_name] = {
                    'deck_name': row['deck_name'],
                    'set': row['set']
                }
        except Exception as e:
            # If anything goes wrong, provide default options
            print(f"Error creating deck options: {e}")
            display_name = "Example Deck (1.0)"
            deck_display_names.append(display_name)
            deck_name_mapping[display_name] = {
                'deck_name': 'example-deck',
                'set': 'A3'
            }
    
    # Store mapping in session state
    st.session_state.deck_name_mapping = deck_name_mapping
    
    return deck_display_names, deck_name_mapping

def on_deck_change():
    """Handle deck dropdown selection change"""
    if 'deck_select' not in st.session_state:
        return
        
    selection = st.session_state.deck_select
    if selection:
        if 'deck_display_names' not in st.session_state:
            # Skip if deck_display_names not loaded yet
            return
            
        st.session_state.selected_deck_index = st.session_state.deck_display_names.index(selection)
        
        # Set the deck to analyze
        if 'deck_name_mapping' in st.session_state:
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
    """Create and display the deck selector dropdown with minimal loading"""
    # Initialize session state variables if they don't exist
    if 'selected_deck_index' not in st.session_state:
        st.session_state.selected_deck_index = None
        
    # Only compute dropdown options if not already cached
    if 'deck_display_names' not in st.session_state:
        # Get deck options
        deck_display_names, deck_name_mapping = create_deck_options()
        
        # Store for reuse
        st.session_state.deck_display_names = deck_display_names
        st.session_state.deck_name_mapping = deck_name_mapping
    else:
        # Use cached options
        deck_display_names = st.session_state.deck_display_names
        deck_name_mapping = st.session_state.deck_name_mapping
    
    # Calculate time ago
    time_str = calculate_time_ago(st.session_state.fetch_time)
    
    # Get current set from selected deck or default
    current_set = "-"  # Default
    if st.session_state.selected_deck_index is not None and st.session_state.selected_deck_index < len(deck_display_names):
        selected_deck_display = deck_display_names[st.session_state.selected_deck_index]
        deck_info = st.session_state.deck_name_mapping[selected_deck_display]
        current_set = deck_info['set'].upper()
    
    # Handle deck_to_analyze if set (e.g., from sidebar selection)
    if 'deck_to_analyze' in st.session_state and st.session_state.deck_to_analyze:
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
    rank_symbol = ""
    if rank is not None and 0 <= rank <= 10:
        rank_symbol = circled_numbers[rank]
    
    # Create a plain text expander title with the rank and power index
    with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']} ({power_index})", expanded=expanded):
        # Get sample deck data
        deck_name = deck['deck_name']
        
        try:
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
        except Exception as e:
            st.warning(f"Unable to load deck preview for {deck_name}")
            print(f"Error rendering deck in sidebar: {e}")
        
def render_sidebar_from_cache():
    """Render the sidebar using cached data instead of fetching new data"""
    # Call update check function for background updates
    check_and_update_tournament_data()
    
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
    
    # Ensure energy cache is initialized
    import cache_manager
    cache_manager.ensure_energy_cache()
    
    # Get current month and year for display
    from datetime import datetime
    current_month_year = datetime.now().strftime("%B %Y")
    
    # Display performance data if it exists
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        # Get the top 10 performing decks
        top_decks = st.session_state.performance_data.head(10)
        
        # Render each deck one by one, passing the rank (index + 1)
        for idx, deck in top_decks.iterrows():
            rank = idx + 1  # Calculate rank (1-based)
            render_deck_in_sidebar(deck, rank=rank)
    
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
            * **Positive vs Negative**: Positive numbers mean winning more than losing (decks with negative Power Index will mostly not be shown here)
            """)
    else:
        st.info(f"No tournament performance data available for {current_month_year}")

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


