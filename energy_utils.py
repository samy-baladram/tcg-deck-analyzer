# # energy_utils.py
# """Utility functions for handling energy types"""
# import streamlit as st
# import json
# import os
# from datetime import datetime

# # Constants
# ENERGY_CACHE_FILE = "cached_data/energy_types.json"

# def initialize_energy_types():
#     """Initialize energy types dictionary in session state if not exists"""
#     if 'archetype_energy_types' not in st.session_state:
#         st.session_state.archetype_energy_types = {}
        
#     if 'archetype_first_energy_combo' not in st.session_state:
#         st.session_state.archetype_first_energy_combo = {}
        
#     if 'archetype_energy_combos' not in st.session_state:
#         st.session_state.archetype_energy_combos = {}
        
#     # Load energy types from disk if available
#     load_energy_types_from_disk()
    
#     # Ensure most_common combinations are set correctly
#     update_most_common_combinations()

# def update_most_common_combinations():
#     """Update most common energy combinations for all archetypes"""
#     if 'archetype_energy_combos' not in st.session_state:
#         return
        
#     # For each archetype with combo data
#     for archetype, combos in st.session_state.archetype_energy_combos.items():
#         if not combos:
#             continue
            
#         # Find the most common combo
#         most_common = max(combos.items(), key=lambda x: x[1])[0]
        
#         # Update first_energy_combo to use the most common one
#         st.session_state.archetype_first_energy_combo[archetype] = list(most_common)

# def get_archetype_from_deck_name(deck_name):
#     """Extract archetype name from deck name"""
#     return deck_name#.split('-')[0] if '-' in deck_name else deck_name
    
# # In energy_utils.py - Modify get_energy_types_for_deck function
# def get_energy_types_for_deck(deck_name, deck_energy_types):
#     """
#     Get energy types for a deck, always using the most common combination
    
#     Returns:
#         Tuple of (energy_types, is_typical)
#     """
#     # If deck has specific energy types, use them
#     if deck_energy_types:
#         return deck_energy_types, False
    
#     # Get archetype name
#     archetype = get_archetype_from_deck_name(deck_name)
    
#     # Always use the most common energy combination from the stats
#     if 'archetype_energy_combos' in st.session_state and archetype in st.session_state.archetype_energy_combos:
#         combos = st.session_state.archetype_energy_combos[archetype]
#         if combos:
#             # Find the most common combination
#             most_common_combo = max(combos.items(), key=lambda x: x[1])[0]
#             return list(most_common_combo), True
    
#     # # If no combo stats, use all energy types as fallback
#     # if 'archetype_energy_types' in st.session_state and archetype in st.session_state.archetype_energy_types:
#     #     return list(st.session_state.archetype_energy_types[archetype]), True
    
#     # No energy types found
#     return [], False

# def track_energy_combination(deck_name, energy_types):
#     """Track unique energy combinations and their counts for each deck"""
#     if not energy_types:
#         return
    
#     # Initialize if doesn't exist
#     if 'archetype_energy_combos' not in st.session_state:
#         st.session_state.archetype_energy_combos = {}
    
#     # Get archetype (full deck name as per your design)
#     archetype = deck_name
    
#     # Initialize archetype entry if needed
#     if archetype not in st.session_state.archetype_energy_combos:
#         st.session_state.archetype_energy_combos[archetype] = {}
    
#     # Create a tuple from the energy types for use as a key
#     combo_key = tuple(sorted(energy_types))
    
#     # Increment count for this combo
#     if combo_key in st.session_state.archetype_energy_combos[archetype]:
#         st.session_state.archetype_energy_combos[archetype][combo_key] += 1
#     else:
#         st.session_state.archetype_energy_combos[archetype][combo_key] = 1
    
#     # Save to disk
#     save_energy_types_to_disk()

# # Update store_energy_types to also track combinations
# def store_energy_types(deck_name, energy_types):
#     """
#     Store energy types for an archetype in the session state
#     """
#     if not energy_types:
#         return
    
#     # Initialize if doesn't exist
#     if 'archetype_energy_types' not in st.session_state:
#         st.session_state.archetype_energy_types = {}
    
#     # Get archetype name
#     archetype = get_archetype_from_deck_name(deck_name)
    
#     # Store in the main collection
#     if archetype not in st.session_state.archetype_energy_types:
#         st.session_state.archetype_energy_types[archetype] = set()
    
#     for energy in energy_types:
#         st.session_state.archetype_energy_types[archetype].add(energy)
    
#     # Track this combination for statistics
#     track_energy_combination(deck_name, energy_types)
    
#     # Track per-deck energy
#     if 'deck_num' in st.session_state:
#         track_per_deck_energy(deck_name, st.session_state.deck_num, energy_types)
    
#     # Save to disk
#     save_energy_types_to_disk()

# # Update save_energy_types_to_disk to include the combinations
# # In energy_utils.py - Update save_energy_types_to_disk function
# def save_energy_types_to_disk():
#     """Save energy types to disk for persistence between sessions"""
#     try:
#         # Create directory if it doesn't exist
#         os.makedirs(os.path.dirname(ENERGY_CACHE_FILE), exist_ok=True)
        
