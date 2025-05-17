# app.py
"""Main Streamlit application for TCG Deck Analyzer"""

import streamlit as st
from datetime import datetime, timedelta
import os
import json
import pandas as pd

# Import all modules
from config import MIN_META_SHARE, CACHE_TTL, IMAGE_BASE_URL
from scraper import get_deck_list, analyze_recent_performance, get_sample_deck_for_archetype
from analyzer import analyze_deck, build_deck_template
from formatters import format_deck_name, format_deck_option, parse_deck_option
from image_processor import get_base64_image, create_deck_header_images, get_card_thumbnail
from visualizations import create_usage_bar_chart, display_chart, create_variant_bar_chart
from utils import calculate_time_ago, format_card_display
from card_renderer import CardGrid, render_deck_section, render_option_section, render_variant_cards

# Add this right after st.set_page_config()
st.set_page_config(page_title="Pokémon TCG Pocket Meta Deck Analyzer", layout="wide")

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

/* Expander styling - using direct class approach */
/* Expander hover effect */
.stExpander > details > summary:hover {
    color: #00A0FF !important;
    background-color: rgba(0, 160, 255, 0.1) !important;
}

.stExpander > details > summary:hover svg path {
    stroke: #00A0FF !important;
}

/* Remove default chevron color override */
.stExpander svg {
    /* No styling here to keep original color */
}

/* Remove left border highlight */
.stExpander > details[open] > summary {
    color: #00A0FF !important;
    /* No border-left styling */
}
</style>
""", unsafe_allow_html=True)

# Constants for cached data
PERFORMANCE_DATA_PATH = "cached_data/tournament_performance.json"
PERFORMANCE_DATA_TIMESTAMP_PATH = "cached_data/tournament_performance_timestamp.txt"

# Function to load cached tournament performance data
def load_tournament_performance_data():
    """Load tournament performance data from cache if available"""
    try:
        # Check if data file exists
        if os.path.exists(PERFORMANCE_DATA_PATH):
            # Read the data from JSON file
            with open(PERFORMANCE_DATA_PATH, 'r') as f:
                data = json.load(f)
            
            # Convert to DataFrame
            performance_df = pd.DataFrame(data)
            
            # Read timestamp
            if os.path.exists(PERFORMANCE_DATA_TIMESTAMP_PATH):
                with open(PERFORMANCE_DATA_TIMESTAMP_PATH, 'r') as f:
                    timestamp_str = f.read().strip()
                    timestamp = datetime.fromisoformat(timestamp_str)
            else:
                # Default to an hour ago if no timestamp file
                timestamp = datetime.now() - timedelta(hours=1)
            
            return performance_df, timestamp
        
    except Exception as e:
        st.error(f"Error loading cached data: {e}")
    
    # Return empty dataframe and old timestamp if loading fails
    return pd.DataFrame(), datetime.now() - timedelta(hours=2)

# Function to save tournament performance data to cache
def save_tournament_performance_data(performance_df):
    """Save tournament performance data to cache"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(PERFORMANCE_DATA_PATH), exist_ok=True)
        
        # Save data to JSON file
        with open(PERFORMANCE_DATA_PATH, 'w') as f:
            json.dump(performance_df.to_dict(orient='records'), f)
        
        # Save timestamp
        with open(PERFORMANCE_DATA_TIMESTAMP_PATH, 'w') as f:
            f.write(datetime.now().isoformat())
        
        return True
    
    except Exception as e:
        st.error(f"Error saving cached data: {e}")
        return False

# Get the base64 string of your image
img_path = "title_banner.png"
img_base64 = get_base64_image(img_path)

# Define the maximum width you want for the banner
max_banner_width = 800  # Adjust this value as needed

# Display the image with restricted width
st.markdown(f"""
<div style="display: flex; justify-content: center; width: 100%; margin-top:-2rem;">
    <img src="data:image/png;base64,{img_base64}" style="width: 100%; max-width: {max_banner_width}px; height: auto;">
</div>
""", unsafe_allow_html=True)

