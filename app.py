import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta

# Global variables
BASE_URL = "https://play.limitlesstcg.com"

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_deck_list():
    """Get all available decks with their share percentages"""
    url = f"{BASE_URL}/decks?game=pocket"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    decks = []
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 7:
            deck_link = cells[2].find('a', href=True)
            
            if deck_link and '/decks/' in deck_link['href'] and 'matchup' not in deck_link['href']:
                href = deck_link['href']
                deck_name = href.split('/decks/')[1].split('?')[0]
                
                # Extract set name
                set_name = 'A3'  # Default
                if 'set=' in href:
                    set_name = href.split('set=')[1].split('&')[0]
                
                # Extract share percentage
                share_text = cells[4].text.strip()
                share = float(share_text.replace('%', '')) if '%' in share_text else 0
                
                decks.append({
                    'deck_name': deck_name,
                    'set': set_name,
                    'share': share
                })
    
    return pd.DataFrame(decks).sort_values('share', ascending=False)

@st.cache_data
def get_deck_urls(deck_name, set_name="A3"):
    """Get URLs for all decklists of a specific archetype"""
    url = f"{BASE_URL}/decks/{deck_name}/?game=POCKET&format=standard&set={set_name}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    urls = []
    table = soup.find('table', class_='striped')
    
    if table:
        for row in table.find_all('tr')[1:]:  # Skip header
            last_cell = row.find_all('td')[-1]
            link = last_cell.find('a')
            if link and 'href' in link.attrs:
                urls.append(f"{BASE_URL}{link['href']}")
    
    return urls

