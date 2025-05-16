# scraper.py
"""Web scraping functions for Limitless TCG"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
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
