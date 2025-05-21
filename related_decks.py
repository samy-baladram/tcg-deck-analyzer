# Add this to a new file called related_decks.py

import pandas as pd
from image_processor import extract_pokemon_from_deck_name

# Updated find_related_decks function in related_decks.py

def find_related_decks(current_deck_name, deck_list_mapping, max_related=10):
    """
    Find decks related to the current deck based on shared Pokémon in deck names.
    Only includes decks that are in the current deck selection dropdown.
    
    Args:
        current_deck_name: The name of the current deck
        deck_list_mapping: Dictionary mapping display names to deck info from session state
        max_related: Maximum number of related decks to return
        
    Returns:
        DataFrame of related decks sorted by relevance (shared Pokémon count)
    """
    # Extract Pokémon from current deck name
    current_pokemon = extract_pokemon_from_deck_name(current_deck_name)
    
    if not current_pokemon or not deck_list_mapping:
        return pd.DataFrame()
    
    # Convert deck_list_mapping to DataFrame for easier processing
    deck_data = []
    for display_name, deck_info in deck_list_mapping.items():
        # Extract meta share percentage from display name if available
        share = 0.0
        if "%" in display_name:
            try:
                share_part = display_name.split("- ")[-1].strip()
                share = float(share_part.replace("%", ""))
            except:
                # If using power index format instead of share percentage
                share = 0.0
        
        # Extract clean display name without the percentage/power index part
        if " (" in display_name:
            clean_display = display_name.split(" (")[0]
        elif " - " in display_name:
            clean_display = display_name.split(" - ")[0]
        else:
            clean_display = display_name
            
        deck_data.append({
            'display_name': clean_display,
            'deck_name': deck_info['deck_name'],
            'set': deck_info['set'],
            'share': share
        })
    
    deck_df = pd.DataFrame(deck_data)
    
    # No decks to process
    if deck_df.empty:
        return pd.DataFrame()
    
    # Function to count shared Pokémon
    def count_shared_pokemon(deck_name):
        other_pokemon = extract_pokemon_from_deck_name(deck_name)
        shared = set(current_pokemon).intersection(set(other_pokemon))
        return len(shared)
    
    # Apply function to all decks
    deck_df['shared_pokemon'] = deck_df['deck_name'].apply(count_shared_pokemon)
    
    # Filter to only include decks with at least one shared Pokémon
    related_decks = deck_df[deck_df['shared_pokemon'] > 0]
    
    # Remove the current deck
    related_decks = related_decks[related_decks['deck_name'] != current_deck_name]
    
    # Sort by number of shared Pokémon (desc) and meta-weighted win rate (desc)
    # Try to get meta-weighted win rate from session state performance data if available
    meta_winrate_map = {}
    if 'performance_data' in st.session_state and not st.session_state.performance_data.empty and 'meta_weighted_winrate' in st.session_state.performance_data.columns:
        performance_df = st.session_state.performance_data
        meta_winrate_map = {deck['deck_name']: deck['meta_weighted_winrate'] for _, deck in performance_df.iterrows()}
    
    # Add meta-weighted win rate to the related decks dataframe
    related_decks['meta_weighted_winrate'] = related_decks['deck_name'].apply(
        lambda x: meta_winrate_map.get(x, 0.0)
    )
    
    # Sort by shared Pokémon first, then by meta-weighted win rate
    related_decks = related_decks.sort_values(
        by=['shared_pokemon', 'meta_weighted_winrate'], 
        ascending=[False, False]
    )
    
    # Limit to max_related
    if len(related_decks) > max_related:
        related_decks = related_decks.head(max_related)
    
    return related_decks
