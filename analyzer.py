# analyzer.py

"""
This module contains functions for analyzing deck data, including:
1. Card usage analysis
2. Performance metrics calculation
3. Variant analysis
4. Dynamic updating with new tournament data
"""

import pandas as pd
import time
import streamlit as st
from scraper import get_deck_urls, extract_cards, get_deck_performance_data
from config import CATEGORY_BINS, CATEGORY_LABELS, FLEXIBLE_CORE_THRESHOLD
from utils import is_flexible_core, calculate_display_usage, format_card_display
#from energy_utils import store_energy_types
from cache_utils import save_analyzed_deck_components
import math

# Modify analyze_recent_performance() to log its version
def analyze_recent_performance(raw_performance_data=None):
    """
    Analyze the recent performance of popular decks
    Can either fetch new data or use provided raw_performance_data
    """
    from config import ALGORITHM_VERSION
    print(f"🔄 Running analyze_recent_performance() version {ALGORITHM_VERSION}")
    
    import math
    
    if raw_performance_data is None:
        # Import from scraper if not provided
        from scraper import get_deck_performance_data
        raw_performance_data = get_deck_performance_data()
    
    # Process the raw data with Wilson Score Interval
    results = []
    
    for deck_data in raw_performance_data:
        # Extract performance data
        performance = deck_data['performance']
        
        # Calculate totals
        total_wins = performance['wins'].sum()
        total_losses = performance['losses'].sum()
        total_ties = performance['ties'].sum()
        tournaments_played = len(performance['tournament_id'])
        
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
        else:
            power_index = 0.0
        
        results.append({
            'deck_name': deck_data['deck_name'],
            'displayed_name': deck_data['displayed_name'],
            'share': deck_data['share'],
            'set': deck_data['set'],
            'total_wins': total_wins,
            'total_losses': total_losses,
            'total_ties': total_ties,
            'tournaments_played': tournaments_played,
            'power_index': power_index,
            'win_rate': (total_wins + (0.5 * total_ties)) / total_games if total_games > 0 else 0
        })
    
    # Convert to DataFrame and sort
    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values('power_index', ascending=False).reset_index(drop=True)
    
    # Add version to output
    results_df['algorithm_version'] = ALGORITHM_VERSION
    return results_df
    
# In analyzer.py - Modify analyze_deck function
# Modify the collect_decks function in analyzer.py to save to disk

def collect_decks(deck_name, set_name="A3"):
    """Collect all decks for an archetype and store their data"""
    # Get all player-tournament pairs instead of just URLs
    from scraper import get_player_tournament_pairs, extract_cards, get_deck_by_player_tournament
    pairs = get_player_tournament_pairs(deck_name, set_name)
    
    # Show progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialize collection for all decks
    all_decks = []
    all_energy_types = set()
    
    # Handle the case of no pairs found
    if not pairs:
        progress_bar.empty()
        status_text.empty()
        return all_decks, list(all_energy_types), 0
    
    for i, pair in enumerate(pairs):
        progress_bar.progress((i + 1) / len(pairs))
        status_text.text(f"Loading deck {i+1} of {len(pairs)}...")
        
        # Get cards and energy types using the URL from the pair
        url = pair['url']
        
        # Try direct extraction first
        try:
            cards_result = extract_cards(url)
            
            # Handle both formats
            if isinstance(cards_result, tuple) and len(cards_result) == 2:
                cards, energy_types = cards_result
            else:
                # Old format or no energy types
                cards = cards_result
                energy_types = []
                
        except Exception as e:
            # If extraction fails, try the alternative method
            try:
                # Try alternative direct method using player and tournament IDs
                cards, energy_types = get_deck_by_player_tournament(
                    pair['tournament_id'], 
                    pair['player_id']
                )
            except Exception:
                # Skip this deck if both methods fail
                continue
        
        # Add energy types to the global set
        if energy_types:
            all_energy_types.update(energy_types)
            
            # Track per-deck energy
            from energy_utils import track_per_deck_energy
            track_per_deck_energy(deck_name, i, energy_types)
        
        # Create deck entry with player and tournament IDs
        deck_data = {
            'deck_num': i,
            'cards': cards,
            'energy_types': energy_types,
            'url': url,
            'player_id': pair['player_id'],
            'tournament_id': pair['tournament_id']
        }
        
        # Add to collection
        all_decks.append(deck_data)
        
        time.sleep(0.3)  # Be nice to the server
    
    progress_bar.empty()
    status_text.empty()
    
    # Store collected decks in session state for future use
    if 'collected_decks' not in st.session_state:
        st.session_state.collected_decks = {}
    
    total_decks = len(pairs)  # Use the number of pairs instead of urls
    
    deck_key = f"{deck_name}_{set_name}"
    st.session_state.collected_decks[deck_key] = {
        'decks': all_decks,
        'all_energy_types': list(all_energy_types),
        'total_decks': total_decks
    }
    
    # Save to disk cache
    import cache_utils
    cache_utils.save_collected_decks(deck_name, set_name, all_decks, list(all_energy_types), total_decks)
    
    # Return collected data
    return all_decks, list(all_energy_types), total_decks

