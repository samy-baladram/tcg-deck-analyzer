# formatters.py
"""Text formatting functions for the TCG Deck Analyzer"""

import re
from utils import is_set_code, format_set_code

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
