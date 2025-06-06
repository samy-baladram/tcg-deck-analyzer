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

def render_unified_deck_in_sidebar(deck, deck_type="meta", expanded=False, rank=None):
    """
    Unified function to render any type of deck in sidebar with cached components
    
    Args:
        deck: Deck data dictionary
        deck_type: Type of deck ("meta", "trending", "gems")
        expanded: Whether expander should be expanded
        rank: Rank number for display
    """
    try:
        # Define type-specific configurations
        type_configs = {
            "meta": {
                "rank_symbol": ["⓪", "🥇", "🥈", "🥉", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"][rank] if rank and 0 <= rank <= 10 else "",
                "caption_template": lambda d: f"Power Index: {round(d['power_index'], 2)}",
                "button_key_prefix": "details"
            },
            "trending": {
                "rank_symbol": "🚀",
                "caption_template": lambda d: f"Best Finishes: {d['tournaments_played']} • Meta Share: {d['share']:.2f}%",
                "button_key_prefix": "trending_details"
            },
            "gems": {
                "rank_symbol": "💎",
                "caption_template": lambda d: f"Win Rate: {d['win_rate']:.1f}% ({d.get('total_wins', 0)}-{d.get('total_losses', 0)}-{d.get('total_ties', 0)}) • Share: {d['share']:.2f}%",
                "button_key_prefix": "gem_details"
            }
        }
        
        config = type_configs.get(deck_type, type_configs["meta"])
        rank_symbol = config["rank_symbol"]
        
        with st.sidebar.expander(f"{rank_symbol} {deck['displayed_name']} ", expanded=expanded):
            try:
                # 1. USE CACHED HEADER IMAGE
                header_image = get_header_image_cached(deck['deck_name'], deck['set'])
                
                if header_image:
                    st.markdown(f"""
                    <div style="width: 100%; margin-bottom: 10px;">
                        <img src="data:image/png;base64,{header_image}" style="width: 120%; height: auto;">
                    </div>
                    """, unsafe_allow_html=True)
                
                # 2. USE CACHED SAMPLE DECK
                deck_name = deck['deck_name']
                
                if CARD_CACHE_AVAILABLE:
                    sample_deck = get_sample_deck_cached(deck_name, deck['set'])
                else:
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

                # 3. USE CACHED ENERGY TYPES AND DETAILS BUTTON
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    energy_types, is_typical = get_energy_types_for_deck(deck['deck_name'])
                    
                    if energy_types:
                        # Special compact rendering for gems type
                        if deck_type == "gems":
                            energy_html_compact = ""
                            for energy in energy_types:
                                energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
                                energy_html_compact += f'<img src="{energy_url}" alt="{energy}" style="height:16px; margin-right:2px;">'
                            
                            st.markdown(f"""
                            <div style="margin-top:5px; margin-bottom:-5px;">
                                <p style="margin-bottom:5px;"><strong>Energy:</strong> {energy_html_compact}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # USE CACHED ENERGY ICON RENDERING (STANDARD)
                            energy_html = render_energy_icons_cached(tuple(energy_types), is_typical)
                            st.markdown(energy_html, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="margin-bottom: 5px;">
                            <div style="font-size: 0.8rem; color: #888;">No energy data</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Display type-specific caption
                    caption_text = config["caption_template"](deck)
                    st.caption(caption_text)
                
                with col2:
                    button_key = f"{config['button_key_prefix']}_{deck['deck_name']}_{rank}"
                    if st.button("Details", key=button_key, type="tertiary", use_container_width=True):
                        st.session_state.deck_to_analyze = deck['deck_name']
                        st.rerun()
                
            except Exception as e:
                st.warning(f"Unable to load deck preview for {deck_name}")
                print(f"Error rendering {deck_type} deck in sidebar: {e}")
                # Show basic info as fallback
                st.write(f"**{deck['displayed_name']}**")
                fallback_caption = config["caption_template"](deck)
                st.caption(fallback_caption)
                
    except Exception as e:
        print(f"Critical error in render_unified_deck_in_sidebar: {e}")
        st.error("Error loading deck data")

def create_deck_section(section_type, banner_path, fallback_title, data_source, max_decks=10):
   """
   Create a unified deck section with banner, first deck display, and expandable list
   
   Args:
       section_type: Type of section ("meta", "trending", "gems")
       banner_path: Path to banner image
       fallback_title: Fallback title if no banner
       data_source: DataFrame with deck data
       max_decks: Maximum number of decks to show in expanded view
   """
   # Display banner
   if os.path.exists(banner_path):
       banner_base64 = get_cached_banner_image(banner_path)
       if banner_base64:
           st.markdown(f"""<div style="width:100%; text-align:center;">
               <hr style='margin-bottom:20px; border: 0.5px solid rgba(137, 148, 166, 0.2); margin-top:-25px;'>
               <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px;">
           </div>
           """, unsafe_allow_html=True)
   else:
       st.markdown(f"### {fallback_title}")
   
   # Use data_source directly (it's already a DataFrame)
   deck_data = data_source
   
   if deck_data.empty:
       # No data available
       st.markdown("""
       <div style="width: 100%; height: 60px; background-color: #f0f0f0; border-radius: 6px;
           display: flex; align-items: center; justify-content: center;">
           <span style="color: #888; font-size: 0.8rem;">No data found</span>
       </div>
       """, unsafe_allow_html=True)
       st.caption("No decks found matching criteria")
       return
   
   # Display first deck
   first_deck = deck_data.iloc[0]
   
   # Generate header image for first deck
   header_image = get_header_image_cached(first_deck['deck_name'], first_deck['set'])

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
   
   # 2-column layout for deck name and See More button
   col1, col2 = st.columns([3, 1])
   
   with col1:         
       # Button to switch to this deck
       if st.button(
           first_deck['displayed_name'], 
           key=f"first_{section_type}_deck_button",
           type="tertiary",
           use_container_width=False
       ):
           st.session_state.deck_to_analyze = first_deck['deck_name']
           st.rerun()

   with col2:
       # Toggle button for expanded view
       show_key = f'show_{section_type}_decks'
       if show_key not in st.session_state:
           st.session_state[show_key] = False

       button_text = "Close" if st.session_state[show_key] else "See More"
       if st.button(button_text, type="tertiary", use_container_width=False, key=f"{section_type}_toggle_button"):
           st.session_state[show_key] = not st.session_state[show_key]
           st.rerun()

   # Show expanded deck list if toggled
   if st.session_state[show_key]:
       with st.spinner(f"Loading {section_type} deck details..."):
           # Ensure energy cache is initialized
           import cache_manager
           cache_manager.ensure_energy_cache()
           
           # Display decks using unified renderer
           decks_to_show = deck_data.head(max_decks)
           
           for idx, (_, deck) in enumerate(decks_to_show.iterrows()):
               rank = idx + 1
               render_unified_deck_in_sidebar(deck, deck_type=section_type, rank=rank)
       
       # Add section-specific disclaimer
       display_section_disclaimer(section_type, max_decks)
   else:
       st.write("")

def display_section_disclaimer(section_type, max_decks):
   """Display section-specific disclaimer text"""
   performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
   
   disclaimers = {
       "meta": {
           "description": f"Top performers from the past {TOURNAMENT_COUNT} tournaments",
           "sorting": "Sorted by their Power Index (see the bottom of sidebar)"
       },
       "trending": {
           "description": f"Most active from the past {TOURNAMENT_COUNT} tournaments",
           "sorting": "Sorted by tournament activity, then by lowest meta share"
       },
       "gems": {
           "description": f"Underrepresented from the past {TOURNAMENT_COUNT} tournaments",
           "sorting": "0.05-0.5% meta share, 55%+ win rate, 20+ games"
       }
   }
   
   config = disclaimers.get(section_type, disclaimers["meta"])
   
   st.markdown(f"""
   <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
       <div>{config["description"]}</div>
       <div>Updated {performance_time_str}</div>
   </div>
   <div style="font-size: 0.75rem; margin-bottom: 5px; color: #777;">
       {config["sorting"]}
   </div>
   """, unsafe_allow_html=True)
   st.write("")
   st.write("")
   st.write("")
    
def get_filtered_deck_data(filter_type):
    """
    Get filtered deck data based on filter type
    
    Args:
        filter_type: Type of filter ("trending", "gems", "meta")
        
    Returns:
        Filtered and sorted DataFrame
    """
    if 'performance_data' not in st.session_state or st.session_state.performance_data.empty:
        return pd.DataFrame()
    
    perf_data = st.session_state.performance_data.copy()
    
    # Calculate win_rate if not present (should already exist but safety check)
    if 'win_rate' not in perf_data.columns:
        perf_data['total_games'] = perf_data['total_wins'] + perf_data['total_losses'] + perf_data['total_ties']
        perf_data['win_rate'] = (
            (perf_data['total_wins'] + 0.5 * perf_data['total_ties']) / 
            perf_data['total_games'] * 100
        ).fillna(0)
    
    # Apply filters and sorting based on type
    if filter_type == "trending":
        return perf_data.sort_values(['tournaments_played', 'share'], ascending=[False, True])
    
    elif filter_type == "gems":
        # Add total_games if not present
        if 'total_games' not in perf_data.columns:
            perf_data['total_games'] = perf_data['total_wins'] + perf_data['total_losses'] + perf_data['total_ties']
        
        # Filter for hidden gems criteria
        filtered_data = perf_data[
            (perf_data['share'] >= 0.05) & 
            (perf_data['share'] <= 0.5) & 
            (perf_data['win_rate'] >= 55) &
            (perf_data['total_games'] >= 20)
        ]
        return filtered_data.sort_values('win_rate', ascending=False)
    
    elif filter_type == "meta":
        return perf_data.head(10)  # Already sorted by power_index
    
    else:
        return perf_data

def render_sidebar_from_cache():
    """Render sidebar with aggressive caching - FULLY STREAMLINED VERSION"""
    check_and_update_tournament_data()

    # Check if we have performance data
    if 'performance_data' not in st.session_state or st.session_state.performance_data.empty:
        st.warning("No performance data available")
        return

    # Define all sections configuration
    sections_config = [
        {
            "type": "meta",
            "banner_path": "sidebar_banner.png",
            "fallback_title": "🏆 Top Meta Decks", 
            "max_decks": 10
        },
        {
            "type": "trending",
            "banner_path": "trending_banner.png",
            "fallback_title": "📈 Trending Decks",
            "max_decks": 5
        },
        {
            "type": "gems", 
            "banner_path": "gems_banner.png",
            "fallback_title": "💎 Hidden Gems",
            "max_decks": 5
        }
    ]

    # Render all sections using unified approach
    for section in sections_config:
        # Get filtered data directly
        filtered_data = get_filtered_deck_data(section["type"])
        
        create_deck_section(
            section_type=section["type"],
            banner_path=section["banner_path"], 
            fallback_title=section["fallback_title"],
            data_source=filtered_data,  # Pass DataFrame directly
            max_decks=section["max_decks"]
        )

    # Continue with existing sections...
    with st.spinner("Loading counter picker..."):
        display_counter_picker_sidebar()
    
    # Power Index explanation and about section remain unchanged
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
    
def display_counter_picker_sidebar():
    """Display counter picker in sidebar with expander format"""
    
    # Banner image (same as before)
    banner_path = "picker_banner.png"
    if os.path.exists(banner_path):
        with open(banner_path, "rb") as f:
            banner_base64 = base64.b64encode(f.read()).decode()
        st.markdown(f"""<div style="width:100%; text-align:center;">
            <hr style='margin-bottom:20px;  border: 0.5px solid rgba(137, 148, 166, 0.2); margin-top:-25px;'>
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
                        <img src="data:image/png;base64,{header_image}" style="width: 120%; height: auto; ">
                    </div>
                    """, unsafe_allow_html=True)
                
                # USE CACHED SAMPLE DECK
                if CARD_CACHE_AVAILABLE:
                    sample_deck = get_sample_deck_cached(deck['deck_name'], deck['set'])
                else:
                    # Fallback to direct import if cache not available
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

                # Energy types and Details button (SAME FORMAT AS TOP 10 META)
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # USE CACHED ENERGY TYPES (SAME AS TOP 10 META)
                    energy_types, is_typical = get_energy_types_for_deck(deck['deck_name'])
                    
                    if energy_types:
                        # USE CACHED ENERGY ICON RENDERING (SAME AS TOP 10 META)
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
                # Show basic info as fallback
                st.write(f"**{deck['displayed_name']}**")
                st.caption(f"Win Rate: {win_rate_display}")
    
    # Overall caption
    st.caption(f"Win rates weighted by match count • Minimum {MIN_COUNTER_MATCHES} matches required • Data from Limitless TCG")

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
