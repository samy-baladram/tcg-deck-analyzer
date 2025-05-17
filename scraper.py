# scraper.py
"""Web scraping functions for Limitless TCG"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import math
from config import BASE_URL

def get_deck_list():
    """Get all available decks with their share percentages"""
    url = f"{BASE_URL}/decks?game=pocket"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    decks = []
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 7:
            deck_link = cells[2].find('a', href=True)
            
            if deck_link and '/decks/' in deck_link['href'] and 'matchup' not in deck_link['href']:
                href = deck_link['href']
                deck_name = href.split('/decks/')[1].split('?')[0]
                
                # Extract set name
                set_name = 'A3'  # Default
                if 'set=' in href:
                    set_name = href.split('set=')[1].split('&')[0]
                
                # Extract share percentage
                share_text = cells[4].text.strip()
                share = float(share_text.replace('%', '')) if '%' in share_text else 0
                
                decks.append({
                    'deck_name': deck_name,
                    'set': set_name,
                    'share': share
                })
    
    return pd.DataFrame(decks).sort_values('share', ascending=False)

def get_popular_decks_with_performance(share_threshold=0.6):
    """Get decks that exceed a minimum share percentage with performance metrics."""
    url = f"{BASE_URL}/decks?game=pocket"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    decks = []
    rank = 1
    
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 6:
            continue
            
        deck_link = cells[2].find('a', href=True)
        if not deck_link or '/decks/' not in deck_link['href'] or 'matchup' in deck_link['href']:
            continue
            
        # Extract share percentage
        share_text = cells[4].text.strip() if len(cells) > 4 else '0%'
        try:
            share = float(share_text.replace('%', '')) if '%' in share_text else 0
        except ValueError:
            share = 0
        
        # Skip decks below the threshold
        if share < share_threshold:
            continue
            
        href = deck_link['href']
        deck_name = href.split('/decks/')[1].split('?')[0]
        displayed_name = deck_link.text.strip()
        
        # Extract set name
        set_name = 'A3'  # Default
        if 'set=' in href:
            set_name = href.split('set=')[1].split('&')[0]
        
        decks.append({
            'rank': rank,
            'deck_name': deck_name,
            'displayed_name': displayed_name,
            'share': share,
            'set': set_name
        })
        
        rank += 1
    
    return pd.DataFrame(decks)

def get_deck_urls(deck_name, set_name="A3"):
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

def extract_cards(url):
    """Extract cards from a single decklist"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    cards = []
    
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
    
    return cards

def get_all_recent_tournaments():
    """Get IDs of all tournaments completed recently."""
    tournament_id_set = set()
    tournament_ids = []
    
    url = f"{BASE_URL}/tournaments"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for tournament links in anchor tags
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/tournament/' in href:
                match = re.search(r'/tournament/([a-zA-Z0-9]+)', href)
                if match and match.group(1) not in tournament_id_set:
                    tournament_id = match.group(1)
                    tournament_id_set.add(tournament_id)
                    tournament_ids.append(tournament_id)
        
    except Exception as e:
        print(f"Error fetching tournaments: {e}")
    
    return tournament_ids

def get_deck_performance(deck_name, set_code="A3"):
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
    # Get popular decks above threshold
    popular_decks = get_popular_decks_with_performance(share_threshold=share_threshold)
    
    # Get recent tournament IDs
    recent_tournament_ids = set(get_all_recent_tournaments())
    
    # Prepare results dataframe
    results = []
    
    # Process each deck
    for _, deck in popular_decks.iterrows():
        deck_name = deck['deck_name']
        displayed_name = deck['displayed_name']
        share = deck['share']
        set_name = deck['set']
        
        # Get performance data for this deck
        performance = get_deck_performance(deck_name, set_name)
        
        # Filter for only recent tournaments
        recent_performance = performance[performance['tournament_id'].isin(recent_tournament_ids)]
        
        # Skip if no recent data
        if recent_performance.empty:
            continue
        
        # Calculate totals
        total_wins = recent_performance['wins'].sum()
        total_losses = recent_performance['losses'].sum()
        total_ties = recent_performance['ties'].sum()
        tournaments_played = len(recent_performance['tournament_id'].unique())
        
        # Calculate total games
        total_games = total_wins + total_losses + total_ties
        
        if total_games > 0:
            # Calculate Power Index
            power_index = ((total_wins + (0.75*total_ties) - total_losses) / math.sqrt(total_games))
            
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

    # Convert to DataFrame and sort by Power Index
    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values('power_index', ascending=False).reset_index(drop=True)

    return results_df
