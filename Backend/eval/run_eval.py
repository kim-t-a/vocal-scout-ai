"""
Retrieval + guard evaluation for VocalScout.

Runs the golden question set (eval/golden_set.json) through four retrieval
configs — dense-only, BM25-only, RRF fusion, and fusion + LLM judge — over the
REAL pipeline code (no mocks), then scores each config and sweeps the
off-topic guard threshold over the actual cosine score distributions.

For scope:"in" questions, the expected chunks are derived at runtime from the
question's chapter_index (all chunks with that chapter_index) — so the set
survives re-chunking.

Usage:  python eval/run_eval.py
Output: printed comparison table + eval/report.json (per-question rows).
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb

import services.retriever as retriever
from services.embeddings import get_embedding
from services.reranker import rerank as judge_rerank

EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_PATH = EVAL_DIR / "golden_set.json"
REPORT_PATH = EVAL_DIR / "report.json"

DENSE_K = 20        # candidates fetched per dense query
FINAL_K = 3         # what the app finally shows the model
JUDGE_REPEATS = 2   # rerun the judge config to measure non-determinism

# "--video <id>" limits the run to one video (e.g. after re-ingesting just
# that video); "--skip-judge" drops the judge configs (~17s/question saved).
ARGS = sys.argv[1:]
ONLY_VIDEO = ARGS[ARGS.index("--video") + 1] if "--video" in ARGS else None
SKIP_JUDGE = "--skip-judge" in ARGS

CONFIGS = ["dense", "bm25", "fusion"] + (
    [] if SKIP_JUDGE else ["judge_r1", "judge_r2"]
)

client = chromadb.PersistentClient(path="chroma_db")


# ----------------------------------------------------------------- ground truth
def expected_chunk_ids(chunks: list[dict], chapter_index) -> set[str]:
    return {
        chunk["chunk_id"]
        for chunk in chunks
        if chunk.get("chapter_index") == chapter_index
    }


# ----------------------------------------------------------------- rankers
def dense_rank(query_embedding, video_id: str, k: int = DENSE_K):
    collection = client.get_collection(f"video_{video_id}")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, collection.count()),
        include=["metadatas", "distances"],
    )
    return results["ids"][0], results["distances"][0]


def bm25_rank(video_id: str, question: str) -> list[str]:
    ranks = retriever._bm25_ranks(video_id, question)
    return [chunk_id for chunk_id, _ in sorted(ranks.items(), key=lambda kv: kv[1])]


def fusion_rank(dense_ids: list[str], bm25_ids: list[str]) -> list[str]:
    ranks = {chunk_id: rank for rank, chunk_id in enumerate(bm25_ids)}
    fused = retriever._rrf_fuse(dense_ids, ranks)
    return [
        chunk_id
        for chunk_id, _ in sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
    ]


def judge_config_order(question: str, fused_ids: list[str], texts_by_id: dict):
    """Judge the fused shortlist. Returns reordered ids, or None on failure."""

    shortlist = fused_ids[: retriever.RERANK_CANDIDATES]
    order = judge_rerank(question, [texts_by_id.get(chunk_id, "") for chunk_id in shortlist])

    if order is None:
        return None

    return [shortlist[index] for index in order]


# ----------------------------------------------------------------- metrics
def rank_metrics(ranked: list[str], expected: set[str], k: int = FINAL_K) -> tuple[int, float, int]:
    """(hit@k, rr, recall@k) for one question under one config."""

    top_k = ranked[:k]
    hit = int(any(chunk_id in expected for chunk_id in top_k))

    rr = 0.0
    for rank, chunk_id in enumerate(ranked[:DENSE_K], start=1):
        if chunk_id in expected:
            rr = 1.0 / rank
            break

    recall = int(any(chunk_id in expected for chunk_id in ranked[:DENSE_K]))
    return hit, rr, recall


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


# ----------------------------------------------------------------- per video
def evaluate_video(video: dict, rows: list, threshold_scores: dict):
    video_id = video["video_id"]
    chunks_path = Path("chunks") / f"{video_id}_chunks.json"
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    collection = client.get_collection(f"video_{video_id}")
    space = (collection.metadata or {}).get("hnsw:space", "l2")

    # Chunk texts for the judge (ids must match the collection's).
    texts_by_id = {chunk["chunk_id"]: chunk["text"] for chunk in chunks}

    configs = CONFIGS
    stats = {
        name: {"hits": [], "rr": [], "recall": [], "latency": []}
        for name in configs
    }

    for entry in video["questions"]:
        question = entry["question"]
        expected = (
            expected_chunk_ids(chunks, entry["chapter_index"])
            if entry["scope"] == "in"
            else set()
        )

        t0 = time.perf_counter()
        try:
            embedding = get_embedding(question)
        except requests.RequestException as e:
            print(f"   embedding failed ({type(e).__name__}), retrying once...", flush=True)
            time.sleep(3)
            try:
                embedding = get_embedding(question)
            except requests.RequestException:
                print(f"   SKIP (embedding unavailable): {question[:50]}", flush=True)
                continue
        embed_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        dense_ids, distances = dense_rank(embedding, video_id)
        dense_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        bm25_ids = bm25_rank(video_id, question)
        bm25_ms = (time.perf_counter() - t0) * 1000

        fused_ids = fusion_rank(dense_ids, bm25_ids)

        per_config = {
            "dense": dense_ids,
            "bm25": bm25_ids,
            "fusion": fused_ids,
        }

        if SKIP_JUDGE:
            judge_ms = judge2_ms = 0.0
        else:
            # Judge calls: a network hiccup must not kill a 60-question run —
            # treat it like any other judge failure (fusion order stands).
            t0 = time.perf_counter()
            try:
                order1 = judge_config_order(question, fused_ids, texts_by_id)
            except requests.RequestException as e:
                print(f"   judge r1 {type(e).__name__}, fusion order kept", flush=True)
                order1 = None
            judge_ms = (time.perf_counter() - t0) * 1000
            try:
                order2 = judge_config_order(question, fused_ids, texts_by_id)
            except requests.RequestException:
                order2 = None
            judge2_ms = (time.perf_counter() - t0) * 1000

            per_config["judge_r1"] = order1 if order1 is not None else fused_ids
            per_config["judge_r2"] = order2 if order2 is not None else fused_ids

        # Cosine score of the best dense chunk feeds the guard sweep.
        if space == "cosine" and distances:
            threshold_scores[entry["scope"]].append(1.0 - distances[0])

        row = {"video_id": video_id, "question": question, "scope": entry["scope"],
               "kind": entry.get("kind", ""), "chapter": entry.get("chapter_index")}

        for name, ranked in per_config.items():
            if entry["scope"] == "in":
                hit, rr, recall = rank_metrics(ranked, expected)
                stats[name]["hits"].append(hit)
                stats[name]["rr"].append(rr)
                stats[name]["recall"].append(recall)
                row[f"{name}_hit"] = hit
                row[f"{name}_rr"] = round(rr, 3)
            else:
                # Off-scope: success = the guard would reject it (score below
                # threshold) AND retrieval agreeing is informational only.
                row[f"{name}_top1"] = ranked[0] if ranked else None

        # Judge agreement between repeats (in-scope questions only).
        if entry["scope"] == "in" and not SKIP_JUDGE:
            row["judge_agree"] = int((order1 or []) == (order2 or []))

        row["embed_ms"] = round(embed_ms)
        row["dense_ms"] = round(dense_ms)
        row["bm25_ms"] = round(bm25_ms)
        row["judge_ms"] = round(judge_ms)
        rows.append(row)

        if len(rows) % 10 == 0:
            print(f"   {len(rows)} questions evaluated...", flush=True)

        stats["dense"]["latency"].append(dense_ms)
        stats["bm25"]["latency"].append(bm25_ms + embed_ms)
        stats["fusion"]["latency"].append(dense_ms + bm25_ms + embed_ms)
        if not SKIP_JUDGE:
            stats["judge_r1"]["latency"].append(dense_ms + bm25_ms + embed_ms + judge_ms)
            stats["judge_r2"]["latency"].append(dense_ms + bm25_ms + embed_ms + judge2_ms)

    summary = {}
    for name in configs:
        s = stats[name]
        summary[name] = {
            "hit@3": round(mean(s["hits"]), 3),
            "mrr": round(mean(s["rr"]), 3),
            "recall@20": round(mean(s["recall"]), 3),
            "avg_ms": round(mean(s["latency"])),
            "n": len(s["hits"]),
        }

    agreement = mean([r["judge_agree"] for r in rows
                      if r["video_id"] == video_id and "judge_agree" in r])
    summary["judge_agreement"] = round(agreement, 3)

    return summary


# ----------------------------------------------------------------- guard sweep
def sweep_threshold(threshold_scores: dict):
    in_scores = sorted(threshold_scores["in"], reverse=True)
    off_scores = threshold_scores["off"]

    if not in_scores or not off_scores:
        return None, "guard sweep skipped (need a cosine-space collection)"

    print(f"\n== Off-topic guard sweep (n_in={len(in_scores)}, n_off={len(off_scores)}) ==")
    print("threshold | in-scope kept | off-topic caught")

    best = None
    for threshold in [round(0.10 + 0.05 * i, 2) for i in range(13)]:
        kept = mean([s >= threshold for s in in_scores])
        caught = mean([s < threshold for s in off_scores])
        print(f"  {threshold:.2f}    |   {kept:.0%}       |   {caught:.0%}")

        # Recommend: catch every off-topic question while keeping >=95% in-scope.
        if kept >= 0.95 and caught >= 1.0 and best is None:
            best = threshold

    if best is None:
        # Fall back to the threshold with zero false rejections and max catches.
        best = 0.35
        for threshold in [round(0.10 + 0.05 * i, 2) for i in range(13)]:
            kept = mean([s >= threshold for s in in_scores])
            caught = mean([s < threshold for s in off_scores])
            if kept >= 0.98 and caught > mean(
                [s < best for s in off_scores]
            ):
                best = threshold

    return best, None


# ----------------------------------------------------------------- main
def main():
    if not GOLDEN_PATH.exists():
        print(f"{GOLDEN_PATH} not found. Review golden_set.generated.json, edit freely,")
        print("then save the reviewed copy as eval/golden_set.json and rerun.")
        sys.exit(1)

    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    rows: list = []
    threshold_scores = {"in": [], "off": []}
    summaries = {}

    videos = golden["videos"]
    if ONLY_VIDEO:
        videos = [v for v in videos if v["video_id"] == ONLY_VIDEO]
        if not videos:
            print(f"No video {ONLY_VIDEO} in {GOLDEN_PATH}.")
            sys.exit(1)

    for v_index, video in enumerate(videos):
        print(f"\n== {video['video_id']} ({video['name']}) — video {v_index + 1}/{len(videos)} ==")
        summaries[video["video_id"]] = evaluate_video(video, rows, threshold_scores)
        done = sum(1 for r in rows if r["video_id"] == video["video_id"])
        print(f"   {done} questions done.")

    print("\n" + "=" * 72)
    print(f"{'config':<10} {'Hit@3':>7} {'MRR':>7} {'Recall@20':>10} {'avg ms':>8}")
    print("-" * 72)
    for video_id, summary in summaries.items():
        print(video_id)
        for name in CONFIGS:
            s = summary[name]
            print(f"{name:<10} {s['hit@3']:>7.1%} {s['mrr']:>7.3f} {s['recall@20']:>10.1%} {s['avg_ms']:>8}")

    threshold, note = sweep_threshold(threshold_scores)
    if note:
        print(f"\n{note}")
    else:
        print(f"\nRecommended OFF_TOPIC_THRESHOLD: {threshold}  (current: 0.35)")

    report_path = (
        REPORT_PATH.with_name(f"report_{ONLY_VIDEO}.json") if ONLY_VIDEO else REPORT_PATH
    )
    report_path.write_text(
        json.dumps({"summaries": summaries, "rows": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nPer-question rows -> {report_path}")


if __name__ == "__main__":
    main()
