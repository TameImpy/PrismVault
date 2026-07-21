"""Deterministic segment -> icon resolution for the deck (PRD #96 / slice #100).

Every recommended segment resolves to a real, bundled PNG icon:

    keyword override  ->  icon_key (from the expansion call)  ->  category  ->  default

The bundled PNGs live in data/segment_icons/ and are open-licensed Noto Emoji
(Apache-2.0) — see data/segment_icons/LICENSE. `ICON_CODEPOINTS` is the single
source of truth for which icons exist; scripts/fetch_segment_icons.py downloads
exactly this set, and the resolver below can only ever return one of these
names, so the fallback is never missing.
"""
import os
import re

ICON_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "segment_icons")

DEFAULT_ICON = "default"

# icon name -> Noto Emoji codepoint (hex, as used in the PNG filename
# emoji_u<codepoint>.png). This set is what gets bundled.
ICON_CODEPOINTS = {
    "food-drink": "1f37d",          # fork and knife with plate
    "baking": "1f35e",              # bread
    "wine": "1f377",                # wine glass
    "coffee": "2615",               # hot beverage
    "beer": "1f37a",                # beer mug
    "arts-entertainment": "1f3ad",  # performing arts
    "auto": "1f697",                # car
    "gaming": "1f3ae",              # video game
    "sports": "26bd",               # soccer ball
    "fitness": "1f4aa",             # flexed biceps
    "interest": "2b50",             # star
    "gardening": "1f331",           # seedling
    "parenting": "1f476",           # baby
    "christmas": "1f384",           # christmas tree
    "gifting": "1f381",             # wrapped gift
    "retail": "1f6cd",              # shopping bags
    "travel": "2708",               # airplane
    "finance": "1f4b7",             # banknote with pound
    "insurance": "1f6e1",           # shield
    "energy": "26a1",               # high voltage
    "broadband": "1f4f6",           # antenna bars
    "tech": "1f4bb",                # laptop
    "device": "1f4f1",              # mobile phone
    "home": "1f3e0",                # house
    "diy": "1f528",                 # hammer
    "beauty": "1f484",              # lipstick
    "fashion": "1f457",             # dress
    "health": "1f489",              # syringe
    "pet-owner": "1f43e",           # paw prints
    "commuters": "1f687",           # metro
    "geo": "1f4cd",                 # round pushpin
    "news": "1f4f0",                # newspaper
    "demographics": "1f465",        # busts in silhouette
    "default": "1f3af",             # direct hit / bullseye
}

# Segment icon_key / category slug -> bundled icon name. Slugs match the
# icon_key column produced by scripts/build_segments.py (lower-kebab category).
CATEGORY_ICONS = {
    "food-drink": "food-drink",
    "food-drinks": "food-drink",
    "food-and-drink": "food-drink",
    "arts-entertainment": "arts-entertainment",
    "arts-entertainments": "arts-entertainment",
    "auto": "auto",
    "gaming": "gaming",
    "sports": "sports",
    "fitness": "fitness",
    "interest": "interest",
    "interests": "interest",
    "gardening": "gardening",
    "parenting": "parenting",
    "christmas": "christmas",
    "seasonal": "gifting",
    "gifting": "gifting",
    "retail": "retail",
    "purchase-intenders": "retail",
    "travel": "travel",
    "holiday-intenders": "travel",
    "commuters": "commuters",
    "finance": "finance",
    "insurance": "insurance",
    "energy": "energy",
    "broadband": "broadband",
    "internet-service-provider": "broadband",
    "isp": "broadband",
    "tech": "tech",
    "technology": "tech",
    "device": "device",
    "home": "home",
    "home-renovation": "diy",
    "diy": "diy",
    "beauty": "beauty",
    "beauty-cosmetics": "beauty",
    "fashion": "fashion",
    "fashion-beauty": "beauty",
    "health": "health",
    "pet-owner": "pet-owner",
    "news": "news",
    "geo-targeting": "geo",
    "geo": "geo",
    "location": "geo",
    "demographics-employment": "demographics",
    "demographics-children": "demographics",
    "demographics-custom": "demographics",
    "demographic-custom": "demographics",
    "employment": "demographics",
    "lifestage": "demographics",
}

# Keyword (matched against segment name + category tokens) -> bundled icon name.
# Overrides the category mapping for extra polish.
KEYWORD_ICONS = {
    "baking": "baking",
    "bake": "baking",
    "bakers": "baking",
    "bread": "baking",
    "cake": "baking",
    "wine": "wine",
    "coffee": "coffee",
    "cafe": "coffee",
    "beer": "beer",
    "lager": "beer",
    "car": "auto",
    "vehicle": "auto",
    "garden": "gardening",
    "flower": "gardening",
    "pet": "pet-owner",
    "dog": "pet-owner",
    "cat": "pet-owner",
    "football": "sports",
    "fitness": "fitness",
    "gym": "fitness",
    "travel": "travel",
    "holiday": "travel",
    "flight": "travel",
    "gaming": "gaming",
    "beauty": "beauty",
    "makeup": "beauty",
}


def _slug(text):
    """Lower-kebab slug, matching build_segments' icon_key convention."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower())
    return slug.strip("-")


def _tokens(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def icon_name_for(category=None, segment_name="", icon_key=None):
    # type: (...) -> str
    """Resolve a segment to a bundled icon name (keyword > icon_key > category > default)."""
    # 1. Keyword override on the segment name + category tokens.
    for token in _tokens("%s %s" % (segment_name, category or "")):
        if token in KEYWORD_ICONS:
            return KEYWORD_ICONS[token]

    # 2. Explicit icon_key from the expansion call, if it is a bundled icon.
    if icon_key:
        key = _slug(icon_key)
        if key in ICON_CODEPOINTS:
            return key
        if key in CATEGORY_ICONS:
            return CATEGORY_ICONS[key]

    # 3. Category slug.
    cat_slug = _slug(category)
    if cat_slug in CATEGORY_ICONS:
        return CATEGORY_ICONS[cat_slug]

    # 4. Guaranteed fallback.
    return DEFAULT_ICON


def icon_path(category=None, segment_name="", icon_key=None):
    # type: (...) -> str
    """Absolute path to the segment's bundled PNG; falls back to default if missing."""
    name = icon_name_for(category=category, segment_name=segment_name, icon_key=icon_key)
    path = os.path.join(ICON_DIR, "%s.png" % name)
    if not os.path.exists(path):
        path = os.path.join(ICON_DIR, "%s.png" % DEFAULT_ICON)
    return path
