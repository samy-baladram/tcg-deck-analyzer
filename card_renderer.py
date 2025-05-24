# card_renderer.py
import streamlit as st
from image_processor import format_card_number

# Configuration constants
class CardConfig:
    """Configuration constants for card rendering"""
    WIDTH = 76
    GAP = 8
    MARGIN = 8
    BORDER_RADIUS = 5
    BORDER_COLOR = "rgba(102, 102, 102, 0.3)"
    FALLBACK_HEIGHT = 140
    PERCENTAGE_FONT_SIZE = 14
    IMAGE_BASE_URL = "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket"


class CardGrid:
    """Class for rendering grids of Pokémon TCG cards"""
    
    def __init__(self, 
                 card_width=CardConfig.WIDTH, 
                 gap=CardConfig.GAP, 
                 margin_bottom=CardConfig.MARGIN,
                 border_radius=CardConfig.BORDER_RADIUS,
                 border_color=CardConfig.BORDER_COLOR,
                 show_percentage=False,
                 percentage_font_size=CardConfig.PERCENTAGE_FONT_SIZE):
        """Initialize a card grid with styling options"""
        self.card_width = card_width
        self.gap = gap
        self.margin_bottom = margin_bottom
        self.border_radius = border_radius
        self.border_color = border_color
        self.show_percentage = show_percentage
        self.percentage_font_size = percentage_font_size
        self.cards_html = []
    
    def clear(self):
        """Clear all cards from the grid"""
        self.cards_html = []
        return self
        
    def add_card(self, card_name, set_code, num, count=1, usage_pct=None, card_data=None):
        """Add a card to the grid, repeating it 'count' times"""
        formatted_num = format_card_number(num) if num else ""
        
        # Generate HTML for each copy of the card
        for _ in range(count):
            card_html = self._generate_card_html(card_name, set_code, formatted_num, usage_pct, card_data)
            self.cards_html.append(card_html)
        
        return self
            
    def add_cards_from_dict(self, cards_dict, repeat_by_count=True):
        """Add multiple cards from a dictionary with fields: name, set, num, count (optional)"""
        if not cards_dict:
            return self
            
        for card in cards_dict:
            count = card.get('count', 1) if repeat_by_count else 1
            usage_pct = card.get('display_usage', None)
            self.add_card(
                card_name=card.get('name', card.get('card_name', '')),
                set_code=card.get('set', ''),
                num=card.get('num', ''),
                count=count,
                usage_pct=usage_pct
            )
        
        return self
    
    def add_cards_from_dataframe(self, df, repeat_by_count=False):
        """Add cards from a pandas DataFrame"""
        if df is None or df.empty:
            return self
            
        for _, card in df.iterrows():
            count = 1
            if repeat_by_count and 'count' in df.columns:
                count = card['count']
                
            usage_pct = None
            if 'display_usage' in df.columns:
                usage_pct = card['display_usage']
                
            self.add_card(
                card_name=card.get('card_name', ''),
                set_code=card.get('set', ''),
                num=card.get('num', ''),
                count=count,
                usage_pct=usage_pct
            )
        
        return self
    
    def _generate_card_html(self, card_name, set_code, formatted_num, usage_pct=None, card_data=None):
        """Generate HTML for a single card"""
        # Card container
        card_html = f"<div style=\"width: {self.card_width}px; margin-bottom: {self.margin_bottom}px;\" title=\"{card_name}\">"
        
        # Card image or fallback
        if set_code and formatted_num:
            card_html += self._generate_image_html(set_code, formatted_num, card_data)
        else:
            card_html += self._generate_fallback_html(card_name)
        
        # Add percentage if requested
        if self.show_percentage and usage_pct is not None:
            card_html += self._generate_percentage_html(usage_pct)
            
        card_html += "</div>"
        return card_html
    
    def _generate_image_html(self, set_code, formatted_num, card_data=None):
        """Generate HTML for card image with hover effect"""
        # Standard card image URL
        standard_url = f"{CardConfig.IMAGE_BASE_URL}/{set_code}/{set_code}_{formatted_num}_EN.webp"
        
        # Create basic image HTML
        img_html = (f"<img src=\"{standard_url}\" "
                f"style=\"width: 100%; border-radius: {self.border_radius}px; border: 0.5px solid {self.border_color};\">")
        
        # Enhance with hover effect and clickability
        # Pass card_data if available for better set/num handling
        if card_data:
            enhanced_html = enhance_card_image_html(img_html, standard_url, card_data)
        else:
            enhanced_html = enhance_card_image_html(img_html, standard_url)
        
        return enhanced_html
    
    def _generate_fallback_html(self, card_name):
        """Generate HTML for fallback when image is not available"""
        return (f"<div style=\"border: 1px dashed {self.border_color}; "
                f"border-radius: {self.border_radius}px; "
                f"padding: 5px; height: {CardConfig.FALLBACK_HEIGHT}px; "
                f"display: flex; align-items: center; justify-content: center; "
                f"text-align: center; font-size: 11px;\">{card_name}</div>")
    
    def _generate_percentage_html(self, usage_pct):
        """Generate HTML for usage percentage display"""
        return (f"<div class=\"card-percentage\" "
                f"style=\"text-align: center; margin: 0 0 0 0px; "
                f"font-size: {self.percentage_font_size}px; font-weight: 500;\">"
                f"{usage_pct}%</div>")
    
    def render(self):
        """Render the card grid and return HTML"""
        grid_html = (f"<div style=\"display: flex; flex-wrap: wrap; gap: {self.gap}px; justify-content: center;\">"
                    f"{''.join(self.cards_html)}"
                    f"</div>")
        return grid_html
    
    def display(self):
        """Display the card grid in Streamlit"""
        st.markdown(self.render(), unsafe_allow_html=True)
        return self


