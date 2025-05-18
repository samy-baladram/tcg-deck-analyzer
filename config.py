# config.py
"""Configuration and constants for the TCG Deck Analyzer"""

# API and website URLs
BASE_URL = "https://play.limitlesstcg.com"
IMAGE_BASE_URL = "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket"

# Cache settings
CACHE_TTL = 3600  # 1 hour in seconds

# Tournament count
TOURNAMENT_COUNT = 40

# Display settings
MIN_META_SHARE = 0.5  # Minimum meta share percentage to display

CHART_COLORS = {
    'pokemon_1': '#81D4FA',  # Light blue
    'pokemon_2': '#0288D1',  # Darker blue
    'trainer_1': '#dfdde0',  # Light green
    'trainer_2': '#bbb7bd',  # Darker green
    'mixed': '#bbb7bd'       # Medium blue
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
    'bottom': 0.45
}

IMAGE_GRADIENT = {
    'top_height': 0.00,
    'bottom_height': 0.00
}

# Category thresholds
CATEGORY_BINS = [-1, 25, 70, 100]
CATEGORY_LABELS = ['Tech', 'Standard', 'Core']

# Flexible core thresholds
FLEXIBLE_CORE_THRESHOLD = 25
