# energy_utils.py
"""Utility functions for handling energy types"""

import streamlit as st

def initialize_energy_types():
    """Initialize energy types dictionary in session state if not exists"""
    if 'archetype_energy_types' not in st.session_state:
        st.session_state.archetype_energy_types = {}
    
    # New dictionary to store first energy combination for each archetype
    if 'archetype_first_energy_combo' not in st.session_state:
        st.session_state.archetype_first_energy_combo = {}

def get_archetype_from_deck_name(deck_name):
    """Extract archetype name from deck name"""
    return deck_name.split('-')[0] if '-' in deck_name else deck_name

def store_energy_types(deck_name, energy_types):
    """
    Store energy types for an archetype in the session state,
    preserving the first energy combination found for each archetype
    """
    # Skip if no energy types
    if not energy_types:
        return
    
    # Extract archetype name
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Store in the original collection (for backward compatibility)
    if archetype not in st.session_state.archetype_energy_types:
        st.session_state.archetype_energy_types[archetype] = set()
    
    for energy in energy_types:
        st.session_state.archetype_energy_types[archetype].add(energy)
    
    # Store as first energy combination if not already present
    if archetype not in st.session_state.archetype_first_energy_combo and energy_types:
        # Store a copy of the list to prevent modification
        st.session_state.archetype_first_energy_combo[archetype] = list(energy_types)

def get_energy_types_for_deck(deck_name, deck_energy_types):
    """
    Get energy types for a deck, falling back to the first energy combo found for the archetype
    
    Returns:
        Tuple of (energy_types, is_typical)
    """
    # If this specific deck has energy types directly, use them
    if deck_energy_types:
        return deck_energy_types, False
    
    # Otherwise try to get the first energy combo found for this archetype
    archetype = get_archetype_from_deck_name(deck_name)
    
    # First priority: use the first energy combo found for this archetype
    if 'archetype_first_energy_combo' in st.session_state and archetype in st.session_state.archetype_first_energy_combo:
        return st.session_state.archetype_first_energy_combo[archetype], True
    
    # Fallback: use all energy types if no first combo available (backward compatibility)
    if archetype in st.session_state.archetype_energy_types:
        return list(st.session_state.archetype_energy_types[archetype]), True
    
    # Nothing found
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
