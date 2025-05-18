# image_processor.py
"""Image processing functions for deck header images"""
import functools
import base64
import requests
from PIL import Image, ImageDraw
from io import BytesIO
import re
from config import IMAGE_BASE_URL, IMAGE_CROP_BOX, IMAGE_GRADIENT
from utils import is_set_code

# Simple utility functions
def get_base64_image(path):
    """Convert image file to base64 string"""
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def format_card_number(num):
    """Ensure card number is properly formatted for image URL"""
    if not num:
        return "001"
    
    # Ensure it's a string
    num = str(num)
    
    # Pad with zeros if needed (assuming 3 digits)
    if len(num) < 3:
        return num.zfill(3)
    
    return num

# Core processing functions
def fetch_and_crop_image(set_code, number):
    """
    Fetch and crop image without applying gradient
    
    Parameters:
    set_code: String (example: "A3")
    number: String (example: "122")
    
    Returns:
    PIL Image cropped but without gradient
    """
    # Build URL
    url = f"{IMAGE_BASE_URL}/{set_code}/{set_code}_{number}_EN.webp"
    
    try:
        # Get image
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        
        # Crop
        width, height = img.size
        crop_box = (
            int(width * IMAGE_CROP_BOX['left']),
            int(height * IMAGE_CROP_BOX['top']),
            int(width * IMAGE_CROP_BOX['right']),
            int(height * IMAGE_CROP_BOX['bottom'])
        )
        cropped = img.crop(crop_box)
        
        # Convert to RGBA
        if cropped.mode != 'RGBA':
            cropped = cropped.convert('RGBA')
            
        return cropped
    
    except Exception as e:
        print(f"Error fetching image for {set_code}-{number}: {e}")
        return None
        
def apply_vertical_gradient(image):
    """
    Apply gradient transparency to top and bottom of an image
    
    Parameters:
    image: PIL Image
    
    Returns:
    PIL Image with gradient transparency
    """
    # Ensure image has alpha channel
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create mask with full opacity
    mask = Image.new('L', image.size, 255)
    draw = ImageDraw.Draw(mask)
    
    # Calculate gradient heights
    gradient_height_top = int(image.height * IMAGE_GRADIENT['top_height'])
    gradient_height_bottom = int(image.height * IMAGE_GRADIENT['bottom_height'])
    
    # Draw top gradient (fade in from top)
    for y in range(gradient_height_top):
        opacity = int(255 * (y / gradient_height_top))
        draw.rectangle([(0, y), (image.width, y)], fill=opacity)
    
    # Draw bottom gradient (fade out to bottom)
    for y in range(gradient_height_bottom):
        y_pos = image.height - gradient_height_bottom + y
        opacity = int(255 * (1 - y / gradient_height_bottom))
        draw.rectangle([(0, y_pos), (image.width, y_pos)], fill=opacity)
    
    # Apply mask to alpha channel
    result = image.copy()
    result.putalpha(mask)
    
    return result

def apply_diagonal_cut(image, cut_type):
    """
    Apply a diagonal cut to an image (trapezoid shape)
    
    Parameters:
    image: PIL Image
    cut_type: String - "left" for left image, "right" for right image
    
    Returns:
    PIL Image with diagonal cut applied
    """
    if cut_type not in ["left", "right"]:
        return image
    
    # Ensure image has alpha channel
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create a mask for the diagonal cut
    width, height = image.size
    cut_mask = Image.new('L', image.size, 255)
    draw = ImageDraw.Draw(cut_mask)
    
    # Define the cutoff percentage
    cutoff_percentage = 0.7
    
    if cut_type == "left":
        # Cut lower right trapezoid
        points = [
            (width, 0),                             # Top right (full width)
            (width, height),                        # Bottom right
            (width * cutoff_percentage, height),    # Bottom cut point
            (width, 0),                             # Back to top right
        ]
        draw.polygon(points, fill=0)
    else:  # cut_type == "right"
        # Cut upper left trapezoid
        points = [
            (0, 0),                                      # Top left
            (width * (1 - cutoff_percentage), 0),        # Top cut point
            (0, height),                                 # Bottom left (full width)
            (0, 0),                                      # Back to top left
        ]
        draw.polygon(points, fill=0)
    
    # Apply the cut mask to the alpha channel
    result = image.copy()
    alpha = result.split()[-1]
    alpha = Image.composite(alpha, Image.new('L', alpha.size, 0), cut_mask)
    result.putalpha(alpha)
    
    return result

