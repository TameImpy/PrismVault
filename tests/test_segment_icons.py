"""Tests for deterministic segment→icon resolution (PRD #96 / slice #100)."""
import os

from src import segment_icons


def test_category_maps_to_its_icon():
    assert segment_icons.icon_name_for(category="Food & Drink") == "food-drink"
    assert segment_icons.icon_name_for(category="Gardening") == "gardening"


def test_keyword_override_beats_category():
    # "Baking Fans" in Food & Drink should get the baking icon, not the generic
    # food-drink one — keyword overrides add polish.
    name = segment_icons.icon_name_for(category="Food & Drink", segment_name="Baking Fans")
    assert name == "baking"
    wine = segment_icons.icon_name_for(category="Food & Drink", segment_name="White Wine fans")
    assert wine == "wine"


def test_icon_key_used_when_category_unknown():
    # A messy/unmapped category falls back to the icon_key slug if that is bundled.
    name = segment_icons.icon_name_for(category="RiverStreet MPU Q1", icon_key="auto")
    assert name == "auto"


def test_unknown_everything_falls_back_to_default():
    name = segment_icons.icon_name_for(category="Totally Unknown Category")
    assert name == segment_icons.DEFAULT_ICON


def test_icon_path_always_resolves_to_an_existing_png():
    # The guarantee the deck relies on: every segment resolves to a real PNG.
    for category in ["Food & Drink", "Totally Unknown", "Gardening", "Auto"]:
        path = segment_icons.icon_path(category=category)
        assert path.endswith(".png")
        assert os.path.exists(path), "icon path must exist (fallback never missing): %s" % path


def test_every_mapped_icon_name_is_bundled():
    # Every name the resolver can return must have a codepoint (so the fetch
    # script downloads it) and, once fetched, a PNG on disk.
    names = set(segment_icons.CATEGORY_ICONS.values())
    names |= set(segment_icons.KEYWORD_ICONS.values())
    names.add(segment_icons.DEFAULT_ICON)
    for name in names:
        assert name in segment_icons.ICON_CODEPOINTS, "no codepoint for %r" % name
