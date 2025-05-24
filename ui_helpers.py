import streamlit as st
from datetime import datetime
from formatters import format_deck_name, format_deck_option
from utils import calculate_time_ago
from scraper import get_popular_decks_with_performance
import cache_manager
from config import POWER_INDEX_EXPLANATION, MIN_META_SHARE, TOURNAMENT_COUNT, MIN_COUNTER_MATCHES
import pandas as pd
import base64
import os
from display_tabs import fetch_matchup_data
from header_image_cache import get_header_image_cached
# ADD: Try to import card cache, but provide fallback if it fails
try:
    from card_cache import get_sample_deck_cached
    CARD_CACHE_AVAILABLE = True
except ImportError:
    print("Card cache not available, using fallback")
    CARD_CACHE_AVAILABLE = False
    
ENERGY_CACHE_FILE = "cached_data/energy_types.json"

# ADD: Banner image caching
@st.cache_data
def get_cached_banner_image(img_path):
    """Cache banner images to avoid repeated file reads"""
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

# ADD: Cache for popular decks data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cached_popular_decks():
    """Cache popular decks data to avoid repeated API calls"""
    return get_popular_decks_with_performance()

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

# ENHANCE: Add caching to energy types function
def get_energy_types_for_deck(deck_name, deck_energy_types=None):
    """Get energy types for a deck, using dedicated energy cache"""
    # If specific energy types provided, use them
    if deck_energy_types:
        return deck_energy_types, False
    
    # Check session cache first for faster access
    energy_cache_key = f"energy_{deck_name}"
    if energy_cache_key in st.session_state:
        cached_energy = st.session_state[energy_cache_key]
        return cached_energy['types'], cached_energy['is_typical']
    
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
        # Cache in session state for faster subsequent access
        st.session_state[energy_cache_key] = {
            'types': energy_types,
            'is_typical': True
        }
        return energy_types, True
    
    # If no energy found in cache, try to force a new calculation
    cache_manager.ensure_deck_collected(deck_name, set_name)
    energy_types = cache_manager.calculate_and_cache_energy(deck_name, set_name)
    
    if energy_types:
        # Cache in session state
        st.session_state[energy_cache_key] = {
            'types': energy_types,
            'is_typical': True
        }
        return energy_types, True
    
    # Cache empty result to avoid repeated calculations
    st.session_state[energy_cache_key] = {
        'types': [],
        'is_typical': False
    }
    return [], False

# ENHANCE: Cache energy icon HTML generation
@st.cache_data
def render_energy_icons_cached(energy_types_tuple, is_typical=False):
    """Generate HTML for energy icons with caching"""
    if not energy_types_tuple:
        return ""
        
    energy_html = ""
    # Create image tags for each energy type
    for energy in energy_types_tuple:
        energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
        energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:20px; margin-right:4px; vertical-align:middle; ">'
    
    energy_display = f"""<div style="margin-bottom: -5px;">
        <p style="margin-bottom:5px;"><strong>Energy:</strong> {energy_html}</p>
    </div>"""
    return energy_display

def render_energy_icons(energy_types, is_typical=False):
    """Generate HTML for energy icons (wrapper for cached version)"""
    # Convert to tuple for caching (lists aren't hashable)
    energy_tuple = tuple(energy_types) if energy_types else ()
    return render_energy_icons_cached(energy_tuple, is_typical)
            
def display_banner(img_path, max_width=900):
    """Display the app banner image with caching"""
    # USE CACHED VERSION
    img_base64 = get_cached_banner_image(img_path)
    
    if img_base64:
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
    
    # ENHANCE: Use cached popular decks
    if 'deck_list' not in st.session_state:
        st.session_state.deck_list = get_cached_popular_decks()
        st.session_state.fetch_time = datetime.now()

