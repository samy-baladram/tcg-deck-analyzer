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
    Get energy types for a deck, with multiple fallback options to ensure something is shown
    
    Returns:
        Tuple of (energy_types, is_typical)
    """
    # If deck has energy types, use them directly
    if deck_energy_types:
        return deck_energy_types, False
    
    # Get the archetype
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Fallback 1: Try to get the most common energy combination
    if archetype in st.session_state.archetype_energy_combinations:
        combinations = st.session_state.archetype_energy_combinations[archetype]
        
        if combinations:
            # Filter out empty combinations
            valid_combinations = [(combo, count) for combo, count in combinations.items() if combo]
            
            if valid_combinations:
                most_common_combo, _ = max(valid_combinations, key=lambda x: x[1])
                return list(most_common_combo), True
    
    # Fallback 2: Use any non-empty energy combination from the counter
    if archetype in st.session_state.archetype_energy_combinations:
        for combo, count in st.session_state.archetype_energy_combinations[archetype].items():
            if combo:  # If not empty
                return list(combo), True
    
    # Fallback 3: Use the individual energy types collection
    if archetype in st.session_state.archetype_energy_types:
        all_energies = list(st.session_state.archetype_energy_types[archetype])
        if all_energies:
            # Limit to 3 energies to be consistent with TCG Pocket rules
            return all_energies[:3], True
    
    # Fallback 4: Check for similar archetypes (first word match)
    archetype_first_word = archetype.split('-')[0] if '-' in archetype else archetype
    
    # Look for archetypes with the same first word
    for other_archetype in st.session_state.archetype_energy_types:
        other_first_word = other_archetype.split('-')[0] if '-' in other_archetype else other_archetype
        
        if archetype_first_word == other_first_word and archetype != other_archetype:
            all_energies = list(st.session_state.archetype_energy_types[other_archetype])
            if all_energies:
                # Mark as typical with higher uncertainty
                return all_energies[:3], True
    
    # No energy types found after all fallbacks
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
