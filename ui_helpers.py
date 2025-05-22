# ui_helpers.py
"""UI helper functions for TCG Deck Analyzer"""

import streamlit as st
from datetime import datetime
from formatters import format_deck_name, format_deck_option, displayed_name_to_markdown
from utils import calculate_time_ago
from scraper import get_deck_list
import cache_manager
from config import POWER_INDEX_EXPLANATION, MIN_META_SHARE, TOURNAMENT_COUNT
import pandas as pd
import base64
import os
from display_tabs import display_counter_picker, fetch_matchup_data, create_deck_header_images

ENERGY_CACHE_FILE = "cached_data/energy_types.json"

# Add this at the top level (outside any function) in ui_helpers.py
# Add this at the top level of ui_helpers.py
# Modify the check_and_update_tournament_data function in ui_helpers.py
def check_and_update_tournament_data():
    """Check if tournament data needs updating"""
    # Import necessary modules
    from datetime import datetime, timedelta
    from config import CACHE_TTL
    
    # Check if data is stale
    if 'performance_fetch_time' in st.session_state:
        time_since_update = datetime.now() - st.session_state.performance_fetch_time
        seconds_until_update = CACHE_TTL - time_since_update.total_seconds()
        print(f"Seconds until update: {seconds_until_update:.1f}")
        
        # Update if older than cache TTL
        if time_since_update.total_seconds() > CACHE_TTL:
            # Update and set flag to prevent multiple updates during rerun
            if not st.session_state.get('update_running', False):
                st.session_state.update_running = True
                st.rerun()  # Trigger rerun to show spinner
            
            # This will only execute after rerun, with spinner visible
            with st.spinner("Updating tournament data..."):
                # Update tournament data
                performance_df, performance_timestamp = cache_manager.load_or_update_tournament_data(force_update=True)
                
                # Update session state
                st.session_state.performance_data = performance_df
                st.session_state.performance_fetch_time = performance_timestamp
                
                # Update card usage data
                card_usage_df = cache_manager.aggregate_card_usage()
                st.session_state.card_usage_data = card_usage_df
                
                # Reset flag
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
    # Initialize minimal caches first
    cache_manager.init_caches()
    
    # Initialize session state variables
    if 'selected_deck_index' not in st.session_state:
        st.session_state.selected_deck_index = 0  # Pre-select first option (index 0)
        
    if 'deck_to_analyze' not in st.session_state:
        st.session_state.deck_to_analyze = None
    
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
        top_performing_decks = st.session_state.performance_data #.head(30)
        
        for _, deck in top_performing_decks.iterrows():
            power_index = round(deck['power_index'], 2)
            # Format: "Deck Name (Power Index)"
            display_name = deck['displayed_name']
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

def ensure_performance_data_updated():
    """Ensure performance data uses latest formula"""
    import math
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        print("Updating power index formula...")
        
        # Force recalculate power index with new formula
        performance_df = st.session_state.performance_data.copy()
        
        # Apply the new formula to each row
        def recalculate_power_index(row):
            total_wins = row['total_wins']
            total_losses = row['total_losses']
            total_ties = row['total_ties']
            total_games = total_wins + total_losses + total_ties
            
            if total_games > 0:
                # Calculate total games (including ties)
                total_games = total_wins + total_losses + total_ties
                
                if total_games > 0:
                    # Handle ties as half-wins (common in card games)
                    adjusted_wins = total_wins + (0.5 * total_ties)
                    
                    # Calculate win proportion
                    win_proportion = adjusted_wins / total_games
                    
                    # Wilson Score Interval parameters
                    z = 1.96  # 95% confidence level
                    z_squared = z * z
                    
                    # Calculate Wilson Score lower bound
                    numerator = (win_proportion + (z_squared / (2 * total_games)) - 
                                 z * math.sqrt((win_proportion * (1 - win_proportion) + 
                                              (z_squared / (4 * total_games))) / total_games))
                    
                    denominator = 1 + (z_squared / total_games)
                    
                    # Wilson Score lower bound (conservative estimate of true win rate)
                    wilson_score = numerator / denominator
                    
                    # Scale to make more intuitive (similar range to original power index)
                    # Transforming from 0-1 scale to -5 to +5 scale
                    #
                    power_index = (wilson_score - 0.5) * 10
                return power_index
            return 0.0
        
        # Update power index and resort
        performance_df['power_index'] = performance_df.apply(recalculate_power_index, axis=1)
        performance_df = performance_df.sort_values('power_index', ascending=False).reset_index(drop=True)
        
        # Replace in session state
        st.session_state.performance_data = performance_df
        
        # Also clear deck display names to force regeneration
        if 'deck_display_names' in st.session_state:
            del st.session_state['deck_display_names']

    return
    