def collect_decks_by_tournaments(deck_name, set_name, tournament_ids):
    """
    Collect only decks from specific tournaments for an archetype
    
    Args:
        deck_name: Name of the deck archetype
        set_name: Set code (e.g., "A3")
        tournament_ids: List of tournament IDs to collect from
        
    Returns:
        Same as collect_decks but only includes decks from the specified tournaments
    """
    from scraper import get_player_tournament_pairs, extract_cards
    
    # Get all player-tournament pairs
    pairs = get_player_tournament_pairs(deck_name, set_name)
    
    # Filter pairs to only include specified tournaments
    tournament_id_set = set(tournament_ids)
    filtered_pairs = [pair for pair in pairs if pair['tournament_id'] in tournament_id_set]
    
    # Show progress
    progress_bar = st.progress(0)
    
    # Initialize collection
    all_decks = []
    all_energy_types = set()
    
    # Handle the case of no pairs found
    if not filtered_pairs:
        progress_bar.empty()
        return all_decks, list(all_energy_types), 0
    
    # Process filtered pairs
    for i, pair in enumerate(filtered_pairs):
        progress_bar.progress((i + 1) / len(filtered_pairs))
        
        # Get cards and energy types
        url = pair['url']  # Define url from the pair
        cards_result = extract_cards(url)
        
        # Rest of processing similar to collect_decks
        # Handle both formats
        if isinstance(cards_result, tuple) and len(cards_result) == 2:
            cards, energy_types = cards_result
        else:
            # Old format or no energy types
            cards = cards_result
            energy_types = []
        
        # Add energy types to the global set
        if energy_types:
            all_energy_types.update(energy_types)
            
            # Track per-deck energy
            from energy_utils import track_per_deck_energy
            track_per_deck_energy(deck_name, i, energy_types)
        
        # Create deck entry with player and tournament IDs
        deck_data = {
            'deck_num': i,
            'cards': cards,
            'energy_types': energy_types,
            'url': url,
            'player_id': pair['player_id'],
            'tournament_id': pair['tournament_id']
        }
        
        # Add to collection
        all_decks.append(deck_data)
        
        time.sleep(0.3)  # Be nice to the server
    
    progress_bar.empty()
        
    # Return in the same format as collect_decks
    return all_decks, list(all_energy_types), len(filtered_pairs)

def create_tournament_deck_mapping(decks_data):
    """
    Create a mapping of tournament IDs to deck archetypes
    
    Args:
        decks_data: Dictionary mapping deck_name to collected deck data
        
    Returns:
        Dictionary mapping tournament_id to set of deck_names that use it
    """
    tournament_map = {}
    
    for deck_name, data in decks_data.items():
        for deck in data['decks']:
            if 'tournament_id' in deck:
                tournament_id = deck['tournament_id']
                if tournament_id not in tournament_map:
                    tournament_map[tournament_id] = set()
                tournament_map[tournament_id].add(deck_name)
    
    return tournament_map

# def update_deck_analysis(deck_name, set_name, new_tournament_ids):
#     """Update deck analysis by incorporating data from new tournaments"""
    
#     deck_key = f"{deck_name}_{set_name}"
    
#     # Show status
#     status = st.empty()
#     status.text(f"Updating analysis for {deck_name}...")
    
#     if 'collected_decks' not in st.session_state or deck_key not in st.session_state.collected_decks:
#         # If no existing data, clear cache and do full analysis
#         clear_deck_cache_on_switch(deck_name, set_name)  # ADD THIS
#         analyze_deck(deck_name, set_name)
#         status.empty()
#         return True
    