#         # Create a serializable representation of the data
#         data_to_save = {
#             'archetype_energy_types': {k: list(v) for k, v in st.session_state.archetype_energy_types.items()},
#             'archetype_energy_combos': {
#                 k: {','.join(sorted(combo)): count for combo, count in v.items()} 
#                 for k, v in st.session_state.get('archetype_energy_combos', {}).items()
#             },
#             'per_deck_energy': {
#                 archetype: {
#                     deck_key: energy_list 
#                     for deck_key, energy_list in deck_data.items()
#                 }
#                 for archetype, deck_data in st.session_state.get('per_deck_energy', {}).items()
#             },
#             'timestamp': datetime.now().isoformat()
#         }
        
#         # Save to file
#         with open(ENERGY_CACHE_FILE, 'w') as f:
#             json.dump(data_to_save, f)
            
#     except Exception as e:
#         print(f"Error saving energy types to disk: {e}")

# # In energy_utils.py - Update load_energy_types_from_disk function
# def load_energy_types_from_disk():
#     """Load energy types from disk"""
#     try:
#         if os.path.exists(ENERGY_CACHE_FILE):
#             with open(ENERGY_CACHE_FILE, 'r') as f:
#                 data = json.load(f)
            
#             # Convert lists back to sets for archetype_energy_types
#             st.session_state.archetype_energy_types = {
#                 k: set(v) for k, v in data.get('archetype_energy_types', {}).items()
#             }
            
#             # Load energy combinations statistics
#             combo_data = data.get('archetype_energy_combos', {})
#             st.session_state.archetype_energy_combos = {}
            
#             for archetype, combos in combo_data.items():
#                 st.session_state.archetype_energy_combos[archetype] = {
#                     tuple(sorted(combo.split(','))): count 
#                     for combo, count in combos.items()
#                 }
            
#             # Load per-deck energy data
#             per_deck_data = data.get('per_deck_energy', {})
#             st.session_state.per_deck_energy = per_deck_data
            
#             print(f"Loaded energy types from disk: {len(st.session_state.archetype_energy_types)} archetypes")
            
#     except Exception as e:
#         print(f"Error loading energy types from disk: {e}")
#         # Initialize empty if loading fails
#         st.session_state.archetype_energy_types = {}
#         st.session_state.archetype_energy_combos = {}
#         st.session_state.per_deck_energy = {}

# # Add this new function to display energy combo statistics
# def display_energy_stats(archetype):
#     """
#     Display energy combination statistics for an archetype
#     with improved visual indication of the most common combination
    
#     Returns:
#         HTML string with a table of energy combinations and counts
#     """
#     if 'archetype_energy_combos' not in st.session_state:
#         return ""
    
#     if archetype not in st.session_state.archetype_energy_combos:
#         return ""
    
#     # Get combinations and sort by count (descending)
#     combos = st.session_state.archetype_energy_combos[archetype]
    
#     if not combos:
#         return ""
    
#     # Sort combinations by count (descending)
#     sorted_combos = sorted(combos.items(), key=lambda x: x[1], reverse=True)
#     most_common_count = sorted_combos[0][1] if sorted_combos else 0
    
#     # Create HTML table
#     table_html = """<div style="margin-top: 10px; margin-bottom: 15px;">
#         <p style="font-size: 0.85rem; margin-bottom: 5px;"><strong>Energy Combinations Found:</strong></p>
#         <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
#             <tr style="border-bottom: 1px solid #ddd;">
#                 <th style="text-align: left; padding: 4px;">Energy</th>
#                 <th style="text-align: right; padding: 4px;">Count</th>
#             </tr>"""
    
#     # Add rows for each combination
#     for combo, count in sorted_combos:
#         # Generate energy icons
#         energy_html = ""
#         for energy in combo:
#             energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
#             energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:16px; margin-right:3px; vertical-align:middle;">'
        
#         # Highlight most common combination
#         is_most_common = (count == most_common_count)
#         row_style = 'background-color: rgba(0, 160, 255, 0.1);' if is_most_common else ''
        
#         # Add row to table
#         table_html += f"""<tr style="border-bottom: 1px solid #eee; {row_style}">
#                 <td style="text-align: left; padding: 4px;">{energy_html}{' (most common)' if is_most_common else ''}</td>
#                 <td style="text-align: right; padding: 4px;">{count}</td></tr>"""
    
#     table_html += """</table></div>"""
    
#     return table_html

# def render_energy_icons(energy_types, is_typical=False):
#     """Generate HTML for energy icons"""
#     if not energy_types:
#         return ""
        
#     energy_html = ""
#     # Create image tags for each energy type
#     for energy in energy_types:
#         # Direct URL to the energy icon
#         energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
#         energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:20px; margin-right:4px; vertical-align:middle;">'
    
#     # Add note if these are typical energy types
#     archetype_note = ''
#     #archetype_note = '<span style="font-size: 0.8rem; color: #888; margin-left: 4px;">(most common)</span>' if is_typical else ""
    
#     energy_display = f"""<div style="margin-bottom: 10px;">
#         <p style="margin-bottom:5px;"><strong>Energy:</strong> {energy_html} {archetype_note}</p>
#     </div>"""
#     return energy_display

