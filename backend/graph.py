"""
graph.py — LangGraph Agentic RAG Pipeline

5-node state machine:
    route_query → retrieve → grade_docs → [rewrite_query → retrieve]* → generate

The loop between rewrite_query and retrieve is the self-correction mechanism.
Max 2 retries before falling back to a direct answer.
"""

from __future__ import annotations

import os
import time
from typing import Annotated, Optional
import operator

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from retriever import retrieve_documents


# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    query: str
    route_decision: str                                    # 'retrieve' | 'direct'
    rewritten_query: Optional[str]
    documents: list[dict]                                  # relevant chunks only (post-grade)
    raw_documents: list[dict]                              # all chunks with grade labels (for UI)
    generation: str
    retry_count: int
    nodes_fired: Annotated[list[str], operator.add]        # accumulates across nodes
    latency_ms: dict[str, float]
    rewrite_happened: bool


# ─── LLM factory ──────────────────────────────────────────────────────────────

def _llm() -> ChatGroq:
    """Create a Groq LLM instance. Called per-node so config is always fresh."""
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )


# ─── Node 1: route_query ──────────────────────────────────────────────────────

_ROUTE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a query router for a document retrieval system.\n"
        "Classify the query into exactly one of two categories.\n\n"
        "Return ONLY one word:\n"
        "  'retrieve' — the query asks about specific domain knowledge, facts, cases, or documents\n"
        "  'direct'   — the query is a greeting, system question, or simple general knowledge"
    )),
    ("human", "{query}"),
])


def route_query(state: AgentState) -> dict:
    """Decide whether to retrieve documents or answer directly."""
    t0 = time.perf_counter()
    raw = (_ROUTE_PROMPT | _llm() | StrOutputParser()).invoke({"query": state["query"]})
    decision = "direct" if "direct" in raw.strip().lower() else "retrieve"
    elapsed = _ms(t0)
    return {
        "route_decision": decision,
        "nodes_fired": ["route_query"],
        "latency_ms": {**state.get("latency_ms", {}), "route_query": elapsed},
    }


# ─── Node 2: retrieve ─────────────────────────────────────────────────────────

def retrieve(state: AgentState) -> dict:
    """Embed the current query and pull top-k chunks from Qdrant."""
    t0 = time.perf_counter()
    active_query = state.get("rewritten_query") or state["query"]
    docs = retrieve_documents(active_query, top_k=int(os.getenv("TOP_K", "5")))
    elapsed = _ms(t0)
    return {
        "raw_documents": docs,
        "nodes_fired": ["retrieve"],
        "latency_ms": {**state.get("latency_ms", {}), "retrieve": elapsed},
    }


# ─── Node 3: grade_docs ───────────────────────────────────────────────────────

_GRADE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are grading the relevance of a retrieved document chunk to a user query.\n"
        "Return ONLY 'yes' if the chunk contains information useful for answering the query.\n"
        "Return ONLY 'no' if the chunk is irrelevant or unhelpful.\n"
        "One word. No explanations."
    )),
    ("human", "Query: {query}\n\nChunk:\n{chunk}"),
])


def grade_docs(state: AgentState) -> dict:
    """Score each retrieved chunk for relevance. Filter to relevant only."""
    t0 = time.perf_counter()
    active_query = state.get("rewritten_query") or state["query"]
    llm = _llm()
    chain = _GRADE_PROMPT | llm | StrOutputParser()

    graded: list[dict] = []
    for doc in state.get("raw_documents", []):
        verdict = chain.invoke({"query": active_query, "chunk": doc["text"]}).strip().lower()
        graded.append({**doc, "relevant": verdict == "yes"})

    relevant = [d for d in graded if d["relevant"]]
    elapsed = _ms(t0)
    return {
        "documents": relevant,
        "raw_documents": graded,
        "nodes_fired": ["grade_docs"],
        "latency_ms": {**state.get("latency_ms", {}), "grade_docs": elapsed},
    }


# ─── Node 4: rewrite_query ────────────────────────────────────────────────────

_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "A document retrieval query failed to find relevant results.\n"
        "Your job is to rewrite it to improve retrieval accuracy.\n\n"
        "Strategies:\n"
        "  - Use different terminology or domain synonyms\n"
        "  - Decompose complex questions into their core concept\n"
        "  - Make implicit context explicit\n\n"
        "Return ONLY the rewritten query. No preamble, no explanations."
    )),
    ("human", "Original query: {query}"),
])


