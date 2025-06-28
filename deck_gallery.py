# deck_gallery.py
"""Deck Gallery display functions for showcasing all fetched decks"""

import streamlit as st
import pandas as pd
from display_tabs import display_deck_template_tab
from ui_helpers import get_header_image_cached, format_deck_name

def display_deck_gallery():
    """
    Display all collected decks in a three-column gallery format.
    Each deck shows in an expander with format: "Deck {number}. Record {record}"
    """
    
    # Check if we have collected decks data
    if 'collected_decks' not in st.session_state or not st.session_state.collected_decks:
        st.info("No deck data available. Please analyze some decks first.")
        return
    
    # Extract all deck information
    all_deck_info = []
    
    for deck_key, deck_data in st.session_state.collected_decks.items():
        # Parse deck_key format: "deck_name_set_name"
        parts = deck_key.rsplit('_', 1)
        if len(parts) == 2:
            deck_name, set_name = parts
        else:
            deck_name = deck_key
            set_name = 'A3'  # fallback
        
        # Get all individual deck instances for this archetype
        if 'decks' in deck_data and deck_data['decks']:
            for deck_instance in deck_data['decks']:
                # Extract record if available
                record = deck_instance.get('record', 'No record')
                deck_num = deck_instance.get('deck_num', 'Unknown')
                
                all_deck_info.append({
                    'deck_name': deck_name,
                    'set_name': set_name,
                    'deck_key': deck_key,
                    'deck_num': deck_num,
                    'record': record,
                    'deck_instance': deck_instance,
                    'deck_data': deck_data
                })
    
    if not all_deck_info:
        st.info("No deck instances found in collected data.")
        return
    
    st.write(f"### Deck Gallery ({len(all_deck_info)} decks)")
    
    # Create three-column layout
    cols = st.columns(3)
    
    for i, deck_info in enumerate(all_deck_info):
        col_idx = i % 3
        
        with cols[col_idx]:
            # Format expander title
            expander_title = f"Deck {deck_info['deck_num']}. Record {deck_info['record']}"
            
            with st.expander(expander_title, expanded=False):
                # Display deck header image
                header_image = get_header_image_cached(
                    deck_info['deck_name'], 
                    deck_info['set_name']
                )
                
                if header_image:
                    st.markdown(f"""
                    <div style="width: 100%; margin-bottom: 12px;">
                        <img src="data:image/png;base64,{header_image}" 
                             style="width: 100%; height: auto; border-radius: 4px;">
                    </div>
                    """, unsafe_allow_html=True)
                
                # Display deck name
                formatted_name = format_deck_name(deck_info['deck_name'])
                st.write(f"**{formatted_name}**")
                
                # Display basic deck info
                if 'tournament_id' in deck_info['deck_instance']:
                    st.caption(f"Tournament: {deck_info['deck_instance']['tournament_id']}")
                
                if 'player_name' in deck_info['deck_instance']:
                    st.caption(f"Player: {deck_info['deck_instance']['player_name']}")
                
                # Add button to analyze this specific deck archetype
                if st.button(f"Analyze {formatted_name}", 
                           key=f"analyze_{deck_info['deck_key']}_{i}", 
                           type="secondary"):
                    # Set this deck to be analyzed
                    st.session_state.deck_to_analyze = deck_info['deck_name']
                    st.rerun()
                
                # Show deck content preview (cards)
                try:
                    # Get analyzed results for this deck archetype if available
                    cache_key = f"full_deck_{deck_info['deck_name']}_{deck_info['set_name']}"
                    
                    if ('analyzed_deck_cache' in st.session_state and 
                        cache_key in st.session_state.analyzed_deck_cache):
                        
                        analyzed_data = st.session_state.analyzed_deck_cache[cache_key]
                        results = analyzed_data.get('results')
                        variant_df = analyzed_data.get('variant_df')
                        
                        if results is not None and not results.empty:
                            # Show simplified card list
                            st.write("**Cards:**")
                            
                            # Get top cards (limit to 10 for space)
                            top_cards = results.head(10)
                            
                            for _, card in top_cards.iterrows():
                                card_name = card.get('card_name', 'Unknown')
                                avg_count = card.get('avg_count', 0)
                                usage_rate = card.get('usage_rate', 0)
                                
                                st.write(f"• {card_name} - {avg_count:.1f} avg ({usage_rate:.0f}%)")
                        
                        else:
                            st.caption("No detailed analysis available")
                    
                    else:
                        # Show basic card info from deck instance if available
                        if 'cards' in deck_info['deck_instance']:
                            st.write("**Cards:**")
                            for card in deck_info['deck_instance']['cards'][:8]:  # Show first 8 cards
                                card_name = card.get('name', 'Unknown')
                                count = card.get('count', 1)
                                st.write(f"• {card_name} x{count}")
                            
                            if len(deck_info['deck_instance']['cards']) > 8:
                                st.caption(f"... and {len(deck_info['deck_instance']['cards']) - 8} more cards")
                        else:
                            st.caption("Card list not available")
                
                except Exception as e:
                    st.caption(f"Error displaying deck preview: {str(e)}")

