# deck_gallery.py
"""Functions for displaying all fetched decks in the Deck Gallery tab"""

import streamlit as st
import json
import os
from ui_helpers import get_energy_types_for_deck
from card_renderer import render_sidebar_deck
import cache_manager

def get_deck_record(tournament_id, player_id):
    """
    Get win-lose-tie record for a deck by matching tournament and player
    Returns tuple (wins, losses, ties) or (0, 0, 0) if not found
    """
    try:
        # DEBUG: Print what we're looking for
        print(f"DEBUG: Looking for tournament {tournament_id}, player {player_id}")
        
        # First, find the correct date path for this tournament
        tournament_file_path = find_tournament_file_path(tournament_id)
        
        print(f"DEBUG: Found file path: {tournament_file_path}")
        
        if tournament_file_path and os.path.exists(tournament_file_path):
            with open(tournament_file_path, 'r') as f:
                tournament_data = json.load(f)
            
            # DEBUG: Show tournament info
            tournament_name = tournament_data.get('name', 'Unknown')
            player_count = len(tournament_data.get('players', []))
            print(f"DEBUG: Tournament '{tournament_name}' has {player_count} players")
            
            # Search for the player in the players array
            if 'players' in tournament_data:
                player_names = [p.get('player_name', '') for p in tournament_data['players']]
                print(f"DEBUG: Player names in tournament: {player_names[:5]}...")  # Show first 5
                
                for player in tournament_data['players']:
                    # The player_id might actually be the player_name
                    if str(player.get('player_name', '')) == str(player_id):
                        record_str = player.get('record', '0 - 0 - 0')
                        print(f"DEBUG: Found player {player_id} with record: {record_str}")
                        
                        # Parse the record string "7 - 3 - 0" format
                        wins, losses, ties = parse_record_string(record_str)
                        return (wins, losses, ties)
                
                print(f"DEBUG: Player {player_id} not found in tournament {tournament_id}")
                        
        else:
            print(f"DEBUG: Tournament file not found for tournament {tournament_id}")
        
        # Fallback: Return default record if not found
        return (0, 0, 0)
        
    except Exception as e:
        print(f"ERROR getting deck record for tournament {tournament_id}, player {player_id}: {e}")
        return (0, 0, 0)

def find_tournament_file_path(tournament_id):
    """
    Find the file path for a tournament by looking through the index.json
    Returns the full path to the tournament file or None if not found
    """
    try:
        index_path = "tournament_cache/index.json"
        
        print(f"DEBUG: Looking for index at {index_path}")
        
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                index_data = json.load(f)
            
            print(f"DEBUG: Index loaded, total tournaments: {index_data.get('total_tournaments', 0)}")
            
            # Search through tournaments_by_path to find the date path
            tournaments_by_path = index_data.get('tournaments_by_path', {})
            
            for date_path, tournament_list in tournaments_by_path.items():
                if tournament_id in tournament_list:
                    # Found the tournament in this date path
                    file_path = f"tournament_cache/{date_path}/{tournament_id}.json"
                    print(f"DEBUG: Found tournament {tournament_id} in {date_path}")
                    return file_path
            
            print(f"DEBUG: Tournament {tournament_id} not found in tournaments_by_path")
            
            # If not found in tournaments_by_path, try the old direct path
            direct_path = f"tournament_cache/{tournament_id}.json"
            if os.path.exists(direct_path):
                print(f"DEBUG: Found tournament at direct path: {direct_path}")
                return direct_path
            else:
                print(f"DEBUG: Direct path also doesn't exist: {direct_path}")
                
        else:
            print(f"DEBUG: Index file not found at {index_path}")
        
        return None
        
    except Exception as e:
        print(f"ERROR finding tournament file path for {tournament_id}: {e}")
        return None

def parse_record_string(record_str):
    """
    Parse record string like "7 - 3 - 0" or "1 - 3 - 0drop"
    Returns tuple (wins, losses, ties)
    """
    try:
        # Remove any "drop" text and clean up
        cleaned_record = record_str.replace('drop', '').strip()
        
        # Split by " - " and extract numbers
        parts = cleaned_record.split(' - ')
        
        if len(parts) >= 2:
            wins = int(parts[0].strip()) if parts[0].strip().isdigit() else 0
            losses = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
            ties = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip().isdigit() else 0
            return (wins, losses, ties)
        else:
            # Fallback parsing for different formats
            import re
            numbers = re.findall(r'\d+', cleaned_record)
            if len(numbers) >= 2:
                wins = int(numbers[0])
                losses = int(numbers[1])
                ties = int(numbers[2]) if len(numbers) > 2 else 0
                return (wins, losses, ties)
                
    except Exception as e:
        print(f"Error parsing record string '{record_str}': {e}")
    
    return (0, 0, 0)

