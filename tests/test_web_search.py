from unittest.mock import patch, MagicMock

import pytest

from src.web_search import (
    _build_topic_directive,
    load_skills,
    research_advertiser,
    _format_results_block,
    _run_search,
    _skill_queries,
    run_skill,
)


def test_load_skills_finds_all():
    skills = load_skills()
    assert len(skills) >= 3
    names = [s["name"] for s in skills]
    assert "Company Overview" in names
    assert "Strategy & Challenges" in names
    assert "Recent News" in names


def test_skill_structure():
    skills = load_skills()
    for skill in skills:
        assert "name" in skill
        assert "queries" in skill
        assert len(skill["queries"]) > 0
        assert "prompt" in skill
        assert len(skill["prompt"]) > 0
        assert "max_results_per_query" in skill
        assert skill["max_results_per_query"] > 0


def test_skill_queries_have_brand_placeholder():
    skills = load_skills()
    for skill in skills:
        for query in skill["queries"]:
            assert "{brand}" in query, f"Query missing {{brand}} placeholder: {query}"


def test_skill_prompt_has_placeholders():
    skills = load_skills()
    for skill in skills:
        assert "{brand}" in skill["prompt"] or "{search_results}" in skill["prompt"]


def test_skills_include_timelimit():
    skills = load_skills()
    for skill in skills:
        assert "timelimit" in skill, f"Skill {skill['name']} missing timelimit key"


def test_timelimit_defaults_to_year():
    """Skills that omit timelimit from frontmatter should default to 'y'."""
    skills = load_skills()
    for skill in skills:
        if skill["timelimit"] is not None:
            assert skill["timelimit"] in ("d", "w", "m", "y"), \
                f"Skill {skill['name']} has invalid timelimit: {skill['timelimit']}"


def test_company_overview_has_no_timelimit():
    """Company Overview should explicitly opt out of time filtering."""
    skills = load_skills()
    overview = [s for s in skills if s["name"] == "Company Overview"][0]
    assert overview["timelimit"] is None


@patch("src.web_search.DDGS")
def test_run_search_passes_timelimit(mock_ddgs_cls):
    """_run_search should pass timelimit to ddgs.text()."""
    mock_instance = MagicMock()
    mock_instance.text.return_value = []
    mock_ddgs_cls.return_value = mock_instance

    _run_search("test query", max_results=3, timelimit="y")

    mock_instance.text.assert_called_once_with(
        "test query", max_results=3, timelimit="y"
    )


@patch("src.web_search.DDGS")
def test_run_search_passes_none_timelimit(mock_ddgs_cls):
    """_run_search with timelimit=None should pass None to ddgs.text()."""
    mock_instance = MagicMock()
    mock_instance.text.return_value = []
    mock_ddgs_cls.return_value = mock_instance

    _run_search("test query", max_results=3, timelimit=None)

    mock_instance.text.assert_called_once_with(
        "test query", max_results=3, timelimit=None
    )


@patch("src.web_search.DDGS")
def test_run_skill_substitutes_year_placeholder(mock_ddgs_cls):
    """run_skill should replace {year} in queries with the current year."""
    from datetime import datetime

    mock_instance = MagicMock()
    mock_instance.text.return_value = [
        {"title": "Test", "body": "Test body", "href": "http://example.com"}
    ]
    mock_ddgs_cls.return_value = mock_instance

    skill = {
        "name": "Test Skill",
        "queries": ['"{brand}" strategy {year}'],
        "max_results_per_query": 3,
        "timelimit": "y",
        "prompt": "Summarise results about {brand}:\n{search_results}",
    }

    with patch("src.web_search.OpenAI"):
        run_skill(skill, "Acme Corp")

    expected_query = '"Acme Corp" strategy %d' % datetime.now().year
    mock_instance.text.assert_called_once_with(
        expected_query, max_results=3, timelimit="y"
    )


# ---------------------------------------------------------------------------
# Topic-aware research (#155)
#
# The brief's topic has to reach the search step, or the research comes back
# describing whatever the advertiser is best known for. These tests pin the
# three seams: which queries run, how results are labelled, and what the
# summariser is told to do with them.
# ---------------------------------------------------------------------------


def _skill(**overrides):
    skill = {
        "name": "Test Skill",
        "queries": ['"{brand}" about company overview'],
        "topic_queries": ['"{brand}" {topic}', '"{brand}" {topic} campaign'],
        "max_results_per_query": 3,
        "timelimit": "y",
        "prompt": "Summarise results about {brand}:\n{search_results}",
    }
    skill.update(overrides)
    return skill


def test_every_skill_declares_topic_queries():
    """Each shipped skill must have at least one topic-anchored query."""
    for skill in load_skills():
        assert skill["topic_queries"], f"{skill['name']} has no topic_queries"
        for query in skill["topic_queries"]:
            assert "{topic}" in query, f"{skill['name']} topic query missing {{topic}}: {query}"


