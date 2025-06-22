# local_metagame.py - Fixed version

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from formatters import format_deck_name, extract_pokemon_urls

# Configuration constants
MIN_META_SHARE = 0.5  # Minimum meta share threshold (0.5%)
MIN_WIN_RATE = 45.0   # Minimum win rate threshold (45%)

def calculate_power_index(wins, losses):
    """
    Calculate Power Index using Wilson score confidence interval
    """
    if wins + losses == 0:
        return 0
    
    n = wins + losses
    p = wins / n
    z = 1.96  # 95% confidence interval
    
    # Wilson score interval
    denominator = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    interval = z * (p * (1 - p) / n + z**2 / (4 * n**2))**0.5
    
    lower_bound = (center - interval) / denominator
    return lower_bound * 100

def generate_local_metagame_table():
    """
    Generate metagame table from local tournament database
    """
    try:
        # Connect to database
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        # Set cutoff date (last 30 days)
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Query for archetype performance data
        query = """
        SELECT 
            aa.archetype as deck_name,
            COUNT(DISTINCT aa.tournament_id) as tournaments_played,
            COUNT(*) as total_appearances,
            SUM(t.total_players) as total_tournament_players,
            SUM(aa.wins) as total_wins,
            SUM(aa.losses) as total_losses,
            SUM(aa.ties) as total_ties
        FROM archetype_appearances aa
        JOIN tournaments t ON aa.tournament_id = t.tournament_id
        WHERE t.date >= ?
        GROUP BY aa.archetype
        HAVING total_appearances > 0
        ORDER BY total_appearances DESC
        """
        
        df = pd.read_sql_query(query, conn, params=[cutoff_date])
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        # Calculate meta share percentage
        total_players_all_tournaments = df['total_tournament_players'].sum()
        df['share'] = (df['total_appearances'] / total_players_all_tournaments) * 100
        
        # Calculate win rate
        total_games = df['total_wins'] + df['total_losses'] + df['total_ties']
        df['win_rate'] = ((df['total_wins'] + 0.5 * df['total_ties']) / total_games * 100).fillna(0)
        
        # Calculate Power Index
        df['power_index'] = df.apply(lambda row: calculate_power_index(row['total_wins'], row['total_losses']), axis=1)
        
        # Filter by thresholds (same as current system)
        df_filtered = df[
            (df['share'] >= MIN_META_SHARE) & 
            (df['win_rate'] >= MIN_WIN_RATE)
        ].copy()
        
        # Sort by Power Index (descending)
        df_filtered = df_filtered.sort_values('power_index', ascending=False)
        
        # Add formatted display names
        df_filtered['displayed_name'] = df_filtered['deck_name'].apply(format_deck_name)
        
        # Add set information (defaulting to current set)
        df_filtered['set'] = 'A3a'  # Current set placeholder
        
        # Round numerical values for display
        df_filtered['power_index'] = df_filtered['power_index'].round(2)
        df_filtered['share'] = df_filtered['share'].round(2)
        df_filtered['win_rate'] = df_filtered['win_rate'].round(1)
        
        return df_filtered
        
    except Exception as e:
        print(f"Error generating local metagame table: {e}")
        return pd.DataFrame()