def get_deck_record_summary(deck_key, deck_data):
    """
    Calculate aggregate record summary for a deck archetype
    
    Args:
        deck_key: The deck identifier
        deck_data: The collected deck data
        
    Returns:
        dict: Summary with total wins, losses, ties, and formatted record
    """
    total_wins = 0
    total_losses = 0 
    total_ties = 0
    deck_count = 0
    
    if 'decks' in deck_data:
        for deck_instance in deck_data['decks']:
            record = deck_instance.get('record', '')
            if record and record != 'No record':
                # Parse record string like "12 - 1 - 0"
                try:
                    parts = [part.strip() for part in record.split('-')]
                    if len(parts) >= 3:
                        wins = int(parts[0])
                        losses = int(parts[1])
                        ties = int(parts[2])
                        
                        total_wins += wins
                        total_losses += losses
                        total_ties += ties
                        deck_count += 1
                        
                except (ValueError, IndexError):
                    continue
    
    if deck_count == 0:
        return {
            'total_wins': 0,
            'total_losses': 0,
            'total_ties': 0,
            'deck_count': 0,
            'formatted_record': 'No records',
            'win_rate': 0.0
        }
    
    # Calculate win rate
    total_games = total_wins + total_losses + total_ties
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0.0
    
    return {
        'total_wins': total_wins,
        'total_losses': total_losses,
        'total_ties': total_ties,
        'deck_count': deck_count,
        'formatted_record': f"{total_wins} - {total_losses} - {total_ties}",
        'win_rate': win_rate
    }

def display_deck_gallery_by_archetype():
    """
    Alternative display showing one entry per deck archetype with aggregated records
    """
    
    # Check if we have collected decks data
    if 'collected_decks' not in st.session_state or not st.session_state.collected_decks:
        st.info("No deck data available. Please analyze some decks first.")
        return
    
    # Get summary for each deck archetype
    archetype_summaries = []
    
    for deck_key, deck_data in st.session_state.collected_decks.items():
        # Parse deck_key format: "deck_name_set_name"
        parts = deck_key.rsplit('_', 1)
        if len(parts) == 2:
            deck_name, set_name = parts
        else:
            deck_name = deck_key
            set_name = 'A3'
        
        # Get record summary
        record_summary = get_deck_record_summary(deck_key, deck_data)
        
        archetype_summaries.append({
            'deck_name': deck_name,
            'set_name': set_name,
            'deck_key': deck_key,
            'deck_data': deck_data,
            'record_summary': record_summary
        })
    
    if not archetype_summaries:
        st.info("No deck archetypes found.")
        return
    
    # Sort by total number of decks (most represented first)
    archetype_summaries.sort(key=lambda x: x['record_summary']['deck_count'], reverse=True)
    
    st.write(f"### Deck Gallery by Archetype ({len(archetype_summaries)} archetypes)")
    
    # Create three-column layout
    cols = st.columns(3)
    
    for i, archetype in enumerate(archetype_summaries):
        col_idx = i % 3
        
        with cols[col_idx]:
            record_summary = archetype['record_summary']
            
            # Format expander title with archetype name and aggregate record
            formatted_name = format_deck_name(archetype['deck_name'])
            expander_title = f"{formatted_name}. Record {record_summary['formatted_record']}"
            
            with st.expander(expander_title, expanded=False):
                # Display deck header image
                header_image = get_header_image_cached(
                    archetype['deck_name'], 
                    archetype['set_name']
                )
                
                if header_image:
                    st.markdown(f"""
                    <div style="width: 100%; margin-bottom: 12px;">
                        <img src="data:image/png;base64,{header_image}" 
                             style="width: 100%; height: auto; border-radius: 4px;">
                    </div>
                    """, unsafe_allow_html=True)
                
                # Display statistics
                st.write(f"**{formatted_name}**")
                st.write(f"**Decks collected:** {record_summary['deck_count']}")
                st.write(f"**Win Rate:** {record_summary['win_rate']:.1f}%")
                
                # Add button to analyze this deck archetype
                if st.button(f"Analyze {formatted_name}", 
                           key=f"analyze_arch_{archetype['deck_key']}_{i}", 
                           type="secondary"):
                    st.session_state.deck_to_analyze = archetype['deck_name']
                    st.rerun()
