# energy_utils.py
"""Utility functions for handling energy types"""

import streamlit as st
from collections import Counter

def initialize_energy_types():
    """Initialize energy types dictionary in session state if not exists"""
    if 'archetype_energy_types' not in st.session_state:
        st.session_state.archetype_energy_types = {}
    
    # Initialize energy combinations counter if not exists
    if 'archetype_energy_combinations' not in st.session_state:
        st.session_state.archetype_energy_combinations = {}

def get_archetype_from_deck_name(deck_name):
    """Extract archetype name from deck name"""
    return deck_name.split('-')[0] if '-' in deck_name else deck_name

def store_energy_types(deck_name, energy_types):
    """Store energy types for an archetype in the session state"""
    if not energy_types:
        return
    
    # Limit to top 3 energy types max (TCG Pocket decks can have at most 3)
    energy_types = energy_types[:3]
    
    # Create a frozen set (immutable) of the energy types for this deck
    energy_set = frozenset(energy_types)
    
    # Get the archetype
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Initialize archetype entry if not exists
    if archetype not in st.session_state.archetype_energy_combinations:
        st.session_state.archetype_energy_combinations[archetype] = Counter()
    
    # Increment the count for this specific energy combination
    st.session_state.archetype_energy_combinations[archetype][energy_set] += 1
    
    # Also store individual energies for backwards compatibility
    if archetype not in st.session_state.archetype_energy_types:
        st.session_state.archetype_energy_types[archetype] = set()
    
    for energy in energy_types:
        st.session_state.archetype_energy_types[archetype].add(energy)

def get_energy_types_for_deck(deck_name, deck_energy_types):
    """
    Get energy types for a deck, with fallback options to ensure something is displayed
    
    Returns:
        Tuple of (energy_types, is_typical)
    """
    # If deck has energy types, use them directly (most reliable)
    if deck_energy_types:
        return deck_energy_types, False
    
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Try approach 1: Most common specific combination for this archetype
    if archetype in st.session_state.archetype_energy_combinations:
        combinations = st.session_state.archetype_energy_combinations[archetype]
        
        if combinations:
            # Filter out empty combinations
            valid_combinations = [(combo, count) for combo, count in combinations.items() if combo]
            
            if valid_combinations:
                most_common_combo, _ = max(valid_combinations, key=lambda x: x[1])
                return list(most_common_combo), True
    
    # Try approach 2: All energy types for this archetype (up to 3)
    if archetype in st.session_state.archetype_energy_types:
        all_energies = list(st.session_state.archetype_energy_types[archetype])
        if all_energies:
            return all_energies[:3], True
    
    # Try approach 3: Find related archetypes by name prefix (first 3-5 chars)
    prefix = archetype[:min(5, len(archetype))]
    related_archetypes = [a for a in st.session_state.archetype_energy_types.keys() 
                          if a.startswith(prefix) and a != archetype]
    
    # Collect all energy types from related archetypes
    all_related_energies = set()
    for related in related_archetypes:
        if related in st.session_state.archetype_energy_types:
            all_related_energies.update(st.session_state.archetype_energy_types[related])
    
    if all_related_energies:
        return list(all_related_energies)[:3], True
    
    # Try approach 4: If all else fails, return the 3 most common energy types overall
    if st.session_state.archetype_energy_types:
        # Count occurrences of each energy type across all archetypes
        energy_counter = Counter()
        for archetype_energies in st.session_state.archetype_energy_types.values():
            for energy in archetype_energies:
                energy_counter[energy] += 1
        
        # Get the 3 most common energy types
        if energy_counter:
            common_energies = [energy for energy, _ in energy_counter.most_common(3)]
            if common_energies:
                return common_energies, True
    
    # Absolute last resort: No energy data anywhere, return empty list
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
