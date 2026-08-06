"""
Tests for the data-provenance registry at src/provenance.py (#156).

The module is pure and file-backed — no LLM, no network — so these tests read
the real `data/provenance.csv` where the question is "does the record cover
what a brief renders?", and a temp CSV where the question is about the
mechanics.
"""
import sys
import os

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import datetime
import re

import pytest

from src.provenance import (
    FIELDS,
    RUN_DATE_TOKEN,
    build_provenance,
    drop_retired_sections,
    format_provenance_block,
    format_provenance_line,
    format_provenance_row,
    load_provenance,
    provenance_for,
)

# Every section of a brief that carries figures. A section missing from the
# registry is a figure a reviewer cannot trace, which is the defect #156 raised.
EXPECTED_SECTIONS = [
    "Advertiser Overview",
    "Client Relationship",
    "Audience Segments & Reach",
    "Recommended Products",
    "Historical Research",
]


def _write_csv(tmp_path, rows):
    """Write a provenance CSV with the canonical header and return its path."""
    path = str(tmp_path / "provenance.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(",".join(FIELDS) + "\n")
        for row in rows:
            f.write(",".join('"%s"' % row.get(k, "") for k in FIELDS) + "\n")
    return path


MATCHED_RESEARCH = {
    "relevant": True,
    "file": "travel_audience_research_2024_25.md",
    "title": "Immediate Media Travel Audience Research 2024/25",
    "organisation": "Immediate Media",
    "fieldwork": "2024-11-26 to 2024-12-02",
    "total_respondents": 1589,
    "matched_on": ["travel"],
}


# ---------------------------------------------------------------------------
# The record itself
# ---------------------------------------------------------------------------


def test_registry_covers_every_data_section():
    """Each data section a brief renders has a provenance row."""
    sections = [e["section"] for e in load_provenance()]
    for expected in EXPECTED_SECTIONS:
        assert expected in sections, "no provenance recorded for %s" % expected


def test_every_row_states_source_coverage_and_period():
    """The four fields #156 asks for are populated on every row.

    `as_at` is exempt for Historical Research alone: its date is the matched
    study's fieldwork, which is per-brief rather than per-registry.
    """
    for entry in load_provenance():
        assert entry["source"], "%s has no source" % entry["section"]
        assert entry["coverage"], "%s has no coverage" % entry["section"]
        assert entry["period"], "%s has no period" % entry["section"]
        assert entry["cadence"], "%s has no refresh cadence" % entry["section"]
        if entry["section"] != "Historical Research":
            assert entry["as_at"], "%s has no as-at date" % entry["section"]


def test_recorded_dates_are_real_past_dates():
    """A declared as-at date parses and is not in the future.

    The registry is hand-maintained alongside the extracts it describes, so the
    cheap failure to catch is a typo or a date nobody updated to a real one.
    """
    today = datetime.date.today()
    for entry in load_provenance():
        as_at = entry["as_at"]
        if not as_at or as_at == RUN_DATE_TOKEN:
            continue
        parsed = datetime.datetime.strptime(as_at, "%Y-%m-%d").date()
        assert parsed <= today, "%s is dated in the future" % entry["section"]


def test_campaign_history_names_the_export_not_the_ad_server():
    """The misread that cost this QA round is named in the record.

    A reviewer reconciled campaign CTR against Google Ad Manager because
    nothing said the figures come from the manual delivery export.
    """
    entry = provenance_for(load_provenance(), "Client Relationship")
    assert "ad server" in entry["source"].lower() or "ad manager" in entry["source"].lower()


def test_the_registry_carries_no_google_trends_row():
    """Google Trends left the product entirely (#176).

    The row is checked for by name rather than only by absence from
    EXPECTED_SECTIONS, because a stray row would be rendered — the builder
    resolves whatever the registry holds — and would tell a reader the brief
    was sourced from something it never queried.
    """
    for entry in load_provenance():
        assert "trends" not in entry["section"].lower()
        assert "trends" not in entry["source"].lower()


def test_the_brief_still_writes_the_headings_the_footers_bind_to():
    """The UI attaches a section's footer by matching the registry's section
    name against the brief's `## ` heading — which the model writes. If a
    prompt edit renames a heading the footer silently vanishes, so the two are
    pinned together here rather than discovered in production.

    Every row is checked: with Google Trends gone (#176) the registry no longer
    holds a section that has no heading of its own.
    """
    from src.prompts import SYSTEM_PROMPT

    for entry in load_provenance():
        assert "## %s" % entry["section"] in SYSTEM_PROMPT, (
            "the brief no longer has a '%s' heading for its provenance footer "
            "to attach to" % entry["section"]
        )


def test_the_uis_hardcoded_section_names_exist_in_the_registry():
    """`lib/provenance.ts` names sections as literals for the surfaces that
    have no markdown heading to read one from. Those literals and this registry
    are two halves of one pair across a language boundary, and a mismatch fails
    silently — the footer just never appears.
    """
    path = os.path.join(PROJECT_ROOT, "frontend", "lib", "provenance.ts")
    with open(path, encoding="utf-8") as f:
        block = f.read().split("PROVENANCE_SECTIONS = {")[1].split("}")[0]

    named = re.findall(r':\s*"([^"]+)"', block)
    assert named, "PROVENANCE_SECTIONS names no sections — has it been renamed?"

    sections = [e["section"] for e in load_provenance()]
    for name in named:
        assert name in sections, (
            "the UI asks for provenance for %r, which the registry does not "
            "carry" % name
        )


def test_missing_registry_degrades_to_nothing(tmp_path):
    """A missing file yields no provenance rather than raising."""
    assert load_provenance(str(tmp_path / "nope.csv")) == []


# ---------------------------------------------------------------------------
# build_provenance()
# ---------------------------------------------------------------------------


def test_live_sources_are_dated_with_the_run_date(tmp_path):
    """The run-date token resolves to the date the brief was generated."""
    path = _write_csv(tmp_path, [
        {"section": "Advertiser Overview", "source": "Live public web search",
         "as_at": RUN_DATE_TOKEN, "coverage": "External to the network",
         "period": "As published", "cadence": "Live"},
    ])
    entries = build_provenance(run_date=datetime.date(2026, 8, 5), csv_path=path)
    assert entries[0]["as_at"] == "2026-08-05"


def test_historical_research_is_the_only_conditional_section(tmp_path):
    """Every row but Historical Research is rendered unconditionally.

    Google Trends used to be conditional too, because the run could decline to
    fetch it (#176 removed the feature and with it the branch). Nothing else
    may acquire that behaviour by accident: an absent source line is how a
    reviewer is told a section was never sourced, and a section that renders
    on an empty result must still say what was searched.
    """
    path = _write_csv(tmp_path, [
        {"section": "Advertiser Overview", "source": "Live public web search",
         "as_at": RUN_DATE_TOKEN, "coverage": "External", "period": "As published",
         "cadence": "Live"},
        {"section": "Recommended Products", "source": "Benchmarking sheet",
         "as_at": "2026-07-20", "coverage": "Whole network", "period": "12 months",
         "cadence": "Monthly"},
    ])
    sections = [e["section"] for e in build_provenance(csv_path=path)]
    assert sections == ["Advertiser Overview", "Recommended Products"]


def test_build_provenance_takes_no_trends_flag():
    """The parameter went with the feature, rather than lingering as a no-op
    that a caller could still pass and believe was doing something."""
    import inspect

    assert "include_google_trends" not in inspect.signature(
        build_provenance).parameters


def test_a_retired_sections_line_is_not_rendered_to_a_client(tmp_path):
    """A brief saved before Google Trends was removed still carries its source
    line (#176). Storage keeps it — the payload is the record of what that run
    did — but the deck appendix and the email footer reach clients, and a
    source line for a section the brief no longer contains describes nothing.
    """
    path = _write_csv(tmp_path, [
        {"section": "Recommended Products", "source": "Benchmarking sheet",
         "as_at": "2026-07-20", "coverage": "Whole network", "period": "12 months",
         "cadence": "Monthly"},
    ])
    legacy = [
        {"section": "Recommended Products", "source": "Benchmarking sheet"},
        {"section": "Google Trends", "source": "Google Trends, queried live"},
    ]
    kept = drop_retired_sections(legacy, csv_path=path)
    assert [e["section"] for e in kept] == ["Recommended Products"]


def test_dropping_retired_sections_leaves_a_current_brief_untouched():
    """Every section of a brief run today survives, in order."""
    entries = build_provenance(historical_research=MATCHED_RESEARCH)
    assert drop_retired_sections(entries) == entries


def test_dropping_retired_sections_passes_an_absent_list_through():
    """A brief saved before provenance existed carries none at all."""
    assert drop_retired_sections(None) is None
    assert drop_retired_sections([]) == []


def test_historical_research_is_dropped_when_nothing_matched():
    """No research section in the brief means no provenance line for it."""
    sections = [e["section"] for e in build_provenance(historical_research=None)]
    assert "Historical Research" not in sections

    sections = [e["section"] for e in build_provenance(
        historical_research={"relevant": False})]
    assert "Historical Research" not in sections


def test_historical_research_provenance_comes_from_the_matched_study():
    """The matched file's own frontmatter dates and sizes the research."""
    entry = provenance_for(
        build_provenance(historical_research=MATCHED_RESEARCH), "Historical Research")

    # The title already leads with the publisher, so it is not named twice.
    assert entry["source"] == "Immediate Media Travel Audience Research 2024/25"
    # Fieldwork is both the period the research covers and how it is dated.
    assert entry["period"] == "Fieldwork 2024-11-26 to 2024-12-02"
    assert entry["as_at"] == "2024-12-02"
    # The base is what stops a percentage being read as a network figure.
    assert "1,589" in entry["coverage"]


def test_a_study_titled_separately_from_its_publisher_names_both():
    entry = provenance_for(build_provenance(historical_research={
        "relevant": True, "title": "Reader Travel Habits", "organisation": "Immediate Media",
        "fieldwork": "2024-12-02", "total_respondents": 100,
    }), "Historical Research")

    assert entry["source"] == "Immediate Media — Reader Travel Habits"


def test_the_deck_facing_record_names_systems_not_repository_paths():
    """The deck's appendix reaches clients, and a reviewer reconciles against
    the export a figure came from — not against a file in the repo."""
    for entry in load_provenance():
        assert ".csv" not in entry["source"], (
            "%s names a file path rather than the system it came from"
            % entry["section"]
        )


def test_research_without_fieldwork_dates_says_so_rather_than_inventing():
    """A study with no fieldwork dates leaves as-at empty, never guessed."""
    entry = provenance_for(build_provenance(historical_research={
        "relevant": True, "title": "Untitled study", "organisation": "Immediate Media",
        "fieldwork": "", "total_respondents": None,
    }), "Historical Research")

    assert entry["as_at"] == ""
    assert entry["period"] == ""


def test_sections_come_back_in_registry_order():
    """Order is the record's order, so the brief and the deck agree."""
    recorded = [e["section"] for e in load_provenance()]
    built = [e["section"] for e in build_provenance(
        historical_research=MATCHED_RESEARCH)]
    assert built == [s for s in recorded if s in built]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_a_line_labels_every_populated_field():
    line = format_provenance_line({
        "section": "Recommended Products", "source": "Benchmarking sheet",
        "as_at": "2026-07-20", "coverage": "Whole network",
        "period": "Rolling 12 months", "cadence": "Monthly",
    })
    for expected in ("Source: Benchmarking sheet", "As at: 2026-07-20",
                     "Coverage: Whole network", "Period: Rolling 12 months",
                     "Refreshed: Monthly"):
        assert expected in line


def test_a_line_omits_fields_with_nothing_behind_them():
    """An absent date is left out, never rendered as an empty label."""
    line = format_provenance_line({
        "section": "Historical Research", "source": "A study", "as_at": "",
        "coverage": "", "period": "", "cadence": "On publication",
    })
    assert "As at:" not in line
    assert "Coverage:" not in line
    assert line.startswith("Source: A study")


def test_a_row_leads_with_the_section_it_describes():
    """The deck appendix and the email footer share this row, so neither can
    describe the same figure differently."""
    row = format_provenance_row({
        "section": "Recommended Products", "source": "Benchmarking sheet",
        "as_at": "2026-07-20", "coverage": "Whole network",
        "period": "Rolling 12 months", "cadence": "Monthly",
    })
    assert row.startswith("Recommended Products — Source: Benchmarking sheet")


def test_a_row_for_nothing_is_nothing():
    """The deck asks for more rows than a brief has; the spare ones blank."""
    assert format_provenance_row(None) == ""
    assert format_provenance_row({}) == ""


def test_a_block_carries_one_labelled_line_per_section():
    block = format_provenance_block(build_provenance(
        historical_research=MATCHED_RESEARCH))
    for section in EXPECTED_SECTIONS:
        assert section in block
    # One line per section (plus the heading), never one per figure.
    body = [ln for ln in block.splitlines() if ln.strip().startswith("Advertiser Overview")]
    assert len(body) == 1


def test_an_empty_block_renders_as_nothing():
    assert format_provenance_block([]) == ""


def test_provenance_for_returns_none_when_a_section_is_absent():
    assert provenance_for([], "Recommended Products") is None
    assert provenance_for(None, "Recommended Products") is None
