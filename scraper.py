# scraper.py
"""Web scraping functions for Limitless TCG"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import math
import streamlit as st
from config import BASE_URL, TOURNAMENT_COUNT, MIN_META_SHARE, MIN_WIN_RATE, CURRENT_SET


def get_popular_decks_with_performance(share_threshold=0.0):
    """Simple replacement using local data"""
    try:
        from meta_table import MetaTableBuilder
        builder = MetaTableBuilder()
        meta_df = builder.build_complete_meta_table(limit=50)
        
        # Filter by threshold and convert to expected format
        filtered_df = meta_df[meta_df['share_7d'] >= share_threshold].copy()
        
        result_df = pd.DataFrame({
            'deck_name': filtered_df.index,
            'displayed_name': filtered_df['formatted_deck_name'],
            'share': filtered_df['share_7d'],
            'set': 'A3a'
        })
        
        return result_df
        
    except Exception as e:
        print(f"Error getting popular decks from local data: {e}")
        return pd.DataFrame()

# In scraper.py, update get_all_recent_tournaments function
def get_all_recent_tournaments():
    """Get IDs of all tournaments completed recently."""
    tournament_id_set = set()
    tournament_ids = []
    
    # Get current year and month
    from datetime import datetime
    current_date = datetime.now()
    current_year_month = current_date.strftime("%Y-%m")  # Format: YYYY-MM
    
    # Build URL with current year and month
    #url = f"https://play.limitlesstcg.com/tournaments/completed?game=POCKET&format=STANDARD&platform=all&type=all&time={current_year_month}&show={TOURNAMENT_COUNT}"
    url = f"https://play.limitlesstcg.com/tournaments/completed?game=POCKET&format=STANDARD&platform=all&type=all&show={TOURNAMENT_COUNT}"
    
    try:
        print(f"DEBUG: Fetching tournaments from: {url}")  # Add debug
        response = requests.get(url)
        print(f"DEBUG: Response status: {response.status_code}")  # Add debug
        
        if response.status_code != 200:
            print(f"DEBUG: Bad response status, trying previous month...")
            # Try previous month as fallback
            prev_month = current_date.replace(day=1) - timedelta(days=1)
            prev_year_month = prev_month.strftime("%Y-%m")
            url = f"https://play.limitlesstcg.com/tournaments/completed?game=POCKET&format=STANDARD&platform=all&type=all&show={TOURNAMENT_COUNT}"
            #url = f"https://play.limitlesstcg.com/tournaments/completed?game=POCKET&format=STANDARD&platform=all&type=all&time={prev_year_month}&show={TOURNAMENT_COUNT}"
            response = requests.get(url)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for tournament links in anchor tags
        links_found = 0
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/tournament/' in href:
                links_found += 1
                match = re.search(r'/tournament/([a-zA-Z0-9-_]+)', href)
                if match and match.group(1) not in tournament_id_set:
                    tournament_slug = match.group(1)
                    
                    # Check if it's a standard tournament ID format (24 character hexadecimal)
                    is_standard_id = bool(re.match(r'^[0-9a-f]{24}$', tournament_slug))
                    
                    if is_standard_id:
                        tournament_id = tournament_slug
                    else:
                        # If not standard format, scrape the tournament page to find the actual ID
                        tournament_id = get_tournament_id_from_page(tournament_slug)
                    
                    tournament_id = tournament_slug
                    
                    if tournament_id and tournament_id not in tournament_id_set:
                        tournament_id_set.add(tournament_id)
                        tournament_ids.append(tournament_id)
        
        print(f"DEBUG: Found {links_found} tournament links, extracted {len(tournament_ids)} valid IDs")  # Add debug
        
    except Exception as e:
        print(f"Error fetching tournaments: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
    
    return tournament_ids

def get_tournament_id_from_page(tournament_slug):
    """Extract actual tournament ID from the tournament page JavaScript."""
    try:
        # Build the URL for the tournament standings page
        url = f"https://play.limitlesstcg.com/tournament/{tournament_slug}/standings"
        
        # Fetch the page
        response = requests.get(url)
        
        # Extract tournament ID from JavaScript variable
        # Look for pattern: var tournamentId = 'XXXX'
        id_match = re.search(r"var\s+tournamentId\s*=\s*['\"]([0-9a-f]{24})['\"]", response.text)
        
        if id_match:
            return id_match.group(1)
        
        # Alternative approach: Look for tournament ID in other potential locations
        # For example, in JSON data or other script tags
        alt_match = re.search(r'"tournamentId":\s*"([0-9a-f]{24})"', response.text)
        if alt_match:
            return alt_match.group(1)
            
        # If ID not found, return None
        return None
        
    except Exception as e:
        print(f"Error fetching tournament page for {tournament_slug}: {e}")
        return None

def extract_cards(url):
    """Extract cards and energy types from a single decklist"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    cards = []
    energy_types = []
    
    # Extract energy types from image elements
    img_elements = soup.find_all('img')
    for img in img_elements:
        src = img.get('src', '').lower()
        
        # Check for energy type patterns in image URLs
        if 'grass.png' in src:
            energy_types.append('grass')
        elif 'fire.png' in src:
            energy_types.append('fire')
        elif 'water.png' in src:
            energy_types.append('water')
        elif 'lightning.png' in src:
            energy_types.append('lightning')
        elif 'psychic.png' in src:
            energy_types.append('psychic')
        elif 'fighting.png' in src:
            energy_types.append('fighting')
        elif 'darkness.png' in src:
            energy_types.append('darkness')
        elif 'metal.png' in src:
            energy_types.append('metal')
        elif 'colorless.png' in src:
            energy_types.append('colorless')
    
    # Remove duplicates
    energy_types = list(set(energy_types))
    
    # Find sections containing cards
    for div in soup.find_all('div', class_='heading'):
        section_text = div.text.strip()
        
        # Check if section is Pokémon or Trainer
        if 'Pokémon' in section_text or 'Trainer' in section_text:
            section_type = 'Pokemon' if 'Pokémon' in section_text else 'Trainer'
            
            # Process each card entry in this section
            for p in div.parent.find_all('p'):
                card_text = p.get_text(strip=True)
                if not card_text:
                    continue
                
                # Extract card quantity and name
                parts = card_text.split(' ', 1)
                if len(parts) != 2:
                    continue
                
                try:
                    # Parse amount and clean name
                    amount = int(parts[0])
                    full_name = parts[1]
                    name = full_name.split(' (')[0] if ' (' in full_name else full_name
                    
                    # Extract set code and number from link
                    set_code = num = ""
                    card_link = p.find('a', href=True)
                    
                    if card_link and '/cards/' in card_link['href']:
                        url_parts = card_link['href'].rstrip('/').split('/')
                        if len(url_parts) >= 2:
                            set_code = url_parts[-2]
                            num = url_parts[-1]
                    
                    # Add card to result list
                    cards.append({
                        'type': section_type,
                        'card_name': name,
                        'amount': amount,
                        'set': set_code,
                        'num': num
                    })
                except (ValueError, IndexError):
                    # Skip entries that can't be properly parsed
                    continue
    
    return cards, energy_types