def create_deck_selector():
    """Create and display the deck selector dropdown with minimal loading"""

    ensure_performance_data_updated()
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
        
        # Pre-select first deck if we have options and no selection yet
        if deck_display_names and (st.session_state.selected_deck_index is None or 'analyze' not in st.session_state):
            st.session_state.selected_deck_index = 0
            
            # Set the first deck to analyze
            first_deck_display = deck_display_names[0]
            first_deck_info = deck_name_mapping[first_deck_display]
            st.session_state.analyze = {
                'deck_name': first_deck_info['deck_name'],
                'set_name': first_deck_info['set'],
            }
    else:
        # Use cached options
        deck_display_names = st.session_state.deck_display_names
        deck_name_mapping = st.session_state.deck_name_mapping
        
        # Check if we need to pre-select first deck
        if deck_display_names and (st.session_state.selected_deck_index is None or 'analyze' not in st.session_state):
            st.session_state.selected_deck_index = 0
            
            # Set the first deck to analyze
            first_deck_display = deck_display_names[0]
            first_deck_info = deck_name_mapping[first_deck_display]
            st.session_state.analyze = {
                'deck_name': first_deck_info['deck_name'],
                'set_name': first_deck_info['set'],
            }
    
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

    deck_icon_display_names = []
    for name in deck_display_names:
        deck_icon_display_names.append(displayed_name_to_markdown(name))

    # Display the selectbox
    selected_option = st.selectbox(
        label_text,
        deck_icon_display_names,
        #deck_display_names,
        index=st.session_state.selected_deck_index,
        placeholder="Select a deck to analyze...",
        help=help_text,
        key="deck_select",
        on_change=on_deck_change,
        format_func=lambda x: x  # This ensures the markdown is passed through
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
    with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']} ", expanded=expanded):
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
            st.caption(f"Power Index: {power_index}")
        except Exception as e:
            st.warning(f"Unable to load deck preview for {deck_name}")
            print(f"Error rendering deck in sidebar: {e}")
        
def render_sidebar_from_cache():
    # Call update check function for background updates
    check_and_update_tournament_data()

    from datetime import datetime
    current_month_year = datetime.now().strftime("%B %Y")
 
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

    # Add debug button to toggle deck visibility
    if 'show_decks' not in st.session_state:
        st.session_state.show_decks = False

    # Only show the button if decks are not currently visible
    if not st.session_state.show_decks:
    
        # Debug button to show/hide decks
        if st.button("See now!", type="tertiary", use_container_width=True):
            st.session_state.show_decks = True
            #st.session_state.show_decks = not st.session_state.show_decks
            st.rerun()
    # Only show decks if the button has been clicked
    if st.session_state.show_decks:
        
        # Ensure energy cache is initialized
        import cache_manager
        cache_manager.ensure_energy_cache()
        
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
            
            # Add expandable methodology section
            st.write("")
            with st.expander("🔍 About the Power Index"):
                # Format the explanation with the current date and tournament count
                formatted_explanation = POWER_INDEX_EXPLANATION.format(
                    tournament_count=TOURNAMENT_COUNT,
                    current_month_year=current_month_year
                )
                
                # Display the enhanced explanation
                st.markdown(formatted_explanation)
     
    else:
        st.write("")
        #st.info(f"No tournament performance data available for {current_month_year}")
    st.markdown("<hr style='margin-top: 25px; margin-bottom: 25px; border: 0; border-top: 0.5px solid;'>", unsafe_allow_html=True)
    # Display counter picker directly (no container)
    display_counter_picker_sidebar()
    st.markdown("""
    <div style="height: 300px;"></div>
    """, unsafe_allow_html=True) 
    
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
    
    # Check if we should switch to a selected deck
    if 'switch_to_deck' in st.session_state:
        deck_name = st.session_state.switch_to_deck
        # Clear the flag
        del st.session_state['switch_to_deck']
        # Set the deck for analysis - this uses create_deck_selector's logic
        st.session_state.deck_to_analyze = deck_name
    
    # Multi-select for decks to counter
    selected_decks = st.multiselect(
        "Select decks you want to counter:",
        options=meta_decks,
        default=meta_decks[:3] if len(meta_decks) >= 3 else meta_decks,
        help="Choose the decks you want to counter in the meta"
    )

    # Button to trigger analysis
    st.session_state.run_counter_analysis = False
    if st.button("Find Counters", type="secondary", use_container_width=True):
        st.session_state.run_counter_analysis = True
        st.session_state.selected_counter_decks = selected_decks
    
    # Only run analysis if button was clicked
    if st.session_state.run_counter_analysis and 'selected_counter_decks' in st.session_state:
        analyze_counter(st.session_state.selected_counter_decks)
        # Reset the flag after analysis
        st.session_state.run_counter_analysis = False

def analyze_counter(selected_decks):        
    with st.spinner("Analyzing counters..."):
        # This collects all matchup data for each meta deck
        counter_data = []

        selected_internal_names = []
        for displayed in selected_decks:
            for _, meta_deck in st.session_state.performance_data.iterrows():
                if meta_deck['displayed_name'] == displayed:
                    selected_internal_names.append(meta_deck['deck_name'])

        # For each possible counter deck in the meta
        for _, deck in st.session_state.performance_data.iterrows():
            deck_name = deck['deck_name']
            set_name = deck['set']
            displayed_name = deck['displayed_name']
            
            # Get this deck's matchups
            matchups = fetch_matchup_data(deck_name, set_name)
            
            if matchups.empty:
                continue
            
            # Initialize variables for weighted average calculation
            total_weighted_win_rate = 0
            total_matches = 0
            matched_decks = 0  # Add this line to initialize matched_decks
            
            # Look for matchups against selected decks
            for _, matchup in matchups.iterrows():
                if matchup['opponent_deck_name'] in selected_internal_names:
                    # Get the number of matches for this matchup
                    match_count = matchup['matches_played']
                    
                    # Add to weighted sum (win percentage × number of matches)
                    total_weighted_win_rate += matchup['win_pct'] * match_count
                    
                    # Add to total matches count
                    total_matches += match_count
                    
                    # Still track number of matched decks for filtering
                    matched_decks += 1
            
            # Only include if we found matchups against at least half the selected decks
            if matched_decks >= len(selected_decks) / 2:
                # Calculate weighted average: total weighted sum divided by total matches
                avg_win_rate = total_weighted_win_rate / total_matches if total_matches > 0 else 0
                
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
        
        # # Create DataFrame and sort by average win rate
        if counter_data:
            counter_df = pd.DataFrame(counter_data)
            counter_df = counter_df.sort_values('average_win_rate', ascending=False)
            
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
                        
                        # MODIFIED: Replace text with button, using callback method
                        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
                        button_label = f"{rank_emoji} {deck['displayed_name']}"
                        
                        # Create a unique key for each button
                        button_key = f"counter_deck_btn_{deck['deck_name']}_{i}"
                        st.button(
                            button_label, 
                            key=button_key,
                            type="tertiary",
                            on_click=set_deck_to_analyze,
                            args=(deck['deck_name'],)
                        )
                    
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
                        
                        # MODIFIED: Replace text with button
                        rank_num = f"#{i+1}"
                        button_label = f"{rank_num} {deck['displayed_name']}"
                        
                        # Create a unique key for each button
                        button_key = f"counter_deck_btn_{deck['deck_name']}_{i}"
                        st.button(
                            button_label, 
                            key=button_key,
                            type="tertiary",
                            on_click=set_deck_to_analyze,
                            args=(deck['deck_name'],)
                        )
                    
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
                    st.markdown(f"<hr style='margin-top: -10px; margin-bottom: -10px; border-top: {divider_style} {divider_color};'>", unsafe_allow_html=True)
            
            # Add explanation text 
            st.caption("Win rates shown are weighted by number of matches played, providing a more reliable performance indicator against your selected decks. Decks with higher win rates have demonstrated stronger results in tournament play. Data from [Limitless TCG](https://play.limitlesstcg.com/decks?game=pocket)")
        else:
            st.warning("No counter data found for the selected decks")

def set_deck_to_analyze(deck_name):
    """Callback function when counter deck button is clicked"""
    # Set the deck to analyze
    st.session_state.deck_to_analyze = deck_name
