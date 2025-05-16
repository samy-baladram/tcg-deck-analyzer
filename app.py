# app.py
"""Main Streamlit application for TCG Deck Analyzer"""

import streamlit as st
from datetime import datetime, timedelta

# Import all modules
from config import MIN_META_SHARE, CACHE_TTL, IMAGE_BASE_URL
from scraper import get_deck_list
from analyzer import analyze_deck, build_deck_template
from formatters import format_deck_name, format_deck_option
from image_processor import get_base64_image, create_deck_header_images, get_card_thumbnail
from visualizations import create_usage_bar_chart, display_chart, create_variant_bar_chart
from utils import calculate_time_ago, format_card_display

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

/* Even more specific selector targeting the text */
div[data-testid="stTabs"] [data-baseweb="tab-list"] [data-testid="stMarkdownContainer"] p {
    font-size: 18px !important;
    padding: 8px 16px !important;
}

</style>
""", unsafe_allow_html=True)

# Main title
st.image("title_banner.png", use_container_width=True)

# Initialize session state and fetch deck list on first load
if 'deck_list' not in st.session_state:
    with st.spinner("Fetching deck list..."):
        st.session_state.deck_list = get_deck_list()
        st.session_state.fetch_time = datetime.now()

# Also ensure fetch_time exists
if 'fetch_time' not in st.session_state:
    st.session_state.fetch_time = datetime.now()

# Initialize selected deck if not exists
if 'selected_deck_index' not in st.session_state:
    st.session_state.selected_deck_index = None

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

# Main content area
if 'analyze' in st.session_state and selected_option:
    deck_info = st.session_state.analyze
    
    # Run analysis
    results, total_decks, variant_df = analyze_deck(deck_info['deck_name'], deck_info['set_name'])
    
    # Create header with images
    header_image = create_deck_header_images(deck_info, results)
    
    if header_image:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: flex-start; margin-bottom: 1rem;">
            <img src="data:image/png;base64,{header_image}" style="width: 100%; max-width: 500px; height: auto; margin-bottom:-3.5em">
            <h2 style="margin: 0.5rem 0 0 0;">{format_deck_name(deck_info['deck_name'])}</h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.header(format_deck_name(deck_info['deck_name']))
    
    # Display results in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Card Usage", "Deck Template", "Variants", "Raw Data"])
    
    with tab1:
        #st.subheader(f"Card Usage Summary")
        
        # Create two columns for Pokemon and Trainer
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("#### Pokemon")
            type_cards = results[results['type'] == 'Pokemon']
            
            if not type_cards.empty:
                fig = create_usage_bar_chart(type_cards, 'Pokemon')
                display_chart(fig)
                st.text(f"{total_decks} decks analyzed")
            else:
                st.info("No Pokemon cards found")
        
        with col2:
            st.write("#### Trainer")
            type_cards = results[results['type'] == 'Trainer']
            
            if not type_cards.empty:
                fig = create_usage_bar_chart(type_cards, 'Trainer')
                display_chart(fig)
            else:
                st.info("No Trainer cards found")
    
    with tab2:
        #st.subheader("Deck Template")
        
        deck_list, total_cards, options = build_deck_template(results)
        
        col1, col2 = st.columns(2)
        
        with col1:
            pokemon_count = sum(int(c.split()[0]) for c in deck_list['Pokemon'])
            st.write(f"#### Pokemon ({pokemon_count})")
            for card in deck_list['Pokemon']:
                st.write(f"{card}")
        
        with col2:
            trainer_count = sum(int(c.split()[0]) for c in deck_list['Trainer'])
            st.write(f"#### Trainer ({trainer_count})")
            for card in deck_list['Trainer']:
                st.write(f"{card}")
        
        #st.write("---")
        remaining = 20 - total_cards
        st.write(f"### Flexible Slots ({remaining} cards)")
        st.write("Common choices include:")
        
        # Format options for display
        options_display = options[['card_name', 'set', 'num', 'display_usage', 'type']].copy()
        options_display['Card Display'] = options_display.apply(
            lambda row: format_card_display(row['card_name'], row['set'], row['num']), 
            axis=1
        )
        final_display = options_display[['Card Display', 'display_usage', 'type']].copy()
        final_display.columns = ['Card Name', 'Usage %', 'Type']
        st.dataframe(final_display, use_container_width=True, hide_index=True)
    
    with tab3:
        if not variant_df.empty:
            st.write("This shows how players use different versions of the same card:")
            
            # Import needed functions
            from image_processor import format_card_number, IMAGE_BASE_URL
            
            # Display variant analysis
            for _, row in variant_df.iterrows():
                with st.expander(f"{row['Card Name']} - {row['Total Decks']} decks use this card"):
                    # Extract set codes and numbers
                    var1 = row['Var1']
                    var2 = row['Var2']
                    
                    var1_parts = var1.split('-')
                    var2_parts = var2.split('-')
                    
                    var1_set = var1_parts[0] if len(var1_parts) > 0 else ""
                    var1_num = var1_parts[1] if len(var1_parts) > 1 else ""
                    var2_set = var2_parts[0] if len(var2_parts) > 0 else ""
                    var2_num = var2_parts[1] if len(var2_parts) > 1 else ""
                    
                    # Format numbers for URL
                    formatted_num1 = format_card_number(var1_num) if var1_num else ""
                    formatted_num2 = format_card_number(var2_num) if var2_num else ""
                    
                    # Create the 2-column layout
                    col1, col2 = st.columns([1, 1])
                    
                    # Column 1: Both Variants side by side
                    with col1:
                        st.markdown(f"""
                        <div style="height:240px; display:flex; justify-content:space-between; margin-top:-20px;">
                            <!-- Variant 1 -->
                            <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                                <div style="text-align:center; margin-bottom:2px;"><strong>{var1}</strong></div>
                                {
                                    f'<img src="{IMAGE_BASE_URL}/{var1_set}/{var1_set}_{formatted_num1}_EN.webp" style="max-height:180px; max-width:100%; object-fit:contain; border:1px solid #ddd; border-radius:5px;">' 
                                    if var1_set and formatted_num1 else
                                    '<div style="border:1px dashed #ddd; border-radius:5px; padding:20px; color:#888; text-align:center; width:80%;">Image not available</div>'
                                }
                            </div>
                            <!-- Variant 2 -->
                            <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                                <div style="text-align:center; margin-bottom:2px;"><strong>{var2}</strong></div>
                                {
                                    f'<img src="{IMAGE_BASE_URL}/{var2_set}/{var2_set}_{formatted_num2}_EN.webp" style="max-height:180px; max-width:100%; object-fit:contain; border:1px solid #ddd; border-radius:5px;">' 
                                    if var2_set and formatted_num2 else
                                    '<div style="border:1px dashed #ddd; border-radius:5px; padding:20px; color:#888; text-align:center; width:80%;">Image not available</div>'
                                }
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Column 2: Bar Chart
                    with col2:
                        # Create variant bar chart with fixed height
                        fig = create_variant_bar_chart(row)
                        fig.update_layout(height=220)
                        display_chart(fig)
        else:
            st.info("No cards with variants found in this deck.")
    
    with tab4:
        #st.subheader("Raw Analysis Data")
        
        # Main analysis data
        st.write("#### Card Usage Data")
        st.dataframe(results, use_container_width=True)
        
        # Variant analysis data
        if not variant_df.empty:
            st.write("#### Variant Analysis Data")
            st.dataframe(variant_df, use_container_width=True)
        
        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            csv_main = results.to_csv(index=False)
            st.download_button(
                label="Download Card Usage CSV",
                data=csv_main,
                file_name=f"{deck_info['deck_name']}_analysis.csv",
                mime="text/csv"
            )
        
        with col2:
            if not variant_df.empty:
                csv_variant = variant_df.to_csv(index=False)
                st.download_button(
                    label="Download Variant Analysis CSV",
                    data=csv_variant,
                    file_name=f"{deck_info['deck_name']}_variants.csv",
                    mime="text/csv"
                )

else:
    st.info("👆 Select a deck from the dropdown to view detailed analysis")

# Add this at the very end of app.py, after the main content
st.markdown("---")
st.markdown("""
<div style="text-align: center; font-size: 0.8em; color: #777; margin-top: 1rem; padding: 1rem;">
    <p><strong>Disclaimer:</strong></p>
    <p>The literal and graphical information presented on this website about the Pokémon Trading Card Game Pocket, 
    including card images and text, is copyright The Pokémon Company, DeNA Co., Ltd., and/or Creatures, Inc. 
    This website is not produced by, endorsed by, supported by, or affiliated with any of those copyright holders.</p>
    <p>Deck composition data is sourced from <a href="https://play.limitlesstcg.com" target="_blank">Limitless TCG</a>, 
    which aggregates tournament results and decklists from competitive play. Card images are retrieved from 
    Limitless TCG's image repository. This tool is intended for educational and analytical purposes only.</p>
    <p>This is an independent, fan-made project and is not affiliated with Limitless TCG, The Pokémon Company, 
    or any other official entities.</p>
</div>
""", unsafe_allow_html=True)
