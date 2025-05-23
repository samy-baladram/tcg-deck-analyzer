# card_cache.py
"""Card caching system for sample decks and card data"""

import functools
import os
import json
from datetime import datetime, timedelta
import streamlit as st

# In-memory cache
_card_cache = {}

# Disk cache settings
CARD_CACHE_DIR = "cached_data/card_cache"
CARD_CACHE_INDEX = os.path.join(CARD_CACHE_DIR, "card_index.json")
CACHE_EXPIRE_DAYS = 14  # Cards expire after 2 weeks

def ensure_cache_dir():
    """Ensure card cache directory exists"""
    os.makedirs(CARD_CACHE_DIR, exist_ok=True)

def get_cache_key(deck_name, set_name="A3", cache_type="sample"):
    """Generate consistent cache key for card data"""
    return f"{cache_type}_{deck_name}_{set_name}"

def load_cache_index():
    """Load cache index from disk"""
    try:
        if os.path.exists(CARD_CACHE_INDEX):
            with open(CARD_CACHE_INDEX, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading card cache index: {e}")
    return {}

def save_cache_index(index):
    """Save cache index to disk"""
    try:
        ensure_cache_dir()
        with open(CARD_CACHE_INDEX, 'w') as f:
            json.dump(index, f)
    except Exception as e:
        print(f"Error saving card cache index: {e}")

def is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    try:
        created_time = datetime.fromisoformat(cache_entry['created'])
        expire_time = created_time + timedelta(days=CACHE_EXPIRE_DAYS)
        return datetime.now() < expire_time
    except:
        return False

def get_sample_deck_cached(deck_name, set_name="A3"):
    """Get sample deck with caching"""
    cache_key = get_cache_key(deck_name, set_name, "sample")
    
    # Check in-memory cache first
    if cache_key in _card_cache:
        print(f"Sample deck from memory cache: {deck_name}")
        return _card_cache[cache_key]
    
    # Check disk cache
    cache_index = load_cache_index()
    if cache_key in cache_index:
        cache_entry = cache_index[cache_key]
        
        if is_cache_valid(cache_entry):
            cache_file = os.path.join(CARD_CACHE_DIR, f"{cache_key}.json")
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        sample_deck = json.load(f)
                    
                    # Store in memory cache
                    _card_cache[cache_key] = sample_deck
                    
                    print(f"Sample deck from disk cache: {deck_name}")
                    return sample_deck
                except Exception as e:
                    print(f"Error loading cached sample deck: {e}")
    
    # Generate new sample deck
    print(f"Generating new sample deck: {deck_name}")
    from scraper import get_sample_deck_for_archetype
    
    pokemon_cards, trainer_cards, energy_types = get_sample_deck_for_archetype(deck_name, set_name)
    
    sample_deck = {
        'pokemon_cards': pokemon_cards,
        'trainer_cards': trainer_cards,
        'energy_types': energy_types
    }
    
    # Save to memory cache
    _card_cache[cache_key] = sample_deck
    
    # Save to disk cache
    try:
        ensure_cache_dir()
        
        # Save sample deck file
        cache_file = os.path.join(CARD_CACHE_DIR, f"{cache_key}.json")
        with open(cache_file, 'w') as f:
            json.dump(sample_deck, f)
        
        # Update cache index
        cache_index[cache_key] = {
            'created': datetime.now().isoformat(),
            'deck_name': deck_name,
            'set_name': set_name,
            'cache_type': 'sample'
        }
        save_cache_index(cache_index)
        
        print(f"Saved sample deck to cache: {deck_name}")
        
    except Exception as e:
        print(f"Error saving sample deck to cache: {e}")
    
    return sample_deck

def get_analyzed_deck_cached(deck_name, set_name="A3"):
    """Get analyzed deck data with caching"""
    cache_key = get_cache_key(deck_name, set_name, "analyzed")
    
    # Check in-memory cache first
    if cache_key in _card_cache:
        print(f"Analyzed deck from memory cache: {deck_name}")
        return _card_cache[cache_key]
    
    # Check disk cache
    cache_index = load_cache_index()
    if cache_key in cache_index:
        cache_entry = cache_index[cache_key]
        
        if is_cache_valid(cache_entry):
            cache_file = os.path.join(CARD_CACHE_DIR, f"{cache_key}.json")
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        analyzed_data = json.load(f)
                    
                    # Store in memory cache
                    _card_cache[cache_key] = analyzed_data
                    
                    print(f"Analyzed deck from disk cache: {deck_name}")
                    return analyzed_data
                except Exception as e:
                    print(f"Error loading cached analyzed deck: {e}")
    
    # If not in cache, return None to trigger normal analysis flow
    return None

def save_analyzed_deck_to_cache(deck_name, set_name, analyzed_data):
    """Save analyzed deck data to cache"""
    cache_key = get_cache_key(deck_name, set_name, "analyzed")
    
    # Prepare serializable data
    cache_data = {
        'deck_list': analyzed_data.get('deck_list', {}),
        'deck_info': analyzed_data.get('deck_info', {}),
        'total_cards': analyzed_data.get('total_cards', 0),
        'energy_types': analyzed_data.get('energy_types', []),
        'most_common_energy': analyzed_data.get('most_common_energy', [])
    }
    
    # Save to memory cache
    _card_cache[cache_key] = cache_data
    
    # Save to disk cache
    try:
        ensure_cache_dir()
        
        # Save analyzed deck file
        cache_file = os.path.join(CARD_CACHE_DIR, f"{cache_key}.json")
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Update cache index
        cache_index = load_cache_index()
        cache_index[cache_key] = {
            'created': datetime.now().isoformat(),
            'deck_name': deck_name,
            'set_name': set_name,
            'cache_type': 'analyzed'
        }
        save_cache_index(cache_index)
        
        print(f"Saved analyzed deck to cache: {deck_name}")
        
    except Exception as e:
        print(f"Error saving analyzed deck to cache: {e}")

def clear_expired_cache():
    """Remove expired cache entries"""
    try:
        cache_index = load_cache_index()
        updated_index = {}
        
        for cache_key, cache_entry in cache_index.items():
            if is_cache_valid(cache_entry):
                updated_index[cache_key] = cache_entry
            else:
                # Remove expired file
                cache_file = os.path.join(CARD_CACHE_DIR, f"{cache_key}.json")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                print(f"Removed expired card cache: {cache_key}")
        
        save_cache_index(updated_index)
        print(f"Card cache cleanup: {len(cache_index) - len(updated_index)} expired entries removed")
        
    except Exception as e:
        print(f"Error during card cache cleanup: {e}")

def get_cache_stats():
    """Get cache statistics"""
    memory_count = len(_card_cache)
    disk_count = len(load_cache_index())
    
    return {
        'memory_cached': memory_count,
        'disk_cached': disk_count,
        'cache_dir': CARD_CACHE_DIR
    }

def invalidate_deck_cache(deck_name, set_name="A3"):
    """Invalidate all cache entries for a specific deck"""
    cache_types = ["sample", "analyzed"]
    
    for cache_type in cache_types:
        cache_key = get_cache_key(deck_name, set_name, cache_type)
        
        # Remove from memory cache
        if cache_key in _card_cache:
            del _card_cache[cache_key]
            print(f"Removed {cache_type} deck from memory cache: {deck_name}")
        
        # Remove from disk cache
        cache_file = os.path.join(CARD_CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"Removed {cache_type} deck from disk cache: {deck_name}")
    
    # Update cache index
    cache_index = load_cache_index()
    keys_to_remove = [k for k in cache_index.keys() if deck_name in k and set_name in k]
    
    for key in keys_to_remove:
        del cache_index[key]
    
    save_cache_index(cache_index)
