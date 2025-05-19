# app.py
"""Main Streamlit application for TCG Deck Analyzer"""

import streamlit as st
import base64
import os
from datetime import datetime

# Import helper modules
import ui_helpers
import cache_manager
import display_tabs
from config import MIN_META_SHARE, TOURNAMENT_COUNT
import background

# Set up page
st.set_page_config(page_title="Pokémon TCG Pocket Meta Deck Analyzer", layout="wide")

# Add background from repository
background.add_app_background()

# Apply custom styles - same as before
st.markdown("""
<style>
... (styles unchanged)
</style>
""", unsafe_allow_html=True)

# Initialize app state tracking
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        'initial_data_loaded': False,
        'sidebar_loading_started': False
    }

# Display banner
ui_helpers.display_banner("title_banner.png")

# First-time initialization - only load essential data for main app
if not st.session_state.app_state['initial_data_loaded']:
    # Initialize caches
    cache_manager.init_caches()
    
    # Load deck list for dropdown
    if 'deck_list' not in st.session_state:
        from scraper import get_deck_list
        st.session_state.deck_list = get_deck_list()
        st.session_state.fetch_time = datetime.now()
    
    # Load performance data if not already in session state
    if 'performance_data' not in st.session_state:
        performance_df, performance_timestamp = cache_manager.load_or_update_tournament_data()
        st.session_state.performance_data = performance_df
        st.session_state.performance_fetch_time = performance_timestamp
    
    st.session_state.app_state['initial_data_loaded'] = True

# Start sidebar loading with progress bar
if not st.session_state.app_state['sidebar_loading_started']:
    with st.sidebar:
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
        
        # Create progress bar and status message
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Loading meta deck data...")
        
        # Ensure energy cache is initialized
        cache_manager.ensure_energy_cache()
        progress_bar.progress(10)
        status_text.text("Processing top decks...")
        
        # Check if performance data is available
        if st.session_state.performance_data.empty:
            progress_bar.progress(100)
            status_text.empty()
            st.info(f"No tournament performance data available")
        else:
            # Get current month and year for display
            current_month_year = datetime.now().strftime("%B %Y")
            
            # Get top decks
            top_decks = st.session_state.performance_data.head(10)
            progress_bar.progress(30)
            
            # Render each deck with progress updates
            for idx, (_, deck) in enumerate(top_decks.iterrows()):
                rank = idx + 1
                current_progress = 30 + (idx * 6)  # Progress from 30% to 90%
                progress_bar.progress(current_progress)
                status_text.text(f"Loading deck {rank}/10: {deck['displayed_name']}")
                
                # Render the deck
                ui_helpers.render_deck_in_sidebar(deck, rank=rank)
            
            # Complete progress
            progress_bar.progress(100)
            status_text.empty()
            
            # Add disclaimer with update time
            performance_time_str = ui_helpers.calculate_time_ago(st.session_state.performance_fetch_time)
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0px; font-size: 0.85rem;">
                <div>Top performers from {current_month_year}</div>
                <div>Updated {performance_time_str}</div>
            </div>
            <div style="font-size: 0.75rem; margin-bottom: 5px; color: #777;">
                Based on up to {TOURNAMENT_COUNT} tournament results
            </div>
            """, unsafe_allow_html=True)
            
            # Add a divider
            st.markdown("<hr style='margin-top: 25px; margin-bottom: 15px; border: 0; border-top: 1px solid;'>", unsafe_allow_html=True)
            
            # Add expandable methodology section
            with st.expander("🔍 About the Power Index"):
                st.markdown(f"""
                #### Power Index: How We Rank the Best Decks
                
                **Where the Data Comes From**  
                Our Power Index uses the most recent community tournament results from the current month ({current_month_year}) on [Limitless TCG](https://play.limitlesstcg.com/tournaments/completed). This shows how decks actually perform in the most recent competitive play, not just how popular they are.
                
                **What the Power Index Measures**  
                The Power Index is calculated as:
                """)
                
                st.code("Power Index = (Wins + (0.75 × Ties) - Losses) / √(Total Games)", language="")
                
                st.markdown("""
                This formula captures three key things:
                * How many more wins than losses a deck achieves
                * The value of ties (counted as 75% of a win)
                * Statistical confidence (more games = more reliable data)
                
                **Why It's Better Than Other Methods**
                * **Better than Win Rate**: Accounts for both winning and avoiding losses
                * **Better than Popularity**: Measures actual performance, not just what people choose to play
                * **Better than Record Alone**: Balances impressive results against sample size
                
                **Reading the Numbers**
                * **Higher is Better**: The higher the Power Index, the stronger the deck has proven itself
                * **Positive vs Negative**: Positive numbers mean winning more than losing
                * **Comparing Decks**: A deck with a Power Index of 2.0 is performing significantly better than one with 1.0
                """)
                
            # Add cache statistics at the bottom
            with st.expander("🔧 Cache Statistics", expanded=False):
                cache_stats = cache_manager.get_cache_statistics()
                st.markdown(f"""
                - **Decks Cached**: {cache_stats['decks_cached']}
                - **Sample Decks**: {cache_stats['sample_decks_cached']}
                - **Tournaments Tracked**: {cache_stats['tournaments_tracked']}
                - **Last Updated**: {cache_stats['last_update']}
                """)
                
            # Add update buttons
            st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Force Update Data", help="Force refresh all tournament data"):
                    with st.spinner("Updating tournament data..."):
                        stats = cache_manager.update_all_caches()
                        st.success(f"Updated {stats['updated_decks']} decks from {stats['new_tournaments']} new tournaments")
                        if st.button("Apply Updates"):
                            st.rerun()
            
            with col2:
                if st.button("📊 Update Card Stats", help="Refresh card usage statistics"):
                    with st.spinner("Updating card statistics..."):
                        cache_manager.aggregate_card_usage(force_update=True)
                        st.success("Card statistics updated")
                        if st.button("Apply Updates"):
                            st.rerun()
    
    # Set flag to indicate sidebar loading started
    st.session_state.app_state['sidebar_loading_started'] = True

# Create deck selector - this is part of main content
selected_option = ui_helpers.create_deck_selector()

# Main content area (rest of app unchanged)
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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Deck Template", 
                                                  "Card Usage",  
                                                  "Meta Matchups",
                                                  "Metagame Overview",
                                                  "Related Decks",
                                                  "Raw Data"])
    
    with tab1:
        display_tabs.display_deck_template_tab(results)
         # Display last update time for the current deck
        last_update = ui_helpers.display_deck_update_info(
            original_deck_info['deck_name'], 
            original_deck_info['set_name']
        )
        display_tabs.display_energy_debug_tab(original_deck_info)
        if last_update:
            st.caption(last_update)           
    
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

# Scripts remain the same
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