def display_local_metagame_comparison():
    """
    Display local metagame table that mimics the display_tabs.py implementation.
    Uses existing functions for images and formatting.
    """
    # Generate local metagame table
    with st.spinner("Generating local metagame analysis..."):
        local_df = generate_local_metagame_table()
    
    if local_df.empty:
        st.warning("No local tournament data available")
        return
    
    # Display separator and header
    st.markdown("---")
    st.markdown("### 🔬 **Local Data Processing (Testing)**")
    st.caption("This table is generated using local tournament database instead of Limitless API calls")
    
    # Create display dataframe (similar to display_tabs.py)
    display_df = local_df.copy()
    
    # Add rank column 
    display_df['rank_int'] = range(1, len(display_df) + 1)
    
    # Get current deck name for highlighting
    current_deck_name = None
    if 'analyze' in st.session_state:
        current_deck_name = st.session_state.analyze.get('deck_name', None)
    
    # Add rank display with current deck indicator
    display_df['rank_display'] = display_df.apply(
        lambda row: f"➡️ {row['rank_int']}" if row['deck_name'] == current_deck_name else str(row['rank_int']), 
        axis=1
    )
    
    # Extract Pokemon URLs for each row (same as display_metagame_tab)
    try:
        pokemon_data = []
        for _, row in display_df.iterrows():
            try:
                url1, url2 = extract_pokemon_urls(row['deck_name'])
                pokemon_data.append({'pokemon_url1': url1, 'pokemon_url2': url2})
            except Exception as e:
                print(f"Error extracting Pokemon URLs for {row['deck_name']}: {e}")
                pokemon_data.append({'pokemon_url1': None, 'pokemon_url2': None})
        
        # Convert to DataFrame and join with display_df
        pokemon_df = pd.DataFrame(pokemon_data)
        display_df = pd.concat([display_df.reset_index(drop=True), pokemon_df], axis=1)
        
    except Exception as e:
        st.error(f"Error processing Pokemon URLs: {str(e)}")
        # Continue without Pokemon images
        display_df['pokemon_url1'] = None
        display_df['pokemon_url2'] = None
    
    # Select and rename columns for display (same structure as display_tabs.py)
    display_cols = {
        'rank_display': 'Rank',
        'displayed_name': 'Deck',
        'share': 'Meta Share %',
        'tournaments_played': 'Best Finishes',
        'total_wins': 'Wins',
        'total_losses': 'Losses',
        'total_ties': 'Ties',
        'win_rate': 'Win %',
        'power_index': 'Index',
    }
    
    # Create final display dataframe
    try:
        final_df = display_df[list(display_cols.keys())].rename(columns=display_cols)
        
        # Add Pokemon image columns in the same positions as display_tabs.py
        final_df.insert(1, 'Icon1', display_df['pokemon_url1'])
        final_df.insert(2, 'Icon2', display_df['pokemon_url2'])
        
        # Display dataframe with same column configuration as display_tabs.py
        st.dataframe(
            final_df,
            use_container_width=True,
            height=400,  # Smaller height for comparison table
            column_config={
                "Rank": st.column_config.TextColumn(
                    "Rank",
                    help="Position in the meta based on Power Index",
                    width="small"
                ),
                "Icon1": st.column_config.ImageColumn(
                    "Icon 1",
                    help="First archetype Pokémon in the deck",
                    width="small",
                ),
                "Icon2": st.column_config.ImageColumn(
                    "Icon 2", 
                    help="Second archetype Pokémon in the deck",
                    width="small",
                ),
                "Deck": st.column_config.TextColumn(
                    "Deck",
                    help="Deck archetype name"
                ),
                "Meta Share %": st.column_config.NumberColumn(
                    "Meta Share %",
                    help="Percentage of total tournament appearances",
                    format="%.2f%%"
                ),
                "Best Finishes": st.column_config.NumberColumn(
                    "Best Finishes",
                    help="Number of tournaments with recorded results"
                ),
                "Wins": st.column_config.NumberColumn(
                    "Wins",
                    help="Total wins across all tournaments"
                ),
                "Losses": st.column_config.NumberColumn(
                    "Losses", 
                    help="Total losses across all tournaments"
                ),
                "Ties": st.column_config.NumberColumn(
                    "Ties",
                    help="Total ties across all tournaments"
                ),
                "Win %": st.column_config.NumberColumn(
                    "Win %",
                    help="Overall win percentage across all matches",
                    format="%.1f%%"
                ),
                "Index": st.column_config.NumberColumn(
                    "Index",
                    help="Performance metric: The Wilson score (see sidebar for details)",
                    format="%.2f"
                ),
            },
            hide_index=True
        )
        
    except Exception as e:
        # Fallback to simpler version if there's an issue with images
        st.error(f"Error displaying styled dataframe with images: {str(e)}")
        st.write("Showing basic version without styling and images:")
        
        # Remove image columns for fallback
        basic_df = display_df[list(display_cols.keys())].rename(columns=display_cols)
        st.dataframe(
            basic_df,
            use_container_width=True,
            column_config={
                "Win %": st.column_config.NumberColumn(
                    "Win %",
                    format="%.1f%%",
                ),
                "Meta Share %": st.column_config.NumberColumn(
                    "Meta Share %",
                    format="%.2f%%"
                ),
                "Index": st.column_config.NumberColumn(
                    "Index",
                    format="%.2f"
                ),
            },
            hide_index=True
        )
    
    # Add footer note
    st.caption("Generated from local tournament database. Data may differ from live API results.")
