"""
cache.py — In-memory semantic cache.

When a query comes in, its embedding is compared to all cached query embeddings.
If cosine similarity exceeds the threshold, the cached result is returned instantly
without running the full agent pipeline (saves 2–5 seconds per repeat query).

This resets on server restart — intentionally. For persistence, swap _entries
for a Redis sorted set keyed by embedding hash.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

THRESHOLD = float(os.getenv("CACHE_THRESHOLD", "0.95"))
MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "256"))


@dataclass
class _Entry:
    query: str
    vector: list[float]
    result: dict
    timestamp: float = field(default_factory=time.time)
    hits: int = 0


class SemanticCache:
    """
    Cosine-similarity cache for agent query results.

    Usage:
        result = cache.get(query)   # None on miss
        if result is None:
            result = run_query(query)
            cache.set(query, result)
    """

    def __init__(self, threshold: float = THRESHOLD, max_size: int = MAX_SIZE):
        self.threshold = threshold
        self.max_size = max_size
        self._entries: list[_Entry] = []

    # ── public API ────────────────────────────────────────────────────────────

    def get(self, query: str) -> Optional[dict]:
        """Return cached result + metadata if a similar query exists."""
        if not self._entries:
            return None
        from retriever import embed  # lazy import to avoid circular dependency
        qv = np.array(embed(query))
        best_sim, best_entry = 0.0, None
        for entry in self._entries:
            sim = _cosine(qv, np.array(entry.vector))
            if sim > best_sim:
                best_sim, best_entry = sim, entry
        if best_entry and best_sim >= self.threshold:
            best_entry.hits += 1
            return {**best_entry.result, "cache_hit": True, "cache_similarity": round(best_sim, 4)}
        return None

    def set(self, query: str, result: dict) -> None:
        """Store a query → result mapping."""
        from retriever import embed
        if len(self._entries) >= self.max_size:
            # Evict entry with fewest cache hits (LFU eviction)
            self._entries.sort(key=lambda e: e.hits)
            self._entries.pop(0)
        self._entries.append(_Entry(query=query, vector=embed(query), result=result))

    def clear(self) -> None:
        self._entries.clear()

    def stats(self) -> dict:
        return {
            "entries": len(self._entries),
            "max_size": self.max_size,
            "threshold": self.threshold,
            "total_hits": sum(e.hits for e in self._entries),
            "queries_cached": [e.query[:60] for e in self._entries],
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

cache = SemanticCache()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0
