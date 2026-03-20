from src.web_search import load_skills


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
