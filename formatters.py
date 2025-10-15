# formatters.py
"""Text formatting functions for the TCG Deck Analyzer"""

import re
from utils import is_set_code, format_set_code

from config import POKEMON_EXCEPTIONS
def format_deck_name(deck_name):
    """
    Convert deck names from URL format to display format.
    Example: garchomp-ex-a2a-rampardos-a2 -> Garchomp Ex (A2a) Rampardos (A2)
    Special handling for hyphenated Pokemon like Porygon-Z, Ho-Oh
    """
    from config import POKEMON_NAME_PATTERNS
    
    parts = deck_name.split('-')
    result = []
    i = 0
    
    # Get Pokemon names that should preserve hyphens
    PRESERVE_HYPHENS = POKEMON_NAME_PATTERNS.get('PRESERVE_HYPHENS', [])
    SPECIAL_CASING = POKEMON_NAME_PATTERNS.get('SPECIAL_CASING', {})
    
    while i < len(parts):
        part = parts[i]
        
        if is_set_code(part):
            # Format set code: A3b format
            formatted = format_set_code(part)
            if result and not result[-1].endswith(')'):
                result[-1] += f" ({formatted})"
            i += 1
        else:
            # Check if this starts a multi-word Pokemon that preserves hyphens
            matched_pokemon = None
            for preserve_name in PRESERVE_HYPHENS:
                preserve_parts = preserve_name.split('-')
                # Check if we have enough parts remaining
                if i + len(preserve_parts) <= len(parts):
                    # Check if parts match
                    candidate = '-'.join(parts[i:i+len(preserve_parts)]).lower()
                    if candidate == preserve_name:
                        matched_pokemon = preserve_name
                        word_count = len(preserve_parts)
                        break
            
            if matched_pokemon:
                # Use special casing if available, otherwise title case with hyphen
                if matched_pokemon in SPECIAL_CASING:
                    word = SPECIAL_CASING[matched_pokemon]
                else:
                    word = '-'.join([p.title() for p in matched_pokemon.split('-')])
                
                # Check for suffixes (ex, v, etc.)
                suffix_start = i + word_count
                if suffix_start < len(parts) and parts[suffix_start].lower() in ['ex', 'v', 'vmax', 'vstar', 'gx']:
                    word += f" {parts[suffix_start].lower()}"
                    word_count += 1
                
                # Check if next part after Pokemon is a set code
                set_idx = i + word_count
                if set_idx < len(parts) and is_set_code(parts[set_idx]):
                    set_code = parts[set_idx]
                    formatted = format_set_code(set_code)
                    word += " " # f" ({formatted})"
                    i = set_idx + 1
                else:
                    i += word_count
                
                result.append(word)
            else:
                # Normal single word processing
                word = part.title()
                
                # Check if next part is a set code
                if i + 1 < len(parts) and is_set_code(parts[i + 1]):
                    set_code = parts[i + 1]
                    formatted = format_set_code(set_code)
                    word += " " # f" ({formatted})"
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
    from config import POKEMON_URL_EXCEPTIONS, POKEMON_URL_SUFFIXES
    from image_processor import extract_pokemon_from_deck_name
    
    # Use the unified Pokemon extraction function
    pokemon_names = extract_pokemon_from_deck_name(deck_name)
    
    # Convert spaces back to hyphens and make lowercase for URL generation
    pokemon_names = [name.lower().replace(' ', '-') for name in pokemon_names]
    
    # Remove Pokemon suffixes (ex, v, vmax, vstar, gx, sp)
    cleaned_names = []
    for name in pokemon_names:
        # Split by hyphens to check each part
        parts = name.split('-')
        # Filter out suffixes
        filtered_parts = [part for part in parts if part not in POKEMON_URL_SUFFIXES]
        # Rejoin with hyphens
        cleaned_name = '-'.join(filtered_parts)
        cleaned_names.append(cleaned_name)
    
    pokemon_names = cleaned_names
    
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
        
    return urls[0], urls[1]
