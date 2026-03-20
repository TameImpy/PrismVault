import tiktoken
from openai import OpenAI
import config


def _count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def _split_into_sentences(text: str) -> list[str]:
    """Split text on sentence boundaries (period, question mark, exclamation)."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_transcript(transcript_json: dict) -> list[dict]:
    """Split a transcript into overlapping chunks of ~CHUNK_SIZE tokens.

    Each chunk carries metadata from the parent transcript.
    """
    text = transcript_json["transcript"]
    metadata = {
        "interview_id": transcript_json["interview_id"],
        "editor_name": transcript_json["editor_name"],
        "publication": transcript_json["publication"],
        "date": transcript_json["date"],
        "vertical": transcript_json["vertical"],
        "topics": ", ".join(transcript_json["topics"]),
    }

    # Split into paragraphs first, then sentences
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    sentences = []
    for para in paragraphs:
        sentences.extend(_split_into_sentences(para))

    chunks = []
    current_sentences = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = _count_tokens(sentence)

        if current_tokens + sentence_tokens > config.CHUNK_SIZE and current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append({"text": chunk_text, "metadata": metadata.copy()})

            # Keep overlap: walk backwards from end until we have ~CHUNK_OVERLAP tokens
            overlap_sentences = []
            overlap_tokens = 0
            for s in reversed(current_sentences):
                s_tokens = _count_tokens(s)
                if overlap_tokens + s_tokens > config.CHUNK_OVERLAP:
                    break
                overlap_sentences.insert(0, s)
                overlap_tokens += s_tokens

            current_sentences = overlap_sentences
            current_tokens = overlap_tokens

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Final chunk
    if current_sentences:
        chunk_text = " ".join(current_sentences)
        chunks.append({"text": chunk_text, "metadata": metadata.copy()})

    # Add chunk index to metadata
    for i, chunk in enumerate(chunks):
        chunk["metadata"]["chunk_index"] = i
        chunk["id"] = f"{metadata['interview_id']}_{i}"

    return chunks


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch-embed texts using OpenAI text-embedding-3-small."""
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]
