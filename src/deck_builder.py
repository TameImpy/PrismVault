"""
Deck builder module. Populates a branded PowerPoint template with structured
slide content and returns the finished .pptx as a BytesIO buffer.
"""
import io
import os

from pptx import Presentation
from pptx.util import Pt, Emu, Inches
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

from src.font_embed import embed_fonts
from src.slide_content import build_audience_slide_content

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "templates", "prism_plan_template.pptx"
)

# Brand colours
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xC0, 0xC0, 0xC0)
CYAN_ACCENT = RGBColor(0x1F, 0x89, 0xDF)


def build_deck(slide_content, topic, advertiser):
    """Build a branded PowerPoint deck from structured slide content.

    Args:
        slide_content: dict from generate_slide_content() with all slide fields.
        topic: The editorial topic.
        advertiser: The advertiser name.

    Returns:
        io.BytesIO containing the finished .pptx file.
    """
    prs = Presentation(TEMPLATE_PATH)

    _fix_autofit(prs)

    _populate_title_slide(prs.slides[0], topic, advertiser, slide_content)
    _populate_stats_slide(prs.slides[1], slide_content)
    _populate_two_column_slide(prs.slides[2], slide_content)
    _populate_body_slide(prs.slides[3], slide_content)
    _populate_closing_slide(prs.slides[4], slide_content)

    # Deterministic "Recommended Audiences" slide (PRD #96 / slice #100). Built
    # from the audience_segments payload — reach is placed verbatim, never via
    # the LLM. Skipped entirely when no segments matched.
    audience = build_audience_slide_content(slide_content.get("audience_segments"))
    if audience["matched"]:
        _add_audience_slide(prs, audience)
        # Slide out with the CTA: move the new (last) slide before the closing one.
        _move_slide(prs, len(prs.slides._sldIdLst) - 1, len(prs.slides._sldIdLst) - 2)

    buf = io.BytesIO()
    prs.save(buf)
    # Embed Barlow so the deck renders on-brand on a machine without it installed.
    return embed_fonts(buf)


def _move_slide(prs, from_index, to_index):
    """Reorder slides by moving the sldId element within the slide id list."""
    sldIdLst = prs.slides._sldIdLst
    slides = list(sldIdLst)
    element = slides[from_index]
    sldIdLst.remove(element)
    sldIdLst.insert(to_index, element)


def _add_text_lines(slide, left, top, width, height, lines):
    """Add a textbox whose paragraphs are `lines` — one (text, font, size,
    colour, bold) tuple per visual line. Each line is its own <a:p> with a
    single run, so no literal newline ever reaches an <a:t> (PowerPoint-safe).
    """
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, (text, font_name, size, colour, bold) in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = para.add_run()
        run.text = text
        _apply_font(run, font_name, size, colour, bold)
    return box


