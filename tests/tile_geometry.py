"""Slide geometry helpers shared by the deck tests (#162).

Both `test_tile_fit.py` (does each budget clear its neighbours?) and
`test_deck_builder.py` (does a built deck's text clear its neighbours?) ask the
same question of the same units, so the measuring lives here rather than twice.

Everything is in inches. python-pptx reports EMU, and 914,400 of them make an
inch — a number worth naming once.
"""
from src.tile_fit import inches, text_inset, wrapping_width


def text_origin(shape):
    """Where a shape's first line of text starts, inset included."""
    return (inches(shape.left) + text_inset(shape, "lIns"),
            inches(shape.top) + text_inset(shape, "tIns"))


def overlaps(a, b):
    """Do two (x0, y0, x1, y1) rects intersect? Touching does not count."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def artwork_rects(slide, slide_width):
    """The logo marks on a slide.

    The full-bleed background picture is not one — it covers every slide by
    design, and counting it would make every rect a collision.
    """
    return [(shape.name, (inches(shape.left), inches(shape.top),
                          inches(shape.left + shape.width),
                          inches(shape.top + shape.height)))
            for shape in slide.shapes
            if not shape.has_text_frame
            and inches(shape.width) < slide_width * 0.95]


def rendered_text_rect(shape):
    """Where a shape's text actually lands once the renderer has autofitted it.

    Rects, not boxes: a tile's box may be wider than the text in it, and the
    question #162 asks is whether the *drawn text* of two tiles collides.
    Returns None for a shape holding no text.
    """
    from src.tile_fit import line_height, rendered_lines, text_width

    left, top = text_origin(shape)
    width = wrapping_width(shape)

    bottom, widest = top, 0.0
    for para in shape.text_frame.paragraphs:
        run = next((r for r in para.runs if r.text.strip()), None)
        if run is None:
            continue
        typeface = run.font.name or "Barlow"
        size = run.font.size.pt if run.font.size else 14.0
        for line in rendered_lines(para.text, width, typeface, size):
            bottom += line_height(typeface, size)
            widest = max(widest, text_width(line, typeface, size))

    if widest == 0.0:
        return None
    return (left, top, left + widest, bottom)
