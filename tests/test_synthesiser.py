from src.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.synthesiser import _format_editorial_insights, _format_advertiser_research


def test_system_prompt_not_empty():
    assert len(SYSTEM_PROMPT) > 100


def test_system_prompt_has_key_sections():
    assert "Advertiser Overview" in SYSTEM_PROMPT
    assert "Strategic Alignment" in SYSTEM_PROMPT
    assert "Editorial Insights" in SYSTEM_PROMPT


def test_user_prompt_template_has_placeholders():
    assert "{topic}" in USER_PROMPT_TEMPLATE
    assert "{advertiser}" in USER_PROMPT_TEMPLATE
    assert "{editorial_insights}" in USER_PROMPT_TEMPLATE
    assert "{advertiser_research}" in USER_PROMPT_TEMPLATE
    assert "{audience_timing}" in USER_PROMPT_TEMPLATE
    assert "{google_trends}" in USER_PROMPT_TEMPLATE


def test_user_prompt_renders():
    rendered = USER_PROMPT_TEMPLATE.format(
        topic="test topic",
        advertiser="test brand",
        editorial_insights="some insights",
        advertiser_research="some research",
        audience_timing="some timing",
        google_trends="some trends",
    )
    assert "test topic" in rendered
    assert "test brand" in rendered


def test_format_editorial_insights_empty():
    results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    text, sources = _format_editorial_insights(results)
    assert "No editorial insights" in text
    assert sources == []


def test_format_editorial_insights_with_data():
    results = {
        "documents": [["Some editorial content about wellness."]],
        "metadatas": [[{
            "editor_name": "Test Editor",
            "publication": "Test Pub",
            "date": "2025-01-01",
            "vertical": "Health",
            "topics": "wellness, health",
        }]],
        "distances": [[0.5]],
    }
    text, sources = _format_editorial_insights(results)
    assert "Test Editor" in text
    assert "Test Pub" in text
    assert len(sources) == 1
    assert sources[0]["editor"] == "Test Editor"


def test_format_advertiser_research():
    skill_results = [
        {
            "skill_name": "Company Overview",
            "raw_results": [{"title": "Test", "body": "Test body"}],
            "processed_summary": "Test company does testing.",
            "error": None,
        },
        {
            "skill_name": "Recent News",
            "raw_results": [],
            "processed_summary": "No results found.",
            "error": None,
        },
    ]
    formatted = _format_advertiser_research(skill_results)
    assert "Company Overview" in formatted
    assert "Recent News" in formatted
    assert "Test company does testing." in formatted


def test_format_advertiser_research_empty():
    formatted = _format_advertiser_research([])
    assert "No advertiser research available" in formatted
