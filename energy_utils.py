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
    
# In energy_utils.py - Modified get_energy_types_for_deck function
def get_energy_types_for_deck(deck_name, deck_energy_types):
    """
    Get energy types for a deck, prioritizing the most common combination
    for the archetype when specific deck energy types aren't available
    
    Returns:
        Tuple of (energy_types, is_typical)
    """
    # If deck has specific energy types, use them (most accurate)
    if deck_energy_types:
        return deck_energy_types, False
    
    # Get archetype name
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Check for energy combinations (most reliable source)
    if 'archetype_energy_combos' in st.session_state and archetype in st.session_state.archetype_energy_combos:
        combos = st.session_state.archetype_energy_combos[archetype]
        if combos:
            # Find the most common combination
            most_common_combo = max(combos.items(), key=lambda x: x[1])[0]
            return list(most_common_combo), True
    
    # Fall back to first energy combo if no combination stats yet
    if 'archetype_first_energy_combo' in st.session_state and archetype in st.session_state.archetype_first_energy_combo:
        return st.session_state.archetype_first_energy_combo[archetype], True
    
    # Last resort - use all energy types found
    if 'archetype_energy_types' in st.session_state and archetype in st.session_state.archetype_energy_types:
        return list(st.session_state.archetype_energy_types[archetype]), True
    
    # No energy types found
    return [], False

# In energy_utils.py - Enhanced track_energy_combination function
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
    
    # Log for debugging (optional)
    # print(f"Tracked energy combo for {archetype}: {combo_key} (count: {st.session_state.archetype_energy_combos[archetype][combo_key]})")

# Update store_energy_types to also track combinations

# In energy_utils.py - Update store_energy_types function
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
    
    # Add energy types to the set
    for energy in energy_types:
        st.session_state.archetype_energy_types[archetype].add(energy)
    
    # Store as first energy combination if not already present
    if archetype not in st.session_state.archetype_first_energy_combo and energy_types:
        # Sort the energy types for consistency
        st.session_state.archetype_first_energy_combo[archetype] = sorted(list(energy_types))
    
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
    with improved visual indication of the most common combination
    
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
    most_common_count = sorted_combos[0][1] if sorted_combos else 0
    
    # Create HTML table
    table_html = """<div style="margin-top: 10px; margin-bottom: 15px;">
        <p style="font-size: 0.85rem; margin-bottom: 5px;"><strong>Energy Combinations Found:</strong></p>
        <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
            <tr style="border-bottom: 1px solid #ddd;">
                <th style="text-align: left; padding: 4px;">Energy</th>
                <th style="text-align: right; padding: 4px;">Count</th>
            </tr>"""
    
    # Add rows for each combination
    for combo, count in sorted_combos:
        # Generate energy icons
        energy_html = ""
        for energy in combo:
            energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
            energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:16px; margin-right:3px; vertical-align:middle;">'
        
        # Highlight most common combination
        is_most_common = (count == most_common_count)
        row_style = 'background-color: rgba(0, 160, 255, 0.1);' if is_most_common else ''
        
        # Add row to table
        table_html += f"""<tr style="border-bottom: 1px solid #eee; {row_style}">
                <td style="text-align: left; padding: 4px;">{energy_html}{' (most common)' if is_most_common else ''}</td>
                <td style="text-align: right; padding: 4px;">{count}</td>
            </tr>"""
    
    table_html += """</table></div>"""
    
    return table_html

# In energy_utils.py - Updated render_energy_icons function
# In energy_utils.py
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
    
    # Add a more descriptive note if these are typical energy types
    archetype_note = '<span style="font-size: 0.8rem; color: #888; margin-left: 4px;">(most common)</span>' if is_typical else ""
    
    energy_display = f"""<div style="margin-bottom: 10px;">
        <p style="margin-bottom:5px;"><strong>Energy:</strong> {energy_html} {archetype_note}</p>
    </div>"""
    return energy_display

# Add to energy_utils.py
def track_per_deck_energy(deck_name, deck_num, energy_types):
    """
    Track energy types for each individual deck
    
    Parameters:
        deck_name: Name of the deck archetype
        deck_num: Unique identifier for this specific deck instance
        energy_types: List of energy types found in this deck
    """
    # Initialize if needed
    if 'per_deck_energy' not in st.session_state:
        st.session_state.per_deck_energy = {}
    
    # Get archetype
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Initialize archetype entry if needed
    if archetype not in st.session_state.per_deck_energy:
        st.session_state.per_deck_energy[archetype] = {}
    
    # Store energy for this specific deck
    deck_key = f"{deck_name}-{deck_num}"
    st.session_state.per_deck_energy[archetype][deck_key] = list(energy_types)

