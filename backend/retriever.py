"""
retriever.py — Qdrant vector search interface.

Handles embedding (via sentence-transformers) and similarity search.
Both the client and encoder are cached so they're initialized only once.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

COLLECTION = os.getenv("COLLECTION_NAME", "agentic_rag")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def _encoder() -> SentenceTransformer:
    """Load embedding model once and cache it. 384-dim, fast on CPU."""
    return SentenceTransformer(EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    """Create Qdrant client once and cache it."""
    return QdrantClient(
        url=(os.getenv("QDRANT_URL") or "").strip(),
        api_key=(os.getenv("QDRANT_API_KEY") or "").strip(),
    )


def embed(text: str) -> list[float]:
    """Embed a string into a normalized float vector."""
    vector = _encoder().encode(text, normalize_embeddings=True)
    return vector.tolist()


def retrieve_documents(query: str, top_k: int = 5) -> list[dict]:
    """
    Embed query and return top_k chunks from Qdrant.
    Each returned dict has: text, source, chunk_index, score, relevant (None until graded).
    """
    query_vector = embed(query)

    response = _client().query_points(
        collection_name=COLLECTION,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )
    results: list[ScoredPoint] = response.points

    return [
        {
            "text": hit.payload.get("text", "") if hit.payload else "",
            "source": hit.payload.get("source", "unknown") if hit.payload else "unknown",
            "chunk_index": hit.payload.get("chunk_index", 0) if hit.payload else 0,
            "score": round(float(hit.score), 4),
            "relevant": None,  # populated by grade_docs node
        }
        for hit in results
    ]


def get_collection_info() -> dict:
    """Return collection stats — used by the /health endpoint."""
    try:
        info = _client().get_collection(COLLECTION)
        return {
            "collection": COLLECTION,
            "vectors_count": info.vectors_count,
            "status": str(info.status),
        }
    except Exception as e:
        return {"collection": COLLECTION, "error": str(e)}
