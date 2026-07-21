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
        "candidates": [],
    }


def _aggregate_campaigns(rows):
    # type: (list) -> list
    """Aggregate rows for a single brand by campaign_id into campaign records."""
    campaigns = {}
    for row in rows:
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
    return list(campaigns.values())


def _best_campaign(campaign_list):
    # type: (list) -> tuple
    """Return (best_campaign, best_ctr) by CTR, impressions as tiebreaker."""
    def _ctr_sort_key(c):
        ctr = (c["clicks"] / c["impressions"] * 100) if c["impressions"] > 0 else 0.0
        return (ctr, c["impressions"])

    best = max(campaign_list, key=_ctr_sort_key)
    best_ctr = (best["clicks"] / best["impressions"] * 100) if best["impressions"] > 0 else 0.0
    return best, best_ctr


def _summarise_brand(brand_name, campaign_list, header=None):
    # type: (str, list, str) -> str
    """Produce a prompt-ready summary block for one brand's campaigns."""
    total_impressions = sum(c["impressions"] for c in campaign_list)
    total_clicks = sum(c["clicks"] for c in campaign_list)
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0

    categories = sorted(set(c["category"] for c in campaign_list if c["category"] != "Unknown"))
    most_recent = max(campaign_list, key=lambda c: c["start_date"])
    best, best_ctr = _best_campaign(campaign_list)

    if header is None:
        header = "Direct campaign history for '%s':" % brand_name

    return "\n".join([
        header,
        "- Total campaigns: %d" % len(campaign_list),
        "- Categories: %s" % (", ".join(categories) if categories else "N/A"),
        "- Total impressions: %s" % _format_number(total_impressions),
        "- Average CTR: %.2f%%" % avg_ctr,
        "- Most recent campaign: %s (%s)" % (most_recent["campaign_name"], most_recent["start_date"]),
        "- Best performing: %s (%.2f%% CTR, %s impressions)" % (
            best["campaign_name"], best_ctr, _format_number(best["impressions"])
        ),
    ])


def get_campaign_summary(advertiser, csv_path=None):
    # type: (str, str) -> dict
    """Look up an advertiser's campaign history and return a summary.

    Resolution is deterministic (see ``src.entity_resolution``): the queried
    advertiser is matched against the roster of canonical advertiser names,
    never by crude substring. Returns a dict with:
        summary (str): prompt-ready formatted summary
        campaigns (list): raw campaign records (one per campaign ID)
        status (str): "match", "possible_match", or "no_match"
        matched_name (str|None): the canonical roster name on a confident match
        candidates (list): names to verify, on a possible_match
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
    status = resolution["status"]

    if status == "no_match":
        return _no_match_result()

    if status == "possible_match":
        return _possible_match_result(resolution["candidates"], rows)

    # Confident match.
    matched_name = resolution["matched_name"]
    matched = [r for r in rows if r.get("advertiser", "") == matched_name]
    campaign_list = _aggregate_campaigns(matched)

    return {
        "summary": _summarise_brand(matched_name, campaign_list),
        "campaigns": campaign_list,
        "status": "match",
        "matched_name": matched_name,
        "candidates": [],
    }


def _possible_match_result(candidates, rows):
    # type: (list, list) -> dict
    """Render the ambiguous state: a ⚠ verify callout naming each candidate
    with its history, asserting no confirmed relationship. Comparables are
    suppressed for this state (handled downstream)."""
    blocks = [
        "⚠ POSSIBLE MATCH — VERIFY BEFORE CLAIMING A RELATIONSHIP.",
        "The queried advertiser is ambiguous. We are not asserting a direct "
        "relationship. These roster brands are possible matches — confirm which "
        "(if any) is the client before referencing any history:",
    ]
    for candidate in candidates:
        candidate_rows = [r for r in rows if r.get("advertiser", "") == candidate]
        campaign_list = _aggregate_campaigns(candidate_rows)
        if campaign_list:
            blocks.append(
                _summarise_brand(
                    candidate, campaign_list,
                    header="Candidate '%s' (direct history — unverified):" % candidate,
                )
            )
        else:
            blocks.append("Candidate '%s': no direct campaign history on record." % candidate)

    return {
        "summary": "\n\n".join(blocks),
        "campaigns": [],
        "status": "possible_match",
        "matched_name": None,
        "candidates": list(candidates),
    }


def _format_number(n):
    # type: (int) -> str
    """Format a large number with commas for readability."""
    if n >= 1000000:
        return "%.1fM" % (n / 1000000.0)
    if n >= 1000:
        return "%.1fK" % (n / 1000.0)
    return str(n)
