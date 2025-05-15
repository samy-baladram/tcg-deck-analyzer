# utils.py
"""Utility functions for the TCG Deck Analyzer"""

from datetime import datetime, timedelta
import re

def calculate_time_ago(fetch_time):
    """Calculate human-readable time difference"""
    time_diff = datetime.now() - fetch_time
    
    if time_diff < timedelta(minutes=1):
        return "just now"
    elif time_diff < timedelta(hours=1):
        minutes = int(time_diff.total_seconds() / 60)
        return f"{minutes} minutes ago"
    else:
        hours = int(time_diff.total_seconds() / 3600)
        return f"{hours} hours ago"

def is_set_code(part):
    """Check if a string matches the set code pattern"""
    set_pattern = re.compile(r'^[a-z]\d+[a-z]?$', re.IGNORECASE)
    return bool(set_pattern.match(part))

def format_set_code(set_code):
    """Format set code to standard format (e.g., 'a3b' -> 'A3b')"""
    if not set_code:
        return set_code
    return set_code[0].upper() + set_code[1:].lower()

def calculate_deck_space(pokemon_count, trainer_count):
    """Calculate remaining deck space (20 cards total)"""
    return 20 - (pokemon_count + trainer_count)

def is_flexible_core(card):
    """Determine if a card is flexible core based on usage patterns"""
    from config import FLEXIBLE_CORE_THRESHOLD
    return ((card['pct_1'] >= FLEXIBLE_CORE_THRESHOLD and card['majority'] == 2) or 
            (card['pct_2'] >= FLEXIBLE_CORE_THRESHOLD and card['majority'] == 1))

def calculate_display_usage(card):
    """Calculate display usage for flexible core cards"""
    return min(card['pct_1'], card['pct_2']) if card['category'] == 'Core' else card['pct_total']

def format_card_display(card_name, set_code, num):
    """Format card display with set info"""
    if set_code:
        return f"{card_name} ({set_code}-{num})"
    return card_name

def extract_share_from_display(display_name):
    """Extract share percentage from display name"""
    match = re.search(r'(\d+\.\d+)%', display_name)
    if match:
        return float(match.group(1))
    return 0.0
