# app.py
"""Main Streamlit application for TCG Deck Analyzer"""

import streamlit as st

# Import helper modules
import ui_helpers
import cache_manager
import display_tabs
from config import MIN_META_SHARE

# Set up page
st.set_page_config(page_title="Pokémon TCG Pocket Meta Deck Analyzer", layout="wide")

# Apply custom styles
st.markdown("""
<style>
# Your existing styles here...
</style>
""", unsafe_allow_html=True)

# Show loading spinner for entire app initialization
with st.spinner("Loading app data..."):
    # Display banner
    ui_helpers.display_banner("title_banner.png")
    
    # Load initial data - this is where the heavy lifting happens
    ui_helpers.load_initial_data()

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
    tab1, tab2, tab3, tab4 = st.tabs(["Card Usage", "Deck Template", "Raw Data", "Metagame Overview"])
    
    with tab1:
        display_tabs.display_card_usage_tab(results, total_decks, variant_df)
    
    with tab2:
        display_tabs.display_deck_template_tab(results)
    
    with tab3:
        display_tabs.display_raw_data_tab(results, variant_df)
    
    with tab4:
        display_tabs.display_metagame_tab()
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
