# cache_utils.py
"""Utilities for caching data to disk"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import logging

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
        
        # Create a safe filename base
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        base_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}_{set_name}")
        
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
        # Create a safe filename base
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        base_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}_{set_name}")
        
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
    """Clear disk and memory cache for a specific deck"""
    # Create a safe filename base
    safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
    base_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}_{set_name}")
    
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
        
        # Create a safe filename base
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        file_path = os.path.join(COLLECTED_DECKS_PATH, f"{safe_name}_{set_name}_collected.json")
        
        # Create serializable version of all_decks
        # (The cards list might be too large, so we'll just save metadata)
        serializable_decks = []
        for deck in all_decks:
            # Save key metadata but not full card lists
            serializable_deck = {
                'deck_num': deck.get('deck_num', 0),
                'energy_types': deck.get('energy_types', []),
                'url': deck.get('url', ''),
                'player_id': deck.get('player_id', ''),
                'tournament_id': deck.get('tournament_id', '')
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
            
        logger.info(f"Saved collected deck metadata for {deck_name} to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving collected decks: {e}")
        return False

def load_collected_decks(deck_name, set_name):
    """Load collected deck metadata from disk"""
    try:
        # Create a safe filename base
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        file_path = os.path.join(COLLECTED_DECKS_PATH, f"{safe_name}_{set_name}_collected.json")
        
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