def test_topic_queries_default_to_empty_when_absent():
    """A skill file without topic_queries still loads (backward compatible)."""
    skill = _skill()
    del skill["topic_queries"]
    assert _skill_queries(skill, "gut health") == [('"{brand}" about company overview', False)]


def test_skill_queries_include_topic_queries_when_topic_given():
    queries = _skill_queries(_skill(), "gut health")
    assert queries == [
        ('"{brand}" about company overview', False),
        ('"{brand}" {topic}', True),
        ('"{brand}" {topic} campaign', True),
    ]


@pytest.mark.parametrize("topic", ["", "   ", None])
def test_topic_queries_are_skipped_without_a_topic(topic):
    """No topic must never become a blank substitution — the query is dropped."""
    assert _skill_queries(_skill(), topic) == [('"{brand}" about company overview', False)]


@patch("src.web_search.DDGS")
def test_run_skill_searches_for_the_topic(mock_ddgs_cls):
    """AC1: the topic reaches the search step and shapes what is searched for."""
    mock_instance = MagicMock()
    mock_instance.text.return_value = []
    mock_ddgs_cls.return_value = mock_instance

    with patch("src.web_search.OpenAI"), patch("src.web_search.time.sleep"):
        run_skill(_skill(), "Morrisons", topic="Christmas")

    issued = [call.args[0] for call in mock_instance.text.call_args_list]
    assert '"Morrisons" about company overview' in issued
    assert '"Morrisons" Christmas' in issued
    assert '"Morrisons" Christmas campaign' in issued


@patch("src.web_search.DDGS")
def test_run_skill_without_topic_is_unchanged(mock_ddgs_cls):
    """AC4: with no topic, the brand-only baseline runs exactly as before."""
    mock_instance = MagicMock()
    mock_instance.text.return_value = []
    mock_ddgs_cls.return_value = mock_instance

    with patch("src.web_search.OpenAI"), patch("src.web_search.time.sleep"):
        run_skill(_skill(), "Morrisons")

    issued = [call.args[0] for call in mock_instance.text.call_args_list]
    assert issued == ['"Morrisons" about company overview']


def test_results_block_separates_topic_from_general():
    results = [
        {"title": "Morrisons Christmas ad", "body": "Festive campaign", "href": "http://a", "topic_anchored": True},
        {"title": "Morrisons kidswear", "body": "Nutmeg range", "href": "http://b", "topic_anchored": False},
    ]
    block = _format_results_block(results, "Morrisons", "Christmas")

    assert "TOPIC-SPECIFIC" in block
    assert "GENERAL BRAND" in block
    # Each result sits under the right heading.
    topic_part, general_part = block.split("GENERAL BRAND")
    assert "Morrisons Christmas ad" in topic_part
    assert "Morrisons kidswear" not in topic_part
    assert "Morrisons kidswear" in general_part


def test_results_block_states_when_no_topic_material_found():
    """AC3: absence is reported, not quietly backfilled with brand material."""
    results = [
        {"title": "Morrisons kidswear", "body": "Nutmeg range", "href": "http://b", "topic_anchored": False},
    ]
    block = _format_results_block(results, "Morrisons", "Christmas")

    topic_part = block.split("GENERAL BRAND")[0]
    assert "none" in topic_part.lower()


def test_results_block_is_a_flat_list_without_a_topic():
    """No topic, no sectioning — the prompt sees what it saw before."""
    results = [
        {"title": "Morrisons kidswear", "body": "Nutmeg range", "href": "http://b", "topic_anchored": False},
    ]
    block = _format_results_block(results, "Morrisons", "")

    assert "TOPIC-SPECIFIC" not in block
    assert block == "- [Morrisons kidswear](http://b): Nutmeg range"


@patch("src.web_search.DDGS")
def test_run_skill_dedupes_and_keeps_the_topic_flag(mock_ddgs_cls):
    """A hit found by both a brand and a topic query counts as topic material once."""
    mock_instance = MagicMock()
    mock_instance.text.side_effect = [
        [{"title": "Shared", "body": "Same article", "href": "http://same"}],
        [{"title": "Shared", "body": "Same article", "href": "http://same"}],
        [],
    ]
    mock_ddgs_cls.return_value = mock_instance

    with patch("src.web_search.OpenAI"), patch("src.web_search.time.sleep"):
        result = run_skill(_skill(), "Morrisons", topic="Christmas")

    assert len(result["raw_results"]) == 1
    assert result["raw_results"][0]["topic_anchored"] is True


@patch("src.web_search.DDGS")
def test_run_skill_prompt_carries_topic_and_brief(mock_ddgs_cls):
    """The summariser is told the subject and how to handle a thin topic section."""
    mock_instance = MagicMock()
    mock_instance.text.return_value = [
        {"title": "T", "body": "B", "href": "http://x"}
    ]
    mock_ddgs_cls.return_value = mock_instance

    with patch("src.web_search.OpenAI") as mock_openai_cls, patch("src.web_search.time.sleep"):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        run_skill(
            _skill(),
            "Morrisons",
            topic="Christmas",
            client_brief="Drive festive food sales in November.",
        )

    prompt = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "Christmas" in prompt
    assert "Drive festive food sales in November." in prompt
    assert "TOPIC-SPECIFIC" in prompt
    # The instruction that stops general material being passed off as topic material.
    assert "Do not pad" in prompt


