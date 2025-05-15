# image_processor.py
"""Image processing functions for deck header images"""

import base64
import requests
from PIL import Image, ImageDraw
from io import BytesIO
import re
from config import IMAGE_BASE_URL, IMAGE_CROP_BOX, IMAGE_GRADIENT
from utils import is_set_code

def get_base64_image(path):
    """Convert image file to base64 string"""
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def fetch_and_process_vertical_gradient(set_code, number):
    """
    Fetch, crop, and add gradient transparency to top and bottom.
    
    Parameters:
    set_code: String (example: "A3")
    number: String (example: "122")
    
    Returns:
    PIL Image with gradient transparency at top and bottom
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
        
        # Create mask with full opacity
        mask = Image.new('L', cropped.size, 255)
        draw = ImageDraw.Draw(mask)
        
        # Calculate gradient heights
        gradient_height_top = int(cropped.height * IMAGE_GRADIENT['top_height'])
        gradient_height_bottom = int(cropped.height * IMAGE_GRADIENT['bottom_height'])
        
        # Draw top gradient (fade in from top)
        for y in range(gradient_height_top):
            opacity = int(255 * (y / gradient_height_top))
            draw.rectangle([(0, y), (cropped.width, y)], fill=opacity)
        
        # Draw bottom gradient (fade out to bottom)
        for y in range(gradient_height_bottom):
            y_pos = cropped.height - gradient_height_bottom + y
            opacity = int(255 * (1 - y / gradient_height_bottom))
            draw.rectangle([(0, y_pos), (cropped.width, y_pos)], fill=opacity)
        
        # Apply mask to alpha channel
        cropped.putalpha(mask)
        
        return cropped
    
    except Exception as e:
        print(f"Error fetching image for {set_code}-{number}: {e}")
        return None

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

def create_deck_header_images(deck_info, analysis_results):
    """
    Create header images for a deck based on Pokemon in the deck name
    Returns list of base64 encoded images (empty if no valid images found)
    """
    # Extract Pokemon from deck name
    pokemon_names = extract_pokemon_from_deck_name(deck_info['deck_name'])
    
    # Get card info for each Pokemon
    images = []
    
    for pokemon_name in pokemon_names:
        card_info = get_pokemon_card_info(pokemon_name, analysis_results)
        
        if card_info:
            formatted_num = format_card_number(card_info['num'])
            
            # Fetch and process the image
            img = fetch_and_process_vertical_gradient(card_info['set'], formatted_num)
            
            if img:
                # Convert to base64
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                images.append(img_base64)
    
    # If we only found one Pokemon, duplicate it
    if len(images) == 1:
        images.append(images[0])
    
    # Return empty list if no valid images found
    return images
