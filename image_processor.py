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
    Returns a single base64 encoded merged image
    """
    # Extract Pokemon from deck name
    pokemon_names = extract_pokemon_from_deck_name(deck_info['deck_name'])
    
    if not pokemon_names:
        return None
    
    pil_images = []
    
    # Get images for each Pokemon
    for i, pokemon_name in enumerate(pokemon_names[:2]):
        card_info = get_pokemon_card_info(pokemon_name, analysis_results)
        
        if card_info:
            formatted_num = format_card_number(card_info['num'])
            
            # Fetch and crop the image (without gradient)
            img = fetch_and_crop_image(card_info['set'], formatted_num)
            
            if img:
                # Apply diagonal cut based on position
                cut_type = "left" if i == 0 else "right"
                img = apply_diagonal_cut(img, cut_type)
                pil_images.append(img)
    
    # Handle cases with less than 2 images
    if len(pil_images) == 0:
        return None
    elif len(pil_images) == 1:
        # Fetch the same image again for the right side
        pokemon_name = pokemon_names[0]
        card_info = get_pokemon_card_info(pokemon_name, analysis_results)
        if card_info:
            formatted_num = format_card_number(card_info['num'])
            img = fetch_and_crop_image(card_info['set'], formatted_num)
            if img:
                img = apply_diagonal_cut(img, "right")
                pil_images.append(img)
    
    if len(pil_images) < 2:
        return None
    
    # Merge the two images (without gradient)
    cutoff_percentage = 0.7
    merged_image = merge_header_images(
        pil_images[0], 
        pil_images[1], 
        gap=5,
        cutoff_percentage=cutoff_percentage
    )
    
    # Apply gradient to the merged image
    merged_with_gradient = apply_vertical_gradient(merged_image)
    
    # Convert to base64
    buffered = BytesIO()
    merged_with_gradient.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return img_base64