# Initialize session state and fetch deck list on first load
if 'deck_list' not in st.session_state:
    with st.spinner("Fetching deck list..."):
        st.session_state.deck_list = get_deck_list()
        st.session_state.fetch_time = datetime.now()

# Try to load tournament data from cache first
performance_df, performance_timestamp = load_tournament_performance_data()

# Check if data needs to be updated (if it's older than 1 hour)
if performance_df.empty or (datetime.now() - performance_timestamp) > timedelta(hours=1):
    with st.spinner("Updating tournament performance data..."):
        # Analyze recent performance
        performance_df = analyze_recent_performance(share_threshold=MIN_META_SHARE)
        
        # Save to cache
        save_tournament_performance_data(performance_df)
        
        # Update session state
        performance_timestamp = datetime.now()

# Store in session state
st.session_state.performance_data = performance_df
st.session_state.performance_fetch_time = performance_timestamp

# Also ensure fetch_time exists
if 'fetch_time' not in st.session_state:
    st.session_state.fetch_time = datetime.now()

# Initialize selected deck if not exists
if 'selected_deck_index' not in st.session_state:
    st.session_state.selected_deck_index = None

# Add this with your other session state initializations
if 'deck_to_analyze' not in st.session_state:
    st.session_state.deck_to_analyze = None
    
# Top navigation bar - single row dropdown
# Filter and display popular decks
popular_decks = st.session_state.deck_list[st.session_state.deck_list['share'] >= MIN_META_SHARE]

# Create deck options with formatted names and store mapping
deck_display_names = []
deck_name_mapping = {}  # Maps display name to original name

for _, row in popular_decks.iterrows():
    display_name = format_deck_option(row['deck_name'], row['share'])
    deck_display_names.append(display_name)
    deck_name_mapping[display_name] = row['deck_name']

# Store mapping in session state
st.session_state.deck_name_mapping = deck_name_mapping

# Calculate time ago
time_str = calculate_time_ago(st.session_state.fetch_time)

# Get current set from selected deck or default
current_set = "-"  # Default
if st.session_state.selected_deck_index is not None and st.session_state.selected_deck_index < len(deck_display_names):
    selected_deck_display = deck_display_names[st.session_state.selected_deck_index]
    deck_name = st.session_state.deck_name_mapping[selected_deck_display]
    selected_row = popular_decks[popular_decks['deck_name'] == deck_name].iloc[0]
    current_set = selected_row['set'].upper()

label_text = f"Current Set: {current_set}"
help_text = f"Showing decks with ≥{MIN_META_SHARE}% meta share from Limitless TCG. Updated {time_str}."

# Use on_change callback to handle selection
def on_deck_change():
    selection = st.session_state.deck_select
    if selection:
        st.session_state.selected_deck_index = deck_display_names.index(selection)
    else:
        st.session_state.selected_deck_index = None

# Add this right before the selectbox declaration
if st.session_state.get('deck_to_analyze'):
    # Find the matching display name and index
    for i, (display_name, name) in enumerate([(d, deck_name_mapping[d]) for d in deck_display_names]):
        if name == st.session_state.deck_to_analyze:
            st.session_state.selected_deck_index = i
            # Clear the deck_to_analyze for next time
            st.session_state.deck_to_analyze = None
            break
            
selected_option = st.selectbox(
    label_text,
    deck_display_names,
    index=st.session_state.selected_deck_index,
    placeholder="Select a deck to analyze...",
    help=help_text,
    key="deck_select",
    on_change=on_deck_change
)

# Auto-analyze when selection is made
if selected_option:
    # Get original deck name from mapping
    deck_name = st.session_state.deck_name_mapping[selected_option]
    selected_row = popular_decks[popular_decks['deck_name'] == deck_name].iloc[0]
    set_name = selected_row['set']
    
    current_selection = {
        'deck_name': deck_name,
        'set_name': set_name,
    }
    
    # Update analysis state
    st.session_state.analyze = current_selection

# Final solution: Add these functions to app.py

# Function to get deck key for session state
def get_deck_cache_key(deck_name, set_name):
    """Generate a unique key for caching deck data in session state"""
    return f"deck_cache_{deck_name}_{set_name}"

