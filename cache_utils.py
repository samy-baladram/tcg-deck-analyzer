# cache_utils.py
"""Utilities for caching data to disk"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for cached data paths
CACHE_DIR = "cached_data"
TOURNAMENT_DATA_PATH = os.path.join(CACHE_DIR, "tournament_performance.json")
TOURNAMENT_TIMESTAMP_PATH = os.path.join(CACHE_DIR, "tournament_performance_timestamp.txt")
ANALYZED_DECKS_DIR = os.path.join(CACHE_DIR, "analyzed_decks")
CARD_USAGE_PATH = os.path.join(CACHE_DIR, "card_usage.json")
CARD_USAGE_TIMESTAMP_PATH = os.path.join(CACHE_DIR, "card_usage_timestamp.txt")
MATCHUPS_DIR = os.path.join(CACHE_DIR, "matchups")
MATCHUPS_TIMESTAMP_PATH = os.path.join(CACHE_DIR, "matchups_timestamp.txt")

# Add these constants
SAVED_INDEX_PATH = os.path.join(CACHE_DIR, "saved_index.json")
CURRENT_INDEX_PATH = "tournament_cache/index.json"

def save_current_index_as_baseline():
    """Save current tournament_cache/index.json as baseline for comparison"""
    try:
        ensure_cache_dirs()
        
        if os.path.exists(CURRENT_INDEX_PATH):
            with open(CURRENT_INDEX_PATH, 'r') as f:
                current_index = json.load(f)
            
            # Add comparison timestamp
            current_index['saved_timestamp'] = datetime.now().isoformat()
            
            with open(SAVED_INDEX_PATH, 'w') as f:
                json.dump(current_index, f, indent=2)
            
            logger.info(f"Saved baseline index with {len(current_index.get('tournaments', []))} tournaments")
            return True
        else:
            logger.warning(f"Current index not found at {CURRENT_INDEX_PATH}")
            return False
            
    except Exception as e:
        logger.error(f"Error saving baseline index: {e}")
        return False

def load_saved_index():
    """Load the saved baseline index"""
    try:
        if os.path.exists(SAVED_INDEX_PATH):
            with open(SAVED_INDEX_PATH, 'r') as f:
                saved_index = json.load(f)
            logger.info(f"Loaded saved index with {len(saved_index.get('tournaments', []))} tournaments")
            return saved_index
        else:
            logger.info("No saved index found")
            return {}
    except Exception as e:
        logger.error(f"Error loading saved index: {e}")
        return {}

def load_current_index():
    """Load the current tournament_cache/index.json"""
    try:
        if os.path.exists(CURRENT_INDEX_PATH):
            with open(CURRENT_INDEX_PATH, 'r') as f:
                current_index = json.load(f)
            logger.info(f"Loaded current index with {len(current_index.get('tournaments', []))} tournaments")
            return current_index
        else:
            logger.warning(f"Current index not found at {CURRENT_INDEX_PATH}")
            return {}
    except Exception as e:
        logger.error(f"Error loading current index: {e}")
        return {}

def compare_tournament_indices():
    """Compare current index with saved index to detect new tournaments"""
    try:
        saved_index = load_saved_index()
        current_index = load_current_index()
        
        # Get tournament lists
        saved_tournaments = set(saved_index.get('tournaments', []))
        current_tournaments = set(current_index.get('tournaments', []))
        
        # Find new tournaments
        new_tournaments = current_tournaments - saved_tournaments
        
        # Check if total tournament count changed
        saved_total = saved_index.get('total_tournaments', 0)
        current_total = current_index.get('total_tournaments', 0)
        
        # Check if last_updated timestamp changed
        saved_timestamp = saved_index.get('last_updated', 0)
        current_timestamp = current_index.get('last_updated', 0)
        
        result = {
            'has_changes': len(new_tournaments) > 0 or current_total != saved_total or current_timestamp != saved_timestamp,
            'new_tournaments': list(new_tournaments),
            'new_tournament_count': len(new_tournaments),
            'total_change': current_total - saved_total,
            'timestamp_changed': current_timestamp != saved_timestamp,
            'saved_total': saved_total,
            'current_total': current_total
        }
        
        logger.info(f"Index comparison: {result['new_tournament_count']} new tournaments, total change: {result['total_change']}")
        return result
        
    except Exception as e:
        logger.error(f"Error comparing indices: {e}")
        return {
            'has_changes': False,
            'new_tournaments': [],
            'new_tournament_count': 0,
            'total_change': 0,
            'timestamp_changed': False,
            'saved_total': 0,
            'current_total': 0
        }
        
def ensure_cache_dirs():
    """Ensure all cache directories exist"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(ANALYZED_DECKS_DIR, exist_ok=True)

