import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

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
    
    return grouped, total_decks

def build_deck_template(analysis_df):
    """Build a deck template from analysis results"""
    core_cards = analysis_df[analysis_df['category'] == 'Core']
    
    deck_list = {'Pokemon': [], 'Trainer': []}
    total_cards = 0
    
    # Add core cards
    for _, card in core_cards.iterrows():
        count = card['majority']
        total_cards += count
        deck_list[card['type']].append(f"{count} {card['card_name']}")
    
    # Get flexible options
    options = analysis_df[
        (analysis_df['category'] == 'Standard') |
        ((analysis_df['category'] == 'Core') & 
         (analysis_df['pct_2'] >= 25) & 
         (analysis_df['majority'] == 1))
    ]
    
    return deck_list, total_cards, options

# Main Streamlit UI
st.title("Pokémon TCG Pocket Meta Deck Analyzer")

# Sidebar for deck selection
with st.sidebar:
    st.header("Deck Selection")
    
    if st.button("Fetch Deck List", type="primary"):
        st.session_state.deck_list = get_deck_list()
    
    # Add context information
    st.caption("Fetches current meta decks with ≥0.5% share from [Limitless TCG](https://play.limitlesstcg.com/decks?game=pocket)")    
    if 'deck_list' in st.session_state:
        popular_decks = st.session_state.deck_list[st.session_state.deck_list['share'] >= 0.5]
        
        # Create deck options
        deck_options = [f"{row['deck_name']} ({row['share']:.1f}%)" 
                       for _, row in popular_decks.iterrows()]
        
        selected_option = st.selectbox("Select Deck:", deck_options)
        
        if selected_option:
            # Extract deck name from selection
            deck_name = selected_option.split(' (')[0]
            selected_row = popular_decks[popular_decks['deck_name'] == deck_name].iloc[0]
            set_name = selected_row['set']
            
            st.info(f"Set: {set_name}")
            
            if st.button("Analyze Deck", type="primary"):
                st.session_state.analyze = {
                    'deck_name': deck_name,
                    'set_name': set_name
                }

# Main content area
if 'analyze' in st.session_state:
    deck_info = st.session_state.analyze
    
    st.header(f"Analyzing {deck_info['deck_name']}")
    
    # Run analysis
    results, total_decks = analyze_deck(deck_info['deck_name'], deck_info['set_name'])
    
    # Display results in tabs
    tab1, tab2, tab3 = st.tabs(["Card Usage", "Deck Template", "Raw Data"])
    
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
                display_df = type_cards[['card_name', 'pct_total', 'category', 'majority']].copy()
                display_df.columns = ['Card Name', 'Usage %', 'Category', 'Majority Count']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("Deck Template")
        
        deck_list, total_cards, options = build_deck_template(results)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### Pokemon")
            pokemon_count = sum(int(c.split()[0]) for c in deck_list['Pokemon'])
            st.write(f"**Total: {pokemon_count}**")
            for card in deck_list['Pokemon']:
                st.write(f"{card}")
        
        with col2:
            st.write("### Trainer")
            trainer_count = sum(int(c.split()[0]) for c in deck_list['Trainer'])
            st.write(f"**Total: {trainer_count}**")
            for card in deck_list['Trainer']:
                st.write(f"{card}")
        
        st.write("---")
        remaining = 20 - total_cards
        st.write(f"### Flexible Slots ({remaining} cards)")
        st.write("Common choices include:")
        
        options_display = options[['card_name', 'pct_total', 'type']].copy()
        options_display.columns = ['Card Name', 'Usage %', 'Type']
        st.dataframe(options_display, use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("Raw Analysis Data")
        st.dataframe(results, use_container_width=True)
        
        # Download button
        csv = results.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"{deck_info['deck_name']}_analysis.csv",
            mime="text/csv"
        )

else:
    st.info("👈 Click 'Fetch Deck List' in the sidebar to start")
