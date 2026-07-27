"""
Font embedder. Injects the Barlow brand weights into a .pptx so the deck renders
in the template's own typefaces on a machine that doesn't have them installed.

PowerPoint stores an embedded font as a `.fntdata` part holding the raw TrueType
bytes, referenced from a `<p:embeddedFontLst>` in presentation.xml. python-pptx
has no notion of font parts, so this module works on the saved package: it takes
.pptx bytes and returns .pptx bytes with the font parts, the embedded-font list,
the relationships and the content-type entry all added.

Each Barlow weight is a separate font *family* internally (family names
"Barlow", "Barlow ExtraBold", "Barlow ExtraLight" — matching the typeface
strings in the template), so each occupies the regular slot of its own entry
rather than the bold/italic slots of one shared family.
"""
import io
import os
import posixpath
import zipfile
from collections import namedtuple

from lxml import etree

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "fonts")

FONT_CONTENT_TYPE = "application/x-fontdata"
FONT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
PR_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

PRESENTATION_PART = "ppt/presentation.xml"
PRESENTATION_RELS_PART = "ppt/_rels/presentation.xml.rels"
CONTENT_TYPES_PART = "[Content_Types].xml"

# Elements that CT_Presentation orders *after* embeddedFontLst. The list must be
# inserted before the first of these, or PowerPoint rejects the file.
_AFTER_EMBEDDED_FONT_LST = (
    "custShowLst", "photoAlbum", "custDataLst", "kinsoku",
    "defaultTextStyle", "modifyVerifier", "extLst",
)

# Swiss (sans-serif), variable pitch, ANSI charset — what PowerPoint records for Barlow.
_PITCH_FAMILY = "34"
_CHARSET = "0"

EmbeddedFont = namedtuple("EmbeddedFont", "typeface filename")

# The weights the official template uses (PRD #131). `typeface` must equal the
# font's internal family name *and* the template's typeface string.
BARLOW_FONTS = (
    EmbeddedFont("Barlow", "Barlow-Regular.ttf"),
    EmbeddedFont("Barlow ExtraBold", "Barlow-ExtraBold.ttf"),
    EmbeddedFont("Barlow ExtraLight", "Barlow-ExtraLight.ttf"),
)


def embed_fonts(pptx_file, fonts=BARLOW_FONTS):
    """Embed `fonts` into a .pptx package.

    Args:
        pptx_file: the source .pptx as bytes or a readable binary buffer.
        fonts: EmbeddedFont specs, resolved against FONTS_DIR.

    Returns:
        io.BytesIO containing the .pptx with the fonts embedded. Idempotent —
        re-embedding replaces any fonts a previous call added.

    Raises:
        FileNotFoundError: a font file is missing from FONTS_DIR.
    """
    blobs = [_read_font(font.filename) for font in fonts]

    source = _as_bytes(pptx_file)
    with zipfile.ZipFile(io.BytesIO(source)) as zf:
        parts = [(item.filename, zf.read(item.filename)) for item in zf.infolist()]

    parts = [(name, blob) for name, blob in parts if not name.endswith(".fntdata")]
    part_names = ["ppt/fonts/font%d.fntdata" % (i + 1) for i in range(len(fonts))]

    rel_ids = _rewrite(parts, PRESENTATION_RELS_PART, _relationships, part_names)
    _rewrite(parts, PRESENTATION_PART, _presentation, fonts, rel_ids)
    _rewrite(parts, CONTENT_TYPES_PART, _content_types)

    parts.extend(zip(part_names, blobs))
    return _repackage(parts)


def _read_font(filename):
    path = os.path.join(FONTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError("Font file not found for embedding: %s" % path)
    with open(path, "rb") as f:
        return f.read()


def _as_bytes(pptx_file):
    if isinstance(pptx_file, bytes):
        return pptx_file
    pptx_file.seek(0)
    return pptx_file.read()


def _rewrite(parts, part_name, transform, *args):
    """Apply `transform` to the XML of `part_name` in place, returning its result."""
    for i, (name, blob) in enumerate(parts):
        if name != part_name:
            continue
        root = etree.fromstring(blob)
        result = transform(root, *args)
        parts[i] = (name, etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True))
        return result
    raise KeyError("Not a .pptx package — missing %s" % part_name)


def _relationships(root, part_names):
    """Point presentation.xml at the font parts; return the new rIds in order."""
    used = set()
    for rel in root.findall("{%s}Relationship" % PR_NS):
        if rel.get("Type") == FONT_REL_TYPE:
            root.remove(rel)
        else:
            used.add(rel.get("Id"))

    rel_ids = []
    next_id = 1
    for part_name in part_names:
        while "rId%d" % next_id in used:
            next_id += 1
        rel_id = "rId%d" % next_id
        used.add(rel_id)
        rel_ids.append(rel_id)
        etree.SubElement(root, "{%s}Relationship" % PR_NS, {
            "Id": rel_id,
            "Type": FONT_REL_TYPE,
            "Target": posixpath.relpath(part_name, posixpath.dirname(PRESENTATION_PART)),
        })
    return rel_ids


def _presentation(root, fonts, rel_ids):
    """Set the embed flag and rebuild the embedded-font list."""
    root.set("embedTrueTypeFonts", "1")
    # We embed complete fonts, not the subset PowerPoint would save — so a
    # recipient without Barlow installed can still edit the deck.
    root.set("saveSubsetFonts", "0")

    for existing in root.findall("{%s}embeddedFontLst" % P_NS):
        root.remove(existing)

    lst = etree.Element("{%s}embeddedFontLst" % P_NS)
    for font, rel_id in zip(fonts, rel_ids):
        entry = etree.SubElement(lst, "{%s}embeddedFont" % P_NS)
        etree.SubElement(entry, "{%s}font" % P_NS, {
            "typeface": font.typeface,
            "pitchFamily": _PITCH_FAMILY,
            "charset": _CHARSET,
        })
        etree.SubElement(entry, "{%s}regular" % P_NS, {"{%s}id" % R_NS: rel_id})

    root.insert(_schema_position(root), lst)


def _schema_position(root):
    """Index for embeddedFontLst that keeps CT_Presentation's element order."""
    for i, child in enumerate(root):
        if etree.QName(child).localname in _AFTER_EMBEDDED_FONT_LST:
            return i
    return len(root)


def _content_types(root):
    """Declare the fntdata extension, the way PowerPoint does."""
    for default in root.findall("{%s}Default" % CT_NS):
        if default.get("Extension", "").lower() == "fntdata":
            return
    etree.SubElement(root, "{%s}Default" % CT_NS, {
        "Extension": "fntdata",
        "ContentType": FONT_CONTENT_TYPE,
    })


def _repackage(parts):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, blob in parts:
            zf.writestr(name, blob)
    buf.seek(0)
    return buf
