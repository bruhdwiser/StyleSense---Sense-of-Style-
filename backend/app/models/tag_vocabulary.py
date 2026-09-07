"""StyleSense AI — Controlled Tag Vocabulary.

Defines the controlled taxonomy for aesthetics, colors, silhouettes, fits, seasons, and occasions
as specified in static_implementation.md Section 3.3.
"""

from typing import Set, Dict, List

AESTHETICS: Set[str] = {
    "minimalist",
    "streetwear",
    "formal",
    "casual",
    "bohemian",
    "athleisure",
    "ethnic",
}

COLORS: Set[str] = {
    "black",
    "white",
    "navy",
    "grey",
    "beige",
    "brown",
    "red",
    "blue",
    "green",
    "pink",
    "purple",
}

SILHOUETTES: Set[str] = {
    "slim",
    "regular",
    "relaxed",
    "oversized",
    "fitted",
}

FITS: Set[str] = {
    "slim_fit",
    "regular_fit",
    "relaxed_fit",
    "loose_fit",
}

SEASONS: Set[str] = {
    "summer",
    "winter",
    "monsoon",
    "spring",
    "fall",
}

OCCASIONS: Set[str] = {
    "casual",
    "formal",
    "party",
    "sports",
    "ethnic",
    "workwear",
}

ALL_VOCABULARY_TAGS: Set[str] = (
    AESTHETICS | COLORS | SILHOUETTES | FITS | SEASONS | OCCASIONS
)

COLOR_SYNONYMS: Dict[str, str] = {
    "navy blue": "navy",
    "blue": "blue",
    "black": "black",
    "white": "white",
    "grey": "grey",
    "gray": "grey",
    "silver": "grey",
    "charcoal": "grey",
    "beige": "beige",
    "cream": "beige",
    "khaki": "beige",
    "tan": "beige",
    "brown": "brown",
    "coffee": "brown",
    "maroon": "red",
    "red": "red",
    "burgundy": "red",
    "rust": "red",
    "green": "green",
    "olive": "green",
    "teal": "green",
    "pink": "pink",
    "rose": "pink",
    "magenta": "pink",
    "purple": "purple",
    "lavender": "purple",
    "violet": "purple",
    "yellow": "beige",
    "orange": "brown",
    "gold": "beige",
    "multi": "casual",
}

SEASON_SYNONYMS: Dict[str, str] = {
    "summer": "summer",
    "winter": "winter",
    "fall": "fall",
    "autumn": "fall",
    "spring": "spring",
    "monsoon": "monsoon",
}

USAGE_SYNONYMS: Dict[str, str] = {
    "casual": "casual",
    "formal": "formal",
    "party": "party",
    "sports": "sports",
    "ethnic": "ethnic",
    "smart casual": "workwear",
    "travel": "casual",
}
