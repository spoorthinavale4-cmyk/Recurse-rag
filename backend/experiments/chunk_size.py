"""
experiments/chunk_size.py — Chunk size impact on retrieval quality.

Tests 3 chunk sizes (256, 512, 1024 words) and plots Avg Token F1 vs chunk size.
The graph goes directly into your README and is a key portfolio differentiator.

Usage:
    python experiments/chunk_size.py
    python experiments/chunk_size.py --dataset ../eval_dataset.json --sizes 256,512,1024
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

# Allow imports from parent (backend/) directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _tokenize(text: str) -> set[str]:
    return set(text.lower().split())


def _token_f1(pred: str, gt: str) -> float:
    p_toks, g_toks = _tokenize(pred), _tokenize(gt)
    if not p_toks or not g_toks:
        return 0.0
    overlap = p_toks & g_toks
    precision = len(overlap) / len(p_toks)
    recall = len(overlap) / len(g_toks)
    return (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0


def run_experiment(dataset_path: str, chunk_sizes: list[int]):
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from ingest import chunk_text, load_documents
    from retriever import _encoder, embed

    # ── Load eval dataset ─────────────────────────────────────────────────────
    dpath = Path(dataset_path)
    if not dpath.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    with open(dpath) as f:
        dataset: list[dict] = json.load(f)
    print(f"Loaded {len(dataset)} eval samples.\n")

    # ── Load corpus ───────────────────────────────────────────────────────────
    corpus_dir = Path(__file__).resolve().parent.parent / "data"
    if corpus_dir.exists():
        corpus_texts = load_documents(corpus_dir)
    else:
        # Fallback: use ground truths as a mini-corpus (for testing the script)
        print("[warn] No ./data directory. Using eval ground truths as mini-corpus.")
        corpus_texts = [(f"sample_{i}", s["ground_truth"]) for i, s in enumerate(dataset)]

    print(f"Corpus: {len(corpus_texts)} document(s)\n")

    encoder = _encoder()
    vector_size = encoder.get_sentence_embedding_dimension()
    client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

    results: dict[int, float] = {}

    for chunk_size in chunk_sizes:
        overlap = chunk_size // 8
        exp_col = f"_experiment_cs{chunk_size}"
        print(f"── Chunk size: {chunk_size} words (overlap: {overlap}) ──")

        # Clean slate
        existing = {c.name for c in client.get_collections().collections}
        if exp_col in existing:
            client.delete_collection(exp_col)
        client.create_collection(exp_col, vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE))

        # Ingest with this chunk size
        batch: list[PointStruct] = []
        total = 0
        for source, text in corpus_texts:
            for i, chunk in enumerate(chunk_text(text, chunk_size, overlap)):
                total += 1
                batch.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embed(chunk),
                    payload={"text": chunk, "source": source, "chunk_index": i},
                ))
                if len(batch) >= 64:
                    client.upsert(collection_name=exp_col, points=batch)
                    batch.clear()
        if batch:
            client.upsert(collection_name=exp_col, points=batch)
        print(f"  Ingested {total} chunks")

        # Evaluate retrieval
        f1_scores: list[float] = []
        for sample in dataset:
            hits = client.query_points(
                collection_name=exp_col,
                query=embed(sample["query"]),
                limit=5,
                with_payload=True,
            ).points
            retrieved = " ".join(h.payload.get("text", "") for h in hits if h.payload)
            f1_scores.append(_token_f1(retrieved, sample.get("ground_truth", "")))

        avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
        results[chunk_size] = avg_f1
        print(f"  Avg Retrieval F1: {avg_f1:.4f}\n")

        # Cleanup experiment collection
        client.delete_collection(exp_col)

    # ── Plot ──────────────────────────────────────────────────────────────────
    sizes = list(results.keys())
    scores = list(results.values())
    best_score = max(scores)
    best_size = sizes[scores.index(best_score)]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#4f46e5" if s == best_score else "#94a3b8" for s in scores]
    bars = ax.bar([str(s) for s in sizes], scores, color=colors, width=0.5, edgecolor="white", linewidth=1.5)

    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.008,
            f"{score:.3f}",
            ha="center", va="bottom", fontsize=11, fontweight="bold",
            color="#1e293b",
        )

    ax.set_xlabel("Chunk Size (words)", fontsize=12, labelpad=10)
    ax.set_ylabel("Avg Retrieval Token F1", fontsize=12, labelpad=10)
    ax.set_title("Chunk Size vs. Retrieval Quality", fontsize=14, fontweight="bold", pad=16)
    ax.set_ylim(0, min(1.0, best_score * 1.25) + 0.05)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linestyle="--")

    best_patch = mpatches.Patch(
        color="#4f46e5",
        label=f"Best: {best_size} words  (F1 = {best_score:.3f})",
    )
    ax.legend(handles=[best_patch], fontsize=10, loc="lower right")

    out_path = Path(__file__).resolve().parent.parent / "chunk_size_experiment.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()

    print("=" * 40)
    print("RESULTS")
    print("=" * 40)
    for cs, f1 in results.items():
        star = " ← best" if cs == best_size else ""
        print(f"  {cs:>6} words  F1 = {f1:.4f}{star}")
    print(f"\nPlot saved → {out_path}")
    print("Add this image to your README under 'Retrieval Experiments'.")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk size retrieval experiment.")
    parser.add_argument("--dataset", default="../eval_dataset.json")
    parser.add_argument("--sizes", default="256,512,1024", help="Comma-separated chunk sizes")
    args = parser.parse_args()

    sizes = [int(x.strip()) for x in args.sizes.split(",")]
    run_experiment(args.dataset, sizes)
