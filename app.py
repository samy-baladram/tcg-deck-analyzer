# app.py
"""Main Streamlit application for TCG Deck Analyzer"""

import streamlit as st

# Import helper modules
import ui_helpers
import cache_manager
import display_tabs
from config import MIN_META_SHARE
from card_renderer import add_card_hover_effect

# Set up page
st.set_page_config(page_title="Pokémon TCG Pocket Meta Deck Analyzer", layout="wide")

# Apply custom styles
st.markdown("""
<style>
/* Change primary color to blue */
div[data-baseweb="select"] > div {
    border-color: #00A0FF !important;
}

/* Selected option */
div[data-baseweb="select"] [aria-selected="true"] {
    background-color: #00A0FF !important;
}

/* Hover effect */
div[role="option"]:hover {
    background-color: #00A0FF !important;
}

/* Button primary color */
.stButton > button {
    border-color: #00A0FF;
    color: #00A0FF;
}

.stButton > button:hover {
    border-color: #00A0FF;
    color: #00A0FF;
}

/* Progress bar */
.stProgress > div > div > div > div {
    background-color: #00A0FF;
}

/* TAB NAVIGATION STYLES */
/* Active tab text color */
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    color: #00A0FF !important;
}

/* Tab hover with 50% transparency */
.stTabs [data-baseweb="tab-list"] button[aria-selected="false"]:hover {
    color: rgba(72, 187, 255, 0.4) !important;
    transition: color 0.3s;
}

/* SELECTED TAB UNDERLINE ONLY */
/* This targets the moving underline indicator */
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #00A0FF !important;
}

/* Remove any background color from tab list */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
}

/* Ensure only selected tab has the indicator */
.stTabs [data-baseweb="tab-list"] button[aria-selected="false"] {
    border-bottom: none !important;
}

/* Even more specific selector targeting the text */
div[data-testid="stTabs"] [data-baseweb="tab-list"] [data-testid="stMarkdownContainer"] p {
    font-size: 18px !important;
    padding: 8px 16px !important;
}

/* Sidebar style for performance cards */
.performance-card {
    margin-bottom: 10px;
    padding: 10px;
    border-radius: 5px;
    border: 1px solid rgba(0, 160, 255, 0.3);
}

.positive-index {
    color: #00A02A;
    font-weight: bold;
}

.negative-index {
    color: #FF4500;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# Add the hover effect setup after your page_config and style settings
add_card_hover_effect()

# Display banner
ui_helpers.display_banner("title_banner.png")

# Show loading spinner for entire app initialization
with st.spinner("Loading app data..."):
    # Load initial data - this is where the heavy lifting happens
    ui_helpers.load_initial_data()
    # Add this line to preload Pokémon info for all decks
    from pokemon_info_manager import preload_all_deck_pokemon_info
    preload_all_deck_pokemon_info()

# Create sidebar
with st.spinner("Loading sidebar data..."):
    ui_helpers.render_sidebar()

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
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Card Usage", "Deck Template", "Raw Data", "Metagame Overview", "Related Decks"])
    
    with tab1:
        display_tabs.display_card_usage_tab(results, total_decks, variant_df)
    
    with tab2:
        display_tabs.display_deck_template_tab(results)
    
    with tab3:
        display_tabs.display_raw_data_tab(results, variant_df)
    
    with tab4:
        display_tabs.display_metagame_tab()
        
    with tab5:
        display_tabs.display_related_decks_tab(original_deck_info, results)
else:
    st.info("👆 Select a deck from the dropdown to view detailed analysis")

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
