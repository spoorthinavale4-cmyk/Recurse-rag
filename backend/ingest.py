"""
ingest.py — Corpus ingestion script.

Chunks documents, embeds them, and upserts into Qdrant.
Supports .txt and .pdf files.

Usage:
    # Basic
    python ingest.py

    # Custom path, chunk size, overlap
    python ingest.py --corpus ./data --chunk-size 512 --overlap 64

    # Dry run: count chunks without uploading
    python ingest.py --dry-run

    # Wipe and re-ingest from scratch
    python ingest.py --recreate
"""

from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from retriever import _encoder, embed

DEFAULT_CORPUS = BASE_DIR / "data"
COLLECTION = os.getenv("COLLECTION_NAME", "agentic_rag")


# ─── Chunking ─────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping word-count chunks."""
    words = text.split()
    step = max(1, chunk_size - overlap)
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# ─── Document loading ─────────────────────────────────────────────────────────

def load_documents(corpus_path: Path) -> list[tuple[str, str]]:
    """
    Walk corpus_path and return (filename, text) pairs.
    Supports .txt and .pdf.
    """
    docs: list[tuple[str, str]] = []

    for path in sorted(corpus_path.rglob("*")):
        if path.suffix.lower() == ".txt":
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    docs.append((path.name, text))
            except Exception as e:
                print(f"  [skip] {path.name}: {e}")

        elif path.suffix.lower() == ".pdf":
            try:
                import pypdf  # optional dependency

                reader = pypdf.PdfReader(str(path))
                text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
                if text:
                    docs.append((path.name, text))
            except ImportError:
                print("  [warn] pypdf not installed — skipping PDFs. Run: pip install pypdf")
                break
            except Exception as e:
                print(f"  [skip] {path.name}: {e}")

    return docs


# ─── Qdrant helpers ───────────────────────────────────────────────────────────

def _get_client() -> QdrantClient:
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )


def _ensure_collection(client: QdrantClient, collection: str, vector_size: int, recreate: bool):
    existing = {c.name for c in client.get_collections().collections}
    if recreate and collection in existing:
        client.delete_collection(collection)
        print(f"  Deleted existing collection '{collection}'")
        existing.discard(collection)
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        print(f"  Created collection '{collection}' (dim={vector_size}, metric=cosine)")
    else:
        print(f"  Using existing collection '{collection}' (use --recreate to wipe)")


def _load_encoder():
    try:
        return _encoder()
    except Exception as e:
        raise RuntimeError(
            "Failed to load the embedding model. Ensure the model is available locally "
            "or that this machine can reach Hugging Face."
        ) from e


# ─── Main ─────────────────────────────────────────────────────────────────────

def ingest(
    corpus_path: str,
    collection: str,
    chunk_size: int,
    overlap: int,
    dry_run: bool,
    recreate: bool,
    batch_size: int = 64,
):
    path = Path(corpus_path)
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Corpus path not found: {path}")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Ingesting corpus")
    print(f"  Path:       {path}")
    print(f"  Collection: {collection}")
    print(f"  Chunk size: {chunk_size} words | Overlap: {overlap} words")
    print(f"  Batch size: {batch_size}\n")

    docs = load_documents(path)
    if not docs:
        print("No documents found. Add .txt or .pdf files to the corpus directory.")
        return

    print(f"Found {len(docs)} document(s)\n")

    client = None
    if not dry_run:
        encoder = _load_encoder()
        vector_size = encoder.get_sentence_embedding_dimension()
        client = _get_client()
        _ensure_collection(client, collection, vector_size, recreate)

    total_chunks = 0
    batch: list[PointStruct] = []

    progress_label = "Counting chunks" if dry_run else "Embedding documents"
    for source, text in tqdm(docs, desc=progress_label):
        chunks = chunk_text(text, chunk_size, overlap)
        for idx, chunk in enumerate(chunks):
            total_chunks += 1
            if dry_run:
                continue
            batch.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=embed(chunk),
                payload={"text": chunk, "source": source, "chunk_index": idx},
            ))
            if len(batch) >= batch_size:
                client.upsert(collection_name=collection, points=batch)
                batch.clear()

    if client and batch:
        client.upsert(collection_name=collection, points=batch)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done.")
    print(f"  Total chunks {'would be ' if dry_run else ''}upserted: {total_chunks}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a document corpus into Qdrant.")
    parser.add_argument(
        "--corpus",
        default=str(DEFAULT_CORPUS),
        help=f"Path to corpus directory (default: {DEFAULT_CORPUS})",
    )
    parser.add_argument("--collection", default=COLLECTION, help="Qdrant collection name")
    parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size in words (default: 512)")
    parser.add_argument("--overlap", type=int, default=64, help="Overlap in words (default: 64)")
    parser.add_argument("--batch-size", type=int, default=64, help="Qdrant upsert batch size")
    parser.add_argument("--dry-run", action="store_true", help="Count chunks without uploading")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the collection")
    args = parser.parse_args()

    ingest(
        corpus_path=args.corpus,
        collection=args.collection,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        dry_run=args.dry_run,
        recreate=args.recreate,
        batch_size=args.batch_size,
    )
