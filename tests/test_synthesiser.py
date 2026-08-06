import glob
import json
import logging
import os

from src.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.synthesiser import (
    _format_editorial_insights,
    _format_advertiser_research,
    _run_format_name_guardrail,
)

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


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
    # {google_trends} went with the feature (#176) — the template must not ask
    # the synthesiser for a value it no longer computes.
    assert "{google_trends}" not in USER_PROMPT_TEMPLATE
    assert "{advertiser_kpi}" in USER_PROMPT_TEMPLATE
    assert "{format_recommendations}" in USER_PROMPT_TEMPLATE
    assert "{campaign_history}" in USER_PROMPT_TEMPLATE
    assert "{client_brief}" in USER_PROMPT_TEMPLATE
    assert "{historical_research}" in USER_PROMPT_TEMPLATE


def test_user_prompt_renders():
    rendered = USER_PROMPT_TEMPLATE.format(
        topic="test topic",
        advertiser="test brand",
        advertiser_kpi="Awareness",
        advertiser_research="some research",
        audience_segments="some segments",
        format_recommendations="some formats",
        campaign_history="some history",
        client_brief="some brief",
        historical_research="some historical research",
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
        result = generate_insights(topic="test", advertiser="TestCo", kpi="Clicks")

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

    assert result == {"recognised": [], "recommended": [], "unrecognised": []}
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_guardrail_none_content_returns_empty_results_and_no_warning(caplog):
    """None as content must be coerced safely via 'content or \"\"' and must
    not crash or emit a warning."""
    with caplog.at_level(logging.WARNING):
        result = _run_format_name_guardrail(None)

    assert result == {"recognised": [], "recommended": [], "unrecognised": []}
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_guardrail_returns_safe_fallback_if_load_format_names_raises(caplog):
    """If load_format_names raises unexpectedly the guardrail must catch the
    exception, log at ERROR level, and return the empty safe-fallback dict
    rather than propagating the error."""
    from unittest.mock import patch

    with patch("src.synthesiser.load_format_names", side_effect=RuntimeError("CSV gone")):
        with caplog.at_level(logging.ERROR):
            result = _run_format_name_guardrail("- **Some Format** — CTR 1.00%")

    assert result == {"recognised": [], "recommended": [], "unrecognised": []}
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


# ---------------------------------------------------------------------------
# Structured deck payload (PRD #131 / slice #133)
#
# The deck download reuses what the brief run already produced. These tests pin
# the structured shape of the three fields the deck consumes so no numeric
# value ever has to be re-extracted from the generated markdown.
# ---------------------------------------------------------------------------

RESEARCH_BODY = "## Finding\n72% of travellers book city breaks in Q1."

# A brief naming one real catalogue format, so the deterministic name guardrail
# has something to recognise.
BRIEF_NAMING_A_FORMAT = (
    "## Recommended Products\n"
    "- **Standard display - Mobile Banner** — efficient mobile reach\n"
)


def _run_generate_insights(historical=None, content=BRIEF_NAMING_A_FORMAT):
    """Run generate_insights() with every external dependency stubbed out."""
    from unittest.mock import patch, MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content

    if historical is None:
        historical = {"relevant": False, "prompt_text": "No historical research matched this brief."}

    empty_segments = {"matched": False, "note": "", "query_terms": [], "platforms": []}

    with patch("src.synthesiser.research_advertiser", return_value=[]), \
         patch("src.synthesiser.expand_query", return_value={"keywords": [], "categories": []}), \
         patch("src.synthesiser.recommend_segments", return_value=empty_segments), \
         patch("src.synthesiser.get_campaign_summary",
               return_value={"summary": "No previous campaign data found.", "campaigns": []}), \
         patch("src.synthesiser.get_relevant_research", return_value=historical), \
         patch("src.synthesiser.OpenAI") as mock_openai_cls:

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        from src.synthesiser import generate_insights
        result = generate_insights(
            topic="city breaks", advertiser="TestCo", kpi="Clicks"
        )
        user_prompt = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]

    return result, user_prompt


def test_generate_insights_returns_only_the_recommended_formats():
    """The rows are narrowed to the formats the brief actually named, with the
    metrics straight off the CSV — so the deck knows which format is which
    without re-reading the prose, and no number came from the LLM."""
    from src.formats import load_format_rows

    result, user_prompt = _run_generate_insights()

    rows = result["format_recommendations"]
    assert [r["format"] for r in rows] == ["Standard display - Mobile Banner"]
    source = [
        r for r in load_format_rows()
        if r["format"] == "Standard display - Mobile Banner"
    ][0]
    assert rows[0] == source
    # The prompt still gets the whole catalogue as prose — narrowing is for the deck.
    assert "Primary objective:" in user_prompt


