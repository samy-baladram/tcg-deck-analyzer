# cache_manager.py
"""Caching management for the TCG Deck Analyzer"""

import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

import cache_utils
from analyzer import analyze_deck, build_deck_template, create_tournament_deck_mapping, update_deck_analysis
from scraper import get_all_recent_tournaments, get_new_tournament_ids, get_affected_decks, get_sample_deck_for_archetype
from config import MIN_META_SHARE, CURRENT_SET

# In cache_manager.py - Add this import at the top
from card_cache import get_sample_deck_cached, save_analyzed_deck_to_cache, get_analyzed_deck_cached

def initialize_tournament_baseline():
    """Initialize baseline index if it doesn't exist"""
    if not os.path.exists(cache_utils.SAVED_INDEX_PATH):
        #print("DEBUG: No baseline index found, creating initial baseline")
        cache_utils.save_current_index_as_baseline()
        return True
    return False
    
def init_caches():
    """
    Initialize all necessary caches in session state without network calls.
    Simplified version - uses meta_table directly instead of performance_data.
    """
    import pandas as pd
    
    # Initialize baseline index if needed
    initialize_tournament_baseline()
    
    # Deck analysis cache
    if 'analyzed_deck_cache' not in st.session_state:
        st.session_state.analyzed_deck_cache = {}
    
    # Sample deck cache
    if 'sample_deck_cache' not in st.session_state:
        st.session_state.sample_deck_cache = {}
    
    # Track tournament IDs in session state
    if 'known_tournament_ids' not in st.session_state:
        st.session_state.known_tournament_ids = cache_utils.load_tournament_ids()
    
    # Initialize selected deck if not exists
    if 'selected_deck_index' not in st.session_state:
        st.session_state.selected_deck_index = None
        
    # Initialize deck_to_analyze if not exists
    if 'deck_to_analyze' not in st.session_state:
        st.session_state.deck_to_analyze = None
    
    # Initialize cache timestamps
    if 'fetch_time' not in st.session_state:
        st.session_state.fetch_time = datetime.now()
    
    if 'performance_fetch_time' not in st.session_state:
        st.session_state.performance_fetch_time = datetime.now()
    
    # Initialize update_running flag
    if 'update_running' not in st.session_state:
        st.session_state.update_running = False
        
    # Simplified first load - create proper DataFrame placeholder
    if 'first_load' not in st.session_state:
        print("DEBUG: First load - using meta_table system")
        
        # Set proper DataFrame placeholder with expected columns
        st.session_state.performance_data = pd.DataFrame(columns=[
            'deck_name', 'displayed_name', 'share', 'total_wins', 
            'total_losses', 'total_ties', 'power_index', 'tournaments_played', 'set'
        ])
        st.session_state.performance_fetch_time = datetime.now()
        
        # Load card usage data from disk (keep this if you use it)
        try:
            card_usage_df, _ = cache_utils.load_card_usage_data()
            st.session_state.card_usage_data = card_usage_df
            print("DEBUG: Loaded card usage data")
        except Exception as e:
            print(f"DEBUG: No card usage data available: {e}")
            st.session_state.card_usage_data = pd.DataFrame()
        
        # Mark as loaded
        st.session_state.first_load = True
        print("DEBUG: Cache initialization complete - using meta_table system")


# FIX 3: Update the stub functions in cache_manager.py

def load_or_update_tournament_data(force_update=False):
    """
    SIMPLIFIED - Just return proper DataFrame placeholder since we use meta_table directly
    """
    import pandas as pd
    
    print("DEBUG: load_or_update_tournament_data - using meta_table system")
    
    try:
        # Try to load from cache first
        performance_df, performance_timestamp = cache_utils.load_tournament_performance_data()
        
        # If no cached data or force update, create proper placeholder
        if performance_df.empty or force_update:
            print("DEBUG: Creating DataFrame placeholder (using meta_table)")
            
            # Create proper empty DataFrame with expected columns
            performance_df = pd.DataFrame(columns=[
                'deck_name', 'displayed_name', 'share', 'total_wins', 
                'total_losses', 'total_ties', 'power_index', 'tournaments_played', 'set'
            ])
            
            performance_timestamp = datetime.now()
            
            # Save placeholder to prevent future calls
            cache_utils.save_tournament_performance_data(performance_df)
        
        return performance_df, performance_timestamp
        
    except Exception as e:
        print(f"DEBUG: Error in load_or_update_tournament_data: {e}")
        # Return proper DataFrame fallback
        fallback_data = pd.DataFrame(columns=[
            'deck_name', 'displayed_name', 'share', 'total_wins', 
            'total_losses', 'total_ties', 'power_index', 'tournaments_played', 'set'
        ])
        return fallback_data, datetime.now()

