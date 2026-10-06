"""
Regeneratable golden-question generator for the retrieval eval.

Reads each video's AssemblyAI chapters (external ground truth — not produced
by our LLM) and a few of its actual chunk texts, asks the chat model for
in-scope questions tagged with the chapter they belong to, and merges them
with hand-written off-topic / near-miss questions.

Output: Backend/eval/golden_set.generated.json — REVIEW BEFORE TRUSTING.
The reviewed/edited copy must be saved as golden_set.json, which run_eval.py
reads. Chapter tags become the eval's ground truth at RUNTIME (a question's
expected chunks = the chunks whose chapter_index matches), so the golden set
stays valid even after re-chunking.

Usage:  python eval/generate_golden.py
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.chat import generate_answer

EVAL_DIR = Path(__file__).resolve().parent

# Videos in the eval. Chapters come from the saved AssemblyAI transcripts.
VIDEOS = {
    "XQNv0SRB0OM": {
        "name": "Docker crash course (~50 min)",
        "transcript": "transcripts/XQNv0SRB0OM.json",
        "chunks": "chunks/XQNv0SRB0OM_chunks.json",
    },
    "1KGWF704DUA": {
        "name": "Learn Python in 15 minutes",
        "transcript": "transcripts/1KGWF704DUA.json",
        "chunks": "chunks/1KGWF704DUA_chunks.json",
    },
}

# Hand-written, video-specific. scope:"off" questions must NOT be answerable
# from the video; kind "near_miss" = related topic the video never covers
# (the hardest cases for the off-topic guard), "off_topic" = clearly unrelated.
HAND_WRITTEN = {
    "XQNv0SRB0OM": [
        {"question": "How do I deploy my Docker containers to Kubernetes?", "scope": "off", "kind": "near_miss"},
        {"question": "What is the difference between Docker and Podman?", "scope": "off", "kind": "near_miss"},
        {"question": "How do I write a CI pipeline for my containers?", "scope": "off", "kind": "near_miss"},
        {"question": "How do I containerize a legacy .NET Framework app?", "scope": "off", "kind": "near_miss"},
        {"question": "What's the best pizza topping?", "scope": "off", "kind": "off_topic"},
        {"question": "Who won the 2022 football world cup?", "scope": "off", "kind": "off_topic"},
        {"question": "How do I invest in index funds?", "scope": "off", "kind": "off_topic"},
        {"question": "Explain the French Revolution.", "scope": "off", "kind": "off_topic"},
    ],
    "1KGWF704DUA": [
        {"question": "How do I use type hints in Python?", "scope": "off", "kind": "near_miss"},
        {"question": "How do I publish my package to PyPI?", "scope": "off", "kind": "near_miss"},
        {"question": "What is list comprehension syntax?", "scope": "off", "kind": "near_miss"},
        {"question": "How do I connect Python to a Postgres database?", "scope": "off", "kind": "off_topic"},
        {"question": "What is the capital of Japan?", "scope": "off", "kind": "off_topic"},
        {"question": "Recommend me a good laptop for programming.", "scope": "off", "kind": "off_topic"},
    ],
}

QUESTIONS_PER_CHAPTER = 4   # factoid / paraphrase / exact-term / conceptual

PROMPT = """You are building an evaluation set for a video-tutor search index.

Below are the headline, summary, and a few transcript excerpts from ONE chapter
of a tutorial video. Write {count} DIFFERENT questions a viewer could ask that
this chapter answers:

1. one direct factoid (answer is stated almost verbatim),
2. one paraphrase (same meaning, but reworded — do NOT reuse the transcript's
   own phrasing),
3. one exact-term question (uses specific technical terms that literally
   appear in the excerpts),
4. one conceptual "why" or "how" question.

Rules:
- Every question must be answerable from THIS chapter's text alone.
- Self-contained: no "in this video", no "the speaker", no pronouns referring
  to the transcript.
- Under 20 words each.
- Reply with ONLY a JSON array: [{{"question": "...", "kind": "factoid"}}, ...]
  with kind one of: factoid, paraphrase, exact_term, conceptual.

Chapter {index}: {headline}
Summary: {summary}

Transcript excerpts:
{excerpts}"""


def _parse_questions(text: str) -> list[dict]:
    """Extract the model's JSON array, keeping only well-formed rows."""

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return []

    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return []

    if not isinstance(data, list):
        return []

    allowed = {"factoid", "paraphrase", "exact_term", "conceptual"}
    questions = []

    for item in data:
        if not isinstance(item, dict):
            continue
        question = item.get("question")
        kind = item.get("kind", "factoid")
        if isinstance(question, str) and 8 <= len(question) <= 200:
            questions.append({
                "question": question.strip(),
                "scope": "in",
                "kind": kind if kind in allowed else "factoid",
            })

    return questions


def _chapter_excerpts(chunks: list[dict], chapter_index: int, sample: int = 3) -> str:
    """A few of the chapter's real chunk texts as topic seeds."""

    texts = [
        chunk["text"][:300]
        for chunk in chunks
        if chunk.get("chapter_index") == chapter_index
    ][:sample]
    return "\n---\n".join(texts) if texts else "(no text available)"


def generate_for_video(video_id: str, config: dict) -> dict:
    """All eval rows for one video: per-chapter LLM questions + hand-written."""

    transcript = json.loads(Path(config["transcript"]).read_text(encoding="utf-8"))
    chunks = json.loads(Path(config["chunks"]).read_text(encoding="utf-8"))
    chapters = transcript.get("chapters") or []

    entries = []
    used = set()

    for index, chapter in enumerate(chapters):
        headline = (chapter.get("headline") or "").strip()
        prompt = PROMPT.format(
            count=QUESTIONS_PER_CHAPTER,
            index=index,
            headline=headline,
            summary=(chapter.get("summary") or "")[:500],
            excerpts=_chapter_excerpts(chunks, index),
        )

        answer = generate_answer(prompt)
        generated = _parse_questions(answer) if answer else []

        if not generated:
            print(f"  chapter {index} ({headline[:40]}): generation failed, skipped")
            continue

        for row in generated:
            dedupe_key = row["question"].lower()
            if dedupe_key in used:
                continue
            used.add(dedupe_key)
            entries.append({
                "question": row["question"],
                "scope": "in",
                "kind": row["kind"],
                "chapter_index": index,
                # Review context only — the eval derives expectations from
                # chapter_index at runtime, never from these strings.
                "_chapter_headline": headline,
            })

        print(f"  chapter {index}: +{len(generated)} ({headline[:48]})")

    for row in HAND_WRITTEN.get(video_id, []):
        if row["question"].lower() not in used:
            used.add(row["question"].lower())
            entries.append(dict(row))

    return {
        "video_id": video_id,
        "name": config["name"],
        "questions": entries,
    }


def main():
    out_path = EVAL_DIR / "golden_set.generated.json"

    payload = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "MACHINE-GENERATED — review, edit, then save as golden_set.json. "
                    "run_eval.py reads golden_set.json only. Expected chunks for "
                    "scope:'in' questions derive from chapter_index at runtime.",
        },
        "videos": [generate_for_video(video_id, config) for video_id, config in VIDEOS.items()],
    }

    counts = [
        (v["video_id"], len(v["questions"]),
         sum(1 for q in v["questions"] if q["scope"] == "in"))
        for v in payload["videos"]
    ]
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {out_path}")
    for video_id, total, in_scope in counts:
        print(f"  {video_id}: {total} questions ({in_scope} in-scope, {total - in_scope} off)")


if __name__ == "__main__":
    main()
