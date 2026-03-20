import pandas as pd
from src.audience import get_topic_trends, load_audience_data


def test_load_audience_data():
    df = load_audience_data()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "topic" in df.columns
    assert "audience_index" in df.columns


def test_get_topic_trends_found():
    df = load_audience_data()
    result = get_topic_trends(df, "gut health")
    assert "gut health" in result.lower()
    assert "Peak month" in result
    assert "Top segment" in result


def test_get_topic_trends_case_insensitive():
    df = load_audience_data()
    result = get_topic_trends(df, "GUT HEALTH")
    assert "No audience trend data" not in result


def test_get_topic_trends_partial_match():
    df = load_audience_data()
    result = get_topic_trends(df, "skin")
    assert "No audience trend data" not in result


def test_get_topic_trends_not_found():
    df = load_audience_data()
    result = get_topic_trends(df, "cryptocurrency")
    assert "No audience trend data" in result
