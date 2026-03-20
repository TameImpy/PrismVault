from src.embeddings import chunk_transcript, _count_tokens, _split_into_sentences
import config


SAMPLE_TRANSCRIPT = {
    "interview_id": "TEST-001",
    "editor_name": "Test Editor",
    "publication": "Test Pub",
    "date": "2025-01-01",
    "vertical": "Test",
    "topics": ["topic1", "topic2"],
    "transcript": (
        "This is the first sentence about wellness trends. "
        "This is the second sentence about gut health and probiotics. "
        "This is the third sentence about consumer behaviour.\n\n"
        "This is a new paragraph about skincare. "
        "Ingredients like niacinamide are trending. "
        "Consumers want transparency in their products."
    ),
}


def test_chunk_transcript_returns_list():
    chunks = chunk_transcript(SAMPLE_TRANSCRIPT)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1


def test_chunk_metadata():
    chunks = chunk_transcript(SAMPLE_TRANSCRIPT)
    chunk = chunks[0]
    assert chunk["metadata"]["interview_id"] == "TEST-001"
    assert chunk["metadata"]["editor_name"] == "Test Editor"
    assert chunk["metadata"]["publication"] == "Test Pub"
    assert chunk["metadata"]["vertical"] == "Test"
    assert "topic1" in chunk["metadata"]["topics"]


def test_chunk_ids_are_unique():
    chunks = chunk_transcript(SAMPLE_TRANSCRIPT)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_has_text():
    chunks = chunk_transcript(SAMPLE_TRANSCRIPT)
    for chunk in chunks:
        assert len(chunk["text"]) > 0


def test_split_into_sentences():
    text = "First sentence. Second sentence! Third sentence?"
    sentences = _split_into_sentences(text)
    assert len(sentences) == 3


def test_count_tokens():
    count = _count_tokens("hello world")
    assert count > 0
    assert isinstance(count, int)
