# config.py
"""Configuration and constants for the TCG Deck Analyzer"""
import streamlit as st

# API and website URLs
BASE_URL = "https://play.limitlesstcg.com"
IMAGE_BASE_URL = "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket"

# Cache settings
CACHE_TTL = 3600  # 1 hour in seconds
CURRENT_SET = "A3a"

# Add to config.py
ALGORITHM_VERSION = 1  # Increment this when you change algorithms like analyze_recent_performance

# Tournament count
TOURNAMENT_COUNT = 70
MIN_MATCHUP_MATCHES = 5
MIN_COUNTER_MATCHES = 8

# Display settings
MIN_META_SHARE = 0.04  # Minimum meta share percentage to display
MIN_WIN_RATE = 45 # Minimum win rate share percentage to display

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

# Pokemon URL mapping exceptions - context-dependent replacements
POKEMON_URL_EXCEPTIONS = {
    # Format: 'pokemon_name': {
    #     'paired_with_pokemon': 'replacement_name',
    #     'default': 'default_replacement_name'  # optional fallback
    # }
    'oricorio': {
        'greninja': 'oricorio-pom-pom',
        'default': 'oricorio-pom-pom'  # fallback if no specific pairing found
    },
    'lycanroc': {
        'rampardos': 'lycanroc-midnight',
        'default': 'lycanroc-midnight'  # fallback
    },
    'alolan-raichu': {
        'default': 'raichu-alola'  # fallback
    },
    'paldean-clodsire': {
        'default': 'clodsire'  # fallback
    },
    'alolan-dugtrio': {
        'default': 'dugtrio-alola'  # fallback
    },
    'dusk-mane-necrozma': {
        'default': 'necrozma-dusk-mane'  # fallback
    },
    'ultra-necrozma': {
        'default': 'necrozma-ultra'  # fallback
    },
    # Add more exceptions as needed
    # 'rotom': {
    #     'pikachu': 'rotom-wash',
    #     'charizard': 'rotom-heat',
    #     'default': 'rotom-wash'
    # }
}

# Pokemon suffixes to filter out
POKEMON_URL_SUFFIXES = ['ex', 'v', 'vmax', 'vstar', 'gx']

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
    'left': 0.08,
    'top': 0.115,
    'right': 0.92,
    'bottom': 0.47
}

IMAGE_GRADIENT = {
    'top_height': 0.02,
    'bottom_height': 0.02
}

# Category thresholds
CATEGORY_BINS = [-1, 25, 79, 100]
CATEGORY_LABELS = ['Tech', 'Standard', 'Core']

# Flexible core thresholds
FLEXIBLE_CORE_THRESHOLD = 25

# Pokemon name patterns for multi-word recognition
POKEMON_NAME_PATTERNS = {
    # Regional prefixes that create multi-word Pokemon
    'REGIONAL_PREFIXES': ['alolan', 'galarian', 'hisuian', 'paldean'],
    
    # Single-word form prefixes
    'FORM_PREFIXES': ['mega', 'primal', 'ultra'],
    
    # Multi-word form prefixes
    'MULTI_WORD_FORM_PREFIXES': ['origin-forme', 'white-striped',  'dawn-wings', 'dusk-mane'],
    
    # Paradox prefixes (future Pokemon start with "iron-")
    'PARADOX_PREFIXES': ['iron'],
    
    # Special multi-word base names that don't follow standard patterns
    'SPECIAL_MULTIWORD': {
        # Tapu series
        'tapu-koko', 'tapu-lele', 'tapu-bulu', 'tapu-fini',
        
        # Ancient Paradox Pokemon
        'great-tusk', 'scream-tail', 'brute-bonnet', 'flutter-mane',
        'slither-wing', 'sandy-shocks', 'roaring-moon', 'walking-wake',
        'gouging-fire', 'raging-bolt',
        
        # Classic multi-word Pokemon
        'mr-mime', 'mime-jr', 'type-null', 'ho-oh',
        'nidoran-m', 'nidoran-f', 'porygon-z',
        
        # Gen 7 dragons
        'jangmo-o', 'hakamo-o', 'kommo-o',
        
        # Gen 9 legends
        'wo-chien', 'chien-pao', 'ting-lu', 'chi-yu',
        'koraidon', 'miraidon',
        
        # ADD THESE MISSING NECROZMA FORMS:
        'dusk-mane-necrozma',
        'dawn-wings-necrozma',
        'ultra-necrozma',
        
        # ADD THESE MISSING KYUREM FORMS:
        'black-kyurem',
        'white-kyurem',
        
        # ADD OTHER POTENTIAL MULTI-WORD POKEMON:
        'shadow-lugia',      # If it exists
        'primal-dialga',     # If different from prefix-based detection
        'origin-forme-dialga',
        'origin-forme-palkia',
        'origin-forme-giratina',
        'therian-forme-tornadus',
        'therian-forme-thundurus',
        'therian-forme-landorus',
    },
    
    # Pokemon suffixes
    'POKEMON_SUFFIXES': ['ex', 'v', 'vmax', 'vstar', 'gx', 'sp']
}
# Text for sidebar
# POWER_INDEX_EXPLANATION = """
# #### Power Index: How We Rank the Best Decks

