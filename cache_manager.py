# cache_manager.py
"""Caching management for the TCG Deck Analyzer"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

import cache_utils
from analyzer import analyze_deck, build_deck_template, create_tournament_deck_mapping, update_deck_analysis
from scraper import get_all_recent_tournaments, get_new_tournament_ids, get_affected_decks, analyze_recent_performance, get_sample_deck_for_archetype
from config import MIN_META_SHARE

# In cache_manager.py - Add this import at the top
from card_cache import get_sample_deck_cached, save_analyzed_deck_to_cache, get_analyzed_deck_cached

def init_caches():
    """
    Initialize all necessary caches in session state without network calls.
    """
    # Deck analysis cache
    if 'analyzed_deck_cache' not in st.session_state:
        st.session_state.analyzed_deck_cache = {}
    
    # Sample deck cache
    if 'sample_deck_cache' not in st.session_state:
        st.session_state.sample_deck_cache = {}
    
    # Track tournament IDs in session state
    if 'known_tournament_ids' not in st.session_state:
        # Load from disk
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
        
    # Load cached data without network calls on first load
    if 'first_load' not in st.session_state:
        # Load tournament data directly from disk
        performance_df, performance_timestamp = cache_utils.load_tournament_performance_data()
        st.session_state.performance_data = performance_df
        st.session_state.performance_fetch_time = performance_timestamp
        
        # Load card usage data from disk
        card_usage_df, _ = cache_utils.load_card_usage_data()
        st.session_state.card_usage_data = card_usage_df
        
        # Mark as loaded
        st.session_state.first_load = True

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
    required_fields = ['results', 'deck_list', 'deck_info', 'total_cards']
    
    if not isinstance(cached_data, dict):
        return False
        
    for field in required_fields:
        if field not in cached_data:
            return False
            
    # Check if results DataFrame is valid
    results = cached_data.get('results')
    if results is None or (hasattr(results, 'empty') and results.empty):
        return False
        
    return True

def analyze_deck_fresh(deck_name, set_name):
    """Perform fresh deck analysis without using any cache"""
    from analyzer import analyze_deck, build_deck_template
    
    print(f"Performing fresh analysis for {deck_name}")
    
    # Force fresh collection and analysis
    results, total_decks, variant_df, energy_types = analyze_deck(deck_name, set_name)
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    most_common_energy = get_most_common_energy(deck_name, set_name)
    
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
    
    return analyzed_data

# Update the get_or_analyze_full_deck function
def get_or_analyze_full_deck(deck_name, set_name, force_refresh=False):
    """Get full analyzed deck from cache or analyze if not cached"""
    cache_key = f"full_deck_{deck_name}_{set_name}"
    
    # If force_refresh is True, skip cache entirely
    if force_refresh:
        print(f"Force refreshing analysis for {deck_name}")
        return analyze_deck_fresh(deck_name, set_name)
    
    # Check session cache first
    if cache_key in st.session_state.analyzed_deck_cache:
        cached_data = st.session_state.analyzed_deck_cache[cache_key]
        # Validate cache integrity
        if validate_cache_data(cached_data):
            print(f"Found valid {deck_name} in session cache")
            return cached_data
        else:
            print(f"Invalid cache data for {deck_name}, clearing")
            del st.session_state.analyzed_deck_cache[cache_key]
            
    if cache_key in st.session_state.analyzed_deck_cache:
        print(f"Found {deck_name} in session cache")
        return st.session_state.analyzed_deck_cache[cache_key]
    
    # Check card cache for basic deck template data
    cached_deck_data = get_analyzed_deck_cached(deck_name, set_name)
    if cached_deck_data:
        print(f"Found basic deck data in card cache for {deck_name}")
        # Store in session cache and return
        st.session_state.analyzed_deck_cache[cache_key] = cached_deck_data
        return cached_deck_data
    
    # Then check disk cache for full analysis
    cached_results, cached_total_decks, cached_variant_df, cached_energy_types = cache_utils.load_analyzed_deck_components(deck_name, set_name)
    
    if cached_results is not None:
        print(f"Using cached analysis data for {deck_name}")
        
        # Generate the deck template from cached results
        deck_list, deck_info, total_cards, options = build_deck_template(cached_results)
        
        # Calculate most common energy
        most_common_energy = get_most_common_energy(deck_name, set_name)
        
        # Create cache entry
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
        
        # Store in session cache
        st.session_state.analyzed_deck_cache[cache_key] = analyzed_data
        
        # Also save to card cache for faster future access
        save_analyzed_deck_to_cache(deck_name, set_name, analyzed_data)
        
        return analyzed_data
    
    # If not in any cache, analyze the deck
    print(f"No cache found for {deck_name}, analyzing")
    
    # Rest of the analysis logic remains the same...
    from analyzer import analyze_deck
    results, total_decks, variant_df, energy_types = analyze_deck(deck_name, set_name)
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    most_common_energy = get_most_common_energy(deck_name, set_name)
    
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
    st.session_state.analyzed_deck_cache[cache_key] = analyzed_data
    
    # Store in disk cache
    cache_utils.save_analyzed_deck_components(deck_name, set_name, results, total_decks, variant_df, energy_types)
    
    # Also save to card cache
    save_analyzed_deck_to_cache(deck_name, set_name, analyzed_data)
    
    return analyzed_data

def aggregate_card_usage(force_update=False):
    """
    Aggregate card usage across all top decks and cache results.
    Only updates once per day unless forced.
    """
    # Try to load existing data first
    card_usage_df, timestamp = cache_utils.load_card_usage_data()
    
    # Check if update is needed
    if not force_update and not card_usage_df.empty and (datetime.now() - timestamp) < timedelta(days=1):
        # Data is fresh (less than a day old)
        return card_usage_df
    
    # Data needs to be updated
    with st.spinner("Aggregating card usage data..."):
        # Get top decks from performance data
        if 'performance_data' not in st.session_state or st.session_state.performance_data.empty:
            # Load or update performance data if needed
            performance_df, _ = cache_utils.load_tournament_performance_data()
            if performance_df.empty:
                performance_df = analyze_recent_performance(share_threshold=MIN_META_SHARE)
                cache_utils.save_tournament_performance_data(performance_df)
        else:
            performance_df = st.session_state.performance_data
        
        # Get top 5 decks to analyze
        top_decks = performance_df.head(1)
        
        # Store all card data
        all_cards = []
        
        # For each deck, get its cards
        for _, deck in top_decks.iterrows():
            deck_name = deck['deck_name']
            set_name = deck['set']
            
            # Try to load analyzed deck data
            deck_data = cache_utils.load_analyzed_deck(deck_name, set_name)
            
            if deck_data is None:
                # Analyze the deck if not cached
                results, _, _, _ = analyze_deck(deck_name, set_name)
                
                # Store relevant info for each card
                for _, card in results.iterrows():
                    all_cards.append({
                        'deck_name': deck_name,
                        'deck_share': deck['share'],
                        'card_name': card['card_name'],
                        'type': card['type'],
                        'set': card['set'],
                        'num': card['num'],
                        'count_1': card['count_1'],
                        'count_2': card['count_2'],
                        'pct_1': card['pct_1'],
                        'pct_2': card['pct_2'],
                        'pct_total': card['pct_total'],
                        'category': card['category'] if 'category' in card else 'Unknown'
                    })
                
                # Save the analyzed deck for future use
                deck_list, deck_info, total_cards, options = build_deck_template(results)
                analyzed_data = {
                    'results': results,
                    'total_decks': 0,  # Not needed for this purpose
                    'variant_df': pd.DataFrame(),  # Not needed
                    'deck_list': deck_list,
                    'deck_info': deck_info,
                    'total_cards': total_cards,
                    'options': options
                }
                cache_utils.save_analyzed_deck(deck_name, set_name, analyzed_data)
            else:
                # Use cached data
                results = deck_data['results']
                
                # Store relevant info for each card
                for _, card in results.iterrows():
                    all_cards.append({
                        'deck_name': deck_name,
                        'deck_share': deck['share'],
                        'card_name': card['card_name'],
                        'type': card['type'],
                        'set': card['set'],
                        'num': card['num'],
                        'count_1': card['count_1'],
                        'count_2': card['count_2'],
                        'pct_1': card['pct_1'],
                        'pct_2': card['pct_2'],
                        'pct_total': card['pct_total'],
                        'category': card['category'] if 'category' in card else 'Unknown'
                    })
        
        # Create DataFrame from all cards
        card_usage_df = pd.DataFrame(all_cards)
        
        # Calculate total usage weighted by deck share
        card_usage_summary = card_usage_df.groupby(['card_name', 'type', 'set', 'num']).apply(
            lambda x: pd.Series({
                'deck_count': len(x),
                'total_count': sum(x['count_1'] + x['count_2']),
                'weighted_usage': sum(x['pct_total'] * x['deck_share'] / 100),
                'decks': ', '.join(x['deck_name']),
            })
        ).reset_index()
        
        # Sort by weighted usage
        card_usage_summary = card_usage_summary.sort_values('weighted_usage', ascending=False)
        
        # Save to cache
        cache_utils.save_card_usage_data(card_usage_summary)
        
        return card_usage_summary

def load_or_update_tournament_data(force_update=False):
    """Load tournament data from cache or update if stale"""
    # Try to load tournament data from cache first
    performance_df, performance_timestamp = cache_utils.load_tournament_performance_data()

    # Import CACHE_TTL from config
    from config import CACHE_TTL

    # Check if data needs to be updated (if it's older than cache TTL or force update)
    if force_update or performance_df.empty or (datetime.now() - performance_timestamp) > timedelta(seconds=CACHE_TTL):
        # Update only if needed - without spinner
        update_stats = update_tournament_tracking()
        
        # Only reanalyze performance if there are new tournaments or no existing data
        if update_stats['new_tournaments'] > 0 or performance_df.empty:
            # Then update performance metrics
            performance_df = analyze_recent_performance(share_threshold=MIN_META_SHARE)
            
            # Save to cache
            cache_utils.save_tournament_performance_data(performance_df)
        
        # Update timestamp regardless of whether we found new data
        # This ensures "Updated just now" even when no new data exists
        performance_timestamp = datetime.now()
        
        # Save the updated timestamp to disk
        with open(cache_utils.TOURNAMENT_TIMESTAMP_PATH, 'w') as f:
            f.write(performance_timestamp.isoformat())

    # Return the loaded or updated data with timestamp
    return performance_df, performance_timestamp

#######################################################################################################################

def track_player_tournament_mapping(deck_name, set_name):
    """Track player and tournament IDs for a deck"""
    from scraper import get_player_tournament_pairs, create_mapping_key
    
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
    """
    Update tournament tracking and deck caches
    
    Returns:
        Dict with stats on updates performed
    """
    # Track update statistics
    stats = {
        'current_tournaments': 0,
        'new_tournaments': 0,
        'affected_decks': 0,
        'updated_decks': 0
    }
    
    # Skip spinner for background updates
    # Load previous tournament IDs
    previous_ids = cache_utils.load_tournament_ids()
    
    # Get current tournament IDs
    current_ids = get_all_recent_tournaments()
    stats['current_tournaments'] = len(current_ids)
    
    # Find new tournament IDs
    new_ids = get_new_tournament_ids(previous_ids)
    stats['new_tournaments'] = len(new_ids)
    
    # If no new tournaments, nothing to do
    if not new_ids:
        return stats
    
    # Save updated tournament IDs
    cache_utils.save_tournament_ids(current_ids)
    
    # Load player-tournament mapping
    mapping = cache_utils.load_player_tournament_mapping()
    
    # Find affected deck archetypes
    affected_decks = get_affected_decks(new_ids, mapping)
    stats['affected_decks'] = len(affected_decks)

    print(f"Found {len(new_ids)} new tournaments: {new_ids}")
    print(f"Found {len(affected_decks)} affected decks: {affected_decks}")
  
    # Update each affected deck
    for deck_name in affected_decks:
        # For now, assume set_name is 'A3' - could be stored in mapping
        set_name = 'A3'
        
        # Update the deck analysis
        success = update_deck_analysis(deck_name, set_name, new_ids)
        
        if success:
            stats['updated_decks'] += 1
    
    return stats

def update_all_caches():
    """
    Comprehensive update of all caching systems.
    """
    # First, update tournament data - this already calls load_or_update_tournament_data internally
    stats = update_tournament_tracking()
    
    # Get the updated performance data
    if 'performance_data' not in st.session_state or st.session_state.performance_data.empty:
        performance_df, performance_timestamp = load_or_update_tournament_data()
        
        # Update session state with performance data
        st.session_state.performance_data = performance_df
        st.session_state.performance_fetch_time = performance_timestamp
    
    # Finally, update card usage data (only if performance data exists)
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
        card_usage_df = aggregate_card_usage(force_update=False)
        st.session_state.card_usage_data = card_usage_df
    
    # Set timestamp
    st.session_state.fetch_time = datetime.now()
    
    return stats

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
        if 'performance_data' in st.session_state and not st.session_state.performance_data.empty:
            performance_data = st.session_state.performance_data
            meta_share_map = {deck['deck_name']: deck['share'] for _, deck in performance_data.iterrows()}
        
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
            matchup_df = matchup_df.sort_values('win_pct', ascending=False).reset_index(drop=True)
        
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
