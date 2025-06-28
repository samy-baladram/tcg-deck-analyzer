"""
Meta Table Module - Clean archetype performance analysis with corrected counting logic
"""

# Add these imports at the top of meta_table.py if not already present
import math
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


class MetaAnalyzer:
    """Base class for meta analysis operations"""
    
    def __init__(self, db_path="meta_analysis/tournament_meta.db"):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)


class ArchetypeAnalyzer(MetaAnalyzer):
    """Handle archetype-specific analysis with corrected counting logic"""
    
    def fetch_top_archetypes_by_share(self, period_days=7, limit=20):
        """
        Fetch top archetypes based on recent share data - CORRECTED VERSION
        
        Args:
            period_days: Days to look back for analysis
            limit: Number of top archetypes to return
            
        Returns:
            DataFrame with archetype performance data
        """
        query = """
        WITH total_players_in_period AS (
            SELECT SUM(t.total_players) as total_count
            FROM tournaments t
            WHERE t.date >= date('now', '-{} days')
        ),
        archetype_share AS (
            SELECT 
                aa.archetype,
                SUM(aa.count) as archetype_count,
                COUNT(DISTINCT aa.tournament_id) as tournament_count,
                SUM(pp.wins) as total_wins,
                SUM(pp.losses) as total_losses,  
                SUM(pp.ties) as total_ties
            FROM archetype_appearances aa
            JOIN tournaments t ON aa.tournament_id = t.tournament_id
            LEFT JOIN player_performance pp ON aa.tournament_id = pp.tournament_id 
                AND aa.archetype = pp.archetype
            WHERE t.date >= date('now', '-{} days')
            GROUP BY aa.archetype
            HAVING archetype_count >= 5
        )
        SELECT 
            archetype as deck_name,
            tournament_count,
            archetype_count as total_players,
            total_wins,
            total_losses,
            total_ties,
            (CAST(archetype_count AS FLOAT) / tp.total_count * 100) as share
        FROM archetype_share
        CROSS JOIN total_players_in_period tp
        ORDER BY share DESC
        LIMIT ?
        """.format(period_days, period_days)
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[limit])
            
            # Calculate win rates
            df = self._calculate_win_rates(df)
            return df
            
        except Exception as e:
            print(f"Error fetching top archetypes: {e}")
            return pd.DataFrame()
    
    def calculate_period_comparison(self, deck_name):
        """
        Compare archetype performance between different time periods - CORRECTED VERSION
        
        Args:
            deck_name: The archetype name
            
        Returns:
            Dict with period comparison data
        """
        # Get 7-day data
        data_7d = self._get_period_data(deck_name, 7)
        # Get 3-day data  
        data_3d = self._get_period_data(deck_name, 3)
        
        share_7d = data_7d['share']
        share_3d = data_3d['share']
        trend_change = share_3d - share_7d
        
        return {
            'archetype_count_7d': data_7d['archetype_count'],
            'total_count_7d': data_7d['total_count'],
            'archetype_count_3d': data_3d['archetype_count'],
            'total_count_3d': data_3d['total_count'],
            'share_7d': round(share_7d, 2),
            'share_3d': round(share_3d, 2),
            'trend_change': round(trend_change, 2),
            'trend_direction': self._get_trend_direction(trend_change)
        }
    
    def get_daily_trend_data(self, deck_name, days_back=7):
        """
        Get daily meta share data for trend analysis - CORRECTED VERSION
        
        Args:
            deck_name: The archetype name
            days_back: Number of days to analyze
            
        Returns:
            Dict with daily percentages
        """
        # CRITICAL FIX: Use tournaments.total_players for daily totals
        query = """
        WITH daily_tournament_totals AS (
            SELECT 
                t.date,
                SUM(t.total_players) as total_players
            FROM tournaments t
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
        FROM daily_tournament_totals dt
        JOIN archetype_daily ad ON dt.date = ad.date
        WHERE dt.total_players > 0
        ORDER BY dt.date DESC
        LIMIT ?
        """.format(days_back, days_back)
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[deck_name, days_back])
            
            daily_data = {}
            for i in range(days_back):
                day_key = f'day_{i+1}'
                if i < len(df):
                    daily_data[day_key] = round(df.iloc[i]['meta_percentage'], 2)
                else:
                    daily_data[day_key] = 0.0
                    
            return daily_data
            
        except Exception as e:
            print(f"Error fetching daily trend data for {deck_name}: {e}")
            return {f'day_{i+1}': 0.0 for i in range(days_back)}
    
    def _get_period_data(self, deck_name, days):
        """Get data for a specific time period - CORRECTED VERSION"""
        # CRITICAL FIX: Use tournaments.total_players instead of sum of archetype appearances
        query = """
        WITH period_tournaments AS (
            SELECT tournament_id, total_players
            FROM tournaments t
            WHERE t.date >= date('now', '-{} days')
        ),
        archetype_count AS (
            SELECT COALESCE(SUM(aa.count), 0) as archetype_count
            FROM archetype_appearances aa
            WHERE aa.tournament_id IN (SELECT tournament_id FROM period_tournaments)
              AND aa.archetype = ?
        ),
        total_count AS (
            SELECT SUM(total_players) as total_count
            FROM period_tournaments
        )
        SELECT 
            ac.archetype_count,
            tc.total_count
        FROM archetype_count ac
        CROSS JOIN total_count tc
        """.format(days)
        
        try:
            with self.get_connection() as conn:
                result = pd.read_sql_query(query, conn, params=[deck_name])
            
            archetype_count = result.iloc[0]['archetype_count'] or 0
            total_count = result.iloc[0]['total_count'] or 0
            share = (archetype_count / total_count * 100) if total_count > 0 else 0
            
            return {
                'archetype_count': int(archetype_count),
                'total_count': int(total_count),
                'share': share
            }
            
        except Exception as e:
            print(f"Error getting {days}-day data for {deck_name}: {e}")
            return {'archetype_count': 0, 'total_count': 0, 'share': 0.0}
    
    def _calculate_win_rates(self, df):
        """Calculate win rates for archetype data"""
        df = df.copy()
        df['total_wins'] = df['total_wins'].fillna(0)
        df['total_losses'] = df['total_losses'].fillna(0)
        df['total_ties'] = df['total_ties'].fillna(0)
        
        total_games = df['total_wins'] + df['total_losses'] + df['total_ties']
        df['win_rate'] = ((df['total_wins'] + 0.5 * df['total_ties']) / total_games * 100).fillna(50.0)
        
        return df
    
    def _get_trend_direction(self, trend_change):
        """Determine trend direction from change value"""
        if abs(trend_change) < 0.1:
            return 'neutral'
        elif trend_change > 0:
            return 'up'
        else:
            return 'down'


