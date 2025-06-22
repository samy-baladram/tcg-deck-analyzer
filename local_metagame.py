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
    Generate metagame table using local tournament database.
    
    Returns:
        pd.DataFrame: Metagame table with same structure as current system
    """
    try:
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        # Query to get archetype performance data
        query = """
        SELECT 
            aa.archetype as deck_name,
            aa.archetype as displayed_name,
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
        GROUP BY aa.archetype
        HAVING total_appearances > 0
        ORDER BY total_appearances DESC
        """
        
        df = pd.read_sql_query(query, conn)
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
        import re
        from card_cache import get_header_image_cached
        
        # Extract Pokemon URLs for each row (similar to current display_metagame_tab)
        pokemon_data = []
        for _, row in display_df.iterrows():
            try:
                # Extract primary Pokemon from deck name
                deck_name = row['deck_name']
                pokemon_parts = deck_name.split('-')
                
                if len(pokemon_parts) >= 2:
                    primary_pokemon = pokemon_parts[0]
                    secondary_pokemon = pokemon_parts[1] if len(pokemon_parts) > 1 else primary_pokemon
                    
                    # Get cached images
                    primary_image = get_header_image_cached(primary_pokemon, row['set'])
                    secondary_image = get_header_image_cached(secondary_pokemon, row['set'])
                    
                    if primary_image and secondary_image:
                        pokemon_data.append({
                            'Icon1': f"data:image/png;base64,{primary_image}",
                            'Icon2': f"data:image/png;base64,{secondary_image}"
                        })
                    else:
                        pokemon_data.append({'Icon1': '', 'Icon2': ''})
                else:
                    pokemon_data.append({'Icon1': '', 'Icon2': ''})
                    
            except Exception as e:
                print(f"Error getting images for {row['deck_name']}: {e}")
                pokemon_data.append({'Icon1': '', 'Icon2': ''})
        
        # Add image columns to dataframe
        pokemon_df = pd.DataFrame(pokemon_data)
        display_df = pd.concat([display_df.reset_index(drop=True), pokemon_df], axis=1)
        
    except Exception as e:
        print(f"Error adding Pokemon images: {e}")
        # Continue without images
        display_df['Icon1'] = ''
        display_df['Icon2'] = ''
    
    # Display the table with same styling as current system
    try:
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "rank_display": st.column_config.TextColumn(
                    "Rank",
                    help="Ranking based on Power Index from local tournament data"
                ),
                "Icon1": st.column_config.ImageColumn(
                    "Primary",
                    help="Primary Pokemon in this deck archetype"
                ),
                "Icon2": st.column_config.ImageColumn(
                    "Secondary", 
                    help="Secondary Pokemon in this deck archetype"
                ),
                "displayed_name": st.column_config.TextColumn(
                    "Deck Name",
                    help="Deck archetype name from local data"
                ),
                "power_index": st.column_config.NumberColumn(
                    "Power Index",
                    help="Statistical ranking using local tournament data",
                    format="%.2f"
                ),
                "share": st.column_config.NumberColumn(
                    "Meta Share %",
                    help="Percentage representation from local tournaments",
                    format="%.2f%%"
                ),
                "best_finishes": st.column_config.NumberColumn(
                    "Best Finishes",
                    help="Tournament entries from local database"
                ),
                "win_rate": st.column_config.NumberColumn(
                    "Win %",
                    help="Win percentage from local match records", 
                    format="%.1f%%"
                ),
                "total_wins": st.column_config.NumberColumn(
                    "Wins",
                    help="Total wins from local data"
                ),
                "total_losses": st.column_config.NumberColumn(
                    "Losses",
                    help="Total losses from local data"
                ),
                "total_ties": st.column_config.NumberColumn(
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
