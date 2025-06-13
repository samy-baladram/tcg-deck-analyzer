import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
import sqlite3
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
    
    # Extract format information
    page_text = details_soup.get_text()
    format_type = "Standard"  # Default fallback
    
    # Pattern 1: "- NOEX format -" or "- Standard format -"
    format_match = re.search(r'-\s*(NOEX|Standard)\s+format\s*-', page_text, re.IGNORECASE)
    if format_match:
        format_type = format_match.group(1).upper()
    else:
        # Pattern 2: "Format: NOEX" or "Format: Standard"
        format_match = re.search(r'Format:\s*(NOEX|Standard)', page_text, re.IGNORECASE)
        if format_match:
            format_type = format_match.group(1).upper()
        else:
            # Pattern 3: Look for "NOEX" anywhere (indicating no EX cards)
            if re.search(r'\bNOEX\b|\bNo\s*EX\b', page_text, re.IGNORECASE):
                format_type = "NOEX"
    
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
        'format': format_type,
        'player_count': len(players),
        'players': players
    }

def get_date_folder_path(timestamp):
    """Convert timestamp to YYYY/MM/DD folder path"""
    if not timestamp:
        date = datetime.now()
    else:
        date = datetime.fromtimestamp(timestamp / 1000)
    
    return f"{date.year}/{date.month:02d}/{date.day:02d}"

def get_date_string(timestamp):
    """Convert timestamp to YYYY-MM-DD string"""
    if not timestamp:
        date = datetime.now()
    else:
        date = datetime.fromtimestamp(timestamp / 1000)
    
    return date.strftime('%Y-%m-%d')