# **Data Source and Limitations**  
# The Power Index uses recent tournament data from [Limitless TCG](https://play.limitlesstcg.com/tournaments/completed), specifically the most recent {tournament_count} tournaments. This provides a rolling window of competitive results that adapts as the metagame evolves. Note that this data only includes reported "Best Finish" results, which may represent a subset of all matches played.

# **Formula and Methodology**  
# The Power Index is calculated as:

# Power Index = (Wins - Losses) / √(Wins + Losses)

# This formula balances three critical factors:
# * Win-loss differential (raw performance)
# * Sample size (statistical confidence)
# * Recent metagame context (using latest tournament data)

# **Advantages Over Alternative Metrics**
# * **More robust than Win Rate**: Differentiates between decks with small sample sizes and those with proven consistency
# * **More dynamic than Popularity**: Measures actual competitive performance rather than just prevalence in the meta
# * **More normalized than Raw Record**: A 20-5 record and a 40-10 record would have different win rates but similar Power Index values, properly accounting for confidence

# **Interpretation Guide**
# * **Positive values**: Indicate winning records (higher values = stronger performance)
# * **Negative values**: Indicate losing records (generally filtered from top displays)
# * **Magnitude**: Values typically range from -3 to +3, with top-tier decks usually above 1.0

# **Important Caveats**
# * The metric is sensitive to metagame shifts and tournament representation
# * Limited by the quantity of available tournament data
# * Best used as one factor in deck selection alongside matchup analysis and personal play style considerations
# """

POWER_INDEX_EXPLANATION = """
#### Power Index: Statistical Ranking of Meta Decks

**Data Source and Methodology**  
The Power Index analyzes performance data from the {tournament_count} most recent tournaments on Limitless TCG, using a statistical approach called the Wilson Score Interval.

**Technical Formula**
Lower bound of 95% confidence interval for win rate, where:

p = (wins + 0.5*ties)/(total games)

z = 1.96 (95% confidence level)

Power Index = [(p + z²/(2n) - z√(p(1-p)/n + z²/(4n²)))/(1 + z²/n) - 0.5] * 10

**Statistical Foundations**
* Uses confidence interval statistics rather than simple ratios
* Properly accounts for variable sample sizes
* Conservatively estimates true win rate with 95% confidence
* Scaled to intuitive -5 to +5 range for easier interpretation

**Technical Advantages**
* **Statistical validity**: Based on well-established binomial confidence intervals
* **Sample size robustness**: Automatically adjusts confidence based on number of games
* **Small sample protection**: Prevents decks with few games from dominating rankings
* **Tie handling**: Properly incorporates ties as half-wins

**Interpretation Guide**
* **Positive values**: Indicate decks performing above 50% win rate with statistical confidence
* **Negative values**: Indicate underperforming decks (below 50% win rate)
* **Magnitude**: Values of +2 or higher generally represent strong meta contenders

**Technical Limitations**
* Based on {tournament_count} recent tournaments (rolling window)
* Cannot account for evolving strategies and counter-play between tournaments
* Focuses on past performance rather than theoretical potential
"""