def merge_header_images(img1, img2, gap=5, cutoff_percentage=0.7):
    """
    Merge two diagonally cut images side by side
    
    Parameters:
    img1: PIL Image - left image with right side cut
    img2: PIL Image - right image with left side cut
    gap: int - gap in pixels between the visible parts
    cutoff_percentage: float - the percentage used in the diagonal cut
    
    Returns:
    PIL Image - merged image
    """
    # Ensure both images have alpha channel
    if img1.mode != 'RGBA':
        img1 = img1.convert('RGBA')
    if img2.mode != 'RGBA':
        img2 = img2.convert('RGBA')
    
    # Get dimensions
    width1, height1 = img1.size
    width2, height2 = img2.size
    
    # Calculate positions
    img2_x_position = int(width1 * cutoff_percentage) + gap
    
    # Calculate new dimensions
    max_height = max(height1, height2)
    total_width = img2_x_position + width2
    
    # Create new image with transparent background
    merged = Image.new('RGBA', (total_width, max_height), (0, 0, 0, 0))
    
    # Paste images
    y1 = (max_height - height1) // 2
    y2 = (max_height - height2) // 2
    
    merged.paste(img1, (0, y1), img1)
    merged.paste(img2, (img2_x_position, y2), img2)
    
    return merged

# Data extraction functions
def extract_pokemon_from_deck_name(deck_name):
    """
    Extract Pokemon names from deck name
    Handles cases with and without set codes as separators
    """
    # Pokemon suffixes that belong to the previous word
    POKEMON_SUFFIXES = ['ex', 'v', 'vmax', 'vstar', 'gx', 'sp']
    
    parts = deck_name.split('-')
    pokemon_names = []
    current_pokemon = []
    
    for i, part in enumerate(parts):
        if is_set_code(part):
            # Found a set code, save current Pokemon if exists
            if current_pokemon:
                pokemon_names.append('-'.join(current_pokemon))
                current_pokemon = []
        else:
            # Check if this part is a suffix
            is_suffix = part.lower() in POKEMON_SUFFIXES
            
            if is_suffix and current_pokemon:
                # Add suffix to current Pokemon
                current_pokemon.append(part)
            else:
                # This is a new word (not a suffix)
                if current_pokemon:
                    # Check if we should start a new Pokemon
                    last_was_suffix = current_pokemon[-1].lower() in POKEMON_SUFFIXES
                    
                    # If the last part was a suffix (like 'ex'), 
                    # and this is a new non-suffix word, it's a new Pokemon
                    if last_was_suffix and not is_suffix:
                        pokemon_names.append('-'.join(current_pokemon))
                        current_pokemon = [part]
                    # If neither is a suffix, it's also a new Pokemon
                    elif not last_was_suffix and not is_suffix:
                        pokemon_names.append('-'.join(current_pokemon))
                        current_pokemon = [part]
                    else:
                        # Continue current Pokemon
                        current_pokemon.append(part)
                else:
                    # Start first Pokemon
                    current_pokemon = [part]
    
    # Don't forget the last Pokemon
    if current_pokemon:
        pokemon_names.append('-'.join(current_pokemon))
    
    # Limit to first 2 Pokemon
    return pokemon_names[:2]

def get_pokemon_card_info(pokemon_name, analysis_results):
    """
    Find the card info for a Pokemon from analysis results
    Returns dict with set and number, or None if not found
    """
    # Clean up the Pokemon name for matching
    clean_name = pokemon_name.replace('-', ' ').title()
    
    # Handle 'ex' case
    if 'Ex' in clean_name:
        clean_name = clean_name.replace('Ex', 'ex')
    
    # Search for the Pokemon in the results
    pokemon_cards = analysis_results[
        (analysis_results['type'] == 'Pokemon') & 
        (analysis_results['card_name'].str.lower() == clean_name.lower())
    ]
    
    if not pokemon_cards.empty:
        # Get the most used variant (highest total percentage)
        best_card = pokemon_cards.loc[pokemon_cards['pct_total'].idxmax()]
        return {
            'name': best_card['card_name'],
            'set': best_card['set'],
            'num': best_card['num']
        }
    
    return None

# Update in image_processor.py

