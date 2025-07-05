# energy_background.py
"""Background rectangle functionality based on deck energy types"""

import streamlit as st
from visualizations import ENERGY_COLORS, get_energy_colors

def get_current_deck_energy():
    """Get the primary energy type from currently selected deck"""
    try:
        # Get current deck info from session state
        if 'analyze' not in st.session_state:
            return None
            
        deck_info = st.session_state.analyze
        deck_name = deck_info.get('deck_name', '')
        
        if not deck_name:
            return None
            
        # Import here to avoid circular imports
        from ui_helpers import get_energy_types_for_deck
        
        # Get energy types for current deck
        energy_types, is_typical = get_energy_types_for_deck(deck_name)
        
        # Return the first (most common) energy type
        return energy_types[0] if energy_types else None
        
    except Exception as e:
        print(f"Error getting deck energy: {e}")
        return None

def get_background_color(energy_type):
    """Get the primary color for the given energy type"""
    if not energy_type:
        # Default color if no energy type found
        return "#f0f2f6"  # Light gray default
        
    energy_colors = get_energy_colors(energy_type)
    return energy_colors['primary']

def apply_energy_background():
    """Apply the energy-based background rectangle to the page"""
    
    # Get current deck's primary energy type
    primary_energy = get_current_deck_energy()
    
    # Get the background color
    bg_color = get_background_color(primary_energy)
    
    # Apply CSS for the background rectangle
    background_css = f"""
    <style>
    /* Energy-based background rectangle */
    .energy-background {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 35vh; /* Adjust this value to fit under your dropdown */
        background-color: {bg_color};
        opacity: 0.15; /* Make it subtle */
        border-bottom-left-radius: 30px;
        border-bottom-right-radius: 30px;
        z-index: -1; /* Behind all content */
        pointer-events: none; /* Don't block interactions */
    }}
    
    /* Responsive adjustments */
    @media (max-width: 768px) {{
        .energy-background {{
            height: 40vh; /* Slightly taller on mobile */
        }}
    }}
    
    @media (min-width: 1200px) {{
        .energy-background {{
            height: 30vh; /* Shorter on wide screens */
        }}
    }}
    </style>
    
    <div class="energy-background"></div>
    """
    
    st.markdown(background_css, unsafe_allow_html=True)

def apply_energy_background_custom_height(height_vh=35, opacity=0.15):
    """
    Apply energy background with custom height and opacity
    
    Args:
        height_vh (int): Height in viewport height units (vh)
        opacity (float): Opacity level (0.0 to 1.0)
    """
    
    # Get current deck's primary energy type
    primary_energy = get_current_deck_energy()
    
    # Get the background color
    bg_color = get_background_color(primary_energy)
    
    # Apply CSS with custom parameters
    background_css = f"""
    <style>
    .energy-background-custom {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: {height_vh}vh;
        background-color: {bg_color};
        opacity: {opacity};
        border-bottom-left-radius: 30px;
        border-bottom-right-radius: 30px;
        z-index: -1;
        pointer-events: none;
    }}
    </style>
    
    <div class="energy-background-custom"></div>
    """
    
    st.markdown(background_css, unsafe_allow_html=True)