def init_meta_database():
    """Initialize SQLite database with required tables"""
    meta_dir = "meta_analysis"
    os.makedirs(meta_dir, exist_ok=True)
    
    conn = sqlite3.connect(f"{meta_dir}/tournament_meta.db")
    
    # Create tables with format field and new player_performance table
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tournaments (
            tournament_id TEXT PRIMARY KEY,
            date TEXT,
            format TEXT,
            total_players INTEGER,
            unique_archetypes INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS archetype_appearances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT,
            archetype TEXT,
            count INTEGER,
            percentage REAL,
            FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id)
        );
        
        CREATE TABLE IF NOT EXISTS player_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT,
            player_name TEXT,
            archetype TEXT,
            placement INTEGER,
            wins INTEGER,
            losses INTEGER,
            ties INTEGER,
            FOREIGN KEY (tournament_id) REFERENCES tournaments (tournament_id)
        );
        
        CREATE TABLE IF NOT EXISTS daily_meta (
            date TEXT PRIMARY KEY,
            total_players INTEGER,
            total_tournaments INTEGER,
            archetype_data TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_archetype_tournament 
        ON archetype_appearances(archetype, tournament_id);
        
        CREATE INDEX IF NOT EXISTS idx_tournament_date 
        ON tournaments(date);
        
        CREATE INDEX IF NOT EXISTS idx_tournament_format 
        ON tournaments(format);
        
        CREATE INDEX IF NOT EXISTS idx_player_performance_archetype 
        ON player_performance(archetype);
        
        CREATE INDEX IF NOT EXISTS idx_player_performance_tournament 
        ON player_performance(tournament_id);
    """)
    
    conn.commit()
    conn.close()

def parse_record(record_str):
    """
    Parse record string like "9 - 2 - 0" into wins, losses, ties
    
    Args:
        record_str: String like "9 - 2 - 0"
        
    Returns:
        tuple: (wins, losses, ties) or (0, 0, 0) if parsing fails
    """
    try:
        # Remove extra spaces and split by '-'
        parts = [part.strip() for part in record_str.split('-')]
        
        if len(parts) >= 3:
            wins = int(parts[0])
            losses = int(parts[1]) 
            ties = int(parts[2])
            return wins, losses, ties
        elif len(parts) == 2:
            # Handle case with no ties recorded
            wins = int(parts[0])
            losses = int(parts[1])
            ties = 0
            return wins, losses, ties
            
    except (ValueError, IndexError):
        pass
    
    return 0, 0, 0

def process_tournament_meta(tournament_data):
    """Process tournament data and update meta database"""
    tournament_id = tournament_data['tournament_id']
    date_str = get_date_string(tournament_data['timestamp'])
    total_players = tournament_data['player_count']
    format_type = tournament_data.get('format', 'Standard')
    
    # Count archetypes
    archetype_counts = {}
    for player in tournament_data['players']:
        archetype = player.get('archetype')
        if archetype:
            archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1
    
    if not archetype_counts:
        print(f"No archetypes found for tournament {tournament_id}")
        return
    
    conn = sqlite3.connect("meta_analysis/tournament_meta.db")
    
    # Add tournament summary
    conn.execute("""
        INSERT OR REPLACE INTO tournaments 
        VALUES (?, ?, ?, ?, ?)
    """, (tournament_id, date_str, format_type, total_players, len(archetype_counts)))
    
    # Remove existing data for this tournament (in case of reprocessing)
    conn.execute("DELETE FROM archetype_appearances WHERE tournament_id = ?", (tournament_id,))
    conn.execute("DELETE FROM player_performance WHERE tournament_id = ?", (tournament_id,))
    
    # Add archetype appearances
    for archetype, count in archetype_counts.items():
        percentage = (count / total_players) * 100
        conn.execute("""
            INSERT INTO archetype_appearances 
            (tournament_id, archetype, count, percentage) 
            VALUES (?, ?, ?, ?)
        """, (tournament_id, archetype, count, percentage))
    
    # Add individual player performance data
    for player in tournament_data['players']:
        if player.get('archetype'):  # Only add players with known archetypes
            wins, losses, ties = parse_record(player.get('record', '0-0-0'))
            
            conn.execute("""
                INSERT INTO player_performance 
                (tournament_id, player_name, archetype, placement, wins, losses, ties) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                tournament_id,
                player.get('player_name', 'Unknown'),
                player['archetype'],
                player.get('placement', 999),
                wins,
                losses,
                ties
            ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Meta processed: {tournament_id} ({format_type}) - {len(archetype_counts)} archetypes, {len(tournament_data['players'])} players")

def update_quick_index():
    """Update the quick JSON index file"""
    conn = sqlite3.connect("meta_analysis/tournament_meta.db")
    
    # Get basic stats
    cursor = conn.execute("SELECT COUNT(*) FROM tournaments")
    total_tournaments = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT MIN(date), MAX(date) FROM tournaments")
    date_range = cursor.fetchone()
    
    # Get format distribution
    cursor = conn.execute("""
        SELECT format, COUNT(*) as count 
        FROM tournaments 
        GROUP BY format 
        ORDER BY count DESC
    """)
    format_distribution = {}
    for format_type, count in cursor.fetchall():
        format_distribution[format_type] = count
    
    # Get top archetypes (by total appearances)
    cursor = conn.execute("""
        SELECT archetype, SUM(count) as total_count 
        FROM archetype_appearances 
        GROUP BY archetype 
        ORDER BY total_count DESC 
        LIMIT 10
    """)
    top_archetypes = [row[0] for row in cursor.fetchall()]
    
    # Get top archetypes by format
    top_archetypes_by_format = {}
    for format_type in format_distribution.keys():
        cursor = conn.execute("""
            SELECT archetype, SUM(aa.count) as total_count 
            FROM archetype_appearances aa
            JOIN tournaments t ON aa.tournament_id = t.tournament_id
            WHERE t.format = ?
            GROUP BY archetype 
            ORDER BY total_count DESC 
            LIMIT 5
        """, (format_type,))
        top_archetypes_by_format[format_type] = [row[0] for row in cursor.fetchall()]
    
    # Get recent daily meta (last 7 days)
    cursor = conn.execute("""
        SELECT date, total_players, total_tournaments 
        FROM daily_meta 
        ORDER BY date DESC 
        LIMIT 7
    """)
    recent_daily = {}
    for date, players, tournaments in cursor.fetchall():
        recent_daily[date] = {
            "total_players": players,
            "total_tournaments": tournaments
        }
    
    conn.close()
    
    # Create quick index with format information
    quick_index = {
        "last_updated": int(time.time()),
        "total_tournaments": total_tournaments,
        "format_distribution": format_distribution,
        "date_range": {
            "earliest": date_range[0] if date_range[0] else None,
            "latest": date_range[1] if date_range[1] else None
        },
        "top_archetypes": top_archetypes,
        "top_archetypes_by_format": top_archetypes_by_format,
        "recent_daily_meta": recent_daily
    }
    
    # Save to JSON
    with open("meta_analysis/quick_index.json", 'w') as f:
        json.dump(quick_index, f, indent=2)
    
    print("✅ Quick index updated with format data")

# Add this simple function
def update_sets_index():
    """Simple function to update sets index"""
    try:
        response = requests.get("https://pocket.limitlesstcg.com/cards")
        soup = BeautifulSoup(response.text, 'html.parser')
        lines = [line.strip() for line in soup.get_text().split('\n') if line.strip()]
        
        sets_data = []
        for i in range(len(lines) - 3):
            set_name, set_code, date_str, count_str = lines[i:i+4]
            
            if re.match(r'^[A-Z]\d[a-z]?$|^P-[A-Z]$', set_code) and count_str.isdigit():
                # Parse date from format "29 May 25"
                release_date = None
                if re.match(r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{2}$', date_str):
                    try:
                        date_obj = datetime.strptime(date_str, '%d %b %y')
                        if date_obj.year < 1950:
                            date_obj = date_obj.replace(year=date_obj.year + 2000)
                        release_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        pass
                
                sets_data.append({
                    'set_name': set_name,
                    'set_code': set_code,
                    'release_date': release_date,
                    'card_count': int(count_str)
                })
        
        # Save to meta_analysis directory
        sets_file = "meta_analysis/sets_index.json"
        os.makedirs(os.path.dirname(sets_file), exist_ok=True)
        
        with open(sets_file, 'w') as f:
            json.dump({
                'last_updated': datetime.now().isoformat(),
                'sets': sets_data
            }, f, indent=2)
        
        print(f"✅ Updated sets index with {len(sets_data)} sets")
        
    except Exception as e:
        print(f"❌ Error updating sets: {e}")
        
def update_tournament_cache():
    """Main function to update tournament cache and meta analysis"""
    cache_dir = "tournament_cache"
    index_file = f"{cache_dir}/index.json"
    
    # Ensure directories exist
    os.makedirs(cache_dir, exist_ok=True)
    
    # Initialize meta database
    init_meta_database()

    # Update sets index
    update_sets_index()
    
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
    
    # ADDITION: Check which tournaments are missing from SQLite
    conn = sqlite3.connect("meta_analysis/tournament_meta.db")
    cursor = conn.execute("SELECT tournament_id FROM tournaments")
    existing_in_db = {row[0] for row in cursor.fetchall()}
    conn.close()
    
    # Find tournaments that exist as JSON but not in SQLite
    missing_from_db = []
    for tournament_id in index['tournaments']:
        if tournament_id not in existing_in_db:
            # Find the JSON file for this tournament
            for date_path, tournament_list in index['tournaments_by_path'].items():
                if tournament_id in tournament_list:
                    json_file = f"{cache_dir}/{date_path}/{tournament_id}.json"
                    if os.path.exists(json_file):
                        missing_from_db.append(json_file)
                    break
    
    print(f"Found {len(missing_from_db)} tournaments to process into SQLite")
    
    # Process existing JSON files into SQLite
    for json_file in missing_from_db:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            process_tournament_meta(data)
            print(f"✅ Processed existing: {data['tournament_id']}")
        except Exception as e:
            print(f"❌ Failed to process {json_file}: {e}")
    
    # Get recent tournament IDs
    tournament_ids = get_recent_tournament_ids(100)
    print(f"Found {len(tournament_ids)} recent tournaments")
    
    # Find NEW tournaments
    new_tournament_ids = [tid for tid in tournament_ids if tid not in index['tournaments']]
    print(f"New tournaments to scrape: {len(new_tournament_ids)}")
    
    if not new_tournament_ids and not missing_from_db:
        print("No new tournaments found and SQLite is up to date")
        return
    
    # CHANGE: Find tournaments without actual files (not just index entries)
    unprocessed_tournament_ids = []
    for tid in tournament_ids:
        # Check if tournament file actually exists
        found_file = False
        for date_path in index.get('tournaments_by_path', {}).keys():
            tournament_file = f"{cache_dir}/{date_path}/{tid}.json"
            if os.path.exists(tournament_file):
                found_file = True
                break
        
        if not found_file:
            unprocessed_tournament_ids.append(tid)
    
    print(f"Unprocessed tournaments to scrape: {len(unprocessed_tournament_ids)}")
    
    if not unprocessed_tournament_ids:
        print("No unprocessed tournaments found - nothing to scrape")
        return
    
    new_count = 0
    
    # Process unprocessed tournaments
    for tournament_id in unprocessed_tournament_ids:
        try:
            # Scrape tournament data
            data = scrape_tournament_data(tournament_id)
            if data:
                # Save tournament file
                date_path = get_date_folder_path(data['timestamp'])
                full_folder_path = f"{cache_dir}/{date_path}"
                os.makedirs(full_folder_path, exist_ok=True)
                
                tournament_file = f"{full_folder_path}/{tournament_id}.json"
                with open(tournament_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Process meta data
                process_tournament_meta(data)
                
                # Update index
                if tournament_id not in index['tournaments']:
                    index['tournaments'].append(tournament_id)
                if date_path not in index['tournaments_by_path']:
                    index['tournaments_by_path'][date_path] = []
                if tournament_id not in index['tournaments_by_path'][date_path]:
                    index['tournaments_by_path'][date_path].append(tournament_id)
                
                new_count += 1
                print(f"✅ PROCESSED: {tournament_id} saved to {date_path}/ - {data['name'][:50]}... ({data['player_count']} players)")
            else:
                print(f"❌ Failed to scrape {tournament_id}: no data returned")
        except Exception as e:
            print(f"❌ Failed {tournament_id}: {e}")
        
        time.sleep(2)
    
    # Update index
    index['last_updated'] = int(time.time())
    index['total_tournaments'] = len(index['tournaments'])
    
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)
    
    # Update quick index
    update_quick_index()
    
    print(f"Update complete: {new_count} tournaments processed")
    print(f"Total tournaments in cache: {index['total_tournaments']}")

if __name__ == "__main__":
    update_tournament_cache()
