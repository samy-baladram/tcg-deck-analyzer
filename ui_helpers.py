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
from display_tabs import display_counter_picker, fetch_matchup_data, create_deck_header_images

ENERGY_CACHE_FILE = "cached_data/energy_types.json"

# Add this at the top level (outside any function) in ui_helpers.py
# Add this at the top level of ui_helpers.py
# In ui_helpers.py - Modify check_and_update_tournament_data function

def check_and_update_tournament_data():
    """Check if tournament data needs updating and start background update if needed"""
    # Import necessary modules
    import threading
    from datetime import datetime, timedelta
    from config import CACHE_TTL
    
    # Only proceed if not already updating
    if st.session_state.get('update_running', False):
        return
        
    # Check if data is stale
    if 'performance_fetch_time' in st.session_state:
        time_since_update = datetime.now() - st.session_state.performance_fetch_time
        seconds_until_update = CACHE_TTL - time_since_update.total_seconds()
        print(f"Seconds until update: {seconds_until_update:.1f}")
        
        # Update if older than cache TTL
        if time_since_update.total_seconds() > CACHE_TTL:
            # Set flag to prevent multiple updates
            st.session_state.update_running = True
            
            def background_update():
                try:
                    # Update tournament data without spinner
                    performance_df, performance_timestamp = cache_manager.load_or_update_tournament_data(force_update=True)
                    
                    # Ensure meta-weighted win rate is calculated
                    if 'meta_weighted_winrate' not in performance_df.columns:
                        performance_df = cache_manager.calculate_all_meta_weighted_winrates()
                    
                    # Update session state
                    st.session_state.performance_data = performance_df
                    st.session_state.performance_fetch_time = performance_timestamp
                    
                    # Update card usage data
                    card_usage_df = cache_manager.aggregate_card_usage()
                    st.session_state.card_usage_data = card_usage_df
                    
                    print("Background update completed successfully")
                except Exception as e:
                    print(f"Background update error: {e}")
                finally:
                    st.session_state.update_running = False
            
            # Start update in background
            thread = threading.Thread(target=background_update)
            thread.daemon = True
            thread.start()
            print("Background update started")
            
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
# In ui_helpers.py - Modify render_deck_in_sidebar function

