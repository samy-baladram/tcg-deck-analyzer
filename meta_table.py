"""
Meta Table Module - Clean archetype performance analysis with trend data
"""

import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


class MetaAnalyzer:
    """Main class for meta analysis operations"""
    
    def __init__(self, db_path="meta_analysis/tournament_meta.db"):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)


class ArchetypeAnalyzer(MetaAnalyzer):
    """Handle archetype-specific analysis"""
    
    def fetch_top_archetypes_by_share(self, period_days=7, limit=20):
        """
        Fetch top archetypes based on recent share data
        
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
        Compare archetype performance between different time periods
        
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
    """Build formatted meta table data"""
    
    def __init__(self, db_path="meta_analysis/tournament_meta.db"):
        super().__init__(db_path)
        self.archetype_analyzer = ArchetypeAnalyzer(db_path)
    
    def build_complete_meta_table(self, limit=20):
        """
        Build complete meta table with all analysis data
        
        Args:
            limit: Number of archetypes to include
            
        Returns:
            DataFrame with complete meta analysis
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
            print(f"Processing {deck_name}...")
            
            # Get period comparison data
            period_data = self.archetype_analyzer.calculate_period_comparison(deck_name)
            
            # Get daily trend data
            daily_data = self.archetype_analyzer.get_daily_trend_data(deck_name)
            
            # Build complete row data
            row_data = {
                'deck_name': deck_name,
                'display_name': self._format_deck_name(deck_name),
                'current_share': round(row['share'], 2),
                'win_rate': round(row['win_rate'], 1),
                **period_data,  # Add all period comparison data
                **daily_data    # Add all daily trend data
            }
            
            table_data.append(row_data)
        
        # Convert to DataFrame and sort by 7-day share
        result_df = pd.DataFrame(table_data)
        result_df = result_df.sort_values('share_7d', ascending=False).reset_index(drop=True)
        result_df['rank'] = range(1, len(result_df) + 1)
        
        print(f"Built meta table with {len(result_df)} archetypes")
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
            return f"📈 +{abs(trend_change):.2f}%"
        elif trend_direction == 'down':
            return f"📉 -{abs(trend_change):.2f}%"
        else:
            return f"➡️ {trend_change:.2f}%"
    
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


def display_meta_overview_table():
    """Main function to display the meta overview table"""
    
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
    
    try:
        # Create final display DataFrame
        final_df = pd.DataFrame({
            'Icon1': meta_df['pokemon_url1'],
            'Icon2': meta_df['pokemon_url2'], 
            'Deck': meta_df['formatted_deck_name'],
            'Count-7d': meta_df['archetype_count_7d'],
            'Total-7d': meta_df['total_count_7d'],
            'Share-7d': meta_df['share_7d'],
            'Count-3d': meta_df['archetype_count_3d'],
            'Total-3d': meta_df['total_count_3d'],
            'Share-3d': meta_df['share_3d'],
            'Change': meta_df['trend_indicator'],
            'Win %': meta_df['win_rate']
        })
        
        # Configure column display
        column_config = {
            'Icon1': st.column_config.ImageColumn(
                "Icon 1", width=40, help="Primary Pokemon"
            ),
            'Icon2': st.column_config.ImageColumn(
                "Icon 2", width=40, help="Secondary Pokemon"
            ),
            'Deck': st.column_config.TextColumn("Deck", width="medium"),
            'Count-7d': st.column_config.NumberColumn(
                "Count-7d", help="Archetype appearances in last 7 days", format="%d"
            ),
            'Total-7d': st.column_config.NumberColumn(
                "Total-7d", help="Total appearances in last 7 days", format="%d"
            ),
            'Share-7d': st.column_config.NumberColumn(
                "Share-7d", help="Meta share in last 7 days", format="%.2f%%"
            ),
            'Count-3d': st.column_config.NumberColumn(
                "Count-3d", help="Archetype appearances in last 3 days", format="%d"
            ),
            'Total-3d': st.column_config.NumberColumn(
                "Total-3d", help="Total appearances in last 3 days", format="%d"
            ),
            'Share-3d': st.column_config.NumberColumn(
                "Share-3d", help="Meta share in last 3 days", format="%.2f%%"
            ),
            'Change': st.column_config.TextColumn(
                "Change", help="Trend from 7d to 3d average", width="small"
            ),
            'Win %': st.column_config.NumberColumn(
                "Win %", help="Win rate percentage", format="%.1f%%"
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
