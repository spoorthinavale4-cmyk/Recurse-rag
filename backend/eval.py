"""
eval.py — Evaluation runner (token-overlap metrics, no LLM cost).

Runs the full agent pipeline on a ground-truth dataset and computes:
  - Token recall   (what fraction of GT tokens appear in the answer)
  - Token precision
  - Token F1
  - Average latency
  - Rewrite rate   (how often the agent needed to rephrase the query)

Usage:
    python eval.py
    python eval.py --dataset ../eval_dataset.json --output eval_results.json
    python eval.py --sample 10   # run on first N samples only
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# ─── Metrics ──────────────────────────────────────────────────────────────────

def _tokens(text: str) -> set[str]:
    return set(text.lower().split())


def token_metrics(prediction: str, ground_truth: str) -> dict[str, float]:
    pred = _tokens(prediction)
    gt = _tokens(ground_truth)
    overlap = pred & gt

    recall = len(overlap) / len(gt) if gt else 0.0
    precision = len(overlap) / len(pred) if pred else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "token_recall": round(recall, 4),
        "token_precision": round(precision, 4),
        "token_f1": round(f1, 4),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_evaluation(dataset_path: str, output_path: str, sample: int | None = None):
    from graph import run_query

    dataset_file = Path(dataset_path)
    if not dataset_file.exists():
        raise FileNotFoundError(
            f"Dataset not found: {dataset_path}\n"
            "Run with the sample eval_dataset.json at the project root."
        )

    with open(dataset_file) as f:
        dataset: list[dict] = json.load(f)

    if sample:
        dataset = dataset[:sample]

    print(f"\nRunning evaluation on {len(dataset)} sample(s)...\n")

    results: list[dict] = []

    for i, sample_item in enumerate(tqdm(dataset, desc="Evaluating")):
        query = sample_item["query"]
        ground_truth = sample_item.get("ground_truth", "")

        try:
            output = run_query(query)
            metrics = token_metrics(output["answer"], ground_truth)
        except Exception as e:
            print(f"\n  [error] Sample {i+1}: {e}")
            output = {"answer": "", "nodes_fired": [], "rewrite_happened": False,
                      "retry_count": 0, "latency_ms": {"total": 0}}
            metrics = {"token_recall": 0.0, "token_precision": 0.0, "token_f1": 0.0}

        results.append({
            "index": i + 1,
            "query": query,
            "ground_truth": ground_truth,
            "answer": output["answer"],
            "nodes_fired": output["nodes_fired"],
            "rewrite_happened": output["rewrite_happened"],
            "retry_count": output["retry_count"],
            "latency_total_ms": output["latency_ms"].get("total", 0),
            **metrics,
        })

    # ── Aggregate ─────────────────────────────────────────────────────────────
    n = len(results)
    summary = {
        "n_samples": n,
        "avg_token_recall": round(sum(r["token_recall"] for r in results) / n, 4) if n else 0.0,
        "avg_token_precision": round(sum(r["token_precision"] for r in results) / n, 4) if n else 0.0,
        "avg_token_f1": round(sum(r["token_f1"] for r in results) / n, 4) if n else 0.0,
        "avg_latency_ms": round(sum(r["latency_total_ms"] for r in results) / n, 1) if n else 0.0,
        "rewrite_rate": round(sum(1 for r in results if r["rewrite_happened"]) / n, 4) if n else 0.0,
        "zero_f1_count": sum(1 for r in results if r["token_f1"] == 0),
    }

    output_data = {"summary": summary, "results": results}
    Path(output_path).write_text(json.dumps(output_data, indent=2))

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 45)
    print("  EVALUATION SUMMARY")
    print("=" * 45)
    for k, v in summary.items():
        print(f"  {k:<28} {v}")
    print("=" * 45)
    print(f"\nFull results → {output_path}")
    print("\nPaste these numbers into your README eval table.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the Agentic RAG pipeline.")
    parser.add_argument("--dataset", default="../eval_dataset.json")
    parser.add_argument("--output", default="eval_results.json")
    parser.add_argument("--sample", type=int, default=None, help="Run on first N samples only")
    args = parser.parse_args()

    run_evaluation(args.dataset, args.output, args.sample)