def test_generate_insights_recommends_no_formats_when_the_brief_names_none():
    """A brief naming no confirmed format yields an empty list rather than the
    whole catalogue — the deck shows nothing before it shows the wrong product."""
    result, _ = _run_generate_insights(content="A brief with no product names.")

    assert result["format_recommendations"] == []


def test_generate_insights_names_the_matched_research_file_not_its_body():
    """On a match the payload identifies the source file. The ~30KB body stays
    server-side: it is not persisted per brief nor round-tripped via the client."""
    historical = {
        "relevant": True,
        "prompt_text": RESEARCH_BODY,
        "file": "travel_audience_research_2024_25.md",
        "title": "Travel Audience Research",
        "organisation": "Prism",
        "fieldwork": "2024 to 2025",
        "total_respondents": 2000,
        "matched_on": ["city breaks"],
    }
    result, _ = _run_generate_insights(historical=historical)

    research = result["historical_research"]
    assert research["relevant"] is True
    assert research["file"] == "travel_audience_research_2024_25.md"
    assert research["title"] == "Travel Audience Research"
    # The body must not leave the server under any key.
    assert RESEARCH_BODY not in json.dumps(research)
    assert "prompt_text" not in research


def test_generate_insights_omits_research_file_when_nothing_matched():
    """No match means nothing to ground insights in — the deck omits the section."""
    result, _ = _run_generate_insights()

    research = result["historical_research"]
    assert research["relevant"] is False
    assert "file" not in research
    assert "prompt_text" not in research


def test_generate_insights_payload_is_json_serialisable():
    """The whole result is persisted to briefs.result_json and re-posted to the
    deck endpoint, so every deck-bearing field must survive a JSON round-trip."""
    result, _ = _run_generate_insights()
    revived = json.loads(json.dumps(result))

    for key in ("audience_segments", "format_recommendations", "historical_research",
                "provenance"):
        assert revived[key] == result[key]


# ---------------------------------------------------------------------------
# Google Trends is gone (#176)
#
# The removal crosses the fetch, the payload, the prompt and the dependency
# list, and a half-removal is worse than either end of it: a prompt still
# asking for a "### Google Trends" block the synthesiser no longer fills would
# either raise on format() or, worse, quietly hand the model an empty section
# to reason about. These pin each end.
# ---------------------------------------------------------------------------


def test_the_brief_payload_carries_no_google_trends_key():
    result, _ = _run_generate_insights()

    assert "google_trends" not in result


def test_no_prompt_asks_the_model_about_google_trends():
    """Neither half of the prompt may mention a source the model is not given.

    Asking it to "note when Trends data is unavailable" against a prompt with
    no Trends block at all is an invitation to write about an absence the user
    never chose.
    """
    _, user_prompt = _run_generate_insights()

    assert "google trends" not in user_prompt.lower()
    assert "google trends" not in SYSTEM_PROMPT.lower()


def test_nothing_imports_the_trends_module_or_pytrends():
    """The module and its dependency left together. A stale import would only
    surface at runtime, on a machine that had never uninstalled pytrends — so
    every directory that ships Python is swept, not just the package the
    pipeline lives in.
    """
    paths = glob.glob(os.path.join(PROJECT_ROOT, "*.py"))
    for package in ("src", "api", "scripts"):
        paths += glob.glob(os.path.join(PROJECT_ROOT, package, "*.py"))
    assert len(paths) > 20, "the sweep found almost nothing — has a path moved?"

    for path in paths:
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert "pytrends" not in source, "%s still imports pytrends" % path
        assert "src.trends" not in source, "%s still imports src.trends" % path

    with open(os.path.join(PROJECT_ROOT, "requirements.txt"), encoding="utf-8") as f:
        assert "pytrends" not in f.read()


# ---------------------------------------------------------------------------
# Provenance (#156)
#
# Every figure a brief carries has to name the source, date, coverage and
# period behind it. The pipeline's job is to attach the right set of sections
# for the run — the registry itself is tested in tests/test_provenance.py.
# ---------------------------------------------------------------------------


def test_generate_insights_attaches_provenance_for_every_section_it_rendered():
    result, _ = _run_generate_insights()

    sections = [e["section"] for e in result["provenance"]]
    for expected in ("Advertiser Overview", "Client Relationship",
                     "Audience Segments & Reach", "Recommended Products"):
        assert expected in sections
    for entry in result["provenance"]:
        assert entry["source"]
        assert entry["coverage"]
        assert entry["period"]


def test_generate_insights_omits_provenance_for_sections_it_did_not_render():
    """No research matched, so there is no source line claiming one did."""
    result, _ = _run_generate_insights()

    sections = [e["section"] for e in result["provenance"]]
    assert "Historical Research" not in sections


