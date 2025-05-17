# cache_utils.py
"""Utilities for caching data to disk"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import logging  # Add logging for debugging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for cached data paths
CACHE_DIR = "cached_data"
TOURNAMENT_DATA_PATH = os.path.join(CACHE_DIR, "tournament_performance.json")
TOURNAMENT_TIMESTAMP_PATH = os.path.join(CACHE_DIR, "tournament_performance_timestamp.txt")
ANALYZED_DECKS_DIR = os.path.join(CACHE_DIR, "analyzed_decks")

def ensure_cache_dirs():
    """Ensure all cache directories exist"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(ANALYZED_DECKS_DIR, exist_ok=True)
    logger.info(f"Cache directories ensured: {CACHE_DIR}, {ANALYZED_DECKS_DIR}")

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

def get_deck_cache_path(deck_name, set_name):
    """Generate a file path for a deck cache file"""
    # Sanitize filename (replace invalid characters)
    safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
    return os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}_{set_name}.json")

def save_analyzed_deck(deck_name, set_name, deck_data):
    """Save analyzed deck data to disk cache"""
    try:
        ensure_cache_dirs()
        
        # Prepare the path
        cache_path = get_deck_cache_path(deck_name, set_name)
        
        # Convert pandas DataFrames to dictionaries
        serializable_data = {}
        for key, value in deck_data.items():
            if isinstance(value, pd.DataFrame):
                serializable_data[key] = value.to_dict(orient='records')
            else:
                serializable_data[key] = value
        
        # Add timestamp
        serializable_data['timestamp'] = datetime.now().isoformat()
        
        # Save to file
        with open(cache_path, 'w') as f:
            json.dump(serializable_data, f)
        
        logger.info(f"Saved analyzed deck data to {cache_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving analyzed deck: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def load_analyzed_deck(deck_name, set_name):
    """Load analyzed deck data from disk cache if available"""
    try:
        # Get cache path
        cache_path = get_deck_cache_path(deck_name, set_name)
        
        # Check if file exists
        if os.path.exists(cache_path):
            logger.info(f"Found deck cache at {cache_path}")
            
            # Read data from file
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Convert dictionaries back to DataFrames
            result = {}
            for key, value in data.items():
                if key in ['results', 'variant_df', 'options'] and isinstance(value, list):
                    result[key] = pd.DataFrame(value)
                elif key != 'timestamp':  # Skip timestamp in results
                    result[key] = value
            
            return result
        else:
            logger.info(f"No deck cache found at {cache_path}")
        
    except Exception as e:
        logger.error(f"Error loading analyzed deck: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Return None if loading fails
    return None

# Add these to cache_utils.py

def get_card_usage_path():
    """Get the file path for the aggregated card usage data"""
    return os.path.join(CACHE_DIR, "card_usage.json")

def get_card_usage_timestamp_path():
    """Get the file path for the card usage timestamp"""
    return os.path.join(CACHE_DIR, "card_usage_timestamp.txt")

def save_card_usage_data(card_usage_df):
    """Save aggregated card usage data to cache"""
    try:
        ensure_cache_dirs()
        
        # Save data to JSON file
        with open(get_card_usage_path(), 'w') as f:
            json.dump(card_usage_df.to_dict(orient='records'), f)
        
        # Save timestamp
        with open(get_card_usage_timestamp_path(), 'w') as f:
            f.write(datetime.now().isoformat())
        
        logger.info(f"Saved card usage data to {get_card_usage_path()}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving card usage data: {e}")
        return False

def load_card_usage_data():
    """Load aggregated card usage data from cache if available"""
    try:
        # Check if data file exists
        if os.path.exists(get_card_usage_path()):
            logger.info(f"Found card usage data at {get_card_usage_path()}")
            
            # Read the data from JSON file
            with open(get_card_usage_path(), 'r') as f:
                data = json.load(f)
            
            # Convert to DataFrame
            card_usage_df = pd.DataFrame(data)
            
            # Read timestamp
            if os.path.exists(get_card_usage_timestamp_path()):
                with open(get_card_usage_timestamp_path(), 'r') as f:
                    timestamp_str = f.read().strip()
                    timestamp = datetime.fromisoformat(timestamp_str)
                logger.info(f"Card usage data timestamp: {timestamp}")
            else:
                # Default to a day ago if no timestamp file
                timestamp = datetime.now() - timedelta(days=1)
                logger.info(f"No timestamp file, using default: {timestamp}")
            
            return card_usage_df, timestamp
        else:
            logger.info(f"No card usage data found at {get_card_usage_path()}")
        
    except Exception as e:
        logger.error(f"Error loading card usage data: {e}")
    
    # Return empty dataframe and old timestamp if loading fails
    return pd.DataFrame(), datetime.now() - timedelta(days=1)

def save_analyzed_deck_simple(deck_name, set_name, results_df):
    """Save just the results DataFrame to disk"""
    try:
        # Ensure directory exists
        os.makedirs(ANALYZED_DECKS_DIR, exist_ok=True)
        
        # Create a safe filename
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        cache_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}_{set_name}_results.csv")
        
        # Save as CSV (simpler than JSON for DataFrames)
        results_df.to_csv(cache_path, index=False)
        
        return True
    except Exception as e:
        print(f"Error saving results: {e}")
        return False

def load_analyzed_deck_simple(deck_name, set_name):
    """Load just the results DataFrame from disk"""
    try:
        # Create a safe filename
        safe_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in deck_name)
        cache_path = os.path.join(ANALYZED_DECKS_DIR, f"{safe_name}_{set_name}_results.csv")
        
        # Check if file exists
        if os.path.exists(cache_path):
            # Load CSV
            results_df = pd.read_csv(cache_path)
            return results_df
        else:
            return None
    except Exception as e:
        print(f"Error loading results: {e}")
        return None

def save_analyzed_deck_components(deck_name, set_name, results_df, total_decks, variant_df):
    """Save the three main deck analysis components to disk"""
    try:
        # Ensure directory exists
        os.makedirs(ANALYZED_DECKS_DIR, exist_ok=True)
        
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
        
        # Save a marker file with timestamp
        with open(f"{base_path}_timestamp.txt", 'w') as f:
            f.write(datetime.now().isoformat())
        
        return True
    except Exception as e:
        print(f"Error saving deck components: {e}")
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
            return None, 0, pd.DataFrame()
        
        # Load results
        results_df = pd.read_csv(results_path)
        
        # Load total_decks
        total_decks = 0
        try:
            with open(f"{base_path}_total_decks.txt", 'r') as f:
                total_decks = int(f.read().strip())
        except:
            # If can't load, try to get from results
            if 'deck_num' in results_df.columns:
                total_decks = len(results_df['deck_num'].unique())
        
        # Load variant_df if it exists
        variant_df = pd.DataFrame()
        variant_path = f"{base_path}_variants.csv"
        if os.path.exists(variant_path):
            variant_df = pd.read_csv(variant_path)
        
        return results_df, total_decks, variant_df
    except Exception as e:
        print(f"Error loading deck components: {e}")
        return None, 0, pd.DataFrame()
