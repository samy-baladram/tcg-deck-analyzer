# Add this to a new file called related_decks.py

import pandas as pd
from image_processor import extract_pokemon_from_deck_name

def find_related_decks(current_deck_name, deck_list_df, max_related=10):
    """
    Find decks related to the current deck based on shared Pokémon in deck names.
    
    Args:
        current_deck_name: The name of the current deck
        deck_list_df: DataFrame containing all available decks
        max_related: Maximum number of related decks to return
        
    Returns:
        DataFrame of related decks sorted by relevance (shared Pokémon count and meta share)
    """
    # Extract Pokémon from current deck name
    current_pokemon = extract_pokemon_from_deck_name(current_deck_name)
    
    if not current_pokemon:
        return pd.DataFrame()
    
    # Function to count shared Pokémon
    def count_shared_pokemon(deck_name):
        other_pokemon = extract_pokemon_from_deck_name(deck_name)
        shared = set(current_pokemon).intersection(set(other_pokemon))
        return len(shared)
    
    # Apply function to all decks
    related_decks = deck_list_df.copy()
    related_decks['shared_pokemon'] = related_decks['deck_name'].apply(count_shared_pokemon)
    
    # Filter to only include decks with at least one shared Pokémon
    related_decks = related_decks[related_decks['shared_pokemon'] > 0]
    
    # Remove the current deck
    related_decks = related_decks[related_decks['deck_name'] != current_deck_name]
    
    # Sort by number of shared Pokémon (desc) and share percentage (desc)
    related_decks = related_decks.sort_values(by=['shared_pokemon', 'share'], ascending=[False, False])
    
    # Limit to max_related
    if len(related_decks) > max_related:
        related_decks = related_decks.head(max_related)
    
    return related_decks
