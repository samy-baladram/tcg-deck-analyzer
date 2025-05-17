def get_energy_types_for_deck(deck_name, deck_energy_types):
    """
    Get energy types for a deck, falling back to most common energy combination if needed
    
    Returns:
        Tuple of (energy_types, is_typical)
    """
    # If deck has energy types, use them
    if deck_energy_types:
        return deck_energy_types, False
    
    # Otherwise, try to get the most common combination for this archetype
    archetype = get_archetype_from_deck_name(deck_name)
    
    # Check if we have energy combinations for this archetype
    if archetype in st.session_state.archetype_energy_combinations:
        combinations = st.session_state.archetype_energy_combinations[archetype]
        
        # If we have combinations, get the most common one
        if combinations:
            # Filter out empty combinations
            valid_combinations = [(combo, count) for combo, count in combinations.items() if combo]
            
            # If we have valid combinations, get the most common one
            if valid_combinations:
                most_common_combo, _ = max(valid_combinations, key=lambda x: x[1])
                return list(most_common_combo), True
    
    # If no combinations are found, fall back to the old method for compatibility
    if archetype in st.session_state.archetype_energy_types:
        all_energies = list(st.session_state.archetype_energy_types[archetype])
        # Only return up to 3 energies (TCG Pocket limit)
        if all_energies:
            return all_energies[:3], True
    
    # No energy types found
    return [], False
