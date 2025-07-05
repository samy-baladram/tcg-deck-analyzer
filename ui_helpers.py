import streamlit as st
from datetime import datetime
from formatters import format_deck_name, format_deck_option
from scraper import get_popular_decks_with_performance
from utils import calculate_time_ago
import cache_manager
import json
from config import POWER_INDEX_EXPLANATION, MIN_META_SHARE, TOURNAMENT_COUNT, MIN_COUNTER_MATCHES, MIN_WIN_RATE, CACHE_TTL
import pandas as pd
import base64
import os
from display_tabs import fetch_matchup_data
from header_image_cache import get_header_image_cached
from meta_table import display_meta_overview_table, display_meta_overview_table_with_buttons, MetaTableBuilder

# Replace the existing SIDEBAR_SECTIONS_CONFIG in ui_helpers.py with this:

SIDEBAR_SECTIONS_CONFIG = {
    "meta": {
        "type": "meta",
        "banner_path": "img/sidebar_banner.webp",
        "fallback_title": "🏆 Top Meta Decks",
        "max_decks": 10,
        "show_key": "show_meta_decks",
        "button_key_prefix": "details",
        "rank_symbols": ["🥇", "🥈", "🥉", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"],
        "caption_template": lambda d: f"{d['share_3d']:.2f}% share",
        "sort_config": {
            "columns": ["share_3d"],
            "ascending": [False],
            "method": "head",
            "count": 10
        },
        "description": "Most popular decks from the past 3 days",
        "sorting_note": "Sorted by 3-day meta share percentage"
    },
    "trending": {
        "type": "trending", 
        "banner_path": "img/trending_banner.webp",
        "fallback_title": "📈 Trending Decks",
        "max_decks": 5,
        "show_key": "show_trending_decks", 
        "button_key_prefix": "trending_details",
        "rank_symbols": ["🚀"] * 10,
        "caption_template": lambda d: f"+{(d['share_7d'] - d['share_3d']):.2f}% share, {d['ratio']:.1f}x more play",
        "filter_config": {
            "ratio_min": 1.0
        },
        "sort_config": {
            "columns": ["trending_score"],
            "ascending": [False],
            "method": "head", 
            "count": 5
        },
        "description": "Decks gaining momentum (3d vs 7d share ratio > 1.0)",
        "sorting_note": "Sorted by trending momentum (3d-share × ratio)"
    },
    "gems": {
        "type": "gems",
        "banner_path": "img/gems_banner.webp", 
        "fallback_title": "💎 Hidden Gems",
        "max_decks": 5,
        "show_key": "show_gems_decks",
        "button_key_prefix": "gems_details",
        "rank_symbols": ["💎"] * 10,
        "caption_template": lambda d: f"{d['win_rate']:.1f}% win, {d['share_3d']:.2f}% share",
        "filter_config": {
            "win_rate_min": 50.0,
            "share_3d_max": 1.0,
            "total_games_min": 10
        },
        "sort_config": {
            "columns": ["gems_score"],
            "ascending": [False],
            "method": "head",
            "count": 5
        },
        "description": "High win rate decks (>50%) with low representation (<1% share, ≥10 games)", 
        "sorting_note": "Sorted by (Win Rate-50%) × (1-Share-3d) potential"
    },
    "counter_picker": {
        "type": "counter_picker",
        "banner_path": "img/picker_banner.webp",
        "fallback_title": "🎯 Counter Picker",
        "max_source_decks": 20,
        "max_counter_results": 8,
        "multiselect_key": "counter_target_decks",
        "button_key_prefix": "counter_details",
        "caption_template": lambda deck, total_matches, confidence, matched_decks, total_selected: f"vs {matched_decks}/{total_selected} decks ({total_matches} matches)",
        "description": "Find decks that counter the current meta",
        "sorting_note": "Sorted by win rate against selected meta decks"
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

def preload_sidebar_deck_images():
    """Pre-generate and cache images for all sidebar decks on startup"""
    try:
        # Get all deck data that will be shown in sidebar
        meta_data = get_filtered_deck_data("meta")
        trending_data = get_filtered_deck_data("trending") 
        gems_data = get_filtered_deck_data("gems")
        
        all_sidebar_decks = []
        if not meta_data.empty:
            all_sidebar_decks.extend(meta_data.to_dict('records'))
        if not trending_data.empty:
            all_sidebar_decks.extend(trending_data.to_dict('records'))
        if not gems_data.empty:
            all_sidebar_decks.extend(gems_data.to_dict('records'))
        
        # Pre-generate images for each deck
        for deck in all_sidebar_decks:
            deck_name = deck.get('deck_name', '')
            set_name = deck.get('set', 'A3')
            
            # REMOVE: Direct cache access - this was causing the error
            # cache_key = f"{deck_name}"
            # if cache_key in _header_image_cache:
            #     continue
                
            # FIX: Use proper cache function instead
            print(f"Pre-generating image for: {deck_name}")
            get_header_image_cached(deck_name, set_name, analysis_results=None)
            
    except Exception as e:
        print(f"Error pre-loading sidebar images: {e}")
        
# ADD: Cache for popular decks data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cached_popular_decks():
    """Cache popular decks data to avoid repeated API calls"""
    return get_popular_decks_with_performance()

def check_and_update_tournament_data():
    """Simple placeholder - we use meta_table directly now"""
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    
    # Set proper DataFrame placeholder to prevent .empty errors
    if 'performance_data' not in st.session_state:
        # Create empty DataFrame with expected columns
        st.session_state.performance_data = pd.DataFrame(columns=[
            'deck_name', 'displayed_name', 'share', 'total_wins', 
            'total_losses', 'total_ties', 'power_index', 'tournaments_played', 'set'
        ])
        st.session_state.performance_fetch_time = datetime.now()
    
    print("DEBUG: Using meta_table data directly (performance_data is empty placeholder)")

                    
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
            
def display_banner(img_path, max_width=500):
    """Display the app banner image with caching"""
    # USE CACHED VERSION
    img_base64 = get_cached_banner_image(img_path)
    
    if img_base64:
        st.markdown(f"""<div style="display: flex; justify-content: center; width: 100%; margin-top:10px; margin-bottom:0px;">
            <img src="data:image/png;base64,{img_base64}" style="width: 100%; max-width: {max_width}px;  height: auto; margin-top:-70px;">
        </div>
        """, unsafe_allow_html=True)

def load_initial_data():
    """Load only essential initial data for fast app startup"""
    # Initialize minimal caches first
    cache_manager.init_caches()
    
    # Initialize session state variables
    if 'selected_deck_index' not in st.session_state:
        st.session_state.selected_deck_index = None
        
    if 'deck_to_analyze' not in st.session_state:
        st.session_state.deck_to_analyze = None
    
    # Ensure we have deck list data before continuing
    if 'deck_list' not in st.session_state:
        st.session_state.deck_list = get_cached_popular_decks()
        st.session_state.fetch_time = datetime.now()
        print("DEBUG: Loaded initial deck list data")
        
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
            
            # Directly update analyze (NO flags needed)
            st.session_state.analyze = {
                'deck_name': new_deck_name,
                'set_name': new_set_name,
            }
            
            print(f"DEBUG: Switched to deck: {new_deck_name}")
    else:
        st.session_state.selected_deck_index = None
    
# Replace the existing get_filtered_deck_data function in ui_helpers.py with this:

def get_filtered_deck_data(section_type):
    """Get filtered deck data based on section configuration using Extended Meta Trend Table"""
    
    # Use Extended Meta Trend Table data instead of performance_data
    from meta_table import MetaTableBuilder
    
    try:
        builder = MetaTableBuilder()
        extended_df = builder.build_complete_meta_table(100)
        
        if extended_df.empty:
            return pd.DataFrame()
        
        # Add formatted display names if not present
        if 'displayed_name' not in extended_df.columns:
            extended_df['displayed_name'] = extended_df['deck_name'].apply(format_deck_name)
        
        # Add set column if not present
        if 'set' not in extended_df.columns:
            extended_df['set'] = 'A3a'
            
    except Exception as e:
        print(f"Error loading Extended Meta Trend Table: {e}")
        return pd.DataFrame()
    
    config = SIDEBAR_SECTIONS_CONFIG.get(section_type)
    if not config:
        return pd.DataFrame()
    
    result_data = extended_df.copy()
    
    # Calculate missing columns if needed
    if 'ratio' not in result_data.columns:
        result_data['ratio'] = result_data['share_3d'] / result_data['share_7d'].replace(0, 0.01)  # Avoid division by zero
    
    # Apply section-specific filters and calculations
    if section_type == "trending":
        # Filter: ratio > 1.0
        if 'filter_config' in config:
            filter_cfg = config['filter_config']
            result_data = result_data[result_data['ratio'] >= filter_cfg['ratio_min']]
        
        # Calculate trending score: Share-3d * Ratio
        result_data['trending_score'] = result_data['share_3d'] * result_data['ratio']
        
    elif section_type == "gems":
        # Safely calculate total games, checking if columns exist
        if all(col in result_data.columns for col in ['wins', 'losses', 'ties']):
            result_data['total_games'] = result_data['wins'] + result_data['losses'] + result_data['ties']
        else:
            print("Warning: wins/losses/ties columns missing from Extended Meta Trend Table")
            result_data['total_games'] = 0  # Default to 0 if columns missing
        
        # Filter: Win Rate > 50%, Share-3d < 1%, and Total Games >= 10
        if 'filter_config' in config:
            filter_cfg = config['filter_config']
            result_data = result_data[
                (result_data['win_rate'] >= filter_cfg['win_rate_min']) & 
                (result_data['share_3d'] <= filter_cfg['share_3d_max']) &
                (result_data['total_games'] >= filter_cfg['total_games_min'])
            ]
        
        # Calculate gems score: (Win Rate-0.5)*(1-Share-3d)
        result_data['gems_score'] = (result_data['win_rate'] - 50.0) * (1 - result_data['share_3d']/100)
    
    # Apply sorting
    sort_cfg = config['sort_config']
    sorted_data = result_data.sort_values(sort_cfg['columns'], ascending=sort_cfg['ascending'])
    
    # Apply count limit
    if sort_cfg['method'] == 'head':
        return sorted_data.head(sort_cfg['count'])
    else:
        return sorted_data

def get_latest_set_code():
    """Get the latest set code and name from sets_index.json"""
    try:
        with open("meta_analysis/sets_index.json", 'r') as f:
            sets_data = json.load(f)
        
        # Filter sets with release dates and sort by date (newest first)
        sets_with_dates = [s for s in sets_data['sets'] if s.get('release_date')]
        
        if sets_with_dates:
            latest_set = sorted(sets_with_dates, key=lambda x: x['release_date'], reverse=True)[0]
            return {
                'set_name': latest_set['set_name'],
                'set_code': latest_set['set_code']
            }
            
    except Exception as e:
        print(f"Error getting latest set info: {e}")
    
    return None

def create_deck_options():
    """Create deck options for dropdown using Extended Meta Trend Table sorted by Share-7d"""
    
    # Check cache first
    if ('deck_options_cache' in st.session_state and 
        st.session_state.deck_options_cache):
        return (st.session_state.deck_options_cache['display_names'], 
                st.session_state.deck_options_cache['name_mapping'])
    
    deck_display_names = []
    deck_name_mapping = {}
    
    # Get latest set code for reference
    latest_set_info = get_latest_set_code()
    latest_set_code = latest_set_info['set_code'] if latest_set_info else 'A3a'
    
    try:
        # Use Extended Meta Trend Table instead of performance_data
        from meta_table import MetaTableBuilder
        
        builder = MetaTableBuilder()
        extended_df = builder.build_complete_meta_table(100)
        
        if not extended_df.empty:
            # Sort by share_3d (descending) for dropdown ranking
            extended_df = extended_df.sort_values('share_3d', ascending=False)
            
            for idx, (_, row) in enumerate(extended_df.iterrows()):
                rank = idx + 1
                display_name = f"{rank}. {format_deck_option(row['deck_name'], row['share_3d'])}"
                deck_display_names.append(display_name)
                
                # Preserve original set information
                original_set = row.get('set', latest_set_code)
                deck_name_mapping[display_name] = {
                    'deck_name': row['deck_name'],
                    'set': original_set
                }
        else:
            display_name = "1. Example Deck (1.0%)"
            deck_display_names.append(display_name)
            deck_name_mapping[display_name] = {
                'deck_name': 'example-deck',
                'set': latest_set_code
            }
            
    except Exception as e:
        print(f"Error creating deck options from Extended Meta Trend Table: {e}")
        display_name = "1. Example Deck (1.0%)"
        deck_display_names.append(display_name)
        deck_name_mapping[display_name] = {
            'deck_name': 'example-deck',
            'set': latest_set_code
        }
    
    # Cache the results
    if extended_df is not None and not extended_df.empty:
        data_hash = hash(str(extended_df.to_dict()))
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
    """Get the latest set code and name from sets_index.json"""
    try:
        with open("meta_analysis/sets_index.json", 'r') as f:
            sets_data = json.load(f)
        
        # Filter sets with release dates and sort by date (newest first)
        sets_with_dates = [s for s in sets_data['sets'] if s.get('release_date')]
        
        if sets_with_dates:
            latest_set = sorted(sets_with_dates, key=lambda x: x['release_date'], reverse=True)[0]
            return {
                'set_name': latest_set['set_name'],
                'set_code': latest_set['set_code']
            }
            
    except Exception as e:
        print(f"Error getting latest set info: {e}")
    
    return None

def create_deck_selector():
    """Create and display the deck selector dropdown with minimal loading"""

    # Initialize session state variables if they don't exist
    if 'selected_deck_index' not in st.session_state:
        st.session_state.selected_deck_index = None
        
    # Handle deck_to_analyze ONLY if dropdown already existed (not fresh load)
    preserved_deck = None
    if ('deck_to_analyze' in st.session_state and 
        st.session_state.deck_to_analyze and 
        'deck_display_names' in st.session_state):
        
        target_deck = st.session_state.deck_to_analyze
        print(f"DEBUG: Processing deck_to_analyze: {target_deck}")
        preserved_deck = target_deck
        st.session_state.deck_to_analyze = None
        
    # Only compute dropdown options if not already cached
    if 'deck_display_names' not in st.session_state:
        # Get deck options
        deck_display_names, deck_name_mapping = create_deck_options()
        
        # Store for reuse
        st.session_state.deck_display_names = deck_display_names
        st.session_state.deck_name_mapping = deck_name_mapping
        
        # Simple default selection - just use first deck
        st.session_state.selected_deck_index = 0
        
        if deck_display_names:
            selected_deck_display = deck_display_names[0]
            selected_deck_info = deck_name_mapping[selected_deck_display]
            st.session_state.analyze = {
                'deck_name': selected_deck_info['deck_name'],
                'set_name': selected_deck_info['set'],
            }
            print(f"DEBUG: Set initial deck: {selected_deck_info['deck_name']}")
 
    else:
        # Use cached options
        deck_display_names = st.session_state.deck_display_names
        deck_name_mapping = st.session_state.deck_name_mapping
        
        # Only set default if no valid selection exists
        if (st.session_state.selected_deck_index is None or 
            st.session_state.selected_deck_index >= len(deck_display_names) or
            'analyze' not in st.session_state):
            
            # Simple fallback to first deck
            st.session_state.selected_deck_index = 0
            
            if deck_display_names:
                selected_deck_display = deck_display_names[0]
                selected_deck_info = deck_name_mapping[selected_deck_display]
                st.session_state.analyze = {
                    'deck_name': selected_deck_info['deck_name'],
                    'set_name': selected_deck_info['set'],
                }
                print(f"DEBUG: Set fallback deck: {selected_deck_info['deck_name']}")

    # Process preserved deck ONLY if it's from a tournament update
    if preserved_deck:
        print(f"DEBUG: Looking for preserved deck: {preserved_deck}")
        
        found_match = False
        for i, display_name in enumerate(deck_display_names):
            deck_info = deck_name_mapping[display_name]
            if deck_info['deck_name'] == preserved_deck:
                print(f"DEBUG: Found preserved deck at index {i}: {display_name}")
                
                st.session_state.selected_deck_index = i
                st.session_state.analyze = {
                    'deck_name': deck_info['deck_name'],
                    'set_name': deck_info['set'],
                }
                
                if st.session_state.get('auto_refresh_in_progress', False):
                    st.session_state.force_deck_refresh = True
                    del st.session_state.auto_refresh_in_progress
                
                found_match = True
                break
        
        if not found_match:
            print(f"DEBUG: Preserved deck not found in new rankings: {preserved_deck}")

    # Calculate time ago
    time_str = calculate_time_ago(st.session_state.fetch_time)
    
    # ENHANCED: Get latest set name and code from JSON file for label
    latest_set_info = get_latest_set_code()
    if latest_set_info:
        #label_text = f"Current Set: {latest_set_info['set_name']} ({latest_set_info['set_code']})"
        label_text = ""
    else:
        label_text = "Current Set: A3a"
    help_text = f"Ranked by 3-day meta share percentage from all tournaments in the past 3 days.  \nSource: [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET).  Updated {time_str}."

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
    
def render_unified_deck_in_sidebar(deck, section_config, rank=None, expanded=False):
    """Unified function to render any type of deck in sidebar - LIGHTWEIGHT VERSION"""
    try:
        # Get rank symbol
        if rank and rank <= len(section_config['rank_symbols']):
            rank_symbol = section_config['rank_symbols'][rank-1]
        else:
            rank_symbol = section_config['rank_symbols'][0] if section_config['rank_symbols'] else ""
        
        # Calculate stats text based on section type
        if section_config['type'] == "meta":
            stats_text = f"{deck['share_3d']:.2f}% share"
        elif section_config['type'] == "trending":
            share_diff = deck['share_3d'] - deck['share_7d']
            stats_text = f"+{share_diff:.2f}% share, {deck['ratio']:.1f}x more play"
        elif section_config['type'] == "gems":
            stats_text = f"{deck['win_rate']:.1f}% win, {deck['share_3d']:.2f}% share"
        else:
            stats_text = f"{deck['share_3d']:.1f}% share"
        
        # Deck name as left-aligned button (single column)
        if st.button(
            f"{rank_symbol} {deck['displayed_name']}", 
            key=f"{section_config['button_key_prefix']}_{deck['deck_name']}_{rank}",
            type="tertiary",
            use_container_width=False
        ):
            st.session_state.deck_to_analyze = deck['deck_name']
            st.rerun()
            
        # Display header image with original styling
        
        header_image = get_header_image_cached(deck['deck_name'], deck['set'])
        if header_image:
            st.markdown(f"""
            <div style="width: 100%; margin-top: -16px; margin-bottom: 7px; position: relative;">
                <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border-radius: 4px; z-index:-1;">
                <div style="position: absolute; bottom: 0px; right: 0px; background-color: rgba(38, 39, 48, 0.75); color: lightcyan; padding: 2px 4px; border-radius: 4px 0px 4px 0px; font-size: 0.7rem; font-weight: 500;">
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
            st.markdown(f"""<div style="width:100%; text-align:left; ">
                <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:210px; margin-top: 0px;">
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
    # In ui_helpers.py, find the section where featured deck stats are calculated and replace with:
    
    # Update the stats_text calculation in the featured deck display section:
    if config['type'] == "meta":
        stats_text = f"{first_deck['share_3d']:.2f}% share"
    elif config['type'] == "trending":
        share_diff = first_deck['share_3d'] - first_deck['share_7d']
        stats_text = f"+{share_diff:.2f}% share, {first_deck['ratio']:.1f}x more play"
    elif config['type'] == "gems":
        stats_text = f"{first_deck['win_rate']:.1f}% win, {first_deck['share_3d']:.2f}% share"
    else:
        stats_text = f"{first_deck['share_3d']:.1f}% share"

    # Featured deck name with emoji (single column, shorter spacing)
    if st.button(
        f"{first_rank_symbol} {first_deck['displayed_name']}", 
        key=f"first_{section_type}_deck_button",
        type="tertiary",
        use_container_width=False
    ):
        st.session_state.deck_to_analyze = first_deck['deck_name']
        st.rerun()
        
    if header_image:
        st.markdown(f"""
        <div style="width: 100%; margin-top: -18px; position: relative;">
            <img src="data:image/png;base64,{header_image}" style="width: 100%; height: auto; border-radius: 6px 6px 0px 0px; margin-bottom: -7px; z-index:-2;">
            <div style="position: absolute; bottom: 0px; right: 0px; background-color: rgba(38, 39, 48, 0.8); color: lightcyan; padding: 2px 4px; margin-bottom: -7px; border-radius: 4px 0px 0px 0px; font-size: 0.7rem; font-weight: 500;">
                {stats_text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="width: 100%; margin-top: -18px; height: 60px; background-color: #f0f0f0; border-radius: 6px;
            display: flex; align-items: center; justify-content: center;">
            <span style="color: #888; font-size: 0.8rem;">No image</span>
        </div>
        """, unsafe_allow_html=True)  

    # Always show expander (no toggle button)
    with st.expander("More decks", expanded=False):
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
        
        st.caption(f"{config['description']}. {config['sorting_note']}")
    #st.write("")
    #st.write("")
    #st.write("")
    #st.markdown(f"""<hr style='margin-bottom:40px; border: 0.5px solid rgba(137, 148, 166, 0.3); margin-top:0px;'>""", unsafe_allow_html=True)        
     

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
        <div style="width: 100%; margin-top: -30px; margin-bottom: 10px;">
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
            st.markdown(f"""<div style="width:100%; text-align:left; margin-bottom:5px;">               
                <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:210px; margin-top: 0px;">
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
    """Render sidebar with tabbed interface"""
    check_and_update_tournament_data()

    # Add last update caption at the very top
    if 'performance_fetch_time' in st.session_state:
        performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
        update_text = f"Data updated {performance_time_str}"
 
    st.markdown(f"""
    <div style="font-size: 0.85rem; color: rgb(163, 168, 184);  margin-top: -50px; margin-bottom: 10px; text-align: left;">
        {update_text}
    </div>
    """, unsafe_allow_html=True)
    
    # Create three tabs in sidebar
    tab1, tab2 = st.tabs(["Top Lists", "Meta Trend"])
    #tab1, tab2, tab3, tab4 = st.tabs(["Meta", "Trend", "Gainers", "Losers"])

    
    with tab1:
        # Render all deck sections
        create_deck_section("meta")
        create_deck_section("trending")
        create_deck_section("gems")
        
        # # Render counter picker using unified approach
        # with st.spinner("Loading counter picker..."):
        #     display_counter_picker_sidebar()
        
        # Rest of current content...
        st.markdown("<hr style='margin:25px; border: 0.5px solid rgba(137, 148, 166, 0.2);'>", unsafe_allow_html=True)
        # with st.expander("🔍 About the Power Index"):
        #     from datetime import datetime
        #     current_month_year = datetime.now().strftime("%B %Y")
        #     formatted_explanation = POWER_INDEX_EXPLANATION.format(
        #         tournament_count=TOURNAMENT_COUNT,
        #         current_month_year=current_month_year
        #     )
        #     st.markdown(formatted_explanation)
        
        render_about_section()
    
    with tab2:
        # Empty tab for experimental tools
        display_meta_overview_table()
        # st.divider()
        # st.write("Experimental")
        # display_meta_overview_table_with_buttons()
    
    # with tab3:
    #     from meta_table import display_gainers_table
    #     display_gainers_table()
    
    # with tab4:
    #     from meta_table import display_losers_table
    #     display_losers_table()