def test_generate_insights_dates_research_provenance_from_the_matched_study():
    historical = {
        "relevant": True,
        "prompt_text": RESEARCH_BODY,
        "file": "travel_audience_research_2024_25.md",
        "title": "Travel Audience Research",
        "organisation": "Prism",
        "fieldwork": "2024-11-26 to 2024-12-02",
        "total_respondents": 2000,
        "matched_on": ["city breaks"],
    }
    result, _ = _run_generate_insights(historical=historical)

    entry = [e for e in result["provenance"] if e["section"] == "Historical Research"][0]
    assert entry["as_at"] == "2024-12-02"
    assert "Travel Audience Research" in entry["source"]


def test_generate_insights_never_asks_the_model_for_a_source():
    """Provenance is placed deterministically, so it cannot be hallucinated —
    the prompt carries no source registry for the model to paraphrase."""
    from src.provenance import load_provenance

    _, user_prompt = _run_generate_insights()

    for entry in load_provenance():
        assert entry["source"] not in user_prompt


def test_advertiser_research_receives_the_topic_and_brief():
    """#155: the topic and client brief must reach the advertiser research step."""
    from unittest.mock import patch, MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test brief content"

    empty_segments = {"matched": False, "note": "", "query_terms": [], "platforms": []}

    with patch("src.synthesiser.research_advertiser", return_value=[]) as mock_research, \
         patch("src.synthesiser.expand_query", return_value={"keywords": [], "categories": []}), \
         patch("src.synthesiser.recommend_segments", return_value=empty_segments), \
         patch("src.synthesiser.get_campaign_summary", return_value={"summary": "", "campaigns": []}), \
         patch("src.synthesiser.summarise_brief", return_value="Festive food push in November.") as mock_summarise, \
         patch("src.synthesiser.OpenAI") as mock_openai_cls:

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        from src.synthesiser import generate_insights
        generate_insights(
            topic="Christmas",
            advertiser="Morrisons",
            kpi="Reach",
            client_brief="We want to drive festive food sales in November.",
        )

    assert mock_research.call_args.kwargs["topic"] == "Christmas"
    assert mock_research.call_args.kwargs["client_brief"] == "Festive food push in November."
    # The brief is summarised once and reused, not summarised twice.
    assert mock_summarise.call_count == 1


def test_advertiser_research_gets_no_brief_context_when_none_supplied():
    """An absent brief must not reach research as the 'No client brief' sentinel."""
    from unittest.mock import patch, MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test brief content"

    empty_segments = {"matched": False, "note": "", "query_terms": [], "platforms": []}

    with patch("src.synthesiser.research_advertiser", return_value=[]) as mock_research, \
         patch("src.synthesiser.expand_query", return_value={"keywords": [], "categories": []}), \
         patch("src.synthesiser.recommend_segments", return_value=empty_segments), \
         patch("src.synthesiser.get_campaign_summary", return_value={"summary": "", "campaigns": []}), \
         patch("src.synthesiser.OpenAI") as mock_openai_cls:

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        from src.synthesiser import generate_insights
        generate_insights(
            topic="Christmas",
            advertiser="Morrisons",
            kpi="Reach",
        )

    assert mock_research.call_args.kwargs["client_brief"] == ""


def test_recommended_formats_come_back_in_the_order_the_brief_listed_them():
    """The rows the brief returns are what the format reason strip renders (#163)
    and what the deck's product tiles take its first three from. Both sit next
    to the brief's own list, so "first" has to mean the brief's first, not the
    catalogue's — otherwise the reasons read in one order and the products they
    explain in another.
    """
    from unittest.mock import patch, MagicMock

    # The brief recommends two formats, deliberately in the reverse of the
    # order the catalogue holds them in.
    content = (
        "## Recommended Products\n"
        "- **Host Read** — first\n"
        "- **Standard display - MPU** — second\n"
    )
    catalogue = [
        {"format": "Standard display - MPU", "best_for_brief": "Efficient reach"},
        {"format": "Host Read", "best_for_brief": "Trusted endorsement"},
        {"format": "Never Recommended", "best_for_brief": "Not in this brief"},
    ]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content

    with patch("src.synthesiser.research_advertiser", return_value=[]), \
         patch("src.synthesiser.expand_query", return_value={"keywords": [], "categories": []}), \
         patch("src.synthesiser.recommend_segments", return_value={"matched": False, "note": "", "query_terms": [], "platforms": []}), \
         patch("src.synthesiser.get_campaign_summary", return_value={"summary": "none", "campaigns": []}), \
         patch("src.synthesiser.load_format_rows", return_value=catalogue), \
         patch("src.synthesiser.load_format_names", return_value=[r["format"] for r in catalogue]), \
         patch("src.synthesiser.OpenAI") as mock_openai_cls:

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        from src.synthesiser import generate_insights
        result = generate_insights(topic="t", advertiser="A", kpi="Awareness")

    assert [row["format"] for row in result["format_recommendations"]] == [
        "Host Read", "Standard display - MPU",
    ]
