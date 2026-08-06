"""
Tile fitter for the deck (#162).

The template's text boxes are all `spAutoFit` — "resize shape to fit text".
python-pptx writes the text and leaves the stored height alone, so the shape
only grows when PowerPoint lays the slide out on open. A value longer than its
placeholder therefore looks fine in the file and lands on the tile below it on
screen. That is what "some exported slides have text overlapping" was.

So each marker gets a **tile budget**: the width its text may occupy and the
number of lines it may grow to before it reaches its neighbour. Values are
measured in the template's own Barlow weights and shortened to fit before they
are written.

`TILE_BUDGETS` is a reading of the template, not a set of preferences —
`tests/test_tile_fit.py` re-derives every entry against the file: the typeface
and point size must be the template's own, no two full tiles may overlap, and
none may reach the slide edge or the logo artwork. A template revision that
moves a box fails there rather than shipping a client-facing collision.

Widths are narrower than the boxes they sit in, deliberately. Several boxes in
the template are drawn wider than the column they belong to — `[INSIGHT_2_STAT]`
extends 0.22" past the right edge of the slide — so the box width is not a
usable bound. The budget is the column: the distance to whatever sits to the
right of the tile.

This module is also where the deck's font measurement lives, kept out of
`deck_builder` so that module stays free of type metrics (the template is the
single source of truth for styling; reading it is not the same as setting it).
"""
import os
import re
from collections import namedtuple

from fontTools.ttLib import TTFont

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "fonts")

# The weights the template uses, as its runs name them (see src/font_embed.py).
FONT_FILES = {
    "Barlow": "Barlow-Regular.ttf",
    "Barlow ExtraBold": "Barlow-ExtraBold.ttf",
    "Barlow ExtraLight": "Barlow-ExtraLight.ttf",
}
FALLBACK_FONT = "Barlow"

ELLIPSIS = "…"

# width: inches of text the tile may occupy. lines: how far it may grow.
Tile = namedtuple("Tile", "width lines typeface size")

# Markers are keyed by family — [SEGMENT_1_NAME] and [SEGMENT_4_NAME] share one
# budget, so three tiles that look identical break identically.
TILE_BUDGETS = {
    # Slide 0, title. The box holds two lines at 50pt and nothing sits below it.
    "[ADVERTISER_NAME]": Tile(7.90, 2, "Barlow ExtraBold", 50.0),

    # Slide 2, advertiser overview. A full-width block with the rest of the
    # slide beneath it; six lines is 1.4" of the 3.71" available.
    "[ADVERTISER_OVERVIEW]": Tile(8.43, 6, "Barlow", 14.0),

    # Slide 3, product tiles. The figures are one line by nature; the format
    # name is the only one that runs long, and two lines holds every name in
    # data/format_recommendations.csv.
    "[PRODUCT_N_CTR]": Tile(4.60, 1, "Barlow ExtraBold", 40.0),
    "[PRODUCT_N_VIEW]": Tile(4.60, 1, "Barlow ExtraLight", 26.0),
    "[PRODUCT_N_FORMAT]": Tile(2.42, 2, "Barlow", 11.0),

    # Slide 4, segment tiles. Segment names run to 95 characters in
    # data/segments.csv; the 0.82" between the name and the row beneath it
    # takes four 11pt lines, which holds the longest of them whole.
    "[SEGMENT_N_REACH]": Tile(4.60, 1, "Barlow ExtraBold", 36.0),
    "[SEGMENT_N_NAME]": Tile(2.42, 4, "Barlow", 11.0),

    # Slide 5, insight tiles. Two lines for the supporting phrase: tile 1 has
    # 0.89" of room before tile 3's figure. The width clears the Prism logo,
    # which sits under tile 3.
    "[INSIGHT_N]": Tile(4.33, 1, "Barlow ExtraBold", 40.0),
    "[INSIGHT_N_STAT]": Tile(3.54, 2, "Barlow ExtraLight", 26.0),
}

# The appendix is one flowing block of paragraphs rather than a tile, so it is
# measured whole (test_the_real_registry_fits_on_the_appendix_slide) instead of
# line by line. Truncating a source line would defeat what #156 added it for.
EXEMPT_MARKERS = frozenset(["[PROVENANCE_N]"])

_INDEX_RE = re.compile(r"_\d+")
_metrics_cache = {}


def budget_for(marker):
    """The tile budget for a marker, or None if it has none."""
    return TILE_BUDGETS.get(_family(marker))


def _family(marker):
    return _INDEX_RE.sub("_N", marker)


def fit_to_tile(marker, text):
    """Shorten `text` until it fits `marker`'s tile, marking any cut with "…".

    Markers with no budget pass through, but every value is still collapsed to
    one line first: markers sit in single-line placeholders, and a literal
    newline inside an <a:t> element is what PowerPoint reads as a corrupt file.
    """
    text = " ".join(str(text or "").split())
    tile = budget_for(marker)
    if tile is None or not text or _fits(text, tile):
        return text

    # Drop whole words from the end first — a name cut mid-word reads as a
    # rendering fault rather than a deliberate shortening.
    words = text.split()
    for count in range(len(words) - 1, 0, -1):
        candidate = " ".join(words[:count]) + ELLIPSIS
        if _fits(candidate, tile):
            return candidate

    # One unbreakable word longer than the tile: cut it mid-word rather than
    # let it overflow.
    for count in range(len(text) - 1, 0, -1):
        candidate = text[:count] + ELLIPSIS
        if _fits(candidate, tile):
            return candidate
    return ELLIPSIS


def _fits(text, tile):
    return len(rendered_lines(text, tile.width, tile.typeface, tile.size)) <= tile.lines


def rendered_lines(text, width, typeface, size):
    """Wrap `text` the way PowerPoint would: greedy, on word boundaries.

    A word wider than the tile on its own still takes its own line — matching
    the renderer, which overflows rather than hyphenating. `fit_to_tile` is what
    stops that reaching the file.
    """
    lines, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if current and text_width(trial, typeface, size) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines or [""]


def text_width(text, typeface, size):
    """Width of `text` in inches, from the real Barlow advance widths."""
    advances, _, fallback = _metrics(typeface)
    ems = sum(advances.get(char, fallback) for char in text)
    return ems * size / 72.0


def line_height(typeface, size):
    """Height of one line in inches, from the font's own vertical metrics."""
    _, line_ems, _ = _metrics(typeface)
    return line_ems * size / 72.0


def _metrics(typeface):
    """(advance width per character, line height in ems, fallback advance).

    Read once per weight and cached — a deck build measures thousands of
    characters and the files are on disk beside the ones we embed.
    """
    filename = FONT_FILES.get(typeface, FONT_FILES[FALLBACK_FONT])
    if filename in _metrics_cache:
        return _metrics_cache[filename]

    font = TTFont(os.path.join(FONTS_DIR, filename))
    upem = float(font["head"].unitsPerEm)
    hmtx = font["hmtx"]
    advances = {chr(code): hmtx[glyph][0] / upem
                for code, glyph in font.getBestCmap().items()
                if glyph in hmtx.metrics}
    hhea = font["hhea"]
    line_ems = (hhea.ascender - hhea.descender + hhea.lineGap) / upem
    # An unmapped character renders as .notdef, which is the em box's own width.
    fallback = advances.get("W", 0.7)

    _metrics_cache[filename] = (advances, line_ems, fallback)
    return _metrics_cache[filename]
