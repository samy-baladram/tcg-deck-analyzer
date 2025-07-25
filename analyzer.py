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
from scraper import get_deck_urls, extract_cards
from config import CATEGORY_BINS, CATEGORY_LABELS, FLEXIBLE_CORE_THRESHOLD, CURRENT_SET
from utils import is_flexible_core, calculate_display_usage, format_card_display
#from energy_utils import store_energy_types
from cache_utils import save_analyzed_deck_components
import math
    
# In analyzer.py - Modify analyze_deck function
# Modify the collect_decks function in analyzer.py to save to disk

def collect_decks(deck_name, set_name=CURRENT_SET):
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
        
        # time.sleep(0.2)  # Be nice to the server
    
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

def analyze_deck(deck_name, set_name=CURRENT_SET):
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

# def update_deck_analysis(deck_name, set_name, new_tournament_ids):
#     """
#     Update deck analysis by incorporating data from new tournaments
    
#     Args:
#         deck_name: Name of the deck archetype
#         set_name: Set code (e.g., "A3")
#         new_tournament_ids: List of new tournament IDs to analyze
        
#     Returns:
#         Boolean indicating success
#     """
#     # Check if decks have already been collected
#     deck_key = f"{deck_name}_{set_name}"
    
#     # Show status
#     status = st.empty()
#     status.text(f"Updating analysis for {deck_name}...")
    
#     if 'collected_decks' not in st.session_state or deck_key not in st.session_state.collected_decks:
#         # If no existing data, just do a full analysis
#         status.text(f"No existing data for {deck_name}, performing full analysis...")
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
#         # No new data to add
#         status.text(f"No new data found for {deck_name}")
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
    
#     # Rerun analysis with the combined dataset
#     # This will reuse the stored decks rather than fetching again
#     status.text(f"Running analysis on combined data for {deck_name}...")
#     analyze_deck(deck_name, set_name)
    
#     status.empty()
#     return True
def update_deck_analysis(deck_name, set_name, new_tournament_ids):
    """Update deck analysis with new tournament data - clear caches first"""
    
    # Show status
    status = st.empty()
    status.text(f"Re-analyzing {deck_name} with new tournament data...")
    
    # CRITICAL: Clear ALL caches BEFORE doing anything
    clear_all_deck_caches(deck_name, set_name)
    print(f"Cleared all caches for {deck_name} due to new tournament data")
    
    # Force fresh collection and analysis
    status.text(f"Collecting fresh data for {deck_name}...")
    from analyzer import collect_decks, analyze_deck
    
    # Force fresh collection (this will also clear any existing collected data)
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

def clear_all_deck_caches(deck_name, set_name):
    """Clear ALL caches for a specific deck to force fresh analysis"""
    
    # Clear session caches
    cache_key = f"full_deck_{deck_name}_{set_name}"
    sample_key = f"sample_deck_{deck_name}_{set_name}"
    energy_key = f"energy_{deck_name}"
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
    
    # Clear disk caches
    cache_utils.clear_deck_cache(deck_name, set_name)
    
    # Clear energy utils cache
    if 'archetype_energy_types' in st.session_state and deck_name in st.session_state.archetype_energy_types:
        del st.session_state.archetype_energy_types[deck_name]
    
    if 'archetype_energy_combos' in st.session_state and deck_name in st.session_state.archetype_energy_combos:
        del st.session_state.archetype_energy_combos[deck_name]
    
    # CRITICAL: Also clear card cache
    from card_cache import invalidate_deck_cache
    invalidate_deck_cache(deck_name, set_name)
    
    print(f"Cleared ALL caches for {deck_name}")
