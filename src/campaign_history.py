import csv
import os

from src.entity_resolution import resolve

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "campaign_history.csv")

# Scoped to "direct": the dataset is direct-only, so we never claim to know
# about programmatic activity and never assert "we've never advertised".
NO_DATA_MESSAGE = "No direct campaign history with this advertiser."


def _no_match_result():
    # type: () -> dict
    return {
        "summary": NO_DATA_MESSAGE,
        "campaigns": [],
        "status": "no_match",
        "matched_name": None,
    }


def get_campaign_summary(advertiser, csv_path=None):
    # type: (str, str) -> dict
    """Look up an advertiser's campaign history and return a summary.

    Resolution is deterministic (see ``src.entity_resolution``): the queried
    advertiser is matched against the roster of canonical advertiser names,
    never by crude substring. Returns a dict with:
        summary (str): prompt-ready formatted summary
        campaigns (list): raw campaign records (one per campaign ID)
        status (str): "match" or "no_match"
        matched_name (str|None): the canonical roster name on a match
    """
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH

    if not os.path.exists(csv_path):
        return _no_match_result()

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return _no_match_result()

    # Resolve the queried advertiser against the roster of canonical names.
    roster = sorted({r.get("advertiser", "") for r in rows if r.get("advertiser")})
    resolution = resolve(advertiser, roster)

    if resolution["status"] != "match":
        return _no_match_result()

    matched_name = resolution["matched_name"]
    matched = [r for r in rows if r.get("advertiser", "") == matched_name]

    # Aggregate by campaign_id to avoid counting individual placements
    campaigns = {}
    for row in matched:
        cid = row.get("campaign_id", "")
        impressions = int(row.get("impressions", 0) or 0)
        clicks = int(row.get("clicks", 0) or 0)

        if cid in campaigns:
            campaigns[cid]["impressions"] += impressions
            campaigns[cid]["clicks"] += clicks
        else:
            campaigns[cid] = {
                "campaign_id": cid,
                "campaign_name": row.get("campaign_name", "Unknown"),
                "category": row.get("category", "Unknown"),
                "start_date": row.get("start_date", "Unknown"),
                "impressions": impressions,
                "clicks": clicks,
            }

    campaign_list = list(campaigns.values())

    # Compute aggregates
    total_impressions = sum(c["impressions"] for c in campaign_list)
    total_clicks = sum(c["clicks"] for c in campaign_list)
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0

    categories = sorted(set(c["category"] for c in campaign_list if c["category"] != "Unknown"))

    # Most recent campaign
    most_recent = max(campaign_list, key=lambda c: c["start_date"])

    # Best campaign by CTR (impressions as tiebreaker)
    def _ctr_sort_key(c):
        ctr = (c["clicks"] / c["impressions"] * 100) if c["impressions"] > 0 else 0.0
        return (ctr, c["impressions"])

    best = max(campaign_list, key=_ctr_sort_key)
    best_ctr = (best["clicks"] / best["impressions"] * 100) if best["impressions"] > 0 else 0.0

    # Format summary
    summary_lines = [
        "Direct campaign history for '%s':" % matched_name,
        "- Total campaigns: %d" % len(campaign_list),
        "- Categories: %s" % (", ".join(categories) if categories else "N/A"),
        "- Total impressions: %s" % _format_number(total_impressions),
        "- Average CTR: %.2f%%" % avg_ctr,
        "- Most recent campaign: %s (%s)" % (most_recent["campaign_name"], most_recent["start_date"]),
        "- Best performing: %s (%.2f%% CTR, %s impressions)" % (
            best["campaign_name"], best_ctr, _format_number(best["impressions"])
        ),
    ]

    return {
        "summary": "\n".join(summary_lines),
        "campaigns": campaign_list,
        "status": "match",
        "matched_name": matched_name,
    }


def _format_number(n):
    # type: (int) -> str
    """Format a large number with commas for readability."""
    if n >= 1000000:
        return "%.1fM" % (n / 1000000.0)
    if n >= 1000:
        return "%.1fK" % (n / 1000.0)
    return str(n)
