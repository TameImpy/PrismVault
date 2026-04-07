import chromadb
import config
from src.embeddings import get_embeddings


def _get_client():
    """Return a ChromaDB client — CloudClient if cloud vars are set, else PersistentClient."""
    if config.CHROMA_CLOUD_API_KEY:
        return chromadb.CloudClient(
            api_key=config.CHROMA_CLOUD_API_KEY,
            tenant=config.CHROMA_CLOUD_TENANT or None,
            database=config.CHROMA_CLOUD_DATABASE or None,
        )
    return chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)


def get_collection():
    """Get or create the editorial_transcripts collection with cosine similarity."""
    client = _get_client()
    collection = client.get_or_create_collection(
        name="editorial_transcripts",
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def add_chunks(chunks: list[dict], embeddings: list[list[float]]):
    """Upsert chunks with embeddings into ChromaDB."""
    collection = get_collection()
    collection.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )


def search_transcripts(query: str, n_results: int = 5) -> dict:
    """Embed query and search ChromaDB. Returns ChromaDB results dict."""
    collection = get_collection()

    if collection.count() == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    query_embedding = get_embeddings([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
    )
    return results
