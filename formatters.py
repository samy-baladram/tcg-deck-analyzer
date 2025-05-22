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
                word += f" ({formatted})"
                i += 2
            else:
                i += 1
                
            result.append(word)
    
    return ' '.join(result)

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
def extract_pokemon_urls(displayed_name):
    # Remove content in parentheses and clean
    clean_name = re.sub(r'\([^)]*\)', '', displayed_name).strip()
    
    # Split by spaces and slashes
    parts = re.split(r'[\s/]+', clean_name)
    
    # Filter out suffixes
    suffixes = ['ex', 'v', 'vmax', 'vstar', 'gx']
    pokemon_names = []
    
    for part in parts:
        part = part.lower()
        if part and part not in suffixes:
            # Apply exceptions
            if part in POKEMON_EXCEPTIONS:
                part = POKEMON_EXCEPTIONS[part]
            
            pokemon_names.append(part)
            
            # Limit to 2 Pokémon
            if len(pokemon_names) >= 2:
                break
    
    # Create URLs
    urls = []
    for name in pokemon_names:
        urls.append(f"https://r2.limitlesstcg.net/pokemon/gen9/{name}.png")
        
    # Ensure we have exactly 2 elements
    while len(urls) < 2:
        urls.append(None)
        
    return urls[0], urls[1]  # Return as separate values

def displayed_name_to_markdown(displayed_name):
    """
    Convert displayed deck name to markdown format with Pokemon images
    
    Args:
        displayed_name: The deck name to extract Pokemon from
        
    Returns:
        str: Markdown formatted string with Pokemon images
    """
    # Get URLs using the existing function
    url1, url2 = extract_pokemon_urls(displayed_name)
    
    # Extract Pokemon names for alt text (reuse logic from extract_pokemon_urls)
    clean_name = re.sub(r'\([^)]*\)', '', displayed_name).strip()
    parts = re.split(r'[\s/]+', clean_name)
    suffixes = ['ex', 'v', 'vmax', 'vstar', 'gx']
    pokemon_names = []
    
    for part in parts:
        part_lower = part.lower()
        if part_lower and part_lower not in suffixes:
            if part_lower in POKEMON_EXCEPTIONS:
                part_lower = POKEMON_EXCEPTIONS[part_lower]
            pokemon_names.append(part.title())  # Keep original case for display
            if len(pokemon_names) >= 2:
                break
    
    # Build markdown string
    markdown_parts = []
    
    if url1:
        name1 = pokemon_names[0] if len(pokemon_names) > 0 else "Pokemon1"
        markdown_parts.append(f"![{name1}]({url1})")
    
    if url2:
        name2 = pokemon_names[1] if len(pokemon_names) > 1 else "Pokemon2"
        markdown_parts.append(f"![{name2}]({url2})")
    
    return " ".join(markdown_parts)