def rewrite_query(state: AgentState) -> dict:
    """Reformulate the query when grading found zero relevant documents."""
    t0 = time.perf_counter()
    original = state.get("rewritten_query") or state["query"]
    rewritten = (_REWRITE_PROMPT | _llm() | StrOutputParser()).invoke({"query": original}).strip()
    elapsed = _ms(t0)
    return {
        "rewritten_query": rewritten,
        "retry_count": state.get("retry_count", 0) + 1,
        "rewrite_happened": True,
        "nodes_fired": ["rewrite_query"],
        "latency_ms": {**state.get("latency_ms", {}), "rewrite_query": elapsed},
    }


# ─── Node 5: generate ─────────────────────────────────────────────────────────

_GENERATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a precise question-answering assistant.\n"
        "Answer the query using ONLY the provided context.\n"
        "If the context is insufficient, say so and explain what information is missing.\n"
        "Be concise, factual, and cite the source document when relevant."
    )),
    ("human", "Context:\n{context}\n\nQuery: {query}"),
])

_DIRECT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Answer clearly and concisely."),
    ("human", "{query}"),
])


def generate(state: AgentState) -> dict:
    """Synthesize the final answer from graded relevant documents."""
    t0 = time.perf_counter()
    query = state["query"]
    docs = state.get("documents", [])
    llm = _llm()

    if state.get("route_decision") == "direct":
        answer = (_DIRECT_PROMPT | llm | StrOutputParser()).invoke({"query": query})
    elif not docs:
        # Fallback: no relevant documents found after all retries
        direct_answer = (_DIRECT_PROMPT | llm | StrOutputParser()).invoke({"query": query})
        retries = state.get("retry_count", 0)
        answer = (
            f"⚠️ No relevant documents found after {retries} retrieval attempt(s).\n\n"
            f"General answer (not grounded in your documents):\n\n{direct_answer}"
        )
    else:
        context = "\n\n---\n\n".join(
            f"[Source: {d.get('source', 'unknown')} | chunk {d.get('chunk_index', '?')}]\n{d['text']}"
            for d in docs
        )
        answer = (_GENERATE_PROMPT | llm | StrOutputParser()).invoke(
            {"query": query, "context": context}
        )

    elapsed = _ms(t0)
    latency = {**state.get("latency_ms", {}), "generate": elapsed}
    latency["total"] = round(sum(latency.values()), 1)

    return {
        "generation": answer,
        "nodes_fired": ["generate"],
        "latency_ms": latency,
    }


# ─── Conditional edge functions ───────────────────────────────────────────────

def _decide_route(state: AgentState) -> str:
    return state.get("route_decision", "retrieve")


def _decide_after_grade(state: AgentState) -> str:
    if state.get("documents"):
        return "generate"
    if state.get("retry_count", 0) < int(os.getenv("MAX_RETRIES", "2")):
        return "rewrite"
    return "generate"  # fallback: max retries hit


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(AgentState)

    g.add_node("route_query", route_query)
    g.add_node("retrieve", retrieve)
    g.add_node("grade_docs", grade_docs)
    g.add_node("rewrite_query", rewrite_query)
    g.add_node("generate", generate)

    g.set_entry_point("route_query")

    g.add_conditional_edges(
        "route_query",
        _decide_route,
        {"retrieve": "retrieve", "direct": "generate"},
    )
    g.add_edge("retrieve", "grade_docs")
    g.add_conditional_edges(
        "grade_docs",
        _decide_after_grade,
        {"generate": "generate", "rewrite": "rewrite_query"},
    )
    g.add_edge("rewrite_query", "retrieve")   # ← the self-correction loop
    g.add_edge("generate", END)

    return g.compile()


# Singleton — compiled once on import
rag_graph = build_graph()


def run_query(query: str) -> dict:
    """
    Run the full agentic RAG pipeline.
    Returns a dict ready to be serialized as the API response.
    """
    initial: AgentState = {
        "query": query,
        "route_decision": "",
        "rewritten_query": None,
        "documents": [],
        "raw_documents": [],
        "generation": "",
        "retry_count": 0,
        "nodes_fired": [],
        "latency_ms": {},
        "rewrite_happened": False,
    }

    final = rag_graph.invoke(initial)

    return {
        "answer": final["generation"],
        "nodes_fired": final["nodes_fired"],
        "retrieved_chunks": final.get("raw_documents", []),
        "latency_ms": final.get("latency_ms", {}),
        "rewrite_happened": final.get("rewrite_happened", False),
        "rewritten_query": final.get("rewritten_query"),
        "retry_count": final.get("retry_count", 0),
        "route_decision": final.get("route_decision", "retrieve"),
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)
