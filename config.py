# config.py
"""Configuration and constants for the TCG Deck Analyzer"""

# API and website URLs
BASE_URL = "https://play.limitlesstcg.com"
IMAGE_BASE_URL = "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket"

# Cache settings
CACHE_TTL = 3600  # 1 hour in seconds

# Tournament count
TOURNAMENT_COUNT = 70

# Display settings
MIN_META_SHARE = 0.5  # Minimum meta share percentage to display

# Meta-weighted win rate configuration
MWWR_MIN_SHARE = 0.5          # Minimum meta share for inclusion (0.5%)
MWWR_USE_SQUARED = True        # Whether to use squared meta share in weighting
MWWR_DEVIATION_BASED = True    # Whether to use deviation from 50% win rate
MWWR_NEUTRAL_WINRATE = 50.0    # The win rate considered "neutral" (50%)

# Formula description depends on the mode
MWWR_FORMULA_STANDARD = "Meta-weighted win rate = Σ(win% against deck × deck's meta share²) ÷ Σ(deck's meta share²)"
MWWR_FORMULA_DEVIATION = "Meta-weighted win rate = Σ((win% - 50%)² × sign(win% - 50%) × deck's meta share) ÷ Σ(deck's meta share)"
MWWR_DESCRIPTION_STANDARD = """
This score weights each matchup by the square of the opponent's meta share percentage.
This gives extra importance to matchups against the most common decks, accounting for
their faster rate of prevalence in the metagame.
"""
MWWR_DESCRIPTION_DEVIATION = """
This score emphasizes how much a deck's win rates deviate from 50% against the meta.
It quadratically weights matchups that strongly deviate from 50% (either wins or losses)
while preserving the sign (positive for >50%, negative for <50%). This helps identify
decks that have decisive matchups against the current metagame.
"""

CHART_COLORS = {
    'pokemon_1': '#81D4FA',  # Light blue
    'pokemon_2': '#0288D1',  # Darker blue
    'trainer_1': '#dfdde0',  # Light green
    'trainer_2': '#bbb7bd',  # Darker green
    'mixed': '#bbb7bd'       # Medium blue
}

# Pokemon Exceptions
POKEMON_EXCEPTIONS = {
        'oricorio': 'oricorio-pom-pom',
        'lycanroc': 'lycanroc-midnight'
    }

# Chart settings
CHART_MIN_HEIGHT = 350
CHART_ROW_HEIGHT = 45
VAR_CHART_MIN_HEIGHT = 180
VAR_CHART_ROW_HEIGHT = 60
CHART_FONT_SIZE = 15
CHART_BAR_GAP = 0.2
CHART_TEXT_THRESHOLD = 5  # Don't show percentage if less than this

# Plotly config to disable interactivity
PLOTLY_CONFIG = {
    'displayModeBar': False,
    'staticPlot': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'zoom2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
    'doubleClick': False,
    'showTips': False,
    'allowHTML': True  # Add this to allow HTML in labels
}

# Image processing settings
IMAGE_CROP_BOX = {
    'left': 0.05,
    'top': 0.115,
    'right': 0.95,
    'bottom': 0.47
}

IMAGE_GRADIENT = {
    'top_height': 0.02,
    'bottom_height': 0.02
}

# Category thresholds
CATEGORY_BINS = [-1, 25, 70, 100]
CATEGORY_LABELS = ['Tech', 'Standard', 'Core']

# Flexible core thresholds
FLEXIBLE_CORE_THRESHOLD = 25

# Save configuration function to persist changes
def save_current_config():
    """Save the current formula configuration to disk"""
    import cache_utils
    
    # Create a dictionary of the current configuration
    config_dict = {
        'MWWR_USE_SQUARED': MWWR_USE_SQUARED,
        'MWWR_DEVIATION_BASED': MWWR_DEVIATION_BASED,
        'MWWR_NEUTRAL_WINRATE': MWWR_NEUTRAL_WINRATE,
        'MWWR_MIN_SHARE': MWWR_MIN_SHARE
    }
    
    # Print debug info
    print(f"Saving config to disk: SQUARED={MWWR_USE_SQUARED}, DEVIATION={MWWR_DEVIATION_BASED}")
    
    # Save to disk
    cache_utils.save_formula_config(config_dict)

# Make sure this function is called whenever a config value changes
# Add this at the bottom of config.py
save_current_config()