# Update the get_or_load_sample_deck function
def get_or_load_sample_deck(deck_name, set_name):
    """Get sample deck from cache or load if not cached"""
    # Use cached version
    sample_deck = get_sample_deck_cached(deck_name, set_name)
    
    # If no energy types in sample deck, try to get from other caches
    if not sample_deck.get('energy_types'):
        # Try to get energy types from analyzed deck cache
        analyzed_key = f"full_deck_{deck_name}_{set_name}"
        if analyzed_key in st.session_state.analyzed_deck_cache:
            energy_types = st.session_state.analyzed_deck_cache[analyzed_key].get('energy_types', [])
            most_common_energy = st.session_state.analyzed_deck_cache[analyzed_key].get('most_common_energy', [])
            
            # Update sample deck with energy info
            sample_deck['energy_types'] = energy_types
            sample_deck['most_common_energy'] = most_common_energy
    
    return sample_deck

def validate_cache_data(cached_data):
    """Validate that cached data has all required fields"""
    # UPDATED: Check for the critical fields needed by the app
    critical_fields = ['results', 'total_decks', 'variant_df']  # These are essential
    optional_fields = ['deck_list', 'deck_info', 'total_cards', 'options', 'energy_types', 'most_common_energy']
    
    if not isinstance(cached_data, dict):
        print("Cache validation failed: not a dictionary")
        return False
    
    # Check critical fields first
    for field in critical_fields:
        if field not in cached_data:
            print(f"Cache validation failed: missing critical field {field}")
            return False
            
    # Check if results DataFrame is valid
    results = cached_data.get('results')
    if results is None:
        print("Cache validation failed: results is None")
        return False
        
    if hasattr(results, 'empty') and results.empty:
        print("Cache validation failed: results DataFrame is empty")
        return False
        
    # Check if results has the expected columns
    if hasattr(results, 'columns'):
        expected_columns = ['card_name', 'type', 'pct_total']
        missing_columns = [col for col in expected_columns if col not in results.columns]
        if missing_columns:
            print(f"Cache validation failed: missing columns {missing_columns}")
            return False
    
    # Check variant_df
    variant_df = cached_data.get('variant_df')
    if variant_df is None:
        print("Cache validation failed: variant_df is None")
        return False
    
    # total_decks should be a number
    total_decks = cached_data.get('total_decks', 0)
    if not isinstance(total_decks, (int, float)) or total_decks < 0:
        print(f"Cache validation failed: invalid total_decks value: {total_decks}")
        return False
    
    print("Cache validation passed")
    return True

def analyze_deck_fresh(deck_name, set_name):
    """Perform fresh deck analysis without using any cache"""
    from analyzer import collect_decks, analyze_deck, build_deck_template
    
    print(f"Performing COMPLETELY FRESH analysis for {deck_name}")
    
    # CRITICAL: Clear the collected_decks session state to force fresh collection
    deck_key = f"{deck_name}_{set_name}"
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        del st.session_state.collected_decks[deck_key]
        print(f"Cleared session collected_decks for {deck_name}")
    
    # Force fresh collection and analysis (no cache checking)
    results, total_decks, variant_df, energy_types = analyze_deck(deck_name, set_name)
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    most_common_energy = get_most_common_energy(deck_name, set_name)
    
    # Create COMPLETE analyzed data structure
    analyzed_data = {
        'results': results,                              
        'total_decks': total_decks,                      
        'variant_df': variant_df,                        
        'deck_list': deck_list,                          
        'deck_info': deck_info,                          
        'total_cards': total_cards,                      
        'options': options,                              
        'energy_types': energy_types,                    
        'most_common_energy': most_common_energy         
    }
    
    # Store in session cache
    cache_key = f"full_deck_{deck_name}_{set_name}"
    st.session_state.analyzed_deck_cache[cache_key] = analyzed_data
    
    # Save to disk cache (with new data)
    cache_utils.save_analyzed_deck_components(deck_name, set_name, results, total_decks, variant_df, energy_types)
    
    print(f"Completed fresh analysis for {deck_name} with {total_decks} decks")
    return analyzed_data

