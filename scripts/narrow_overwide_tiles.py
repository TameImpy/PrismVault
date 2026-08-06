"""One-off template edit: narrow the tile text boxes to their columns (#162).

Reported as "some exported slides have text overlapping". The cause is
geometry, not content. Several marker boxes in the official template are drawn
wider than the column they belong to — `[INSIGHT_2_STAT]` is a 5.34" box at
x=4.88" on a 10" slide, so it extends 0.22" past the right edge — and every box
is `spAutoFit`. PowerPoint wraps text at the *box* width and grows the shape
downward, so a value long enough to use the box's full width is drawn across
the neighbouring tile, or over the Prism logo. No amount of shortening the text
fixes that: on slide 5 the only string guaranteed to stay inside tile 1 with
the box as drawn is about four words long, which would gut the insight tiles.

So the boxes are narrowed to the column each tile actually occupies. Nothing
else changes: no font, size, colour, position or anchoring is touched, and the
text is left-aligned and top-anchored, so for every value short enough to fit
today the rendering is byte-for-byte what it was. The edit only bites where
text used to spill.

There is deliberately no table of widths here. Each box is set to exactly the
width its tile is budgeted in `src.tile_fit.TILE_BUDGETS`, plus that shape's own
insets — so the number the renderer wraps at and the number the fitter measures
against are one number, not two kept in step by hand.

The budgets themselves are the columns, read off the template: the gap to the
next tile on the right, to the slide edge, or to the logo artwork. Markers whose
box already matches their budget — the 2.62" name and format labels, the title,
the overview — are left untouched, so running this is a no-op for them.

Idempotent: the widths are absolute, so re-running after a template revision
re-applies them rather than shrinking anything twice.

    python3 scripts/narrow_overwide_tiles.py
"""
import os
import sys

from pptx import Presentation
from pptx.util import Inches

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.deck_builder import TEMPLATE_PATH  # noqa: E402
from src.tile_fit import MARKER_RE, budget_for, inches, text_inset  # noqa: E402


def narrow(path=TEMPLATE_PATH):
    prs = Presentation(path)
    changed = []

    for index, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            markers = MARKER_RE.findall(shape.text_frame.text)
            if not markers:
                continue
            tile = budget_for(markers[0])
            if tile is None:
                continue
            target = (tile.width
                      + text_inset(shape, "lIns") + text_inset(shape, "rIns"))
            was = shape.width
            # The budgets are round numbers by choice, so a box already at its
            # budget sits a few thousandths of an inch off it. Rewriting over
            # that would churn slides this edit has no business touching — and
            # the boxes that genuinely need narrowing are out by 0.15" or more,
            # so a hundredth of an inch separates the two cleanly.
            if abs(Inches(target) - was) <= Inches(0.01):
                continue
            shape.width = Inches(target)
            changed.append("slide %d  %-20s %-12s %.2f\" -> %.2f\""
                           % (index, markers[0], shape.name,
                              inches(was), target))

    prs.save(path)
    return changed


if __name__ == "__main__":
    for line in narrow():
        print(line)
    print("template written: %s" % os.path.relpath(TEMPLATE_PATH, PROJECT_ROOT))
