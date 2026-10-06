import json
import os
import re
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi

from services.reranker import rerank

client = chromadb.PersistentClient(path="chroma_db")

# --- Hybrid retrieval --------------------------------------------------------
# Dense embeddings are good at meaning but blur exact terms ("COPY" vs "ADD");
# BM25 is the reverse. Both produce ranked candidate lists, Reciprocal Rank
# Fusion merges them without any score-scale tuning, and an LLM judge makes the
# final call — it reads the question and every candidate together, which a
# bi-encoder similarity score can never do. (The NVIDIA catalog no longer
# hosts a cross-encoder reranker, so the chat model judges; see reranker.py.)
DENSE_CANDIDATES = 20    # fetched from Chroma before fusion (n_results=3 today)
RRF_K = 60               # standard RRF damping constant
RERANK_CANDIDATES = 12   # passages sent to the reranker — one API call
FINAL_RESULTS = 3        # chunks returned to the prompt, same as before

# The LLM judge measured WORSE than plain fusion (Hit@3 93.0% vs 95.3%, MRR
# 0.877 vs 0.855) while costing ~17s per question, and repeated runs agreed
# on the ordering only 23% of the time — so it is OFF by default. Set
# RERANK_ENABLED=1 in the environment to turn it back on for experiments.
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "0") == "1"

CHUNKS_DIR = Path("chunks")
_bm25_cache: dict[str, tuple[list[str], BM25Okapi]] = {}   # video_id -> (ids, index)
_BM25_CACHE_LIMIT = 8   # small: one single-user server, one active video


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens — all BM25 needs for transcript text."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _load_bm25(video_id: str) -> tuple[list[str], BM25Okapi]:
    """
    BM25 index over the video's chunk texts, built once and cached.

    Reads the same chunks/{video_id}_chunks.json the chunker wrote, so every
    video already on disk (including legacy window-chunked ones) gets keyword
    search with zero re-ingestion.
    """

    cached = _bm25_cache.get(video_id)
    if cached is not None:
        return cached

    chunks_path = CHUNKS_DIR / f"{video_id}_chunks.json"

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        raise ValueError("chunks file is empty")

    ids = [chunk["chunk_id"] for chunk in chunks]
    index = BM25Okapi([_tokenize(chunk["text"]) for chunk in chunks])

    if len(_bm25_cache) >= _BM25_CACHE_LIMIT:
        _bm25_cache.pop(next(iter(_bm25_cache)))

    _bm25_cache[video_id] = (ids, index)
    return ids, index


def _bm25_ranks(video_id: str, query: str) -> dict[str, int]:
    """
    {chunk_id: 0-based rank} for one question, best chunk first.
    Empty dict when the index can't be built — caller falls back to dense-only.
    """

    try:
        ids, index = _load_bm25(video_id)
    except Exception as e:  # noqa: BLE001 — keyword search must never sink retrieval
        print(f"BM25 unavailable for {video_id} ({type(e).__name__}: {e}), dense only.")
        return {}

    scores = index.get_scores(_tokenize(query))
    order = sorted(range(len(ids)), key=lambda i: scores[i], reverse=True)
    return {ids[position]: rank for rank, position in enumerate(order)}


def _rrf_fuse(dense_ids: list[str], bm25_ranks: dict[str, int]) -> dict[str, float]:
    """Sum of 1/(RRF_K + rank) over every list a chunk appears in."""

    fused: dict[str, float] = {}

    for rank, chunk_id in enumerate(dense_ids):
        fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    for chunk_id, rank in bm25_ranks.items():
        fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    return fused


def search_chunks(query_embedding, query: str, video_id: str, n_results: int = FINAL_RESULTS):
    """
    Hybrid retrieval for one video: dense + BM25 candidates, RRF fusion,
    cross-encoder rerank.

    The BM25 half indexes the chunk file already on disk (no re-ingestion
    needed); if it's missing or the reranker is down, retrieval degrades to
    plain vector search instead of failing. Returns the same shape the old
    vector-only search did, so nothing downstream changes.
    """

    collection_name = f"video_{video_id}"

    collection = client.get_collection(collection_name)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=DENSE_CANDIDATES,
        include=["documents", "metadatas", "distances"],
    )

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadata = results["metadatas"][0]
    distances = results["distances"][0]

    by_id = {
        chunk_id: (doc, meta, dist)
        for chunk_id, doc, meta, dist in zip(ids, documents, metadata, distances)
    }

    # Fusion. The BM25 corpus can list ids the collection doesn't have (chunks
    # file and Chroma can drift), so filter to what Chroma returned before
    # ranking — phantom ids must not push real candidates out of the top ranks.
    bm25_ranks = _bm25_ranks(video_id, query)

    if bm25_ranks:
        fused = _rrf_fuse(ids, bm25_ranks)
        ordered_ids = sorted(
            (chunk_id for chunk_id in fused if chunk_id in by_id),
            key=fused.get,
            reverse=True,
        )
    else:
        ordered_ids = list(ids)

    # Rerank the fusion winners. Off by default (see RERANK_ENABLED); when
    # enabled, any reranker failure leaves the fusion order standing — same
    # degrade-don't-die rule as everywhere else in the pipeline.
    shortlist = ordered_ids[:RERANK_CANDIDATES]

    if RERANK_ENABLED:
        order = rerank(query, [by_id[chunk_id][0] for chunk_id in shortlist])

        if order is not None:
            shortlist = [shortlist[index] for index in order]

    chosen = shortlist[:n_results]

    if not chosen:
        raise ValueError(f"no chunks retrieved for {video_id}")

    context_docs = [by_id[chunk_id][0] for chunk_id in chosen]
    best_meta = by_id[chosen[0]][1]
    best_distance = by_id[chosen[0]][2]

    # Relevance score of the final best chunk in [0, 1] — still what the
    # off-topic guard consumes. Only meaningful for cosine collections;
    # legacy l2 collections report None and the caller skips the check.
    space = (collection.metadata or {}).get("hnsw:space", "l2")
    score = (1.0 - best_distance) if space == "cosine" else None

    return {
        "context": "\n\n".join(context_docs),
        "timestamp": best_meta["start_ms"],
        "quote": context_docs[0][:200],
        "chapter": best_meta.get("chapter") or "",
        "score": score,
    }
