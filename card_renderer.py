# card_renderer.py
import streamlit as st
from image_processor import format_card_number

# Default card styling constants
DEFAULT_CARD_WIDTH = 100
DEFAULT_CARD_GAP = 8
DEFAULT_CARD_MARGIN = 8
DEFAULT_BORDER_RADIUS = 3
DEFAULT_BORDER_COLOR = "rgba(102, 102, 102, 0.5)"
DEFAULT_FALLBACK_HEIGHT = 140
DEFAULT_PERCENTAGE_FONT_SIZE = 14
IMAGE_BASE_URL = "https://limitlesstcg.nyc3.digitaloceanspaces.com/tpci/cards/poke"  # Make sure to import this correctly

class CardGrid:
    """Class for rendering grids of Pokémon TCG cards"""
    
    def __init__(self, 
                 card_width=DEFAULT_CARD_WIDTH, 
                 gap=DEFAULT_CARD_GAP, 
                 margin_bottom=DEFAULT_CARD_MARGIN,
                 border_radius=DEFAULT_BORDER_RADIUS,
                 border_color=DEFAULT_BORDER_COLOR,
                 show_percentage=False,
                 percentage_font_size=DEFAULT_PERCENTAGE_FONT_SIZE):
        """Initialize a card grid with styling options"""
        self.card_width = card_width
        self.gap = gap
        self.margin_bottom = margin_bottom
        self.border_radius = border_radius
        self.border_color = border_color
        self.show_percentage = show_percentage
        self.percentage_font_size = percentage_font_size
        self.cards_html = []
        
    def add_card(self, card_name, set_code, num, count=1, usage_pct=None):
        """Add a card to the grid, repeating it 'count' times"""
        formatted_num = format_card_number(num) if num else ""
        
        # Generate HTML for each copy of the card
        for _ in range(count):
            card_html = self._generate_card_html(card_name, set_code, formatted_num, usage_pct)
            self.cards_html.append(card_html)
            
    def add_cards_from_dict(self, cards_dict, repeat_by_count=True):
        """Add multiple cards from a dictionary with fields: name, set, num, count (optional)"""
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
    
    def add_cards_from_dataframe(self, df, repeat_by_count=False):
        """Add cards from a pandas DataFrame"""
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
    def _generate_card_html(self, card_name, set_code, formatted_num, usage_pct=None):
        """Generate HTML for a single card"""
        card_html = f"<div style=\"width: {self.card_width}px; margin-bottom: {self.margin_bottom}px;\" title=\"{card_name}\">"
        
        # Card image or fallback
        if set_code and formatted_num:
            # Make sure the URL matches exactly what was working before
            card_html += f"<img src=\"{IMAGE_BASE_URL}/{set_code}/{set_code}_{formatted_num}_EN.webp\" style=\"width: 100%; border-radius: {self.border_radius}px; border: 1px solid {self.border_color};\">"
        else:
            card_html += f"<div style=\"border: 1px dashed {self.border_color}; border-radius: {self.border_radius}px; padding: 5px; height: {DEFAULT_FALLBACK_HEIGHT}px; display: flex; align-items: center; justify-content: center; text-align: center; font-size: 11px;\">{card_name}</div>"
        
        # Add percentage if requested
        if self.show_percentage and usage_pct is not None:
            card_html += f"<div class=\"card-percentage\" style=\"text-align: center; margin-top: 4px; font-size: {self.percentage_font_size}px; font-weight: 500;\">{usage_pct}%</div>"
            
        card_html += "</div>"
        return card_html
    
    def render(self):
        """Render the card grid and return HTML"""
        grid_html = f"""<div style="display: flex; flex-wrap: wrap; gap: {self.gap}px;">
            {''.join(self.cards_html)}
        </div>"""
        return grid_html
    
    def display(self):
        """Display the card grid in Streamlit"""
        st.markdown(self.render(), unsafe_allow_html=True)

# Utility functions for quick card rendering
def render_deck_section(cards, section_title, card_count=None):
    """Render a complete deck section with title and cards"""
    if card_count is None and isinstance(cards, list):
        card_count = sum(card.get('count', 1) for card in cards)
    
    st.markdown(f"<h4 style='font-family: Nunito, sans-serif; font-weight: 600;'>{section_title} ({card_count})</h4>", unsafe_allow_html=True)
    
    grid = CardGrid()
    if isinstance(cards, list):
        grid.add_cards_from_dict(cards, repeat_by_count=True)
    else:
        grid.add_cards_from_dataframe(cards, repeat_by_count=False)
    
    grid.display()

def render_option_section(cards_df, section_title):
    """Render options section with percentages"""
    st.markdown(f"####{section_title}", unsafe_allow_html=True)
    
    grid = CardGrid(
        card_width=95,
        margin_bottom=12,
        show_percentage=True,
        percentage_font_size=14
    )
    
    grid.add_cards_from_dataframe(cards_df)
    grid.display()

def render_variant_cards(var1_set, var1_num, var2_set, var2_num, var1, var2):
    """Render variant cards side by side"""
    formatted_num1 = format_card_number(var1_num) if var1_num else ""
    formatted_num2 = format_card_number(var2_num) if var2_num else ""
    
    variant_html = f"""<div style="height:240px; display:flex; justify-content:space-between; margin-top:-20px;">
        <!-- Variant 1 -->
        <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
            <div style="text-align:center; margin-bottom:2px;"><strong>{var1}</strong></div>
            {
                f'<img src="{IMAGE_BASE_URL}/{var1_set}/{var1_set}_{formatted_num1}_EN.webp" style="max-height:180px; max-width:100%; object-fit:contain; border:1px solid rgba(102, 102, 102, 0.5); border-radius:3px;">' 
                if var1_set and formatted_num1 else
                '<div style="border:1px dashed rgba(102, 102, 102, 0.5); border-radius:3px; padding:20px; color:#888; text-align:center; width:80%;">Image not available</div>'
            }
        </div>
        <!-- Variant 2 -->
        <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
            <div style="text-align:center; margin-bottom:2px;"><strong>{var2}</strong></div>
            {
                f'<img src="{IMAGE_BASE_URL}/{var2_set}/{var2_set}_{formatted_num2}_EN.webp" style="max-height:180px; max-width:100%; object-fit:contain; border:1px solid rgba(102, 102, 102, 0.5); border-radius:3px;">' 
                if var2_set and formatted_num2 else
                '<div style="border:1px dashed rgba(102, 102, 102, 0.5); border-radius:3px; padding:20px; color:#888; text-align:center; width:80%;">Image not available</div>'
            }
        </div>
    </div>"""
    return variant_html