class MetaTableBuilder(MetaAnalyzer):
    """Build formatted meta table data with corrected calculations"""
    
    def __init__(self, db_path="meta_analysis/tournament_meta.db"):
        super().__init__(db_path)
        self.archetype_analyzer = ArchetypeAnalyzer(db_path)

    def build_complete_meta_table(self, limit=20):
        """
        Build complete meta table with all analysis data - CORRECTED VERSION
        
        Args:
            limit: Number of archetypes to include
            
        Returns:
            DataFrame with complete meta analysis including performance data
        """
        print("Building meta table data...")
        
        # Get top archetypes based on 7-day share
        archetypes_df = self.archetype_analyzer.fetch_top_archetypes_by_share(7, limit * 2)
        
        if archetypes_df.empty:
            print("No archetype data found")
            return pd.DataFrame()
        
        table_data = []
        
        for _, row in archetypes_df.iterrows():
            deck_name = row['deck_name']
            #print(f"Processing {deck_name}...")
            
            # Get period comparison data
            period_data = self.archetype_analyzer.calculate_period_comparison(deck_name)
            
            # Get daily trend data
            daily_data = self.archetype_analyzer.get_daily_trend_data(deck_name)
            
            # Get performance data (wins, losses, ties)
            try:
                import sqlite3
                with sqlite3.connect(self.db_path) as conn:
                    perf_query = """
                    SELECT 
                        COALESCE(SUM(pp.wins), 0) as total_wins,
                        COALESCE(SUM(pp.losses), 0) as total_losses,
                        COALESCE(SUM(pp.ties), 0) as total_ties
                    FROM player_performance pp
                    JOIN tournaments t ON pp.tournament_id = t.tournament_id
                    WHERE pp.archetype = ?
                    AND t.date >= date('now', '-7 days')
                    """
                    
                    perf_result = pd.read_sql_query(perf_query, conn, params=[deck_name])
                    
                    wins = int(perf_result['total_wins'].iloc[0] or 0)
                    losses = int(perf_result['total_losses'].iloc[0] or 0)
                    ties = int(perf_result['total_ties'].iloc[0] or 0)
                    
            except Exception as e:
                print(f"Error fetching performance data for {deck_name}: {e}")
                wins = losses = ties = 0
            
            # Build complete row data
            row_data = {
                'deck_name': deck_name,
                'formatted_deck_name': self._format_deck_name(deck_name),
                'current_share': round(row['share'], 2),
                'win_rate': round(row['win_rate'], 1),
                'wins': wins,           # Add performance data
                'losses': losses,       # Add performance data  
                'ties': ties,           # Add performance data
                **period_data,          # Add all period comparison data
                **daily_data            # Add all daily trend data
            }
            
            table_data.append(row_data)
        
        # Convert to DataFrame and sort by 7-day share
        result_df = pd.DataFrame(table_data)
        result_df = result_df.sort_values('share_7d', ascending=False).reset_index(drop=True)
        result_df['rank'] = range(1, len(result_df) + 1)
        
        print(f"Built meta table with {len(result_df)} archetypes including performance data")
        return result_df.head(limit)
    
    def _format_deck_name(self, deck_name):
        """Format deck name for display"""
        return deck_name.replace('-', ' ').title()


class MetaDisplayFormatter:
    """Format meta data for Streamlit display"""
    
    @staticmethod
    def format_trend_indicator(trend_change, trend_direction):
        """Format trend change as colored indicator"""
        if trend_direction == 'up':
            return f"+{abs(trend_change):.2f}%"
        elif trend_direction == 'down':
            return f"-{abs(trend_change):.2f}%"
        else:
            return f"{trend_change:.2f}%"
    
    @staticmethod
    def prepare_display_dataframe(meta_df):
        """Prepare DataFrame for Streamlit display with Pokemon URLs"""
        if meta_df.empty:
            return pd.DataFrame()
        
        # Add trend indicators
        meta_df['trend_indicator'] = meta_df.apply(
            lambda row: MetaDisplayFormatter.format_trend_indicator(
                row['trend_change'], row['trend_direction']
            ), 
            axis=1
        )
        
        # Format deck names
        try:
            from formatters import format_deck_name
            meta_df['formatted_deck_name'] = meta_df['deck_name'].apply(format_deck_name)
        except ImportError:
            meta_df['formatted_deck_name'] = meta_df['display_name']
        
        # Add Pokemon URLs
        try:
            from formatters import extract_pokemon_urls
            pokemon_data = []
            for _, row in meta_df.iterrows():
                try:
                    url1, url2 = extract_pokemon_urls(row['deck_name'])
                    pokemon_data.append({'pokemon_url1': url1, 'pokemon_url2': url2})
                except Exception as e:
                    print(f"Error extracting Pokemon URLs for {row['deck_name']}: {e}")
                    pokemon_data.append({'pokemon_url1': None, 'pokemon_url2': None})
            
            pokemon_df = pd.DataFrame(pokemon_data)
            meta_df = pd.concat([meta_df.reset_index(drop=True), pokemon_df], axis=1)
            
        except ImportError:
            meta_df['pokemon_url1'] = None
            meta_df['pokemon_url2'] = None
        
        return meta_df


# def display_meta_overview_table():
#     """Main function to display the meta overview table with styled change column"""
    
#     with st.spinner("Loading meta overview data..."):
#         builder = MetaTableBuilder()
#         meta_df = builder.build_complete_meta_table(20)
    
#     if meta_df.empty:
#         st.warning("No meta data available at this time.")
#         return
    