def create_deck_header_images(deck_info, analysis_results=None):
    """
    Create header images for a deck based on Pokemon in the deck name
    Uses pre-loaded Pokemon info if available, falls back to extracting from analysis_results
    
    Returns a single base64 encoded merged image
    """
    # Get deck name
    deck_name = deck_info['deck_name']
    
    # Initialize list for images
    pil_images = []
    
    # Try the three approaches in order of preference:
    # 1. First try to use pre-loaded info from session state
    if 'deck_pokemon_info' in st.session_state and deck_name in st.session_state.deck_pokemon_info:
        pokemon_info = st.session_state.deck_pokemon_info[deck_name]
        
        if pokemon_info:
            # Get images for each Pokemon (up to 2)
            for i, pokemon in enumerate(pokemon_info[:2]):
                if pokemon.get('set') and pokemon.get('num'):
                    formatted_num = format_card_number(pokemon['num'])
                    
                    # Fetch and crop the image
                    img = fetch_and_crop_image(pokemon['set'], formatted_num)
                    
                    if img:
                        # Apply diagonal cut based on position
                        cut_type = "left" if i == 0 else "right"
                        img = apply_diagonal_cut(img, cut_type)
                        pil_images.append(img)
    
    # 2. If no images yet, check if we're currently analyzing this deck
    if not pil_images and analysis_results is not None and not analysis_results.empty:
        # Extract Pokemon from deck name
        pokemon_names = extract_pokemon_from_deck_name(deck_name)
        
        if pokemon_names:
            # Get images for each Pokemon
            for i, pokemon_name in enumerate(pokemon_names[:2]):
                card_info = get_pokemon_card_info(pokemon_name, analysis_results)
                
                if card_info:
                    formatted_num = format_card_number(card_info['num'])
                    
                    # Fetch and crop the image
                    img = fetch_and_crop_image(card_info['set'], formatted_num)
                    
                    if img:
                        # Apply diagonal cut based on position
                        cut_type = "left" if i == 0 else "right"
                        img = apply_diagonal_cut(img, cut_type)
                        pil_images.append(img)
                        
                        # Also store this info in session state for future use
                        if 'deck_pokemon_info' not in st.session_state:
                            st.session_state.deck_pokemon_info = {}
                        if deck_name not in st.session_state.deck_pokemon_info:
                            st.session_state.deck_pokemon_info[deck_name] = []
                            
                        # Add this pokemon to the cached info
                        st.session_state.deck_pokemon_info[deck_name].append({
                            'name': pokemon_name,
                            'card_name': card_info['name'],
                            'set': card_info['set'],
                            'num': card_info['num']
                        })
    
    # 3. Last resort: Try to load sample deck data to get pokemon info
    if not pil_images and 'analyze' in st.session_state:
        import cache_manager
        
        # Try to get set name from deck_info or session state
        set_name = deck_info.get('set', st.session_state.analyze.get('set_name', 'A3'))
        
        # Get sample deck
        sample_deck = cache_manager.get_or_load_sample_deck(deck_name, set_name)
        
        # Extract Pokemon from deck name
        pokemon_names = extract_pokemon_from_deck_name(deck_name)
        
        if pokemon_names and 'pokemon_cards' in sample_deck:
            # Look for matching Pokemon in sample deck
            for i, pokemon_name in enumerate(pokemon_names[:2]):
                # Clean up the name for matching
                clean_name = pokemon_name.replace('-', ' ').title()
                if 'Ex' in clean_name:
                    clean_name = clean_name.replace('Ex', 'ex')
                
                # Find matching card
                for card in sample_deck['pokemon_cards']:
                    if card['card_name'].lower() == clean_name.lower() and card.get('set') and card.get('num'):
                        formatted_num = format_card_number(card['num'])
                        
                        # Fetch and crop the image
                        img = fetch_and_crop_image(card['set'], formatted_num)
                        
                        if img:
                            # Apply diagonal cut based on position
                            cut_type = "left" if i == 0 else "right"
                            img = apply_diagonal_cut(img, cut_type)
                            pil_images.append(img)
                            
                            # Store this info for future use
                            if 'deck_pokemon_info' not in st.session_state:
                                st.session_state.deck_pokemon_info = {}
                            if deck_name not in st.session_state.deck_pokemon_info:
                                st.session_state.deck_pokemon_info[deck_name] = []
                            
                            # Add to cached info
                            st.session_state.deck_pokemon_info[deck_name].append({
                                'name': pokemon_name,
                                'card_name': card['card_name'],
                                'set': card['set'],
                                'num': card['num']
                            })
                            
                            break
    
    # Handle cases with less than 2 images
    if not pil_images:
        return None
    elif len(pil_images) == 1:
        # For the case with one Pokémon, we need to handle this differently
        # Instead of duplicating the cut image, we need to fetch the original image again
        
        if 'deck_pokemon_info' in st.session_state and deck_name in st.session_state.deck_pokemon_info:
            # If we have Pokemon info in the cache
            pokemon_info = st.session_state.deck_pokemon_info[deck_name]
            if pokemon_info and len(pokemon_info) > 0:
                pokemon = pokemon_info[0]  # Get the first (and only) Pokemon
                
                if pokemon.get('set') and pokemon.get('num'):
                    formatted_num = format_card_number(pokemon['num'])
                    
                    # Fetch and crop the image AGAIN, but don't apply left cut
                    img = fetch_and_crop_image(pokemon['set'], formatted_num)
                    
                    if img:
                        # Apply RIGHT cut for the second image
                        img = apply_diagonal_cut(img, "right") 
                        pil_images.append(img)
        
        # If we couldn't add a second image using cached info, duplicate the first one
        if len(pil_images) == 1:
            # Find where we applied the left cut to get the original uncut image
            original_set = None
            original_num = None
            
            # Try to find the original set and number from the session state
            if 'deck_pokemon_info' in st.session_state and deck_name in st.session_state.deck_pokemon_info:
                pokemon_info = st.session_state.deck_pokemon_info[deck_name]
                if pokemon_info and len(pokemon_info) > 0:
                    original_set = pokemon_info[0].get('set')
                    original_num = pokemon_info[0].get('num')
            
            # If we found the original info, fetch it again
            if original_set and original_num:
                formatted_num = format_card_number(original_num)
                
                # Fetch and crop the image again
                img = fetch_and_crop_image(original_set, formatted_num)
                
                if img:
                    # Apply RIGHT cut this time
                    img = apply_diagonal_cut(img, "right")
                    pil_images.append(img)
            else:
                # Fallback: duplicate the first image with opposite cut
                # This is not ideal but better than nothing
                img = pil_images[0].copy()
                
                # We can't "uncut" it, but we can flip it horizontally to make it less obvious
                from PIL import ImageOps
                img = ImageOps.mirror(img)
                
                # Apply right cut pattern
                img = apply_diagonal_cut(img, "right")
                pil_images.append(img)