# ENHANCE: Cache deck options creation
def create_deck_options():
    """Create deck options for dropdown from performance data or fallback to deck list"""
    # Check if we already have cached options
    if ('deck_options_cache' in st.session_state and 
        'performance_data' in st.session_state and 
        st.session_state.deck_options_cache.get('data_hash') == hash(str(st.session_state.performance_data.to_dict()))):
        
        print("Using cached deck options")
        cached_options = st.session_state.deck_options_cache
        return cached_options['display_names'], cached_options['name_mapping']
    
    # Initialize deck display names and mapping
    deck_display_names = []
    deck_name_mapping = {}
    
    # First try to use performance data
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        top_performing_decks = st.session_state.performance_data
        
        for _, deck in top_performing_decks.iterrows():
            display_name = deck['displayed_name']
            deck_display_names.append(display_name)
            deck_name_mapping[display_name] = {
                'deck_name': deck['deck_name'],
                'set': deck['set']
            }
    else:
        # Use cached deck list
        if 'deck_list' not in st.session_state:
            st.session_state.deck_list = get_cached_popular_decks()
            st.session_state.fetch_time = datetime.now()
                
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
            print(f"Error creating deck options: {e}")
            display_name = "Example Deck (1.0)"
            deck_display_names.append(display_name)
            deck_name_mapping[display_name] = {
                'deck_name': 'example-deck',
                'set': 'A3'
            }
    
    # Cache the results
    if 'performance_data' in st.session_state:
        data_hash = hash(str(st.session_state.performance_data.to_dict()))
    else:
        data_hash = hash(str(deck_display_names))
    
    st.session_state.deck_options_cache = {
        'display_names': deck_display_names,
        'name_mapping': deck_name_mapping,
        'data_hash': data_hash
    }
    
    # Store mapping in session state
    st.session_state.deck_name_mapping = deck_name_mapping
    
    return deck_display_names, deck_name_mapping

# Fix 2: Update ui_helpers.py - Fix the deck selection callback
def on_deck_change():
    """Handle deck dropdown selection change with proper cache clearing"""
    if 'deck_select' not in st.session_state:
        return
        
    selection = st.session_state.deck_select
    if selection:
        if 'deck_display_names' not in st.session_state:
            return
            
        # Get the new deck info
        new_deck_info = st.session_state.deck_name_mapping[selection]
        new_deck_name = new_deck_info['deck_name']
        new_set_name = new_deck_info['set']
        
        # Check if this is actually a different deck
        current_deck = st.session_state.get('analyze', {})
        if (current_deck.get('deck_name') != new_deck_name or 
            current_deck.get('set_name') != new_set_name):
            
            # Clear caches for the new deck to force fresh analysis
            import cache_manager
            cache_manager.clear_deck_cache_on_switch(new_deck_name, new_set_name)
            
            # Update selection index
            st.session_state.selected_deck_index = st.session_state.deck_display_names.index(selection)
            
            # Set the new deck to analyze
            st.session_state.analyze = {
                'deck_name': new_deck_name,
                'set_name': new_set_name,
            }
            
            print(f"Switched to deck: {new_deck_name}")
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
    help_text = f"Showing decks with meta share ≥ 0.1% and win rate ≥ 45%, ordered by Power Index (details in sidebar).\nSource: [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET).\nUpdated {time_str}."

    # deck_icon_display_names = []
    # for name in deck_display_names:
    #     deck_icon_display_names.append(f"{displayed_name_to_markdown(name)} {name}")

    # Display the selectbox
    selected_option = st.selectbox(
        label_text,
        deck_display_names,
        index=st.session_state.selected_deck_index,
        placeholder="Select a deck to analyze...",
        help=help_text,
        key="deck_select",
        on_change=on_deck_change,
        #format_func=lambda x: x  # This ensures the markdown is passed through
    )
    
    return selected_option