def display_single_deck_expander(deck_data, deck_number, energy_types, is_typical):
    """
    Display a single deck in an expander format
    Similar to the existing expander in display_deck_template_tab
    """
    # Get record for this deck
    tournament_id = deck_data.get('tournament_id', '')
    player_id = deck_data.get('player_id', '')
    wins, losses, ties = get_deck_record(tournament_id, player_id)
    
    # Format record string
    record_str = f"{wins}-{losses}-{ties}"
    
    # Create expander title
    expander_title = f"Deck {deck_number}. Record {record_str}"
    
    # Create the expander
    with st.expander(expander_title, expanded=False):
        # DEBUG: Show tournament and player info
        st.write("**DEBUG INFO:**")
        st.write(f"Tournament ID: `{tournament_id}`")
        st.write(f"Player Name: `{player_id}`")
        st.write(f"Record: `{record_str}`")
        st.divider()
        
        # Display energy types if available
        if energy_types:
            from card_renderer import render_energy_icons
            energy_html = render_energy_icons(energy_types, is_typical)
            st.markdown(energy_html, unsafe_allow_html=True)
        
        # Get deck cards
        cards = deck_data.get('cards', [])
        
        if cards:
            # Separate Pokemon and Trainer cards
            pokemon_cards = []
            trainer_cards = []
            
            for card in cards:
                if card.get('type', '').lower() == 'pokemon':
                    pokemon_cards.append({
                        'name': card.get('card_name', ''),
                        'set': card.get('set', ''),
                        'num': card.get('num', ''),
                        'amount': card.get('amount', 1)
                    })
                else:
                    trainer_cards.append({
                        'name': card.get('card_name', ''),
                        'set': card.get('set', ''),
                        'num': card.get('num', ''),
                        'amount': card.get('amount', 1)
                    })
            
            # Render the deck using CardGrid
            deck_html = render_sidebar_deck(
                pokemon_cards, 
                trainer_cards,
                card_width=65
            )
            st.markdown(deck_html, unsafe_allow_html=True)
        else:
            st.info("No deck data available")

def display_deck_gallery_tab():
    """
    Display the Deck Gallery tab with all collected decks in 3 columns
    """
    st.write("##### Deck Gallery - All Collected Decks")
    
    # Get current deck info
    if 'analyze' not in st.session_state:
        st.info("Select a deck to view the gallery")
        return
    
    deck_name = st.session_state.analyze.get('deck_name', '')
    set_name = st.session_state.analyze.get('set_name', 'A3')
    
    # Get energy types for the current archetype
    energy_types, is_typical = get_energy_types_for_deck(deck_name)
    
    # Get collected decks from session state
    deck_key = f"{deck_name}_{set_name}"
    
    if 'collected_decks' not in st.session_state or deck_key not in st.session_state.collected_decks:
        st.info("No collected decks found for this archetype")
        return
    
    collected_data = st.session_state.collected_decks[deck_key]
    all_decks = collected_data.get('decks', [])
    
    if not all_decks:
        st.info("No deck data available")
        return
    
    # Create 3 columns for layout
    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]
    
    # For now, display up to 20 decks as requested
    max_decks = min(20, len(all_decks))
    
    # Display decks in columns
    for i in range(max_decks):
        deck = all_decks[i]
        column_index = i % 3  # Distribute across 3 columns
        
        with columns[column_index]:
            display_single_deck_expander(
                deck, 
                deck.get('deck_num', i + 1), 
                energy_types, 
                is_typical
            )
    
    # Display summary info
    st.divider()
    st.caption(f"Showing {max_decks} of {len(all_decks)} collected decks for {deck_name}")

# Alternative function for testing/development
def display_deck_gallery_tab_simple():
    """
    Simplified version for testing - just copies the expander code 20 times
    This is what the user specifically requested for now
    """
    st.write("##### Deck Gallery - All Collected Decks")
    
    # Get current deck info
    if 'analyze' not in st.session_state:
        st.info("Select a deck to view the gallery")
        return
    
    deck_name = st.session_state.analyze.get('deck_name', '')
    set_name = st.session_state.analyze.get('set_name', 'A3')
    
    # Get energy types for the current archetype
    energy_types, is_typical = get_energy_types_for_deck(deck_name)
    
    # Create 3 columns for layout
    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]
    
    # Create 20 expanders as requested
    for i in range(20):
        column_index = i % 3  # Distribute across 3 columns
        deck_number = i + 1
        
        # Placeholder record for now
        record_str = f"{2}-{1}-{0}"  # Placeholder win-lose-tie
        expander_title = f"Deck {deck_number}. Record {record_str}"
        
        with columns[column_index]:
            with st.expander(expander_title, expanded=False):
                # Display energy types if available
                if energy_types:
                    from card_renderer import render_energy_icons
                    energy_html = render_energy_icons(energy_types, is_typical)
                    st.markdown(energy_html, unsafe_allow_html=True)
                
                # Get sample deck data (using the same logic as the original)
                sample_deck = cache_manager.get_or_load_sample_deck(deck_name, set_name)
                
                # Render the sample deck
                if sample_deck:
                    deck_html = render_sidebar_deck(
                        sample_deck['pokemon_cards'], 
                        sample_deck['trainer_cards'],
                        card_width=65
                    )
                    st.markdown(deck_html, unsafe_allow_html=True)
                else:
                    st.info(f"Sample deck {deck_number} - No data available")
    
    # Display summary info
    st.divider()
    #st.caption(f"Showing 20 sample decks for {deck_name} archetype")
    st.caption(f"Showing best-finishes sample decks for {deck_name} archetype")
