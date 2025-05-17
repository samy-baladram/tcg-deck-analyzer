# cache_manager.py
"""Caching management for the TCG Deck Analyzer"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

import cache_utils
from analyzer import analyze_deck, build_deck_template
from scraper import analyze_recent_performance, get_sample_deck_for_archetype
from config import MIN_META_SHARE

def init_caches():
    """Initialize all necessary caches in session state"""
    # Deck analysis cache
    if 'analyzed_deck_cache' not in st.session_state:
        st.session_state.analyzed_deck_cache = {}
    
    # Sample deck cache
    if 'sample_deck_cache' not in st.session_state:
        st.session_state.sample_deck_cache = {}
    
    # Initialize cache timestamps
    if 'fetch_time' not in st.session_state:
        st.session_state.fetch_time = datetime.now()
    
    if 'performance_fetch_time' not in st.session_state:
        st.session_state.performance_fetch_time = datetime.now()

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
        
        # Create cache entry
        analyzed_data = {
            'results': cached_results,
            'total_decks': cached_total_decks,
            'variant_df': cached_variant_df,
            'deck_list': deck_list,
            'deck_info': deck_info,
            'total_cards': total_cards,
            'options': options,
            'energy_types': cached_energy_types  # Add energy types
        }
        
        # Store energy types for this archetype
        from energy_utils import store_energy_types
        store_energy_types(deck_name, cached_energy_types)
        
        # Store in session cache
        st.session_state.analyzed_deck_cache[cache_key] = analyzed_data
        return analyzed_data
    
    # If not in any cache, analyze the deck
    print(f"No cache found for {deck_name}, analyzing")
    
    # Analyze the deck (now returns energy types too)
    results, total_decks, variant_df, energy_types = analyze_deck(deck_name, set_name)
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    # Create cache entry
    analyzed_data = {
        'results': results,
        'total_decks': total_decks,
        'variant_df': variant_df,
        'deck_list': deck_list,
        'deck_info': deck_info,
        'total_cards': total_cards,
        'options': options,
        'energy_types': energy_types  # Add energy types
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
    analyzed_key = f"full_deck_{deck_name}_{set_name}"
    if analyzed_key in st.session_state.analyzed_deck_cache:
        energy_types = st.session_state.analyzed_deck_cache[analyzed_key].get('energy_types', [])
    
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
    
    # Store energy types in archetype mapping
    from energy_utils import store_energy_types
    store_energy_types(deck_name, energy_types)
    
    # Store in cache
    st.session_state.sample_deck_cache[cache_key] = {
        'pokemon_cards': pokemon_cards,
        'trainer_cards': trainer_cards,
        'energy_types': energy_types
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
        top_decks = performance_df.head(5)
        
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
                results, _, _ = analyze_deck(deck_name, set_name)
                
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
            # Analyze recent performance
            performance_df = analyze_recent_performance(share_threshold=MIN_META_SHARE)
            
            # Save to cache
            cache_utils.save_tournament_performance_data(performance_df)
            
            # Update timestamp
            performance_timestamp = datetime.now()

    # Return the loaded or updated data with timestamp
    return performance_df, performance_timestamp
