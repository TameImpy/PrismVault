from unittest.mock import patch, MagicMock

from src.brief import summarise_brief


def test_summarise_brief_empty_input_returns_fallback():
    """summarise_brief() should return fallback string for empty input without calling GPT-4o."""
    with patch("src.brief.OpenAI") as mock_openai_cls:
        result = summarise_brief("")

        assert "No client brief provided" in result
        mock_openai_cls.assert_not_called()


def test_summarise_brief_non_empty_calls_gpt_and_returns_summary():
    """summarise_brief() should call GPT-4o for non-empty input and return the response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Client seeks Gen Z awareness for skincare launch."

    with patch("src.brief.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        result = summarise_brief("Big long brief about skincare targeting Gen Z with awareness goals")

        assert result == "Client seeks Gen Z awareness for skincare launch."
        mock_client.chat.completions.create.assert_called_once()


def test_summarise_brief_whitespace_only_returns_fallback():
    """summarise_brief() should treat whitespace-only input as empty."""
    with patch("src.brief.OpenAI") as mock_openai_cls:
        result = summarise_brief("   \n  ")

        assert "No client brief provided" in result
        mock_openai_cls.assert_not_called()
