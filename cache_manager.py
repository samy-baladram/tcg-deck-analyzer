# cache_manager.py
"""Caching management for the TCG Deck Analyzer"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

import cache_utils
from analyzer import analyze_deck, build_deck_template, create_tournament_deck_mapping, update_deck_analysis
from scraper import get_all_recent_tournaments, get_new_tournament_ids, get_affected_decks, analyze_recent_performance, get_sample_deck_for_archetype
from config import MIN_META_SHARE

def init_caches():
    """
    Initialize all necessary caches in session state.
    
    This function sets up:
    - analyzed_deck_cache: Dictionary mapping keys to analyzed deck data
    - sample_deck_cache: Dictionary mapping keys to sample deck data
    - known_tournament_ids: List of known tournament IDs
    - fetch_time: Timestamp of last data fetch
    - performance_fetch_time: Timestamp of last performance data update
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
    
    # Initialize cache timestamps
    if 'fetch_time' not in st.session_state:
        st.session_state.fetch_time = datetime.now()
    
    if 'performance_fetch_time' not in st.session_state:
        st.session_state.performance_fetch_time = datetime.now()
        
    # Ensure initial data is loaded
    if 'first_load' not in st.session_state:
        update_all_caches()
        st.session_state.first_load = True

def get_or_analyze_full_deck(deck_name, set_name):
    """Get full analyzed deck from cache or analyze if not cached"""
    # First check session cache
    cache_key = f"full_deck_{deck_name}_{set_name}"
    if cache_key in st.session_state.analyzed_deck_cache:
        print(f"Found {deck_name} in session cache")
        return st.session_state.analyzed_deck_cache[cache_key]
    
    # Then check disk cache
    cached_results, cached_total_decks, cached_variant_df, cached_energy_types = cache_utils.load_analyzed_deck_components(deck_name, set_name)
    
    if cached_results is not None:
        print(f"Using cached data for {deck_name}")
        
        # Generate the deck template from cached results
        deck_list, deck_info, total_cards, options = build_deck_template(cached_results)
        
        # Try to get the most common energy combination from disk or collected decks
        most_common_energy = []
        deck_key = f"{deck_name}_{set_name}"
        
        # Check if we already have collected decks to calculate most common energy
        if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
            collected_data = st.session_state.collected_decks[deck_key]
            if 'decks' in collected_data and collected_data['decks']:
                most_common_energy = calculate_most_common_energy(collected_data['decks'])
        
        # If no collected decks, use cached energy types
        if not most_common_energy and cached_energy_types:
            most_common_energy = cached_energy_types
        
        # Create cache entry
        analyzed_data = {
            'results': cached_results,
            'total_decks': cached_total_decks,
            'variant_df': cached_variant_df,
            'deck_list': deck_list,
            'deck_info': deck_info,
            'total_cards': total_cards,
            'options': options,
            'energy_types': cached_energy_types,  # All energy types
            'most_common_energy': most_common_energy  # Most common combination
        }
        
        # Store in session cache
        st.session_state.analyzed_deck_cache[cache_key] = analyzed_data
        return analyzed_data
    
    # If not in any cache, analyze the deck
    print(f"No cache found for {deck_name}, analyzing")
    
    # Analyze the deck (now returns energy types too)
    results, total_decks, variant_df, energy_types = analyze_deck(deck_name, set_name)
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    # Calculate most common energy combination
    most_common_energy = []
    deck_key = f"{deck_name}_{set_name}"
    
    # Check if we have collected decks to calculate most common energy
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        collected_data = st.session_state.collected_decks[deck_key]
        if 'decks' in collected_data and collected_data['decks']:
            most_common_energy = calculate_most_common_energy(collected_data['decks'])
    
    # If no collected decks, use all energy types
    if not most_common_energy and energy_types:
        most_common_energy = energy_types
    
    # Create cache entry
    analyzed_data = {
        'results': results,
        'total_decks': total_decks,
        'variant_df': variant_df,
        'deck_list': deck_list,
        'deck_info': deck_info,
        'total_cards': total_cards,
        'options': options,
        'energy_types': energy_types,  # All energy types
        'most_common_energy': most_common_energy  # Most common combination
    }
    
    # Store in session cache
    st.session_state.analyzed_deck_cache[cache_key] = analyzed_data
    
    # Store in disk cache
    cache_utils.save_analyzed_deck_components(deck_name, set_name, results, total_decks, variant_df, energy_types)
    
    return analyzed_data

