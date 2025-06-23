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

def fetch_archetype_trend_data_detailed(deck_name, days_back=7):
    """
    Fetch daily meta share data for a specific archetype with individual day columns
    
    Args:
        deck_name: The archetype name
        days_back: Number of days to look back
        
    Returns:
        Dict with daily percentages for last 7 days
    """
    try:
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        query = """
        WITH daily_totals AS (
            SELECT 
                t.date,
                SUM(aa.count) as total_players
            FROM tournaments t
            JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id
            WHERE t.date >= date('now', '-{} days')
            GROUP BY t.date
        ),
        archetype_daily AS (
            SELECT 
                t.date,
                COALESCE(SUM(aa.count), 0) as archetype_players
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
        ORDER BY dt.date DESC
        LIMIT 7
        """.format(days_back, days_back)
        
        df = pd.read_sql_query(query, conn, params=[deck_name])
        conn.close()
        
        # Create dict with last 7 days
        daily_data = {}
        for i in range(7):
            day_key = f'day_{i+1}'  # day_1 = today, day_2 = yesterday, etc.
            if i < len(df):
                daily_data[day_key] = round(df.iloc[i]['meta_percentage'], 2)
            else:
                daily_data[day_key] = 0.0
                
        return daily_data
        
    except Exception as e:
        print(f"Error fetching detailed trend data for {deck_name}: {e}")
        return {f'day_{i+1}': 0.0 for i in range(7)}


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
        WITH total_players_recent AS (
            SELECT SUM(aa.count) as total_count
            FROM archetype_appearances aa
            JOIN tournaments t ON aa.tournament_id = t.tournament_id
            WHERE t.date >= date('now', '-30 days')
        )
        SELECT 
            aa.archetype as deck_name,
            COUNT(DISTINCT aa.tournament_id) as tournament_count,
            SUM(aa.count) as total_players,
            SUM(pp.wins) as total_wins,
            SUM(pp.losses) as total_losses,
            SUM(pp.ties) as total_ties,
            (CAST(SUM(aa.count) AS FLOAT) / tp.total_count * 100) as current_share
        FROM archetype_appearances aa
        JOIN tournaments t ON aa.tournament_id = t.tournament_id
        LEFT JOIN player_performance pp ON aa.tournament_id = pp.tournament_id 
            AND aa.archetype = pp.archetype
        CROSS JOIN total_players_recent tp
        WHERE t.date >= date('now', '-30 days')
        GROUP BY aa.archetype, tp.total_count
        HAVING total_players >= 10
        ORDER BY current_share DESC
        LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        
        # Calculate win rate (handle case where no performance data exists)
        df['total_wins'] = df['total_wins'].fillna(0)
        df['total_losses'] = df['total_losses'].fillna(0)
        df['total_ties'] = df['total_ties'].fillna(0)
        
        total_games = df['total_wins'] + df['total_losses'] + df['total_ties']
        df['win_rate'] = ((df['total_wins'] + 0.5 * df['total_ties']) / total_games * 100).fillna(50.0)
        
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
                SUM(aa.count) as total_players
            FROM tournaments t
            JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id
            WHERE t.date >= date('now', '-{} days')
            GROUP BY t.date
        ),
        archetype_daily AS (
            SELECT 
                t.date,
                COALESCE(SUM(aa.count), 0) as archetype_players
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


def calculate_cumulative_shares(trend_df):
    """
    Calculate cumulative shares over 7 days vs 3 days for trend comparison
    
    Args:
        trend_df: DataFrame with daily meta percentages
        
    Returns:
        Dict with cumulative shares and trend comparison
    """
    if trend_df.empty or len(trend_df) < 3:
        return {
            'cumulative_7d': 0.0,
            'cumulative_3d': 0.0,
            'trend_change': 0.0,
            'trend_direction': 'neutral'
        }
    
    # Sort by date to ensure proper order (most recent first)
    trend_df = trend_df.sort_values('date', ascending=False)
    
    # Get last 7 days and last 3 days
    last_7_days = trend_df.head(7)
    last_3_days = trend_df.head(3)
    
    # Calculate cumulative shares (sum of daily percentages)
    cumulative_7d = last_7_days['meta_percentage'].sum()
    cumulative_3d = last_3_days['meta_percentage'].sum()
    
    # Calculate trend change (compare 3-day vs 7-day average)
    avg_7d = cumulative_7d / 7 if len(last_7_days) > 0 else 0
    avg_3d = cumulative_3d / 3 if len(last_3_days) > 0 else 0
    
    trend_change = avg_3d - avg_7d  # Positive = recent trend is higher
    
    # Determine trend direction
    if abs(trend_change) < 0.1:
        trend_direction = 'neutral'
    elif trend_change > 0:
        trend_direction = 'up'  # Recent 3 days higher than 7-day average
    else:
        trend_direction = 'down'  # Recent 3 days lower than 7-day average
    
    return {
        'cumulative_7d': round(cumulative_7d, 2),
        'cumulative_3d': round(cumulative_3d, 2),
        'avg_7d': round(avg_7d, 2),
        'avg_3d': round(avg_3d, 2),
        'trend_change': round(trend_change, 2),
        'trend_direction': trend_direction
    }


def build_meta_table_data():
    """
    Build complete data for the meta table with daily breakdown
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
        
        # Calculate cumulative shares instead of moving averages
        cumulative_data = calculate_cumulative_shares(trend_df)
        
        # Get detailed daily data for last 7 days
        daily_data = fetch_archetype_trend_data_detailed(deck_name)
        
        # Generate sparkline chart
        chart_img = generate_sparkline_chart(trend_df, deck_name)
        
        # Build row data with daily breakdowns
        row_data = {
            'deck_name': deck_name,
            'display_name': deck_name.replace('-', ' ').title(),
            'current_share': round(row['current_share'], 2),
            'win_rate': round(row['win_rate'], 1),
            'cumulative_7d': cumulative_data['cumulative_7d'],
            'cumulative_3d': cumulative_data['cumulative_3d'],
            'avg_7d': cumulative_data['avg_7d'],
            'avg_3d': cumulative_data['avg_3d'],
            'trend_change': cumulative_data['trend_change'],
            'trend_direction': cumulative_data['trend_direction'],
            'chart_img': chart_img,
            # Add daily data
            'day_1': daily_data['day_1'],  # Today
            'day_2': daily_data['day_2'],  # Yesterday  
            'day_3': daily_data['day_3'],  # 2 days ago
            'day_4': daily_data['day_4'],  # 3 days ago
            'day_5': daily_data['day_5'],  # 4 days ago
            'day_6': daily_data['day_6'],  # 5 days ago
            'day_7': daily_data['day_7'],  # 6 days ago
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

def wrap_text(sentences, width):
    """
    This function takes a list of sentences and a width and returns a list of lists,
    where each inner list contains the wrapped lines for the corresponding sentence.

    Args:
    sentences: A list of strings, where each string is a sentence.
    width: An integer representing the maximum character width per line.

    Returns:
    A list of lists, where each inner list contains wrapped lines for a sentence.
    """
    wrapped_sentences = []
    for sentence in sentences:
        # Split the sentence on word boundaries (ensures no mid-word breaks)
        words = re.findall(r"\b\w+\b", sentence)
        lines = []
        current_line = []
        for word in words:
            # Check if adding the word exceeds the line width
            if len(" ".join(current_line + [word])) <= width:
                current_line.append(word)
            else:
                # Add the current line and start a new one
                lines.append(" ".join(current_line))
                current_line = [word]
        # Add the last line (if any)
        if current_line:
            lines.append(" ".join(current_line))
        wrapped_sentences.append("<br>".join(lines))
    return wrapped_sentences
    
def display_meta_overview_table():
    """
    Main function to display the complete meta overview table in sidebar tab 2
    """
    
    # Add loading message
    with st.spinner("Loading meta overview data..."):
        # Build the complete meta table data
        meta_df = build_meta_table_data()
    
    if meta_df.empty:
        st.warning("No meta data available at this time.")
        return
    
    # SORT BY 7-DAY AVERAGE INSTEAD OF CURRENT SHARE
    meta_df = meta_df.sort_values('avg_7d', ascending=False).reset_index(drop=True)
    
    # Add rank column AFTER sorting
    meta_df['rank_int'] = range(1, len(meta_df) + 1)
    
    # Rest of the function remains the same...
    # Format trend indicators
    meta_df['trend_indicator'] = meta_df.apply(
        lambda row: format_trend_indicator(row['trend_change'], row['trend_direction']), 
        axis=1
    )
    
    # PROPER DECK NAME FORMATTING: Use the same format_deck_name function as Tournament Performance Data
    try:
        from formatters import format_deck_name
        meta_df['formatted_deck_name'] = meta_df['deck_name'].apply(format_deck_name)
    except Exception as e:
        print(f"Error formatting deck names: {e}")
        # Fallback to simple formatting
        meta_df['formatted_deck_name'] = meta_df['deck_name'].str.replace('-', ' ').str.title()
    
    # MIMICK EXACT LOGIC FROM display_metagame_tab: Extract Pokemon URLs
    try:
        # Import the exact same function used in Tournament Performance Data
        from formatters import extract_pokemon_urls
        
        # Extract Pokemon URLs for each row (same as display_metagame_tab)
        pokemon_data = []
        for _, row in meta_df.iterrows():
            try:
                url1, url2 = extract_pokemon_urls(row['deck_name'])
                pokemon_data.append({'pokemon_url1': url1, 'pokemon_url2': url2})
            except Exception as e:
                print(f"Error extracting Pokemon URLs for {row['deck_name']}: {e}")
                pokemon_data.append({'pokemon_url1': None, 'pokemon_url2': None})
        
        # Convert to DataFrame and join with meta_df
        pokemon_df = pd.DataFrame(pokemon_data)
        meta_df = pd.concat([meta_df.reset_index(drop=True), pokemon_df], axis=1)
        
    except Exception as e:
        st.error(f"Error processing Pokemon URLs: {str(e)}")
        # Continue without Pokemon images
        meta_df['pokemon_url1'] = None
        meta_df['pokemon_url2'] = None
    
    # Display the table header
    st.write("##### Meta Overview - Top 20 Archetypes")
    
    try:
        # Create final display dataframe with daily columns for debugging
        final_df = pd.DataFrame({
            'Icon1': meta_df['pokemon_url1'],
            'Icon2': meta_df['pokemon_url2'], 
            'Deck': meta_df['formatted_deck_name'],
            'Today': meta_df['day_1'],
            'Day-1': meta_df['day_2'], 
            'Day-2': meta_df['day_3'],
            'Day-3': meta_df['day_4'],
            'Day-4': meta_df['day_5'],
            'Day-5': meta_df['day_6'],
            'Day-6': meta_df['day_7'],
            '7-Day Avg': meta_df['avg_7d'],        # Changed from ma_7d
            '3-Day Avg': meta_df['avg_3d'],        # Added 3-day average
            'Change': meta_df['trend_indicator'],
            'Win %': meta_df['win_rate']
        })
        
        # Configure column display
        column_config = {
            "Icon1": st.column_config.ImageColumn("Icon 1", width=60),
            "Icon2": st.column_config.ImageColumn("Icon 2", width=60),
            "Deck": st.column_config.TextColumn("Deck", width=150),
            "Today": st.column_config.NumberColumn("Today", format="%.2f%%", width=60),
            "Day-1": st.column_config.NumberColumn("Day-1", format="%.2f%%", width=60),
            "Day-2": st.column_config.NumberColumn("Day-2", format="%.2f%%", width=60),
            "Day-3": st.column_config.NumberColumn("Day-3", format="%.2f%%", width=60),
            "Day-4": st.column_config.NumberColumn("Day-4", format="%.2f%%", width=60),
            "Day-5": st.column_config.NumberColumn("Day-5", format="%.2f%%", width=60),
            "Day-6": st.column_config.NumberColumn("Day-6", format="%.2f%%", width=60),
            "7-Day Avg": st.column_config.NumberColumn("7-Day Avg", format="%.2f%%", width=60),
            "3-Day Avg": st.column_config.NumberColumn("3-Day Avg", format="%.2f%%", width=60),
            "Change": st.column_config.TextColumn("Change", width=60),
            "Win %": st.column_config.NumberColumn("Win %", format="%.1f%%", width=60)
        }
        
        # Display the dataframe
        st.dataframe(
            final_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=600
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
        basic_df = meta_df[['rank_int', 'formatted_deck_name', 'ma_7d', 'trend_indicator', 'current_share', 'win_rate']].copy()
        basic_df.columns = ['Rank', 'Deck', '7-Day Avg', 'Change', 'Share %', 'Win %']
        st.dataframe(
            basic_df,
            use_container_width=True,
            hide_index=True
        )
