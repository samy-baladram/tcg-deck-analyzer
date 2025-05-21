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

# Text for sidebar
POWER_INDEX_EXPLANATION = """
#### Power Index: How We Rank the Best Decks

**Data Source and Limitations**  
The Power Index uses recent tournament data from [Limitless TCG](https://play.limitlesstcg.com/tournaments/completed), specifically the most recent {tournament_count} tournaments. This provides a rolling window of competitive results that adapts as the metagame evolves. Note that this data only includes reported "Best Finish" results, which may represent a subset of all matches played.

**Formula and Methodology**  
The Power Index is calculated as:

Power Index = (Wins - Losses) / √(Wins + Losses)

This formula balances three critical factors:
* Win-loss differential (raw performance)
* Sample size (statistical confidence)
* Recent metagame context (using latest tournament data)

**Advantages Over Alternative Metrics**
* **More robust than Win Rate**: Differentiates between decks with small sample sizes and those with proven consistency
* **More dynamic than Popularity**: Measures actual competitive performance rather than just prevalence in the meta
* **More normalized than Raw Record**: A 20-5 record and a 40-10 record would have different win rates but similar Power Index values, properly accounting for confidence

**Interpretation Guide**
* **Positive values**: Indicate winning records (higher values = stronger performance)
* **Negative values**: Indicate losing records (generally filtered from top displays)
* **Magnitude**: Values typically range from -3 to +3, with top-tier decks usually above 1.0

**Important Caveats**
* The metric is sensitive to metagame shifts and tournament representation
* Limited by the quantity of available tournament data
* Best used as one factor in deck selection alongside matchup analysis and personal play style considerations
"""
