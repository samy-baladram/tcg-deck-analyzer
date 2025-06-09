import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os

def get_recent_tournament_ids(max_fetch=20):
    """Get recent tournament IDs"""
    url = f"https://play.limitlesstcg.com/tournaments/completed?game=POCKET&format=all&platform=all&type=all&show={max_fetch}"
    
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    tournament_ids = []
    for link in soup.find_all('a', href=True):
        match = re.search(r'/tournament/([0-9a-f]{24})', link['href'])
        if match and match.group(1) not in tournament_ids:
            tournament_ids.append(match.group(1))
    
    return tournament_ids

def scrape_tournament_data(tournament_id):
    """Scrape tournament data"""
    print(f"Scraping tournament: {tournament_id}")
    
    # Get tournament metadata
    details_response = requests.get(f"https://play.limitlesstcg.com/tournament/{tournament_id}/details")
    details_soup = BeautifulSoup(details_response.text, 'html.parser')
    
    name = details_soup.find('title').get_text(strip=True).replace(' | Limitless', '')
    time_element = details_soup.find(attrs={'data-time': True})
    timestamp = int(time_element.get('data-time')) if time_element else None
    
    # Get player data
    standings_response = requests.get(f"https://play.limitlesstcg.com/tournament/{tournament_id}/standings")
    standings_soup = BeautifulSoup(standings_response.text, 'html.parser')
    
    table = standings_soup.find('table')
    if not table:
        print(f"No standings table found for {tournament_id}")
        return None
        
    rows = table.find_all('tr')[1:]  # Skip header
    
    players = []
    for i, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        
        # Extract archetype from metagame link in cell 7
        archetype = None
        if len(cells) > 7:
            archetype_link = cells[7].find('a')
            if archetype_link:
                match = re.search(r'/metagame/([^/?]+)', archetype_link.get('href', ''))
                if match:
                    archetype = match.group(1)
        
        players.append({
            'placement': i + 1,
            'player_name': cells[1].get_text(strip=True) if len(cells) > 1 else 'Unknown',
            'record': cells[4].get_text(strip=True) if len(cells) > 4 else 'Unknown',
            'archetype': archetype
        })
    
    return {
        'tournament_id': tournament_id,
        'name': name,
        'timestamp': timestamp,
        'player_count': len(players),
        'players': players
    }

def update_tournament_cache():
    """Main function to update tournament cache"""
    cache_dir = "tournament_cache"
    index_file = f"{cache_dir}/index.json"
    
    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)
    
    # Load existing cache
    if os.path.exists(index_file):
        with open(index_file, 'r') as f:
            index = json.load(f)
    else:
        index = {"tournaments": [], "last_updated": 0}
    
    print(f"Current cache has {len(index['tournaments'])} tournaments")
    
    # Get recent tournament IDs
    tournament_ids = get_recent_tournament_ids(30)
    print(f"Found {len(tournament_ids)} recent tournaments")
    
    new_count = 0
    target_count = 2  # Only process 2 tournaments for testing
    
    for tournament_id in tournament_ids:
        if new_count >= target_count:
            break
            
        if tournament_id not in index['tournaments']:
            try:
                data = scrape_tournament_data(tournament_id)
                if data and data['player_count'] >= 50:  # Only cache tournaments with 50+ players
                    # Save individual tournament file
                    tournament_file = f"{cache_dir}/{tournament_id}.json"
                    with open(tournament_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    # Update index
                    index['tournaments'].append(tournament_id)
                    new_count += 1
                    print(f"✅ Cached {tournament_id}: {data['name'][:50]}... ({data['player_count']} players)")
                else:
                    print(f"⏭️  Skipped {tournament_id}: too small or failed")
            except Exception as e:
                print(f"❌ Failed {tournament_id}: {e}")
            
            time.sleep(2)  # Be nice to the server
    
    # Update index with new timestamp
    index['last_updated'] = int(time.time())
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"Update complete: {new_count} new tournaments cached")

if __name__ == "__main__":
    update_tournament_cache()