def save_tournament_performance_data(performance_df):
    """Save tournament performance data to cache"""
    try:
        ensure_cache_dirs()
        
        # Save data to JSON file
        with open(TOURNAMENT_DATA_PATH, 'w') as f:
            json.dump(performance_df.to_dict(orient='records'), f)
        
        # Save timestamp
        with open(TOURNAMENT_TIMESTAMP_PATH, 'w') as f:
            f.write(datetime.now().isoformat())
        
        logger.info(f"Saved tournament data to {TOURNAMENT_DATA_PATH}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving tournament data: {e}")
        return False

def load_tournament_performance_data():
    """Load tournament performance data from cache if available"""
    try:
        # Check if data file exists
        if os.path.exists(TOURNAMENT_DATA_PATH):
            logger.info(f"Found tournament data at {TOURNAMENT_DATA_PATH}")
            
            # Read the data from JSON file
            with open(TOURNAMENT_DATA_PATH, 'r') as f:
                data = json.load(f)
            
            # Convert to DataFrame
            performance_df = pd.DataFrame(data)
            
            # Read timestamp
            if os.path.exists(TOURNAMENT_TIMESTAMP_PATH):
                with open(TOURNAMENT_TIMESTAMP_PATH, 'r') as f:
                    timestamp_str = f.read().strip()
                    timestamp = datetime.fromisoformat(timestamp_str)
                logger.info(f"Tournament data timestamp: {timestamp}")
            else:
                # Default to an hour ago if no timestamp file
                timestamp = datetime.now() - timedelta(hours=1)
                logger.info(f"No timestamp file, using default: {timestamp}")
            
            return performance_df, timestamp
        else:
            logger.info(f"No tournament data found at {TOURNAMENT_DATA_PATH}")
        
    except Exception as e:
        logger.error(f"Error loading tournament data: {e}")
    
    # Return empty dataframe and old timestamp if loading fails
    return pd.DataFrame(), datetime.now() - timedelta(hours=2)

