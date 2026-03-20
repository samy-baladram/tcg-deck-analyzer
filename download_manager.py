"""
Download Manager Module - Handles bulk data export and zip file creation
"""

import pandas as pd
import io
import zipfile
from meta_table import get_cached_extended_meta_data
from display_tabs import fetch_matchup_data
import cache_manager


def get_meta_overview_data():
    """
    Get the metagame overview table data
    
    Returns:
        DataFrame with meta overview data
    """
    try:
        meta_df = get_cached_extended_meta_data()
        
        if meta_df.empty:
            print("No meta data available")
            return pd.DataFrame()
        
        # Return a clean version for export
        return meta_df
    except Exception as e:
        print(f"Error getting meta overview data: {e}")
        return pd.DataFrame()


def get_deck_raw_data(deck_name, set_name="A3"):
    """
    Get raw analysis data for a specific deck
    
    Args:
        deck_name: Name of the deck
        set_name: Set code for the deck
        
    Returns:
        DataFrame with raw card usage data
    """
    try:
        analyzed_deck = cache_manager.get_or_analyze_full_deck(
            deck_name,
            set_name,
            force_refresh=False
        )
        
        if analyzed_deck is None:
            return pd.DataFrame()
        
        # Get the results DataFrame
        results = analyzed_deck.get('results', pd.DataFrame())
        return results
        
    except Exception as e:
        print(f"Error getting raw data for {deck_name}: {e}")
        return pd.DataFrame()


def get_deck_matchup_data(deck_name, set_name="A3"):
    """
    Get matchup data for a specific deck
    
    Args:
        deck_name: Name of the deck
        set_name: Set code for the deck
        
    Returns:
        DataFrame with matchup data
    """
    try:
        matchup_df = fetch_matchup_data(deck_name, set_name)
        return matchup_df
        
    except Exception as e:
        print(f"Error getting matchup data for {deck_name}: {e}")
        return pd.DataFrame()


def create_export_zip():
    """
    Create a zip file with all meta data and individual deck data
    
    Returns:
        BytesIO object containing the zip file
    """
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        try:
            # 1. Add meta overview table
            meta_df = get_meta_overview_data()
            
            if not meta_df.empty:
                # Clean column names for export
                export_meta_df = meta_df.copy()
                
                # Add CSV to zip
                csv_buffer = io.StringIO()
                export_meta_df.to_csv(csv_buffer, index=False)
                zip_file.writestr('metaoverview.csv', csv_buffer.getvalue())
            
            # 2. Collect deck number for naming
            if not meta_df.empty:
                # Get list of decks from meta data
                for idx, row in meta_df.iterrows():
                    deck_number = idx + 1  # 1-indexed
                    deck_name = row.get('deck_name', f'deck_{deck_number}')
                    
                    # Format deck number with leading zero (e.g., 01, 02, 07)
                    deck_num_str = f"{deck_number:02d}"
                    
                    try:
                        # Get raw data for this deck
                        raw_data = get_deck_raw_data(deck_name)
                        if not raw_data.empty:
                            csv_buffer = io.StringIO()
                            raw_data.to_csv(csv_buffer, index=False)
                            filename = f'rawdata_deck_{deck_num_str}.csv'
                            zip_file.writestr(filename, csv_buffer.getvalue())
                        
                        # Get matchup data for this deck (if available)
                        matchup_data = get_deck_matchup_data(deck_name)
                        if not matchup_data.empty:
                            csv_buffer = io.StringIO()
                            matchup_data.to_csv(csv_buffer, index=False)
                            filename = f'metamatchup_deck_{deck_num_str}.csv'
                            zip_file.writestr(filename, csv_buffer.getvalue())
                    
                    except Exception as e:
                        print(f"Error processing deck {deck_number} ({deck_name}): {e}")
                        continue
        
        except Exception as e:
            print(f"Zip creation error: {e}")
    
    zip_buffer.seek(0)
    return zip_buffer