# Function to get or analyze deck
def get_or_analyze_deck(deck_name, set_name):
    """Get deck from cache or analyze if not cached"""
    cache_key = get_deck_cache_key(deck_name, set_name)
    
    # Check if deck is in cache
    if cache_key in st.session_state.deck_cache:
        return st.session_state.deck_cache[cache_key]
    
    # Analyze deck
    results, total_decks, variant_df = analyze_deck(deck_name, set_name)
    deck_list, deck_info, total_cards, options = build_deck_template(results)
    
    # Store in cache
    st.session_state.deck_cache[cache_key] = {
        'results': results,
        'deck_info': deck_info,
        'total_cards': total_cards,
        'total_decks': total_decks
    }
    
    return st.session_state.deck_cache[cache_key]

# Add to session state initialization
if 'sample_deck_cache' not in st.session_state:
    st.session_state.sample_deck_cache = {}

# Function to get or load a sample deck
def get_or_load_sample_deck(deck_name, set_name):
    """Get sample deck from cache or load if not cached"""
    cache_key = f"sample_deck_{deck_name}_{set_name}"
    
    # Check if sample deck is in cache
    if cache_key in st.session_state.sample_deck_cache:
        return st.session_state.sample_deck_cache[cache_key]
    
    # Load sample deck
    pokemon_cards, trainer_cards = get_sample_deck_for_archetype(deck_name, set_name)
    
    # Store in cache
    st.session_state.sample_deck_cache[cache_key] = {
        'pokemon_cards': pokemon_cards,
        'trainer_cards': trainer_cards
    }
    
    return st.session_state.sample_deck_cache[cache_key]

# Sidebar content - Tournament Performance
st.sidebar.title("Tournament Performance")