#     # Format for display
#     formatter = MetaDisplayFormatter()
#     meta_df = formatter.prepare_display_dataframe(meta_df)
    
#     # Clean up trend indicators - remove emojis and %
#     def clean_trend_indicator(trend_indicator):
#         """Remove emojis and % symbol, return clean number"""
#         if not trend_indicator:
#             return "0.00"
        
#         # Remove emojis, %, and clean up
#         clean_str = trend_indicator.replace("📈", "").replace("📉", "").replace("➡️", "").replace("%", "").strip()
        
#         # Ensure proper +/- formatting
#         if not clean_str.startswith(('+', '-')) and clean_str != "0.00":
#             if "+" in trend_indicator or "📈" in trend_indicator:
#                 clean_str = "+" + clean_str
#             elif "-" in trend_indicator or "📉" in trend_indicator:
#                 clean_str = "-" + clean_str
        
#         return clean_str
    
#     # Calculate recent vs overall ratio
#     def calculate_ratio(row):
#         """Calculate recent (3d) vs overall (7d) ratio"""
#         if row['share_7d'] == 0:
#             return "0.0x"
#         ratio = row['share_3d'] / row['share_7d']
#         return f"{ratio:.1f}x"
    
#     # Clean the trend indicators and add ratio
#     meta_df['trend_indicator'] = meta_df['trend_indicator'].apply(clean_trend_indicator)
#     meta_df['ratio'] = meta_df.apply(calculate_ratio, axis=1)
    
#     # Display table header
#     st.write("##### Meta Overview - Top 20 Archetypes Share")
    
#     try:
#         # Create final display DataFrame
#         final_df = pd.DataFrame({
#             '': meta_df['pokemon_url1'],      # Empty for icon1
#             ' ': meta_df['pokemon_url2'],     # Space for icon2  
#             'Deck': meta_df['formatted_deck_name'],
#             '%': meta_df['share_7d'],         # Just % symbol
#             #'Δ': meta_df['trend_indicator'],  # Delta for change
#             'R': meta_df['ratio'],            # Recent vs overall ratio
#         })
        
#         # Define styling function for Change column
#         def style_change_column(val):
#             """Apply conditional styling to Change column"""
#             if not val or val == "0.00":
#                 return 'color: #888888; font-size: 0.8rem; font-weight: normal;'
#             elif val.startswith('+'):
#                 return 'color: #06B804; font-size: 0.8rem; font-weight: bold;'
#             elif val.startswith('-'):
#                 return 'color: #FD6C6C; font-size: 0.8rem; font-weight: bold;'
#             else:
#                 return 'color: #888888; font-size: 0.8rem; font-weight: normal;'
        
#         # Define styling function for Ratio column
#         def style_ratio_column(val):
#             """Apply conditional styling to Ratio column"""
#             if not val or val == "0.0x":
#                 return 'color: #888888; font-size: 0.8rem; font-weight: normal;'
            
#             # Extract numeric value
#             try:
#                 ratio_num = float(val.replace('x', ''))
#                 if ratio_num > 1.2:
#                     return 'color: #06B804; font-size: 0.8rem; font-weight: bold;'  # Strong green
#                 elif ratio_num > 1.0:
#                     return 'color: #06B804; font-size: 0.8rem; font-weight: normal;'  # Light green
#                 elif ratio_num < 0.8:
#                     return 'color: #FD6C6C; font-size: 0.8rem; font-weight: bold;'  # Strong red
#                 elif ratio_num < 1.0:
#                     return 'color: #FD6C6C; font-size: 0.8rem; font-weight: normal;'  # Light red
#                 else:
#                     return 'color: #888888; font-size: 0.8rem; font-weight: normal;'  # Neutral
#             except:
#                 return 'color: #888888; font-size: 0.8rem; font-weight: normal;'
        
#         # Apply styling to the dataframe
#         styled_df = final_df.style.applymap(
#             style_change_column, 
#             subset=['R']
#         ).applymap(
#             style_ratio_column,
#             subset=['R']
#         )
        
#         # Configure column display
#         column_config = {
#             '': st.column_config.ImageColumn(
#                 "", width=25, help="Primary Pokemon"
#             ),
#             ' ': st.column_config.ImageColumn(
#                 "", width=25, help="Secondary Pokemon"
#             ),
#             'Deck': st.column_config.TextColumn("Deck", width=140),  # Slightly smaller
#             '%': st.column_config.NumberColumn(
#                 "%", width=40, help="Meta share percentage", format="%.2f"
#             ),
#             'Δ': st.column_config.TextColumn(
#                 "Δ", width=30, help="Trend change"
#             ),
#             'R': st.column_config.TextColumn(
#                 "R", width=30, help="Recent (3d) vs Overall (7d) ratio"
#             )
#         }
        
#         # Display the styled dataframe
#         st.dataframe(
#             styled_df,
#             column_config=column_config,
#             hide_index=True,
#             height=750,
#             use_container_width=True
#         )
        
#     except Exception as e:
#         st.error(f"Error displaying meta table: {str(e)}")
#         print(f"Display error: {e}")
import random