def save_analyzed_deck_components(deck_name, set_name, results_df, total_decks, variant_df, energy_types=None):
    """Save the three main deck analysis components to disk"""
    try:
        # Ensure directory exists
        ensure_cache_dirs()
        
        # Create a safe filename base (REMOVED SET NAME SUFFIX)
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        base_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}")  # <-- CHANGED: No more _{set_name}
        
        # Save each component
        results_df.to_csv(f"{base_path}_results.csv", index=False)
        
        # Save total_decks to a text file
        with open(f"{base_path}_total_decks.txt", 'w') as f:
            f.write(str(total_decks))
        
        # Save variant_df if it's not empty
        if not variant_df.empty:
            variant_df.to_csv(f"{base_path}_variants.csv", index=False)
        
        # Save energy_types if provided
        if energy_types:
            import json
            with open(f"{base_path}_energy.json", 'w') as f:
                json.dump(energy_types, f)
        
        # Save a marker file with timestamp
        with open(f"{base_path}_timestamp.txt", 'w') as f:
            f.write(datetime.now().isoformat())
            
        logger.info(f"Saved deck components for {deck_name} to {base_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving deck components: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
def save_analyzed_deck(deck_name, set_name, analyzed_data):
    """Save analyzed deck data (legacy wrapper for compatibility)"""
    try:
        # Extract components from the analyzed_data dictionary
        results_df = analyzed_data.get('results', pd.DataFrame())
        total_decks = analyzed_data.get('total_decks', 0)
        variant_df = analyzed_data.get('variant_df', pd.DataFrame())
        energy_types = analyzed_data.get('energy_types', [])
        
        # Call the component-based save function
        return save_analyzed_deck_components(deck_name, set_name, results_df, total_decks, variant_df, energy_types)
    except Exception as e:
        logger.error(f"Error saving analyzed deck: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
def load_analyzed_deck_components(deck_name, set_name):
    """Load the three main deck analysis components from disk"""
    try:
        # Create a safe filename base (REMOVED SET NAME SUFFIX)
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        base_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}")  # <-- CHANGED: No more _{set_name}
        
        # Check if results file exists
        results_path = f"{base_path}_results.csv"
        if not os.path.exists(results_path):
            logger.info(f"No results file found at {results_path}")
            return None, 0, pd.DataFrame(), []
        
        # Load results
        results_df = pd.read_csv(results_path)
        logger.info(f"Loaded results for {deck_name} from {results_path}")
        
        # Load total_decks
        total_decks = 0
        try:
            with open(f"{base_path}_total_decks.txt", 'r') as f:
                total_decks = int(f.read().strip())
        except:
            # If can't load, try to get from results
            if 'deck_num' in results_df.columns:
                total_decks = len(results_df['deck_num'].unique())
            logger.info(f"Used fallback for total_decks: {total_decks}")
        
        # Load variant_df if it exists
        variant_df = pd.DataFrame()
        variant_path = f"{base_path}_variants.csv"
        if os.path.exists(variant_path):
            variant_df = pd.read_csv(variant_path)
            logger.info(f"Loaded variants from {variant_path}")
        
        # Load energy_types if it exists
        energy_types = []
        energy_path = f"{base_path}_energy.json"
        if os.path.exists(energy_path):
            try:
                import json
                with open(energy_path, 'r') as f:
                    energy_types = json.load(f)
                logger.info(f"Loaded energy types for {deck_name}")
            except:
                logger.warning(f"Error loading energy types from {energy_path}")
        
        return results_df, total_decks, variant_df, energy_types
    except Exception as e:
        logger.error(f"Error loading deck components: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, 0, pd.DataFrame(), []

def load_analyzed_deck(deck_name, set_name):
    """Legacy function to maintain compatibility"""
    results, total_decks, variant_df, energy_types = load_analyzed_deck_components(deck_name, set_name)
    if results is None:
        return None
    return {'results': results, 'energy_types': energy_types}

def save_card_usage_data(card_usage_df):
    """Save card usage data to cache"""
    try:
        ensure_cache_dirs()
        
        # Save data to JSON file
        with open(CARD_USAGE_PATH, 'w') as f:
            json.dump(card_usage_df.to_dict(orient='records'), f)
        
        # Save timestamp
        with open(CARD_USAGE_TIMESTAMP_PATH, 'w') as f:
            f.write(datetime.now().isoformat())
        
        logger.info(f"Saved card usage data to {CARD_USAGE_PATH}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving card usage data: {e}")
        return False

def load_card_usage_data():
    """Load card usage data from cache if available"""
    try:
        # Check if data file exists
        if os.path.exists(CARD_USAGE_PATH):
            logger.info(f"Found card usage data at {CARD_USAGE_PATH}")
            
            # Read the data from JSON file
            with open(CARD_USAGE_PATH, 'r') as f:
                data = json.load(f)
            
            # Convert to DataFrame
            card_usage_df = pd.DataFrame(data)
            
            # Read timestamp
            if os.path.exists(CARD_USAGE_TIMESTAMP_PATH):
                with open(CARD_USAGE_TIMESTAMP_PATH, 'r') as f:
                    timestamp_str = f.read().strip()
                    timestamp = datetime.fromisoformat(timestamp_str)
                logger.info(f"Card usage data timestamp: {timestamp}")
            else:
                # Default to a day ago if no timestamp file
                timestamp = datetime.now() - timedelta(days=1)
                logger.info(f"No timestamp file, using default: {timestamp}")
            
            return card_usage_df, timestamp
        else:
            logger.info(f"No card usage data found at {CARD_USAGE_PATH}")
        
    except Exception as e:
        logger.error(f"Error loading card usage data: {e}")
    
    # Return empty dataframe and old timestamp if loading fails
    return pd.DataFrame(), datetime.now() - timedelta(days=1)
    
######################################################################################################################################################

# Add these new functions to cache_utils.py

# Constants for tournament ID tracking
TOURNAMENT_IDS_PATH = os.path.join(CACHE_DIR, "tournament_ids.json")
PLAYER_TOURNAMENT_MAPPING_PATH = os.path.join(CACHE_DIR, "player_tournament_mapping.json")

def save_tournament_ids(tournament_ids):
    """Save the list of known tournament IDs"""
    try:
        ensure_cache_dirs()
        with open(TOURNAMENT_IDS_PATH, 'w') as f:
            json.dump(tournament_ids, f)
        logger.info(f"Saved {len(tournament_ids)} tournament IDs")
        return True
    except Exception as e:
        logger.error(f"Error saving tournament IDs: {e}")
        return False

def load_tournament_ids():
    """Load the list of known tournament IDs"""
    try:
        if os.path.exists(TOURNAMENT_IDS_PATH):
            with open(TOURNAMENT_IDS_PATH, 'r') as f:
                tournament_ids = json.load(f)
            logger.info(f"Loaded {len(tournament_ids)} tournament IDs")
            return tournament_ids
        else:
            logger.info("No tournament IDs file found")
            return []
    except Exception as e:
        logger.error(f"Error loading tournament IDs: {e}")
        return []

def save_player_tournament_mapping(mapping):
    """Save the mapping of player-tournament pairs to deck archetypes"""
    try:
        ensure_cache_dirs()
        with open(PLAYER_TOURNAMENT_MAPPING_PATH, 'w') as f:
            # Convert any set values to lists for JSON serialization
            serializable_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, set):
                    serializable_mapping[key] = list(value)
                else:
                    serializable_mapping[key] = value
            json.dump(serializable_mapping, f)
        logger.info(f"Saved player-tournament mapping with {len(mapping)} entries")
        return True
    except Exception as e:
        logger.error(f"Error saving player-tournament mapping: {e}")
        return False

def load_player_tournament_mapping():
    """Load the mapping of player-tournament pairs to deck archetypes"""
    try:
        if os.path.exists(PLAYER_TOURNAMENT_MAPPING_PATH):
            with open(PLAYER_TOURNAMENT_MAPPING_PATH, 'r') as f:
                mapping = json.load(f)
            logger.info(f"Loaded player-tournament mapping with {len(mapping)} entries")
            return mapping
        else:
            logger.info("No player-tournament mapping file found")
            return {}
    except Exception as e:
        logger.error(f"Error loading player-tournament mapping: {e}")
        return {}

def clear_deck_cache(deck_name, set_name):
    """Clear cached data for a specific deck"""
    # Create a safe filename (REMOVED SET NAME SUFFIX)
    safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
    base_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}")  # <-- CHANGED: No more _{set_name}
    
    # Try to remove all files
    try:
        extensions = ["_results.csv", "_total_decks.txt", "_variants.csv", "_energy.json", "_timestamp.txt"]
        for ext in extensions:
            file_path = f"{base_path}{ext}"
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Removed {file_path}")
    except Exception as e:
        logger.error(f"Error clearing disk cache for {deck_name}: {e}")
    
    # Clear from session state too
    cache_key = f"full_deck_{deck_name}_{set_name}"
    if 'analyzed_deck_cache' in st.session_state and cache_key in st.session_state.analyzed_deck_cache:
        del st.session_state.analyzed_deck_cache[cache_key]
        logger.info(f"Cleared {deck_name} from session cache")


