# formatters.py
"""Text formatting functions for the TCG Deck Analyzer"""

import re
from utils import is_set_code, format_set_code

from config import POKEMON_EXCEPTIONS
def format_deck_name(deck_name):
    """
    Convert deck names from URL format to display format.
    Example: garchomp-ex-a2a-rampardos-a2 -> Garchomp Ex (A2a) Rampardos (A2)
    """
    parts = deck_name.split('-')
    result = []
    i = 0
    
    while i < len(parts):
        part = parts[i]
        
        if is_set_code(part):
            # Format set code: A3b format
            formatted = format_set_code(part)
            if result and not result[-1].endswith(')'):
                result[-1] += f" ({formatted})"
            i += 1
        else:
            word = part.title()
            
            # Check if next part is a set code
            if i + 1 < len(parts) and is_set_code(parts[i + 1]):
                set_code = parts[i + 1]
                formatted = format_set_code(set_code)
                word += " " #f" ({formatted})"
                i += 2
            else:
                i += 1
                
            result.append(word)
    
    return ' '.join(result).strip()

def format_percentage(value, show_zero=False):
    """Format a percentage value for display"""
    if value == 0 and not show_zero:
        return ""
    return f"{value}%"

def format_card_count(count, card_name):
    """Format card count for deck list display"""
    return f"{count} {card_name}"

def format_deck_option(deck_name, share):
    """Format deck option for dropdown display"""
    return f"{format_deck_name(deck_name)} - {share:.2f}%"

def parse_deck_option(option_text):
    """Parse deck option to extract name and share"""
    parts = option_text.rsplit(' - ', 1)
    if len(parts) == 2:
        name = parts[0]
        share = float(parts[1].replace('%', ''))
        return name, share
    return option_text, 0.0

def format_variant_id(set_code, num):
    """Format variant ID for display"""
    return f"{set_code}-{num}"

def format_card_label(card_name, set_code=None, num=None):
    """Format card label for charts and displays"""
    if set_code and num:
        return f"{card_name} ({set_code}-{num})"
    return card_name

# Extract Pokémon names and create image URLs
# formatters.py - Updated function
def extract_pokemon_urls(deck_name):
    """
    Extract Pokemon names and create image URLs with context-dependent exceptions.
    Uses config.POKEMON_URL_EXCEPTIONS for pair-based name replacements.
    
    Args:
        deck_name: The deck name to extract Pokemon from (changed from displayed_name)
        
    Returns:
        Tuple of (url1, url2) - Pokemon image URLs
    """
    from config import POKEMON_URL_EXCEPTIONS
    from image_processor import extract_pokemon_from_deck_name
    
    # Use the unified Pokemon extraction function
    pokemon_names = extract_pokemon_from_deck_name(deck_name)
    
    # Convert to lowercase and remove spaces/hyphens for URL generation
    pokemon_names = [name.lower().replace(' ', '').replace('-', '') for name in pokemon_names]
    
    # Apply context-dependent exceptions
    if len(pokemon_names) >= 2:
        # Check if first Pokemon has exceptions based on second Pokemon
        if pokemon_names[0] in POKEMON_URL_EXCEPTIONS:
            exceptions = POKEMON_URL_EXCEPTIONS[pokemon_names[0]]
            if pokemon_names[1] in exceptions:
                pokemon_names[0] = exceptions[pokemon_names[1]]
            elif 'default' in exceptions:
                pokemon_names[0] = exceptions['default']
        
        # Check if second Pokemon has exceptions based on first Pokemon
        if pokemon_names[1] in POKEMON_URL_EXCEPTIONS:
            exceptions = POKEMON_URL_EXCEPTIONS[pokemon_names[1]]
            if pokemon_names[0] in exceptions:
                pokemon_names[1] = exceptions[pokemon_names[0]]
            elif 'default' in exceptions:
                pokemon_names[1] = exceptions['default']
    elif len(pokemon_names) == 1:
        # Single Pokemon - apply default exception if available
        if pokemon_names[0] in POKEMON_URL_EXCEPTIONS:
            exceptions = POKEMON_URL_EXCEPTIONS[pokemon_names[0]]
            if 'default' in exceptions:
                pokemon_names[0] = exceptions['default']
    
    # Create URLs
    urls = []
    for name in pokemon_names:
        urls.append(f"https://r2.limitlesstcg.net/pokemon/gen9/{name}.png")
        
    # Ensure we have exactly 2 elements
    while len(urls) < 2:
        urls.append(None)
        
    return urls[0], urls[1]  # Return as separate values
