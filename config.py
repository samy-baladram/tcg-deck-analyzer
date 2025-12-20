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
MIN_META_SHARE = 0.01  # Minimum meta share percentage to display
MIN_WIN_RATE = 35 # Minimum win rate share percentage to display

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
    'dusk-mane-necrozma': {
        'default': 'necrozma-dusk-mane'  # fallback
    },
    'ultra-necrozma': {
        'default': 'necrozma-ultra'  # fallback
    },
    
    # Alolan forms (18 total)
    'alolan-rattata': {
        'default': 'rattata-alola'
    },
    'alolan-raticate': {
        'default': 'raticate-alola'
    },
    'alolan-raichu': {
        'default': 'raichu-alola'
    },
    'alolan-sandshrew': {
        'default': 'sandshrew-alola'
    },
    'alolan-sandslash': {
        'default': 'sandslash-alola'
    },
    'alolan-vulpix': {
        'default': 'vulpix-alola'
    },
    'alolan-ninetales': {
        'default': 'ninetales-alola'
    },
    'alolan-diglett': {
        'default': 'diglett-alola'
    },
    'alolan-dugtrio': {
        'default': 'dugtrio-alola'
    },
    'alolan-meowth': {
        'default': 'meowth-alola'
    },
    'alolan-persian': {
        'default': 'persian-alola'
    },
    'alolan-geodude': {
        'default': 'geodude-alola'
    },
    'alolan-graveler': {
        'default': 'graveler-alola'
    },
    'alolan-golem': {
        'default': 'golem-alola'
    },
    'alolan-grimer': {
        'default': 'grimer-alola'
    },
    'alolan-muk': {
        'default': 'muk-alola'
    },
    'alolan-exeggutor': {
        'default': 'exeggutor-alola'
    },
    'alolan-marowak': {
        'default': 'marowak-alola'
    },
    
    # Galarian forms (19 total)
    'galarian-meowth': {
        'default': 'meowth-galar'
    },
    'galarian-persian': {
        'default': 'persian-galar'  # Note: Perrserker is the evolution, not Persian
    },
    'galarian-ponyta': {
        'default': 'ponyta-galar'
    },
    'galarian-rapidash': {
        'default': 'rapidash-galar'
    },
    'galarian-slowpoke': {
        'default': 'slowpoke-galar'
    },
    'galarian-slowbro': {
        'default': 'slowbro-galar'
    },
    'galarian-slowking': {
        'default': 'slowking-galar'
    },
    'galarian-farfetchd': {
        'default': 'farfetchd-galar'
    },
    'galarian-weezing': {
        'default': 'weezing-galar'
    },
    'galarian-mr-mime': {
        'default': 'mr-mime-galar'
    },
    'galarian-articuno': {
        'default': 'articuno-galar'
    },
    'galarian-zapdos': {
        'default': 'zapdos-galar'
    },
    'galarian-moltres': {
        'default': 'moltres-galar'
    },
    'galarian-corsola': {
        'default': 'corsola-galar'
    },
    'galarian-zigzagoon': {
        'default': 'zigzagoon-galar'
    },
    'galarian-linoone': {
        'default': 'linoone-galar'
    },
    'galarian-darumaka': {
        'default': 'darumaka-galar'
    },
    'galarian-darmanitan': {
        'default': 'darmanitan-galar'
    },
    'galarian-yamask': {
        'default': 'yamask-galar'
    },
    'galarian-stunfisk': {
        'default': 'stunfisk-galar'
    },
    'galarian-cursola': {
        'default': 'cursola'  # Cursola only has Galarian form, no original
    },
    
    # Hisuian forms (17 total)
    'hisuian-growlithe': {
        'default': 'growlithe-hisui'
    },
    'hisuian-arcanine': {
        'default': 'arcanine-hisui'
    },
    'hisuian-voltorb': {
        'default': 'voltorb-hisui'
    },
    'hisuian-electrode': {
        'default': 'electrode-hisui'
    },
    'hisuian-typhlosion': {
        'default': 'typhlosion-hisui'
    },
    'hisuian-qwilfish': {
        'default': 'qwilfish-hisui'
    },
    'hisuian-sneasel': {
        'default': 'sneasel-hisui'
    },
    'hisuian-samurott': {
        'default': 'samurott-hisui'
    },
    'hisuian-lilligant': {
        'default': 'lilligant-hisui'
    },
    'hisuian-zorua': {
        'default': 'zorua-hisui'
    },
    'hisuian-zoroark': {
        'default': 'zoroark-hisui'
    },
    'hisuian-braviary': {
        'default': 'braviary-hisui'
    },
    'hisuian-sliggoo': {
        'default': 'sliggoo-hisui'
    },
    'hisuian-goodra': {
        'default': 'goodra-hisui'
    },
    'hisuian-avalugg': {
        'default': 'avalugg-hisui'
    },
    'hisuian-decidueye': {
        'default': 'decidueye-hisui'
    },
    'hisuian-basculin': {
        'default': 'basculin-white-striped'  # White-Striped form
    },
    
    # Paldean forms (4 total - Wooper + 3 Tauros variants)
    'paldean-wooper': {
        'default': 'wooper-paldea'
    },
    'paldean-clodsire': {
        'default': 'clodsire'  # Clodsire only exists as Paldean evolution
    },
    'paldean-tauros': {
        'default': 'tauros-paldea-combat'  # Default to Combat Breed
    },
    'paldean-tauros-combat': {
        'default': 'tauros-paldea-combat'
    },
    'paldean-tauros-blaze': {
        'default': 'tauros-paldea-blaze'
    },
    'paldean-tauros-aqua': {
        'default': 'tauros-paldea-aqua'
    },
    
    # Mega Evolution forms (48 forms total - includes X/Y variants)
    'mega-venusaur': {
        'default': 'venusaur-mega'
    },
    'mega-charizard-x': {
        'default': 'charizard-mega-x'
    },
    'mega-charizard-y': {
        'default': 'charizard-mega-y'
    },
    'mega-blastoise': {
        'default': 'blastoise-mega'
    },
    'mega-beedrill': {
        'default': 'beedrill-mega'
    },
    'mega-pidgeot': {
        'default': 'pidgeot-mega'
    },
    'mega-alakazam': {
        'default': 'alakazam-mega'
    },
    'mega-slowbro': {
        'default': 'slowbro-mega'
    },
    'mega-gengar': {
        'default': 'gengar-mega'
    },
    'mega-kangaskhan': {
        'default': 'kangaskhan-mega'
    },
    'mega-pinsir': {
        'default': 'pinsir-mega'
    },
    'mega-gyarados': {
        'default': 'gyarados-mega'
    },
    'mega-aerodactyl': {
        'default': 'aerodactyl-mega'
    },
    'mega-mewtwo-x': {
        'default': 'mewtwo-mega-x'
    },
    'mega-mewtwo-y': {
        'default': 'mewtwo-mega-y'
    },
    'mega-ampharos': {
        'default': 'ampharos-mega'
    },
    'mega-steelix': {
        'default': 'steelix-mega'
    },
    'mega-scizor': {
        'default': 'scizor-mega'
    },
    'mega-heracross': {
        'default': 'heracross-mega'
    },
    'mega-houndoom': {
        'default': 'houndoom-mega'
    },
    'mega-tyranitar': {
        'default': 'tyranitar-mega'
    },
    'mega-sceptile': {
        'default': 'sceptile-mega'
    },
    'mega-blaziken': {
        'default': 'blaziken-mega'
    },
    'mega-swampert': {
        'default': 'swampert-mega'
    },
    'mega-gardevoir': {
        'default': 'gardevoir-mega'
    },
    'mega-mawile': {
        'default': 'mawile-mega'
    },
    'mega-aggron': {
        'default': 'aggron-mega'
    },
    'mega-medicham': {
        'default': 'medicham-mega'
    },
    'mega-manectric': {
        'default': 'manectric-mega'
    },
    'mega-sharpedo': {
        'default': 'sharpedo-mega'
    },
    'mega-camerupt': {
        'default': 'camerupt-mega'
    },
    'mega-altaria': {
        'default': 'altaria-mega'
    },
    'mega-banette': {
        'default': 'banette-mega'
    },
    'mega-absol': {
        'default': 'absol-mega'
    },
    'mega-glalie': {
        'default': 'glalie-mega'
    },
    'mega-salamence': {
        'default': 'salamence-mega'
    },
    'mega-metagross': {
        'default': 'metagross-mega'
    },
    'mega-latias': {
        'default': 'latias-mega'
    },
    'mega-latios': {
        'default': 'latios-mega'
    },
    'mega-rayquaza': {
        'default': 'rayquaza-mega'
    },
    'mega-lopunny': {
        'default': 'lopunny-mega'
    },
    'mega-garchomp': {
        'default': 'garchomp-mega'
    },
    'mega-lucario': {
        'default': 'lucario-mega'
    },
    'mega-abomasnow': {
        'default': 'abomasnow-mega'
    },
    'mega-gallade': {
        'default': 'gallade-mega'
    },
    'mega-audino': {
        'default': 'audino-mega'
    },
    'mega-diancie': {
        'default': 'diancie-mega'
    },
    'mega-sableye': {
        'default': 'sableye-mega'
    },
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
# IMAGE_CROP_BOX = {
#     'left': 0.08,
#     'top': 0.115,
#     'right': 0.92,
#     'bottom': 0.47
# }
IMAGE_CROP_BOX = {
    'left': 0.04,
    'top': 0.084,
    'right': 0.96,
    'bottom': 0.51
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
    'POKEMON_SUFFIXES': ['ex', 'v', 'vmax', 'vstar', 'gx', 'sp'],

    # NEW: Variant suffixes (form variants like X/Y, forms, etc.)
    'VARIANT_SUFFIXES': ['x', 'y', 'origin', 'altered', 'attack', 'defense', 'speed', 'heat', 'wash', 'frost', 'fan', 'mow', 'sky', 'land', 'therian', 'incarnate'],
 
    'SPECIAL_CASING': {
        'ho-oh-ex': 'Ho-Oh ex',
        'porygon-z': 'Porygon-Z',
        'porygon-z': 'Porygon Z',
        # Add other Pokemon with special casing needs here
        # Examples:
        # 'porygon-z-ex': 'Porygon-Z ex',
        # 'type-null-ex': 'Type: Null ex',
    }
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
