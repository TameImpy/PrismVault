import logging

from src.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.synthesiser import (
    _format_editorial_insights,
    _format_advertiser_research,
    _run_format_name_guardrail,
)


def test_system_prompt_not_empty():
    assert len(SYSTEM_PROMPT) > 100


def test_system_prompt_has_key_sections():
    assert "Advertiser Overview" in SYSTEM_PROMPT
    assert "Strategic Alignment" in SYSTEM_PROMPT
    # Editorial Insights section removed while editorial vector search is
    # disabled (Phase 2).
    assert "Editorial Insights" not in SYSTEM_PROMPT


def test_system_prompt_has_key_recommendations_section():
    """SYSTEM_PROMPT should contain a Key Recommendations output section."""
    assert "Key Recommendations" in SYSTEM_PROMPT


def test_prompt_swaps_audience_timing_for_segments_and_reach():
    """The dummy 'Audience Timing' section is replaced by 'Audience Segments & Reach'."""
    assert "Audience Segments & Reach" in SYSTEM_PROMPT
    assert "Audience Timing" not in SYSTEM_PROMPT
    # The user template exposes an {audience_segments} placeholder, not {audience_timing}.
    assert "{audience_segments}" in USER_PROMPT_TEMPLATE
    assert "{audience_timing}" not in USER_PROMPT_TEMPLATE
    # The model is instructed to quote reach verbatim and never sum.
    assert "verbatim" in SYSTEM_PROMPT.lower()


def test_system_prompt_key_recommendations_is_first_section():
    """Key Recommendations should appear before Advertiser Overview in SYSTEM_PROMPT."""
    recs_pos = SYSTEM_PROMPT.index("Key Recommendations")
    overview_pos = SYSTEM_PROMPT.index("Advertiser Overview")
    assert recs_pos < overview_pos


def test_system_prompt_key_recommendations_instructs_concise_numbered_list():
    """Key Recommendations section should instruct the model to produce numbered, concise recommendations."""
    recs_start = SYSTEM_PROMPT.index("Key Recommendations")
    overview_start = SYSTEM_PROMPT.index("Advertiser Overview")
    recs_section = SYSTEM_PROMPT[recs_start:overview_start]
    assert "concise" in recs_section.lower()
    assert "number" in recs_section.lower()


def test_system_prompt_has_at_a_glance_section():
    """SYSTEM_PROMPT should contain an At a Glance output section."""
    assert "At a Glance" in SYSTEM_PROMPT


def test_system_prompt_at_a_glance_is_before_key_recommendations():
    """At a Glance should appear before Key Recommendations in SYSTEM_PROMPT."""
    glance_pos = SYSTEM_PROMPT.index("At a Glance")
    recs_pos = SYSTEM_PROMPT.index("Key Recommendations")
    assert glance_pos < recs_pos


def test_system_prompt_at_a_glance_has_fixed_labels():
    """At a Glance section should reference all fixed labels (Editor Voice
    removed while editorial vector search is disabled — Phase 2)."""
    glance_start = SYSTEM_PROMPT.index("At a Glance")
    key_recs_start = SYSTEM_PROMPT.index("Key Recommendations")
    glance_section = SYSTEM_PROMPT[glance_start:key_recs_start]
    assert "Core Products" in glance_section
    assert "Latest News" in glance_section
    assert "Messaging" in glance_section
    assert "Tone" in glance_section
    assert "Editor Voice" not in glance_section
    assert "Top Format" in glance_section


def test_system_prompt_has_client_relationship_section():
    """SYSTEM_PROMPT should contain a Client Relationship section (scoped to
    "direct" campaigns) after Advertiser Overview and before Strategic Alignment."""
    assert "Client Relationship" in SYSTEM_PROMPT
    history_pos = SYSTEM_PROMPT.index("Client Relationship")
    overview_pos = SYSTEM_PROMPT.index("Advertiser Overview")
    alignment_pos = SYSTEM_PROMPT.index("Strategic Alignment")
    assert overview_pos < history_pos < alignment_pos
    # Wording is scoped to "direct" and never an absolute no-relationship claim.
    assert "direct" in SYSTEM_PROMPT[history_pos:alignment_pos].lower()


def test_system_prompt_has_client_brief_instruction():
    """SYSTEM_PROMPT should instruct GPT-4o to tailor sections to the client brief."""
    assert "client brief" in SYSTEM_PROMPT.lower()


def test_system_prompt_has_recommended_products_section():
    """SYSTEM_PROMPT should contain a Recommended Products output section."""
    assert "Recommended Products" in SYSTEM_PROMPT


