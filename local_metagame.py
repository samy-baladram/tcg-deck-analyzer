# local_metagame.py
"""
Local tournament data processing for metagame analysis.
Generates metagame tables using local tournament database instead of Limitless API calls.
"""

import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
from config import MIN_META_SHARE, MIN_WIN_RATE

def format_deck_name(deck_name):
    """
    Format deck name for display (same as current system uses).
    Converts "charizard-ex-arcanine-ex" to "Charizard ex / Arcanine ex"
    """
    if not deck_name:
        return deck_name
    
    # Split by hyphens
    parts = deck_name.split('-')
    
    # Process each part
    formatted_parts = []
    current_pokemon = []
    
    for part in parts:
        # Check if this is a suffix (ex, v, vmax, etc.)
        if part.lower() in ['ex', 'v', 'vmax', 'vstar', 'gx']:
            current_pokemon.append(part)
            # Complete this Pokemon and add to formatted_parts
            if current_pokemon:
                pokemon_name = ' '.join(current_pokemon).title()
                # Keep 'ex' lowercase
                pokemon_name = pokemon_name.replace('Ex', 'ex')
                formatted_parts.append(pokemon_name)
                current_pokemon = []
        else:
            # If we have a pending Pokemon, finish it first
            if current_pokemon:
                pokemon_name = ' '.join(current_pokemon).title()
                formatted_parts.append(pokemon_name)
                current_pokemon = []
            
            # Start new Pokemon
            current_pokemon = [part]
    
    # Handle any remaining Pokemon
    if current_pokemon:
        pokemon_name = ' '.join(current_pokemon).title()
        pokemon_name = pokemon_name.replace('Ex', 'ex')
        formatted_parts.append(pokemon_name)
    
    # Join with " / " for multiple Pokemon
    return ' / '.join(formatted_parts)
    
def calculate_power_index(wins, losses):
    """
    Calculate Power Index using same formula as current system.
    
    Args:
        wins: Total wins
        losses: Total losses
        
    Returns:
        float: Power Index value
    """
    total_games = wins + losses
    if total_games == 0:
        return 0.0
    
    # Same formula as current system: (wins - losses) / sqrt(wins + losses)
    power_index = (wins - losses) / np.sqrt(total_games)
    return power_index

def generate_local_metagame_table():
    """
    Generate metagame table using local tournament database (last 3 days only).
    """
    from datetime import datetime, timedelta
    
    try:
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        # Calculate cutoff date (last 3 days)
        cutoff_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Query with date filter
        query = """
        SELECT 
            aa.archetype as deck_name,
            SUM(aa.count) as total_appearances,
            SUM(t.total_players) as total_tournament_players,
            SUM(pp.wins) as total_wins,
            SUM(pp.losses) as total_losses,
            SUM(pp.ties) as total_ties,
            COUNT(pp.id) as best_finishes
        FROM archetype_appearances aa
        JOIN tournaments t ON aa.tournament_id = t.tournament_id
        LEFT JOIN player_performance pp ON aa.tournament_id = pp.tournament_id 
            AND aa.archetype = pp.archetype
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
    Display local metagame table under current table.
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
    
    # Reuse the same display logic from display_tabs.py
    # Add rank column and current deck indicator (similar to current system)
    display_df = local_df.copy()
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
    
    # Try to add Pokemon images (reusing existing logic)
    try:
        # Import the exact function used in display_tabs.py
        from image_processor import extract_pokemon_urls
        
        # Extract Pokemon URLs for each row (same as display_metagame_tab)
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
        print(f"Error processing Pokemon URLs: {e}")
        # Continue without Pokemon images
        display_df['pokemon_url1'] = None
        display_df['pokemon_url2'] = None
    
    # Create final display dataframe with exact same structure
    try:
        # Select and rename columns exactly like display_metagame_tab
        display_cols = {
            'rank_display': 'Rank',
            'displayed_name': 'Deck',
            'share': 'Meta Share %',
            'best_finishes': 'Best Finishes', 
            'total_wins': 'Wins',
            'total_losses': 'Losses',
            'total_ties': 'Ties',
            'win_rate': 'Win %',
            'power_index': 'Index',
        }
        
        final_df = display_df[list(display_cols.keys())].rename(columns=display_cols)
        
        # Add Pokémon image columns in exact same position
        final_df.insert(1, 'Icon1', display_df['pokemon_url1'])
        final_df.insert(2, 'Icon2', display_df['pokemon_url2'])
        
        # Use exact same column config as display_metagame_tab
        st.dataframe(
            final_df,
            use_container_width=True,
            height=850,
            column_config={
                "Rank": st.column_config.TextColumn(
                    "Rank",
                    help="Position in the meta based on Power Index (Local Data)",
                    width="20px"
                ),
                "Icon1": st.column_config.ImageColumn(
                    "Icon 1",
                    help="First archetype Pokémon in the deck",
                    width="20px",
                ),
                "Icon2": st.column_config.ImageColumn(
                    "Icon 2", 
                    help="Second archetype Pokémon in the deck",
                    width="20px",
                ),
                "Deck": st.column_config.TextColumn(
                    "Deck",
                    help="Deck archetype name from local data"
                ),
                "Index": st.column_config.NumberColumn(
                    "Index",
                    help="Performance metric from local tournament data",
                    format="%.2f"
                ),
                "Meta Share %": st.column_config.NumberColumn(
                    "Meta Share %",
                    help="Percentage representation from local tournaments",
                    format="%.2f%%"
                ),
                "Best Finishes": st.column_config.NumberColumn(
                    "Best Finishes",
                    help="Tournament entries from local database"
                ),
                "Win %": st.column_config.NumberColumn(
                    "Win %",
                    help="Win percentage from local match records",
                    format="%.1f%%"
                ),
                "Wins": st.column_config.NumberColumn(
                    "Wins",
                    help="Total wins from local data"
                ),
                "Losses": st.column_config.NumberColumn(
                    "Losses",
                    help="Total losses from local data"
                ),
                "Ties": st.column_config.NumberColumn(
                    "Ties",
                    help="Total ties from local data"
                )
            },
            hide_index=True
        )
        
        st.caption("Generated from local tournament database • Same filtering and calculations as current system")
        
    except Exception as e:
        st.error(f"Error displaying local metagame table: {e}")
        # Show basic version without images
        basic_df = display_df.drop(columns=['Icon1', 'Icon2'], errors='ignore')
        st.dataframe(basic_df, use_container_width=True, hide_index=True)
