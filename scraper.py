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
    """Get all decks with their share percentages and win rates above threshold"""
    url = f"{BASE_URL}/decks?game=pocket"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    decks = []
    
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 6:
            continue
            
        deck_link = cells[2].find('a', href=True)
        if not deck_link or '/decks/' not in deck_link['href'] or 'matchup' in deck_link['href']:
            continue
            
        href = deck_link['href']
        deck_name = href.split('/decks/')[1].split('?')[0]
        displayed_name = deck_link.text.strip()
        
        # Extract set name
        set_name = CURRENT_SET  # Default
        if 'set=' in href:
            set_name = href.split('set=')[1].split('&')[0]
        
        # Extract share percentage (column 4)
        share_text = cells[4].text.strip() if len(cells) > 4 else '0%'
        share = float(share_text.replace('%', '')) if '%' in share_text and share_text.replace('%', '').replace('.', '').isdigit() else 0
        
        # Extract win rate from multiple columns
        win_rate = 0
        for col_idx in [3, 5, 6, 7]:
            if col_idx < len(cells):
                cell_text = cells[col_idx].text.strip()
                if '%' in cell_text and cell_text != share_text:
                    potential_win_rate = float(cell_text.replace('%', '')) if cell_text.replace('%', '').replace('.', '').isdigit() else 0
                    if 0 <= potential_win_rate <= 100:
                        win_rate = potential_win_rate
                        break
        
        decks.append({
            'deck_name': deck_name,
            'displayed_name': displayed_name,
            'set': set_name,
            'share': share,
            'win_rate': win_rate
        })
    
    # Create DataFrame
    df = pd.DataFrame(decks)
    
    # Apply filtering
    df = df[(df['share'] >= share_threshold) & (df['win_rate'] >= MIN_WIN_RATE)]

    # Add rank column after sorting (1-based index)
    df.insert(0, 'rank', range(1, len(df) + 1))
    
    return df.sort_values('win_rate', ascending=False)

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

def get_deck_performance_data():
    """
    Get raw performance data for all popular decks
    Returns raw data for analysis in analyzer.py
    """
    # Get popular decks above threshold
    popular_decks = get_popular_decks_with_performance(share_threshold=MIN_META_SHARE)
    
    # Get recent tournament IDs
    recent_tournament_ids = set(get_all_recent_tournaments())
    
    # Get performance data for each deck
    deck_data = []
    for _, deck in popular_decks.iterrows():
        deck_name = deck['deck_name']
        displayed_name = deck['displayed_name']
        share = deck['share']
        set_name = deck['set']
        
        # Get performance data
        performance = get_deck_performance(deck_name, set_name)
        
        # Filter for only recent tournaments
        recent_performance = performance[performance['tournament_id'].isin(recent_tournament_ids)]
        
        # Skip if no recent data
        if recent_performance.empty:
           continue
            
        deck_data.append({
            'deck_name': deck_name,
            'displayed_name': displayed_name,
            'share': share,
            'set': set_name,
            'performance': recent_performance  # Raw performance data
        })
    
    return deck_data


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


## -- TO BE MOVED -- ##

def get_deck_performance(deck_name, set_code=CURRENT_SET):
    """Get performance data for a specific deck."""
    url = f"{BASE_URL}/decks/{deck_name}?game=POCKET&format=standard&set={set_code}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    results = []
    
    # Find the best finishes table
    table = None
    for t in soup.find_all('table'):
        if 'Score' in t.text and 'Player' in t.text:
            table = t
            break
    
    if not table:
        return pd.DataFrame()
        
    # Find header row and score column index
    header_row = table.find('tr')
    if not header_row:
        return pd.DataFrame()
        
    headers = [th.text.strip() for th in header_row.find_all(['th'])]
    score_col_index = headers.index('Score') if 'Score' in headers else 3
    
    # Process each data row
    for row in table.find_all('tr')[1:]:  # Skip header
        cells = row.find_all(['td'])
        if len(cells) <= score_col_index:
            continue
            
        # Extract tournament ID
        tournament_cell = cells[1]
        tournament_link = tournament_cell.find('a', href=True)
        
        if not tournament_link or 'href' not in tournament_link.attrs:
            continue
            
        tournament_href = tournament_link['href']
        match = re.search(r'/tournament/([^/]+)', tournament_href)
        if not match:
            continue
            
        tournament_id = match.group(1)
        
        # Extract score components
        score_text = cells[score_col_index].text.strip()
        try:
            score_parts = [part.strip() for part in score_text.split('-')]
            wins = int(score_parts[0]) if len(score_parts) > 0 and score_parts[0].isdigit() else 0
            losses = int(score_parts[1]) if len(score_parts) > 1 and score_parts[1].isdigit() else 0
            ties = int(score_parts[2]) if len(score_parts) > 2 and score_parts[2].isdigit() else 0
        except:
            wins, losses, ties = 0, 0, 0
        
        results.append({
            'tournament_id': tournament_id,
            'wins': wins,
            'losses': losses,
            'ties': ties
        })
    
    return pd.DataFrame(results)

