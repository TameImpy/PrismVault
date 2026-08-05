import os
import re
import tempfile
import csv

from src.formats import (
    load_format_data,
    load_format_names,
    load_format_rows,
    validate_format_names,
)

# V2 schema: `When to use this` and `avoid_when` are dropped; all other columns retained.
V2_FIELDNAMES = [
    "Format", "format_family", "CTR avg", "Viewability", "Metric mapping",
    "Indicative cost", "Creative complexity", "primary_objective",
    "secondary_objective", "best_for_brief", "best_for_advertiser_type",
    "video_asset_needed", "strong_mobile_fit", "premium_impact",
    "storytelling_strength", "Source page",
]


def _row(**overrides):
    """Build a V2 row with sensible defaults, overriding named fields."""
    base = {name: "" for name in V2_FIELDNAMES}
    base.update(overrides)
    return base


def _create_test_csv(path):
    """Create a minimal V2-schema CSV: one digital row (benchmarks),
    one non-digital row (blank benchmarks), and one row whose name carries a
    trailing space (the `Masthead ` data-hygiene case)."""
    rows = [
        _row(
            Format="Standard display - Mobile Banner",
            format_family="Standard display",
            **{"CTR avg": "0.08%"},
            Viewability="72.49%",
            **{"Indicative cost": "Low"},
            primary_objective="Reach",
            secondary_objective="Awareness",
            best_for_brief="Mobile-heavy campaigns needing efficient reach",
            best_for_advertiser_type="Performance-led or budget-conscious advertisers",
        ),
        _row(
            Format="Host Read",
            format_family="Podcast",
            **{"Indicative cost": "Medium"},
            primary_objective="Awareness",
            secondary_objective="Consideration",
            best_for_brief="Podcast campaigns needing authentic host endorsement",
            best_for_advertiser_type="Advertisers comfortable with host-led messaging",
        ),
        _row(
            Format="Masthead ",
            format_family="Impact Display",
            **{"Indicative cost": "Medium"},
            primary_objective="Awareness",
            secondary_objective="Reach",
            best_for_brief="High-impact branding with simple creative",
            best_for_advertiser_type="Advertisers seeking standout awareness",
        ),
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=V2_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def test_load_format_names_returns_exact_catalogue_names():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        names = load_format_names(csv_path)

        # Exact names, in file order, with the trailing-space name normalised.
        assert names == [
            "Standard display - Mobile Banner",
            "Host Read",
            "Masthead",
        ]


def test_load_format_data_returns_format_names_and_metrics():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        result = load_format_data(csv_path)

        assert "Standard display - Mobile Banner" in result
        assert "0.08%" in result
        assert "72.49%" in result


def test_load_format_data_blank_benchmarks_render_not_available_wording():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        result = load_format_data(csv_path)

        # Non-digital rows (Host Read) have blank CTR/viewability. They must
        # read as a plain-English note, never a blank or "N/A".
        assert "benchmarks not currently available for this specific format" in result

        # The note stands in for the Host Read metrics specifically.
        host_block = [b for b in result.split("\n\n") if b.startswith("Host Read")][0]
        assert "benchmarks not currently available for this specific format" in host_block
        assert "N/A" not in host_block

        # The digital row keeps its real benchmarks, not the note.
        display_block = [
            b for b in result.split("\n\n")
            if b.startswith("Standard display - Mobile Banner")
        ][0]
        assert "0.08%" in display_block
        assert "72.49%" in display_block
        assert "benchmarks not currently available" not in display_block


def test_load_format_data_omits_removed_when_to_use_column():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        result = load_format_data(csv_path)

        # `When to use this` was dropped from the V2 schema; the loader must
        # not emit a when-to-use line.
        assert "When to use" not in result


def test_load_format_data_missing_csv_returns_fallback():
    result = load_format_data("/nonexistent/path/format_recommendations.csv")

    assert "No format recommendation data available" in result


# ---------------------------------------------------------------------------
# load_format_names — missing / empty file
# ---------------------------------------------------------------------------

def test_load_format_names_missing_file_returns_empty_list():
    names = load_format_names("/nonexistent/path/format_recommendations.csv")

    assert names == []


def test_load_format_names_header_only_csv_returns_empty_list():
    """A file with headers but no data rows must return [], not crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=V2_FIELDNAMES)
            writer.writeheader()

        names = load_format_names(csv_path)

        assert names == []


# ---------------------------------------------------------------------------
# load_format_data — empty file
# ---------------------------------------------------------------------------

def test_load_format_data_header_only_csv_returns_fallback():
    """A CSV with headers but no data rows must return the fallback string."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=V2_FIELDNAMES)
            writer.writeheader()

        result = load_format_data(csv_path)

        assert "No format recommendation data available" in result


# ---------------------------------------------------------------------------
# Partial benchmarks — only one of CTR avg / Viewability present
# ---------------------------------------------------------------------------

def test_load_format_data_only_ctr_no_viewability_renders_not_available():
    """A row with CTR but no Viewability must use the plain-English note,
    not partial benchmark data. The `if ctr and viewability` guard ensures
    this; this test pins that behaviour explicitly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        rows = [
            _row(
                Format="Partial Benchmark Format",
                format_family="Standard display",
                **{"CTR avg": "0.05%"},
                # Viewability intentionally left blank
                primary_objective="Reach",
            ),
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=V2_FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        result = load_format_data(csv_path)

        assert "benchmarks not currently available for this specific format" in result
        # The partial CTR value must not leak through as a standalone line.
        assert "CTR avg: 0.05%" not in result


def test_load_format_data_only_viewability_no_ctr_renders_not_available():
    """A row with Viewability but no CTR must also use the plain-English note."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        rows = [
            _row(
                Format="Viewability Only Format",
                format_family="Standard display",
                # CTR avg intentionally left blank
                Viewability="68.00%",
                primary_objective="Reach",
            ),
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=V2_FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        result = load_format_data(csv_path)

        assert "benchmarks not currently available for this specific format" in result
        assert "Viewability: 68.00%" not in result


# ---------------------------------------------------------------------------
# Whitespace stripping — format name in load_format_data
# ---------------------------------------------------------------------------

def test_load_format_data_strips_format_name_whitespace():
    """The name rendered in the output block must be stripped, matching the
    same hygiene applied in load_format_names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        result = load_format_data(csv_path)

        # Masthead has a trailing space in the CSV; the output block heading
        # must be the stripped form.
        assert "Masthead\n" in result or result.endswith("Masthead")
        assert "Masthead \n" not in result


# ---------------------------------------------------------------------------
# load_format_names — ordering and blank-name filtering
# ---------------------------------------------------------------------------

def test_load_format_names_preserves_file_order():
    """Names must come back in exactly the order they appear in the CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        rows = [
            _row(Format="Format Z"),
            _row(Format="Format A"),
            _row(Format="Format M"),
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=V2_FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        names = load_format_names(csv_path)

        assert names == ["Format Z", "Format A", "Format M"]


def test_load_format_names_skips_rows_with_blank_format_cell():
    """Rows where the Format cell is empty (or whitespace-only) must be
    excluded from the returned list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        rows = [
            _row(Format="Valid Format"),
            _row(Format=""),          # blank — should be skipped
            _row(Format="   "),       # whitespace-only — should be skipped
            _row(Format="Another Valid"),
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=V2_FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        names = load_format_names(csv_path)

        assert names == ["Valid Format", "Another Valid"]


# ---------------------------------------------------------------------------
# validate_format_names — pure, deterministic name-validation guardrail (#94)
# ---------------------------------------------------------------------------

VALID_NAMES = [
    "Standard display - Mobile Banner",
    "Host Read",
    "Gatefold (General)",
    "Masthead",
]


def test_validate_format_names_recognises_in_catalogue_names():
    content = (
        "## Recommended Products\n"
        "- **Standard display - Mobile Banner** — CTR average 0.08%, "
        "Viewability 72.49%, Primary objective: Reach\n"
        "- **Host Read** — benchmarks not currently available for this "
        "specific format, Primary objective: Awareness\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    assert "Standard display - Mobile Banner" in result["recognised"]
    assert "Host Read" in result["recognised"]
    assert result["unrecognised"] == []


def test_validate_format_names_flags_off_catalogue_names():
    content = (
        "## Recommended Products\n"
        "- **Standard display - Mobile Banner** — CTR average 0.08%\n"
        "- **Premium Mega Skin** — CTR average 3.10%, Primary objective: Awareness\n"
        "\n"
        "**Combined rationale:** For Acme this set balances reach and impact.\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    # The real product is recognised; the hallucinated one is flagged.
    assert "Standard display - Mobile Banner" in result["recognised"]
    assert "Premium Mega Skin" in result["unrecognised"]
    # The closing rationale line is not a recommendation entry and must not be flagged.
    assert "Combined rationale" not in result["unrecognised"]


# ---------------------------------------------------------------------------
# validate_format_names — edge cases for the guardrail (#94)
# ---------------------------------------------------------------------------

def test_validate_format_names_numbered_list_items_extracted():
    """List items starting with '1.' and '2)' must be treated as recommendation
    entries just like bullet points."""
    content = (
        "## Recommended Products\n"
        "1. **Host Read** — benchmarks not currently available\n"
        "2) **Ghost Format** — CTR average 1.00%\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    assert "Host Read" in result["recognised"]
    assert "Ghost Format" in result["unrecognised"]


def test_validate_format_names_renamed_real_product_flagged_as_unrecognised():
    """A name that is merely similar to a catalogue name ('Mastheads' vs
    'Masthead') must be flagged as unrecognised — partial similarity is not
    a match on the candidate side.

    Note: 'Masthead' IS in the recognised list because validate_format_names
    uses a substring scan for the recognised set (checking whether the catalogue
    name appears anywhere in the content). 'Mastheads' as a list-entry bold span
    does not match 'masthead' in valid_lookup, so it must also appear in
    unrecognised."""
    content = (
        "## Recommended Products\n"
        "- **Mastheads** — CTR average 2.00%, Primary objective: Awareness\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    assert "Mastheads" in result["unrecognised"]


def test_validate_format_names_name_with_parentheses_not_flagged():
    """A real catalogue name containing parentheses like 'Gatefold (General)'
    must NOT appear in unrecognised when it is in valid_names."""
    content = (
        "## Recommended Products\n"
        "- **Gatefold (General)** — CTR average 0.50%, Primary objective: Reach\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    assert "Gatefold (General)" in result["recognised"]
    assert "Gatefold (General)" not in result["unrecognised"]


def test_validate_format_names_duplicate_unrecognised_listed_only_once():
    """The same unrecognised name appearing in multiple list items must only
    appear once in the unrecognised list."""
    content = (
        "## Recommended Products\n"
        "- **Mystery Format** — CTR average 0.80%\n"
        "- **Mystery Format** — repeated again for some reason\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    assert result["unrecognised"].count("Mystery Format") == 1


def test_validate_format_names_no_list_items_returns_empty_unrecognised():
    """Content with no list items at all (headings, prose, bold labels) must
    return an empty unrecognised list."""
    content = (
        "## Recommended Products\n"
        "**Combined rationale:** This advertiser would benefit from Host Read.\n"
        "See the full format catalogue for more options.\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    assert result["unrecognised"] == []


def test_validate_format_names_empty_content_returns_empty_results():
    """Passing an empty string must not crash and must return empty lists."""
    result = validate_format_names("", VALID_NAMES)

    assert result == {"recognised": [], "recommended": [], "unrecognised": []}


def test_validate_format_names_whitespace_only_content_returns_empty_results():
    """Whitespace-only content must not crash and must return empty lists."""
    result = validate_format_names("   \n\n  \t  ", VALID_NAMES)

    assert result == {"recognised": [], "recommended": [], "unrecognised": []}


def test_validate_format_names_bold_label_on_non_list_line_not_flagged():
    """A bold span like '**Combined rationale:**' that appears on a non-list
    line (no leading list marker) must never be flagged as an unrecognised
    format name."""
    content = (
        "## Recommended Products\n"
        "- **Host Read** — benchmarks not currently available\n"
        "\n"
        "**Combined rationale:** These formats suit the brief.\n"
        "**Note:** All names are from the catalogue.\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    assert "Combined rationale" not in result["unrecognised"]
    assert "Note" not in result["unrecognised"]


def test_validate_format_names_bullet_variants_all_extracted():
    """The three bullet variants (-, *, •) must all be treated as list markers."""
    content = (
        "- **Host Read** — bullet dash\n"
        "* **Fake Alpha** — bullet asterisk\n"
        "• **Fake Beta** — bullet point\n"
    )

    result = validate_format_names(content, VALID_NAMES)

    assert "Host Read" in result["recognised"]
    assert "Fake Alpha" in result["unrecognised"]
    assert "Fake Beta" in result["unrecognised"]


def test_validate_format_names_empty_valid_names_everything_unrecognised():
    """With an empty catalogue every bold list-entry name is unrecognised and
    the recognised list is empty."""
    content = (
        "- **Host Read** — some description\n"
        "- **Masthead** — some description\n"
    )

    result = validate_format_names(content, [])

    assert result["recognised"] == []
    assert "Host Read" in result["unrecognised"]
    assert "Masthead" in result["unrecognised"]


# ---------------------------------------------------------------------------
# load_format_rows — structured catalogue for the deck payload (PRD #131 / #133)
# ---------------------------------------------------------------------------

def test_load_format_rows_returns_structured_rows_with_verbatim_metrics():
    """Rows carry CTR and viewability exactly as the CSV holds them, so the
    deck can place them without re-deriving anything from prose."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        rows = load_format_rows(csv_path)

        assert [r["format"] for r in rows] == [
            "Standard display - Mobile Banner",
            "Host Read",
            "Masthead",
        ]
        display = rows[0]
        assert display["ctr"] == "0.08%"
        assert display["viewability"] == "72.49%"
        assert display["format_family"] == "Standard display"
        assert display["primary_objective"] == "Reach"


def test_load_format_rows_blank_benchmarks_stay_empty_strings():
    """Non-digital rows have no benchmarks. Structured data says so with an
    empty string — the plain-English note is a prose concern, not a data one."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        rows = load_format_rows(csv_path)
        host_read = [r for r in rows if r["format"] == "Host Read"][0]

        assert host_read["ctr"] == ""
        assert host_read["viewability"] == ""
        assert "benchmarks not currently available" not in str(host_read)


def test_load_format_rows_missing_csv_returns_empty_list():
    rows = load_format_rows("/nonexistent/path/format_recommendations.csv")

    assert rows == []


def test_load_format_rows_header_only_csv_returns_empty_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=V2_FIELDNAMES)
            writer.writeheader()

        assert load_format_rows(csv_path) == []


def test_load_format_rows_is_json_serialisable():
    """The rows travel to the browser and back in the deck-download request."""
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        rows = load_format_rows(csv_path)

        assert json.loads(json.dumps(rows)) == rows


# ---------------------------------------------------------------------------
# validate_format_names — `recommended`: the selection signal for the deck
#
# `recognised` is a lenient substring scan, right for "did the model invent a
# name?". Choosing which products go on a slide needs the stricter reading:
# names actually presented as recommendation entries (PRD #131 / #133).
# ---------------------------------------------------------------------------

RECOMMENDATION_BRIEF = (
    "## Recommended Products\n"
    "- **Standard display - Mobile Banner** — efficient mobile reach\n"
    "- **Host Read** — authentic podcast endorsement\n"
)


def test_recommended_excludes_names_only_mentioned_in_prose():
    """"Podcast" is a catalogue format, but here the word only appears inside
    another entry's description. It must not be selected as a product."""
    valid = ["Standard display - Mobile Banner", "Host Read", "Podcast"]

    result = validate_format_names(RECOMMENDATION_BRIEF, valid)

    assert result["recommended"] == ["Standard display - Mobile Banner", "Host Read"]
    # The lenient scan still sees it — the two answer different questions.
    assert "Podcast" in result["recognised"]


def test_recommended_preserves_catalogue_casing_not_the_brief_s():
    """The deck joins on these names, so they must match the catalogue exactly."""
    content = "- **standard display - MOBILE banner** — reach\n"

    result = validate_format_names(content, ["Standard display - Mobile Banner"])

    assert result["recommended"] == ["Standard display - Mobile Banner"]


def test_recommended_lists_each_format_once_in_presentation_order():
    content = (
        "- **Host Read** — first\n"
        "- **Standard display - Mobile Banner** — second\n"
        "- **Host Read** — repeated\n"
    )

    result = validate_format_names(content, ["Standard display - Mobile Banner", "Host Read"])

    assert result["recommended"] == ["Host Read", "Standard display - Mobile Banner"]


def test_recommended_is_empty_when_the_brief_names_no_confirmed_format():
    """Better an empty product slide than a wrong one."""
    content = "- **Totally Fake Format 9000** — invented\n"

    result = validate_format_names(content, ["Host Read"])

    assert result["recommended"] == []
    assert result["unrecognised"] == ["Totally Fake Format 9000"]


# --- Selection rationale (#163) -------------------------------------------
#
# The reason a format was recommended already existed in the catalogue as
# `best_for_brief`; #163 is about it reaching the screen. Nothing here derives
# a reason — these guard the two ways the surfacing can silently break.

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_catalogue_format_can_say_what_it_suits():
    """A recommendation with no reason is the state #163 was raised about, so
    the catalogue is checked for gaps here rather than discovered as a blank
    line under a format name in a client-facing brief."""
    rows = load_format_rows()
    assert rows, "the real format catalogue is empty — has the CSV moved?"

    missing = [row["format"] for row in rows if not row["best_for_brief"].strip()]
    assert not missing, (
        "these catalogue formats have no best_for_brief, so they would be "
        "recommended with no reason shown: %s" % ", ".join(missing)
    )


def test_the_brief_still_writes_the_heading_the_format_reasons_bind_to():
    """The UI attaches the format reasons to the brief's "Recommended Products"
    section by matching a literal in `lib/formatRecommendations.ts` against a
    `## ` heading the model writes. Rename either half and the reasons vanish
    with no error, so the two are pinned together across the language boundary.
    """
    from src.prompts import SYSTEM_PROMPT

    path = os.path.join(PROJECT_ROOT, "frontend", "lib", "formatRecommendations.ts")
    with open(path, encoding="utf-8") as f:
        source = f.read()

    match = re.search(r'RECOMMENDED_PRODUCTS_SECTION = "([^"]+)"', source)
    assert match, "RECOMMENDED_PRODUCTS_SECTION is gone — has it been renamed?"

    heading = match.group(1)
    assert "## %s" % heading in SYSTEM_PROMPT, (
        "the brief no longer has a '%s' heading for the format reasons to "
        "attach to" % heading
    )
