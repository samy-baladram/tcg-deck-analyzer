# energy_utils.py
"""Utility functions for handling energy types"""

import streamlit as st
import random
from collections import defaultdict

def initialize_energy_types():
    """Initialize energy types dictionary in session state if not exists"""
    if 'archetype_energy_types' not in st.session_state:
        st.session_state.archetype_energy_types = {}
        
    if 'archetype_energy_combinations' not in st.session_state:
        st.session_state.archetype_energy_combinations = defaultdict(list)

def get_archetype_from_deck_name(deck_name):
    """Extract archetype name from deck name"""
    return deck_name.split('-')[0] if '-' in deck_name else deck_name

def store_energy_types(deck_name, energy_types):
    """
    Store energy types for a deck by archetype in the session state
    This version stores complete energy combinations, not just individual types
    """
    if not energy_types:
        return
        
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Store individual energy types (for backward compatibility)
    if archetype not in st.session_state.archetype_energy_types:
        st.session_state.archetype_energy_types[archetype] = set()
    
    for energy in energy_types:
        st.session_state.archetype_energy_types[archetype].add(energy)
    
    # Store the complete energy combination
    # Sort the energy types to ensure consistent combinations
    sorted_energy_types = sorted(energy_types)
    energy_combo = tuple(sorted_energy_types)  # Use tuple for hashability
    
    # Only add if it's a new combination
    if energy_combo not in st.session_state.archetype_energy_combinations[archetype]:
        st.session_state.archetype_energy_combinations[archetype].append(energy_combo)

def get_energy_types_for_deck(deck_name, deck_energy_types):
    """
    Get energy types for a deck, falling back to archetype energy combinations if needed
    
    Returns:
        Tuple of (energy_types, is_typical)
    """
    # If deck has energy types, use them
    if deck_energy_types:
        return deck_energy_types, False
    
    # Otherwise, try to get a valid combination from the archetype
    archetype = get_archetype_from_deck_name(deck_name)
    
    # If we have stored combinations, pick a random valid one
    if archetype in st.session_state.archetype_energy_combinations and st.session_state.archetype_energy_combinations[archetype]:
        # Pick a random valid combination
        energy_combo = random.choice(st.session_state.archetype_energy_combinations[archetype])
        return list(energy_combo), True
    
    # Fallback: if we have individual types but no combinations
    if archetype in st.session_state.archetype_energy_types and st.session_state.archetype_energy_types[archetype]:
        # Limit to 3 random energy types maximum (since that's the game limit)
        energy_types = list(st.session_state.archetype_energy_types[archetype])
        if len(energy_types) > 3:
            energy_types = random.sample(energy_types, 3)
        return energy_types, True
    
    # No energy types found
    return [], False

def render_energy_icons(energy_types, is_typical=False):
    """Generate HTML for energy icons"""
    if not energy_types:
        return ""
        
    energy_html = ""
    # Create image tags for each energy type
    for energy in energy_types:
        # Direct URL to the energy icon
        energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
        energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:20px; margin-right:4px; vertical-align:middle;">'
    
    # Add note if these are typical energy types
    archetype_note = '<span style="font-size: 0.8rem; color: #888; margin-left: 4px;">(typical)</span>' if is_typical else ""
    
    energy_display = f"""
    <div style="margin-bottom: 10px;">
        <p style="margin-bottom:5px;"><strong>Energy:</strong> {energy_html} {archetype_note}</p>
    </div>
    """
    return energy_display