# # Add to energy_utils.py
# def track_per_deck_energy(deck_name, deck_num, energy_types):
#     """Track energy types for each individual deck"""
#     # Initialize if needed
#     if 'per_deck_energy' not in st.session_state:
#         st.session_state.per_deck_energy = {}
    
#     # Get archetype (full deck name as per your design)
#     archetype = deck_name
    
#     # Initialize archetype entry if needed
#     if archetype not in st.session_state.per_deck_energy:
#         st.session_state.per_deck_energy[archetype] = {}
    
#     # Ensure energy_types is sorted for consistency
#     sorted_energy = sorted(energy_types)
    
#     # Store energy for this specific deck
#     deck_key = f"{deck_name}-{deck_num}"
#     st.session_state.per_deck_energy[archetype][deck_key] = sorted_energy
    
#     # Also update energy combos table directly
#     track_energy_combination(deck_name, sorted_energy)

# # Add to energy_utils.py
# def display_detailed_energy_table(deck_name):
#     """
#     Display a detailed table of energy types found in each deck for an archetype
    
#     Parameters:
#         deck_name: Name of the deck archetype
        
#     Returns:
#         HTML string with the table
#     """
#     archetype = get_archetype_from_deck_name(deck_name)
    
#     # Check if we have per-deck energy data
#     if 'per_deck_energy' not in st.session_state or archetype not in st.session_state.per_deck_energy:
#         return "<p>No detailed energy data available for this archetype.</p>"
    
#     # Get all unique energy types for this archetype
#     all_energies = set()
#     for energies in st.session_state.per_deck_energy[archetype].values():
#         all_energies.update(energies)
    
#     # Sort energy types alphabetically for consistent display
#     all_energies = sorted(all_energies)
    
#     # Create the table header
#     table_html = """
#     <div style="margin-top: 15px;">
#         <h5 style="margin-bottom: 10px;">Detailed Energy Analysis</h5>
#         <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
#             <tr style="border-bottom: 1px solid #ddd;">
#                 <th style="text-align: left; padding: 4px;">Deck #</th>"""
    
#     # Add energy type headers
#     for energy in all_energies:
#         energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
#         table_html += f'<th style="text-align: center; padding: 4px;"><img src="{energy_url}" alt="{energy}" style="height:16px;"></th>'
    
#     table_html += "</tr>"
    
#     # Add a row for each deck
#     for deck_key, energies in sorted(st.session_state.per_deck_energy[archetype].items()):
#         # Extract deck number from key
#         deck_num = deck_key.split('-')[-1]
        
#         table_html += f"""<tr style="border-bottom: 1px solid #eee;"><td style="text-align: left; padding: 4px;">{deck_num}</td>"""
        
#         # For each possible energy type, check if this deck has it
#         for energy in all_energies:
#             has_energy = energy in energies
#             check_mark = "✓" if has_energy else ""
#             bg_color = "rgba(0, 160, 255, 0.1)" if has_energy else "transparent"
            
#             table_html += f'<td style="text-align: center; padding: 4px; background-color: {bg_color};">{check_mark}</td>'
        
#         table_html += "</tr>"
    
#     # Close the table
#     table_html += """</table></div>"""
    
#     # Calculate and show energy combination statistics
#     combo_stats = {}
#     for energies in st.session_state.per_deck_energy[archetype].values():
#         combo = tuple(sorted(energies))
#         combo_stats[combo] = combo_stats.get(combo, 0) + 1
    
#     # Sort combinations by frequency
#     sorted_combos = sorted(combo_stats.items(), key=lambda x: x[1], reverse=True)
    
#     # Add combo statistics
#     table_html += """<div style="margin-top: 15px;">
#         <h5 style="margin-bottom: 10px;">Energy Combinations</h5>
#         <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
#             <tr style="border-bottom: 1px solid #ddd;">
#                 <th style="text-align: left; padding: 4px;">Energy Combination</th>
#                 <th style="text-align: right; padding: 4px; width: 80px;">Count</th>
#                 <th style="text-align: right; padding: 4px; width: 80px;">Percentage</th>
#             </tr>"""
    
#     total_decks = len(st.session_state.per_deck_energy[archetype])
    
#     for combo, count in sorted_combos:
#         # Generate energy icons
#         energy_html = ""
#         for energy in combo:
#             energy_url = f"https://limitless3.nyc3.cdn.digitaloceanspaces.com/lotp/pocket/{energy}.png"
#             energy_html += f'<img src="{energy_url}" alt="{energy}" style="height:16px; margin-right:3px; vertical-align:middle;">'
        
#         percentage = (count / total_decks * 100) if total_decks > 0 else 0
        
#         table_html += f"""
#             <tr style="border-bottom: 1px solid #eee;">
#                 <td style="text-align: left; padding: 4px;">{energy_html}</td>
#                 <td style="text-align: right; padding: 4px;">{count}</td>
#                 <td style="text-align: right; padding: 4px;">{percentage:.1f}%</td>
#             </tr>"""
    
#     table_html += """</table></div>"""
    
#     return table_html
