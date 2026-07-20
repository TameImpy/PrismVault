import os
import tempfile
import csv

from src.formats import load_format_data, load_format_names

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