def _add_audience_slide(prs, audience):
    """Append a "Recommended Audiences" slide built from the deterministic payload."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank — inherits dark master bg

    _add_text_lines(
        slide, Inches(0.55), Inches(0.30), Inches(9.0), Inches(0.7),
        [("Recommended Audiences", "Barlow ExtraBold", Pt(32), WHITE, True)],
    )
    _add_text_lines(
        slide, Inches(0.55), Inches(1.02), Inches(9.0), Inches(0.4),
        [("Reach is per segment — never summed; segments overlap and are not de-duplicated.",
          "Barlow", Pt(10), CYAN_ACCENT, False)],
    )

    # Two platform columns.
    col_width = Inches(4.25)
    col_lefts = [Inches(0.55), Inches(4.9)]
    for col, platform in enumerate(audience["platforms"][:2]):
        left = col_lefts[col]
        _add_text_lines(
            slide, left, Inches(1.55), col_width, Inches(0.6),
            [
                (platform["platform"], "Barlow ExtraBold", Pt(15), WHITE, True),
                (platform["framing"], "Barlow", Pt(9), LIGHT_GREY, False),
            ],
        )
        row_top = 2.25
        for seg in platform["segments"]:
            icon = seg.get("icon_path")
            if icon and os.path.exists(icon):
                slide.shapes.add_picture(icon, left, Inches(row_top), height=Inches(0.34))
            _add_text_lines(
                slide, left + Inches(0.5), Inches(row_top - 0.04), col_width - Inches(0.5), Inches(0.6),
                [
                    (seg["why"], "Barlow Medium", Pt(11), WHITE, False),
                    ("Reach: %s" % seg["reach"], "Barlow", Pt(9), CYAN_ACCENT, False),
                ],
            )
            row_top += 0.62


def _fix_autofit(prs):
    """Remove conflicting autofit elements from the template.

    The template has both <a:spAutoFit/> and <a:normAutofit fontScale="62500"/>
    inside every <a:bodyPr>. The OOXML spec requires at most one autofit child.
    PowerPoint tolerates this in an unmodified template but flags it as corrupt
    once python-pptx re-serialises the file with modified content.
    We keep normAutofit (shrink text to fit) and remove spAutoFit.
    """
    from pptx.oxml.ns import qn

    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            bodyPr = shape.text_frame._txBody.find(qn("a:bodyPr"))
            if bodyPr is None:
                continue
            sp_auto = bodyPr.find(qn("a:spAutoFit"))
            norm_auto = bodyPr.find(qn("a:normAutofit"))
            if sp_auto is not None and norm_auto is not None:
                bodyPr.remove(sp_auto)


def _apply_font(run, font_name=None, font_size=None, font_color=None, bold=None):
    """Apply font formatting to a run."""
    if font_name:
        run.font.name = font_name
    if font_size:
        run.font.size = font_size
    if font_color:
        run.font.color.rgb = font_color
    if bold is not None:
        run.font.bold = bold


def _set_text(shape, text, font_name=None, font_size=None, font_color=None, bold=None):
    """Replace all text in a shape's text frame.

    Handles newlines by creating proper OOXML paragraph elements instead of
    embedding literal '\\n' in a single run, which PowerPoint treats as corrupt.
    """
    from copy import deepcopy
    from pptx.oxml.ns import qn

    tf = shape.text_frame
    txBody = tf._txBody

    # Capture the first paragraph element as a formatting template
    first_para_elem = txBody.findall(qn("a:p"))[0]

    # Remove all existing paragraphs
    for p in txBody.findall(qn("a:p")):
        txBody.remove(p)

    # Split on newlines and create one <a:p> per line
    lines = text.split("\n")
    for line in lines:
        new_p = deepcopy(first_para_elem)
        # Remove all runs and breaks from the copied paragraph
        for child in new_p.findall(qn("a:r")):
            new_p.remove(child)
        for child in new_p.findall(qn("a:br")):
            new_p.remove(child)
        if line:
            # Add a single run with the line text
            from lxml import etree
            r_elem = etree.SubElement(new_p, qn("a:r"))
            t_elem = etree.SubElement(r_elem, qn("a:t"))
            t_elem.text = line
            t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        # Empty lines become empty paragraphs (visual spacing) — no run needed
        txBody.append(new_p)

    # Apply font formatting to all runs
    for para in tf.paragraphs:
        for run in para.runs:
            _apply_font(run, font_name, font_size, font_color, bold)


def _get_text_shapes(slide):
    """Return all shapes with text frames, ordered by position (top, left)."""
    shapes = [s for s in slide.shapes if s.has_text_frame]
    shapes.sort(key=lambda s: (s.top, s.left))
    return shapes


def _populate_title_slide(slide, topic, advertiser, content):
    """Slide 1: Topic, advertiser, KPI."""
    text_shapes = _get_text_shapes(slide)
    # Find and replace placeholder text
    for shape in text_shapes:
        text = shape.text_frame.text
        if "[TOPIC]" in text:
            _set_text(shape, topic, font_name="Barlow ExtraBold", font_size=Pt(50), font_color=WHITE)
        elif "[ADVERTISER]" in text:
            _set_text(shape, advertiser, font_name="Barlow Medium", font_size=Pt(16), font_color=LIGHT_GREY)
        elif "[KPI]" in text:
            _set_text(shape, "KPI: %s" % content.get("kpi", ""), font_name="Barlow", font_size=Pt(14), font_color=CYAN_ACCENT)


def _populate_stats_slide(slide, content):
    """Slide 2: At a Glance — 6 stat value/label pairs."""
    text_shapes = _get_text_shapes(slide)
    stats = content.get("stats", [])

    # Find value and label placeholders (alternating [VALUE]/[LABEL])
    value_shapes = [s for s in text_shapes if "[VALUE]" in s.text_frame.text]
    label_shapes = [s for s in text_shapes if "[LABEL]" in s.text_frame.text]

    for i, stat in enumerate(stats[:6]):
        if i < len(value_shapes):
            _set_text(value_shapes[i], stat["value"],
                      font_name="Barlow ExtraBold", font_size=Pt(40), font_color=WHITE)
        if i < len(label_shapes):
            _set_text(label_shapes[i], stat["label"],
                      font_name="Barlow", font_size=Pt(11), font_color=LIGHT_GREY)


def _format_bullets(items):
    """Format a list of strings as bullet text."""
    return "\n".join("  %s" % item for item in items)


def _populate_two_column_slide(slide, content):
    """Slide 3: Two-column — Advertiser Overview + Editorial Insights."""
    text_shapes = _get_text_shapes(slide)

    for shape in text_shapes:
        text = shape.text_frame.text
        if "Advertiser Overview" in text:
            _set_text(shape, content.get("left_heading", "Advertiser Overview"),
                      font_name="Barlow ExtraBold", font_size=Pt(22), font_color=WHITE)
        elif "[LEFT_BODY]" in text:
            bullets = content.get("left_bullets", [])
            _set_text(shape, _format_bullets(bullets),
                      font_name="Barlow", font_size=Pt(14), font_color=LIGHT_GREY)
        elif "Editorial Insights" in text:
            _set_text(shape, content.get("right_heading", "Editorial Insights"),
                      font_name="Barlow ExtraBold", font_size=Pt(22), font_color=WHITE)
        elif "[RIGHT_BODY]" in text:
            bullets = content.get("right_bullets", [])
            _set_text(shape, _format_bullets(bullets),
                      font_name="Barlow", font_size=Pt(14), font_color=LIGHT_GREY)


def _populate_body_slide(slide, content):
    """Slide 4: Messaging & Tone Recommendations."""
    text_shapes = _get_text_shapes(slide)

    for shape in text_shapes:
        text = shape.text_frame.text
        if "Messaging" in text:
            _set_text(shape, content.get("messaging_heading", "Messaging & Tone"),
                      font_name="Barlow ExtraBold", font_size=Pt(32), font_color=WHITE)
        elif "[BODY]" in text:
            items = content.get("messaging_items", [])
            lines = []
            for item in items:
                lines.append("%s — %s" % (item["headline"], item["detail"]))
            _set_text(shape, "\n\n".join(lines),
                      font_name="Barlow", font_size=Pt(14), font_color=LIGHT_GREY)


def _populate_closing_slide(slide, content):
    """Slide 5: Recommended Products + CTA."""
    text_shapes = _get_text_shapes(slide)

    for shape in text_shapes:
        text = shape.text_frame.text
        if "Recommended" in text:
            _set_text(shape, "Recommended Products",
                      font_name="Barlow ExtraBold", font_size=Pt(32), font_color=WHITE)
        elif "[PRODUCTS]" in text:
            products = content.get("products", [])
            lines = []
            for prod in products:
                lines.append("%s  |  %s" % (prod["name"], prod["metric"]))
            _set_text(shape, "\n\n".join(lines),
                      font_name="Barlow", font_size=Pt(14), font_color=LIGHT_GREY)
        elif "[CTA]" in text:
            _set_text(shape, content.get("cta", ""),
                      font_name="Barlow Medium", font_size=Pt(14), font_color=CYAN_ACCENT)