# Display performance data if it exists
if not st.session_state.performance_data.empty:
    performance_time_str = calculate_time_ago(st.session_state.performance_fetch_time)
    st.sidebar.write(f"Data updates hourly. Last updated: {performance_time_str}")
    
    # Get the top 10 performing decks
    top_decks = st.session_state.performance_data.head(10)
    
    # For each top deck
    for idx, deck in top_decks.iterrows():
        # Format power index to 2 decimal places
        power_index = round(deck['power_index'], 2)
        
        # Create a plain text expander title with the power index
        with st.sidebar.expander(f"{deck['displayed_name']} ({power_index})", expanded=False):
            # Determine the color class based on power index
            power_class = "positive-index" if power_index > 0 else "negative-index"
            
            # Display performance stats with colored power index inside
            st.markdown(f"""
            <div style="margin-bottom: 10px; font-size: 0.9rem;">
                <p style="margin-bottom: 5px;">Power Index: <span class="{power_class}">{power_index}</span></p>
                <p style="margin-bottom: 5px;"><strong>Record:</strong> {deck['total_wins']}-{deck['total_losses']}-{deck['total_ties']}</p>
                <p style="margin-bottom: 5px;"><strong>Tournaments:</strong> {deck['tournaments_played']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Get sample deck data
            sample_deck = get_or_load_sample_deck(deck['deck_name'], deck['set'])
            
            # Render deck view
            from card_renderer import render_sidebar_deck
            deck_html = render_sidebar_deck(
                sample_deck['pokemon_cards'], 
                sample_deck['trainer_cards'],
                card_width=65
            )
            
            # Display the deck
            st.markdown(deck_html, unsafe_allow_html=True)
else:
    st.sidebar.info("No tournament performance data available")

# Main content area - simplified
if 'analyze' in st.session_state and selected_option:
    deck_info = st.session_state.analyze
    
    # Run analysis
    results, total_decks, variant_df = analyze_deck(deck_info['deck_name'], deck_info['set_name'])
    
    # Create header with images
    header_image = create_deck_header_images(deck_info, results)
    
    if header_image:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: flex-start; margin-bottom: 0rem; margin-top:-1rem">
            <h1 style="margin: 0rem 0 0 0;"><img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 200px; height: auto; margin-bottom:0.2em; margin-right:0.5em;border-radius: 4px;">{format_deck_name(deck_info['deck_name'])}</h1>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.header(format_deck_name(deck_info['deck_name']))
    
    # Display results in tabs
    tab1, tab2, tab3 = st.tabs(["Card Usage", "Deck Template", "Raw Data"])
    
    with tab1:
        # Create two columns for Pokemon and Trainer
        st.write("#### Card Usage & Variants")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.write("##### Pokemon")
            type_cards = results[results['type'] == 'Pokemon']
            
            if not type_cards.empty:
                fig = create_usage_bar_chart(type_cards, 'Pokemon')
                display_chart(fig)
                #st.text(f"{total_decks} decks analyzed")
            else:
                st.info("No Pokemon cards found")

            if not variant_df.empty:
                
                # Import variant renderer
                from card_renderer import render_variant_cards
                
                # Display variant analysis
                for _, row in variant_df.iterrows():
                    with st.expander(f"{row['Card Name']} Variants ({row['Total Decks']} decks)", expanded=False):
                        # Extract set codes and numbers
                        var1 = row['Var1']
                        var2 = row['Var2']
                        
                        var1_set = '-'.join(var1.split('-')[:-1])  # Everything except the last part
                        var1_num = var1.split('-')[-1]         # Just the last part
                        var2_set = '-'.join(var2.split('-')[:-1])
                        var2_num = var2.split('-')[-1]
                        
                        # # Create the 2-column layout
                        var_col1, var_col2 = st.columns([2, 5])
                        
                        # Column 1: Both Variants side by side
                        with var_col1:
                            variant_html = render_variant_cards(var1_set, var1_num, var2_set, var2_num, var1, var2)
                            st.markdown(variant_html, unsafe_allow_html=True)
                        
                        # Column 2: Bar Chart
                        with var_col2:
                            # Create variant bar chart with fixed height
                            fig_var = create_variant_bar_chart(row)
                            display_chart(fig_var) 
        
        with col2:
            st.write("##### Trainer")
            type_cards = results[results['type'] == 'Trainer']
            
            if not type_cards.empty:
                fig = create_usage_bar_chart(type_cards, 'Trainer')
                display_chart(fig)
            else:
                st.info("No Trainer cards found")
    
    with tab2:
        # Use the updated function that returns deck_info
        deck_list, deck_info, total_cards, options = build_deck_template(results)
        
        # Import card renderer
        from card_renderer import render_deck_section, render_option_section
        
        st.write(f"#### Core Cards", unsafe_allow_html=True)
        col1, col2 = st.columns([2, 3])

        with col1:
            # Render Pokemon cards
            render_deck_section(deck_info['Pokemon'], "Pokemon")
        
        with col2:
            # Render Trainer cards
            render_deck_section(deck_info['Trainer'], "Trainer")
        
        # Display flexible slots section
        remaining = 20 - total_cards
        st.write("<br>", unsafe_allow_html=True)
        st.write(f"#### Flexible Slots ({remaining} cards)", unsafe_allow_html=True)
        
        # Sort options by usage percentage (descending) and split by type
        pokemon_options = options[options['type'] == 'Pokemon'].sort_values(by='display_usage', ascending=False)
        trainer_options = options[options['type'] == 'Trainer'].sort_values(by='display_usage', ascending=False)
        
        # Create two columns for flexible slots
        flex_col1, flex_col2 = st.columns([2, 3])
        
        with flex_col1:
            # Render Pokemon options
            render_option_section(pokemon_options, "Pokémon Options")
        
        with flex_col2:
            # Render Trainer options
            render_option_section(trainer_options, "Trainer Options")
    
    with tab3:
        # Main analysis data
        st.write("#### Card Usage Data")
        st.dataframe(results, use_container_width=True)
        
        # Variant analysis data
        if not variant_df.empty:
            st.write("#### Variant Analysis Data")
            st.dataframe(variant_df, use_container_width=True)

else:
    st.info("👆 Select a deck from the dropdown to view detailed analysis")

# Add this at the very end of app.py, after the main content
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