# In ui_helpers.py - Updated render_deck_in_sidebar function
def render_deck_in_sidebar(deck, expanded=False, rank=None):
    """Render a single deck in the sidebar with cached components"""
    try:
        power_index = round(deck['power_index'], 2)
        
        circled_numbers = ["⓪", "🥇", "🥈", "🥉", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
        
        rank_symbol = ""
        if rank is not None and 0 <= rank <= 10:
            rank_symbol = circled_numbers[rank]
        
        with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']} ", expanded=expanded):
            try:
                # 1. USE CACHED HEADER IMAGE
                header_image = get_header_image_cached(deck['deck_name'], deck['set'])
                
                if header_image:
                    st.markdown(f"""
                    <div style="width: 100%; margin-bottom: 10px;">
                        <img src="data:image/png;base64,{header_image}" style="width: 120%; height: auto; ">
                    </div>
                    """, unsafe_allow_html=True)
                
                # 2. USE CACHED SAMPLE DECK
                deck_name = deck['deck_name']
                
                # Check if card cache is available before using it
                if CARD_CACHE_AVAILABLE:
                    sample_deck = get_sample_deck_cached(deck_name, deck['set'])
                else:
                    # Fallback to direct import if cache not available
                    from scraper import get_sample_deck_for_archetype
                    pokemon_cards, trainer_cards, energy_types = get_sample_deck_for_archetype(deck_name, deck['set'])
                    sample_deck = {
                        'pokemon_cards': pokemon_cards,
                        'trainer_cards': trainer_cards,
                        'energy_types': energy_types
                    }
                
                # Render deck view
                from card_renderer import render_sidebar_deck
                deck_html = render_sidebar_deck(
                    sample_deck['pokemon_cards'], 
                    sample_deck['trainer_cards'],
                    card_width=60
                )
                
                st.markdown(deck_html, unsafe_allow_html=True)

                # 3. USE CACHED ENERGY TYPES
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    energy_types, is_typical = get_energy_types_for_deck(deck['deck_name'])
                    
                    if energy_types:
                        # USE CACHED ENERGY ICON RENDERING
                        energy_html = render_energy_icons_cached(tuple(energy_types), is_typical)
                        st.markdown(energy_html, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="margin-bottom: 5px;">
                            <div style="font-size: 0.8rem; color: #888;">No energy data</div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.caption(f"Power Index: {power_index}")    
                
                with col2:
                    if st.button("Details", key=f"details_{deck['deck_name']}_{rank}", type="tertiary", use_container_width=True):
                        st.session_state.deck_to_analyze = deck['deck_name']
                        st.rerun()
                
            except Exception as e:
                st.warning(f"Unable to load deck preview for {deck_name}")
                print(f"Error rendering deck in sidebar: {e}")
                # Show basic info as fallback
                st.write(f"**{deck['displayed_name']}**")
                st.caption(f"Power Index: {power_index}")
                
    except Exception as e:
        print(f"Critical error in render_deck_in_sidebar: {e}")
        st.error("Error loading deck data")

def render_sidebar_from_cache():
    """Render sidebar with aggressive caching"""
    check_and_update_tournament_data()

    from datetime import datetime
    current_month_year = datetime.now().strftime("%B %Y")
 
    # USE CACHED BANNER IMAGE
    banner_base64 = get_cached_banner_image("sidebar_banner.png")
    if banner_base64:
        st.markdown(f"""
        <div style="width:100%; text-align:center;">
            <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px;">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.title("Top 10 Meta Decks")

    # Initialize top_deck variable
    top_deck = None
    
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        top_deck = st.session_state.performance_data.iloc[0]
        
        # USE CACHED HEADER IMAGE
        header_image = get_header_image_cached(top_deck['deck_name'], top_deck['set'])

        if header_image:
            st.markdown(f"""
            <div style="width: 100%; margin-bottom: -1rem;">
                <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border: 2px solid #000; border-radius: 8px;z-index:-1;">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 6px;
                display: flex; align-items: center; justify-content: center;">
                <span style="color: #888; font-size: 0.8rem;">No image</span>
            </div>
            """, unsafe_allow_html=True)
    
    # CRITICAL FIX: Only proceed if we have top_deck data
    if top_deck is not None:
        # NEW: Add 2-column layout for top deck and See more button
        col1, col2 = st.columns([3, 1])
        
        with col1:         
            # Button to switch to this deck
            if st.button(
                top_deck['displayed_name'], 
                key="top_deck_button",
                type="tertiary",
                use_container_width=False
            ):
                # Set the deck to analyze
                st.session_state.deck_to_analyze = top_deck['deck_name']
                st.rerun()

        with col2:
            # Add button to toggle deck visibility for Top 10 Meta Decks
            if 'show_decks' not in st.session_state:
                st.session_state.show_decks = False

            # Only show the button if decks are not currently visible
            if not st.session_state.show_decks:
                if st.button("See more", type="tertiary", use_container_width=False):
                    st.session_state.show_decks = True
                    st.rerun()

        # Only show decks if the button has been clicked
        if st.session_state.show_decks:
            # Ensure energy cache is initialized
            import cache_manager
            cache_manager.ensure_energy_cache()
            
            # Display performance data if it exists
            if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
                # Get the top 10 performing decks (sorted by Power Index)
                top_decks = st.session_state.performance_data.head(10)
                
                # Render each deck one by one, passing the rank (index + 1)
                for idx, (_, deck) in enumerate(top_decks.iterrows()):
                    rank = idx + 1  # Calculate rank (1-based)
                    render_deck_in_sidebar(deck, rank=rank)
            
                # Add disclaimer with update time in one line
                performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center;  font-size: 0.85rem;">
                    <div>Top performers from {current_month_year}</div>
                    <div>Updated {performance_time_str}</div>
                </div>
                <div style="font-size: 0.75rem; margin-bottom: 5px; color: #777;">
                    Based on up to {TOURNAMENT_COUNT} tournament results
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("")

        # ADD NEW SECTION: Trending Decks
        # Load and encode the trending banner image if it exists
        trending_banner_path = "trending_banner.png"
        if os.path.exists(trending_banner_path):
            with open(trending_banner_path, "rb") as f:
                trending_banner_base64 = base64.b64encode(f.read()).decode()
            st.markdown(f"""
            <div style="width:100%; text-align:center; margin-top:-20px;">
                <hr style='margin-bottom:15px;  border: 0.5px solid #aaa;'>
                <img src="data:image/png;base64,{trending_banner_base64}" style="width:100%; max-width:350px;">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("### 📈 Trending Decks")
        
        # Get the first trending deck
        test_deck = st.session_state.performance_data.sort_values('tournaments_played', ascending=False).iloc[0]
        
        # Generate header image for trending deck
        header_image = get_header_image_cached(test_deck['deck_name'], test_deck['set'])

        if header_image:
            st.markdown(f"""
            <div style="width: 100%; margin-bottom: -1rem;">
                <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border: 2px solid #000; border-radius: 8px;z-index:-1;">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 6px;
                display: flex; align-items: center; justify-content: center;">
                <span style="color: #888; font-size: 0.8rem;">No image</span>
            </div>
            """, unsafe_allow_html=True)
        
        # NEW: Add 2-column layout for test deck and See More button
        col1, col2 = st.columns([3, 1])
        
        with col1:         
            # Button to switch to this deck
            if st.button(
                test_deck['displayed_name'], 
                key="test_trending_deck_button",
                type="tertiary",
                use_container_width=False
            ):
                # Set the deck to analyze
                st.session_state.deck_to_analyze = test_deck['deck_name']
                st.rerun()

        with col2:
            # Add button to toggle trending decks visibility
            if 'show_trending_decks' not in st.session_state:
                st.session_state.show_trending_decks = False

            # Only show the button if trending decks are not currently visible
            if not st.session_state.show_trending_decks:
                if st.button("See More", type="tertiary", use_container_width=False, key="trending_button"):
                    st.session_state.show_trending_decks = True
                    st.rerun()

        # Only show trending decks if the button has been clicked
        if st.session_state.show_trending_decks:
            # Ensure energy cache is initialized
            import cache_manager
            cache_manager.ensure_energy_cache()
            
            # Display performance data if it exists
            if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
                # Get trending decks (sorted by tournaments_played/Best Finishes)
                trending_decks = st.session_state.performance_data.sort_values('tournaments_played', ascending=False).head(5)
                
                # Render each trending deck one by one, passing the rank (index + 1)
                for idx, (_, deck) in enumerate(trending_decks.iterrows()):
                    rank = idx + 1  # Calculate rank (1-based)
                    render_trending_deck_in_sidebar(deck, rank=rank)
            
                # Add disclaimer with update time for trending decks
                performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center;  font-size: 0.85rem;">
                    <div>Most active from {current_month_year}</div>
                    <div>Updated {performance_time_str}</div>
                </div>
                <div style="font-size: 0.75rem; margin-bottom: 5px; color: #777;">
                    Sorted by tournament activity
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("")
        
        # Continue with existing code (Counter Picker section)
        display_counter_picker_sidebar()
        
        # Power Index explanation
        st.markdown("<hr style='margin:25px;  border: 0.5px solid #aaa;'>", unsafe_allow_html=True)
        with st.expander("🔍 About the Power Index"):
            # Format the explanation with the current date and tournament count
            formatted_explanation = POWER_INDEX_EXPLANATION.format(
                tournament_count=TOURNAMENT_COUNT,
                current_month_year=current_month_year
            )
            
            # Display the enhanced explanation
            st.markdown(formatted_explanation)
    else:
        # Fallback if no performance data
        st.warning("No performance data available")
    
    # Rest of render_sidebar_from_cache remains the same...
    # [Include all the remaining logic but replace any create_deck_header_images calls with get_header_image_cached]

def render_trending_deck_in_sidebar(deck, expanded=False, rank=None):
    """Render a single trending deck in the sidebar with cached components"""
    tournaments_played = deck['tournaments_played']
    rank_symbol = "🚀"
    
    with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']} ", expanded=expanded):
        try:
            # USE CACHED HEADER IMAGE
            header_image = get_header_image_cached(deck['deck_name'], deck['set'])  # CHANGED
            
            if header_image:
                st.markdown(f"""
                <div style="width: 100%; margin-bottom: 10px;">
                    <img src="data:image/png;base64,{header_image}" style="width: 120%; height: auto;">
                </div>
                """, unsafe_allow_html=True)
            
            # USE CACHED SAMPLE DECK
            deck_name = deck['deck_name']
            sample_deck = get_sample_deck_cached(deck_name, deck['set'])  # CHANGED
            
            from card_renderer import render_sidebar_deck
            deck_html = render_sidebar_deck(
                sample_deck['pokemon_cards'], 
                sample_deck['trainer_cards'],
                card_width=60
            )
            st.markdown(deck_html, unsafe_allow_html=True)

            col1, col2 = st.columns([2, 1])
            
            with col1:
                # USE CACHED ENERGY TYPES
                energy_types, is_typical = get_energy_types_for_deck(deck['deck_name'])
                
                if energy_types:
                    # USE CACHED ENERGY RENDERING
                    energy_html_compact = ""
                    for energy in energy_types:
                        energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
                        energy_html_compact += f'<img src="{energy_url}" alt="{energy}" style="height:30px; margin-right:2px; vertical-align:middle;">'
                    
                    st.markdown(f"""
                    <div style="margin-top:5px; ">
                        <div>{energy_html_compact}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"Best Finishes: {tournaments_played}")
                else:
                    st.markdown("""
                    <div style="margin-bottom: 5px;">
                        <div style="font-size: 0.8rem; color: #888;">No energy data</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                if st.button("Details", 
                            key=f"counter_details_{deck['deck_name']}_{i}", 
                            type="tertiary", 
                            use_container_width=True,
                            on_click=lambda deck_name=deck['deck_name']: setattr(st.session_state, 'deck_to_analyze', deck_name)):
                    pass  # Button logic handled in on_click            
        except Exception as e:
            st.warning(f"Unable to load deck preview for {deck_name}")
            print(f"Error rendering trending deck in sidebar: {e}")

def display_counter_picker_sidebar():
    """Display counter picker in sidebar with expander format"""
    
    # Banner image (same as before)
    banner_path = "picker_banner.png"
    if os.path.exists(banner_path):
        with open(banner_path, "rb") as f:
            banner_base64 = base64.b64encode(f.read()).decode()
        <div style="width:100%; text-align:center;">
            <hr style='margin-bottom:20px;  border: 0.5px solid #aaa; margin-top:-30px;'>
            <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px; margin-bottom:10px;">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.subheader("🎯 Meta Counter Picker")
    
    # Get list of top meta decks to choose from
    meta_decks = []
    meta_deck_info = {}
    
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        performance_data = st.session_state.performance_data
        
        for _, deck in performance_data.iterrows():
            meta_decks.append(deck['displayed_name'])
            meta_deck_info[deck['displayed_name']] = {
                'deck_name': deck['deck_name'],
                'set': deck['set'],
                'share': deck['share'],
                'power_index': deck['power_index']
            }
        
        # Limit to top 20 decks
        meta_decks = meta_decks[:20]
    
    if not meta_decks:
        st.warning("No meta deck data available")
        return
    
    # Multi-select for decks to counter - START WITH EMPTY SELECTION
    selected_decks = st.multiselect(
        "Select decks you want to counter:",
        options=meta_decks,
        default=[],
        help="Choose the decks you want to counter in the meta",
        key="counter_multiselect"  # Add key for stability
    )

    # Button to trigger analysis
    if st.button("Find Counters", type="secondary", use_container_width=True):
        if selected_decks:  # Only analyze if decks are selected
            # Store the analysis results in session state
            st.session_state.counter_analysis_results = analyze_counter_get_data(selected_decks)
            st.session_state.counter_selected_decks = selected_decks.copy()

    # Display results from session state (persists across reruns)
    if ('counter_analysis_results' in st.session_state and 
        not st.session_state.counter_analysis_results.empty):  # Changed this line
        display_counter_results(st.session_state.counter_analysis_results)
    # elif selected_decks:
    #     st.info("Click 'Find Counters' to analyze")
    # else:
    #     st.info("Select decks above to find counters")

def analyze_counter_get_data(selected_decks):
    """Get counter analysis data without displaying (for persistence)"""
    
    counter_data = []
    selected_internal_names = []
    
    # Convert displayed names to internal names
    for displayed in selected_decks:
        for _, meta_deck in st.session_state.performance_data.iterrows():
            if meta_deck['displayed_name'] == displayed:
                selected_internal_names.append(meta_deck['deck_name'])

    # Analyze each potential counter deck
    for _, deck in st.session_state.performance_data.iterrows():
        deck_name = deck['deck_name']
        set_name = deck['set']
        displayed_name = deck['displayed_name']
        
        matchups = fetch_matchup_data(deck_name, set_name)
        
        if matchups.empty:
            continue
        
        total_weighted_win_rate = 0
        total_matches = 0
        matched_decks = 0
        
        for _, matchup in matchups.iterrows():
            if matchup['opponent_deck_name'] in selected_internal_names:
                match_count = matchup['matches_played']
                total_weighted_win_rate += matchup['win_pct'] * match_count
                total_matches += match_count
                matched_decks += 1
        
        if (matched_decks >= len(selected_decks) / 2 and 
            total_matches >= MIN_COUNTER_MATCHES):
            avg_win_rate = total_weighted_win_rate / total_matches if total_matches > 0 else 0
            confidence = 'High' if total_matches >= 20 else 'Medium'
            
            counter_data.append({
                'deck_name': deck_name,
                'displayed_name': displayed_name,
                'set': set_name,
                'average_win_rate': avg_win_rate,
                'meta_share': deck['share'],
                'power_index': deck['power_index'],
                'matched_decks': matched_decks,
                'total_selected': len(selected_decks),
                'total_matches': total_matches,
                'confidence': confidence
            })
    
    if counter_data:
        counter_df = pd.DataFrame(counter_data)
        return counter_df.sort_values('average_win_rate', ascending=False)
    else:
        return pd.DataFrame()

def display_counter_results(counter_df):
    """Display counter analysis results from session state"""
    
    if counter_df.empty:
        st.warning("No reliable counter data found for the selected decks")
        return
    
    st.write("#### 🎯 Best Counters")
    
    # Render top 5 counter decks in expander format
    for i in range(min(5, len(counter_df))):
        deck = counter_df.iloc[i]
        
        # Format win rate as percentage for display
        win_rate = deck['average_win_rate']
        win_rate_display = f"{win_rate:.1f}%"
        
        # Create rank emoji
        rank_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        rank_emoji = rank_emojis[i] if i < len(rank_emojis) else f"#{i+1}"
        
        # Create expander title
        expander_title = f"{rank_emoji} {deck['displayed_name']} - {win_rate_display}"
        
        with st.expander(expander_title, expanded=(i == 0)):
            try:
                # USE CACHED HEADER IMAGE
                header_image = get_header_image_cached(deck['deck_name'], deck['set'])
                
                if header_image:
                    st.markdown(f"""
                    <div style="width: 100%; margin-bottom: 10px;">
                        <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border: 1px solid #aaa; border-radius: 6px;">
                    </div>
                    """, unsafe_allow_html=True)
                
                # USE CACHED SAMPLE DECK
                sample_deck = get_sample_deck_cached(deck['deck_name'], deck['set'])
                
                if sample_deck:
                    from card_renderer import render_sidebar_deck
                    deck_html = render_sidebar_deck(
                        sample_deck['pokemon_cards'], 
                        sample_deck['trainer_cards'],
                        card_width=60
                    )
                    st.markdown(deck_html, unsafe_allow_html=True)

                # Energy types and Details button
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # USE CACHED ENERGY TYPES
                    energy_types, is_typical = get_energy_types_for_deck(deck['deck_name'])
                    
                    if energy_types:
                        energy_html = render_energy_icons_cached(tuple(energy_types), is_typical)
                        st.markdown(energy_html, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="margin-bottom: 5px;">
                            <div style="font-size: 0.8rem; color: #888;">No energy data</div>
                        </div>
                        """, unsafe_allow_html=True)
                    # Details as caption at bottom
                    total_matches = deck['total_matches']
                    confidence = deck['confidence']
                    matched_decks = deck['matched_decks']
                    total_selected = deck['total_selected']
                    
                    confidence_emoji = "🟢" if confidence == 'High' else "🟡"
                    st.caption(f"{confidence_emoji} {total_matches} matches, {confidence.lower()} confidence • Counters {matched_decks}/{total_selected} selected decks")                        
                
                with col2:
                    if st.button("Details", key=f"counter_details_{deck['deck_name']}_{i}", type="tertiary", use_container_width=True):
                        st.session_state.deck_to_analyze = deck['deck_name']
                        st.rerun()
                
                
                
            except Exception as e:
                st.warning(f"Unable to load counter deck preview")
                print(f"Error rendering counter deck in sidebar: {e}")
    
    # Overall caption
    st.caption(f"Win rates weighted by match count • Minimum {MIN_COUNTER_MATCHES} matches required • Data from Limitless TCG")

# def analyze_counter_with_expanders(selected_decks):
#     """Analyze counter decks and display in expander format like Top 10 Meta"""
    
#     counter_data = []
#     selected_internal_names = []
    
#     # Convert displayed names to internal names
#     for displayed in selected_decks:
#         for _, meta_deck in st.session_state.performance_data.iterrows():
#             if meta_deck['displayed_name'] == displayed:
#                 selected_internal_names.append(meta_deck['deck_name'])

#     # Analyze each potential counter deck
#     for _, deck in st.session_state.performance_data.iterrows():
#         deck_name = deck['deck_name']
#         set_name = deck['set']
#         displayed_name = deck['displayed_name']
        
#         matchups = fetch_matchup_data(deck_name, set_name)
        
#         if matchups.empty:
#             continue
        
#         total_weighted_win_rate = 0
#         total_matches = 0
#         matched_decks = 0
        
#         for _, matchup in matchups.iterrows():
#             if matchup['opponent_deck_name'] in selected_internal_names:
#                 match_count = matchup['matches_played']
#                 total_weighted_win_rate += matchup['win_pct'] * match_count
#                 total_matches += match_count
#                 matched_decks += 1
        
#         if (matched_decks >= len(selected_decks) / 2 and 
#             total_matches >= MIN_COUNTER_MATCHES):
#             avg_win_rate = total_weighted_win_rate / total_matches if total_matches > 0 else 0
#             confidence = 'High' if total_matches >= 20 else 'Medium'
            
#             counter_data.append({
#                 'deck_name': deck_name,
#                 'displayed_name': displayed_name,
#                 'set': set_name,
#                 'average_win_rate': avg_win_rate,
#                 'meta_share': deck['share'],
#                 'power_index': deck['power_index'],
#                 'matched_decks': matched_decks,
#                 'total_selected': len(selected_decks),
#                 'total_matches': total_matches,
#                 'confidence': confidence
#             })
    
#     if counter_data:
#         counter_df = pd.DataFrame(counter_data)
#         counter_df = counter_df.sort_values('average_win_rate', ascending=False)
        
#         st.write("#### 🎯 Best Counters")
        
#         # Render top 5 counter decks in expander format
#         for i in range(min(5, len(counter_df))):
#             deck = counter_df.iloc[i]
            
#             # Format win rate as percentage for display
#             win_rate = deck['average_win_rate']
#             win_rate_display = f"{win_rate:.1f}%"
            
#             # Create rank emoji (similar to Top 10 Meta)
#             rank_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
#             rank_emoji = rank_emojis[i] if i < len(rank_emojis) else f"#{i+1}"
            
#             # Create expander title with emoji, name, and win rate
#             expander_title = f"{rank_emoji} {deck['displayed_name']} - {win_rate_display}"
            
#             with st.expander(expander_title, expanded=(i == 0)):  # Only expand first one
#                 try:
#                     # USE CACHED HEADER IMAGE
#                     header_image = get_header_image_cached(deck['deck_name'], deck['set'])
                    
#                     if header_image:
#                         st.markdown(f"""
#                         <div style="width: 100%; margin-bottom: 10px;">
#                             <img src="data:image/png;base64,{header_image}" style="width: 120%; height: auto; ">
#                         </div>
#                         """, unsafe_allow_html=True)
                    
#                     # USE CACHED SAMPLE DECK
#                     sample_deck = get_sample_deck_cached(deck['deck_name'], deck['set'])
                    
#                     if sample_deck:
#                         from card_renderer import render_sidebar_deck
#                         deck_html = render_sidebar_deck(
#                             sample_deck['pokemon_cards'], 
#                             sample_deck['trainer_cards'],
#                             card_width=60
#                         )
#                         st.markdown(deck_html, unsafe_allow_html=True)

#                     # Energy types and Details button
#                     col1, col2 = st.columns([2, 1])
                    
#                     with col1:
#                         # USE CACHED ENERGY TYPES
#                         energy_types, is_typical = get_energy_types_for_deck(deck['deck_name'])
                        
#                         if energy_types:
#                             energy_html = render_energy_icons_cached(tuple(energy_types), is_typical)
#                             st.markdown(energy_html, unsafe_allow_html=True)
#                         else:
#                             st.markdown("""
#                             <div style="margin-bottom: 5px;">
#                                 <div style="font-size: 0.8rem; color: #888;">No energy data</div>
#                             </div>
#                             """, unsafe_allow_html=True)
                    
#                     with col2:
#                         if st.button("Details", key=f"counter_details_{deck['deck_name']}_{i}", type="tertiary", use_container_width=True):
#                             st.session_state.deck_to_analyze = deck['deck_name']
#                             st.rerun()
                    
#                     # Details as caption at bottom
#                     total_matches = deck['total_matches']
#                     confidence = deck['confidence']
#                     matched_decks = deck['matched_decks']
#                     total_selected = deck['total_selected']
                    
#                     confidence_emoji = "🟢" if confidence == 'High' else "🟡"
#                     st.caption(f"{confidence_emoji} {total_matches} matches, {confidence.lower()} confidence • Counters {matched_decks}/{total_selected} selected decks")
                    
#                 except Exception as e:
#                     st.warning(f"Unable to load counter deck preview")
#                     print(f"Error rendering counter deck in sidebar: {e}")
        
#         # Overall caption for the counter analysis
#         st.caption(f"Win rates weighted by match count • Minimum {MIN_COUNTER_MATCHES} matches required • Data from Limitless TCG")
#     else:
#         st.warning("No reliable counter data found for the selected decks")
    
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

def get_confidence_indicator(matches, min_threshold):
    """Get confidence level and color for match count"""
    if matches >= min_threshold * 3:
        return "High", "#4FCC20"
    elif matches >= min_threshold * 2:
        return "Medium", "#FDA700" 
    elif matches >= min_threshold:
        return "Low", "#fd6c6c"
    else:
        return "Very Low", "#999"
        
def set_deck_to_analyze(deck_name):
    """Callback function when counter deck button is clicked"""
    # Set the deck to analyze
    st.session_state.deck_to_analyze = deck_name

# In ui_helpers.py - Add this new function

def render_trending_deck_in_sidebar(deck, expanded=False, rank=None):
    """Render a single trending deck in the sidebar with cached components"""
    tournaments_played = deck['tournaments_played']
    rank_symbol = "🚀"
    
    with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']} ", expanded=expanded):
        try:
            # USE CACHED HEADER IMAGE
            header_image = get_header_image_cached(deck['deck_name'], deck['set'])  # CHANGED
            
            if header_image:
                st.markdown(f"""
                <div style="width: 100%; margin-bottom: 10px;">
                    <img src="data:image/png;base64,{header_image}" style="width: 120%; height: auto; ">
                </div>
                """, unsafe_allow_html=True)
            
            # USE CACHED SAMPLE DECK
            deck_name = deck['deck_name']
            sample_deck = get_sample_deck_cached(deck_name, deck['set'])  # CHANGED
            
            from card_renderer import render_sidebar_deck
            deck_html = render_sidebar_deck(
                sample_deck['pokemon_cards'], 
                sample_deck['trainer_cards'],
                card_width=50
            )
            st.markdown(deck_html, unsafe_allow_html=True)

            col1, col2 = st.columns([2, 1])
            
            with col1:
                # USE CACHED ENERGY TYPES
                energy_types, is_typical = get_energy_types_for_deck(deck['deck_name'])
                
                if energy_types:
                    # USE CACHED ENERGY RENDERING
                    energy_html_compact = ""
                    for energy in energy_types:
                        energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
                        energy_html_compact += f'<img src="{energy_url}" alt="{energy}" style="height:30px; margin-right:2px; vertical-align:middle;">'
                    
                    st.markdown(f"""
                    <div style="margin-top:5px; ">
                        <div>{energy_html_compact}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="margin-bottom: 5px;">
                        <div style="font-size: 0.8rem; color: #888;">No energy data</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                if st.button("Details", key=f"trending_details_{deck['deck_name']}_{rank}", type="tertiary", use_container_width=True):
                    st.session_state.deck_to_analyze = deck['deck_name']
                    st.rerun()
            
            st.caption(f"Best Finishes: {tournaments_played}")
            
        except Exception as e:
            st.warning(f"Unable to load deck preview for {deck_name}")
            print(f"Error rendering trending deck in sidebar: {e}")