# Add a simple in-memory cache for thumbnails
_thumbnail_cache = {}

@functools.lru_cache(maxsize=100)
def get_card_thumbnail(set_code, number, size=40):
    """
    Fetch a small thumbnail of a card for chart labels with caching
    
    Parameters:
    set_code: String (example: "A3")
    number: String (example: "122")
    size: Integer - height in pixels
    
    Returns:
    Base64 encoded image string
    """
    cache_key = f"{set_code}-{number}-{size}"
    
    # Check cache first
    if cache_key in _thumbnail_cache:
        return _thumbnail_cache[cache_key]
    
    try:
        # Reuse existing function to fetch and crop
        img = fetch_and_crop_image(set_code, number)
        
        if img:
            # Resize to thumbnail
            width = int(img.width * (size / img.height))
            thumbnail = img.resize((width, size), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffered = BytesIO()
            thumbnail.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Cache the result
            _thumbnail_cache[cache_key] = img_str
            return img_str
        
        return None
    except Exception as e:
        print(f"Error creating thumbnail for {set_code}-{number}: {e}")
        return None

# Add this to image_processor.py or create a new pokemon_info_manager.py file

import streamlit as st
from image_processor import extract_pokemon_from_deck_name
import cache_manager

def preload_all_deck_pokemon_info():
    """
    Extract and cache Pokémon information for decks in the dropdown selection list.
    This should be called during app initialization to ensure all deck images can be generated.
    """
    if 'deck_pokemon_info' not in st.session_state:
        st.session_state.deck_pokemon_info = {}
    
    # Skip if we already have data
    if st.session_state.deck_pokemon_info:
        return
        
    # Make sure we have the deck mapping from dropdown
    if 'deck_name_mapping' not in st.session_state:
        return
    
    # Get the decks from the dropdown mapping
    deck_mapping = st.session_state.deck_name_mapping
    total_decks = len(deck_mapping)
    
    # Process each deck to extract Pokémon info
    with st.spinner("Pre-loading Pokémon data for meta decks..."):
        # Create a progress bar
        progress_bar = st.progress(0)
        
        # Process each deck with progress updates
        for i, (display_name, deck_info) in enumerate(deck_mapping.items()):
            # Update progress bar
            progress_bar.progress((i + 1) / total_decks)
            
            deck_name = deck_info['deck_name']
            set_name = deck_info['set']
            
            # Skip if already processed
            if deck_name in st.session_state.deck_pokemon_info:
                continue
                
            # Extract Pokémon names from the deck name
            pokemon_names = extract_pokemon_from_deck_name(deck_name)
            
            # Rest of the function remains the same...
            
            # Update caption less frequently
            #if i % 5 == 0:
            #    st.caption(f"Processing deck {i+1}/{total_decks}: {display_name}")
        
        # Clear progress bar when done
        progress_bar.empty()
