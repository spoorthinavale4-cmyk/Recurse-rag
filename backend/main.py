"""
main.py - FastAPI application entry point.

Endpoints:
    POST /query          - Run the agentic RAG pipeline
    GET  /health         - Server + collection health check
    GET  /cache/stats    - Cache hit stats
    DELETE /cache        - Clear the cache
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from cache import cache
from graph import run_query
from retriever import get_collection_info


class QueryRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must not be empty.")
        return v.strip()


class QueryResponse(BaseModel):
    answer: str
    nodes_fired: list[str]
    retrieved_chunks: list[dict]
    latency_ms: dict
    rewrite_happened: bool
    rewritten_query: str | None
    retry_count: int
    route_decision: str
    cache_hit: bool
    cache_similarity: float | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Optionally warm up the encoder on startup."""
    if os.getenv("WARMUP_ENCODER_ON_STARTUP", "false").strip().lower() == "true":
        from retriever import _encoder

        _encoder()
        print("Encoder warmed up")
    yield


app = FastAPI(
    title="Agentic RAG",
    description=(
        "Self-correcting Retrieval-Augmented Generation with LangGraph. "
        "5-node agent: route -> retrieve -> grade -> [rewrite -> retrieve]* -> generate."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    cached = cache.get(req.query)
    if cached:
        return QueryResponse(**cached)

    result = run_query(req.query)
    result["cache_hit"] = False
    result["cache_similarity"] = None
    cache.set(req.query, result)

    return QueryResponse(**result)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "collection": get_collection_info(),
        "cache": cache.stats(),
        "env": {
            "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            "top_k": os.getenv("TOP_K", "5"),
            "max_retries": os.getenv("MAX_RETRIES", "2"),
        },
    }


@app.get("/cache/stats")
def cache_stats():
    return cache.stats()


@app.delete("/cache")
def clear_cache():
    cache.clear()
    return {"message": "Cache cleared.", "entries": 0}