#     # Get existing collected data
#     collected_data = st.session_state.collected_decks[deck_key]
#     existing_decks = collected_data['decks']
#     existing_energy_types = set(collected_data['all_energy_types'])
    
#     # Get new decks from specified tournaments
#     status.text(f"Fetching new data for {deck_name} from {len(new_tournament_ids)} tournaments...")
#     new_decks, new_energy_types, new_total = collect_decks_by_tournaments(
#         deck_name, set_name, new_tournament_ids
#     )
    
#     if not new_decks:
#         status.empty()
#         return False
    
#     # Show updating status
#     status.text(f"Updating {deck_name} with {len(new_decks)} new decks...")
    
#     # Merge energy types
#     all_energy_types = existing_energy_types.union(new_energy_types)
    
#     # Assign new deck numbers to avoid conflicts
#     start_num = len(existing_decks)
#     for i, deck in enumerate(new_decks):
#         deck['deck_num'] = start_num + i
    
#     # Combine existing and new decks
#     all_decks = existing_decks + new_decks
#     total_decks = len(all_decks)
    
#     # Update session state
#     st.session_state.collected_decks[deck_key] = {
#         'decks': all_decks,
#         'all_energy_types': list(all_energy_types),
#         'total_decks': total_decks
#     }
    
#     # CLEAR CACHE BEFORE REANALYSIS - THIS IS THE KEY FIX
#     clear_deck_cache_on_switch(deck_name, set_name)
    
#     # Force refresh if this is the currently selected deck
#     if ('analyze' in st.session_state and 
#         st.session_state.analyze.get('deck_name') == deck_name):
#         st.session_state.force_deck_refresh = True
    
#     # Rerun analysis with the combined dataset
#     status.text(f"Running analysis on combined data for {deck_name}...")
#     analyze_deck(deck_name, set_name)
    
#     status.empty()
#     return True
def update_deck_analysis(deck_name, set_name, new_tournament_ids):
    """Update deck analysis with new tournament data - assumes caches already cleared"""
    
    deck_key = f"{deck_name}_{set_name}"
    
    # Show status
    status = st.empty()
    status.text(f"Re-analyzing {deck_name} with new tournament data...")
    
    # Since caches are cleared, force fresh collection and analysis
    status.text(f"Collecting fresh data for {deck_name}...")
    all_decks, all_energy_types, total_decks = collect_decks(deck_name, set_name)
    
    if not all_decks:
        status.text(f"No data found for {deck_name}")
        status.empty()
        return False
    
    # Run fresh analysis with all data (including new tournaments)
    status.text(f"Running fresh analysis for {deck_name}...")
    results, total_decks, variant_df, energy_types = analyze_deck(deck_name, set_name)
    
    # If this is the currently selected deck, trigger refresh
    if ('analyze' in st.session_state and 
        st.session_state.analyze.get('deck_name') == deck_name):
        st.session_state.force_deck_refresh = True
        st.session_state.auto_refresh_in_progress = True
    
    status.empty()
    return True