# Update the get_or_analyze_full_deck function
def get_or_analyze_full_deck(deck_name, set_name, force_refresh=False):
    """Get full analyzed deck from cache or analyze if not cached"""
    cache_key = f"full_deck_{deck_name}_{set_name}"
    
    # If force_refresh is True, skip cache entirely
    if force_refresh:
        print(f"Force refreshing analysis for {deck_name}")
        # CLEAR ALL CACHES FIRST
        clear_all_deck_caches(deck_name, set_name)
        return analyze_deck_fresh(deck_name, set_name)
    
    # Check session cache first
    if cache_key in st.session_state.analyzed_deck_cache:
        cached_data = st.session_state.analyzed_deck_cache[cache_key]
        # Validate cache integrity
        if validate_cache_data(cached_data):
            print(f"Found valid {deck_name} in session cache")
            return cached_data
        else:
            print(f"Invalid cache data for {deck_name}, clearing and regenerating")
            # CRITICAL FIX: Clear ALL caches, not just session
            clear_all_deck_caches(deck_name, set_name)
            return analyze_deck_fresh(deck_name, set_name)
    
    # Check disk cache for full analysis
    cached_results, cached_total_decks, cached_variant_df, cached_energy_types = cache_utils.load_analyzed_deck_components(deck_name, set_name)
    
    if cached_results is not None and not cached_results.empty:
        print(f"Using cached analysis data for {deck_name}")
        
        # Generate the deck template from cached results
        from analyzer import build_deck_template
        deck_list, deck_info, total_cards, options = build_deck_template(cached_results)
        
        # Calculate most common energy
        most_common_energy = get_most_common_energy(deck_name, set_name)
        
        # Create COMPLETE cache entry with ALL required fields
        analyzed_data = {
            'results': cached_results,                    
            'total_decks': cached_total_decks,           
            'variant_df': cached_variant_df,             
            'deck_list': deck_list,                      
            'deck_info': deck_info,                      
            'total_cards': total_cards,                  
            'options': options,                          
            'energy_types': cached_energy_types,        
            'most_common_energy': most_common_energy     
        }
        
        # Validate before storing
        if validate_cache_data(analyzed_data):
            # Store in session cache
            st.session_state.analyzed_deck_cache[cache_key] = analyzed_data
            return analyzed_data
        else:
            print(f"Disk cache data invalid for {deck_name}, forcing fresh analysis")
            clear_all_deck_caches(deck_name, set_name)
            return analyze_deck_fresh(deck_name, set_name)
    
    # If not in any cache, analyze the deck
    print(f"No cache found for {deck_name}, analyzing")
    return analyze_deck_fresh(deck_name, set_name)

def create_fallback_performance_data():
    """Create minimal fallback performance data when all else fails"""
    import pandas as pd
    
    # Create a minimal dataset with common deck archetypes
    fallback_data = [
        {
            'deck_name': 'charizard-ex-arcanine-ex',
            'displayed_name': 'Charizard Ex Arcanine Ex',
            'set': 'A3a',
            'share': 15.0,
            'win_rate': 52.0,
            'total_wins': 100,
            'total_losses': 92,
            'total_ties': 8,
            'tournaments_played': 25,
            'power_index': 1.2
        },
        # Add more fallback decks as needed
    ]
    
    return pd.DataFrame(fallback_data)
    
#######################################################################################################################

def track_player_tournament_mapping(deck_name, set_name=None):
    """Track player and tournament IDs for a deck"""
    from scraper import get_player_tournament_pairs, create_mapping_key
    
    # FIXED: Get current set name if not provided
    if set_name is None:
        set_name = get_current_set_name()
    
    try:
        # Get all player-tournament pairs
        pairs = get_player_tournament_pairs(deck_name, set_name)
        
        if not pairs:
            print(f"No player-tournament pairs found for {deck_name}")
            return 0
        
        # Load existing mapping
        mapping = cache_utils.load_player_tournament_mapping()
        
        # Add new mappings
        count = 0
        for pair in pairs:
            player_id = pair['player_id']
            tournament_id = pair['tournament_id']
            
            # Create key
            key = create_mapping_key(player_id, tournament_id)
            
            # Add to mapping
            if key not in mapping:
                mapping[key] = deck_name
                count += 1
        
        # Save updated mapping
        cache_utils.save_player_tournament_mapping(mapping)
        
        # Return number of new pairs tracked
        return count
    except Exception as e:
        st.error(f"Error tracking player-tournament mapping for {deck_name}: {str(e)}")
        return 0
    
