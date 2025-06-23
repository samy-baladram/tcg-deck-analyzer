"""
Meta Table Module - Sophisticated table showing archetype performance with trends
"""

import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
import json
import re
from io import BytesIO
import base64


def fetch_top_archetypes(limit=20):
    """
    Fetch top archetypes with meta share and basic performance data
    
    Args:
        limit: Number of top archetypes to return
        
    Returns:
        DataFrame with archetype performance data
    """
    try:
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        query = """
        SELECT 
            aa.archetype as deck_name,
            COUNT(DISTINCT aa.tournament_id) as tournament_count,
            SUM(aa.player_count) as total_players,
            SUM(aa.total_wins) as total_wins,
            SUM(aa.total_losses) as total_losses,
            SUM(aa.total_ties) as total_ties,
            (CAST(SUM(aa.player_count) AS FLOAT) / 
             (SELECT SUM(player_count) FROM archetype_appearances aa2 
              JOIN tournaments t2 ON aa2.tournament_id = t2.tournament_id 
              WHERE t2.date >= (SELECT MAX(date) FROM tournaments) - 30) * 100) as current_share
        FROM archetype_appearances aa
        JOIN tournaments t ON aa.tournament_id = t.tournament_id
        WHERE t.date >= date('now', '-30 days')
        GROUP BY aa.archetype
        HAVING total_players >= 10
        ORDER BY current_share DESC
        LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        
        # Calculate win rate
        total_games = df['total_wins'] + df['total_losses'] + df['total_ties']
        df['win_rate'] = ((df['total_wins'] + 0.5 * df['total_ties']) / total_games * 100).fillna(0)
        
        return df
        
    except Exception as e:
        print(f"Error fetching top archetypes: {e}")
        return pd.DataFrame()


def fetch_archetype_trend_data(deck_name, days_back=30):
    """
    Fetch daily meta share data for a specific archetype
    
    Args:
        deck_name: The archetype name
        days_back: Number of days to look back
        
    Returns:
        DataFrame with daily meta percentages
    """
    try:
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        query = """
        WITH daily_totals AS (
            SELECT 
                t.date,
                SUM(aa.player_count) as total_players
            FROM tournaments t
            JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id
            WHERE t.date >= date('now', '-{} days')
            GROUP BY t.date
        ),
        archetype_daily AS (
            SELECT 
                t.date,
                COALESCE(SUM(aa.player_count), 0) as archetype_players
            FROM tournaments t
            LEFT JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id 
                AND aa.archetype = ?
            WHERE t.date >= date('now', '-{} days')
            GROUP BY t.date
        )
        SELECT 
            dt.date,
            ad.archetype_players,
            dt.total_players,
            CASE 
                WHEN dt.total_players > 0 
                THEN (CAST(ad.archetype_players AS FLOAT) / dt.total_players) * 100
                ELSE 0 
            END as meta_percentage
        FROM daily_totals dt
        JOIN archetype_daily ad ON dt.date = ad.date
        WHERE dt.total_players > 0
        ORDER BY dt.date
        """.format(days_back, days_back)
        
        df = pd.read_sql_query(query, conn, params=[deck_name])
        conn.close()
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        return df
        
    except Exception as e:
        print(f"Error fetching trend data for {deck_name}: {e}")
        return pd.DataFrame()


def calculate_moving_averages(trend_df):
    """
    Calculate 7-day and 3-day moving averages
    
    Args:
        trend_df: DataFrame with daily meta percentages
        
    Returns:
        Dict with current averages and trend comparison
    """
    if trend_df.empty or len(trend_df) < 3:
        return {
            'ma_7d': 0.0,
            'ma_3d': 0.0,
            'trend_change': 0.0,
            'trend_direction': 'neutral'
        }
    
    # Sort by date to ensure proper order
    trend_df = trend_df.sort_values('date')
    
    # Calculate moving averages
    trend_df['ma_7d'] = trend_df['meta_percentage'].rolling(window=7, min_periods=1).mean()
    trend_df['ma_3d'] = trend_df['meta_percentage'].rolling(window=3, min_periods=1).mean()
    
    # Get most recent values
    current_ma_7d = trend_df['ma_7d'].iloc[-1] if not trend_df['ma_7d'].empty else 0.0
    current_ma_3d = trend_df['ma_3d'].iloc[-1] if not trend_df['ma_3d'].empty else 0.0
    
    # Calculate trend change (7-day vs 3-day)
    trend_change = current_ma_7d - current_ma_3d
    
    # Determine trend direction
    if abs(trend_change) < 0.1:
        trend_direction = 'neutral'
    elif trend_change > 0:
        trend_direction = 'up'
    else:
        trend_direction = 'down'
    
    return {
        'ma_7d': round(current_ma_7d, 2),
        'ma_3d': round(current_ma_3d, 2),
        'trend_change': round(trend_change, 2),
        'trend_direction': trend_direction
    }


def generate_sparkline_chart(trend_df, deck_name):
    """
    Generate a small sparkline chart for embedding in table
    
    Args:
        trend_df: DataFrame with trend data
        deck_name: Name of the archetype
        
    Returns:
        Base64 encoded image string or None
    """
    if trend_df.empty:
        return None
    
    try:
        # Create minimal sparkline chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=trend_df['date'],
            y=trend_df['meta_percentage'],
            mode='lines',
            line=dict(color='#00D4AA', width=2),
            showlegend=False,
            hovertemplate='%{y:.1f}%<extra></extra>'
        ))
        
        # Minimal layout for sparkline
        fig.update_layout(
            width=120,
            height=40,
            margin=dict(t=5, l=5, r=5, b=5),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=False,
                showticklabels=False,
                showline=False,
                zeroline=False
            ),
            yaxis=dict(
                showgrid=False,
                showticklabels=False,
                showline=False,
                zeroline=False
            )
        )
        
        # Convert to base64 image
        img_bytes = fig.to_image(format="png", width=120, height=40)
        img_base64 = base64.b64encode(img_bytes).decode()
        
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        print(f"Error generating sparkline for {deck_name}: {e}")
        return None


def extract_pokemon_names(deck_name):
    """
    Extract Pokemon names from deck archetype name
    
    Args:
        deck_name: The deck archetype string
        
    Returns:
        List of Pokemon names
    """
    # Remove common suffixes and split
    cleaned_name = re.sub(r'\s+(deck|control|aggro|combo|ex|gx|v|vmax|vstar)$', '', deck_name, flags=re.IGNORECASE)
    
    # Split by common delimiters
    parts = re.split(r'[/\-\s]+', cleaned_name)
    
    # Filter out empty strings and common words
    exclude_words = {'and', 'the', 'with', 'deck', 'ex', 'gx', 'v', 'vmax', 'vstar'}
    pokemon_names = [part.strip() for part in parts if part.strip().lower() not in exclude_words and len(part.strip()) > 1]
    
    return pokemon_names[:2]  # Return up to 2 Pokemon names


def get_pokemon_image_url(pokemon_name, position=1):
    """
    Generate Pokemon image URL
    
    Args:
        pokemon_name: Name of the Pokemon
        position: Position in deck (1 or 2) for different image variants
        
    Returns:
        Image URL string
    """
    # Clean up the Pokemon name
    clean_name = pokemon_name.lower().replace(' ', '').replace('-', '')
    
    # Map common variations
    name_variations = {
        'pikachu': 'pikachu',
        'charizard': 'charizard',
        'mewtwo': 'mewtwo',
        'mew': 'mew',
        'alakazam': 'alakazam',
        'machamp': 'machamp',
        'gengar': 'gengar',
        'dragonite': 'dragonite',
        'articuno': 'articuno',
        'zapdos': 'zapdos',
        'moltres': 'moltres'
    }
    
    mapped_name = name_variations.get(clean_name, clean_name)
    
    # Use different image sources for variety
    if position == 1:
        return f"https://img.pokemondb.net/artwork/large/{mapped_name}.jpg"
    else:
        return f"https://assets.pokemon.com/assets/cms2/img/pokedex/full/{mapped_name}.png"


def build_meta_table_data():
    """
    Build complete data for the meta table
    
    Returns:
        DataFrame ready for display
    """
    print("Building meta table data...")
    
    # 1. Get top archetypes
    archetypes_df = fetch_top_archetypes(20)
    
    if archetypes_df.empty:
        print("No archetype data found")
        return pd.DataFrame()
    
    # 2. Build complete table data
    table_data = []
    
    for _, row in archetypes_df.iterrows():
        deck_name = row['deck_name']
        print(f"Processing {deck_name}...")
        
        # Get trend data
        trend_df = fetch_archetype_trend_data(deck_name)
        
        # Calculate moving averages
        ma_data = calculate_moving_averages(trend_df)
        
        # Generate sparkline chart
        chart_img = generate_sparkline_chart(trend_df, deck_name)
        
        # Extract Pokemon info
        pokemon_names = extract_pokemon_names(deck_name)
        
        # Build row data
        row_data = {
            'deck_name': deck_name,
            'display_name': deck_name.replace('-', ' ').title(),
            'current_share': round(row['current_share'], 2),
            'win_rate': round(row['win_rate'], 1),
            'ma_7d': ma_data['ma_7d'],
            'ma_3d': ma_data['ma_3d'],
            'trend_change': ma_data['trend_change'],
            'trend_direction': ma_data['trend_direction'],
            'chart_img': chart_img,
            'pokemon_1': pokemon_names[0] if len(pokemon_names) > 0 else '',
            'pokemon_2': pokemon_names[1] if len(pokemon_names) > 1 else '',
            'icon_1_url': get_pokemon_image_url(pokemon_names[0], 1) if len(pokemon_names) > 0 else '',
            'icon_2_url': get_pokemon_image_url(pokemon_names[1], 2) if len(pokemon_names) > 1 else ''
        }
        
        table_data.append(row_data)
    
    # Convert to DataFrame
    result_df = pd.DataFrame(table_data)
    
    print(f"Built meta table with {len(result_df)} archetypes")
    return result_df


def format_trend_indicator(trend_change, trend_direction):
    """
    Format trend change as colored indicator
    
    Args:
        trend_change: Numerical change value
        trend_direction: Direction string ('up', 'down', 'neutral')
        
    Returns:
        Formatted string with emoji indicator
    """
    if trend_direction == 'up':
        return f"📈 +{abs(trend_change):.2f}%"
    elif trend_direction == 'down':
        return f"📉 -{abs(trend_change):.2f}%"
    else:
        return f"➡️ {trend_change:.2f}%"


def prepare_display_dataframe(meta_df):
    """
    Prepare the DataFrame for Streamlit display with proper formatting
    
    Args:
        meta_df: Raw meta table data
        
    Returns:
        Formatted DataFrame ready for st.dataframe()
    """
    if meta_df.empty:
        return pd.DataFrame()
    
    # Create display DataFrame
    display_df = meta_df.copy()
    
    # Add rank column
    display_df['rank'] = range(1, len(display_df) + 1)
    
    # Format trend indicators
    display_df['trend_indicator'] = display_df.apply(
        lambda row: format_trend_indicator(row['trend_change'], row['trend_direction']), 
        axis=1
    )
    
    # Reorder columns for display
    display_columns = [
        'rank',
        'display_name', 
        'chart_img',
        'ma_7d',
        'trend_indicator',
        'current_share',
        'win_rate'
    ]
    
    return display_df[display_columns]


def display_meta_overview_table():
    """
    Main function to display the complete meta overview table in sidebar tab 2
    
    This is the single function to import and use in your sidebar tab.
    Handles all data loading, processing, and display.
    """
    
    # Add loading message
    with st.spinner("Loading meta overview data..."):
        # Build the complete meta table data
        meta_df = build_meta_table_data()
    
    if meta_df.empty:
        st.warning("No meta data available at this time.")
        return
    
    # Prepare data for display
    display_df = prepare_display_dataframe(meta_df)
    
    # Display the table header
    st.write("##### Meta Overview - Top 20 Archetypes")
    
    try:
        # Configure column display
        column_config = {
            "rank": st.column_config.NumberColumn(
                "#",
                help="Current meta ranking",
                width="small"
            ),
            "display_name": st.column_config.TextColumn(
                "Archetype",
                help="Deck archetype name",
                width="medium"
            ),
            "chart_img": st.column_config.ImageColumn(
                "Trend",
                help="Meta share trend over last 30 days",
                width="small"
            ),
            "ma_7d": st.column_config.NumberColumn(
                "7-Day Avg",
                help="7-day moving average meta share",
                format="%.2f%%",
                width="small"
            ),
            "trend_indicator": st.column_config.TextColumn(
                "Trend",
                help="Change: 7-day average vs 3-day average",
                width="small"
            ),
            "current_share": st.column_config.NumberColumn(
                "Current Share",
                help="Current meta share percentage",
                format="%.2f%%",
                width="small"
            ),
            "win_rate": st.column_config.NumberColumn(
                "Win Rate",
                help="Overall win rate percentage",
                format="%.1f%%",
                width="small"
            )
        }
        
        # Display the dataframe with custom styling
        st.dataframe(
            display_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=600  # Fixed height for scrolling
        )
        
        # Add explanatory notes
        st.caption(
            "📈 **Trend indicators**: Compare 7-day moving average to 3-day average. "
            "Green 📈 = rising trend, Red 📉 = declining trend, Gray ➡️ = stable. "
            "Data refreshed daily from tournament results."
        )
        
    except Exception as e:
        st.error(f"Error displaying meta table: {str(e)}")
        
        # Fallback to basic table without images
        st.write("Showing simplified version:")
        basic_df = display_df.drop(columns=['chart_img'], errors='ignore')
        st.dataframe(
            basic_df,
            use_container_width=True,
            hide_index=True
        )
