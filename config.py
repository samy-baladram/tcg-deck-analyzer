# config.py
"""Configuration and constants for the TCG Deck Analyzer"""

# API and website URLs
BASE_URL = "https://play.limitlesstcg.com"
IMAGE_BASE_URL = "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket"

# Cache settings
CACHE_TTL = 3600  # 1 hour in seconds

# Display settings
MIN_META_SHARE = 0.5  # Minimum meta share percentage to display

# Chart colors
CHART_COLORS = {
    'pokemon_1': 'lightskyblue',
    'pokemon_2': 'cornflowerblue',
    'trainer_1': 'lightskyblue',
    'trainer_2': 'cornflowerblue'
}

# Chart settings
CHART_MIN_HEIGHT = 350
CHART_ROW_HEIGHT = 40
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
    'showTips': False
}

# Image processing settings
IMAGE_CROP_BOX = {
    'left': 0.05,
    'top': 0.12,
    'right': 0.95,
    'bottom': 0.45
}

IMAGE_GRADIENT = {
    'top_height': 0.2,
    'bottom_height': 0.6
}

# Category thresholds
CATEGORY_BINS = [-1, 25, 70, 100]
CATEGORY_LABELS = ['Tech', 'Standard', 'Core']

# Flexible core thresholds
FLEXIBLE_CORE_THRESHOLD = 25
