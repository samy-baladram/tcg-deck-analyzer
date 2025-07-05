# background_rectangle.py
"""Static background rectangle component using pure HTML"""

import streamlit as st

# Energy color mapping
ENERGY_COLORS = {
    'fire': '#f86943',
    'lightning': '#ffcf52', 
    'psychic': '#b97dff',
    'water': '#3dafff',
    'fighting': '#ec8758',
    'darkness': '#4d909b',
    'grass': '#6bc464',
    'metal': '#c0baa7',
    'colorless': '#EEEEEE'
}

def get_current_energy_color():
    """Get current deck's primary energy color with better fallback handling"""
    default_color = "#3dafff"  # Blue default
    
    # Always try to get the deck info, even if analyze isn't set yet
    deck_name = ""
    
    if 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', '')
    elif 'selected_deck_index' in st.session_state and 'deck_display_names' in st.session_state:
        # Fallback: try to get from selected dropdown option
        try:
            selected_index = st.session_state.selected_deck_index
            if (selected_index is not None and 
                selected_index < len(st.session_state.deck_display_names)):
                selected_display = st.session_state.deck_display_names[selected_index]
                if 'deck_name_mapping' in st.session_state:
                    deck_info = st.session_state.deck_name_mapping[selected_display]
                    deck_name = deck_info.get('deck_name', '')
        except:
            pass
    
    if not deck_name:
        return default_color
    
    try:
        # Try to get energy types (import locally to avoid issues)
        from ui_helpers import get_energy_types_for_deck
        energy_types, _ = get_energy_types_for_deck(deck_name)
        
        if energy_types and len(energy_types) > 0:
            primary_energy = energy_types[0].lower()
            return ENERGY_COLORS.get(primary_energy, default_color)
    except:
        pass
    
    return default_color

def create_static_background_html(height_px=300, opacity=0.12):
    """
    Create static HTML background that persists better.
    
    Args:
        height_px (int): Fixed height in pixels (easier to control than percentage)
        opacity (float): Background opacity
    """
    color = get_current_energy_color()
    
    # Convert hex to RGB
    hex_color = color.lstrip('#')
    r = int(hex_color[0:2], 16) if len(hex_color) >= 2 else 61
    g = int(hex_color[2:4], 16) if len(hex_color) >= 4 else 175  
    b = int(hex_color[4:6], 16) if len(hex_color) >= 6 else 255
    
    # Create persistent HTML div
    background_html = f"""
    <div style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        width: 100%;
        height: {height_px}px;
        background: linear-gradient(180deg, 
            rgba({r}, {g}, {b}, {opacity}) 0%, 
            rgba({r}, {g}, {b}, {opacity * 0.6}) 80%,
            rgba({r}, {g}, {b}, 0) 100%);
        border-bottom-left-radius: 30px;
        border-bottom-right-radius: 30px;
        z-index: -999;
        pointer-events: none;
    "></div>
    """
    
    return background_html

def apply_static_background(height_px=300, opacity=0.12):
    """Apply the static background using pure HTML"""
    background_html = create_static_background_html(height_px, opacity)
    st.markdown(background_html, unsafe_allow_html=True)

def create_persistent_background_container():
    """
    Create a more persistent background using st.empty() approach
    Returns the container for manual updates
    """
    # Create empty container at the top
    if 'background_container' not in st.session_state:
        st.session_state.background_container = st.empty()
    
    return st.session_state.background_container

def update_background_container(container, height_px=300, opacity=0.12):
    """Update the persistent background container"""
    background_html = create_static_background_html(height_px, opacity)
    container.markdown(background_html, unsafe_allow_html=True)

def apply_minimal_css_background(height_px=300):
    """
    Apply background using minimal CSS that changes less frequently
    """
    # Get current color
    color = get_current_energy_color()
    hex_color = color.lstrip('#')
    r = int(hex_color[0:2], 16) if len(hex_color) >= 2 else 61
    g = int(hex_color[2:4], 16) if len(hex_color) >= 4 else 175  
    b = int(hex_color[4:6], 16) if len(hex_color) >= 6 else 255
    
    # Minimal CSS approach
    st.markdown(f"""
    <style>
    .main-bg {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: {height_px}px;
        background: rgba({r}, {g}, {b}, 0.1);
        border-bottom-left-radius: 30px;
        border-bottom-right-radius: 30px;
        z-index: -999;
        pointer-events: none;
    }}
    </style>
    <div class="main-bg"></div>
    """, unsafe_allow_html=True)