def analyze_deck(deck_name, set_name="A3"):
    """Main analysis function for a deck archetype"""
    # Check if decks have already been collected
    deck_key = f"{deck_name}_{set_name}"
    
    if 'collected_decks' in st.session_state and deck_key in st.session_state.collected_decks:
        # Use existing collected data
        collected_data = st.session_state.collected_decks[deck_key]
        all_decks = collected_data['decks']
        all_energy_types = collected_data['all_energy_types']
        total_decks = collected_data['total_decks']
    else:
        # Collect decks if not already done
        all_decks, all_energy_types, total_decks = collect_decks(deck_name, set_name)
    
    # Prepare all cards for analysis
    all_cards = []
    deck_energy_data = []
    
    for deck in all_decks:
        # Add deck_num to cards
        for card in deck['cards']:
            card['deck_num'] = deck['deck_num']
        
        all_cards.extend(deck['cards'])
        
        # Add energy data for display
        if deck['energy_types']:
            deck_energy_data.append({
                'deck_num': deck['deck_num'],
                'energy_types': sorted(deck['energy_types'])
            })
    
    # Create dataframe and analyze
    df = pd.DataFrame(all_cards)
    
    # Aggregate card usage
    grouped = df.groupby(['type', 'card_name', 'set', 'num']).agg(
        count_1=('amount', lambda x: sum(x == 1)),
        count_2=('amount', lambda x: sum(x == 2))
    ).reset_index()
    
    # Calculate percentages
    grouped['pct_1'] = (grouped['count_1'] / total_decks * 100).astype(int)
    grouped['pct_2'] = (grouped['count_2'] / total_decks * 100).astype(int)
    grouped['pct_total'] = grouped['pct_1'] + grouped['pct_2']
    
    # Categorize cards
    grouped['category'] = pd.cut(
        grouped['pct_total'], 
        bins=CATEGORY_BINS,
        labels=CATEGORY_LABELS
    )
    
    # Determine majority count
    grouped['majority'] = grouped.apply(
        lambda row: 2 if row['count_2'] > row['count_1'] else 1,
        axis=1
    )
    
    # Sort results
    grouped = grouped.sort_values(['type', 'pct_total'], ascending=[True, False])
    
    # Analyze variants
    variant_df = analyze_variants(grouped, df)
    
    # Store energy types in session state for the archetype
    if all_energy_types:
        from energy_utils import store_energy_types
        store_energy_types(deck_name, all_energy_types)
    
    # Save to disk cache
    save_analyzed_deck_components(
        deck_name,
        set_name,
        grouped,
        total_decks,
        variant_df,
        all_energy_types
    )
    
    # Store the deck energy data in session state for debugging
    if deck_energy_data:
        if 'deck_energy_data' not in st.session_state:
            st.session_state.deck_energy_data = {}
        st.session_state.deck_energy_data[deck_name] = deck_energy_data
    
    # Return the traditional tuple format for backward compatibility
    return grouped, total_decks, variant_df, all_energy_types
    

def build_deck_template(analysis_df):
    """Build a deck template from analysis results"""
    # Get core cards
    core_cards = analysis_df[analysis_df['category'] == 'Core'].copy()
    
    # Initialize deck
    deck_list = {'Pokemon': [], 'Trainer': []}
    # Store additional card info for image display
    deck_info = {'Pokemon': [], 'Trainer': []}
    total_cards = 0
    
    # Add core cards to deck
    for _, card in core_cards.iterrows():
        count = 1 if is_flexible_core(card) else int(card['majority'])
        total_cards += count
        
        # Format card display
        card_display = f"{count} {format_card_display(card['card_name'], card['set'], card['num'])}"
        deck_list[card['type']].append(card_display)
        
        # Store card info for image display
        deck_info[card['type']].append({
            'count': count,
            'name': card['card_name'],
            'set': card['set'],
            'num': card['num']
        })
    
    # Get options (standard + flexible core)
    options = pd.concat([
        analysis_df[analysis_df['category'] == 'Standard'],
        analysis_df[analysis_df['category'] == 'Tech'],
        analysis_df[(analysis_df['category'] == 'Core') & 
                   (((analysis_df['pct_1'] >= FLEXIBLE_CORE_THRESHOLD) & (analysis_df['majority'] == 2)) |
                    ((analysis_df['pct_2'] >= FLEXIBLE_CORE_THRESHOLD) & (analysis_df['majority'] == 1)))]
    ]).drop_duplicates()
    
    # Add flexible usage column
    options = options.copy()
    options['display_usage'] = options.apply(calculate_display_usage, axis=1)
    
    return deck_list, deck_info, total_cards, options