def get_or_load_sample_deck(deck_name, set_name):
    """Get sample deck from cache or load if not cached"""
    cache_key = f"sample_deck_{deck_name}_{set_name}"
    
    # Check if sample deck is in cache
    if cache_key in st.session_state.sample_deck_cache:
        return st.session_state.sample_deck_cache[cache_key]
    
    # Try to load energy types from analyzed deck cache first
    energy_types = []
    most_common_energy = []
    analyzed_key = f"full_deck_{deck_name}_{set_name}"
    
    if analyzed_key in st.session_state.analyzed_deck_cache:
        energy_types = st.session_state.analyzed_deck_cache[analyzed_key].get('energy_types', [])
        most_common_energy = st.session_state.analyzed_deck_cache[analyzed_key].get('most_common_energy', [])
    
    # If no energy types in analyzed cache, try to load from disk
    if not energy_types:
        # Check if we have analyzed deck components on disk
        _, _, _, disk_energy_types = cache_utils.load_analyzed_deck_components(deck_name, set_name)
        energy_types = disk_energy_types
    
    # If still no energy types, load sample deck (which might have energy types)
    pokemon_cards, trainer_cards, deck_energy_types = get_sample_deck_for_archetype(deck_name, set_name)
    
    # Use energy types from deck if available, otherwise use what we found earlier
    if deck_energy_types:
        energy_types = deck_energy_types
        # If no most_common_energy yet, use deck_energy_types as fallback
        if not most_common_energy:
            most_common_energy = deck_energy_types
    
    # Store in cache
    st.session_state.sample_deck_cache[cache_key] = {
        'pokemon_cards': pokemon_cards,
        'trainer_cards': trainer_cards,
        'energy_types': energy_types,
        'most_common_energy': most_common_energy
    }
    
    return st.session_state.sample_deck_cache[cache_key]

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

def load_or_update_tournament_data():
    """Load tournament data from cache or update if stale"""
    # Try to load tournament data from cache first
    performance_df, performance_timestamp = cache_utils.load_tournament_performance_data()

    # Check if data needs to be updated (if it's older than 1 hour)
    if performance_df.empty or (datetime.now() - performance_timestamp) > timedelta(hours=1):
        with st.spinner("Updating tournament performance data..."):
            # First check for new tournaments and update affected decks
            update_stats = update_tournament_tracking()
            
            # Only reanalyze performance if there are new tournaments or no existing data
            if update_stats['new_tournaments'] > 0 or performance_df.empty:
                # Then update performance metrics
                performance_df = analyze_recent_performance(share_threshold=MIN_META_SHARE)
                
                # Save to cache
                cache_utils.save_tournament_performance_data(performance_df)
                
                # Update timestamp
                performance_timestamp = datetime.now()
                
                # Show update stats if there were any updates
                if update_stats['new_tournaments'] > 0:
                    st.success(f"Found {update_stats['new_tournaments']} new tournaments. "
                              f"Updated {update_stats['updated_decks']} affected decks.")

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
    
    with st.spinner("Checking for new tournaments..."):
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
      
        # In update_tournament_tracking, add batch processing
        if len(affected_decks) > 5:
            st.info(f"Updating {len(affected_decks)} decks. This may take a while...")
            
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
    Ensure analyzed deck and collected deck data are consistent
    This is called when a deck is loaded or analyzed
    """
    # Cache keys
    deck_key = f"{deck_name}_{set_name}"
    cache_key = f"full_deck_{deck_name}_{set_name}"
    
    # Check if we have analyzed data but no collected data
    if (cache_key in st.session_state.analyzed_deck_cache and 
        (deck_key not in st.session_state.collected_decks or not st.session_state.collected_decks[deck_key].get('decks'))):
        
        # Force collection to populate collected_decks
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
            
    # Check if we have collected data but no analyzed data
    elif (deck_key in st.session_state.collected_decks and 
          cache_key not in st.session_state.analyzed_deck_cache):
        
        # Collected data exists, so analyze using that
        from analyzer import analyze_deck
        from cache_utils import save_analyzed_deck_components
        
        # Use the existing collected decks
        collected_data = st.session_state.collected_decks[deck_key]
        
        # Re-analyze (this will update the session state)
        results, total_decks, variant_df, energy_types = analyze_deck(deck_name, set_name)
        
        # Create and save analyzed data
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
    for deck in decks:
        if not deck.get('energy_types'):
            continue
            
        # Create a tuple of sorted energy types for consistent keys
        combo = tuple(sorted(deck['energy_types']))
        if combo:  # Only count if there are any energy types
            combinations[combo] = combinations.get(combo, 0) + 1
    
    # Find the most common combination
    if combinations:
        most_common = max(combinations.items(), key=lambda x: x[1])[0]
        return list(most_common)
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
        return st.session_state.energy_cache[cache_key]
    
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
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        collected_data = st.session_state.collected_decks[deck_key]
        if 'decks' in collected_data and collected_data['decks']:
            energy_types = calculate_most_common_energy(collected_data['decks'])
            print(f"Calculated energy for {deck_name} from collected decks: {energy_types}")
    
    # If not found from collected decks, try analyzed cache
    if not energy_types:
        analyzed_key = f"full_deck_{deck_name}_{set_name}"
        if analyzed_key in st.session_state.analyzed_deck_cache:
            energy_types = st.session_state.analyzed_deck_cache[analyzed_key].get('energy_types', [])
            print(f"Using energy from analyzed cache for {deck_name}: {energy_types}")
    
    # If still not found, try sample deck
    if not energy_types:
        sample_key = f"sample_deck_{deck_name}_{set_name}"
        if sample_key in st.session_state.sample_deck_cache:
            energy_types = st.session_state.sample_deck_cache[sample_key].get('energy_types', [])
            print(f"Using energy from sample deck for {deck_name}: {energy_types}")
    
    # Cache the result
    st.session_state.energy_cache[cache_key] = energy_types
    print(f"Cached energy for {deck_name}: {energy_types}")
    
    return energy_types