@patch("src.web_search.DDGS")
def test_run_skill_prompt_has_no_topic_directive_without_a_topic(mock_ddgs_cls):
    mock_instance = MagicMock()
    mock_instance.text.return_value = [
        {"title": "T", "body": "B", "href": "http://x"}
    ]
    mock_ddgs_cls.return_value = mock_instance

    with patch("src.web_search.OpenAI") as mock_openai_cls, patch("src.web_search.time.sleep"):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        run_skill(_skill(), "Morrisons")

    prompt = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "Brief context" not in prompt
    assert "TOPIC-SPECIFIC" not in prompt


@patch("src.web_search.DDGS")
def test_run_skill_substitutes_topic_in_the_prompt_body(mock_ddgs_cls):
    """Skill authors can reference {topic} in the prompt body itself."""
    mock_instance = MagicMock()
    mock_instance.text.return_value = [
        {"title": "T", "body": "B", "href": "http://x"}
    ]
    mock_ddgs_cls.return_value = mock_instance

    skill = _skill(prompt="Report on {brand} and {topic}:\n{search_results}")
    with patch("src.web_search.OpenAI") as mock_openai_cls, patch("src.web_search.time.sleep"):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        run_skill(skill, "Morrisons", topic="Christmas")

    prompt = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "Report on Morrisons and Christmas:" in prompt


@patch("src.web_search.DDGS")
def test_no_results_message_names_the_topic(mock_ddgs_cls):
    mock_instance = MagicMock()
    mock_instance.text.return_value = []
    mock_ddgs_cls.return_value = mock_instance

    with patch("src.web_search.OpenAI"), patch("src.web_search.time.sleep"):
        result = run_skill(_skill(), "Morrisons", topic="Christmas")

    assert "Christmas" in result["processed_summary"]


@patch("src.web_search.load_skills")
def test_research_advertiser_forwards_topic_and_brief(mock_load_skills):
    mock_load_skills.return_value = [_skill(), _skill(name="Second")]

    with patch("src.web_search.run_skill", return_value={}) as mock_run_skill, \
         patch("src.web_search.time.sleep"):
        research_advertiser("Morrisons", topic="Christmas", client_brief="Festive food.")

    for call in mock_run_skill.call_args_list:
        assert call.kwargs["topic"] == "Christmas"
        assert call.kwargs["client_brief"] == "Festive food."


# ---------------------------------------------------------------------------
# Per-skill topic focus (#155, AC4)
#
# `topic` is a required API field, so every production brief takes the topic
# path — the no-topic path is unreachable there and proves nothing about
# "thick-roster briefs are no worse". Skills differ in what the topic should do
# to them: Company Overview feeds the brief's Advertiser Overview section and
# must stay brand-complete; the others should lead with the topic.
# ---------------------------------------------------------------------------


def test_company_overview_supplements_rather_than_leads():
    overview = [s for s in load_skills() if s["name"] == "Company Overview"][0]
    assert overview["topic_focus"] == "supplement"


def test_other_skills_lead_with_the_topic():
    for skill in load_skills():
        if skill["name"] == "Company Overview":
            continue
        assert skill["topic_focus"] == "lead", skill["name"]


def test_topic_focus_defaults_to_lead():
    """A skill file that says nothing about focus leads with the topic."""
    skill = _skill()
    assert skill.get("topic_focus", "lead") == "lead"
    directive = _build_topic_directive("Morrisons", "Christmas", "", None)
    assert "Lead with the TOPIC-SPECIFIC results" in directive


def test_supplement_directive_protects_the_general_overview():
    """AC4: a supplement skill keeps its brand-general material intact."""
    directive = _build_topic_directive("Morrisons", "Christmas", "", "supplement")

    assert "do not drop it" in directive
    # The instruction that would have thinned the Advertiser Overview section.
    assert "only as supporting context" not in directive


def test_both_focuses_keep_the_thin_topic_rule():
    """AC3 holds whichever way a skill is focused."""
    for focus in ("lead", "supplement"):
        directive = _build_topic_directive("Morrisons", "Christmas", "", focus)
        assert "Do not pad" in directive
        assert "Little material found" in directive


@patch("src.web_search.DDGS")
def test_run_skill_uses_the_skills_topic_focus(mock_ddgs_cls):
    mock_instance = MagicMock()
    mock_instance.text.return_value = [
        {"title": "T", "body": "B", "href": "http://x"}
    ]
    mock_ddgs_cls.return_value = mock_instance

    with patch("src.web_search.OpenAI") as mock_openai_cls, patch("src.web_search.time.sleep"):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        run_skill(_skill(topic_focus="supplement"), "Morrisons", topic="Christmas")

    prompt = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "do not drop it" in prompt
