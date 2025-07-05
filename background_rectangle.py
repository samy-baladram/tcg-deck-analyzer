# background_rectangle.py
"""Background rectangle component for deck-based UI theming"""

import streamlit as st

# Energy color mapping - matches your existing ENERGY_COLORS
ENERGY_COLORS = {
    'fire': {
        'primary': '#f86943',       # Bright orange-red
        'secondary': '#f4beae'      # Light orange
    },
    'lightning': {
        'primary': '#ffcf52',       # Yellow
        'secondary': '#ffe8ad'      # Light yellow
    },
    'psychic': {
        'primary': '#b97dff',       # Purple
        'secondary': '#d8b7ff'      # Light purple
    },
    'water': {
        'primary': '#3dafff',       # Blue
        'secondary': '#9fd7ff'      # Light blue
    },
    'fighting': {
        'primary': '#ec8758',       # Brown
        'secondary': '#ebc4b2'      # Light brown
    },
    'darkness': {
        'primary': '#4d909b',       # Dark gray
        'secondary': '#b6d3d8'      # Light gray
    },
    'grass': {
        'primary': '#6bc464',       # Green
        'secondary': '#aeddab'      # Light green
    },
    'metal': {
        'primary': '#c0baa7',       # Steel gray
        'secondary': '#dfdcd2'      # Light gray
    },
    'colorless': {
        'primary': '#EEEEEE',       # Light gray
        'secondary': '#F5F5F5'      # Very light gray
    }
}

def get_deck_primary_color():
    """
    Get the primary color for the currently selected deck based on its most common energy type.
    
    Returns:
        str: Hex color code for the primary energy color, or default if none found
    """
    # Default color if no deck selected or no energy found
    default_color = "#3dafff"  # Blue
    
    # Check if we have a selected deck
    if 'analyze' not in st.session_state:
        return default_color
    
    deck_info = st.session_state.analyze
    deck_name = deck_info.get('deck_name', '')
    
    if not deck_name:
        return default_color
    
    # Try to get energy types for the deck
    try:
        # Import here to avoid circular imports
        from ui_helpers import get_energy_types_for_deck
        energy_types, is_typical = get_energy_types_for_deck(deck_name)
        
        # Use the first (most common) energy type
        if energy_types and len(energy_types) > 0:
            primary_energy = energy_types[0].lower()
            if primary_energy in ENERGY_COLORS:
                color = ENERGY_COLORS[primary_energy]['primary']
                print(f"Using energy color for {deck_name}: {primary_energy} -> {color}")
                return color
    
    except Exception as e:
        print(f"Error getting energy color for deck {deck_name}: {e}")
    
    # Fallback to default
    return default_color

def create_background_rectangle_css(height_percentage=25, opacity=0.15):
    """
    Create CSS for the energy-based background rectangle.
    
    Args:
        height_percentage (int): Height as percentage of viewport (default 25%)
        opacity (float): Opacity of the background (default 0.15)
    
    Returns:
        str: CSS string ready for st.markdown()
    """
    primary_color = get_deck_primary_color()
    
    # Convert hex to RGB for opacity control
    hex_color = primary_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16) 
        b = int(hex_color[4:6], 16)
        rgba_color = f"rgba({r}, {g}, {b}, {opacity})"
    else:
        # Fallback if hex parsing fails
        rgba_color = f"rgba(61, 175, 255, {opacity})"  # Blue fallback
    
    css = f"""
    <style>
    /* Energy-based background rectangle */
    .energy-background-rectangle {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: {height_percentage}vh;
        background-color: {rgba_color};
        border-bottom-left-radius: 30px;
        border-bottom-right-radius: 30px;
        z-index: -1;
        pointer-events: none;
    }}
    
    /* Ensure content stays above background */
    .stApp > div:first-child {{
        position: relative;
        z-index: 1;
    }}
    
    /* Optional: Add subtle gradient effect */
    .energy-background-rectangle::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(180deg, 
            {rgba_color} 0%, 
            rgba({r}, {g}, {b}, {opacity * 0.7}) 70%,
            rgba({r}, {g}, {b}, 0) 100%);
        border-bottom-left-radius: 30px;
        border-bottom-right-radius: 30px;
    }}
    </style>
    <div class="energy-background-rectangle"></div>
    """
    
    return css

def apply_background_rectangle(height_percentage=25, opacity=0.15):
    """
    Apply the energy-based background rectangle to the current page.
    
    Args:
        height_percentage (int): Height as percentage of viewport (adjust to fit under dropdown)
        opacity (float): Opacity of the background
    """
    css = create_background_rectangle_css(height_percentage, opacity)
    st.markdown(css, unsafe_allow_html=True)

def apply_responsive_background_rectangle():
    """
    Apply background rectangle with responsive sizing for different screen widths.
    """
    primary_color = get_deck_primary_color()
    
    # Convert hex to RGB
    hex_color = primary_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16) 
        b = int(hex_color[4:6], 16)
    else:
        r, g, b = 61, 175, 255  # Blue fallback
    
    css = f"""
    <style>
    .energy-background-rectangle {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: rgba({r}, {g}, {b}, 0.15);
        border-bottom-left-radius: 30px;
        border-bottom-right-radius: 30px;
        z-index: -1;
        pointer-events: none;
        
        /* Responsive height */
        height: 200px; /* Default for mobile */
    }}
    
    @media (min-width: 768px) {{
        .energy-background-rectangle {{
            height: 250px; /* Tablet */
        }}
    }}
    
    @media (min-width: 1024px) {{
        .energy-background-rectangle {{
            height: 300px; /* Desktop */
        }}
    }}
    
    @media (min-width: 1440px) {{
        .energy-background-rectangle {{
            height: 350px; /* Large desktop */
        }}
    }}
    
    .stApp > div:first-child {{
        position: relative;
        z-index: 1;
    }}
    </style>
    <div class="energy-background-rectangle"></div>
    """
    
    st.markdown(css, unsafe_allow_html=True)
