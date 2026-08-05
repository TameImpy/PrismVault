import os

import pytest

from src.historical_research import (
    get_relevant_research,
    load_catalogue,
    load_research_body,
)

# A minimal fixture file that mirrors the real travel catalogue file's shape:
# YAML frontmatter with `topics` (verbose phrases) + `match_keywords` (single
# words) and a markdown body carrying a quotable, dated survey figure.
FIXTURE_FILE = """---
title: "Immediate Media Travel Audience Research 2024/25"
organisation: "Immediate Media"
fieldwork_start: "2024-11-26"
fieldwork_end: "2024-12-02"
total_respondents: 1589
topics:
  - cruises
  - city breaks
  - rail travel
match_keywords:
  - travel
  - holiday
  - cruise
  - flight
  - hotel
audience_terms:
  - affluent empty-nesters
  - empty nesters
  - over-55s
---

# Immediate Media Travel Audience Research 2024/25

Among 334 cruise intenders, P&O Cruises led consideration at 38%.
"""


@pytest.fixture()
def catalogue_dir(tmp_path):
    """A one-file historical-research catalogue in a temp directory."""
    d = tmp_path / "historical_research"
    d.mkdir()
    (d / "travel.md").write_text(FIXTURE_FILE)
    return str(d)


def test_gate_matches_cruise_brief(catalogue_dir):
    result = get_relevant_research(
        "cruise campaign for over-50s", "P&O Cruises", "",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is True


def test_gate_ignores_non_travel_brief(catalogue_dir):
    result = get_relevant_research(
        "running shoes launch", "Nike", "",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is False
    # No-match contract: fallback string present, no metadata keys.
    assert result["prompt_text"] == "No historical research matched this brief."
    assert "title" not in result


def test_gate_is_case_insensitive(catalogue_dir):
    result = get_relevant_research(
        "CRUISE CAMPAIGN", "P&O CRUISES", "",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is True


def test_gate_hits_on_match_keyword(catalogue_dir):
    # "hotel" is a match_keyword but not a topic phrase.
    result = get_relevant_research(
        "budget hotel promotion", "Premier Inn", "",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is True
    assert "hotel" in result["matched_on"]


def test_gate_hits_on_topic_phrase(catalogue_dir):
    # "city breaks" is a verbose topics phrase, not a single match_keyword.
    result = get_relevant_research(
        "city breaks push", "SomeBrand", "",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is True
    assert "city breaks" in result["matched_on"]


def test_gate_matches_on_client_brief_only(catalogue_dir):
    # A keyword present ONLY in client_brief still fires (concatenation).
    result = get_relevant_research(
        "generic launch", "Acme", "We want to reach cruise intenders this winter",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is True


def test_match_returns_verbatim_frontmatter_metadata(catalogue_dir):
    result = get_relevant_research(
        "cruise campaign", "P&O Cruises", "",
        catalogue_dir=catalogue_dir,
    )
    assert result["title"] == "Immediate Media Travel Audience Research 2024/25"
    assert result["organisation"] == "Immediate Media"
    assert result["fieldwork"] == "2024-11-26 to 2024-12-02"
    assert result["total_respondents"] == 1589
    # The whole file body rides through verbatim for the single GPT-4o call.
    assert "334 cruise intenders" in result["prompt_text"]


# --- Loader ---------------------------------------------------------------

def test_loader_parses_frontmatter_and_body(catalogue_dir):
    files = load_catalogue(catalogue_dir)
    assert len(files) == 1
    f = files[0]
    assert f["meta"]["title"] == "Immediate Media Travel Audience Research 2024/25"
    assert "cruise" in f["match_keywords"]
    assert "cruises" in f["topics"]
    assert f["body"].startswith("# Immediate Media Travel Audience Research")


def test_loader_missing_folder_returns_empty(tmp_path):
    missing = str(tmp_path / "does_not_exist")
    assert load_catalogue(missing) == []


def test_loader_empty_folder_returns_empty(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert load_catalogue(str(empty)) == []


def test_gate_no_files_is_not_relevant(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = get_relevant_research("cruise", "P&O", "", catalogue_dir=str(empty))
    assert result["relevant"] is False
    assert result["prompt_text"] == "No historical research matched this brief."


# --- Real catalogue regression guard (the demo) ---------------------------

def test_real_catalogue_pando_fires_nike_doesnt():
    """The live-demo regression guard, run against the actual shipped file."""
    pando = get_relevant_research("cruise campaign for over-50s", "P&O Cruises", "")
    assert pando["relevant"] is True
    assert pando["total_respondents"] == 1589

    nike = get_relevant_research("running shoes launch", "Nike", "")
    assert nike["relevant"] is False


# --- Edge-case hardening --------------------------------------------------

# Fixture: a catalogue file whose frontmatter has `topics` but NO `match_keywords`
# key at all. The loader must still parse it and the gate must still match on topics.
FIXTURE_NO_MATCH_KEYWORDS = """\
---
title: "Outdoor Activities Study 2025"
organisation: "TestOrg"
fieldwork_start: "2025-01-01"
fieldwork_end: "2025-01-31"
total_respondents: 500
topics:
  - hiking
  - camping
---

# Outdoor Activities Study 2025

Survey of 500 outdoor enthusiasts.
"""

# Fixture: a file with no YAML frontmatter delimiter at all — should be skipped.
FIXTURE_MALFORMED = """\
This file has no frontmatter.

Just some markdown content that should be ignored by the loader.
"""

# Fixture: a second catalogue file to test multi-file matching.
FIXTURE_FILE_B = """\
---
title: "Tech Consumer Survey 2025"
organisation: "TechResearch Ltd"
fieldwork_start: "2025-03-01"
fieldwork_end: "2025-03-15"
total_respondents: 800
topics:
  - smartphones
match_keywords:
  - mobile
  - tech
---

# Tech Consumer Survey 2025

Survey of 800 smartphone users.
"""


@pytest.fixture()
def catalogue_dir_no_match_keywords(tmp_path):
    """Catalogue with one file that has topics but no match_keywords key."""
    d = tmp_path / "historical_research"
    d.mkdir()
    (d / "outdoor.md").write_text(FIXTURE_NO_MATCH_KEYWORDS)
    return str(d)


@pytest.fixture()
def catalogue_dir_with_malformed(tmp_path):
    """Catalogue with one valid file and one malformed file (no frontmatter)."""
    d = tmp_path / "historical_research"
    d.mkdir()
    (d / "travel.md").write_text(FIXTURE_FILE)
    (d / "broken.md").write_text(FIXTURE_MALFORMED)
    return str(d)


@pytest.fixture()
def catalogue_dir_two_files(tmp_path):
    """Catalogue with two valid files — travel.md (first alphabetically) and tech.md."""
    d = tmp_path / "historical_research"
    d.mkdir()
    # "aaa_tech.md" sorts before "travel.md" so it comes first in sorted glob.
    (d / "aaa_tech.md").write_text(FIXTURE_FILE_B)
    (d / "travel.md").write_text(FIXTURE_FILE)
    return str(d)


def test_loader_skips_file_without_match_keywords_key(catalogue_dir_no_match_keywords):
    """A file with topics but no match_keywords key loads with an empty keyword list."""
    files = load_catalogue(catalogue_dir_no_match_keywords)
    assert len(files) == 1
    assert files[0]["match_keywords"] == []
    assert "hiking" in files[0]["topics"]


def test_gate_matches_on_topics_when_match_keywords_absent(catalogue_dir_no_match_keywords):
    """Gate still fires on a topic phrase when match_keywords is missing entirely."""
    result = get_relevant_research("hiking holiday", "OutdoorBrand", "",
                                   catalogue_dir=catalogue_dir_no_match_keywords)
    assert result["relevant"] is True
    assert "hiking" in result["matched_on"]


def test_loader_skips_malformed_file_silently(catalogue_dir_with_malformed):
    """A .md file with no YAML frontmatter block is skipped; the valid file loads."""
    files = load_catalogue(catalogue_dir_with_malformed)
    # Only the valid travel.md should be loaded; broken.md must be silently dropped.
    assert len(files) == 1
    assert files[0]["meta"]["title"] == "Immediate Media Travel Audience Research 2024/25"


def test_gate_word_boundary_rail_does_not_match_email(catalogue_dir):
    """The keyword 'rail' must NOT fire when the brief only contains 'email'.

    'email' contains 'rail' as a substring but the word-boundary regex must
    prevent this false positive — otherwise any brief mentioning email marketing
    would incorrectly trigger the travel research file.
    """
    result = get_relevant_research(
        "email marketing push", "Acme Retail", "Send email newsletter to subscribers",
        catalogue_dir=catalogue_dir,
    )
    # 'rail travel' is a topic phrase — but none of the brief words are 'rail'.
    # 'email' must NOT count as a hit for the needle 'rail'.
    assert result["relevant"] is False


def test_gate_multi_file_returns_first_alphabetical_match(catalogue_dir_two_files):
    """When multiple files match, the function returns the first (sorted) match only."""
    # Both files match on "mobile" (tech.md) and "cruise" (travel.md), but
    # "mobile" only appears in aaa_tech.md — use a brief that hits only aaa_tech.md.
    result = get_relevant_research(
        "mobile phone campaign", "Samsung", "",
        catalogue_dir=catalogue_dir_two_files,
    )
    assert result["relevant"] is True
    assert result["title"] == "Tech Consumer Survey 2025"
    assert result["total_respondents"] == 800


def test_gate_second_file_matches_when_first_does_not(catalogue_dir_two_files):
    """A brief that skips the first file still matches the second one."""
    # "cruise" is only in travel.md (which sorts after aaa_tech.md).
    result = get_relevant_research(
        "luxury cruise holiday", "P&O Cruises", "",
        catalogue_dir=catalogue_dir_two_files,
    )
    assert result["relevant"] is True
    assert result["title"] == "Immediate Media Travel Audience Research 2024/25"


def test_gate_empty_string_inputs_do_not_crash(catalogue_dir):
    """All-empty string inputs return a well-formed no-match result without raising."""
    result = get_relevant_research("", "", "", catalogue_dir=catalogue_dir)
    assert result["relevant"] is False
    assert result["prompt_text"] == "No historical research matched this brief."


def test_gate_none_inputs_do_not_crash(catalogue_dir):
    """None inputs are tolerated without raising — treated as empty strings."""
    result = get_relevant_research(None, None, None, catalogue_dir=catalogue_dir)
    assert result["relevant"] is False
    assert result["prompt_text"] == "No historical research matched this brief."


# --- Subject relevance vs shared demographic (#157) ------------------------
#
# A research file's vocabulary is not all of one kind. Its topics and
# match_keywords describe what the research is ABOUT; its audience_terms
# describe WHO was surveyed. Only the first kind may admit a file — otherwise a
# hearing-aids brief aimed at over-55s pulls in travel research on the strength
# of the demographic alone, which is what Abel hit in the August 2026 QA round.

# A file whose audience descriptors are (wrongly) left in `topics` as well as in
# `audience_terms`. Listing a term as an audience term must demote it wherever
# else it appears, so a mis-authored file cannot re-open the hole.
FIXTURE_DEMOGRAPHIC_IN_TOPICS = """\
---
title: "Later Life Leisure Study 2025"
organisation: "TestOrg"
fieldwork_start: "2025-02-01"
fieldwork_end: "2025-02-28"
total_respondents: 900
topics:
  - garden centres
  - affluent empty-nesters
match_keywords:
  - gardening
audience_terms:
  - affluent empty-nesters
---

# Later Life Leisure Study 2025

Survey of 900 adults aged 55 and over.
"""


@pytest.fixture()
def catalogue_dir_demographic_in_topics(tmp_path):
    d = tmp_path / "historical_research"
    d.mkdir()
    (d / "leisure.md").write_text(FIXTURE_DEMOGRAPHIC_IN_TOPICS)
    return str(d)


def test_shared_demographic_alone_does_not_admit_research(catalogue_dir):
    """Abel's report: a hearing-aids brief must not pull in travel research."""
    result = get_relevant_research(
        "hearing aids", "Boots Hearingcare",
        "Reach affluent empty-nesters, over-55s, in the market for hearing aids",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is False
    assert result["prompt_text"] == "No historical research matched this brief."
    assert "title" not in result


def test_subject_match_still_admits_when_the_demographic_is_shared_too(catalogue_dir):
    """The demographic must not disqualify research that is genuinely on-subject."""
    result = get_relevant_research(
        "river cruises", "Riviera Travel",
        "Reach affluent empty-nesters, over-55s, planning a cruise",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is True
    # Both kinds of term are reported, subject first, so the hero card can say
    # what actually earned the match rather than only who was surveyed.
    assert result["matched_on"][0] in ("cruises", "travel", "cruise")
    assert "affluent empty-nesters" in result["matched_on"]


def test_subject_match_alone_still_admits(catalogue_dir):
    """No demographic overlap at all is still a match on subject."""
    result = get_relevant_research(
        "city breaks push", "SomeBrand", "Reach students",
        catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is True
    assert result["matched_on"] == ["city breaks"]


def test_audience_term_is_demoted_even_where_topics_repeats_it(
    catalogue_dir_demographic_in_topics,
):
    result = get_relevant_research(
        "hearing aids", "Boots Hearingcare", "Reach affluent empty-nesters",
        catalogue_dir=catalogue_dir_demographic_in_topics,
    )
    assert result["relevant"] is False


def test_loader_exposes_audience_terms(catalogue_dir):
    files = load_catalogue(catalogue_dir)
    assert files[0]["audience_terms"] == [
        "affluent empty-nesters", "empty nesters", "over-55s",
    ]
    # ...and they are kept out of the subject vocabulary.
    assert "affluent empty-nesters" not in files[0]["topics"]


def test_loader_defaults_audience_terms_to_empty(catalogue_dir_no_match_keywords):
    """A file predating the field keeps its whole vocabulary as subject terms."""
    files = load_catalogue(catalogue_dir_no_match_keywords)
    assert files[0]["audience_terms"] == []


def test_demographic_only_brief_omits_the_section_end_to_end(catalogue_dir):
    """The no-match path feeds the omission machinery, not just a False flag.

    An empty body is what makes the deck drop its Historical Insights slide, so
    a brief that now stops matching has to reach that state, not merely report
    ``relevant: False``.
    """
    result = get_relevant_research(
        "hearing aids", "Boots Hearingcare", "Reach affluent empty-nesters",
        catalogue_dir=catalogue_dir,
    )
    assert load_research_body(result, catalogue_dir=catalogue_dir) == ""


def test_a_term_ending_in_punctuation_is_not_a_dead_term(tmp_path):
    """`\\b55\\+\\b` can never match "55+" — a silently dead hand-authored term.

    #157's own wording is a 55+ audience, so the trap is one an author of this
    frontmatter would walk straight into. The boundary is defined by what sits
    outside the needle instead.
    """
    d = tmp_path / "historical_research"
    d.mkdir()
    (d / "ages.md").write_text(
        '---\ntitle: "Age Bands Study"\ntopics:\n  - retirement planning\n'
        'audience_terms:\n  - 55+\n---\n\n# Age Bands Study\n\nBody.\n'
    )
    result = get_relevant_research(
        "retirement planning", "Acme", "Audience is 55+", catalogue_dir=str(d),
    )
    assert result["relevant"] is True
    assert "55+" in result["matched_on"]


def test_whole_word_guard_still_rejects_a_substring_hit(catalogue_dir):
    """The lookaround boundary must not loosen the rail/email guarantee."""
    result = get_relevant_research(
        "email marketing", "Acme", "", catalogue_dir=catalogue_dir,
    )
    assert result["relevant"] is False


def test_real_catalogue_hearing_aids_brief_gets_no_travel_research():
    """The shipped catalogue, against the brief Abel actually reported."""
    result = get_relevant_research(
        "hearing aids", "Boots Hearingcare",
        "Audience is affluent empty-nesters, over-55s, with mild hearing loss",
    )
    assert result["relevant"] is False


def test_real_catalogue_still_admits_an_over_55s_travel_brief():
    result = get_relevant_research(
        "cruises", "P&O Cruises", "Audience is affluent empty-nesters, over-55s",
    )
    assert result["relevant"] is True
    assert result["total_respondents"] == 1589


# ---------------------------------------------------------------------------
# Body lookup for the deck (PRD #131 / slice #134)
#
# The deck download posts the matched-research payload back with the body
# stripped out, so the body is re-read here from the same catalogue.
# ---------------------------------------------------------------------------


def test_body_lookup_returns_the_matched_file_body(catalogue_dir):
    research = get_relevant_research("cruise holiday", "P&O", "", catalogue_dir=catalogue_dir)
    research.pop("prompt_text")  # what the API strips before it reaches the client

    body = load_research_body(research, catalogue_dir=catalogue_dir)

    assert "P&O Cruises led consideration at 38%" in body


def test_body_lookup_prefers_a_body_already_on_the_payload(catalogue_dir):
    """A caller holding the body (the brief run itself) needs no second read."""
    research = {"relevant": True, "file": "travel.md", "prompt_text": "already here"}
    assert load_research_body(research, catalogue_dir=catalogue_dir) == "already here"


def test_body_lookup_is_empty_when_nothing_matched(catalogue_dir):
    assert load_research_body(None) == ""
    assert load_research_body({"relevant": False}) == ""
    assert load_research_body({"relevant": True}, catalogue_dir=catalogue_dir) == ""


def test_body_lookup_is_empty_when_the_file_is_gone(catalogue_dir):
    """A brief saved before a research file was retired must not crash a later
    deck download — it just loses the section."""
    research = {"relevant": True, "file": "retired.md"}
    assert load_research_body(research, catalogue_dir=catalogue_dir) == ""
