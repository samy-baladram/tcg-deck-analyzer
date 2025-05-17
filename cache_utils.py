# cache_utils.py
"""Utilities for caching data to disk"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta

# Constants for cached data paths
CACHE_DIR = "cached_data"
TOURNAMENT_DATA_PATH = os.path.join(CACHE_DIR, "tournament_performance.json")
TOURNAMENT_TIMESTAMP_PATH = os.path.join(CACHE_DIR, "tournament_performance_timestamp.txt")
ANALYZED_DECKS_DIR = os.path.join(CACHE_DIR, "analyzed_decks")

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
        
        return True
    
    except Exception as e:
        print(f"Error saving tournament data: {e}")
        return False

def load_tournament_performance_data():
    """Load tournament performance data from cache if available"""
    try:
        # Check if data file exists
        if os.path.exists(TOURNAMENT_DATA_PATH):
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
            else:
                # Default to an hour ago if no timestamp file
                timestamp = datetime.now() - timedelta(hours=1)
            
            return performance_df, timestamp
        
    except Exception as e:
        print(f"Error loading tournament data: {e}")
    
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
        
        return True
    
    except Exception as e:
        print(f"Error saving analyzed deck: {e}")
        return False

def load_analyzed_deck(deck_name, set_name):
    """Load analyzed deck data from disk cache if available"""
    try:
        # Get cache path
        cache_path = get_deck_cache_path(deck_name, set_name)
        
        # Check if file exists
        if os.path.exists(cache_path):
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
        
    except Exception as e:
        print(f"Error loading analyzed deck: {e}")
    
    # Return None if loading fails
    return None