class CardRenderer:
    """Utility class with static methods for rendering different card displays"""
    
    @staticmethod
    def render_deck_section(cards, section_title, card_count=None):
        """Render a complete deck section with title and cards"""
        if card_count is None and isinstance(cards, list):
            card_count = sum(card.get('count', 1) for card in cards)
        
        # Display section title
        st.markdown(f"##### {section_title} ({card_count})", unsafe_allow_html=True)
        
        # Create and display card grid
        grid = CardGrid()
        if isinstance(cards, list):
            grid.add_cards_from_dict(cards, repeat_by_count=True)
        else:
            grid.add_cards_from_dataframe(cards, repeat_by_count=False)
        
        grid.display()
    
    @staticmethod
    def render_option_section(cards_df, section_title):
        """Render options section with percentages"""
        st.markdown(f"##### {section_title}", unsafe_allow_html=True)
        
        # Create and display card grid with percentages
        grid = CardGrid(
            card_width=95,
            margin_bottom=12,
            show_percentage=True,
            percentage_font_size=15
        )
        
        grid.add_cards_from_dataframe(cards_df).display()
    
    @staticmethod
    def render_variant_cards(var1_set, var1_num, var2_set, var2_num, var1, var2):
        """Render variant cards side by side"""
        formatted_num1 = format_card_number(var1_num) if var1_num else ""
        formatted_num2 = format_card_number(var2_num) if var2_num else ""
        
        # Create image URLs
        var1_url = f"{CardConfig.IMAGE_BASE_URL}/{var1_set}/{var1_set}_{formatted_num1}_EN.webp" if var1_set and formatted_num1 else ""
        var2_url = f"{CardConfig.IMAGE_BASE_URL}/{var2_set}/{var2_set}_{formatted_num2}_EN.webp" if var2_set and formatted_num2 else ""
        
        # Create HTML for variant comparison
        variant_html = f"""<div style="height:170px; display:flex; flex-direction:row; justify-content:space-between; margin-top:-10px;">
            <!-- Variant 1 -->
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                <div style="text-align:center; margin-bottom:2px;"><strong>{var1}</strong></div>
                {
                    f'<img class="card-image" src="{var1_url}" style="max-height:150px; max-width:100%; object-fit:contain; border:1px solid {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px;">' 
                    if var1_url else
                    f'<div style="border:1px dashed {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px; padding:20px; color:#888; text-align:center; width:80%;">Image not available</div>'
                }
            </div>
            <!-- Variant 2 -->
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                <div style="text-align:center; margin-bottom:2px;"><strong>{var2}</strong></div>
                {
                    f'<img class="card-image" src="{var2_url}" style="max-height:150px; max-width:100%; object-fit:contain; border:1px solid {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px;">' 
                    if var2_url else
                    f'<div style="border:1px dashed {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px; padding:20px; color:#888; text-align:center; width:80%;">Image not available</div>'
                }
            </div>
        </div>"""
        # variant_html = f"""
        #     <div style="flex:1; display:flex; flex-direction:column; align-items:center; margin-top:-10px; margin-bottom:-20px; justify-content:center;">
        #         <div style="text-align:center; margin-bottom:0px;"><strong>{var1}</strong></div>
        #         {
        #             f'<img class="card-image" src="{var1_url}" style="max-height:100px; max-width:100%; object-fit:contain; margin-bottom:10px; border:1px solid {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px;">' 
        #         }
        #     </div>
        #     <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
        #         <div style="text-align:center; margin-bottom:0px;"><strong>{var2}</strong></div>
        #         {
        #             f'<img class="card-image" src="{var2_url}" style="max-height:100px; max-width:100%; object-fit:contain; margin-bottom:10px; border:1px solid {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px;">' 
        #         }
        #     </div>"""
        return variant_html


# Export simplified interface for backward compatibility
render_deck_section = CardRenderer.render_deck_section
render_option_section = CardRenderer.render_option_section
render_variant_cards = CardRenderer.render_variant_cards

