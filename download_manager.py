"""
Download Manager Module - Handles bulk data export and zip file creation
Exports data in the exact format displayed on screen for each tab
"""

import pandas as pd
import io
import zipfile
from meta_table import MetaTableBuilder
from display_tabs import fetch_matchup_data
import cache_manager
import streamlit as st


def get_meta_overview_data_for_export():
    """
    Get the metagame overview table data in the exact format displayed on screen.
    Matches the final_df created in display_extended_meta_table()
    
    Returns:
        DataFrame with meta overview data in display format
    """
    try:
        # Build the same meta table used for display
        builder = MetaTableBuilder()
        meta_df = builder.build_complete_meta_table(100)
        
        if meta_df.empty:
            print("No meta data available")
            return pd.DataFrame()
        
        # Build extended_df the same way display_extended_meta_table does
        extended_df = meta_df.copy()
        
        # Create the exact same final_df structure as display_extended_meta_table()
        export_data = {
            '#': extended_df.index + 1,  # Ranking
            'Deck': extended_df['formatted_deck_name'],
            'Trend': extended_df['trend_data'],
            'Share-7d': extended_df['share_7d'],
            'Share-3d': extended_df['share_3d'],
            'Ratio': extended_df['ratio'],
            'Wins': extended_df['wins'],
            'Losses': extended_df['losses'],
            'Ties': extended_df['ties'],
            'Win Rate': extended_df['win_rate'],
        }
        
        final_df = pd.DataFrame(export_data)
        
        # Store mapping from formatted names to actual deck names for later use
        if '_deck_name_mapping' not in st.session_state:
            st.session_state._deck_name_mapping = {}
        
        for idx, row in extended_df.iterrows():
            display_name = extended_df.iloc[idx]['formatted_deck_name']
            actual_name = extended_df.iloc[idx]['deck_name']
            st.session_state._deck_name_mapping[display_name] = actual_name
        
        return final_df
        
    except Exception as e:
        print(f"Error getting meta overview data: {e}")
        return pd.DataFrame()


def get_deck_raw_data(deck_name, set_name="A3"):
    """
    Get raw analysis data for a specific deck in the exact format displayed in Raw Data tab.
    This matches what st.dataframe(results) displays on screen.
    
    Args:
        deck_name: Name of the deck
        set_name: Set code for the deck
        
    Returns:
        DataFrame with raw card usage data (exact display format)
    """
    try:
        analyzed_deck = cache_manager.get_or_analyze_full_deck(
            deck_name,
            set_name,
            force_refresh=False
        )
        
        if analyzed_deck is None:
            return pd.DataFrame()
        
        # Get the results DataFrame - this is exactly what's displayed via st.dataframe()
        results = analyzed_deck.get('results', pd.DataFrame())
        
        if results.empty:
            return pd.DataFrame()
        
        # Return as-is - this is the exact format displayed on the Raw Data tab
        return results
        
    except Exception as e:
        print(f"Error getting raw data for {deck_name}: {e}")
        return pd.DataFrame()


def get_deck_matchup_data(deck_name, set_name="A3"):
    """
    Get matchup data for a specific deck in the exact format displayed in Meta Matchups tab.
    This matches what st.dataframe() displays on screen (without image columns).
    
    Args:
        deck_name: Name of the deck
        set_name: Set code for the deck
        
    Returns:
        DataFrame with matchup data (exact display format, no image columns)
    """
    try:
        matchup_df = fetch_matchup_data(deck_name, set_name)
        
        if matchup_df.empty:
            return pd.DataFrame()
        
        # Remove image columns (Icon1, Icon2) if they exist - users download text data, not images
        displayable_df = matchup_df.copy()
        columns_to_drop = ['pokemon_url1', 'pokemon_url2', 'Icon1', 'Icon2']
        for col in columns_to_drop:
            if col in displayable_df.columns:
                displayable_df = displayable_df.drop(columns=[col])
        
        return displayable_df
        
    except Exception as e:
        print(f"Error getting matchup data for {deck_name}: {e}")
        return pd.DataFrame()


def create_export_zip():
    """
    Create a zip file with all meta data and individual deck data
    in the exact format as displayed on screen.
    
    Returns:
        BytesIO object containing the zip file
    """
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        try:
            # 1. Add meta overview table - in display format
            meta_df = get_meta_overview_data_for_export()
            
            if not meta_df.empty:
                # Add CSV to zip
                csv_buffer = io.StringIO()
                meta_df.to_csv(csv_buffer, index=False)
                zip_file.writestr('metaoverview.csv', csv_buffer.getvalue())
            
            # 2. Collect deck data - use the mapping we created
            if not meta_df.empty and '_deck_name_mapping' in st.session_state:
                deck_name_mapping = st.session_state._deck_name_mapping
                
                for idx, row in meta_df.iterrows():
                    deck_number = idx + 1  # 1-indexed
                    display_name = row['Deck']  # Display name from the table
                    
                    # Get actual deck name from mapping
                    actual_deck_name = deck_name_mapping.get(display_name, display_name)
                    
                    # Format deck number with leading zero (e.g., 01, 02, 07)
                    deck_num_str = f"{deck_number:02d}"
                    
                    try:
                        # Get raw data for this deck (in display format)
                        raw_data = get_deck_raw_data(actual_deck_name)
                        if not raw_data.empty:
                            csv_buffer = io.StringIO()
                            raw_data.to_csv(csv_buffer, index=False)
                            filename = f'rawdata_deck_{deck_num_str}.csv'
                            zip_file.writestr(filename, csv_buffer.getvalue())
                        
                        # Get matchup data for this deck (in display format)
                        matchup_data = get_deck_matchup_data(actual_deck_name)
                        if not matchup_data.empty:
                            csv_buffer = io.StringIO()
                            matchup_data.to_csv(csv_buffer, index=False)
                            filename = f'metamatchup_deck_{deck_num_str}.csv'
                            zip_file.writestr(filename, csv_buffer.getvalue())
                    
                    except Exception as e:
                        print(f"Error processing deck {deck_number} ({actual_deck_name}): {e}")
                        continue
        
        except Exception as e:
            print(f"Zip creation error: {e}")
    
    zip_buffer.seek(0)
    return zip_buffer