def analyze_recent_performance(share_threshold=0.6):
    """Analyze the recent performance of popular decks."""
    print(f"DEBUG: Starting analyze_recent_performance with threshold {share_threshold}")
    
    try:
        # Check if streamlit is available
        print("DEBUG: Checking streamlit import...")
        import streamlit as st
        print("DEBUG: Streamlit imported successfully")
        
        # Get popular decks above threshold
        print("DEBUG: Getting popular decks...")
        popular_decks = get_popular_decks_with_performance(share_threshold=share_threshold)
        print(f"DEBUG: Found {len(popular_decks)} popular decks")
        
        # Get recent tournament IDs
        print("DEBUG: Getting recent tournament IDs...")
        recent_tournament_ids = set(get_all_recent_tournaments())
        print(f"DEBUG: Found {len(recent_tournament_ids)} recent tournaments")
        
        # Prepare results dataframe
        results = []
        
        # Process each deck
        print("DEBUG: Processing each deck...")
        for idx, (_, deck) in enumerate(popular_decks.iterrows()):
            print(f"DEBUG: Processing deck {idx+1}/{len(popular_decks)}: {deck['deck_name']}")
            
            deck_name = deck['deck_name']
            displayed_name = deck['displayed_name']
            share = deck['share']
            set_name = deck['set']
            
            # Get performance data for this deck
            print(f"DEBUG: Getting performance data for {deck_name}...")
            performance = get_deck_performance(deck_name, set_name)
            print(f"DEBUG: Found {len(performance)} performance records for {deck_name}")
            
            # Filter for only recent tournaments
            recent_performance = performance[performance['tournament_id'].isin(recent_tournament_ids)]
            print(f"DEBUG: {len(recent_performance)} recent performance records for {deck_name}")
            
            # Skip if no recent data
            if recent_performance.empty:
                print(f"DEBUG: No recent data for {deck_name}, skipping")
                continue
            
            # Calculate totals
            total_wins = recent_performance['wins'].sum()
            total_losses = recent_performance['losses'].sum()
            total_ties = recent_performance['ties'].sum()
            tournaments_played = len(recent_performance['tournament_id'])
            
            print(f"DEBUG: {deck_name} - Wins: {total_wins}, Losses: {total_losses}, Ties: {total_ties}")
            
            # Calculate total games
            total_games = total_wins + total_losses + total_ties
            
            if total_games > 0:
                print(f"DEBUG: Calculating power index for {deck_name} with {total_games} total games")
                
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
                
                # Scale to make more intuitive
                power_index = (wilson_score - 0.5) * 10
                
                print(f"DEBUG: {deck_name} power index: {power_index:.2f}")
                
                results.append({
                    'deck_name': deck_name,
                    'displayed_name': displayed_name,
                    'share': share,
                    'set': set_name,
                    'total_wins': total_wins,
                    'total_losses': total_losses,
                    'total_ties': total_ties,
                    'tournaments_played': tournaments_played,
                    'power_index': power_index
                })
            else:
                print(f"DEBUG: {deck_name} has 0 total games, skipping")

        print(f"DEBUG: Created {len(results)} deck results")
        
        # Convert to DataFrame and sort by Power Index
        results_df = pd.DataFrame(results)
        if not results_df.empty:
            print("DEBUG: Sorting results by power index...")
            results_df = results_df.sort_values('power_index', ascending=False).reset_index(drop=True)
            print(f"DEBUG: Top deck: {results_df.iloc[0]['deck_name']} with power index {results_df.iloc[0]['power_index']:.2f}")
        else:
            print("DEBUG: Results DataFrame is empty!")

        print(f"DEBUG: Returning DataFrame with {len(results_df)} rows")
        return results_df
        
    except Exception as e:
        print(f"DEBUG: Exception in analyze_recent_performance: {e}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        raise e
    
# Add this temporary debugging function to scraper.py
def debug_tournament_data():
    """Debug function to check tournament data loading"""
    print("=== DEBUGGING TOURNAMENT DATA ===")
    
    # Check if we can fetch tournaments
    tournament_ids = get_all_recent_tournaments()
    print(f"Found {len(tournament_ids)} tournament IDs: {tournament_ids[:5]}...")
    
    # Check if we can get performance data
    try:
        performance_data = get_deck_performance_data()
        print(f"Found {len(performance_data)} deck performance entries")
        for i, deck in enumerate(performance_data[:3]):
            print(f"  Deck {i+1}: {deck['deck_name']} (set: {deck['set']})")
    except Exception as e:
        print(f"Error getting performance data: {e}")
    
    # Check popular decks
    try:
        popular_decks = get_popular_decks_with_performance(0.0)
        print(f"Found {len(popular_decks)} popular decks")
        if not popular_decks.empty:
            print(f"  First deck: {popular_decks.iloc[0]['deck_name']}")
            print(f"  Sets found: {popular_decks['set'].unique()}")
    except Exception as e:
        print(f"Error getting popular decks: {e}")

