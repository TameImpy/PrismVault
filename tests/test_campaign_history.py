import os
import tempfile
import csv

from src.campaign_history import get_campaign_summary, NO_DATA_MESSAGE


def _create_test_csv(path, rows=None):
    """Create a campaign history CSV with the expected columns."""
    if rows is None:
        rows = [
            {
                "advertiser": "Tesco",
                "campaign_name": "Tesco Easter",
                "campaign_id": "100",
                "category": "Supermarket",
                "start_date": "2024-04-01",
                "impressions": "5000000",
                "clicks": "10000",
            },
            {
                "advertiser": "Tesco",
                "campaign_name": "Tesco Summer",
                "campaign_id": "101",
                "category": "Food",
                "start_date": "2024-07-01",
                "impressions": "3000000",
                "clicks": "9000",
            },
            {
                "advertiser": "Jaguar Landrover",
                "campaign_name": "JLR Launch",
                "campaign_id": "200",
                "category": "Motoring",
                "start_date": "2025-01-01",
                "impressions": "2000000",
                "clicks": "8000",
            },
            {
                "advertiser": "Aldi",
                "campaign_name": "Aldi Christmas",
                "campaign_id": "300",
                "category": "Supermarket",
                "start_date": "2024-12-01",
                "impressions": "4000000",
                "clicks": "6000",
            },
        ]
    fieldnames = ["advertiser", "campaign_name", "campaign_id", "category",
                  "start_date", "impressions", "clicks"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_exact_match_returns_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("Tesco", csv_path)

        assert "Tesco" in result["summary"]
        assert "Total campaigns: 2" in result["summary"]
        assert len(result["campaigns"]) == 2


def test_substring_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("Jaguar", csv_path)

        assert "JLR Launch" in result["summary"]
        assert len(result["campaigns"]) == 1


def test_case_insensitive_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("tesco", csv_path)

        assert "Total campaigns: 2" in result["summary"]
        assert len(result["campaigns"]) == 2


def test_no_match_returns_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("NonExistentBrand", csv_path)

        assert result["summary"] == NO_DATA_MESSAGE
        assert result["campaigns"] == []


def test_missing_csv_returns_fallback():
    result = get_campaign_summary("Tesco", "/nonexistent/path/campaigns.csv")

    assert result["summary"] == NO_DATA_MESSAGE
    assert result["campaigns"] == []


def test_empty_csv_returns_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path, rows=[])

        result = get_campaign_summary("Tesco", csv_path)

        assert result["summary"] == NO_DATA_MESSAGE
        assert result["campaigns"] == []


def test_aggregates_by_campaign_id():
    """Multiple rows with same campaign_id should be aggregated into one campaign."""
    rows = [
        {
            "advertiser": "Tesco",
            "campaign_name": "Tesco Easter",
            "campaign_id": "100",
            "category": "Supermarket",
            "start_date": "2024-04-01",
            "impressions": "3000000",
            "clicks": "6000",
        },
        {
            "advertiser": "Tesco",
            "campaign_name": "Tesco Easter",
            "campaign_id": "100",
            "category": "Supermarket",
            "start_date": "2024-04-01",
            "impressions": "2000000",
            "clicks": "4000",
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path, rows=rows)

        result = get_campaign_summary("Tesco", csv_path)

        assert "Total campaigns: 1" in result["summary"]
        assert len(result["campaigns"]) == 1
        assert result["campaigns"][0]["impressions"] == 5000000
        assert result["campaigns"][0]["clicks"] == 10000


def test_ctr_calculation():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("Tesco", csv_path)

        # Tesco: 8M impressions, 19K clicks = 0.24% CTR
        assert "Average CTR: 0.24%" in result["summary"]


def test_categories_in_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("Tesco", csv_path)

        assert "Food" in result["summary"]
        assert "Supermarket" in result["summary"]


def test_most_recent_campaign():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("Tesco", csv_path)

        assert "Tesco Summer" in result["summary"]
        assert "2024-07-01" in result["summary"]


def test_best_performing_campaign():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("Tesco", csv_path)

        # Tesco Summer: 9000/3000000 = 0.30% CTR (higher than Easter 0.20%)
        assert "Best performing: Tesco Summer" in result["summary"]