# Alternative approach: Create background only once per deck change
def create_cached_background(deck_name, height_px=300, opacity=0.12):
    """Create background and cache it to reduce re-rendering"""
    
    # Create cache key
    cache_key = f"bg_{deck_name}_{height_px}_{opacity}"
    
    # Check if already cached
    if 'background_cache' not in st.session_state:
        st.session_state.background_cache = {}
    
    if cache_key not in st.session_state.background_cache:
        # Generate new background HTML
        color = get_current_energy_color()
        hex_color = color.lstrip('#')
        r = int(hex_color[0:2], 16) if len(hex_color) >= 2 else 61
        g = int(hex_color[2:4], 16) if len(hex_color) >= 4 else 175  
        b = int(hex_color[4:6], 16) if len(hex_color) >= 6 else 255
        
        background_html = f"""
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            height: {height_px}px;
            background: rgba({r}, {g}, {b}, {opacity});
            border-bottom-left-radius: 30px;
            border-bottom-right-radius: 30px;
            z-index: -999;
            pointer-events: none;
        "></div>
        """
        
        # Cache it
        st.session_state.background_cache[cache_key] = background_html
    
    # Return cached version
    return st.session_state.background_cache[cache_key]

def apply_cached_background(height_px=300, opacity=0.12):
    """Apply cached background to reduce flickering"""
    if 'analyze' in st.session_state:
        deck_name = st.session_state.analyze.get('deck_name', 'default')
        background_html = create_cached_background(deck_name, height_px, opacity)
        st.markdown(background_html, unsafe_allow_html=True)

def apply_persistent_background(height_px=300, opacity=0.12):
    """Apply background only when deck changes to prevent blinking"""
    
    # Initialize tracking variables
    if 'current_background_deck' not in st.session_state:
        st.session_state.current_background_deck = None
        st.session_state.background_applied = False
    
    # Determine current deck
    current_deck = None
    if 'analyze' in st.session_state:
        current_deck = st.session_state.analyze.get('deck_name', '')
    elif 'selected_deck_index' in st.session_state and 'deck_display_names' in st.session_state:
        try:
            selected_index = st.session_state.selected_deck_index
            if (selected_index is not None and 
                selected_index < len(st.session_state.deck_display_names)):
                selected_display = st.session_state.deck_display_names[selected_index]
                if 'deck_name_mapping' in st.session_state:
                    deck_info = st.session_state.deck_name_mapping[selected_display]
                    current_deck = deck_info.get('deck_name', '')
        except:
            pass
    
    # Only apply background if deck changed or not applied yet
    if (current_deck != st.session_state.current_background_deck or 
        not st.session_state.background_applied):
        
        # Get color for current deck
        color = get_current_energy_color()
        hex_color = color.lstrip('#')
        r = int(hex_color[0:2], 16) if len(hex_color) >= 2 else 61
        g = int(hex_color[2:4], 16) if len(hex_color) >= 4 else 175  
        b = int(hex_color[4:6], 16) if len(hex_color) >= 6 else 255
        
        # Create background with unique ID to avoid conflicts
        background_id = f"energy-bg-{abs(hash(current_deck or 'default'))}"
        
        background_html = f"""
        <style>
        #{background_id} {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            height: {height_px}px;
            background: rgba({r}, {g}, {b}, {opacity});
            border-bottom-left-radius: 30px;
            border-bottom-right-radius: 30px;
            z-index: -999;
            pointer-events: none;
            transition: background-color 0.3s ease;
        }}
        </style>
        <div id="{background_id}"></div>
        """
        
        st.markdown(background_html, unsafe_allow_html=True)
        
        # Update tracking
        st.session_state.current_background_deck = current_deck
        st.session_state.background_applied = True
        
        print(f"Applied background for deck: {current_deck} with color: {color}")

def apply_single_background(height_px=300, opacity=0.12):
    """Apply background only once per session to eliminate blinking"""
    
    # Only apply once per session
    if 'background_applied_once' not in st.session_state:
        st.session_state.background_applied_once = True
        
        # Use default blue color that works for most cases
        default_color = "#3dafff"
        hex_color = default_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16) 
        b = int(hex_color[4:6], 16)
        
        background_html = f"""
        <style>
        .single-energy-bg {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            width: 100%;
            height: {height_px}px;
            background: rgba({r}, {g}, {b}, {opacity});
            border-bottom-left-radius: 30px;
            border-bottom-right-radius: 30px;
            z-index: -999;
            pointer-events: none;
        }}
        </style>
        <div class="single-energy-bg"></div>
        """
        
        st.markdown(background_html, unsafe_allow_html=True)
