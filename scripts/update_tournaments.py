import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
from datetime import datetime

def get_recent_tournament_ids(max_fetch=20):
    """Get recent tournament IDs - limited to 20"""
    url = f"https://play.limitlesstcg.com/tournaments/completed?game=POCKET&format=all&platform=all&type=all&show={max_fetch}"
    
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    tournament_ids = []
    for link in soup.find_all('a', href=True):
        match = re.search(r'/tournament/([0-9a-f]{24})', link['href'])
        if match and match.group(1) not in tournament_ids:
            tournament_ids.append(match.group(1))
            if len(tournament_ids) >= max_fetch:
                break
    
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

def get_date_folder_path(timestamp):
    """Convert timestamp to YYYY/MM/DD folder path"""
    if not timestamp:
        # Fallback to current date if no timestamp
        date = datetime.now()
    else:
        date = datetime.fromtimestamp(timestamp / 1000)
    
    return f"{date.year}/{date.month:02d}/{date.day:02d}"

def update_tournament_cache():
    """Main function to update tournament cache with organized folders"""
    cache_dir = "tournament_cache"
    index_file = f"{cache_dir}/index.json"
    
    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)
    
    # Load existing cache index
    if os.path.exists(index_file):
        with open(index_file, 'r') as f:
            index = json.load(f)
    else:
        index = {
            "tournaments": [],
            "last_updated": 0,
            "total_tournaments": 0,
            "tournaments_by_path": {}
        }
    
    print(f"Current cache has {len(index['tournaments'])} tournaments")
    
    # Get recent tournament IDs (max 20)
    tournament_ids = get_recent_tournament_ids(20)
    print(f"Found {len(tournament_ids)} recent tournaments")
    
    # Find NEW tournaments (not in cache)
    new_tournament_ids = [tid for tid in tournament_ids if tid not in index['tournaments']]
    print(f"New tournaments to scrape: {len(new_tournament_ids)}")
    
    if not new_tournament_ids:
        print("No new tournaments found - nothing to scrape")
        return
    
    new_count = 0
    
    # Process only NEW tournaments - NO FILTERING, GET ALL TOURNAMENTS
    for tournament_id in new_tournament_ids:
        try:
            data = scrape_tournament_data(tournament_id)
            if data:  # Just check if data exists, no player count filter
                
                # Get date folder path from tournament timestamp
                date_path = get_date_folder_path(data['timestamp'])
                full_folder_path = f"{cache_dir}/{date_path}"
                
                # Create date folder if it doesn't exist
                os.makedirs(full_folder_path, exist_ok=True)
                
                # Save tournament file in date folder
                tournament_file = f"{full_folder_path}/{tournament_id}.json"
                with open(tournament_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Update index
                index['tournaments'].append(tournament_id)
                
                # Update tournaments_by_path
                if date_path not in index['tournaments_by_path']:
                    index['tournaments_by_path'][date_path] = []
                index['tournaments_by_path'][date_path].append(tournament_id)
                
                new_count += 1
                print(f"✅ NEW: {tournament_id} saved to {date_path}/ - {data['name'][:50]}... ({data['player_count']} players)")
            else:
                print(f"❌ Failed to scrape {tournament_id}: no data returned")
        except Exception as e:
            print(f"❌ Failed {tournament_id}: {e}")
        
        time.sleep(2)  # Be nice to the server
    
    # Update index metadata
    index['last_updated'] = int(time.time())
    index['total_tournaments'] = len(index['tournaments'])
    
    # Save updated index
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"Update complete: {new_count} new tournaments cached")
    print(f"Total tournaments in cache: {index['total_tournaments']}")

if __name__ == "__main__":
    update_tournament_cache()