# Add these functions to cache_utils.py

# Define paths for collected decks
COLLECTED_DECKS_PATH = os.path.join(CACHE_DIR, "collected_decks")

def save_collected_decks(deck_name, set_name, all_decks, all_energy_types, total_decks):
    """Save collected decks to disk"""
    try:
        # Ensure directory exists
        os.makedirs(COLLECTED_DECKS_PATH, exist_ok=True)
        
        # Create a safe filename base (REMOVED SET NAME SUFFIX)
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        file_path = os.path.join(COLLECTED_DECKS_PATH, f"{safe_name}_collected.json")  # <-- CHANGED: No more _{set_name}
        
        # Create serializable version of all_decks
        serializable_decks = []
        for deck in all_decks:
            # Preserve the cards data
            serializable_deck = {
                'deck_num': deck.get('deck_num', 0),
                'energy_types': deck.get('energy_types', []),
                'url': deck.get('url', ''),
                'player_id': deck.get('player_id', ''),
                'tournament_id': deck.get('tournament_id', ''),
                'cards': deck.get('cards', [])
            }
            serializable_decks.append(serializable_deck)
        
        # Create data to save
        data = {
            'decks': serializable_decks,
            'all_energy_types': all_energy_types,
            'total_decks': total_decks,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to file
        with open(file_path, 'w') as f:
            json.dump(data, f)
            
        logger.info(f"Saved collected deck data for {deck_name} to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving collected decks: {e}")
        return False

def load_collected_decks(deck_name, set_name):
    """Load collected deck metadata from disk"""
    try:
        # Create a safe filename base (REMOVED SET NAME SUFFIX)
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        file_path = os.path.join(COLLECTED_DECKS_PATH, f"{safe_name}_collected.json")  # <-- CHANGED: No more _{set_name}
        
        if not os.path.exists(file_path):
            logger.info(f"No collected deck file found at {file_path}")
            return None
        
        # Load from file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        logger.info(f"Loaded collected deck metadata for {deck_name}")
        return data
    except Exception as e:
        logger.error(f"Error loading collected decks: {e}")
        return None
        
def save_matchup_data(deck_name, set_name, matchup_df):
    """Save matchup data for a specific deck to cache"""
    try:
        # Ensure directories exist
        ensure_cache_dirs()
        os.makedirs(MATCHUPS_DIR, exist_ok=True)
        
        # Create a safe filename (REMOVED SET NAME SUFFIX)
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        file_path = os.path.join(MATCHUPS_DIR, f"{safe_name}_matchups.csv")  # <-- CHANGED: No more _{set_name}
        
        # Save DataFrame to CSV
        matchup_df.to_csv(file_path, index=False)
        
        # Save timestamp for this specific deck
        timestamp_path = os.path.join(MATCHUPS_DIR, f"{safe_name}_timestamp.txt")  # <-- CHANGED: No more _{set_name}
        with open(timestamp_path, 'w') as f:
            f.write(datetime.now().isoformat())
            
        logger.info(f"Saved matchup data for {deck_name} to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving matchup data for {deck_name}: {e}")
        return False

def load_matchup_data(deck_name, set_name, max_age_hours=24):
    """Load matchup data for a specific deck from cache if available and not too old"""
    try:
        # Create a safe filename (REMOVED SET NAME SUFFIX)
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        file_path = os.path.join(MATCHUPS_DIR, f"{safe_name}_matchups.csv")  # <-- CHANGED: No more _{set_name}
        timestamp_path = os.path.join(MATCHUPS_DIR, f"{safe_name}_timestamp.txt")  # <-- CHANGED: No more _{set_name}
        
        # Check if files exist
        if not os.path.exists(file_path) or not os.path.exists(timestamp_path):
            logger.info(f"No matchup cache found for {deck_name}")
            return None, None
        
        # Check timestamp
        with open(timestamp_path, 'r') as f:
            timestamp_str = f.read().strip()
            timestamp = datetime.fromisoformat(timestamp_str)
        
        # Check if data is too old
        age = datetime.now() - timestamp
        if age.total_seconds() > max_age_hours * 3600:
            logger.info(f"Matchup cache for {deck_name} is too old ({age})")
            return None, None
        
        # Load matchup data
        matchup_df = pd.read_csv(file_path)
        logger.info(f"Loaded matchup cache for {deck_name} from {file_path}")
        
        return matchup_df, timestamp
        
    except Exception as e:
        logger.error(f"Error loading matchup cache for {deck_name}: {e}")
        return None, None

def update_all_matchups(min_share=0.5):
    """
    Update matchup data for all decks with at least the specified meta share
    UPDATED to use meta_table instead of performance_data
    """
    try:
        # UPDATED: Get qualifying decks from meta_table instead of performance_data
        from meta_table import MetaTableBuilder
        
        builder = MetaTableBuilder()
        meta_df = builder.build_complete_meta_table(limit=50)
        
        if meta_df.empty:
            print("DEBUG: No meta data available for updating matchups")
            return 0
        
        # Filter for decks with at least min_share
        qualifying_decks = meta_df[meta_df['share_7d'] >= min_share]
        
        print(f"DEBUG: Updating matchups for {len(qualifying_decks)} decks with ≥{min_share}% meta share")
        updated_count = 0
        
        # Update each deck's matchups
        for deck_name in qualifying_decks.index:
            set_name = 'A3a'  # Current set
            
            # Import here to avoid circular imports
            import cache_manager
            
            # Fetch fresh matchup data
            matchup_df = cache_manager.get_or_fetch_matchup_data(deck_name, set_name, force_update=True)
            
            if not matchup_df.empty:
                updated_count += 1
                print(f"DEBUG: Updated matchups for {deck_name}")
        
        print(f"DEBUG: Updated matchups for {updated_count} decks")
        return updated_count
        
    except Exception as e:
        print(f"DEBUG: Error updating all matchups: {e}")
        import traceback
        print(traceback.format_exc())
        return 0

def ensure_cache_dirs():
    """Ensure all cache directories exist"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(ANALYZED_DECKS_DIR, exist_ok=True)
    os.makedirs(MATCHUPS_DIR, exist_ok=True)
