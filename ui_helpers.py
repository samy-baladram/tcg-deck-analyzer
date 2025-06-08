import streamlit as st
from datetime import datetime
from cache_manager import load_or_update_tournament_data
from formatters import format_deck_name, format_deck_option
from scraper import get_popular_decks_with_performance
from utils import calculate_time_ago
import cache_manager
from config import POWER_INDEX_EXPLANATION, MIN_META_SHARE, TOURNAMENT_COUNT, MIN_COUNTER_MATCHES, MIN_WIN_RATE
import pandas as pd
import base64
import os
from display_tabs import fetch_matchup_data
from header_image_cache import get_header_image_cached

# Add this at the top of ui_helpers.py after imports
SIDEBAR_SECTIONS_CONFIG = {
    "meta": {
        "type": "meta",
        "banner_path": "sidebar_banner.webp",
        "fallback_title": "🏆 Top Meta Decks",
        "max_decks": 10,
        "show_key": "show_meta_decks",
        "button_key_prefix": "details",
        "rank_symbols": ["🥇", "🥈", "🥉", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"],
        "caption_template": lambda d: f"Power Index: {round(d['power_index'], 2)}",
        "sort_config": {
            "columns": ["power_index"],
            "ascending": [False],
            "method": "head",
            "count": 10
        },
        "description": f"Top performers from the past {TOURNAMENT_COUNT} tournaments",
        "sorting_note": "Sorted by their Power Index (see the bottom of sidebar)"
    },
    "trending": {
        "type": "trending", 
        "banner_path": "trending_banner.webp",
        "fallback_title": "📈 Trending Decks",
        "max_decks": 5,
        "show_key": "show_trending_decks", 
        "button_key_prefix": "trending_details",
        "rank_symbols": ["🚀"] * 10,  # Same symbol for all ranks
        "caption_template": lambda d: f"Best Finishes: {d['tournaments_played']} • Meta Share: {d['share']:.2f}%",
        "sort_config": {
            "columns": ["tournaments_played", "share"],
            "ascending": [False, True],
            "method": "head",
            "count": 5
        },
        "description": f"Most active from the past {TOURNAMENT_COUNT} tournaments",
        "sorting_note": "Sorted by tournament activity, then by lowest meta share"
    },
    "gems": {
        "type": "gems",
        "banner_path": "gems_banner.webp", 
        "fallback_title": "💎 Hidden Gems",
        "max_decks": 5,
        "show_key": "show_gems_decks",
        "button_key_prefix": "gem_details",
        "rank_symbols": ["💎"] * 10,  # Same symbol for all ranks
        "caption_template": lambda d: f"Win Rate: {d['win_rate']:.1f}% ({d.get('total_wins', 0)}-{d.get('total_losses', 0)}-{d.get('total_ties', 0)}) • Share: {d['share']:.2f}%",
        "filter_config": {
            "share_min": 0.05,
            "share_max": 0.5,
            "win_rate_min": 55,
            "total_games_min": 12
        },
        "sort_config": {
            "columns": ["win_rate"],
            "ascending": [False],
            "method": "head", 
            "count": 5
        },
        "description": f"Underrepresented from the past {TOURNAMENT_COUNT} tournaments",
        "sorting_note": "0.05-0.5% meta share, 55%+ win rate, 20+ games"
    },
    "counter_picker": {
        "type": "counter_picker",
        "banner_path": "picker_banner.webp",
        "fallback_title": "🎯 Meta Counter Picker",
        "max_source_decks": 20,  # Max meta decks to choose from
        "max_result_decks": 5,   # Max counter results to show
        "min_matches": MIN_COUNTER_MATCHES,
        "multiselect_key": "counter_multiselect",
        "rank_symbols": ["🥇", "🥈", "🥉", "④", "⑤"],
        "caption_template": lambda d, matches, confidence, matched, total: f"{confidence} {matches} matches, {confidence.lower()} confidence • Counters {matched}/{total} selected decks",
        "confidence_config": {
            "high_threshold": 20,
            "medium_threshold": 12,
            "low_threshold": 8
        }
    }
}

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
    """Check if tournament data needs updating and trigger deck refresh"""
    from datetime import datetime, timedelta
    from config import CACHE_TTL
    
    if 'performance_fetch_time' in st.session_state:
        time_since_update = datetime.now() - st.session_state.performance_fetch_time
        
        if time_since_update.total_seconds() > CACHE_TTL:
            if not st.session_state.get('update_running', False):
                st.session_state.update_running = True
                
                with st.spinner("Checking for new tournament data..."):
                    # CRITICAL FIX: Get old tournament count before update
                    old_performance_count = len(st.session_state.performance_data) if 'performance_data' in st.session_state else 0
                    
                    # Update tournament tracking (this will clear affected deck caches)
                    stats = cache_manager.update_tournament_tracking()
                    
                    # Update performance data
                    performance_df, performance_timestamp = load_or_update_tournament_data(force_update=True)
                    st.session_state.performance_data = performance_df
                    st.session_state.performance_fetch_time = performance_timestamp
                    
                    # Check if deck count changed (indicating new tournaments)
                    new_performance_count = len(performance_df)
                    
                    # If deck count changed or tournaments were updated, force refresh ALL decks
                    if (new_performance_count != old_performance_count or stats['updated_decks'] > 0):
                        print(f"Tournament data changed, clearing deck options cache to force dropdown refresh")
                        
                        # Clear deck options cache to force dropdown regeneration
                        if 'deck_options_cache' in st.session_state:
                            del st.session_state['deck_options_cache']
                        if 'deck_display_names' in st.session_state:
                            del st.session_state['deck_display_names']
                        if 'deck_name_mapping' in st.session_state:
                            del st.session_state['deck_name_mapping']
                        
                        # Force refresh current deck if any is selected
                        if 'analyze' in st.session_state:
                            current_deck = st.session_state.analyze.get('deck_name')
                            if current_deck:
                                print(f"Forcing refresh of current deck {current_deck} due to tournament update")
                                st.session_state.deck_to_analyze = current_deck
                                st.session_state.auto_refresh_in_progress = True
                                st.session_state.force_deck_refresh = True
                    
                    # Update card usage data
                    card_usage_df = cache_manager.aggregate_card_usage()
                    st.session_state.card_usage_data = card_usage_df
                    
                    st.session_state.update_running = False
                    
                    if stats['new_tournaments'] > 0 or new_performance_count != old_performance_count:
                        st.success(f"Updated with new tournament data: {old_performance_count} → {new_performance_count} decks")

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
        
        for rank, (_, deck) in enumerate(top_performing_decks.iterrows(), 1):  # ADD rank starting from 1
            display_name = f"{rank} - {deck['displayed_name']}"  # ADD rank prefix
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
            
            for rank, (_, row) in enumerate(popular_decks.iterrows(), 1):  # ADD rank starting from 1
                display_name = f"{rank}. {format_deck_option(row['deck_name'], row['share'])}"  # ADD rank prefix
                deck_display_names.append(display_name)
                deck_name_mapping[display_name] = {
                    'deck_name': row['deck_name'],
                    'set': row['set']
                }
        except Exception as e:
            print(f"Error creating deck options: {e}")
            display_name = "1. Example Deck (1.0)"  # ADD rank prefix
            deck_display_names.append(display_name)
            deck_name_mapping[display_name] = {
                'deck_name': 'example-deck',
                'set': 'A3'
            }
    
    # Cache the results (rest stays the same)
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
        # FIXED: Remove .upper() to maintain original case format (A3a, A3b, etc.)
        current_set = deck_info['set']
    
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
    help_text = f"Showing decks with meta share ≥ {MIN_META_SHARE}% and win rate ≥ {MIN_WIN_RATE}%, ordered by Power Index (details in sidebar).\nSource: [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET).\nUpdated {time_str}."

    # Display the selectbox
    selected_option = st.selectbox(
        label_text,
        deck_display_names,
        index=st.session_state.selected_deck_index,
        placeholder="Select a deck to analyze...",
        help=help_text,
        key="deck_select",
        on_change=on_deck_change,
    )
    
    return selected_option  
    
def get_filtered_deck_data(section_type):
    """Get filtered deck data based on section configuration"""
    if 'performance_data' not in st.session_state or st.session_state.performance_data.empty:
        return pd.DataFrame()
    
    config = SIDEBAR_SECTIONS_CONFIG.get(section_type)
    if not config:
        return pd.DataFrame()
    
    perf_data = st.session_state.performance_data.copy()
    
    # Ensure win_rate column exists
    if 'win_rate' not in perf_data.columns:
        perf_data['total_games'] = perf_data['total_wins'] + perf_data['total_losses'] + perf_data['total_ties']
        perf_data['win_rate'] = (
            (perf_data['total_wins'] + 0.5 * perf_data['total_ties']) / 
            perf_data['total_games'] * 100
        ).fillna(0)
    
    # Apply filters if specified
    if 'filter_config' in config:
        filter_cfg = config['filter_config']
        if 'total_games' not in perf_data.columns:
            perf_data['total_games'] = perf_data['total_wins'] + perf_data['total_losses'] + perf_data['total_ties']
        
        filtered_data = perf_data[
            (perf_data['share'] >= filter_cfg['share_min']) & 
            (perf_data['share'] <= filter_cfg['share_max']) & 
            (perf_data['win_rate'] >= filter_cfg['win_rate_min']) &
            (perf_data['total_games'] >= filter_cfg['total_games_min'])
        ]
        result_data = filtered_data
    else:
        result_data = perf_data
    
    # Apply sorting
    sort_cfg = config['sort_config']
    sorted_data = result_data.sort_values(sort_cfg['columns'], ascending=sort_cfg['ascending'])
    
    # Apply count limit
    if sort_cfg['method'] == 'head':
        return sorted_data.head(sort_cfg['count'])
    else:
        return sorted_data

# def render_unified_deck_in_sidebar(deck, section_config, rank=None, expanded=False):
#     """Unified function to render any type of deck in sidebar"""
#     try:
#         # Get rank symbol
#         if rank and rank <= len(section_config['rank_symbols']):
#             rank_symbol = section_config['rank_symbols'][rank-1]
#         else:
#             rank_symbol = section_config['rank_symbols'][0] if section_config['rank_symbols'] else ""
        
#         with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']} ", expanded=expanded):
#             try:
#                 # Header image
#                 header_image = get_header_image_cached(deck['deck_name'], deck['set'])
#                 if header_image:
#                     st.markdown(f"""
#                     <div style="width: 100%; margin-bottom: 10px;">
#                         <img src="data:image/png;base64,{header_image}" style="width: 120%; height: auto;">
#                     </div>
#                     """, unsafe_allow_html=True)
                
#                 # Sample deck
#                 deck_name = deck['deck_name']
#                 if CARD_CACHE_AVAILABLE:
#                     sample_deck = get_sample_deck_cached(deck_name, deck['set'])
#                 else:
#                     from scraper import get_sample_deck_for_archetype
#                     pokemon_cards, trainer_cards, energy_types = get_sample_deck_for_archetype(deck_name, deck['set'])
#                     sample_deck = {
#                         'pokemon_cards': pokemon_cards,
#                         'trainer_cards': trainer_cards,
#                         'energy_types': energy_types
#                     }
                
#                 from card_renderer import render_sidebar_deck
#                 deck_html = render_sidebar_deck(
#                     sample_deck['pokemon_cards'], 
#                     sample_deck['trainer_cards'],
#                     card_width=60
#                 )
#                 st.markdown(deck_html, unsafe_allow_html=True)

#                 # Energy and details section
#                 col1, col2 = st.columns([2, 1])
                
#                 with col1:
#                     energy_types, is_typical = get_energy_types_for_deck(deck['deck_name'])
                    
#                     if energy_types:
#                         if section_config['type'] == "gems":
#                             # Compact rendering for gems
#                             energy_html_compact = ""
#                             for energy in energy_types:
#                                 energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
#                                 energy_html_compact += f'<img src="{energy_url}" alt="{energy}" style="height:16px; margin-right:2px;">'
                            
#                             st.markdown(f"""
#                             <div style="margin-top:5px; margin-bottom:-5px;">
#                                 <p style="margin-bottom:5px;"><strong>Energy:</strong> {energy_html_compact}</p>
#                             </div>
#                             """, unsafe_allow_html=True)
#                         else:
#                             # Standard rendering
#                             energy_html = render_energy_icons_cached(tuple(energy_types), is_typical)
#                             st.markdown(energy_html, unsafe_allow_html=True)
#                     else:
#                         st.markdown("""
#                         <div style="margin-bottom: 5px;">
#                             <div style="font-size: 0.8rem; color: #888;">No energy data</div>
#                         </div>
#                         """, unsafe_allow_html=True)
                    
#                     # Display caption using template
#                     caption_text = section_config['caption_template'](deck)
#                     st.caption(caption_text)
                
#                 with col2:
#                     button_key = f"{section_config['button_key_prefix']}_{deck['deck_name']}_{rank}"
#                     if st.button("Details", key=button_key, type="tertiary", use_container_width=True):
#                         st.session_state.deck_to_analyze = deck['deck_name']
#                         st.rerun()
                
#             except Exception as e:
#                 st.warning(f"Unable to load deck preview for {deck_name}")
#                 print(f"Error rendering {section_config['type']} deck in sidebar: {e}")
#                 fallback_caption = section_config['caption_template'](deck)
#                 st.write(f"**{deck['displayed_name']}**")
#                 st.caption(fallback_caption)
                
#     except Exception as e:
#         print(f"Critical error in render_unified_deck_in_sidebar: {e}")
#         st.error("Error loading deck data")

# def create_deck_section(section_type):
#     """Create a unified deck section using configuration"""
#     config = SIDEBAR_SECTIONS_CONFIG.get(section_type)
#     if not config:
#         st.error(f"Unknown section type: {section_type}")
#         return
    
#     # Display banner
#     if os.path.exists(config['banner_path']):
#         banner_base64 = get_cached_banner_image(config['banner_path'])
#         if banner_base64:
#             st.markdown(f"""<div style="width:100%; text-align:center;">
#                 <hr style='margin-bottom:20px; border: 0.5px solid rgba(137, 148, 166, 0.2); margin-top:-25px;'>
#                 <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px;">
#             </div>
#             """, unsafe_allow_html=True)
#     else:
#         st.markdown(f"### {config['fallback_title']}")
    
#     # Get filtered data
#     deck_data = get_filtered_deck_data(section_type)
    
#     if deck_data.empty:
#         st.markdown("""
#         <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 6px;
#             display: flex; align-items: center; justify-content: center;">
#             <span style="color: #888; font-size: 0.8rem;">No data found</span>
#         </div>
#         """, unsafe_allow_html=True)
#         st.caption("No decks found matching criteria")
#         return
    
#     # Display first deck
#     first_deck = deck_data.iloc[0]
#     header_image = get_header_image_cached(first_deck['deck_name'], first_deck['set'])

#     if header_image:
#         st.markdown(f"""
#         <div style="width: 100%; margin-bottom: -1rem;">
#             <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border: 2px solid #000; border-radius: 8px;z-index:-1;">
#         </div>
#         """, unsafe_allow_html=True)
#     else:
#         st.markdown("""
#         <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 6px;
#             display: flex; align-items: center; justify-content: center;">
#             <span style="color: #888; font-size: 0.8rem;">No image</span>
#         </div>
#         """, unsafe_allow_html=True)
    
#     # 2-column layout for deck name and toggle button
#     col1, col2 = st.columns([3, 1])
    
#     with col1:         
#         if st.button(
#             first_deck['displayed_name'], 
#             key=f"first_{section_type}_deck_button",
#             type="tertiary",
#             use_container_width=False
#         ):
#             st.session_state.deck_to_analyze = first_deck['deck_name']
#             st.rerun()

#     with col2:
#         show_key = config['show_key']
#         if show_key not in st.session_state:
#             st.session_state[show_key] = False

#         button_text = "Close" if st.session_state[show_key] else "See More"
#         if st.button(button_text, type="tertiary", use_container_width=False, key=f"{section_type}_toggle_button"):
#             st.session_state[show_key] = not st.session_state[show_key]
#             st.rerun()

#     # Show expanded deck list if toggled
#     if st.session_state[show_key]:
#         with st.spinner(f"Loading {section_type} deck details..."):
#             import cache_manager
#             cache_manager.ensure_energy_cache()
            
#             decks_to_show = deck_data.head(config['max_decks'])
            
#             for idx, (_, deck) in enumerate(decks_to_show.iterrows()):
#                 rank = idx + 1
#                 render_unified_deck_in_sidebar(deck, config, rank=rank)
        
#         # Display disclaimer
#         display_section_disclaimer(config)
#     else:
#         st.write("")

def render_unified_deck_in_sidebar(deck, section_config, rank=None, expanded=False):
    """Unified function to render any type of deck in sidebar - LIGHTWEIGHT VERSION"""
    try:
        # Get rank symbol
        if rank and rank <= len(section_config['rank_symbols']):
            rank_symbol = section_config['rank_symbols'][rank-1]
        else:
            rank_symbol = section_config['rank_symbols'][0] if section_config['rank_symbols'] else ""
        
        # Calculate stats text
        if section_config['type'] == "meta":
            stats_text = f"Power {deck['power_index']:.2f}"
        elif section_config['type'] == "trending":
            stats_text = f"{deck['tournaments_played']} plays, {deck['share']:.2f}% share"
        elif section_config['type'] == "gems":
            stats_text = f"{deck['win_rate']:.1f}% win, {deck['share']:.2f}% share"
        else:
            stats_text = f"{deck['share']:.1f}% share"
        
        # Header image with stats overlay
        # Deck name as left-aligned button (single column)
        if st.button(
            f"{deck['displayed_name']}", 
            key=f"{section_config['button_key_prefix']}_{deck['deck_name']}_{rank}",
            type="tertiary",
            use_container_width=False
        ):
            st.session_state.deck_to_analyze = deck['deck_name']
            st.rerun()
            
        header_image = get_header_image_cached(deck['deck_name'], deck['set'])
        if header_image:
            st.markdown(f"""
            <div style="width: 100%; margin-top: -5px; margin-bottom: -5px; position: relative;">
                <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border: 2px solid #000; border-radius: 8px; z-index:-1;">
                <div style="position: absolute; top: 0px; left: 0px; background-color: rgba(0, 0, 0, 0.7); color: white; padding: 4px 4px; border-radius: 8px 0px 8px 0px; font-size: 0.8rem; font-weight: 700;">
                    {rank_symbol}
                </div>
                <div style="position: absolute; bottom: 0px; right: 0px; background-color: rgba(0, 0, 0, 0.7); color: white; padding: 2px 4px; border-radius: 6px 0px 8px 0px; font-size: 0.6rem; font-weight: 700;">
                    {stats_text}
                </div>
            </div>
            """, unsafe_allow_html=True)       
                
    except Exception as e:
        print(f"Error rendering {section_config['type']} deck in sidebar: {e}")
        st.error("Error loading deck data")

def create_deck_section(section_type):
    """Create a unified deck section using configuration - LIGHTWEIGHT VERSION"""
    config = SIDEBAR_SECTIONS_CONFIG.get(section_type)
    if not config:
        st.error(f"Unknown section type: {section_type}")
        return
    
    # Display banner
    if os.path.exists(config['banner_path']):
        banner_base64 = get_cached_banner_image(config['banner_path'])
        if banner_base64:
            st.markdown(f"""<div style="width:100%; text-align:center;">
                <hr style='margin-bottom:20px; border: 0.5px solid rgba(137, 148, 166, 0.2); margin-top:-25px;'>
                <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px;">
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"### {config['fallback_title']}")
    
    # Get filtered data
    deck_data = get_filtered_deck_data(section_type)
    
    if deck_data.empty:
        st.markdown("""
        <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 6px;
            display: flex; align-items: center; justify-content: center;">
            <span style="color: #888; font-size: 0.8rem;">No data found</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("No decks found matching criteria")
        return
    
    # Display first deck with emoji and stats overlay
    first_deck = deck_data.iloc[0]
    first_rank_symbol = config['rank_symbols'][0] if config['rank_symbols'] else ""
    header_image = get_header_image_cached(first_deck['deck_name'], first_deck['set'])

    # Calculate stats for featured deck
    if config['type'] == "meta":
        stats_text = f"Power {first_deck['power_index']:.1f}"
    elif config['type'] == "trending":
        stats_text = f"{first_deck['tournaments_played']} plays, {first_deck['share']:.1f}% share"
    elif config['type'] == "gems":
        stats_text = f"{first_deck['win_rate']:.1f}% win, {first_deck['share']:.1f}% share"
    else:
        stats_text = f"{first_deck['share']:.1f}% share"

    # Featured deck name with emoji (single column, shorter spacing)
    if st.button(
        f"{first_deck['displayed_name']}", 
        key=f"first_{section_type}_deck_button",
        type="tertiary",
        use_container_width=False
    ):
        st.session_state.deck_to_analyze = first_deck['deck_name']
        st.rerun()
        
    if header_image:
        st.markdown(f"""
        <div style="width: 100%; margin-top: -5px; margin-bottom: -5px; position: relative;">
            <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border: 2px solid #000; border-radius: 8px; z-index:-1;">
            <div style="position: absolute; top: 0px; left: 0px; background-color: rgba(0, 0, 0, 0.7); color: white; padding: 4px 4px; border-radius: 8px 0px 8px 0px; font-size: 0.8rem; font-weight: 700;">
                {first_rank_symbol}
            </div>
            <div style="position: absolute; bottom: 0px; right: 0px; background-color: rgba(0, 0, 0, 0.7); color: white; padding: 2px 4px; border-radius: 6px 0px 8px 0px; font-size: 0.6rem; font-weight: 700;">
                {stats_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 10px;
            display: flex; align-items: center; justify-content: center;">
            <span style="color: #888; font-size: 0.8rem;">No image</span>
        </div>
        """, unsafe_allow_html=True)  

    # Always show expander (no toggle button)
    with st.expander("More Decks", expanded=False):
        # Show remaining decks (skip first one)
        remaining_decks = deck_data.iloc[1:config['max_decks']]
        
        for idx, (_, deck) in enumerate(remaining_decks.iterrows()):
            rank = idx + 2  # Start from 2 since first deck is already shown
            render_unified_deck_in_sidebar(deck, config, rank=rank)
    
        # Add caption inside expander explaining stats
        if config['type'] == "meta":
            caption_text = "Shows Power Index values"
        elif config['type'] == "trending":
            caption_text = "Shows tournament best-finish plays and meta share"
        elif config['type'] == "gems":
            caption_text = "Shows win rate and meta share"
        else:
            caption_text = "Shows meta share percentages"
        
        st.caption(f"{config['description']}. {caption_text}")
        
def display_section_disclaimer(config):
    """Display section-specific disclaimer text"""
    performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
    
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
        <div>{config['description']}</div>
        <div>Updated {performance_time_str}</div>
    </div>
    <div style="font-size: 0.75rem; margin-bottom: 5px; color: #777;">
        {config['sorting_note']}
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.write("")
    st.write("")

def analyze_counter_matchups(selected_deck_names, config):
    """Analyze counter matchups using configuration"""
    counter_data = []
    
    # Convert displayed names to internal names
    selected_internal_names = []
    for displayed in selected_deck_names:
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
        
        # Apply filtering based on config
        min_coverage = len(selected_deck_names) / 2
        min_matches = config['min_matches']
        
        if matched_decks >= min_coverage and total_matches >= min_matches:
            avg_win_rate = total_weighted_win_rate / total_matches if total_matches > 0 else 0
            
            # Calculate confidence using config
            conf_cfg = config['confidence_config']
            if total_matches >= conf_cfg['high_threshold']:
                confidence = 'High'
                confidence_emoji = "🟢"
            elif total_matches >= conf_cfg['medium_threshold']:
                confidence = 'Medium'
                confidence_emoji = "🟡"
            else:
                confidence = 'Low'
                confidence_emoji = "🔴"
            
            counter_data.append({
                'deck_name': deck_name,
                'displayed_name': displayed_name,
                'set': set_name,
                'average_win_rate': avg_win_rate,
                'meta_share': deck['share'],
                'power_index': deck['power_index'],
                'matched_decks': matched_decks,
                'total_selected': len(selected_deck_names),
                'total_matches': total_matches,
                'confidence': confidence,
                'confidence_emoji': confidence_emoji
            })
    
    if counter_data:
        counter_df = pd.DataFrame(counter_data)
        return counter_df.sort_values('average_win_rate', ascending=False)
    else:
        return pd.DataFrame()

def render_counter_results(counter_df, config):
    """Render counter analysis results using unified approach"""
    if counter_df.empty:
        st.warning("No reliable counter data found for the selected decks")
        return
    
    st.write("#### 🎯 Best Counters")
    
    # Render results using unified pattern
    max_results = min(config['max_result_decks'], len(counter_df))
    
    for i in range(max_results):
        deck = counter_df.iloc[i]
        
        # Format data for display
        win_rate = deck['average_win_rate']
        win_rate_display = f"{win_rate:.1f}%"
        
        # Get rank symbol from config
        rank_symbol = config['rank_symbols'][i] if i < len(config['rank_symbols']) else f"#{i+1}"
        
        # Create expander title
        expander_title = f"{rank_symbol} {deck['displayed_name']} - {win_rate_display}"
        
        with st.expander(expander_title, expanded=(i == 0)):
            try:
                # Use unified deck rendering pattern
                render_counter_deck_content(deck, config, i)
                
            except Exception as e:
                st.warning(f"Unable to load counter deck preview")
                print(f"Error rendering counter deck in sidebar: {e}")
                # Fallback display
                st.write(f"**{deck['displayed_name']}**")
                st.caption(f"Win Rate: {win_rate_display}")
    
    # Overall caption using config
    st.caption(f"Win rates weighted by match count • Minimum {config['min_matches']} matches required • Data from Limitless TCG")

def render_counter_deck_content(deck, config, rank):
    """Render individual counter deck content using unified pattern"""
    # Header image (same as other sections)
    header_image = get_header_image_cached(deck['deck_name'], deck['set'])
    
    if header_image:
        st.markdown(f"""
        <div style="width: 100%; margin-bottom: 10px;">
            <img src="data:image/png;base64,{header_image}" style="width: 120%; height: auto;">
        </div>
        """, unsafe_allow_html=True)
    
    # Sample deck (same as other sections)
    if CARD_CACHE_AVAILABLE:
        sample_deck = get_sample_deck_cached(deck['deck_name'], deck['set'])
    else:
        from scraper import get_sample_deck_for_archetype
        pokemon_cards, trainer_cards, energy_types = get_sample_deck_for_archetype(deck['deck_name'], deck['set'])
        sample_deck = {
            'pokemon_cards': pokemon_cards,
            'trainer_cards': trainer_cards,
            'energy_types': energy_types
        }
    
    if sample_deck:
        from card_renderer import render_sidebar_deck
        deck_html = render_sidebar_deck(
            sample_deck['pokemon_cards'], 
            sample_deck['trainer_cards'],
            card_width=60
        )
        st.markdown(deck_html, unsafe_allow_html=True)

    # Energy types and Details button (same pattern as other sections)
    col1, col2 = st.columns([2, 1])
    
    with col1:
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
        
        # Counter-specific caption using template
        caption_text = f"{deck['confidence_emoji']} {config['caption_template'](deck, deck['total_matches'], deck['confidence'], deck['matched_decks'], deck['total_selected'])}"
        st.caption(caption_text)
    
    with col2:
        button_key = f"counter_details_{deck['deck_name']}_{rank}"
        if st.button("Details", key=button_key, type="tertiary", use_container_width=True):
            st.session_state.deck_to_analyze = deck['deck_name']
            st.rerun()

def display_counter_picker_sidebar():
    """Display counter picker using unified configuration approach"""
    config = SIDEBAR_SECTIONS_CONFIG['counter_picker']
    
    # Banner (same pattern as other sections)
    if os.path.exists(config['banner_path']):
        banner_base64 = get_cached_banner_image(config['banner_path'])
        if banner_base64:
            st.markdown(f"""<div style="width:100%; text-align:center;">
                <hr style='margin-bottom:20px; border: 0.5px solid rgba(137, 148, 166, 0.2); margin-top:-25px;'>
                <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px; margin-bottom:10px;">
            </div>
            """, unsafe_allow_html=True)
    else:
        st.subheader(config['fallback_title'])
    
    # Get meta deck options (using config)
    meta_decks, meta_deck_info = get_meta_deck_options(config['max_source_decks'])
    
    if not meta_decks:
        st.warning("No meta deck data available")
        return
    
    # Multi-select for decks to counter
    selected_decks = st.multiselect(
        "Select decks you want to counter:",
        options=meta_decks,
        default=[],
        help="Choose the decks you want to counter in the meta",
        key=config['multiselect_key']
    )

    # Analyze button
    if st.button("Find Counters", type="secondary", use_container_width=True):
        if selected_decks:
            # Store results using unified analysis
            st.session_state.counter_analysis_results = analyze_counter_matchups(selected_decks, config)
            st.session_state.counter_selected_decks = selected_decks.copy()

    # Display results from session state
    if ('counter_analysis_results' in st.session_state and 
        not st.session_state.counter_analysis_results.empty):
        render_counter_results(st.session_state.counter_analysis_results, config)

def get_meta_deck_options(max_decks):
    """Get meta deck options for counter picker"""
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
        
        # Limit to max_decks
        meta_decks = meta_decks[:max_decks]
    
    return meta_decks, meta_deck_info
    
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

def render_about_section():
    """Render the About & Contact section at the bottom of the sidebar"""
    with st.expander("🔗 About & Contact", expanded=False):
        st.markdown("""
        #### Behind the Scenes
        
        Built this during late nights analyzing PTCGP meta shifts. Started as a personal tool to track which meta decks were actually winning tournaments, then grew into... well, this.
        
        The Wilson Score algorithm for Power Index was inspired by Reddit's comment ranking system, seemed fitting for ranking decks too.
        
        #### Hit Me Up
        
        **Reddit:** [u/Myxas_](https://www.reddit.com/user/Myxas_/)  
        **Email:** [myxas.draxabalm@gmail.com](mailto:myxas.draxabalm@gmail.com)
        
        Always down to discuss meta trends, weird deck ideas, or if something breaks.
        
        #### Technical Notes
        
        - Scrapes Limitless TCG hourly for fresh tournament data (if any)
        - Aggressive caching minimizes server requests (0.3s delays between calls)
        - Card images load from CDN with local caching
        - All analysis runs client-side after data collection
        
        *Huge respect to Limitless TCG for providing the data foundation. This tool implements rate limiting and caching to be a good citizen of their infrastructure.*
        
        *Not affiliated with TPCi or Limitless - just a fan project.*
        """)

def render_sidebar_from_cache():
    """Render sidebar with fully unified configuration approach"""
    check_and_update_tournament_data()

    if 'performance_data' not in st.session_state or st.session_state.performance_data.empty:
        st.warning("No performance data available")
        return

    # Render all deck sections
    for section_type in ["meta", "trending", "gems"]:
        create_deck_section(section_type)

    # Render counter picker using unified approach
    with st.spinner("Loading counter picker..."):
        display_counter_picker_sidebar()
    
    # Rest remains the same...
    st.markdown("<hr style='margin:25px; border: 0.5px solid rgba(137, 148, 166, 0.2);'>", unsafe_allow_html=True)
    with st.expander("🔍 About the Power Index"):
        from datetime import datetime
        current_month_year = datetime.now().strftime("%B %Y")
        formatted_explanation = POWER_INDEX_EXPLANATION.format(
            tournament_count=TOURNAMENT_COUNT,
            current_month_year=current_month_year
        )
        st.markdown(formatted_explanation)
    
    render_about_section()