def test_system_prompt_recommended_products_position():
    """Recommended Products should appear after Audience Segments & Reach and before Messaging & Tone."""
    recs_pos = SYSTEM_PROMPT.index("Recommended Products")
    audience_pos = SYSTEM_PROMPT.index("Audience Segments & Reach")
    messaging_pos = SYSTEM_PROMPT.index("Messaging & Tone")
    assert audience_pos < recs_pos < messaging_pos


def test_system_prompt_recommended_products_has_kpi_mapping():
    """Recommended Products section should contain KPI-to-objective mapping."""
    recs_start = SYSTEM_PROMPT.index("Recommended Products")
    messaging_start = SYSTEM_PROMPT.index("Messaging & Tone")
    recs_section = SYSTEM_PROMPT[recs_start:messaging_start]
    assert "Awareness" in recs_section
    assert "Clicks" in recs_section or "CTR" in recs_section
    assert "Viewability" in recs_section


def _recommended_products_section():
    """Slice out the Recommended Products section of SYSTEM_PROMPT."""
    start = SYSTEM_PROMPT.index("Recommended Products")
    end = SYSTEM_PROMPT.index("Messaging & Tone")
    return SYSTEM_PROMPT[start:end]


def test_recommended_products_instructs_single_combined_rationale():
    """The section must end with one combined, brief-aware rationale tying the
    chosen formats to the specific advertiser and KPI (not per-format prose)."""
    section = _recommended_products_section().lower()
    assert "combined rationale" in section
    assert "advertiser" in section
    assert "kpi" in section


def test_recommended_products_uses_missing_benchmark_wording():
    """Formats without benchmarks must render the plain-English note, not N/A."""
    section = _recommended_products_section()
    assert "benchmarks not currently available for this specific format" in section


def test_recommended_products_does_not_surface_indicative_cost():
    """Indicative cost is model context only — the prompt must instruct the
    model not to surface it (rather than listing it as a per-format field)."""
    section = _recommended_products_section().lower().replace("*", "")
    # The only permitted mention of cost is a prohibition on showing it.
    assert "do not show indicative cost" in section


def test_recommended_products_requires_exact_catalogue_names():
    """The model must use exact catalogue names only (no renamed/invented formats)."""
    section = _recommended_products_section().lower()
    assert "exact" in section
    assert "catalogue" in section or "catalog" in section


def test_recommended_products_per_format_fields():
    """Each recommendation shows name, CTR average, viewability, and primary objective."""
    section = _recommended_products_section().lower()
    assert "ctr" in section
    assert "viewability" in section
    assert "primary objective" in section


def test_recommended_products_bounds_three_to_five():
    """Aim for 5, floor of 3, no padding with weak fits."""
    section = _recommended_products_section()
    assert "3" in section and "5" in section


def test_system_prompt_messaging_section_references_kpi():
    """The Messaging & Tone section should instruct the model to tailor recommendations to the KPI."""
    # Find the Messaging & Tone section and check it mentions KPI
    messaging_start = SYSTEM_PROMPT.index("Messaging & Tone")
    messaging_section = SYSTEM_PROMPT[messaging_start:]
    assert "KPI" in messaging_section


def test_user_prompt_template_has_placeholders():
    assert "{topic}" in USER_PROMPT_TEMPLATE
    assert "{advertiser}" in USER_PROMPT_TEMPLATE
    # {editorial_insights} placeholder removed while editorial is disabled.
    assert "{editorial_insights}" not in USER_PROMPT_TEMPLATE
    assert "{advertiser_research}" in USER_PROMPT_TEMPLATE
    assert "{audience_segments}" in USER_PROMPT_TEMPLATE
    assert "{google_trends}" in USER_PROMPT_TEMPLATE
    assert "{advertiser_kpi}" in USER_PROMPT_TEMPLATE
    assert "{format_recommendations}" in USER_PROMPT_TEMPLATE
    assert "{campaign_history}" in USER_PROMPT_TEMPLATE
    assert "{client_brief}" in USER_PROMPT_TEMPLATE