def display_meta_overview_table():
    """Main function to display the meta overview table with trend line charts"""
    
    with st.spinner("Loading meta overview data..."):
        builder = MetaTableBuilder()
        meta_df = builder.build_complete_meta_table(40)
    
    if meta_df.empty:
        st.warning("No meta data available at this time.")
        return
    
    # Format for display
    formatter = MetaDisplayFormatter()
    meta_df = formatter.prepare_display_dataframe(meta_df)
    
    # Add daily trend data for line charts
    def get_trend_history(deck_name):
        """Get 7-day percentage history for line chart"""
        try:
            # Use the existing builder's analyzer to get daily trend data
            daily_data = builder.archetype_analyzer.get_daily_trend_data(deck_name, days_back=7)
            
            # Extract percentage values - keys are day_1, day_2, etc.
            percentages = []
            for i in range(1, 8):  # day_1 through day_7
                day_key = f'day_{i}'
                percentages.append(daily_data.get(day_key, 0))
            
            # Reverse to show chronological order (oldest to newest)
            percentages.reverse()
            return percentages
            
        except Exception as e:
            print(f"Error getting trend for {deck_name}: {e}")
            # Return sample trend data for demo
            return [random.uniform(0, 5) for _ in range(7)]
    
    # Add trend history column
    meta_df['trend_history'] = meta_df['deck_name'].apply(get_trend_history)
    
    # Display table header
    #st.write("##### Top 30 Archetypes Trend")
    
    try:
        # Create final display DataFrame
        final_df = pd.DataFrame({
            'Icon1': meta_df['pokemon_url1'],
            'Icon2': meta_df['pokemon_url2'], 
            'Deck': meta_df['formatted_deck_name'],
            'Share-7d': meta_df['share_7d'],
            'Trend': meta_df['trend_history'],  # Line chart data
            'R': meta_df.apply(lambda row: row['share_3d'] / row['share_7d'] if row['share_7d'] > 0 else 0, axis=1),
            'Win %': meta_df['win_rate']
        })
        
        # Configure column display
        column_config = {
            'Icon1': st.column_config.ImageColumn(
                "1", width=25, help="Primary Pokemon"
            ),
            'Icon2': st.column_config.ImageColumn(
                "2", width=25, help="Secondary Pokemon"
            ),
            'Deck': st.column_config.TextColumn("Deck", width=140),
            'Share-7d': st.column_config.NumberColumn(
                "Share-7d", width=60, help="Meta share in last 7 days", format="%.2f%%"
            ),
            'Trend': st.column_config.LineChartColumn(
                "7d Trend", 
                width=100,
                help="7-day percentage change trend",
                y_min=0
            ),
            'R': st.column_config.NumberColumn(
                "R", width=40, help="Recent vs Overall ratio", format="%.1fx"
            ),
            'Win %': st.column_config.NumberColumn(
                "Win %", width=50, help="Win rate percentage", format="%.1f%%"
            )
        }
        
        # Simple styling for R column based on value
        def style_dataframe(df):
            def color_r_column(val):
                if val > 1:
                    return 'color: #06B804; font-weight: bold;'  # Green
                else:
                    return 'color: #FD6C6C; font-weight: bold;'  # Red
            
            return df.style.applymap(color_r_column, subset=['R'])
        
        styled_df = style_dataframe(final_df)
        
        # Display the data table
        st.dataframe(
            styled_df,
            column_config=column_config,
            hide_index=True,
            height=1428,
            #height=1088,
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Error displaying meta table: {str(e)}")
        print(f"Display error: {e}")


# Legacy function aliases for backward compatibility
def build_meta_table_data():
    """Legacy function - use MetaTableBuilder.build_complete_meta_table() instead"""
    builder = MetaTableBuilder()
    return builder.build_complete_meta_table()


def calculate_period_shares(deck_name):
    """Legacy function - use ArchetypeAnalyzer.calculate_period_comparison() instead"""
    analyzer = ArchetypeAnalyzer()
    return analyzer.calculate_period_comparison(deck_name)


def fetch_top_archetypes_by_7d_share(limit=20):
    """Legacy function - use ArchetypeAnalyzer.fetch_top_archetypes_by_share() instead"""
    analyzer = ArchetypeAnalyzer()
    return analyzer.fetch_top_archetypes_by_share(7, limit)


def format_trend_indicator(trend_change, trend_direction):
    """Legacy function - use MetaDisplayFormatter.format_trend_indicator() instead"""
    return MetaDisplayFormatter.format_trend_indicator(trend_change, trend_direction)

def fetch_archetype_trend_data_detailed(deck_name, days_back=7):
    """Legacy function - use ArchetypeAnalyzer.get_daily_trend_data() instead"""
    analyzer = ArchetypeAnalyzer()
    return analyzer.get_daily_trend_data(deck_name, days_back)

def debug_deck_appearances(deck_name="mewtwo-ex-gardevoir-a1"):
   """Debug function to show deck appearances by day in last 7 days"""
   try:
       conn = sqlite3.connect("meta_analysis/tournament_meta.db")
       
       query = """
       SELECT 
           t.date,
           t.tournament_id,
           t.total_players,
           aa.count as archetype_count,
           ROUND((CAST(aa.count AS FLOAT) / t.total_players * 100), 2) as deck_share
       FROM tournaments t
       JOIN archetype_appearances aa ON t.tournament_id = aa.tournament_id
       WHERE aa.archetype = ? 
         AND t.date >= date('now', '-7 days')
       ORDER BY t.date DESC, t.tournament_id
       """
       
       df = pd.read_sql_query(query, conn, params=[deck_name])
       conn.close()
       
       if df.empty:
           st.write(f"**DEBUG**: No appearances found for {deck_name} in last 7 days")
           return
       
       st.write(f"**DEBUG**: {deck_name} appearances in last 7 days:")
       
       for date in df['date'].unique():
           day_data = df[df['date'] == date]
           total_appearances = day_data['archetype_count'].sum()
           total_players = day_data['total_players'].sum()
           daily_share = (total_appearances / total_players * 100) if total_players > 0 else 0
           
           st.write(f"**{date}**: {total_appearances} appearances / {total_players} total players = {daily_share:.2f}%")
           for _, row in day_data.iterrows():
               st.write(f"  - Tournament {row['tournament_id']}: {row['archetype_count']}/{row['total_players']} players ({row['deck_share']:.2f}%)")
               
   except Exception as e:
       st.write(f"**DEBUG ERROR**: {e}")


def display_gainers_table():
    """Display meta table sorted by gainers (highest trend change first)"""
    
    with st.spinner("Loading gainers data..."):
        builder = MetaTableBuilder()
        meta_df = builder.build_complete_meta_table(30)
    
    if meta_df.empty:
        st.warning("No meta data available at this time.")
        return
    
    # Sort by trend change descending (highest gains first)
    gainers_df = meta_df.sort_values('trend_change', ascending=False)
    
    # Format for display
    formatter = MetaDisplayFormatter()
    gainers_df = formatter.prepare_display_dataframe(gainers_df)
    
    # Display table header
    st.write("##### 📈 Biggest Gainers - Top 20 Archetypes")
    
    try:
        # Create final display DataFrame
        final_df = pd.DataFrame({
            'Icon1': gainers_df['pokemon_url1'],
            'Icon2': gainers_df['pokemon_url2'], 
            'Deck': gainers_df['formatted_deck_name'],
            'Share-7d': gainers_df['share_7d'],
            'Change': gainers_df['trend_indicator'],
            'Win %': gainers_df['win_rate']
        })
        
        # Configure column display
        column_config = {
            'Icon1': st.column_config.ImageColumn(
                "1", width=28, help="Primary Pokemon"
            ),
            'Icon2': st.column_config.ImageColumn(
                "2", width=28, help="Secondary Pokemon"
            ),
            'Deck': st.column_config.TextColumn("Deck", width=150),
            'Share-7d': st.column_config.NumberColumn(
                "Share-7d", width=65, help="Meta share in last 7 days", format="%.2f%%"
            ),
            'Change': st.column_config.TextColumn(
                "Change", width=80, help="Trend from 7d to 3d average", 
            ),
            'Win %': st.column_config.NumberColumn(
                "Win %", width=70, help="Win rate percentage", format="%.1f%%"
            )
        }
        
        # Display the data table
        st.dataframe(
            final_df,
            column_config=column_config,
            hide_index=False,
            height=750,
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Error displaying gainers table: {str(e)}")
        print(f"Display error: {e}")


def display_losers_table():
    """Display meta table sorted by losers (lowest trend change first)"""
    
    with st.spinner("Loading losers data..."):
        builder = MetaTableBuilder()
        meta_df = builder.build_complete_meta_table(20)
    
    if meta_df.empty:
        st.warning("No meta data available at this time.")
        return
    
    # Sort by trend change ascending (biggest losses first)
    losers_df = meta_df.sort_values('trend_change', ascending=True)
    
    # Format for display
    formatter = MetaDisplayFormatter()
    losers_df = formatter.prepare_display_dataframe(losers_df)
    
    # Display table header
    st.write("##### 📉 Biggest Losers - Top 20 Archetypes")
    
    try:
        # Create final display DataFrame
        final_df = pd.DataFrame({
            'Icon1': losers_df['pokemon_url1'],
            'Icon2': losers_df['pokemon_url2'], 
            'Deck': losers_df['formatted_deck_name'],
            'Share-7d': losers_df['share_7d'],
            'Change': losers_df['trend_indicator'],
            'Win %': losers_df['win_rate']
        })
        
        # Configure column display
        column_config = {
            'Icon1': st.column_config.ImageColumn(
                "1", width=30, help="Primary Pokemon"
            ),
            'Icon2': st.column_config.ImageColumn(
                "2", width=30, help="Secondary Pokemon"
            ),
            'Deck': st.column_config.TextColumn("Deck", width=150),
            'Share-7d': st.column_config.NumberColumn(
                "Share-7d", width=70, help="Meta share in last 7 days", format="%.2f%%"
            ),
            'Change': st.column_config.TextColumn(
                "Change", width=80, help="Trend from 7d to 3d average", 
            ),
            'Win %': st.column_config.NumberColumn(
                "Win %", width=70, help="Win rate percentage", format="%.1f%%"
            )
        }
        
        # Display the data table
        st.dataframe(
            final_df,
            column_config=column_config,
            hide_index=True,
            height=750,
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Error displaying losers table: {str(e)}")
        print(f"Display error: {e}")

def display_meta_overview_table_with_buttons():
    """Display meta overview table with manual deck selection buttons - enhanced compact layout"""
    
    with st.spinner("Loading meta overview data..."):
        builder = MetaTableBuilder()
        meta_df = builder.build_complete_meta_table(20)
    
    if meta_df.empty:
        st.warning("No meta data available at this time.")
        return
    
    # Format for display
    formatter = MetaDisplayFormatter()
    meta_df = formatter.prepare_display_dataframe(meta_df)
    
    # Display table header
    st.write("##### Meta Overview - Top 20 Archetypes")
    
    # Custom CSS for styling
    st.markdown("""
    <style>    
    .deck-button {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        color: #00A0FF !important;
        text-decoration: underline !important;
        cursor: pointer !important;
        font-size: inherit !important;
        font-family: inherit !important;
    }
    .deck-button:hover {
        color: #0080CC !important;
    }
    
    /* Force left alignment for buttons even when wrapping */
    div[data-testid="column"] button {
        text-align: left !important;
        justify-content: flex-start !important;
    }
    
    div[data-testid="column"] button p {
        text-align: left !important;
        width: 100% !important;
    }
    
    /* Additional specificity for wrapped button text */
    .stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        line-height: 1.1 !important;  /* Reduce line height */
        padding: 4px 8px !important;
    }
    
    .stButton > button p {
        text-align: left !important;
        margin: 0 !important;
    }

    .share-column {
        text-align: right !important;
    }
    
    .change-positive {
        color: #06B804 !important;
        font-size: 0.8rem !important;
        margin-top: -2px !important;
        line-height: 1 !important;
        text-align: right !important;
    }
    .change-negative {
        color: #FD6C6C !important;
        font-size: 0.8rem !important;
        margin-top: -2px !important;
        line-height: 1 !important;
        text-align: right !important;
    }
    .change-neutral {
        color: #888888 !important;
        font-size: 0.8rem !important;
        margin-top: -2px !important;
        line-height: 1 !important;
        text-align: right !important;
    }
    .icons-container {
        display: flex !important;
        align-items: center !important;
        gap: 2px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    #Header row with updated layout
    # col1, col2, col3 = st.columns([1, 3, 1.2])
    # with col1:
    #     st.write(" ")
    # with col2:
    #     st.write("**Deck**")
    # with col3:
    #     st.markdown('<div class="share-column"><strong>Share-7d</strong></div>', unsafe_allow_html=True)
    
    # st.markdown('<hr style="margin: 0px 0; border: 0.5px solid rgba(137, 148, 166, 0.2);">', unsafe_allow_html=True)
    
    #Helper function to extract numeric value from trend indicator
    def extract_trend_value(trend_indicator):
        """Extract numeric value and determine color from trend indicator"""
        if not trend_indicator or trend_indicator == "➡️ 0.00%":
            return 0, "neutral"
        
        # Remove emoji and extract number
        if "📈" in trend_indicator:
            value_str = trend_indicator.replace("📈 +", "").replace("%", "")
            try:
                value = float(value_str)
                return value, "positive"
            except:
                return 0, "neutral"
        elif "📉" in trend_indicator:
            value_str = trend_indicator.replace("📉 -", "").replace("%", "")
            try:
                value = float(value_str)
                return -value, "negative"
            except:
                return 0, "neutral"
        else:
            return 0, "neutral"
    
    #Data rows
    for idx, row in meta_df.iterrows():
        col1, col2, col3 = st.columns([1, 3, 1.2])
        
        # Combined Pokemon icons
        with col1:
            icons_html = '<div class="icons-container">'
            
            if row['pokemon_url1']:
                icons_html += f'<img src="{row["pokemon_url1"]}" style="max-height:28px; max-width: 70%; border-radius: 0px; margin-top:5px;">'
            
            if row['pokemon_url2']:
                icons_html += f'<img src="{row["pokemon_url2"]}" style="max-height:28px; max-width: 70%; border-radius: 0px; margin-top:5px;">'
            
            icons_html += '</div>'
            st.markdown(icons_html, unsafe_allow_html=True)
        
        # Clickable deck name
        with col2:
            button_key = f"deck_select_{idx}_{row['deck_name']}"
            if st.button(row['formatted_deck_name'], key=button_key, type="tertiary"):
                st.session_state.deck_to_analyze = row['deck_name']
                st.rerun()
        
        # Share with change underneath
        with col3:
            # Main share value - right aligned
            st.markdown(f'<div class="share-column">{row["share_7d"]:.2f}%</div>', unsafe_allow_html=True)
            
            # Change value underneath with color coding
            trend_value, trend_type = extract_trend_value(row['trend_indicator'])
            
            if trend_type == "positive":
                change_html = f'<div class="change-positive">+ {trend_value:.2f}%</div>'
            elif trend_type == "negative":
                change_html = f'<div class="change-negative">- {trend_value*-1:.2f}%</div>'
            else:
                change_html = f'<div class="change-neutral">0.00%</div>'
            
            st.markdown(change_html, unsafe_allow_html=True)
    
    # Add explanation
    st.caption(
        "**Click on any deck name** to analyze it in detail. "
        "Green/red values show 7d to 3d trend changes."
    )

# Add these imports at the top of meta_table.py if not already present
import math
import random
import sqlite3
import pandas as pd
import streamlit as st

# Add this single function to meta_table.py

def display_extended_meta_table():
    """Extended meta table with Wins, Losses, Ties, Share-7d, Share-3d, Wilson Index (Power Index), and ranking"""
    
    with st.spinner("Loading extended meta data..."):
        builder = MetaTableBuilder()
        meta_df = builder.build_complete_meta_table(100)
    
    if meta_df.empty:
        st.warning("No meta data available at this time.")
        return
    
    # Format for display
    formatter = MetaDisplayFormatter()
    meta_df = formatter.prepare_display_dataframe(meta_df)
    
    # Calculate Wilson Score (Power Index) for each archetype using analyzer.py formula
    def calculate_wilson_score(wins, losses, ties):
        """Calculate Wilson Score confidence interval using analyzer.py formula"""
        total_games = wins + losses + ties
        if total_games == 0:
            return 0.0
        
        # Handle ties as half-wins (common in card games)
        adjusted_wins = wins + (0.5 * ties)
        
        # Calculate win proportion
        win_proportion = adjusted_wins / total_games
        
        # Wilson Score Interval parameters
        z = 1.96  # 95% confidence level
        z_squared = z * z
        
        # Calculate Wilson Score lower bound
        numerator = (win_proportion + (z_squared / (2 * total_games)) - 
                     z * math.sqrt((win_proportion * (1 - win_proportion) + 
                                   (z_squared / (4 * total_games))) / total_games))
        
        denominator = 1 + (z_squared / total_games)
        
        # Wilson Score lower bound (conservative estimate of true win rate)
        wilson_score = numerator / denominator
        
        # Scale to make more intuitive (analyzer.py formula)
        power_index = (wilson_score - 0.5) * 10
        
        return round(power_index, 2)
    
    # Add daily trend data for line charts (copied from working display_meta_overview_table)
    def get_trend_history(deck_name):
        """Get 7-day percentage history for line chart"""
        try:
            # Use the existing builder's analyzer to get daily trend data
            daily_data = builder.archetype_analyzer.get_daily_trend_data(deck_name, days_back=7)
            
            # Extract percentage values - keys are day_1, day_2, etc.
            percentages = []
            for i in range(1, 8):  # day_1 through day_7
                day_key = f'day_{i}'
                percentages.append(daily_data.get(day_key, 0))
            
            # Reverse to show chronological order (oldest to newest)
            percentages.reverse()
            return percentages
            
        except Exception as e:
            print(f"Error getting trend for {deck_name}: {e}")
            # Return sample trend data for demo
            import random
            return [random.uniform(0, 5) for _ in range(7)]
    
    # Add trend history to meta_df (exactly like working version)
    meta_df['trend_history'] = meta_df['deck_name'].apply(get_trend_history)
    
    # Get performance data for each archetype
    extended_data = []
    
    try:
        with sqlite3.connect("meta_analysis/tournament_meta.db") as conn:
            for _, row in meta_df.iterrows():
                deck_name = row['deck_name']
                
                try:
                    # IMPROVED query to handle missing performance data
                    perf_query = """
                    SELECT 
                        COALESCE(SUM(pp.wins), 0) as total_wins,
                        COALESCE(SUM(pp.losses), 0) as total_losses,
                        COALESCE(SUM(pp.ties), 0) as total_ties,
                        COUNT(pp.id) as performance_records
                    FROM player_performance pp
                    JOIN tournaments t ON pp.tournament_id = t.tournament_id
                    WHERE pp.archetype = ?
                    AND t.date >= date('now', '-7 days')
                    """
                    
                    perf_result = pd.read_sql_query(perf_query, conn, params=[deck_name])
                    
                    wins = int(perf_result['total_wins'].iloc[0] or 0)
                    losses = int(perf_result['total_losses'].iloc[0] or 0)
                    ties = int(perf_result['total_ties'].iloc[0] or 0)
                    performance_records = int(perf_result['performance_records'].iloc[0] or 0)
                    
                    # Debug: Check for data mismatch
                    appearance_query = """
                    SELECT SUM(aa.count) as total_appearances
                    FROM archetype_appearances aa
                    JOIN tournaments t ON aa.tournament_id = t.tournament_id
                    WHERE aa.archetype = ?
                    AND t.date >= date('now', '-7 days')
                    """
                    
                    appearance_result = pd.read_sql_query(appearance_query, conn, params=[deck_name])
                    total_appearances = int(appearance_result['total_appearances'].iloc[0] or 0)
                    
                    # Log data mismatches for debugging
                    if total_appearances > 0 and performance_records == 0:
                        print(f"⚠️ Data mismatch for {deck_name}: {total_appearances} appearances, {performance_records} performance records")
                    elif performance_records > 0 and total_appearances == 0:
                        print(f"⚠️ Reverse mismatch for {deck_name}: {performance_records} performance records, {total_appearances} appearances")
                    
                    wilson_index = calculate_wilson_score(wins, losses, ties)
                    
                    # Calculate win rate
                    total_games = wins + losses + ties
                    if total_games > 0:
                        win_rate = round(((wins + 0.5 * ties) / total_games) * 100, 1)
                    else:
                        win_rate = 0.0
                        # Additional debug for zero win rate cases
                        if total_appearances > 0:
                            print(f"📊 {deck_name}: 0% win rate despite {total_appearances} appearances - missing performance data")
                    
                    # Calculate ratio (Share-3d / Share-7d)
                    if row['share_7d'] > 0:
                        ratio = round(row['share_3d'] / row['share_7d'], 2)
                    else:
                        ratio = 0.0
                    
                    # Get trend history for line chart (from meta_df)
                    trend_data = row.get('trend_history', [0] * 7)
                    
                    extended_data.append({
                        'deck_name': deck_name,
                        'formatted_deck_name': row['formatted_deck_name'],
                        'pokemon_url1': row['pokemon_url1'],
                        'pokemon_url2': row['pokemon_url2'],
                        'trend_data': trend_data,
                        'win_rate': win_rate,
                        'wins': wins,
                        'losses': losses,
                        'ties': ties,
                        'share_7d': row['share_7d'],
                        'share_3d': row['share_3d'],
                        'ratio': ratio,
                        'wilson_index': wilson_index
                    })
                    
                except Exception as e:
                    print(f"Error processing deck {deck_name}: {e}")
                    # Add default entry for failed deck to maintain consistency
                    trend_data = row.get('trend_history', [0] * 7)
                    extended_data.append({
                        'deck_name': deck_name,
                        'formatted_deck_name': row.get('formatted_deck_name', deck_name),
                        'pokemon_url1': row.get('pokemon_url1', None),
                        'pokemon_url2': row.get('pokemon_url2', None),
                        'trend_data': trend_data,
                        'win_rate': 0.0,
                        'wins': 0,
                        'losses': 0,
                        'ties': 0,
                        'share_7d': row.get('share_7d', 0),
                        'share_3d': row.get('share_3d', 0),
                        'ratio': 0.0,
                        'wilson_index': 0.0
                    })
        
    except Exception as e:
        st.error(f"Error fetching performance data: {str(e)}")
        return
    
    if not extended_data:
        st.warning("No extended data could be generated.")
        return
    
    # Convert to DataFrame and sort by 7-day share (descending)
    extended_df = pd.DataFrame(extended_data)
    extended_df = extended_df.sort_values('share_7d', ascending=False).reset_index(drop=True)
    
    # Add ranking column (1-based)
    extended_df['rank'] = range(1, len(extended_df) + 1)
    
    # Display table header
    #st.write("##### Extended Tournament Performance Data")
    
    # Custom CSS for styling (enhanced with ratio and win rate colors)
    st.markdown("""
    <style>
    .extended-meta-table {
        font-size: 0.9rem;
    }
    
    .rank-column {
        text-align: center !important;
        font-weight: bold !important;
        color: #00A0FF !important;
    }
    
    .performance-column {
        text-align: center !important;
        font-family: monospace !important;
    }
    
    .share-column {
        text-align: right !important;
    }
    
    .wilson-column {
        text-align: center !important;
        font-weight: bold !important;
    }
    
    /* Ratio and Win Rate column styling */
    .ratio-positive {
        color: #06B804 !important;
        font-weight: bold !important;
    }
    
    .ratio-negative {
        color: #FD6C6C !important;
        font-weight: bold !important;
    }
    
    .ratio-neutral {
        color: #888888 !important;
        font-weight: normal !important;
    }
    
    .winrate-positive {
        color: #06B804 !important;
        font-weight: bold !important;
    }
    
    .winrate-negative {
        color: #FD6C6C !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    try:
        # Create final display DataFrame with correct column order including trend chart
        final_df = pd.DataFrame({
            '#': extended_df['rank'],
            '': extended_df['pokemon_url1'],      # Pokemon icon 1
            ' ': extended_df['pokemon_url2'],     # Pokemon icon 2
            'Deck': extended_df['formatted_deck_name'],
            'Trend': extended_df['trend_data'],   # Use 'Trend' like working version
            'Share-7d': extended_df['share_7d'],
            'Share-3d': extended_df['share_3d'],
            'Ratio': extended_df['ratio'],
            'Win Rate': extended_df['win_rate'],
            'Wins': extended_df['wins'],
            'Losses': extended_df['losses'], 
            'Ties': extended_df['ties'],
            'Index': extended_df['wilson_index']
        })
        
        # Define styling functions for conditional coloring
        def style_ratio_column(val):
            """Apply conditional styling to Ratio column like working table"""
            if pd.isna(val) or val == 0:
                return 'color: #888888; font-weight: normal;'
            elif val > 1.2:
                return 'color: #06B804; font-weight: bold;'  # Strong green for big gains
            elif val > 1.0:
                return 'color: #06B804; font-weight: normal;'  # Light green for gains
            elif val < 0.8:
                return 'color: #FD6C6C; font-weight: bold;'  # Strong red for big losses
            elif val < 1.0:
                return 'color: #FD6C6C; font-weight: normal;'  # Light red for losses
            else:
                return 'color: #888888; font-weight: normal;'  # Neutral
        
        def style_winrate_column(val):
            """Apply conditional styling to Win Rate column"""
            if pd.isna(val) or val == 0:
                return 'color: #888888; font-weight: normal;'
            elif val > 50:
                return 'color: #06B804; font-weight: bold;'  # Green for winning
            else:
                return 'color: #FD6C6C; font-weight: bold;'  # Red for losing
        
        # Apply conditional styling
        styled_df = final_df.style.applymap(
            style_ratio_column, subset=['Ratio']
        ).applymap(
            style_winrate_column, subset=['Win Rate']
        )
        
        # Configure column display
        column_config = {
            '#': st.column_config.NumberColumn(
                "#", width=30, help="Ranking by 7-day meta share"
            ),
            '': st.column_config.ImageColumn(
                "", width=25, help="Primary Pokemon"
            ),
            ' ': st.column_config.ImageColumn(
                "", width=25, help="Secondary Pokemon"
            ),
            'Deck': st.column_config.TextColumn("Deck", width=140),
            'Trend': st.column_config.LineChartColumn(
                "Trend", width=80, help="7-day meta share trend (oldest to newest)"
            ),
            'Win Rate': st.column_config.NumberColumn(
                "Win Rate", width=55, help="Win rate percentage (last 7 days)", format="%.1f%%"
            ),
            'Wins': st.column_config.NumberColumn(
                "Wins", width=45, help="Total wins in last 7 days"
            ),
            'Losses': st.column_config.NumberColumn(
                "Losses", width=45, help="Total losses in last 7 days"
            ),
            'Ties': st.column_config.NumberColumn(
                "Ties", width=40, help="Total ties in last 7 days"
            ),
            'Share-7d': st.column_config.NumberColumn(
                "Share-7d", width=55, help="Meta share in last 7 days", format="%.2f%%"
            ),
            'Share-3d': st.column_config.NumberColumn(
                "Share-3d", width=55, help="Meta share in last 3 days", format="%.2f%%"
            ),
            'Ratio': st.column_config.NumberColumn(
                "Ratio", width=50, help="Share-3d / Share-7d ratio", format="%.2f"
            ),
            'Index': st.column_config.NumberColumn(
                "Index", width=40, help="Wilson Score Power Index (scaled -5 to +5, higher = better)", format="%.2f"
            )
        }
        
        # Display the styled dataframe
        st.dataframe(
            styled_df,
            column_config=column_config,
            hide_index=True,
            height=3000,
            use_container_width=True
        )
        
        # Add explanatory caption
        st.caption(
            "Extended performance data with 7-day trend charts, win rate, wins/losses/ties, meta share trends, ratio, and Wilson Index.  \n"
            "Trend shows daily meta share progression (oldest to newest).  \n"
            "Ratio shows Share-3d / Share-7d with color coding: **green** = gaining popularity (>1.0), **red** = losing popularity (<1.0).  \n"
            "Win Rate is color-coded: **green** = above 50%, **red** = below 50%.  \n"
            "**Note:** ~5 entries may show 0% win rate when individual performance data is unavailable despite meta presence.  \n"
            "Wilson Index is the Power Index from analyzer.py (scaled -5 to +5, positive = above 50% win rate with confidence).  \n"
            "Ranked by 7-day meta share percentage."
        )
        
    except Exception as e:
        st.error(f"Error displaying extended meta table: {str(e)}")
        print(f"Display error: {e}")

def get_tournament_summary_stats(period_days=7):
    """
    Get summary statistics for tournaments in the specified period.
    
    Args:
        period_days: Number of days to look back (default: 7)
        
    Returns:
        dict: Contains tournament_count, total_players, total_matches
    """
    try:
        import sqlite3
        
        conn = sqlite3.connect("meta_analysis/tournament_meta.db")
        
        # Calculate cutoff date
        from datetime import datetime, timedelta
        cutoff_date = (datetime.now() - timedelta(days=period_days)).strftime('%Y-%m-%d')
        
        # Get tournament count and total players
        tournament_query = """
        SELECT 
            COUNT(DISTINCT tournament_id) as tournament_count,
            SUM(total_players) as total_players
        FROM tournaments
        WHERE date >= ?
        """
        
        result = conn.execute(tournament_query, (cutoff_date,)).fetchone()
        tournament_count = result[0] if result[0] else 0
        total_players = result[1] if result[1] else 0
        
        # Get total matches - CORRECTED CALCULATION
        # Total matches = total wins (since each match has exactly one winner)
        # OR alternatively: Total matches = (wins + losses + ties) / 2
        matches_query = """
        SELECT 
            SUM(wins) as total_matches
        FROM player_performance pp
        JOIN tournaments t ON pp.tournament_id = t.tournament_id
        WHERE t.date >= ?
        """
        
        match_result = conn.execute(matches_query, (cutoff_date,)).fetchone()
        total_matches = match_result[0] if match_result[0] else 0
        
        conn.close()
        
        return {
            'tournament_count': tournament_count,
            'total_players': total_players,
            'total_matches': total_matches,
            'period_days': period_days
        }
        
    except Exception as e:
        print(f"Error getting tournament summary stats: {e}")
        return {
            'tournament_count': 0,
            'total_players': 0,
            'total_matches': 0,
            'period_days': period_days
        }

def format_tournament_summary(period_days=7):
    """
    Format tournament summary statistics for display.
    
    Args:
        period_days: Number of days to look back (default: 7)
        
    Returns:
        str: Formatted summary string
    """
    stats = get_tournament_summary_stats(period_days)
    
    return f"{stats['tournament_count']} tournaments, {stats['total_players']} players, {stats['total_matches']} matches"
