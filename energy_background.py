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
    
    # Check if energy type has changed to prevent unnecessary updates
    if 'current_bg_energy' not in st.session_state:
        st.session_state.current_bg_energy = None
    
    # Only update if energy type changed
    if st.session_state.current_bg_energy != primary_energy:
        st.session_state.current_bg_energy = primary_energy
        
        # Get the background color
        bg_color = get_background_color(primary_energy)
        
        # Apply CSS for the background rectangle with smooth transitions
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
            transition: background-color 0.3s ease-in-out; /* Smooth color transitions */
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
    else:
        # Still need to render the div even if CSS hasn't changed
        st.markdown('<div class="energy-background"></div>', unsafe_allow_html=True)

def apply_energy_background_custom_height(height_vh=35, opacity=0.15):
    """
    Apply energy background with custom height and opacity
    
    Args:
        height_vh (int): Height in viewport height units (vh)
        opacity (float): Opacity level (0.0 to 1.0)
    """
    
    # Get current deck's primary energy type
    primary_energy = get_current_deck_energy()
    
    # Check if energy type has changed to prevent unnecessary updates
    cache_key = f"current_bg_energy_{height_vh}_{opacity}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = None
    
    # Only update if energy type changed
    if st.session_state[cache_key] != primary_energy:
        st.session_state[cache_key] = primary_energy
        
        # Get the background color
        bg_color = get_background_color(primary_energy)
        
        # Apply CSS with custom parameters and smooth transitions
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
            transition: background-color 0.3s ease-in-out;
        }}
        </style>
        
        <div class="energy-background-custom"></div>
        """
        
        st.markdown(background_css, unsafe_allow_html=True)
    else:
        # Still render the div even if CSS hasn't changed
        st.markdown('<div class="energy-background-custom"></div>', unsafe_allow_html=True)

def apply_energy_background_stable():
    """
    Alternative stable approach using CSS custom properties
    This version uses CSS variables to reduce re-rendering
    """
    
    # Get current deck's primary energy type
    primary_energy = get_current_deck_energy()
    bg_color = get_background_color(primary_energy)
    
    # Use CSS custom properties for smoother updates
    background_css = f"""
    <style>
    :root {{
        --energy-bg-color: {bg_color};
    }}
    
    .energy-background-stable {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 35vh;
        background-color: var(--energy-bg-color);
        opacity: 0.15;
        border-bottom-left-radius: 30px;
        border-bottom-right-radius: 30px;
        z-index: -1;
        pointer-events: none;
        transition: background-color 0.5s ease-in-out;
    }}
    
    @media (max-width: 768px) {{
        .energy-background-stable {{
            height: 40vh;
        }}
    }}
    
    @media (min-width: 1200px) {{
        .energy-background-stable {{
            height: 30vh;
        }}
    }}
    </style>
    
    <div class="energy-background-stable"></div>
    """
    
    st.markdown(background_css, unsafe_allow_html=True)
