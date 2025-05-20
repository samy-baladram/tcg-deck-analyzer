# app.py modifications

import streamlit as st

# Import helper modules
import ui_helpers
import cache_manager
import display_tabs
from config import MIN_META_SHARE
import background

# Set up page
st.set_page_config(page_title="Pokémon TCG Pocket Meta Deck Analyzer", layout="wide")

# Add background from repository
background.add_app_background()

# Apply custom styles
st.markdown("""
<style>
# Your existing styles here...
</style>
""", unsafe_allow_html=True)

# Initialize app state tracking
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        'initial_data_loaded': False
    }

# Display banner
ui_helpers.display_banner("title_banner.png")

# First-time initialization - only do minimal loading on first run
if not st.session_state.app_state['initial_data_loaded']:
    # Only initialize caches without heavy loading
    cache_manager.init_caches()
    st.session_state.app_state['initial_data_loaded'] = True

# At the very beginning, make sure all session state variables are initialized
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        'initial_data_loaded': False
    }

if 'selected_deck_index' not in st.session_state:
    st.session_state.selected_deck_index = None
    
if 'deck_to_analyze' not in st.session_state:
    st.session_state.deck_to_analyze = None

# IMPORTANT: Load main interface first
# Create deck selector
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
    
    # Display tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Deck Template", "Card Usage",  "Energy Data", "Related Decks",  "Metagame Overview", "Raw Data", "Meta Matchups"])
    
    # Display tab content...
    with tab1:
        display_tabs.display_deck_template_tab(results)
        # Show last update time
        last_update = ui_helpers.display_deck_update_info(
            original_deck_info['deck_name'], 
            original_deck_info['set_name']
        )
        if last_update:
            st.caption(last_update)
    
    # Other tabs...
else:
    st.info("👆 Select a deck from the dropdown to view detailed analysis")

# IMPORTANT: Load sidebar AFTER main interface is rendered
# This ensures the dropdown selector appears first
ui_helpers.render_sidebar()

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
