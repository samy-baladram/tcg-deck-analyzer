# card_renderer.py
import streamlit as st
from image_processor import format_card_number

# Configuration constants
class CardConfig:
    """Configuration constants for card rendering"""
    WIDTH = 100
    GAP = 8
    MARGIN = 8
    BORDER_RADIUS = 3
    BORDER_COLOR = "rgba(102, 102, 102, 0.5)"
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
        
    def add_card(self, card_name, set_code, num, count=1, usage_pct=None):
        """Add a card to the grid, repeating it 'count' times"""
        formatted_num = format_card_number(num) if num else ""
        
        # Generate HTML for each copy of the card
        for _ in range(count):
            card_html = self._generate_card_html(card_name, set_code, formatted_num, usage_pct)
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
    
    def _generate_card_html(self, card_name, set_code, formatted_num, usage_pct=None):
        """Generate HTML for a single card"""
        # Card container
        card_html = f"<div style=\"width: {self.card_width}px; margin-bottom: {self.margin_bottom}px;\" title=\"{card_name}\">"
        
        # Card image or fallback
        if set_code and formatted_num:
            card_html += self._generate_image_html(set_code, formatted_num)
        else:
            card_html += self._generate_fallback_html(card_name)
        
        # Add percentage if requested
        if self.show_percentage and usage_pct is not None:
            card_html += self._generate_percentage_html(usage_pct)
            
        card_html += "</div>"
        return card_html
    
    def _generate_image_html(self, set_code, formatted_num):
        """Generate HTML for card image"""
        return (f"<img src=\"{CardConfig.IMAGE_BASE_URL}/{set_code}/{set_code}_{formatted_num}_EN.webp\" "
                f"style=\"width: 100%; border-radius: {self.border_radius}px; border: 1px solid {self.border_color};\">")
    
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
                f"style=\"text-align: center; margin-top: 4px; "
                f"font-size: {self.percentage_font_size}px; font-weight: 500;\">"
                f"{usage_pct}%</div>")
    
    def render(self):
        """Render the card grid and return HTML"""
        grid_html = (f"<div style=\"display: flex; flex-wrap: wrap; gap: {self.gap}px;\">"
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
        st.markdown(f"#### {section_title} ({card_count})", unsafe_allow_html=True)
        
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
        st.markdown(f"#### {section_title}", unsafe_allow_html=True)
        
        # Create and display card grid with percentages
        grid = CardGrid(
            card_width=95,
            margin_bottom=12,
            show_percentage=True,
            percentage_font_size=14
        )
        
        grid.add_cards_from_dataframe(cards_df).display()
    
    @staticmethod
    def render_variant_cards(var1_set, var1_num, var2_set, var2_num, var1, var2):
        """Render variant cards side by side"""
        formatted_num1 = format_card_number(var1_num) if var1_num else ""
        formatted_num2 = format_card_number(var2_num) if var2_num else ""
        
        # Create HTML for variant comparison
        variant_html = f"""<div style="height:200px; display:flex; justify-content:space-between; margin-top:-10px;">
            <!-- Variant 1 -->
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                <div style="text-align:center; margin-bottom:2px;"><strong>{var1}</strong></div>
                {
                    f'<img src="{CardConfig.IMAGE_BASE_URL}/{var1_set}/{var1_set}_{formatted_num1}_EN.webp" style="max-height:180px; max-width:100%; object-fit:contain; border:1px solid {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px;">' 
                    if var1_set and formatted_num1 else
                    f'<div style="border:1px dashed {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px; padding:20px; color:#888; text-align:center; width:80%;">Image not available</div>'
                }
            </div>
            <!-- Variant 2 -->
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                <div style="text-align:center; margin-bottom:2px;"><strong>{var2}</strong></div>
                {
                    f'<img src="{CardConfig.IMAGE_BASE_URL}/{var2_set}/{var2_set}_{formatted_num2}_EN.webp" style="max-height:180px; max-width:100%; object-fit:contain; border:1px solid {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px;">' 
                    if var2_set and formatted_num2 else
                    f'<div style="border:1px dashed {CardConfig.BORDER_COLOR}; border-radius:{CardConfig.BORDER_RADIUS}px; padding:20px; color:#888; text-align:center; width:80%;">Image not available</div>'
                }
            </div>
        </div>"""
        return variant_html


# Export simplified interface for backward compatibility
render_deck_section = CardRenderer.render_deck_section
render_option_section = CardRenderer.render_option_section
render_variant_cards = CardRenderer.render_variant_cards