def update_tournament_tracking():
    """Update tournament tracking using index.json comparison (no web scraping)"""
    
    stats = {
        'current_tournaments': 0,
        'new_tournaments': 0,
        'affected_decks': 0,
        'updated_decks': 0,
        'has_changes': False
    }
    
    try:
        # Compare current index with saved baseline
        comparison_result = cache_utils.compare_tournament_indices()
        
        stats['current_tournaments'] = comparison_result['current_total']
        stats['new_tournaments'] = comparison_result['new_tournament_count']
        stats['has_changes'] = comparison_result['has_changes']
        
        print(f"DEBUG: Index comparison result: {comparison_result}")
        
        # If no changes detected, return early
        if not comparison_result['has_changes']:
            print("DEBUG: No tournament changes detected")
            return stats
        
        print(f"DEBUG: Tournament changes detected: {comparison_result['new_tournament_count']} new tournaments")
        
        # Clear ALL analyzed deck caches when new tournaments are found
        if comparison_result['new_tournament_count'] > 0:
            print("DEBUG: Clearing all deck caches due to new tournaments")
            
            # Clear session state caches
            if 'analyzed_deck_cache' in st.session_state:
                cleared_count = len(st.session_state.analyzed_deck_cache)
                st.session_state.analyzed_deck_cache.clear()
                stats['updated_decks'] = cleared_count
                print(f"DEBUG: Cleared {cleared_count} analyzed deck caches")
            
            if 'sample_deck_cache' in st.session_state:
                st.session_state.sample_deck_cache.clear()
                print("DEBUG: Cleared sample deck cache")
            
            # Clear disk-based caches
            cache_utils.clear_analyzed_deck_cache()
            
            # Update baseline with current index
            cache_utils.save_current_index_as_baseline()
            print("DEBUG: Updated baseline index")
        
        return stats
        
    except Exception as e:
        print(f"ERROR: Tournament tracking update failed: {e}")
        return stats

def check_tournament_changes_only():
    """Quick check if tournament changes exist without updating caches"""
    try:
        comparison_result = cache_utils.compare_tournament_indices()
        return comparison_result['has_changes']
    except Exception as e:
        print(f"ERROR: Quick tournament check failed: {e}")
        return False

def clear_all_deck_caches(deck_name, set_name):
    """Clear ALL caches for a specific deck to force fresh analysis"""
    
    # Clear session caches
    cache_key = f"full_deck_{deck_name}_{set_name}"
    sample_key = f"sample_deck_{deck_name}_{set_name}"
    energy_key = f"energy_{deck_name}_{set_name}"
    matchup_key = f"matchup_{deck_name}_{set_name}"
    deck_key = f"{deck_name}_{set_name}"
    
    # Clear from all session state caches
    caches_to_clear = [
        ('analyzed_deck_cache', cache_key),
        ('sample_deck_cache', sample_key),
        ('collected_decks', deck_key),
        (None, energy_key),
        (None, matchup_key),
        (None, f"energy_cache_{deck_name}_{set_name}"),
    ]
    
    for cache_name, key in caches_to_clear:
        if cache_name:
            if cache_name in st.session_state and key in st.session_state[cache_name]:
                del st.session_state[cache_name][key]
                print(f"Cleared {cache_name}[{key}]")
        else:
            if key in st.session_state:
                del st.session_state[key]
                print(f"Cleared session state key: {key}")
    
    # CRITICAL FIX: Clear disk caches too when force refreshing
    cache_utils.clear_deck_cache(deck_name, set_name)
    
    # CRITICAL FIX: Also clear collected deck disk cache
    import os
    safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
    collected_file = os.path.join("cached_data/collected_decks", f"{safe_name}_{set_name}_collected.json")
    if os.path.exists(collected_file):
        os.remove(collected_file)
        print(f"Cleared collected deck file: {collected_file}")
    
    # Clear energy utils cache
    if 'archetype_energy_types' in st.session_state and deck_name in st.session_state.archetype_energy_types:
        del st.session_state.archetype_energy_types[deck_name]
    
    if 'archetype_energy_combos' in st.session_state and deck_name in st.session_state.archetype_energy_combos:
        del st.session_state.archetype_energy_combos[deck_name]
    
    # CRITICAL FIX: Also clear card cache
    from card_cache import invalidate_deck_cache
    invalidate_deck_cache(deck_name, set_name)
    
    print(f"Cleared ALL caches (including disk) for {deck_name}")