def extract_cards(url):
    """Extract cards from a single decklist"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    cards = []
    
    # Find Pokemon and Trainer sections
    for div in soup.find_all('div', class_='heading'):
        section_text = div.text.strip()
        
        if any(section in section_text for section in ['Pokémon', 'Trainer']):
            section_type = 'Pokemon' if 'Pokémon' in section_text else 'Trainer'
            cards_container = div.parent
            
            # Extract each card
            for p in cards_container.find_all('p'):
                card_text = p.get_text(strip=True)
                if card_text:
                    parts = card_text.split(' ', 1)
                    if len(parts) == 2:
                        amount = int(parts[0])
                        
                        # Parse card name and set info
                        if '(' in parts[1] and ')' in parts[1]:
                            name, set_info = parts[1].rsplit(' (', 1)
                            set_info = set_info.rstrip(')')
                            
                            if '-' in set_info:
                                set_code, num = set_info.split('-', 1)
                            else:
                                set_code, num = set_info, ""
                        else:
                            name = parts[1]
                            set_code = num = ""
                        
                        cards.append({
                            'type': section_type,
                            'card_name': name,
                            'amount': amount,
                            'set': set_code,
                            'num': num
                        })
    
    return cards

def analyze_deck(deck_name, set_name="A3"):
    """Main analysis function for a deck archetype"""
    # Get all decklist URLs
    urls = get_deck_urls(deck_name, set_name)
    
    # Show progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Extract cards from all decks
    all_cards = []
    for i, url in enumerate(urls):
        progress_bar.progress((i + 1) / len(urls))
        status_text.text(f"Processing deck {i+1}/{len(urls)}...")
        
        cards = extract_cards(url)
        for card in cards:
            card['deck_num'] = i
        all_cards.extend(cards)
        
        time.sleep(0.3)  # Be nice to the server
    
    status_text.text("Analysis complete!")
    
    # Create dataframe and analyze
    df = pd.DataFrame(all_cards)
    
    # Aggregate card usage
    grouped = df.groupby(['type', 'card_name', 'set', 'num']).agg(
        count_1=('amount', lambda x: sum(x == 1)),
        count_2=('amount', lambda x: sum(x == 2))
    ).reset_index()
    
    # Calculate percentages
    total_decks = len(urls)
    grouped['pct_1'] = (grouped['count_1'] / total_decks * 100).astype(int)
    grouped['pct_2'] = (grouped['count_2'] / total_decks * 100).astype(int)
    grouped['pct_total'] = grouped['pct_1'] + grouped['pct_2']
    
    # Categorize cards
    grouped['category'] = pd.cut(
        grouped['pct_total'], 
        bins=[-1, 25, 70, 100],
        labels=['Tech', 'Standard', 'Core']
    )
    
    # Determine majority count
    grouped['majority'] = grouped.apply(
        lambda row: 2 if row['count_2'] > row['count_1'] else 1,
        axis=1
    )
    
    # Sort results
    grouped = grouped.sort_values(['type', 'pct_total'], ascending=[True, False])
    
    # Analyze variants - pass the raw dataframe instead of URLs
    variant_df = analyze_variants(grouped, df)
    
    return grouped, total_decks, variant_df

def build_deck_template(analysis_df):
    """Build a deck template from analysis results"""
    # Get core cards
    core_cards = analysis_df[analysis_df['category'] == 'Core'].copy()
    
    # Initialize deck
    deck_list = {'Pokemon': [], 'Trainer': []}
    total_cards = 0
    
    # Define flexible core condition
    is_flexible_core = lambda card: ((card['pct_1'] >= 25) and (card['majority'] == 2)) or \
                                   ((card['pct_2'] >= 25) and (card['majority'] == 1))
    
    # Add core cards to deck
    for _, card in core_cards.iterrows():
        count = 1 if is_flexible_core(card) else int(card['majority'])
        total_cards += count
        
        # Format card display based on whether set exists
        if card['set']:
            card_display = f"{count} {card['card_name']} ({card['set']}-{card['num']})"
        else:
            card_display = f"{count} {card['card_name']}"
            
        deck_list[card['type']].append(card_display)
    
    # Get options (standard + flexible core)
    options = pd.concat([
        analysis_df[analysis_df['category'] == 'Standard'],
        analysis_df[(analysis_df['category'] == 'Core') & 
                   (((analysis_df['pct_1'] >= 25) & (analysis_df['majority'] == 2)) |
                    ((analysis_df['pct_2'] >= 25) & (analysis_df['majority'] == 1)))]
    ]).drop_duplicates()
    
    # Add flexible usage column (minimum of pct_1 and pct_2 for flexible core)
    options = options.copy()
    options['display_usage'] = options.apply(
        lambda row: min(row['pct_1'], row['pct_2']) if row['category'] == 'Core' else row['pct_total'], 
        axis=1
    )
    
    return deck_list, total_cards, options

def analyze_variants(result_df, all_cards_df):
    """Analyze variant usage patterns"""
    # Find cards with multiple entries (variants)
    card_counts = result_df.groupby('card_name').size()
    cards_with_variants = card_counts[card_counts > 1].index
    
    variant_summaries = []
    
    for card_name in cards_with_variants:
        # Get all variants of this card
        card_variants = result_df[result_df['card_name'] == card_name]
        
        # For now, handle up to 2 variants (most common case)
        if len(card_variants) > 2:
            st.warning(f"Warning: {card_name} has more than 2 variants. Only first 2 will be analyzed.")
        
        # Get variant IDs
        variant_list = []
        for idx, (_, variant) in enumerate(card_variants.iterrows()):
            if idx < 2:  # Only take first 2 variants
                variant_list.append(f"{variant['set']}-{variant['num']}")
        
        # Initialize summary
        summary = {
            'Card Name': card_name,
            'Total Decks': 0,
            'Variants': ', '.join(variant_list),
            'Both Var1': 0,
            'Both Var2': 0,
            'Mixed': 0,
            'Single Var1': 0,
            'Single Var2': 0
        }
        
        # Analyze usage patterns across decks
        deck_count = 0
        
        # For each deck, check which variants it uses
        for deck_num in all_cards_df['deck_num'].unique():
            deck_cards = all_cards_df[
                (all_cards_df['deck_num'] == deck_num) &
                (all_cards_df['card_name'] == card_name)
            ]
            
            if not deck_cards.empty:
                deck_count += 1
                
                # Check pattern for this deck
                var1_count = 0
                var2_count = 0
                
                for _, card in deck_cards.iterrows():
                    variant_id = f"{card['set']}-{card['num']}"
                    if variant_id == variant_list[0]:
                        var1_count += card['amount']
                    elif len(variant_list) > 1 and variant_id == variant_list[1]:
                        var2_count += card['amount']
                
                # Categorize the pattern
                if var1_count == 2 and var2_count == 0:
                    summary['Both Var1'] += 1
                elif var2_count == 2 and var1_count == 0:
                    summary['Both Var2'] += 1
                elif var1_count == 1 and var2_count == 1:
                    summary['Mixed'] += 1
                elif var1_count == 1 and var2_count == 0:
                    summary['Single Var1'] += 1
                elif var2_count == 1 and var1_count == 0:
                    summary['Single Var2'] += 1
        
        summary['Total Decks'] = deck_count
        variant_summaries.append(summary)
    
    if not variant_summaries:
        return pd.DataFrame()
    
    variant_df = pd.DataFrame(variant_summaries)
    return variant_df.sort_values('Total Decks', ascending=False)
    
# Configure page
st.set_page_config(page_title="Pokémon TCG Pocket Meta Deck Analyzer", layout="wide")

# Hide streamlit branding (optional)
hide_menu_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# Global variables
BASE_URL = "https://play.limitlesstcg.com"

# Main title
st.title("Pokémon TCG Pocket Meta Deck Analyzer")

# Initialize session state and fetch deck list on first load
if 'deck_list' not in st.session_state:
    st.session_state.deck_list = get_deck_list()
    st.session_state.fetch_time = datetime.now()

# Also ensure fetch_time exists (in case it was missing from older sessions)
if 'fetch_time' not in st.session_state:
    st.session_state.fetch_time = datetime.now()

# Top navigation bar - simplified without analyze button
col1, col2 = st.columns([3, 0.5])

with col1:
    # Filter and display popular decks
    popular_decks = st.session_state.deck_list[st.session_state.deck_list['share'] >= 0.5]
    
    # Create deck options without placeholder in the list
    deck_options = [f"{row['deck_name']} ({row['share']:.1f}%)" 
                   for _, row in popular_decks.iterrows()]
    
    # Calculate time ago
    time_diff = datetime.now() - st.session_state.fetch_time
    if time_diff < timedelta(minutes=1):
        time_str = "just now"
    elif time_diff < timedelta(hours=1):
        minutes = int(time_diff.total_seconds() / 60)
        time_str = f"{minutes} minutes ago"
    else:
        hours = int(time_diff.total_seconds() / 3600)
        time_str = f"{hours} hours ago"
    
    label_text = f"Select a deck to analyze (Updated: {time_str}):"
    
    selected_option = st.selectbox(
        label_text,
        deck_options,
        index=None,  # This makes the placeholder show by default
        placeholder="Select a deck...",
        help="Showing decks with ≥0.5% meta share from [Limitless TCG](https://play.limitlesstcg.com/decks?game=POCKET). Analysis will start automatically after selection.",
    )

with col2:
    # Extract deck info from selection and show set
    if selected_option:
        deck_name = selected_option.split(' (')[0]
        selected_row = popular_decks[popular_decks['deck_name'] == deck_name].iloc[0]
        set_name = selected_row['set']
        st.metric("Set", set_name.upper())
    else:
        st.empty()

# Auto-analyze when selection is made
if selected_option:
    deck_name = selected_option.split(' (')[0]
    selected_row = popular_decks[popular_decks['deck_name'] == deck_name].iloc[0]
    set_name = selected_row['set']
    
    current_selection = {
        'deck_name': deck_name,
        'set_name': set_name,
        'option_text': selected_option  # Store the full option text
    }
    
    # Trigger analysis
    st.session_state.analyze = current_selection

st.divider()

# Main content area
if 'analyze' in st.session_state and selected_option:
    deck_info = st.session_state.analyze
    
    # Only analyze if the current selection matches what's in session state
    if deck_info.get('option_text') == selected_option:
        st.header(f"Analyzing {deck_info['deck_name']}")
        
        # Run analysis
        results, total_decks, variant_df = analyze_deck(deck_info['deck_name'], deck_info['set_name'])
        
        # Display results in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Card Usage", "Deck Template", "Variants", "Raw Data"])
        
        with tab1:
            st.subheader(f"Card Usage Summary ({total_decks} decks analyzed)")
            
            # Filter by category
            col1, col2 = st.columns([1, 3])
            with col1:
                category_filter = st.multiselect(
                    "Filter by category:",
                    options=['Core', 'Standard', 'Tech'],
                    default=['Core', 'Standard', 'Tech']
                )
            
            filtered_results = results[results['category'].isin(category_filter)]
            
            # Display cards by type
            for card_type in ['Pokemon', 'Trainer']:
                st.write(f"### {card_type}")
                type_cards = filtered_results[filtered_results['type'] == card_type]
                
                if not type_cards.empty:
                    if card_type == 'Pokemon':
                        # Show set and number for Pokemon
                        display_df = type_cards[['card_name', 'set', 'num', 'pct_total', 'category', 'majority']].copy()
                        display_df.columns = ['Card Name', 'Set', 'Number', 'Usage %', 'Category', 'Majority Count']
                    else:
                        # Hide set and number for Trainer
                        display_df = type_cards[['card_name', 'pct_total', 'category', 'majority']].copy()
                        display_df.columns = ['Card Name', 'Usage %', 'Category', 'Majority Count']
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with tab2:
            st.subheader("Deck Template")
            
            deck_list, total_cards, options = build_deck_template(results)
            
            col1, col2 = st.columns(2)
            
            with col1:
                pokemon_count = sum(int(c.split()[0]) for c in deck_list['Pokemon'])
                st.write(f"### Pokemon ({pokemon_count})")
                #st.write(f"**Total: {pokemon_count}**")
                for card in deck_list['Pokemon']:
                    st.write(f"{card}")
            
            with col2:
                trainer_count = sum(int(c.split()[0]) for c in deck_list['Trainer'])
                st.write(f"### Trainer ({trainer_count})")
                #st.write(f"**Total: {trainer_count}**")
                for card in deck_list['Trainer']:
                    st.write(f"{card}")
            
            st.write("---")
            remaining = 20 - total_cards
            st.write(f"### Flexible Slots ({remaining} cards)")
            st.write("Common choices include:")
            
            # Updated to include set and number
            options_display = options[['card_name', 'set', 'num', 'display_usage', 'type']].copy()
            # Combine card name with set info conditionally
            options_display['Card Display'] = options_display.apply(
                lambda row: f"{row['card_name']} ({row['set']}-{row['num']})" if row['set'] else row['card_name'], 
                axis=1
            )
            # Select columns to show
            final_display = options_display[['Card Display', 'display_usage', 'type']].copy()
            final_display.columns = ['Card Name', 'Usage %', 'Type']
            st.dataframe(final_display, use_container_width=True, hide_index=True)
        
        with tab3:
            st.subheader("Card Variants Analysis")
            
            if not variant_df.empty:
                st.write("This shows how players use different versions of the same card:")
                
                # Display variant analysis
                for _, row in variant_df.iterrows():
                    with st.expander(f"{row['Card Name']} - {row['Total Decks']} decks use this card"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Variants:**")
                            st.write(row['Variants'])
                            
                        with col2:
                            st.write("**Usage Patterns:**")
                            if row['Both Var1'] > 0:
                                st.write(f"- Both copies of Var1: {row['Both Var1']} decks")
                            if row['Both Var2'] > 0:
                                st.write(f"- Both copies of Var2: {row['Both Var2']} decks")
                            if row['Mixed'] > 0:
                                st.write(f"- Mixed (1 of each): {row['Mixed']} decks")
                            if row['Single Var1'] > 0:
                                st.write(f"- Single Var1: {row['Single Var1']} decks")
                            if row['Single Var2'] > 0:
                                st.write(f"- Single Var2: {row['Single Var2']} decks")
                
            else:
                st.info("No cards with variants found in this deck.")
                
        with tab4:
            st.subheader("Raw Analysis Data")
            
            # Main analysis data
            st.write("### Card Usage Data")
            st.dataframe(results, use_container_width=True)
            
            # Variant analysis data
            if not variant_df.empty:
                st.write("### Variant Analysis Data")
                st.dataframe(variant_df, use_container_width=True)
            
            # Download buttons for both datasets
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
