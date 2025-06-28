# app.py
"""Main Streamlit application for TCG Deck Analyzer"""

# Import helper modules
import streamlit as st
import ui_helpers
import cache_manager
import display_tabs
import background
from local_metagame import display_local_metagame_comparison
from header_image_cache import clear_expired_cache, get_cache_stats
from card_cache import clear_expired_cache as clear_card_cache
from meta_table import display_extended_meta_table
from PIL import Image

favicon = Image.open("favicon.png").convert('RGBA')

st.set_page_config(
    page_title="PTCGP Deck Analyzer",
    page_icon=favicon,
    layout="wide"
)

# Add background from repository
background.add_app_background()

# In app.py - before using any session state variables
# Initialize app state tracking and load initial data
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        'initial_data_loaded': False
    }

# Add this after loading initial data in app.py
def initialize_matchup_cache():
    """Initialize matchup cache when app starts"""
    if 'matchup_cache_initialized' not in st.session_state:
        import cache_manager
        import threading
        
        def update_matchups_background():
            try:
                # Remove this line - it's causing the import error
                # updated_count = cache_manager.update_matchup_cache(min_share=0.5)
                print("Skipping matchup cache update due to import issues")
            except Exception as e:
                print(f"Error updating matchups in background: {e}")
        
        thread = threading.Thread(target=update_matchups_background)
        thread.daemon = True
        thread.start()
        
        st.session_state.matchup_cache_initialized = True

# Call the initialization function
#initialize_matchup_cache()

# Add cache initialization after other initialization
if 'cache_initialized' not in st.session_state:
    # Clean expired cache on app start
    clear_expired_cache()
    clear_card_cache()     # Card data
    st.session_state.cache_initialized = True
    
    # Optional: Display cache stats in development
    if st.secrets.get("DEBUG_MODE", False):
        stats = get_cache_stats()
        print(f"Header image cache: {stats}")

# Early initialization - Only do heavy loading once
if not st.session_state.app_state['initial_data_loaded']:
    ui_helpers.load_initial_data()  # This loads essential data like deck_list
    st.session_state.app_state['initial_data_loaded'] = True

# SIMPLIFIED: Only handle deck switching, no manual cache clearing
if 'deck_to_analyze' in st.session_state and st.session_state.deck_to_analyze:
    target_deck = st.session_state.deck_to_analyze
    
    # Find the matching display name and index
    if 'deck_display_names' in st.session_state and 'deck_name_mapping' in st.session_state:
        for i, display_name in enumerate(st.session_state.deck_display_names):
            deck_info = st.session_state.deck_name_mapping[display_name]
            if deck_info['deck_name'] == target_deck:
                
                # Just switch decks, no manual cache clearing
                print(f"Switching to deck: {deck_info['deck_name']}")
                
                # Update selection
                st.session_state.selected_deck_index = i
                st.session_state.analyze = {
                    'deck_name': deck_info['deck_name'],
                    'set_name': deck_info['set'],
                }
                
                # Check if this was triggered by automatic refresh
                if st.session_state.get('auto_refresh_in_progress', False):
                    st.session_state.force_deck_refresh = True
                    del st.session_state.auto_refresh_in_progress
                
                # Clear the deck_to_analyze flag
                st.session_state.deck_to_analyze = None
                break
                
# In app.py, after loading initial data but before UI rendering
if 'deck_display_names' in st.session_state and st.session_state.deck_display_names:
    # If we have deck options but no analysis yet, set up the first deck
    if 'analyze' not in st.session_state and 'selected_deck_index' in st.session_state:
        selected_index = st.session_state.selected_deck_index
        
        # Default to first deck if no selection
        if selected_index is None and st.session_state.deck_display_names:
            selected_index = 0
            st.session_state.selected_deck_index = 0
        
        # Set up deck to analyze if valid index
        if selected_index is not None and selected_index < len(st.session_state.deck_display_names):
            selected_deck_display = st.session_state.deck_display_names[selected_index]
            deck_info = st.session_state.deck_name_mapping[selected_deck_display]
            
            st.session_state.analyze = {
                'deck_name': deck_info['deck_name'],
                'set_name': deck_info['set'],
            }
            
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