def get_cache_statistics():
    """Return statistics about cache usage"""
    stats = {
        'decks_cached': len(st.session_state.analyzed_deck_cache),
        'sample_decks_cached': len(st.session_state.sample_deck_cache),
        'tournaments_tracked': len(st.session_state.known_tournament_ids) if 'known_tournament_ids' in st.session_state else 0,
        'last_update': st.session_state.fetch_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return stats

def ensure_analyzed_deck_consistency(deck_name, set_name):
    """
    Ensure analyzed deck and collected deck data are consistent by synchronizing caches
    """
    # Cache keys
    deck_key = f"{deck_name}_{set_name}"
    cache_key = f"full_deck_{deck_name}_{set_name}"
    
    # Initialize session state if needed
    if 'collected_decks' not in st.session_state:
        st.session_state.collected_decks = {}
    
    if 'analyzed_deck_cache' not in st.session_state:
        st.session_state.analyzed_deck_cache = {}
    
    # Case 1: We have analyzed data but no collected data
    if (cache_key in st.session_state.analyzed_deck_cache and 
        (deck_key not in st.session_state.collected_decks or not st.session_state.collected_decks[deck_key].get('decks'))):
        
        print(f"Found analyzed data for {deck_name} but no collected decks - checking disk cache")
        
        # First try to load collected decks from disk
        metadata_loaded = load_collected_decks_metadata(deck_name, set_name)
        
        # If we still don't have collected decks, force collection
        if not metadata_loaded:
            print(f"Need to collect decks for {deck_name}")
            from analyzer import collect_decks
            all_decks, all_energy_types, total_decks = collect_decks(deck_name, set_name)
            
            # The collect_decks function should update session state automatically,
            # but let's check to make sure
            if deck_key not in st.session_state.collected_decks:
                st.session_state.collected_decks[deck_key] = {
                    'decks': all_decks,
                    'all_energy_types': all_energy_types,
                    'total_decks': total_decks
                }
                
                print(f"Stored {len(all_decks)} collected decks for {deck_name}")
    
    # Case 2: We have collected data but no analyzed data
    elif (deck_key in st.session_state.collected_decks and 
          cache_key not in st.session_state.analyzed_deck_cache):
        
        print(f"Found collected decks for {deck_name} but no analyzed data - analyzing")
        
        # Collected data exists, so analyze using that
        from analyzer import analyze_deck
        from cache_utils import save_analyzed_deck_components
        
        # Re-analyze (this will update the session state)
        results, total_decks, variant_df, energy_types = analyze_deck(deck_name, set_name)
        
        # Create and save analyzed data
        from analyzer import build_deck_template
        deck_list, deck_info, total_cards, options = build_deck_template(results)
        
        analyzed_data = {
            'results': results,
            'total_decks': total_decks,
            'variant_df': variant_df,
            'deck_list': deck_list,
            'deck_info': deck_info,
            'total_cards': total_cards,
            'options': options,
            'energy_types': energy_types
        }
        
        # Store in session cache
        st.session_state.analyzed_deck_cache[cache_key] = analyzed_data
        
        # Save to disk
        save_analyzed_deck_components(deck_name, set_name, results, total_decks, variant_df, energy_types)
        
        print(f"Analyzed deck {deck_name} using existing collected data")
    
    else:
        # Both caches are either populated or empty - no action needed
        pass

def ensure_deck_collected(deck_name, set_name):
    """Ensure deck is collected, analyzing if needed"""
    # First, check if deck is already collected in session state
    deck_key = f"{deck_name}_{set_name}"
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        return True
        
    # Next, try to load from cache
    analyzed_data = get_or_analyze_full_deck(deck_name, set_name)
    
    # Check again if collection happened as part of analysis
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        return True
        
    # If still not collected, force collection
    from analyzer import collect_decks
    all_decks, all_energy_types, total_decks = collect_decks(deck_name, set_name)
    
    # This should have updated session state, but let's check
    return 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks              


# Add this function to calculate the most common energy combination
def calculate_most_common_energy(decks):
    """
    Calculate the most common energy type combination from a list of decks
    
    Args:
        decks: List of deck dictionaries, each with 'energy_types' field
        
    Returns:
        List containing the most common energy type combination, or empty list if none found
    """
    # Count frequency of each energy combination
    combinations = {}
    total_decks_with_energy = 0
    
    for deck in decks:
        if not deck.get('energy_types'):
            continue
            
        # Create a tuple of sorted energy types for consistent keys
        energy_types = [e.lower() for e in deck['energy_types'] if e]  # Normalize to lowercase
        combo = tuple(sorted(energy_types))
        
        if combo:  # Only count if there are any energy types
            total_decks_with_energy += 1
            combinations[combo] = combinations.get(combo, 0) + 1
    
    # Print debug info
    print(f"Energy combinations found: {combinations}")
    print(f"Total decks with energy: {total_decks_with_energy}")
    
    # Find the most common combination
    if combinations:
        most_common = max(combinations.items(), key=lambda x: x[1])[0]
        count = combinations[most_common]
        percentage = (count / total_decks_with_energy) * 100
        print(f"Most common energy: {list(most_common)} ({count}/{total_decks_with_energy}, {percentage:.1f}%)")
        return list(most_common)
    
    print("No energy combinations found")
    return []
def get_most_common_energy(deck_name, set_name):
    """
    Get the most common energy combination for a deck
    
    Args:
        deck_name: Name of the deck
        set_name: Set code (e.g., "A3")
        
    Returns:
        List containing the most common energy combination
    """
    # First check if we have it in analyzed deck cache
    analyzed_key = f"full_deck_{deck_name}_{set_name}"
    if analyzed_key in st.session_state.analyzed_deck_cache:
        most_common = st.session_state.analyzed_deck_cache[analyzed_key].get('most_common_energy', [])
        if most_common:
            return most_common
    
    # Next check if it's in sample deck cache
    sample_key = f"sample_deck_{deck_name}_{set_name}"
    if sample_key in st.session_state.sample_deck_cache:
        most_common = st.session_state.sample_deck_cache[sample_key].get('most_common_energy', [])
        if most_common:
            return most_common
    
    # Finally check if we have collected decks to calculate
    deck_key = f"{deck_name}_{set_name}"
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        collected_data = st.session_state.collected_decks[deck_key]
        if 'decks' in collected_data and collected_data['decks']:
            return calculate_most_common_energy(collected_data['decks'])
    
    # Fall back to empty list if nothing found
    return []

# Add this to cache_manager.py
def ensure_energy_cache():
    """Ensure energy cache exists in session state"""
    if 'energy_cache' not in st.session_state:
        st.session_state.energy_cache = {}
        
def get_cached_energy(deck_name, set_name="A3"):
    """Get cached energy for a deck, calculating if needed"""
    ensure_energy_cache()
    
    # Create a unique key for this deck
    cache_key = f"{deck_name}_{set_name}_energy"
    
    # Return cached value if it exists
    if cache_key in st.session_state.energy_cache:
        cached_energy = st.session_state.energy_cache[cache_key]
        print(f"Using cached energy for {deck_name}: {cached_energy}")
        return cached_energy
    
    # Calculate and cache the most common energy
    energy_types = calculate_and_cache_energy(deck_name, set_name)
    return energy_types

def calculate_and_cache_energy(deck_name, set_name="A3"):
    """Calculate most common energy and cache it"""
    ensure_energy_cache()
    cache_key = f"{deck_name}_{set_name}_energy"
    
    # Start with an empty list
    energy_types = []
    
    # First try to get from collected decks
    deck_key = f"{deck_name}_{set_name}"
    
    # If collected decks aren't in session state, try to load from disk
    if 'collected_decks' not in st.session_state or deck_key not in st.session_state.collected_decks:
        load_collected_decks_metadata(deck_name, set_name)
    
    # Now check if we have collected decks
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        collected_data = st.session_state.collected_decks[deck_key]
        if 'decks' in collected_data and collected_data['decks']:
            # First check if there are decks with energy
            decks_with_energy = [d for d in collected_data['decks'] if d.get('energy_types')]
            
            if decks_with_energy:
                energy_types = calculate_most_common_energy(decks_with_energy)
                print(f"Calculated energy for {deck_name} from {len(decks_with_energy)} decks with energy: {energy_types}")
            else:
                print(f"No decks with energy found for {deck_name}")
        else:
            print(f"No decks found for {deck_name}")
    else:
        print(f"No collected decks found for {deck_name}")
    
    # Rest of the function remains the same...
    
    # If not found from collected decks, try analyzed cache
    if not energy_types:
        analyzed_key = f"full_deck_{deck_name}_{set_name}"
        if analyzed_key in st.session_state.analyzed_deck_cache:
            # First check most_common_energy
            cached_most_common = st.session_state.analyzed_deck_cache[analyzed_key].get('most_common_energy', [])
            if cached_most_common:
                energy_types = cached_most_common
                print(f"Using most_common_energy from analyzed cache for {deck_name}: {energy_types}")
            else:
                # Then try energy_types
                cached_energy = st.session_state.analyzed_deck_cache[analyzed_key].get('energy_types', [])
                if cached_energy:
                    energy_types = cached_energy
                    print(f"Using energy_types from analyzed cache for {deck_name}: {energy_types}")
        else:
            print(f"No analyzed data found for {deck_name}")
    
    # If still not found, try sample deck
    if not energy_types:
        sample_key = f"sample_deck_{deck_name}_{set_name}"
        if sample_key in st.session_state.sample_deck_cache:
            # First check most_common_energy
            cached_most_common = st.session_state.sample_deck_cache[sample_key].get('most_common_energy', [])
            if cached_most_common:
                energy_types = cached_most_common
                print(f"Using most_common_energy from sample deck for {deck_name}: {energy_types}")
            else:
                # Then try energy_types
                cached_energy = st.session_state.sample_deck_cache[sample_key].get('energy_types', [])
                if cached_energy:
                    energy_types = cached_energy
                    print(f"Using energy_types from sample deck for {deck_name}: {energy_types}")
        else:
            print(f"No sample deck found for {deck_name}")
            
    # As a last resort, try the energy_utils data
    if not energy_types and 'archetype_energy_combos' in st.session_state and deck_name in st.session_state.archetype_energy_combos:
        combos = st.session_state.archetype_energy_combos[deck_name]
        if combos:
            most_common = max(combos.items(), key=lambda x: x[1])[0]
            energy_types = list(most_common)
            print(f"Using energy_utils archetype_energy_combos for {deck_name}: {energy_types}")
    
    # Cache the result even if empty
    st.session_state.energy_cache[cache_key] = energy_types
    print(f"Cached energy for {deck_name}: {energy_types}")
    
    return energy_types

# Add this function to cache_manager.py

def load_collected_decks_metadata(deck_name, set_name):
    """Load collected decks metadata from disk and store in session state"""
    import cache_utils
    
    # Create key
    deck_key = f"{deck_name}_{set_name}"
    
    # Skip if we already have collected decks in session state
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        print(f"Using collected decks from session state for {deck_name}")
        return True
    
    # Try to load from disk
    data = cache_utils.load_collected_decks(deck_name, set_name)
    if data and 'decks' in data and data['decks']:
        # Initialize if needed
        if 'collected_decks' not in st.session_state:
            st.session_state.collected_decks = {}
        
        # Store in session state
        st.session_state.collected_decks[deck_key] = {
            'decks': data.get('decks', []),
            'all_energy_types': data.get('all_energy_types', []),
            'total_decks': data.get('total_decks', 0)
        }
        
        print(f"Loaded collected deck metadata for {deck_name} from disk ({len(data.get('decks', []))} decks)")
        return True
    
    print(f"No collected deck metadata found for {deck_name}")
    return False

# Add this function to cache_manager.py
# In cache_manager.py - Replace the problematic code
def get_or_fetch_matchup_data(deck_name, set_name, force_update=False):
    """
    Get matchup data from cache or fetch if needed
    
    Args:
        deck_name: Name of the deck
        set_name: Set code (e.g., "A3")
        force_update: Whether to force a fresh fetch
        
    Returns:
        DataFrame with matchup data
    """
    # Check if we have this in session cache first
    session_key = f"matchup_{deck_name}_{set_name}"
    if not force_update and session_key in st.session_state:
        return st.session_state[session_key]
    
    # Try to load from disk cache
    import cache_utils
    matchup_df, timestamp = cache_utils.load_matchup_data(deck_name, set_name)
    
    if matchup_df is not None and not force_update:
        # Store in session cache
        st.session_state[session_key] = matchup_df
        return matchup_df
    
    # If not in cache or force update, fetch from web
    # CRITICAL CHANGE: We need to call the real implementation directly, not via display_tabs
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
    import re
    from config import BASE_URL
    
    # Construct the URL for matchups
    url = f"{BASE_URL}/decks/{deck_name}/matchups/?game=POCKET&format=standard&set={set_name}"
    
    try:
        # Fetch the webpage
        response = requests.get(url)
        if response.status_code != 200:
            return pd.DataFrame()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='striped')
        
        if not table:
            return pd.DataFrame()
        
        # Get meta share data for opponent decks
        meta_share_map = {}
        try:
            from meta_table import MetaTableBuilder
            builder = MetaTableBuilder()
            meta_df = builder.build_complete_meta_table(limit=50)
            
            if not meta_df.empty:
                for deck_name_meta in meta_df.index:
                    share = meta_df.loc[deck_name_meta, 'share_7d']
                    meta_share_map[deck_name_meta] = share
        except Exception as e:
            print(f"DEBUG: Could not load meta share from meta_table: {e}")
            meta_share_map = {}
        
        # Process each data row
        rows = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all(['td'])
            if len(cells) < 5:
                continue
            
            # Extract opponent deck display name
            opponent_display_name = cells[1].text.strip()
            
            # Extract opponent deck raw name from URL
            opponent_deck_name = ""
            opponent_link = cells[1].find('a')
            
            if opponent_link and 'href' in opponent_link.attrs:
                href = opponent_link['href']
                match = re.search(r'/matchups/([^/?]+)', href)
                if match:
                    opponent_deck_name = match.group(1)
                else:
                    match = re.search(r'/decks/([^/?]+)', href)
                    if match:
                        opponent_deck_name = match.group(1)
            
            # Extract matches played
            matches_played = 0
            try:
                matches_played = int(cells[2].text.strip())
            except ValueError:
                pass
            
            # Extract record
            record_text = cells[3].text.strip()
            wins, losses, ties = 0, 0, 0
            
            win_match = re.search(r'^(\d+)', record_text)
            loss_match = re.search(r'-\s*(\d+)\s*-', record_text)
            tie_match = re.search(r'-\s*(\d+)$', record_text)
            
            if win_match: wins = int(win_match.group(1))
            if loss_match: losses = int(loss_match.group(1))
            if tie_match: ties = int(tie_match.group(1))
            
            # Extract win percentage
            win_pct = 0.0
            try:
                win_pct = float(cells[4].text.strip().replace('%', ''))
            except ValueError:
                pass
            
            # Add meta share for this opponent deck
            meta_share = meta_share_map.get(opponent_deck_name, 0.0)
            
            # Create row data
            row_data = {
                'opponent_name': opponent_display_name,
                'opponent_deck_name': opponent_deck_name,
                'wins': wins,
                'losses': losses,
                'ties': ties,
                'win_pct': win_pct,
                'matches_played': matches_played,
                'meta_share': meta_share
            }
            
            rows.append(row_data)
        
        # Create DataFrame from all row data
        matchup_df = pd.DataFrame(rows)
        
        if not matchup_df.empty:
            matchup_df = matchup_df.sort_values('win_pct', ascending=True).reset_index(drop=True)
        
        # Save to disk cache
        cache_utils.save_matchup_data(deck_name, set_name, matchup_df)
        
        # Store in session cache
        st.session_state[session_key] = matchup_df
        
        return matchup_df
        
    except Exception as e:
        return pd.DataFrame()

