# app.py
"""Main Streamlit application for TCG Deck Analyzer"""

import streamlit as st
import os
# Import helper modules
import ui_helpers
import cache_manager
import display_tabs
from config import MIN_META_SHARE
import background
import threading

# Set up page
st.set_page_config(page_title="Pokémon TCG Pocket Meta Deck Analyzer", layout="wide")

# Add background from repository
background.add_app_background()

# Apply custom styles (same as before)
st.markdown("""
<style>
... (your styles here)
</style>
""", unsafe_allow_html=True)

# Initialize app state tracking
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        'initial_data_loaded': False,
        'sidebar_loading': False,
        'sidebar_loaded': False
    }

# Display banner
ui_helpers.display_banner("title_banner.png")

# Initialize sidebar placeholder
sidebar_placeholder = st.sidebar.empty()

# First-time initialization - only do heavy loading once
# This initializes core data for the main app
if not st.session_state.app_state['initial_data_loaded']:
    ui_helpers.load_initial_data(minimal=True)  # Modified to load only essential data
    st.session_state.app_state['initial_data_loaded'] = True

# Start sidebar loading in the background or show already loaded sidebar
if not st.session_state.app_state['sidebar_loaded'] and not st.session_state.app_state['sidebar_loading']:
    # Set loading flag
    st.session_state.app_state['sidebar_loading'] = True
    
    # Create progress bar in sidebar
    with sidebar_placeholder.container():
        # Show banner or title
        banner_path = "sidebar_banner.png"
        if os.path.exists(banner_path):
            with open(banner_path, "rb") as f:
                banner_base64 = base64.b64encode(f.read()).decode()
            st.markdown(f"""
            <div style="width:100%; text-align:center; margin:-20px 0 5px 0;">
                <img src="data:image/png;base64,{banner_base64}" style="width:100%; max-width:350px; margin-bottom:10px;">
            </div>
            """, unsafe_allow_html=True)
        else:
            st.title("Top 10 Meta Decks")
        
        # Show progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Loading meta data...")
else:
    # If sidebar already loaded, render it
    if st.session_state.app_state['sidebar_loaded']:
        ui_helpers.render_loaded_sidebar()

# Create deck selector (this is part of the main content flow)
selected_option = ui_helpers.create_deck_selector()

# Main content area
if 'analyze' in st.session_state and selected_option:
    original_deck_info = st.session_state.analyze
    
    # Get analyzed deck from cache or analyze it
    with st.spinner("Analyzing deck..."):
        analyzed_deck = cache_manager.get_or_analyze_full_deck(original_deck_info['deck_name'], original_deck_info['set_name'])
    
    # Unpack the results
    results = analyzed_deck['results']
    total_decks = analyzed_deck['total_decks']
    variant_df = analyzed_deck['variant_df']
    
    # Display deck header
    display_tabs.display_deck_header(original_deck_info, results)
    
    # Display tabs (same as before)
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Deck Template", 
                                                    "Card Usage",  
                                                    "Meta Matchups",
                                                    "Metagame Overview",
                                                    "Related Decks",
                                                    "Raw Data"])
    
    # Tab content rendering (same as before)
    with tab1:
        display_tabs.display_deck_template_tab(results)
        # Display last update time
        last_update = ui_helpers.display_deck_update_info(
            original_deck_info['deck_name'], 
            original_deck_info['set_name']
        )
        display_tabs.display_energy_debug_tab(original_deck_info)
        if last_update:
            st.caption(last_update)
    
    # Other tabs remain the same
    with tab2:
        display_tabs.display_card_usage_tab(results, total_decks, variant_df)
    
    with tab3:
        display_tabs.display_matchup_tab()
    
    with tab4:
        display_tabs.display_metagame_tab() 
    
    with tab5:
        display_tabs.display_related_decks_tab(original_deck_info, results)
    
    with tab6:
        display_tabs.display_raw_data_tab(results, variant_df)
else:
    st.info("👆 Select a deck from the dropdown to view detailed analysis")

# After main content is loaded, continue loading the sidebar if needed
if st.session_state.app_state['sidebar_loading'] and not st.session_state.app_state['sidebar_loaded']:
    with sidebar_placeholder.container():
        # Continue with the progressive loading
        ui_helpers.load_sidebar_progressively(progress_bar, status_text)
        # Set loaded flag
        st.session_state.app_state['sidebar_loaded'] = True
        st.session_state.app_state['sidebar_loading'] = False

# Footer
st.markdown("---")
st.markdown("""<div style="text-align: center; font-size: 0.8em; color: #777; margin-top: 1rem; padding: 1rem;">
    <p><strong>Disclaimer:</strong></p><p>The literal and graphical information presented on this website about the Pokémon Trading Card Game Pocket, 
    including card images and text, is copyright The Pokémon Company, DeNA Co., Ltd., and/or Creatures, Inc. 
    This website is not produced by, endorsed by, supported by, or affiliated with any of those copyright holders.</p>
    <p>Deck composition data is sourced from <a href="https://play.limitlesstcg.com" target="_blank">Limitless TCG</a>, 
    which aggregates tournament results and decklists from competitive play. Card images are retrieved from 
    Limitless TCG's image repository. This tool is intended for educational and analytical purposes only.</p>
    <p>This is an independent, fan-made project and is not affiliated with Limitless TCG, The Pokémon Company, 
    or any other official entities.</p></div>""", unsafe_allow_html=True)

# At the very end of app.py, after footer
st.markdown("""
<script>
// Trigger card hover setup after everything is loaded
setTimeout(function() {
    if (typeof setupCardHover === 'function') {
        setupCardHover();
    }
}, 2000);
</script>
""", unsafe_allow_html=True)

# At the very end of app.py, after footer
st.markdown("""
<script>
// Simple direct script test
document.addEventListener('DOMContentLoaded', function() {
    alert('Card hover script loaded directly!');
    
    // Create a simple hover popup
    const popup = document.createElement('div');
    popup.id = 'direct-card-popup';
    popup.style.cssText = 'position:fixed; top:0; left:0; background:red; padding:5px; z-index:10000; display:none;';
    popup.textContent = 'Card popup';
    document.body.appendChild(popup);
    
    // Add hover to ALL images
    const allImages = document.querySelectorAll('img');
    allImages.forEach(img => {
        img.addEventListener('mouseenter', function() {
            popup.style.top = (this.getBoundingClientRect().top + window.scrollY) + 'px';
            popup.style.left = (this.getBoundingClientRect().right + window.scrollX) + 'px';
            popup.style.display = 'block';
        });
        
        img.addEventListener('mouseleave', function() {
            popup.style.display = 'none';
        });
    });
});
</script>
""", unsafe_allow_html=True)