# New functions for player-tournament relationship
def get_player_tournament_pairs(deck_name, set_name=CURRENT_SET):
    """
    Extract player_id and tournament_id pairs for a deck archetype
    
    Returns:
        List of dicts with:
        - player_id: Player identifier
        - tournament_id: Tournament identifier
        - url: Full URL to the decklist
    """
    pairs = []
    deck_url = f"{BASE_URL}/decks/{deck_name}/?game=POCKET&format=standard&set={set_name}"
    response = requests.get(deck_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    table = soup.find('table', class_='striped')
    if table:
        for row in table.find_all('tr')[1:]:  # Skip header
            last_cell = row.find_all('td')[-1]
            link = last_cell.find('a')
            if link and 'href' in link.attrs:
                url = f"{BASE_URL}{link['href']}"
                # Extract player_id and tournament_id from URL
                match = re.search(r'/tournament/([^/]+)/player/([^/]+)', link['href'])
                if match:
                    tournament_id = match.group(1)
                    player_id = match.group(2)
                    pairs.append({
                        'tournament_id': tournament_id,
                        'player_id': player_id,
                        'url': url
                    })
    return pairs

def get_deck_by_player_tournament(tournament_id, player_id):
    """
    Get deck using player_id and tournament_id directly
    
    Returns:
        Tuple of (cards, energy_types)
    """
    url = f"{BASE_URL}/tournament/{tournament_id}/player/{player_id}/decklist"
    return extract_cards(url)

# Tournament tracking functions
def get_new_tournament_ids(previous_ids):
    """
    Compare current tournament IDs against previous ones to find new tournaments
    
    Args:
        previous_ids: Set or list of previously known tournament IDs
        
    Returns:
        List of new tournament IDs not in previous_ids
    """
    current_ids = get_all_recent_tournaments()
    # Convert previous_ids to set for efficient lookup
    prev_id_set = set(previous_ids)
    # Find new IDs
    new_ids = [id for id in current_ids if id not in prev_id_set]
    return new_ids

# For the get_affected_decks function
def get_affected_decks(new_tournament_ids, player_tournament_mapping):
    """
    Find decks affected by new tournaments
    
    Args:
        new_tournament_ids: List of new tournament IDs
        player_tournament_mapping: Dict mapping (player_id, tournament_id) to deck_name
        
    Returns:
        Set of deck names affected by the new tournaments
    """
    affected_decks = set()
    new_id_set = set(new_tournament_ids)
    
    # Add comment explaining the expected key format
    # player_tournament_mapping keys should be formatted as "player_id:tournament_id"
    for key, deck_name in player_tournament_mapping.items():
        parts = key.split(':')
        if len(parts) == 2:
            player_id, tournament_id = parts
            if tournament_id in new_id_set:
                affected_decks.add(deck_name)
    
    return affected_decks

# Helper function to create consistent mapping keys
def create_mapping_key(player_id, tournament_id):
    """Create a consistent key for player-tournament mappings"""
    return f"{player_id}:{tournament_id}"


## -- DEPRECATED -- ##

def get_deck_urls(deck_name, set_name=CURRENT_SET):
    """Get URLs for all decklists of a specific archetype"""
    url = f"{BASE_URL}/decks/{deck_name}/?game=POCKET&format=standard&set={set_name}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    urls = []
    table = soup.find('table', class_='striped')
    
    if table:
        for row in table.find_all('tr')[1:]:  # Skip header
            last_cell = row.find_all('td')[-1]
            link = last_cell.find('a')
            if link and 'href' in link.attrs:
                urls.append(f"{BASE_URL}{link['href']}")
    
    return urls

def get_sample_deck_for_archetype(deck_name, set_name=CURRENT_SET):
    """Get a sample deck list for a specific archetype from the first available tournament result."""
    # Get the URLs for this deck archetype
    urls = get_deck_urls(deck_name, set_name)
    
    # If there are no decks available, return empty lists
    if not urls:
        return [], [], []
    
    # Extract cards from the first decklist (most recent/representative)
    cards, energy_types = extract_cards(urls[0])
    
    # Separate Pokemon and Trainer cards
    pokemon_cards = [card for card in cards if card['type'] == 'Pokemon']
    trainer_cards = [card for card in cards if card['type'] == 'Trainer']
    
    return pokemon_cards, trainer_cards, energy_types