def update_matchup_cache(min_share=0.5):
    """Update matchup cache for all decks with at least min_share"""
    import cache_utils
    return cache_utils.update_all_matchups(min_share)
    
def clear_deck_cache_on_switch(deck_name, set_name):
    """Clear all caches for a specific deck when switching"""
    # Clear session caches
    cache_key = f"full_deck_{deck_name}_{set_name}"
    sample_key = f"sample_deck_{deck_name}_{set_name}"
    energy_key = f"energy_{deck_name}"
    matchup_key = f"matchup_{deck_name}_{set_name}"
    
    # Remove from session state caches
    caches_to_clear = [
        ('analyzed_deck_cache', cache_key),
        ('sample_deck_cache', sample_key),
        (None, energy_key),  # Direct session state key
        (None, matchup_key)  # Direct session state key
    ]
    
    for cache_name, key in caches_to_clear:
        if cache_name:
            if cache_name in st.session_state and key in st.session_state[cache_name]:
                del st.session_state[cache_name][key]
                print(f"Cleared {cache_name}[{key}]")
        else:
            if key in st.session_state:
                del st.session_state[key]
                print(f"Cleared session state key: {key}")

def get_current_set_name():
    """Get the current set name from various sources with better fallback"""
    # Try to get from current analysis context
    if 'analyze' in st.session_state:
        set_name = st.session_state.analyze.get('set_name')
        if set_name:
            return set_name
    
    # Try to get from performance data
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        # Get the most common set from performance data
        sets = st.session_state.performance_data['set'].value_counts()
        if not sets.empty:
            return sets.index[0]
    
    # Try to fetch current set from Limitless directly
    try:
        from scraper import get_popular_decks_with_performance
        decks = get_popular_decks_with_performance(0.0)
        if not decks.empty:
            return decks['set'].mode()[0]  # Most common set
    except:
        pass
    
    # Last resort fallback
    return CURRENT_SET
