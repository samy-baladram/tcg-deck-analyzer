# header_image_cache.py
"""Header image caching system for deck images"""

import functools
import base64
import os
import json
from datetime import datetime, timedelta
from image_processor import create_deck_header_images

# In-memory cache
_header_image_cache = {}

# Disk cache settings
HEADER_CACHE_DIR = "cached_data/header_images"
HEADER_CACHE_INDEX = os.path.join(HEADER_CACHE_DIR, "cache_index.json")
CACHE_EXPIRE_DAYS = 7  # Images expire after 7 days

def ensure_cache_dir():
    """Ensure header cache directory exists"""
    os.makedirs(HEADER_CACHE_DIR, exist_ok=True)

def get_cache_key(deck_name, set_name="A3"):
    """Generate consistent cache key for deck header image"""
    return f"{deck_name}_{set_name}"

def load_cache_index():
    """Load cache index from disk"""
    try:
        if os.path.exists(HEADER_CACHE_INDEX):
            with open(HEADER_CACHE_INDEX, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading header cache index: {e}")
    return {}

def save_cache_index(index):
    """Save cache index to disk"""
    try:
        ensure_cache_dir()
        with open(HEADER_CACHE_INDEX, 'w') as f:
            json.dump(index, f)
    except Exception as e:
        print(f"Error saving header cache index: {e}")

def is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    try:
        created_time = datetime.fromisoformat(cache_entry['created'])
        expire_time = created_time + timedelta(days=CACHE_EXPIRE_DAYS)
        return datetime.now() < expire_time
    except:
        return False

# In header_image_cache.py - Update this function
def get_header_image_cached(deck_name, set_name="A3", analysis_results=None):
    """Get header image with aggressive caching"""
    cache_key = get_cache_key(deck_name, set_name)
    
    # Check in-memory cache first
    if cache_key in _header_image_cache:
        return _header_image_cache[cache_key]
    
    # Check disk cache
    cache_index = load_cache_index()
    if cache_key in cache_index:
        cache_entry = cache_index[cache_key]
        
        # Check if cache is still valid
        if is_cache_valid(cache_entry):
            image_file = os.path.join(HEADER_CACHE_DIR, f"{cache_key}.png")
            
            if os.path.exists(image_file):
                try:
                    # Load from disk
                    with open(image_file, 'rb') as f:
                        image_data = f.read()
                    
                    # Convert to base64
                    img_base64 = base64.b64encode(image_data).decode()
                    
                    # Store in memory cache
                    _header_image_cache[cache_key] = img_base64
                    
                    print(f"Loaded header image from disk cache: {deck_name}")
                    return img_base64
                except Exception as e:
                    print(f"Error loading cached header image: {e}")
    
    # Generate new image
    print(f"Generating new header image: {deck_name}")
    deck_info = {'deck_name': deck_name, 'set': set_name}
    img_base64 = create_deck_header_images(deck_info, analysis_results)
    
    if img_base64:
        # Save to memory cache
        _header_image_cache[cache_key] = img_base64
        
        # Save to disk cache
        try:
            ensure_cache_dir()
            
            # Save image file
            image_file = os.path.join(HEADER_CACHE_DIR, f"{cache_key}.png")
            image_data = base64.b64decode(img_base64)
            with open(image_file, 'wb') as f:
                f.write(image_data)
            
            # Update cache index
            cache_index[cache_key] = {
                'created': datetime.now().isoformat(),
                'deck_name': deck_name,
                'set_name': set_name
            }
            save_cache_index(cache_index)
            
            print(f"Saved header image to disk cache: {deck_name}")
            
        except Exception as e:
            print(f"Error saving header image to cache: {e}")
    
    return img_base64

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
                image_file = os.path.join(HEADER_CACHE_DIR, f"{cache_key}.png")
                if os.path.exists(image_file):
                    os.remove(image_file)
                print(f"Removed expired header cache: {cache_key}")
        
        save_cache_index(updated_index)
        print(f"Cache cleanup: {len(cache_index) - len(updated_index)} expired entries removed")
        
    except Exception as e:
        print(f"Error during cache cleanup: {e}")

def get_cache_stats():
    """Get cache statistics"""
    memory_count = len(_header_image_cache)
    disk_count = len(load_cache_index())
    
    return {
        'memory_cached': memory_count,
        'disk_cached': disk_count,
        'cache_dir': HEADER_CACHE_DIR
    }
