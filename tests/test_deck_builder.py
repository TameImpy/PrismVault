"""
Tests for the deck builder at src/deck_builder.py.

No mocks — feeds in a known content dict and inspects the .pptx output.
"""
import sys
import os
import io

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from pptx import Presentation
from src.deck_builder import build_deck

SAMPLE_CONTENT = {
    "stats": [
        {"value": "40%", "label": "addressable audience"},
        {"value": "112", "label": "audience index"},
        {"value": "2.7x", "label": "frequency reach"},
        {"value": "Q3", "label": "peak quarter"},
        {"value": "85%", "label": "brand safe inventory"},
        {"value": "3.2m", "label": "monthly food audience"},
    ],
    "left_heading": "Advertiser Overview",
    "left_bullets": [
        "Leading probiotic brand in UK",
        "Targeting health-conscious ABC1s",
        "Recent gut-brain axis campaign",
    ],
    "right_heading": "Editorial Insights",
    "right_bullets": [
        "Growing reader interest in gut health",
        "Strong wellness editorial alignment",
        "Sponsored content opportunity",
    ],
    "messaging_heading": "Messaging & Tone",
    "messaging_items": [
        {"headline": "Lead with science", "detail": "Ground claims in clinical research"},
        {"headline": "Warm and approachable", "detail": "Avoid jargon, use everyday language"},
        {"headline": "Seasonal hooks", "detail": "January wellness, September routines"},
    ],
    "products": [
        {"name": "Infinity Skin", "metric": "CTR 0.42%, Viewability 78%"},
        {"name": "Playstream Video", "metric": "Viewability 91%"},
    ],
    "cta": "Let's book a call to discuss how these insights can shape your next campaign.",
}


def test_build_deck_returns_valid_pptx():
    """build_deck() returns a BytesIO buffer containing a valid 5-slide .pptx."""
    result = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")

    assert isinstance(result, io.BytesIO)
    # Parse the output to verify it's a valid pptx
    prs = Presentation(result)
    assert len(prs.slides) == 5


def test_title_slide_contains_topic_and_advertiser():
    """Slide 1 contains the topic and advertiser name."""
    result = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")
    prs = Presentation(result)
    slide = prs.slides[0]

    all_text = " ".join(
        shape.text_frame.text for shape in slide.shapes if shape.has_text_frame
    )
    assert "gut health" in all_text
    assert "Yakult" in all_text


def test_stats_slide_contains_values():
    """Slide 2 contains the stat values from the input."""
    result = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")
    prs = Presentation(result)
    slide = prs.slides[1]

    all_text = " ".join(
        shape.text_frame.text for shape in slide.shapes if shape.has_text_frame
    )
    assert "40%" in all_text
    assert "112" in all_text
    assert "3.2m" in all_text


def test_uses_barlow_fonts():
    """All text in the deck uses the Barlow font family."""
    result = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")
    prs = Presentation(result)

    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        if run.font.name:
                            assert run.font.name.startswith("Barlow"), \
                                "Expected Barlow font, got: %s" % run.font.name


def test_closing_slide_contains_cta():
    """Slide 5 contains the CTA text."""
    result = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")
    prs = Presentation(result)
    slide = prs.slides[4]

    all_text = " ".join(
        shape.text_frame.text for shape in slide.shapes if shape.has_text_frame
    )
    assert "book a call" in all_text


# ---------------------------------------------------------------------------
# Regression tests: newline handling in <a:t> XML elements
# ---------------------------------------------------------------------------

import zipfile
from lxml import etree

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_AT_TAG = "{%s}t" % _A_NS


def _all_at_texts(pptx_buf):
    """Return every string value held in an <a:t> element across all slides."""
    pptx_buf.seek(0)
    texts = []
    with zipfile.ZipFile(pptx_buf) as zf:
        slide_names = [n for n in zf.namelist() if n.startswith("ppt/slides/slide")]
        for name in slide_names:
            xml_bytes = zf.read(name)
            root = etree.fromstring(xml_bytes)
            for elem in root.iter(_AT_TAG):
                if elem.text:
                    texts.append(elem.text)
    pptx_buf.seek(0)
    return texts


