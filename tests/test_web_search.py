from unittest.mock import patch, MagicMock

from src.web_search import load_skills, _run_search, run_skill


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
