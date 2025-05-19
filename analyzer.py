# analyzer.py
"""Analysis functions for deck data"""

import pandas as pd
import time
import streamlit as st
from scraper import get_deck_urls, extract_cards
from config import CATEGORY_BINS, CATEGORY_LABELS, FLEXIBLE_CORE_THRESHOLD
from utils import is_flexible_core, calculate_display_usage, format_card_display
from energy_utils import store_energy_types
from cache_utils import save_analyzed_deck_components

# In analyzer.py - Modify analyze_deck function
def collect_decks(deck_name, set_name="A3"):
    """Collect all decks for an archetype and store their data"""
    # Get all decklist URLs
    urls = get_deck_urls(deck_name, set_name)
    
    # Show progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialize collection for all decks
    all_decks = []
    all_energy_types = set()
    
    for i, url in enumerate(urls):
        progress_bar.progress((i + 1) / len(urls))
        #status_text.text(f"Processing deck {i+1}/{len(urls)}...")
        
        # Get cards and energy types
        cards_result = extract_cards(url)
        
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
        
        # Create deck entry
        deck_data = {
            'deck_num': i,
            'cards': cards,
            'energy_types': energy_types,
            'url': url
        }
        
        # Add to collection
        all_decks.append(deck_data)
        
        time.sleep(0.3)  # Be nice to the server
    
    progress_bar.empty()
    status_text.empty()
    
    # Store collected decks in session state for future use
    if 'collected_decks' not in st.session_state:
        st.session_state.collected_decks = {}
    
    deck_key = f"{deck_name}_{set_name}"
    st.session_state.collected_decks[deck_key] = {
        'decks': all_decks,
        'all_energy_types': list(all_energy_types),
        'total_decks': len(urls)
    }
    
    # Return collected data
    return all_decks, list(all_energy_types), len(urls)

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
        if len(card_variants) > 2:
            st.warning(f"Warning: {card_name} has more than 2 variants. Only first 2 will be analyzed.")
        
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