# Final solution: Add this function to card_renderer.py
def render_sidebar_deck(pokemon_cards, trainer_cards, card_width=65):
    """
    Render a condensed version of a deck for the sidebar.
    Cards are displayed all together with duplicates shown.
    
    Args:
        pokemon_cards: List of Pokemon card dictionaries
        trainer_cards: List of Trainer card dictionaries
        card_width: Width of each card in pixels
        
    Returns:
        HTML string for rendering the deck
    """
    # Create a single grid for all cards
    all_cards = []
    
    # Add all cards to a single list with duplicates based on the amount
    for card in pokemon_cards:
        count = card.get('amount', 1)
        for _ in range(count):
            all_cards.append({
                'card_name': card.get('card_name', ''),
                'set': card.get('set', ''),
                'num': card.get('num', ''),
                'count': 1  # Each card is counted individually now
            })
            
    for card in trainer_cards:
        count = card.get('amount', 1)
        for _ in range(count):
            all_cards.append({
                'card_name': card.get('card_name', ''),
                'set': card.get('set', ''),
                'num': card.get('num', ''),
                'count': 1  # Each card is counted individually now
            })
    
    # Create the grid with all cards
    grid = CardGrid(card_width=card_width, gap=3, margin_bottom=4)
    grid.add_cards_from_dict(all_cards, repeat_by_count=False)  # No need to repeat now
    
    # Generate HTML for the entire deck
    html = f"""
    <div style="margin-bottom: 8px;">
        {grid.render()}
    </div>
    """
    
    return html

def add_card_hover_effect():
    """
    Add a simple JavaScript for card hover effect.
    This is a minimal implementation to get basic functionality working.
    """
    hover_js = """
    <script>
    // Simple version - just creates a popup and attaches directly to images
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Simple card hover script loaded');
        
        // Create the popup element
        const popup = document.createElement('div');
        popup.id = 'simple-card-popup';
        popup.style.cssText = `
            position: fixed;
            display: none; 
            z-index: 9999;
            background-color: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
            border-radius: 10px;
            width: 250px;
            height: 350px;
            pointer-events: none;
        `;
        document.body.appendChild(popup);
        
        // Function to handle card hover
        function handleCardHover() {
            // Apply to all images
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                img.addEventListener('mouseenter', function() {
                    // Show enlarged version of this image
                    popup.innerHTML = '';
                    const enlargedImg = document.createElement('img');
                    enlargedImg.src = this.src;
                    enlargedImg.style.cssText = `
                        width: 100%;
                        height: 100%;
                        object-fit: contain;
                        border-radius: 10px;
                    `;
                    popup.appendChild(enlargedImg);
                    
                    // Position popup near the mouse
                    const rect = this.getBoundingClientRect();
                    popup.style.left = (rect.right + 10) + 'px';
                    popup.style.top = rect.top + 'px';
                    
                    // Check if popup would go off right edge
                    if (rect.right + 260 > window.innerWidth) {
                        popup.style.left = (rect.left - 260) + 'px';
                    }
                    
                    // Show popup
                    popup.style.display = 'block';
                });
                
                img.addEventListener('mouseleave', function() {
                    // Hide popup
                    popup.style.display = 'none';
                });
            });
        }
        
        // Initial setup
        handleCardHover();
        
        // Check periodically for new images
        setInterval(handleCardHover, 2000);
        
        // Display debug message on the page
        const debug = document.createElement('div');
        debug.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px;
            z-index: 10000;
            font-size: 12px;
        `;
        debug.textContent = 'Card hover active';
        document.body.appendChild(debug);
        setTimeout(() => debug.remove(), 5000);
    });
    </script>
    """
    
    # Add the JavaScript to the Streamlit app
    import streamlit as st
    st.markdown(hover_js, unsafe_allow_html=True)

def enhance_card_image_html(img_html, full_size_url=None, card_data=None):
    """
    Enhance an image HTML string to make it clickable.
    Links to the Limitless TCG card page using card data or URL parsing.
    
    Parameters:
    img_html: HTML string containing an img tag
    full_size_url: Optional URL to a full-size version of the image
    card_data: Optional dict with 'set' and 'num' fields (preferred method)
    
    Returns:
    Enhanced HTML string with clickable functionality to card page
    """
    # Method 1: Use card_data if provided (preferred)
    if card_data and card_data.get('set') and card_data.get('num'):
        set_code = card_data['set']
        card_num = str(card_data['num']).lstrip('0')  # Remove leading zeros
        
        # Create the card page URL
        card_page_url = f"https://pocket.limitlesstcg.com/cards/{set_code}/{card_num}"
        
        # Wrap the image in an anchor tag
        enhanced_html = f'<a href="{card_page_url}" target="_blank" style="cursor: pointer;">{img_html}</a>'
        return enhanced_html
    
    # Method 2: Fallback to URL parsing (existing method)
    import re
    src_match = re.search(r'src="[^"]+/([A-Za-z0-9-]+)/\1_(\d+)_EN\.webp"', img_html)
    
    if src_match:
        set_code = src_match.group(1)
        card_num = src_match.group(2).lstrip('0')  # Remove leading zeros
        
        # Create the card page URL
        card_page_url = f"https://pocket.limitlesstcg.com/cards/{set_code}/{card_num}"
        
        # Wrap the image in an anchor tag
        enhanced_html = f'<a href="{card_page_url}" target="_blank" style="cursor: pointer;">{img_html}</a>'
        return enhanced_html
    
    # If we couldn't extract the set code and number, return the original HTML
    return img_html
