"""CLI script to load transcripts into ChromaDB. Run once to populate the vector store."""

import glob
import json
import os

from src.embeddings import chunk_transcript, get_embeddings
from src.vectorstore import add_chunks
from src.vertical_classifier import (
    DEFAULT_LOOKUP_PATH,
    distinct_brands_with_hints,
    load_taxonomy,
    refresh_brand_verticals,
    classify_new_brands_llm,
)


def refresh_verticals():
    """Diff the campaign-history roster against the cached brand->vertical
    lookup, LLM-classify any new brands, and flag additions for review."""
    roster, hints = distinct_brands_with_hints()
    if not roster:
        print("No campaign history found; skipping vertical classification.")
        return

    taxonomy = load_taxonomy()
    result = refresh_brand_verticals(
        roster, hints, taxonomy, DEFAULT_LOOKUP_PATH, classify_new_brands_llm
    )

    if result["flagged"]:
        print("\nNew brands classified and FLAGGED FOR REVIEW (%d):"
              % len(result["flagged"]))
        for brand in result["flagged"]:
            print("  - %s -> %s" % (brand, result["lookup"].get(brand, "?")))
    else:
        print("\nNo new brands to classify — brand->vertical cache is current.")


def main():
    transcript_dir = os.path.join(os.path.dirname(__file__), "data", "transcripts")
    files = sorted(glob.glob(os.path.join(transcript_dir, "*.json")))

    if not files:
        print("No transcript files found in data/transcripts/")
        return

    print(f"Found {len(files)} transcript files")

    all_chunks = []
    for filepath in files:
        with open(filepath) as f:
            transcript = json.load(f)
        chunks = chunk_transcript(transcript)
        all_chunks.extend(chunks)
        print(f"  {transcript['interview_id']}: {transcript['editor_name']} — {len(chunks)} chunks")

    print(f"\nEmbedding {len(all_chunks)} chunks...")
    texts = [c["text"] for c in all_chunks]
    embeddings = get_embeddings(texts)

    print("Storing in ChromaDB...")
    add_chunks(all_chunks, embeddings)

    print(f"\nDone! Ingested {len(files)} transcripts, {len(all_chunks)} chunks.")

    print("\nRefreshing brand->vertical lookup...")
    refresh_verticals()


if __name__ == "__main__":
    main()