def test_no_literal_newline_in_at_elements():
    """Regression: _set_text must never embed a literal '\\n' inside an <a:t> element.

    Slide 4 uses '\\n\\n'.join() for messaging items and slide 5 uses '\\n\\n'.join()
    for products — both are multi-line inputs that previously triggered the bug.
    Slide 3 uses '\\n'.join() for bullet lists. All must be clean.
    """
    result = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")
    at_texts = _all_at_texts(result)

    assert at_texts, "Expected at least one <a:t> element in the deck"

    for text in at_texts:
        assert "\n" not in text, (
            "Found a literal newline inside an <a:t> element — "
            "PowerPoint treats this as corrupt XML. Value: %r" % text
        )


def test_multiline_messaging_items_text_preserved_across_paragraphs():
    """Regression: multi-line messaging content must appear across separate paragraphs
    with no data loss — all headline/detail pairs must be findable in the slide text.
    """
    result = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")
    prs = Presentation(result)
    slide = prs.slides[3]  # Slide 4: Messaging & Tone

    # Gather text across all paragraphs in every shape on the slide
    all_para_texts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                all_para_texts.append(para.text)

    combined = "\n".join(all_para_texts)

    for item in SAMPLE_CONTENT["messaging_items"]:
        assert item["headline"] in combined, (
            "Headline %r missing from slide 4 text after newline fix" % item["headline"]
        )
        assert item["detail"] in combined, (
            "Detail %r missing from slide 4 text after newline fix" % item["detail"]
        )


def test_multiline_bullets_text_preserved_across_paragraphs():
    """Regression: bullet lists joined with '\\n' must produce one paragraph per bullet
    with no data loss — every bullet string must appear in slide 3's paragraph text.
    """
    result = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")
    prs = Presentation(result)
    slide = prs.slides[2]  # Slide 3: Two-column

    all_para_texts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                all_para_texts.append(para.text)

    combined = "\n".join(all_para_texts)

    for bullet in SAMPLE_CONTENT["left_bullets"] + SAMPLE_CONTENT["right_bullets"]:
        assert bullet in combined, (
            "Bullet %r missing from slide 3 text after newline fix" % bullet
        )


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.main import app
from api.database import init_db

API_TEST_DB = os.path.join(os.path.dirname(__file__), "test_deck_api.db")


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def api_client():
    import api.auth as auth_module
    import api.database as db_module
    import api.email_samples as samples_module

    if os.path.exists(API_TEST_DB):
        os.remove(API_TEST_DB)
    run(init_db(API_TEST_DB))

    old_auth = auth_module.DB_PATH
    old_db = db_module.DEFAULT_DB_PATH
    old_samples = samples_module.DB_PATH
    auth_module.DB_PATH = API_TEST_DB
    db_module.DEFAULT_DB_PATH = API_TEST_DB
    samples_module.DB_PATH = API_TEST_DB

    yield TestClient(app)

    auth_module.DB_PATH = old_auth
    db_module.DEFAULT_DB_PATH = old_db
    samples_module.DB_PATH = old_samples
    if os.path.exists(API_TEST_DB):
        os.remove(API_TEST_DB)


def test_api_download_deck_returns_401_without_auth(api_client):
    """POST /api/download-deck without auth returns 401."""
    resp = TestClient(app, cookies={}).post(
        "/api/download-deck",
        json={"content": "brief", "topic": "t", "advertiser": "a", "kpi": "k"},
    )
    assert resp.status_code == 401


@patch("api.main.generate_slide_content")
@patch("api.main.build_deck")
def test_api_download_deck_returns_pptx(mock_build, mock_gen, api_client):
    """POST /api/download-deck returns correct content type and filename."""
    mock_gen.return_value = SAMPLE_CONTENT
    # Return a minimal valid pptx
    buf = build_deck(SAMPLE_CONTENT, "gut health", "Yakult")
    mock_build.return_value = buf

    api_client.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "name": "Test", "password": "password123"},
    )
    resp = api_client.post(
        "/api/download-deck",
        json={"content": "brief", "topic": "gut health", "advertiser": "Yakult", "kpi": "Awareness"},
    )

    assert resp.status_code == 200
    assert "openxmlformats" in resp.headers["content-type"]
    assert "Prism_Plan_Yakult_gut_health.pptx" in resp.headers["content-disposition"]