def render_deck_in_sidebar(deck, expanded=False, rank=None):
    """Render a single deck in the sidebar"""
    # Unicode circled numbers: ①②③④⑤⑥⑦⑧⑨⑩⓪
    circled_numbers = ["⓪", "🥇", "🥈", "🥉", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
    
    # Get the appropriate circled number based on rank
    rank_symbol = ""
    if rank is not None and 0 <= rank <= 10:
        rank_symbol = circled_numbers[rank]
    
    # Create a plain text expander title with just the rank and deck name
    with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']}", expanded=expanded):
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
            
            # Display meta-weighted win rate as a caption
            if 'meta_weighted_winrate' in deck and deck['meta_weighted_winrate'] > 0:
                # Determine color based on win rate
                win_rate = deck['meta_weighted_winrate']
                win_color = "#4FCC20" if win_rate >= 55 else "#fda700" if win_rate < 45 else "#fd9a00"
                
                # Create a styled caption with the win rate
                st.markdown(f"""
                <div style="text-align: center; margin-top: 5px;">
                    <span style="font-weight: bold; color: {win_color};">
                        {win_rate:.1f}% Meta-Weighted Win Rate
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Show power index as fallback if no meta-weighted win rate
                st.caption(f"Power Index: {deck['power_index']:.2f}")
            
        except Exception as e:
            st.warning(f"Unable to load deck preview for {deck_name}")
            print(f"Error rendering deck in sidebar: {e}")
        
# In ui_helpers.py - Modify render_sidebar_from_cache function

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
        # Make sure meta_weighted_winrate is calculated
        if 'meta_weighted_winrate' not in st.session_state.performance_data.columns:
            performance_data = cache_manager.calculate_all_meta_weighted_winrates()
        else:
            performance_data = st.session_state.performance_data
        
        # Sort by meta_weighted_winrate instead of power_index
        if 'meta_weighted_winrate' in performance_data.columns:
            performance_data = performance_data.sort_values('meta_weighted_winrate', ascending=False)
        
        # Get the top 10 performing decks
        top_decks = performance_data.head(10)
        
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
        
        
        # Add expandable methodology section
        # In ui_helpers.py - Update the sidebar expander in render_sidebar_from_cache function

        # Add expandable methodology section
        st.write("")
        with st.expander("🔍 About the Meta-Weighted Win Rate"):
            from config import MWWR_FORMULA, MWWR_DESCRIPTION
            
            st.markdown(f"""
            #### Meta-Weighted Win Rate: How We Rank the Best Decks
            
            **Where the Data Comes From**  
            Our Meta-Weighted Win Rate uses the most recent community tournament results from the current month ({current_month_year}) on [Limitless TCG](https://play.limitlesstcg.com/tournaments/completed). This shows how decks actually perform against the current metagame.
            
            **What the Meta-Weighted Win Rate Measures**  
            {MWWR_FORMULA}
            
            {MWWR_DESCRIPTION}
            
            **Why It's Better Than Other Methods**
            * **Better than Win Rate**: Accounts for who you're actually beating
            * **Better than Power Index**: Directly measures performance against the current metagame
            * **Better than Meta Share**: Shows actual effectiveness, not just popularity
            
            **Reading the Numbers**
            * **Higher is Better**: The higher the Meta-Weighted Win Rate, the stronger the deck is against the current metagame
            * **Above 50%**: Expected to perform well in the meta
            * **Below 50%**: May struggle against common decks
            """)
        # Add a divider
        st.markdown("<hr style='margin-top: 25px; margin-bottom: 25px; border: 0; border-top: 0.5px solid;'>", unsafe_allow_html=True)
        
        display_counter_picker_sidebar()
        st.markdown("<hr style='margin-top: 700px; margin-bottom: 300px; border: 0; border-top: 0.5px solid;'>", unsafe_allow_html=True)
            
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

def display_counter_picker_sidebar():
    banner_path = "picker_banner.png"
    if os.path.exists(banner_path):
        with open(banner_path, "rb") as f:
            banner_base64 = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <div style="width:100%; text-align:center; margin:0px 0 0px 0;">
            <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px; margin-bottom:10px;">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.subheader("Meta Counter Picker")
    
    # Get list of top meta decks to choose from
    meta_decks = []
    meta_deck_info = {}  # Add this dictionary to store deck info
    
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        # Use displayed_name for better user experience
        performance_data = st.session_state.performance_data
        
        # Store deck info for each deck
        for _, deck in performance_data.iterrows():
            meta_decks.append(deck['displayed_name'])
            # Store deck info for image generation
            meta_deck_info[deck['displayed_name']] = {
                'deck_name': deck['deck_name'],
                'set': deck['set']
            }
        
        # Limit to top 20 decks
        meta_decks = meta_decks[:20]
    
    if not meta_decks:
        st.warning("No meta deck data available")
        return
    
    # Multi-select for decks to counter
    selected_decks = st.multiselect(
        "Select decks you want to counter:",
        options=meta_decks,
        default=meta_decks[:3] if len(meta_decks) >= 3 else meta_decks,
        help="Choose the decks you want to counter in the meta"
    )
    #st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)  # Exactly 50px space
    # Button to trigger analysis
    find_button = st.button("Find Counters", type="secondary", use_container_width=True)
    
    # Only proceed if decks are selected
    if not selected_decks:
        st.info("Please select at least one deck to find counters")
        return
    
    # Only proceed if button clicked
    if not find_button:
        return
        
    with st.spinner("Analyzing counters..."):
        # This collects all matchup data for each meta deck
        counter_data = []
        
        # For each possible counter deck in the meta
        for _, deck in st.session_state.performance_data.iterrows():
            deck_name = deck['deck_name']
            set_name = deck['set']
            displayed_name = deck['displayed_name']
            
            # Get this deck's matchups
            matchups = fetch_matchup_data(deck_name, set_name)
            
            if matchups.empty:
                continue
            
            # Calculate average win rate against selected decks
            avg_win_rate = 0
            matched_decks = 0
            
            # Convert from displayed names to internal deck names for matching
            selected_internal_names = []
            for displayed in selected_decks:
                for _, meta_deck in st.session_state.performance_data.iterrows():
                    if meta_deck['displayed_name'] == displayed:
                        selected_internal_names.append(meta_deck['deck_name'])
            
            # Look for matchups against selected decks
            for _, matchup in matchups.iterrows():
                if matchup['opponent_deck_name'] in selected_internal_names:
                    avg_win_rate += matchup['win_pct']
                    matched_decks += 1
            
            # Only include if we found matchups against at least half the selected decks
            if matched_decks >= len(selected_decks) / 2:
                avg_win_rate = avg_win_rate / matched_decks if matched_decks > 0 else 0
                
                counter_data.append({
                    'deck_name': deck_name,
                    'displayed_name': displayed_name,
                    'set': set_name,
                    'average_win_rate': avg_win_rate,
                    'meta_share': deck['share'],
                    'power_index': deck['power_index'],
                    'matched_decks': matched_decks,
                    'total_selected': len(selected_decks)
                })
        
        # Create DataFrame and sort by average win rate
        if counter_data:
            counter_df = pd.DataFrame(counter_data)
            counter_df = counter_df.sort_values('average_win_rate', ascending=False)
            
            # Add Pokemon icon URLs
            # Define Pokemon exceptions dictionary (for special cases)
            POKEMON_EXCEPTIONS = {
                'oricorio': 'oricorio-pom-pom',
                # Add other exceptions as needed
            }
            
            # Function to extract Pokemon names and create image URLs
            def extract_pokemon_urls(displayed_name):
                import re
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
            
            # Apply the function to extract Pokemon image URLs
            counter_df[['pokemon_url1', 'pokemon_url2']] = counter_df.apply(
                lambda row: pd.Series(extract_pokemon_urls(row['displayed_name'])), 
                axis=1
            )
            
            # Convert numpy types to Python native types
            counter_df = counter_df.copy()
            for col in counter_df.columns:
                if counter_df[col].dtype == 'int64':
                    counter_df[col] = counter_df[col].astype(int)
                elif counter_df[col].dtype == 'float64':
                    counter_df[col] = counter_df[col].astype(float)
            
            # Display results
            #st.subheader("Best Counter Decks")
            
            # Display top 5 counter decks with images and metrics
            st.write("#### Top Counters to Selected Decks")
            
            # Display top 5 counter decks
            for i in range(min(5, len(counter_df))):
                deck = counter_df.iloc[i]
                
                # Create deck_info object needed for create_deck_header_images
                deck_info = {
                    'deck_name': deck['deck_name'],
                    'set': deck['set']
                }
                
                # Preload Pokemon info into session state to help with image generation
                import cache_manager
                if 'deck_pokemon_info' not in st.session_state:
                    st.session_state.deck_pokemon_info = {}
                
                if deck['deck_name'] not in st.session_state.deck_pokemon_info:
                    # Try to get sample deck to extract Pokemon info
                    sample_deck = cache_manager.get_or_load_sample_deck(deck['deck_name'], deck['set'])
                    
                    # This helps create_deck_header_images find the Pokemon
                    if 'pokemon_cards' in sample_deck:
                        from image_processor import extract_pokemon_from_deck_name
                        pokemon_names = extract_pokemon_from_deck_name(deck['deck_name'])
                        
                        if pokemon_names:
                            st.session_state.deck_pokemon_info[deck['deck_name']] = []
                            
                            for pokemon_name in pokemon_names[:2]:
                                # Find matching card in sample deck
                                for card in sample_deck['pokemon_cards']:
                                    # Normalize names for comparison
                                    card_name_norm = card['card_name'].lower().replace(' ', '-')
                                    pokemon_name_norm = pokemon_name.lower()
                                    
                                    if card_name_norm == pokemon_name_norm:
                                        st.session_state.deck_pokemon_info[deck['deck_name']].append({
                                            'name': pokemon_name,
                                            'card_name': card['card_name'],
                                            'set': card.get('set', ''),
                                            'num': card.get('num', '')
                                        })
                                        break
                
                # Generate header image - passing empty results since we've preloaded info
                header_image = create_deck_header_images(deck_info, None)
                
                # Check if this is a top 3 or lower ranked deck
                is_top_three = i < 3
                
                # Adjust column widths and styling based on ranking
                if is_top_three:
                    # Top 3 decks get normal layout
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Display the banner image
                        if header_image:
                            st.markdown(f"""
                            <div style="margin-right: 1rem; width: 100%; max-width: 250px; text-align: left;">
                                <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border-radius: 10px;">
                            </div>

                            """, unsafe_allow_html=True)
                        else:
                            # Placeholder if no image
                            st.markdown("""
                            <div style="width: 100%; height: 80px; background-color: #f0f0f0; border-radius: 6px; 
                                display: flex; align-items: center; justify-content: center;">
                                <span style="color: #888;">No image</span>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    #with col2:
                        # Display deck name with ranking
                        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
                        st.markdown(f"#### {rank_emoji} {deck['displayed_name']}")
                    
                    with col2:
                        # Display win rate as a big percentage
                        win_rate = deck['average_win_rate']
                        win_color = "#4FCC20" if win_rate >= 60 else "#fd6c6c" if win_rate < 40 else "#FDA700"
                        st.markdown(f"""
                        <div style="text-align: right; margin-top:0.5em;">
                            <span style="font-size: 1.4rem; width:100%; font-weight: bold; color: {win_color};">{win_rate:.1f}%</span>
                            <div style="font-size: 0.8rem; margin-top: -0.5rem;">win rate</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    # 4th and 5th place get smaller layout
                    col1, col2 = st.columns([3.5, 1])
                    
                    with col1:
                        # Display smaller banner image
                        if header_image:
                            st.markdown(f"""
                            <div style="margin-right: 1rem; width: 100%; max-width: 250px; text-align: left;">
                                <img src="data:image/png;base64,{header_image}" style="width: 90%; height: auto; border-radius: 8px;">
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # Smaller placeholder
                            st.markdown("""
                            <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 6px; 
                                display: flex; align-items: center; justify-content: center;">
                                <span style="color: #888; font-size: 0.9rem;">No image</span>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    #with col2:
                        # Display deck name with smaller font
                        rank_num = f"#{i+1}"
                        st.markdown(f"##### {rank_num} {deck['displayed_name']}")
                    
                    with col2:
                        # Display win rate as a smaller percentage without "win rate" text
                        win_rate = deck['average_win_rate']
                        win_color = "#4FCC20" if win_rate >= 60 else "#fd6c6c" if win_rate < 40 else "#FDA700"
                        st.markdown(f"""
                        <div style="text-align: right; width:100%; margin-top:0.5em;">
                            <span style="font-size: 1.2rem; font-weight: bold; color: {win_color};">{win_rate:.1f}%</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Add a horizontal line between decks
                if i < min(4, len(counter_df) - 1):
                    # Top 3 get normal divider, 4-5 get thinner divider
                    divider_style = "solid 0.5px"
                    divider_color = "#ddd"
                    st.markdown(f"<hr style='margin: 0px 0; border-top: {divider_style} {divider_color};'>", unsafe_allow_html=True)
            
            # Display table with all results including icons
            # st.write("")
            # st.write("##### All Counter Options")
            
            # # Create a DataFrame with the ordered columns including icons
            # display_df = pd.DataFrame({
            #     'Icon1': counter_df['pokemon_url1'],
            #     'Icon2': counter_df['pokemon_url2'],
            #     'Deck': counter_df['displayed_name'],
            #     'Win %': counter_df['average_win_rate'],
            #     'Meta Share': counter_df['meta_share'],
            #     'Power Index': counter_df['power_index']
            # })
            
            # st.dataframe(
            #     display_df,
            #     column_config={
            #         "Icon1": st.column_config.ImageColumn(
            #             "Icon 1",
            #             help="First Pokémon in the deck",
            #             width="20px",
            #         ),
            #         "Icon2": st.column_config.ImageColumn(
            #             "Icon 2", 
            #             help="Second Pokémon in the deck",
            #             width="20px",
            #         ),
            #         "Deck": st.column_config.TextColumn(
            #             "Deck",
            #             help="Deck archetype name"
            #         ),
            #         "Win %": st.column_config.NumberColumn(
            #             "Avg Win %",
            #             help="Average win percentage against selected decks",
            #             format="%.1f%%"
            #         ),
            #         # "Meta Share": st.column_config.NumberColumn(
            #         #     "Meta Share",
            #         #     help="Percentage of the current meta",
            #         #     format="%.2f%%"
            #         # ),
            #         # "Power Index": st.column_config.NumberColumn(
            #         #     "Power Index",
            #         #     help="Overall performance in the meta",
            #         #     format="%.2f"
            #         # )
            #     },
            #     hide_index=True,
            #     use_container_width=True
            # )
            
            # Add explanation text 
            st.caption("Higher average win rate indicates better performance against your selected decks. Data is from the current aggregated tournament result in [Limitless TCG](https://play.limitlesstcg.com/decks?game=pocket)")
        else:
            st.warning("No counter data found for the selected decks")