def analyze_variants(result_df, all_cards_df):
    """Analyze variant usage patterns"""
    # Find cards with multiple entries (variants)
    card_counts = result_df.groupby('card_name').size()
    cards_with_variants = card_counts[card_counts > 1].index
    
    variant_summaries = []
    
    for card_name in cards_with_variants:
        # Get all variants of this card
        card_variants = result_df[result_df['card_name'] == card_name]
        
        # For now, handle up to 2 variants (most common case)
        # if len(card_variants) > 2:
        #     st.warning(f"Warning: {card_name} has more than 2 variants. Only first 2 will be analyzed.")
        
        # Get variant IDs
        variant_list = []
        for idx, (_, variant) in enumerate(card_variants.iterrows()):
            if idx < 2:  # Only take first 2 variants
                variant_list.append(f"{variant['set']}-{variant['num']}")
        
        # Initialize summary
        summary = {
            'Card Name': card_name,
            'Total Decks': 0,
            'Var1': variant_list[0] if len(variant_list) > 0 else "",
            'Var2': variant_list[1] if len(variant_list) > 1 else "",
            #'Variants': ', '.join(variant_list),  # Keep this for compatibility with existing code
            'Both Var1': 0,
            'Both Var2': 0,
            'Mixed': 0,
            'Single Var1': 0,
            'Single Var2': 0
        }
        
        # Analyze usage patterns across decks
        deck_count = 0
        
        # For each deck, check which variants it uses
        for deck_num in all_cards_df['deck_num'].unique():
            deck_cards = all_cards_df[
                (all_cards_df['deck_num'] == deck_num) &
                (all_cards_df['card_name'] == card_name)
            ]
            
            if not deck_cards.empty:
                deck_count += 1
                
                # Check pattern for this deck
                var1_count = 0
                var2_count = 0
                
                for _, card in deck_cards.iterrows():
                    variant_id = f"{card['set']}-{card['num']}"
                    if variant_id == variant_list[0]:
                        var1_count += card['amount']
                    elif len(variant_list) > 1 and variant_id == variant_list[1]:
                        var2_count += card['amount']
                
                # Categorize the pattern
                if var1_count == 2 and var2_count == 0:
                    summary['Both Var1'] += 1
                elif var2_count == 2 and var1_count == 0:
                    summary['Both Var2'] += 1
                elif var1_count == 1 and var2_count == 1:
                    summary['Mixed'] += 1
                elif var1_count == 1 and var2_count == 0:
                    summary['Single Var1'] += 1
                elif var2_count == 1 and var1_count == 0:
                    summary['Single Var2'] += 1
        
        summary['Total Decks'] = deck_count
        variant_summaries.append(summary)
    
    if not variant_summaries:
        return pd.DataFrame()
    
    variant_df = pd.DataFrame(variant_summaries)
    return variant_df.sort_values('Total Decks', ascending=False)

def update_deck_analysis(deck_name, set_name, new_tournament_ids):
    """
    Update deck analysis by incorporating data from new tournaments
    
    Args:
        deck_name: Name of the deck archetype
        set_name: Set code (e.g., "A3")
        new_tournament_ids: List of new tournament IDs to analyze
        
    Returns:
        Boolean indicating success
    """
    # Check if decks have already been collected
    deck_key = f"{deck_name}_{set_name}"
    
    # Show status
    status = st.empty()
    status.text(f"Updating analysis for {deck_name}...")
    
    if 'collected_decks' not in st.session_state or deck_key not in st.session_state.collected_decks:
        # If no existing data, just do a full analysis
        status.text(f"No existing data for {deck_name}, performing full analysis...")
        analyze_deck(deck_name, set_name)
        status.empty()
        return True
    
    # Get existing collected data
    collected_data = st.session_state.collected_decks[deck_key]
    existing_decks = collected_data['decks']
    existing_energy_types = set(collected_data['all_energy_types'])
    
    # Get new decks from specified tournaments
    status.text(f"Fetching new data for {deck_name} from {len(new_tournament_ids)} tournaments...")
    new_decks, new_energy_types, new_total = collect_decks_by_tournaments(
        deck_name, set_name, new_tournament_ids
    )
    
    if not new_decks:
        # No new data to add
        status.text(f"No new data found for {deck_name}")
        status.empty()
        return False
    
    # Show updating status
    status.text(f"Updating {deck_name} with {len(new_decks)} new decks...")
    
    # Merge energy types
    all_energy_types = existing_energy_types.union(new_energy_types)
    
    # Assign new deck numbers to avoid conflicts
    start_num = len(existing_decks)
    for i, deck in enumerate(new_decks):
        deck['deck_num'] = start_num + i
    
    # Combine existing and new decks
    all_decks = existing_decks + new_decks
    total_decks = len(all_decks)
    
    # Update session state
    st.session_state.collected_decks[deck_key] = {
        'decks': all_decks,
        'all_energy_types': list(all_energy_types),
        'total_decks': total_decks
    }
    
    # Rerun analysis with the combined dataset
    # This will reuse the stored decks rather than fetching again
    status.text(f"Running analysis on combined data for {deck_name}...")
    analyze_deck(deck_name, set_name)
    
    status.empty()
    return True