/* Hover effect */
div[role="option"]:hover {
    background-color: #00A0FF !important;
}

/* Change primary color to blue */
div[data-baseweb="select"] > div {
    border-color: #00A0FF !important;
}

.stButton > button:hover {
    border-color: #00A0FF;
    color: #00A0FF;
}

/* Progress bar */
.stProgress > div > div > div > div {
    background-color: #00A0FF;
}

/* Selected option */
div[data-baseweb="select"] [aria-selected="true"] {
    background-color: #00A0FF !important;
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

# /* Change primary color to blue */
# div[data-baseweb="select"] > div {
#     border-color: #00A0FF !important;
# }

# /* Selected option */
# div[data-baseweb="select"] [aria-selected="true"] {
#     background-color: #00A0FF !important;
# }

# /* Hover effect */
# div[role="option"]:hover {
#     background-color: #00A0FF !important;
# }

# /* Button primary color */
# .stButton > button {
#     border-color: #00A0FF;
#     color: #00A0FF;
# }

# .stButton > button:hover {
#     border-color: #00A0FF;
#     color: #00A0FF;
# }

# Display banner
ui_helpers.display_banner("title_banner.png")

# Create deck selector AFTER initialization
selected_option = ui_helpers.create_deck_selector()

# Simple, direct sidebar rendering - ALWAYS runs but uses cached data
if not st.session_state.get('deck_switching', False):
    with st.sidebar:
        ui_helpers.render_sidebar_from_cache()
else:
    # Fill sidebar with minimal content to prevent collapse
    with st.sidebar:
        st.write("")
        #st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

# Main content area
if 'analyze' in st.session_state and selected_option and st.session_state.get('deck_display_names'):
    original_deck_info = st.session_state.analyze
    
    # Check if we need to force refresh
    force_refresh = st.session_state.get('force_deck_refresh', False)
    if force_refresh:
        st.session_state.force_deck_refresh = False
    
    # Analyze deck with proper error handling
    with st.spinner("Analyzing deck..."):
        try:
            analyzed_deck = cache_manager.get_or_analyze_full_deck(
                original_deck_info['deck_name'], 
                original_deck_info['set_name'],
                force_refresh=force_refresh
            )
        except Exception as e:
            st.error(f"Error analyzing deck: {str(e)}")
            print(f"Analysis error for {original_deck_info['deck_name']}: {str(e)}")
            analyzed_deck = None
    
    # FIXED: Better validation and fallback logic
    if analyzed_deck is None:
        st.error("Failed to analyze the selected deck. Attempting to reload...")
        
        # Try once more with force refresh
        try:
            with st.spinner("Reloading deck data..."):
                analyzed_deck = cache_manager.get_or_analyze_full_deck(
                    original_deck_info['deck_name'], 
                    original_deck_info['set_name'],
                    force_refresh=True  # Force fresh analysis
                )
        except Exception as e:
            st.error(f"Failed to reload deck data: {str(e)}")
            analyzed_deck = None
    
    if analyzed_deck is None:
        st.error("Unable to load deck data. Please try selecting a different deck or refresh the page.")
    else:
        # Validate the structure of analyzed_deck and provide defaults
        try:
            # Use .get() method with defaults to prevent KeyError
            results = analyzed_deck.get('results', None)
            total_decks = analyzed_deck.get('total_decks', 0)
            variant_df = analyzed_deck.get('variant_df', None)
            
            # FIXED: Better validation with specific error messages
            if results is None:
                st.error("No analysis results available for this deck. The deck data may be corrupted.")
                # Try to debug the issue
                st.write("Debug info - analyzed_deck keys:", list(analyzed_deck.keys()) if analyzed_deck else "None")
            elif hasattr(results, 'empty') and results.empty:
                st.error("Analysis results are empty for this deck.")
            else:
                # Display deck header
                display_tabs.display_deck_header(original_deck_info, results)
                
                # Create tab container
                tab1, tab3, tab4, tab5, tab6 = st.tabs(["Deck Template", 
                                                                    "Meta Matchups",
                                                                    "Meta Trend",  # NEW TAB
                                                                    "Metagame Overview",
                                                                    "Related Decks"
                                                                    ])
                
                with tab1:
                    # Pass variant_df safely (could be None)
                    if variant_df is not None:
                        display_tabs.display_deck_template_tab(results, variant_df)
                        st.divider()
                        display_tabs.display_card_usage_tab(results, total_decks, variant_df)
                    else:
                        # Create empty DataFrame if variant_df is None
                        import pandas as pd
                        empty_variant_df = pd.DataFrame()
                        display_tabs.display_deck_template_tab(results, empty_variant_df)
                        st.divider()
                        display_tabs.display_card_usage_tab(results, total_decks, empty_variant_df)
                    
                    # ADD THIS: Display last update time for the current deck
                    # last_update = ui_helpers.display_deck_update_info(
                    #     original_deck_info['deck_name'], 
                    #     original_deck_info['set_name']
                    # )
                    # if last_update:
                    #     st.caption(last_update)
                
                # with tab2:
                #     # Pass variant_df safely
                #     if variant_df is not None:
                #         display_tabs.display_card_usage_tab(results, total_decks, variant_df)
                #     else:
                #         import pandas as pd
                #         empty_variant_df = pd.DataFrame()
                #         display_tabs.display_card_usage_tab(results, total_decks, empty_variant_df)
                    
                with tab3:
                    display_tabs.display_matchup_tab()
                    
                with tab4:
                    display_tabs.display_meta_trend_tab(original_deck_info)
                   
                with tab5:  
                     display_tabs.display_metagame_tab()
                     st.divider()
                     display_extended_meta_table()
                
                # And shift the existing tabs:
                with tab6:  # Related Decks (was tab5)
                    display_tabs.display_related_decks_tab(original_deck_info, results)
                    
                # with tab7:  # Raw Data (was tab6)
                #     if variant_df is not None:
                #         display_tabs.display_raw_data_tab(results, variant_df)
                #     else:
                #         import pandas as pd
                #         empty_variant_df = pd.DataFrame()
                #         display_tabs.display_raw_data_tab(results, empty_variant_df)
        
        except Exception as e:
            st.error(f"Error displaying deck analysis: {str(e)}")
            print(f"Display error: {str(e)}")
            
            # Debug information (remove in production)
            if st.secrets.get("DEBUG_MODE", False):
                st.write("Debug - analyzed_deck structure:")
                st.write(analyzed_deck)
                import traceback
                st.code(traceback.format_exc())
else:
    # Show proper loading state instead of incomplete content
    if not st.session_state.get('deck_display_names'):
        st.info("Loading deck data...")
    elif not selected_option:
        st.info("Select a deck from the dropdown to view detailed analysis")
    else:
        st.info("Initializing deck analysis...")

# st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
# st.markdown("<hr style='margin: 4rem 0;'>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""<div style="text-align: center; font-size: 0.8em; color: #777; margin-top: 0rem; padding: 0rem;">
    <p><strong>Disclaimer:</strong> Pokémon TCG Pocket content is © The Pokémon Company, DeNA Co., Ltd., and/or Creatures, Inc. 
    Data and images sourced from <a href="https://play.limitlesstcg.com" target="_blank">Limitless TCG</a>. 
    This independent, fan-made analysis tool is for educational purposes only and is not affiliated with 
    any official entities or Limitless TCG.</p>
    <p>App and analysis © 2025 Samy Baladram. Open source under MIT License.</p></div>""", unsafe_allow_html=True)

# Rerun button at bottom
st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    if st.button("Rerun", type="tertiary", use_container_width=True, 
                 help="Refresh the application"):
        st.rerun()
