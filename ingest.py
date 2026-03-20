"""CLI script to load transcripts into ChromaDB. Run once to populate the vector store."""

import glob
import json
import os

from src.embeddings import chunk_transcript, get_embeddings
from src.vectorstore import add_chunks


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


if __name__ == "__main__":
    main()
