from src.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.synthesiser import _format_editorial_insights, _format_advertiser_research


def test_system_prompt_not_empty():
    assert len(SYSTEM_PROMPT) > 100


def test_system_prompt_has_key_sections():
    assert "Advertiser Overview" in SYSTEM_PROMPT
    assert "Strategic Alignment" in SYSTEM_PROMPT
    assert "Editorial Insights" in SYSTEM_PROMPT


def test_system_prompt_messaging_section_references_kpi():
    """The Messaging & Tone section should instruct the model to tailor recommendations to the KPI."""
    # Find the Messaging & Tone section and check it mentions KPI
    messaging_start = SYSTEM_PROMPT.index("Messaging & Tone")
    messaging_section = SYSTEM_PROMPT[messaging_start:]
    assert "KPI" in messaging_section


def test_user_prompt_template_has_placeholders():
    assert "{topic}" in USER_PROMPT_TEMPLATE
    assert "{advertiser}" in USER_PROMPT_TEMPLATE
    assert "{editorial_insights}" in USER_PROMPT_TEMPLATE
    assert "{advertiser_research}" in USER_PROMPT_TEMPLATE
    assert "{audience_timing}" in USER_PROMPT_TEMPLATE
    assert "{google_trends}" in USER_PROMPT_TEMPLATE
    assert "{advertiser_kpi}" in USER_PROMPT_TEMPLATE


def test_user_prompt_renders():
    rendered = USER_PROMPT_TEMPLATE.format(
        topic="test topic",
        advertiser="test brand",
        advertiser_kpi="Awareness",
        editorial_insights="some insights",
        advertiser_research="some research",
        audience_timing="some timing",
        google_trends="some trends",
    )
    assert "test topic" in rendered
    assert "test brand" in rendered
    assert "Awareness" in rendered


def test_generate_insights_accepts_kpi_and_injects_into_prompt():
    """generate_insights() should accept a kpi parameter and include it in the prompt sent to GPT-4o."""
    from unittest.mock import patch, MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test brief content"

    with patch("src.synthesiser.search_transcripts") as mock_search, \
         patch("src.synthesiser.research_advertiser", return_value=[]), \
         patch("src.synthesiser.load_audience_data") as mock_load, \
         patch("src.synthesiser.get_topic_trends", return_value="No data"), \
         patch("src.synthesiser.OpenAI") as mock_openai_cls:

        mock_search.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        mock_load.return_value = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        from src.synthesiser import generate_insights
        generate_insights(topic="test", advertiser="TestCo", kpi="Clicks", include_google_trends=False)

        call_args = mock_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        assert "Clicks" in user_prompt


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