def test_user_prompt_renders():
    rendered = USER_PROMPT_TEMPLATE.format(
        topic="test topic",
        advertiser="test brand",
        advertiser_kpi="Awareness",
        advertiser_research="some research",
        audience_segments="some segments",
        google_trends="some trends",
        format_recommendations="some formats",
        campaign_history="some history",
        client_brief="some brief",
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

    sample_payload = {
        "matched": True,
        "note": "Reach figures are per-segment and must not be summed.",
        "query_terms": ["baking"],
        "platforms": [
            {"platform": "AP", "framing": "Modelled first-party audience — broad reach",
             "segments": [{"segment_name": "Home Baking Intenders", "reach": 5000000,
                           "platform": "AP", "category": "Food & Drink",
                           "plain_english": "Buy baking ingredients", "description": "",
                           "code": "ap_x 1", "frequency": "", "window": ""}]},
            {"platform": "Permutive", "framing": "Behavioural — recently engaged browsers",
             "segments": []},
        ],
    }

    with patch("src.synthesiser.research_advertiser", return_value=[]), \
         patch("src.synthesiser.expand_query", return_value={"keywords": ["baking"], "categories": []}), \
         patch("src.synthesiser.recommend_segments", return_value=sample_payload), \
         patch("src.synthesiser.get_campaign_summary", return_value={"summary": "No previous campaign data found for this advertiser.", "campaigns": []}), \
         patch("src.synthesiser.OpenAI") as mock_openai_cls:

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        from src.synthesiser import generate_insights
        result = generate_insights(topic="test", advertiser="TestCo", kpi="Clicks", include_google_trends=False)

        call_args = mock_client.chat.completions.create.call_args
        user_prompt = call_args[1]["messages"][1]["content"]
        assert "Clicks" in user_prompt
        assert "campaign_history" in result
        # New: the deterministic audience_segments payload is returned and the
        # dummy audience_timing string is gone.
        assert result["audience_segments"] == sample_payload
        assert "audience_timing" not in result
        # The formatted segment text (with verbatim reach) reached the prompt.
        assert "Home Baking Intenders" in user_prompt


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


def test_guardrail_logs_unrecognised_format_names(caplog):
    """The guardrail flags and logs hallucinated/off-catalogue format names."""
    content = (
        "## Recommended Products\n"
        "- **Totally Fake Format 9000** — CTR average 5.00%, Primary objective: Awareness\n"
    )
    with caplog.at_level(logging.WARNING):
        result = _run_format_name_guardrail(content)

    assert "Totally Fake Format 9000" in result["unrecognised"]
    assert "Totally Fake Format 9000" in caplog.text


def test_guardrail_nonblocking_and_silent_for_valid_names(caplog):
    """Recognised names produce no warning and the guardrail never raises."""
    content = (
        "## Recommended Products\n"
        "- **Host Read** — benchmarks not currently available for this specific format\n"
    )
    with caplog.at_level(logging.WARNING):
        result = _run_format_name_guardrail(content)

    assert result["unrecognised"] == []
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


# ---------------------------------------------------------------------------
# _run_format_name_guardrail — edge cases (#94)
# ---------------------------------------------------------------------------

def test_guardrail_empty_content_returns_empty_results_and_no_warning(caplog):
    """An empty string must not crash the guardrail and must produce no warning."""
    with caplog.at_level(logging.WARNING):
        result = _run_format_name_guardrail("")

    assert result == {"recognised": [], "unrecognised": []}
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_guardrail_none_content_returns_empty_results_and_no_warning(caplog):
    """None as content must be coerced safely via 'content or \"\"' and must
    not crash or emit a warning."""
    with caplog.at_level(logging.WARNING):
        result = _run_format_name_guardrail(None)

    assert result == {"recognised": [], "unrecognised": []}
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_guardrail_returns_safe_fallback_if_load_format_names_raises(caplog):
    """If load_format_names raises unexpectedly the guardrail must catch the
    exception, log at ERROR level, and return the empty safe-fallback dict
    rather than propagating the error."""
    from unittest.mock import patch

    with patch("src.synthesiser.load_format_names", side_effect=RuntimeError("CSV gone")):
        with caplog.at_level(logging.ERROR):
            result = _run_format_name_guardrail("- **Some Format** — CTR 1.00%")

    assert result == {"recognised": [], "unrecognised": []}
    # The guardrail must have logged the exception at ERROR/CRITICAL level.
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records, "Expected at least one ERROR-level log from the guardrail exception handler"


def test_guardrail_warning_names_the_module_logger(caplog):
    """The WARNING must be emitted by the synthesiser module logger, not the
    root logger or an unexpected name. This pins the logger.warning() call
    to src.synthesiser so log-routing configuration works correctly in prod."""
    content = (
        "## Recommended Products\n"
        "- **Fictional Ad Unit** — CTR average 9.99%\n"
    )
    with caplog.at_level(logging.WARNING, logger="src.synthesiser"):
        result = _run_format_name_guardrail(content)

    warning_records = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "src.synthesiser"
    ]
    assert warning_records, "Expected a WARNING from the src.synthesiser logger"
    assert "Fictional Ad Unit" in result["unrecognised"]
