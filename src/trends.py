from typing import Optional

from pytrends.request import TrendReq


def _fetch_interest(pytrends: TrendReq, keywords: list, timeframe: str) -> Optional[dict]:
    """Fetch interest_over_time for keywords in a given timeframe.

    Returns None on failure rather than raising.
    """
    try:
        pytrends.build_payload(keywords, timeframe=timeframe)
        df = pytrends.interest_over_time()
        if df.empty:
            return None
        return df
    except Exception:
        return None


def _get_related_queries(pytrends: TrendReq, topic: str) -> list:
    """Fetch rising and top related queries for the topic."""
    try:
        pytrends.build_payload([topic], timeframe="today 12-m")
        related = pytrends.related_queries()
        queries = []
        if topic in related:
            for kind in ("rising", "top"):
                df = related[topic].get(kind)
                if df is not None and not df.empty:
                    queries.extend(df["query"].head(5).tolist())
        return queries
    except Exception:
        return []


def _summarise_interest(df, col: str, label: str) -> str:
    """Build a summary line for a single keyword's interest data."""
    peak_date = df[col].idxmax()
    peak_value = int(df[col].max())
    avg_value = df[col].mean()
    current_value = int(df[col].iloc[-1])
    trend_direction = "rising" if current_value > avg_value else "declining"
    peak_period = peak_date.strftime("%B %Y")

    return (
        f"  - {label}: avg {avg_value:.0f}/100, "
        f"peak {peak_value}/100 ({peak_period}), "
        f"current {current_value}/100 ({trend_direction})"
    )


def get_trend_data(topic: str) -> dict:
    """Fetch Google Trends data for a topic with related keywords and multiple timeframes.

    Searches:
    1. The primary topic over 12 months
    2. Related/rising queries from Google Trends
    3. The primary topic over 3 months for recent momentum

    Returns dict with keys: available (bool), summary (str), peak_period (str),
    related_queries (list[str]).
    """
    try:
        pytrends = TrendReq(hl="en-GB", tz=0)
    except Exception as e:
        return {
            "available": False,
            "summary": f"Google Trends connection failed: {e}",
            "peak_period": "N/A",
            "related_queries": [],
        }

    sections = []
    peak_period = "N/A"
    any_data = False

    # 1. Primary topic — 12-month view
    df_12m = _fetch_interest(pytrends, [topic], "today 12-m")
    if df_12m is not None and topic in df_12m.columns:
        any_data = True
        peak_date = df_12m[topic].idxmax()
        peak_period = peak_date.strftime("%B %Y")
        sections.append(f"**{topic}** (12-month view):")
        sections.append(_summarise_interest(df_12m, topic, topic))

    # 2. Primary topic — 3-month view for recent momentum
    df_3m = _fetch_interest(pytrends, [topic], "today 3-m")
    if df_3m is not None and topic in df_3m.columns:
        any_data = True
        sections.append(f"\n**{topic}** (3-month view — recent momentum):")
        sections.append(_summarise_interest(df_3m, topic, topic))

    # 3. Related queries
    related = _get_related_queries(pytrends, topic)

    if related:
        # Pick top 4 related terms to compare against the main topic
        compare_terms = related[:4]
        sections.append(f"\n**Related rising queries:** {', '.join(related[:10])}")

        # Compare main topic with top related terms (max 5 keywords per payload)
        compare_keywords = [topic] + compare_terms
        df_compare = _fetch_interest(pytrends, compare_keywords, "today 12-m")
        if df_compare is not None:
            any_data = True
            sections.append(f"\n**Comparison** (12-month, {topic} vs related):")
            for kw in compare_keywords:
                if kw in df_compare.columns:
                    sections.append(_summarise_interest(df_compare, kw, kw))

    if not any_data:
        return {
            "available": False,
            "summary": f"No Google Trends data available for '{topic}'.",
            "peak_period": "N/A",
            "related_queries": related,
        }

    summary = "Google Trends analysis:\n" + "\n".join(sections)

    return {
        "available": True,
        "summary": summary,
        "peak_period": peak_period,
        "related_queries": related,
    }
