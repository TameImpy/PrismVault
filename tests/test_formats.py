import os
import tempfile
import csv

from src.formats import load_format_data


def _create_test_csv(path):
    """Create a minimal CSV with the expected columns."""
    rows = [
        {
            "Format": "Standard display - Mobile Banner",
            "format_family": "Standard display",
            "CTR avg": "0.08%",
            "Viewability": "72.49%",
            "Indicative cost": "Low",
            "primary_objective": "Reach",
            "secondary_objective": "Awareness",
            "best_for_brief": "Mobile-heavy campaigns needing efficient reach",
            "best_for_advertiser_type": "Performance-led or budget-conscious advertisers",
            "When to use this": "Use for efficient reach, simple messaging, and campaigns where broad coverage matters.",
        },
        {
            "Format": "Infinity skin - core",
            "format_family": "Infinity desktop",
            "CTR avg": "2.21%",
            "Viewability": "85.82%",
            "Indicative cost": "High",
            "primary_objective": "Awareness",
            "secondary_objective": "Consideration",
            "best_for_brief": "Premium desktop storytelling",
            "best_for_advertiser_type": "Premium brands, launches",
            "When to use this": "Use when the advertiser wants a premium, immersive desktop execution.",
        },
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_load_format_data_returns_format_names_and_metrics():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "format_recommendations.csv")
        _create_test_csv(csv_path)

        result = load_format_data(csv_path)

        assert "Standard display - Mobile Banner" in result
        assert "Infinity skin - core" in result
        assert "0.08%" in result
        assert "2.21%" in result
        assert "72.49%" in result
        assert "85.82%" in result
        assert "Low" in result
        assert "High" in result


def test_load_format_data_missing_csv_returns_fallback():
    result = load_format_data("/nonexistent/path/format_recommendations.csv")

    assert "No format recommendation data available" in result
