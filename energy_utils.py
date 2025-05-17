# energy_utils.py
"""Utility functions for handling energy types"""
import streamlit as st
import json
import os
from datetime import datetime

# Constants
ENERGY_CACHE_FILE = "cached_data/energy_types.json"

def initialize_energy_types():
    """Initialize energy types dictionary in session state if not exists"""
    if 'archetype_energy_types' not in st.session_state:
        st.session_state.archetype_energy_types = {}
        
    if 'archetype_first_energy_combo' not in st.session_state:
        st.session_state.archetype_first_energy_combo = {}
        
    # Load energy types from disk if available
    load_energy_types_from_disk()

def get_archetype_from_deck_name(deck_name):
    """Extract archetype name from deck name"""
    return deck_name.split('-')[0] if '-' in deck_name else deck_name
    
def get_energy_types_for_deck(deck_name, deck_energy_types):
    """
    Get energy types for a deck, falling back to the first energy combo
    found for the archetype or all energy types if needed
    
    Returns:
        Tuple of (energy_types, is_typical)
    """
    # If deck has energy types, use them
    if deck_energy_types:
        return deck_energy_types, False
    
    # Check if session state has the required dictionaries
    if 'archetype_first_energy_combo' not in st.session_state or 'archetype_energy_types' not in st.session_state:
        initialize_energy_types()
    
    # Get archetype name
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Try to get the first energy combo for this archetype
    if archetype in st.session_state.archetype_first_energy_combo:
        return st.session_state.archetype_first_energy_combo[archetype], True
    
    # Fall back to all energy types if no first combo available
    if archetype in st.session_state.archetype_energy_types:
        return list(st.session_state.archetype_energy_types[archetype]), True
    
    # No energy types found
    return [], False

def track_energy_combination(deck_name, energy_types):
    """
    Track unique energy combinations and their counts for each archetype
    """
    if not energy_types:
        return
    
    # Initialize if doesn't exist
    if 'archetype_energy_combos' not in st.session_state:
        st.session_state.archetype_energy_combos = {}
    
    # Get archetype name
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Initialize archetype entry if needed
    if archetype not in st.session_state.archetype_energy_combos:
        st.session_state.archetype_energy_combos[archetype] = {}
    
    # Sort the energy types to ensure consistent combo keys
    combo_key = tuple(sorted(energy_types))
    
    # Increment count for this combo
    if combo_key in st.session_state.archetype_energy_combos[archetype]:
        st.session_state.archetype_energy_combos[archetype][combo_key] += 1
    else:
        st.session_state.archetype_energy_combos[archetype][combo_key] = 1
    
    # Save the updated combinations to disk
    save_energy_types_to_disk()

# Update store_energy_types to also track combinations
def store_energy_types(deck_name, energy_types):
    """
    Store energy types for an archetype in the session state,
    preserving the first energy combination found
    """
    if not energy_types:
        return
    
    # Initialize if doesn't exist
    if 'archetype_energy_types' not in st.session_state:
        st.session_state.archetype_energy_types = {}
    
    if 'archetype_first_energy_combo' not in st.session_state:
        st.session_state.archetype_first_energy_combo = {}
    
    # Get archetype name
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Store in the main collection
    if archetype not in st.session_state.archetype_energy_types:
        st.session_state.archetype_energy_types[archetype] = set()
    
    for energy in energy_types:
        st.session_state.archetype_energy_types[archetype].add(energy)
    
    # Store as first energy combination if not already present
    if archetype not in st.session_state.archetype_first_energy_combo and energy_types:
        # Store a copy of the list to prevent modification
        st.session_state.archetype_first_energy_combo[archetype] = list(energy_types)
    
    # Track this combination for statistics
    track_energy_combination(deck_name, energy_types)
    
    # Save to disk
    save_energy_types_to_disk()

# Update save_energy_types_to_disk to include the combinations
def save_energy_types_to_disk():
    """Save energy types to disk for persistence between sessions"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(ENERGY_CACHE_FILE), exist_ok=True)
        
        # Create a serializable representation of the data
        data_to_save = {
            'archetype_energy_types': {k: list(v) for k, v in st.session_state.archetype_energy_types.items()},
            'archetype_first_energy_combo': st.session_state.archetype_first_energy_combo,
            'archetype_energy_combos': {
                k: {','.join(sorted(combo)): count for combo, count in v.items()} 
                for k, v in st.session_state.get('archetype_energy_combos', {}).items()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to file
        with open(ENERGY_CACHE_FILE, 'w') as f:
            json.dump(data_to_save, f)
            
    except Exception as e:
        print(f"Error saving energy types to disk: {e}")

# Update load_energy_types_from_disk to load combinations
def load_energy_types_from_disk():
    """Load energy types from disk"""
    try:
        if os.path.exists(ENERGY_CACHE_FILE):
            with open(ENERGY_CACHE_FILE, 'r') as f:
                data = json.load(f)
            
            # Convert lists back to sets for archetype_energy_types
            st.session_state.archetype_energy_types = {
                k: set(v) for k, v in data.get('archetype_energy_types', {}).items()
            }
            
            # Load first energy combinations
            st.session_state.archetype_first_energy_combo = data.get('archetype_first_energy_combo', {})
            
            # Load energy combinations statistics
            combo_data = data.get('archetype_energy_combos', {})
            st.session_state.archetype_energy_combos = {}
            
            for archetype, combos in combo_data.items():
                st.session_state.archetype_energy_combos[archetype] = {
                    tuple(sorted(combo.split(','))): count 
                    for combo, count in combos.items()
                }
            
            print(f"Loaded energy types from disk: {len(st.session_state.archetype_first_energy_combo)} archetypes")
            
    except Exception as e:
        print(f"Error loading energy types from disk: {e}")
        # Initialize empty if loading fails
        st.session_state.archetype_energy_types = {}
        st.session_state.archetype_first_energy_combo = {}
        st.session_state.archetype_energy_combos = {}

# Add this new function to display energy combo statistics
def display_energy_stats(archetype):
    """
    Display energy combination statistics for an archetype
    
    Returns:
        HTML string with a table of energy combinations and counts
    """
    if 'archetype_energy_combos' not in st.session_state:
        return ""
    
    if archetype not in st.session_state.archetype_energy_combos:
        return ""
    
    # Get combinations and sort by count (descending)
    combos = st.session_state.archetype_energy_combos[archetype]
    
    if not combos:
        return ""
    
    # Sort combinations by count (descending)
    sorted_combos = sorted(combos.items(), key=lambda x: x[1], reverse=True)
    
    # Create HTML table
    table_html = """
    <div style="margin-top: 10px; margin-bottom: 15px;">
        <p style="font-size: 0.85rem; margin-bottom: 5px;"><strong>Energy Combinations Found:</strong></p>
        <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
            <tr style="border-bottom: 1px solid #ddd;">
                <th style="text-align: left; padding: 4px;">Energy</th>
                <th style="text-align: right; padding: 4px;">Count</th>
            </tr>
    """
    
    # Add rows for each combination
    for combo, count in sorted_combos:
        # Generate energy icons
        energy_html = ""
        for energy in combo:
            energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
            energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:16px; margin-right:3px; vertical-align:middle;">'
        
        # Add row to table
        table_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="text-align: left; padding: 4px;">{energy_html}</td>
                <td style="text-align: right; padding: 4px;">{count}</td>
            </tr>
        """
    
    table_html += """
        </table>
    </div>
    """
    
    return table_html

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
