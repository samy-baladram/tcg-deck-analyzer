# app.py
"""Main Streamlit application for TCG Deck Analyzer"""

import streamlit as st

# Import helper modules
import ui_helpers
import cache_manager
import display_tabs
from config import MIN_META_SHARE
import background
import base64
import os

from PIL import Image

import os
import shutil
import pathlib
import streamlit as st
from cache_utils import CACHE_DIR

# Add background from repository
background.add_app_background()

# In app.py - before using any session state variables
# Initialize app state tracking and load initial data
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        'initial_data_loaded': False
    }

def clear_all_caches():
    """Force clear all caches to ensure formula changes take effect"""
    # Clear session state cache
    if 'performance_data' in st.session_state:
        del st.session_state['performance_data']
    if 'analyzed_deck_cache' in st.session_state:
        st.session_state['analyzed_deck_cache'] = {}
        
    # Force disk cache to be recreated
    import os
    from cache_utils import TOURNAMENT_DATA_PATH
    if os.path.exists(TOURNAMENT_DATA_PATH):
        os.remove(TOURNAMENT_DATA_PATH)
    
    # Mark cache as expired
    import datetime
    st.session_state.performance_fetch_time = datetime.datetime.now() - datetime.timedelta(days=1)
    
    # Set flag to force update
    st.session_state.update_running = True

# Add to app.py near beginning of main code
if st.sidebar.button("Rebuild Performance Data"):
    clear_all_caches()
    with st.spinner("Rebuilding performance data with new formula..."):
        # Force refresh
        perf_data = cache_manager.load_or_update_tournament_data(force_update=True)
        st.success("Performance data rebuilt")
        st.rerun()
        
# if 'disable_background' not in st.session_state:
#     st.session_state.disable_background = True
#     st.session_state.update_running = False  # This should prevent new bg threads

# Early initialization - Only do heavy loading once
if not st.session_state.app_state['initial_data_loaded']:
    ui_helpers.load_initial_data()  # This loads essential data like deck_list
    st.session_state.app_state['initial_data_loaded'] = True

# Apply custom styles - IMPORTANT: Put CSS before any components render
st.markdown("""
<style>
div[data-testid="stExpander"] details summary p{
    font-size: 1rem;
}

/* Expander header styling */
.stExpander > details > summary {
    border-color: #00A0FF !important;
}

/* Expander hover effect */
.stExpander > details > summary:hover {
    color: #00A0FF !important;
    border-color: #00A0FF !important;
    background-color: rgba(0, 160, 255, 0.1) !important;
}

/* Expander open state */
.stExpander > details[open] > summary {
    border-top: 0px solid #00A0FF !important;
    color: #00A0FF !important;
}

div[data-baseweb="tag"] * {
    background-color: rgba(0, 160, 255, 0.1) !important;
    color: #00A0FF !important;
    fill: #00A0FF !important;
    border-color: #00A0FF !important;
}

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
    font-size: 15px !important;
    padding: 8px 12px !important;
}

</style>
""", unsafe_allow_html=True)


# Display banner
ui_helpers.display_banner("title_banner.png")

# Create deck selector AFTER initialization
selected_option = ui_helpers.create_deck_selector()

# Simple, direct sidebar rendering - ALWAYS runs but uses cached data
with st.sidebar:
    ui_helpers.render_sidebar_from_cache()  # You'll need to create this function

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
    
    # Create tab container
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Deck Template", 
                                                        "Card Usage",  
                                                        "Meta Matchups",
                                                        "Metagame Overview",
                                                        "Related Decks",
                                                        "Raw Data"
                                                        ])
    
    with tab1:
        display_tabs.display_deck_template_tab(results)
         # ADD THIS: Display last update time for the current deck
        last_update = ui_helpers.display_deck_update_info(
            original_deck_info['deck_name'], 
            original_deck_info['set_name']
        )
        if last_update:
            st.caption(last_update)
       # st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)    
    
    with tab2:
        display_tabs.display_card_usage_tab(results, total_decks, variant_df)
        st.caption(f"Data of 20 collected decks (with partial energy info). {last_update}")
        #st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
        
    with tab3:
        display_tabs.display_matchup_tab()
        #st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
        
    with tab4:
        display_tabs.display_metagame_tab() 
        #st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
        
    with tab5:
        display_tabs.display_related_decks_tab(original_deck_info, results)
        #st.markdown("<div style='margin-top: 300px;'></div>", unsafe_allow_html=True)
        
    with tab6:
        display_tabs.display_raw_data_tab(results, variant_df)

    #with tab7:
     #   display_tabs.display_counter_picker()
else:
    st.info("👆 Select a deck from the dropdown to view detailed analysis")

st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
st.markdown("<hr style='margin: 4rem 0;'>", unsafe_allow_html=True)
#display_tabs.display_counter_picker()

# Load sidebar AFTER main content to ensure main interface loads first
#ui_helpers.render_sidebar()


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