# Add to energy_utils.py
# In energy_utils.py
def display_detailed_energy_table(deck_name):
    """
    Display a detailed table of energy types found in each deck for an archetype
    
    Parameters:
        deck_name: Name of the deck archetype
        
    Returns:
        HTML string with the table
    """
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Check if we have energy data first
    if 'archetype_energy_combos' not in st.session_state or archetype not in st.session_state.archetype_energy_combos:
        return "<p>No detailed energy data available for this archetype. Try analyzing the deck to collect energy data.</p>"
    
    # Check for per-deck energy data
    has_per_deck_data = ('per_deck_energy' in st.session_state and 
                         archetype in st.session_state.per_deck_energy and 
                         st.session_state.per_deck_energy[archetype])
    
    # If we have detailed deck data, show the deck-by-deck table
    if has_per_deck_data:
        # Get all unique energy types for this archetype
        all_energies = set()
        for energies in st.session_state.per_deck_energy[archetype].values():
            all_energies.update(energies)
        
        # Sort energy types alphabetically for consistent display
        all_energies = sorted(all_energies)
        
        # Create the table header
        table_html = """
        <div style="margin-top: 15px;">
            <h5 style="margin-bottom: 10px;">Detailed Energy Analysis by Deck</h5>
            <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #ddd;">
                    <th style="text-align: left; padding: 4px;">Deck #</th>
        """
        
        # Add energy type headers
        for energy in all_energies:
            energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
            table_html += f'<th style="text-align: center; padding: 4px;"><img src="{energy_url}" alt="{energy}" style="height:16px;"></th>'
        
        table_html += "</tr>"
        
        # Add a row for each deck
        for deck_key, energies in sorted(st.session_state.per_deck_energy[archetype].items()):
            # Extract deck number from key
            deck_num = deck_key.split('-')[-1]
            
            table_html += f"""
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="text-align: left; padding: 4px;">{deck_num}</td>
            """
            
            # For each possible energy type, check if this deck has it
            for energy in all_energies:
                has_energy = energy in energies
                check_mark = "✓" if has_energy else ""
                bg_color = "rgba(0, 160, 255, 0.1)" if has_energy else "transparent"
                
                table_html += f'<td style="text-align: center; padding: 4px; background-color: {bg_color};">{check_mark}</td>'
            
            table_html += "</tr>"
        
        # Close the table
        table_html += """
            </table>
        </div>
        """
    else:
        # If no per-deck data, show a message
        table_html = """
        <div style="margin-top: 15px;">
            <p>No per-deck energy data available. Only energy combination statistics are shown.</p>
        </div>
        """
    
    # Calculate and show energy combination statistics
    combo_stats = {}
    if archetype in st.session_state.archetype_energy_combos:
        combo_stats = st.session_state.archetype_energy_combos[archetype]
    
    # Sort combinations by frequency
    sorted_combos = sorted(combo_stats.items(), key=lambda x: x[1], reverse=True)
    
    # Add combo statistics
    table_html += """
    <div style="margin-top: 15px;">
        <h5 style="margin-bottom: 10px;">Energy Combinations</h5>
        <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
            <tr style="border-bottom: 1px solid #ddd;">
                <th style="text-align: left; padding: 4px;">Energy Combination</th>
                <th style="text-align: right; padding: 4px; width: 80px;">Count</th>
                <th style="text-align: right; padding: 4px; width: 80px;">Percentage</th>
            </tr>
    """
    
    total_decks = sum(combo_stats.values()) if combo_stats else 0
    
    for combo, count in sorted_combos:
        # Generate energy icons
        energy_html = ""
        for energy in combo:
            energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
            energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:16px; margin-right:3px; vertical-align:middle;">'
        
        percentage = (count / total_decks * 100) if total_decks > 0 else 0
        
        # Highlight the most common combination
        is_most_common = combo == sorted_combos[0][0] if sorted_combos else False
        row_style = 'background-color: rgba(0, 160, 255, 0.1);' if is_most_common else ''
        
        table_html += f"""
            <tr style="border-bottom: 1px solid #eee; {row_style}">
                <td style="text-align: left; padding: 4px;">{energy_html}{' <strong>(most common)</strong>' if is_most_common else ''}</td>
                <td style="text-align: right; padding: 4px;">{count}</td>
                <td style="text-align: right; padding: 4px;">{percentage:.1f}%</td>
            </tr>
        """
    
    table_html += """
        </table>
    </div>
    """
    
    return table_html
    
# Add to energy_utils.py
def debug_energy_combinations(deck_name):
    """
    Debug function to print all energy combinations for a given deck
    """
    archetype = get_archetype_from_deck_name(deck_name)
    
    print(f"DEBUG - Energy for {deck_name} (archetype: {archetype}):")
    
    if 'archetype_energy_types' in st.session_state and archetype in st.session_state.archetype_energy_types:
        print(f"  All Energy Types: {st.session_state.archetype_energy_types[archetype]}")
    
    if 'archetype_first_energy_combo' in st.session_state and archetype in st.session_state.archetype_first_energy_combo:
        print(f"  First Energy Combo: {st.session_state.archetype_first_energy_combo[archetype]}")
    
    if 'archetype_energy_combos' in st.session_state and archetype in st.session_state.archetype_energy_combos:
        print(f"  Energy Combinations:")
        for combo, count in st.session_state.archetype_energy_combos[archetype].items():
            print(f"    {combo}: {count}")
            
    if 'per_deck_energy' in st.session_state and archetype in st.session_state.per_deck_energy:
        deck_count = len(st.session_state.per_deck_energy[archetype])
        print(f"  Per-Deck Energy Data ({deck_count} decks):")
        for i, (deck_key, energies) in enumerate(st.session_state.per_deck_energy[archetype].items()):
            if i < 5:  # Show just the first 5 decks to avoid clutter
                print(f"    Deck {deck_key}: {energies}")
        if deck_count > 5:
            print(f"    ... and {deck_count - 5} more decks")
