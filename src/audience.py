import pandas as pd
import os


def load_audience_data() -> pd.DataFrame:
    """Load the audience trends CSV."""
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "audience_trends.csv")
    return pd.read_csv(csv_path)


def get_topic_trends(df: pd.DataFrame, topic: str) -> str:
    """Filter audience data by topic and return a summary string.

    Uses case-insensitive partial matching on the topic column.
    """
    mask = df["topic"].str.lower().str.contains(topic.lower())
    filtered = df[mask]

    if filtered.empty:
        return f"No audience trend data available for '{topic}'."

    # Peak month
    month_agg = filtered.groupby("month")["audience_index"].mean()
    peak_month_num = month_agg.idxmax()
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December",
    }
    peak_month = month_names.get(peak_month_num, str(peak_month_num))

    # Peak day of week
    day_agg = filtered.groupby("day_of_week")["audience_index"].mean()
    peak_day = day_agg.idxmax()

    # Top segment
    seg_agg = filtered.groupby("segment")["audience_index"].mean()
    top_segment = seg_agg.idxmax()
    top_segment_index = seg_agg.max()

    # Overall average
    avg_index = filtered["audience_index"].mean()

    summary = (
        f"Audience trends for '{topic}':\n"
        f"- Average audience index: {avg_index:.0f} (100 = baseline)\n"
        f"- Peak month: {peak_month} (avg index: {month_agg.max():.0f})\n"
        f"- Best day of week: {peak_day} (avg index: {day_agg[peak_day]:.0f})\n"
        f"- Top segment: {top_segment} (avg index: {top_segment_index:.0f})\n"
        f"- Data covers {len(filtered)} data points across {filtered['segment'].nunique()} segments"
    )
    return summary
