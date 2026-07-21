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


def test_match_exposes_status_and_matched_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path)

        result = get_campaign_summary("Tesco", csv_path)

        assert result["status"] == "match"
        assert result["matched_name"] == "Tesco"


def test_substring_false_positive_now_no_match():
    """The old substring match returned Skyscanner for "Sky"; the resolver
    must not — "Sky" shares no whole token with "Skyscanner"."""
    rows = [
        {
            "advertiser": "Skyscanner",
            "campaign_name": "Skyscanner Summer",
            "campaign_id": "500",
            "category": "Travel",
            "start_date": "2025-05-01",
            "impressions": "1000000",
            "clicks": "2000",
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path, rows=rows)

        result = get_campaign_summary("Sky", csv_path)

        assert result["status"] == "no_match"
        assert result["campaigns"] == []
        assert result["summary"] == NO_DATA_MESSAGE


def test_possible_match_renders_verify_callout():
    """An ambiguous query flags candidates to verify, asserts nothing, and
    shows each candidate's history."""
    rows = [
        {
            "advertiser": "Virgin Media",
            "campaign_name": "VM Broadband",
            "campaign_id": "600",
            "category": "Tech",
            "start_date": "2025-03-01",
            "impressions": "2000000",
            "clicks": "5000",
        },
        {
            "advertiser": "Virgin Atlantic",
            "campaign_name": "VA Summer",
            "campaign_id": "601",
            "category": "Travel",
            "start_date": "2025-06-01",
            "impressions": "1500000",
            "clicks": "3000",
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path, rows=rows)

        result = get_campaign_summary("Virgin", csv_path)

        assert result["status"] == "possible_match"
        assert result["matched_name"] is None
        # Both candidates are named for the salesperson to verify.
        assert "Virgin Media" in result["summary"]
        assert "Virgin Atlantic" in result["summary"]
        # The callout is clearly a verify prompt, not an assertion.
        assert "verify" in result["summary"].lower()
        assert "⚠" in result["summary"]
        # Candidates are exposed structurally too.
        assert set(result["candidates"]) == {"Virgin Media", "Virgin Atlantic"}


def test_no_direct_wording_on_no_match():
    """No-match wording is scoped to 'direct', never an absolute claim."""
    assert "direct" in NO_DATA_MESSAGE.lower()
    assert "never" not in NO_DATA_MESSAGE.lower()


def test_alias_hit_resolves_in_campaign_summary():
    """A supplied alias maps a query to its canonical roster brand."""
    rows = [
        {
            "advertiser": "Coca-Cola",
            "campaign_name": "Coke Summer",
            "campaign_id": "700",
            "category": "Food",
            "start_date": "2025-05-01",
            "impressions": "3000000",
            "clicks": "9000",
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        _create_test_csv(csv_path, rows=rows)

        result = get_campaign_summary("Coke", csv_path, aliases={"coke": "Coca-Cola"})

        assert result["status"] == "match"
        assert result["matched_name"] == "Coca-Cola"


def test_no_match_is_logged_when_log_path_given():
    """A genuine miss is appended to the unmatched-brand growth log."""
    import csv as _csv
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        log_path = os.path.join(tmpdir, "unmatched.csv")
        _create_test_csv(csv_path)

        get_campaign_summary("TotallyUnknownBrand", csv_path, log_path=log_path)

        assert os.path.exists(log_path)
        with open(log_path, newline="") as f:
            logged = list(_csv.DictReader(f))
        assert any(r["queried_brand"] == "TotallyUnknownBrand"
                   and r["status"] == "no_match" for r in logged)


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
