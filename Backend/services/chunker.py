import json
import math
from pathlib import Path

from services.embeddings import get_embeddings

CHUNKS_DIR = Path("chunks")
CHUNKS_DIR.mkdir(exist_ok=True)

# --- Fallback windowing ------------------------------------------------------
# Used only when semantic splitting can't run (embedding API unavailable,
# transcript with no word timestamps). Plain slicing on word timestamps, so a
# chunking hiccup can never sink an ingestion run.
WINDOW_MS = 45000      # 45 seconds
OVERLAP_MS = 5000      # 5 seconds

# --- Chapter + semantic chunking --------------------------------------------
# Chapters come from AssemblyAI's `auto_chapters` and are treated as HARD
# boundaries — they are topic boundaries we already paid for. Inside a chapter,
# sentences are embedded and cut where consecutive similarity drops, catching
# the topic shifts that chapters are too coarse to see. Every chunk keeps its
# start/end timestamps so a citation can still seek the player.
SIMILARITY_THRESHOLD = 0.50   # consecutive-sentence cosine similarity below this = topic shift
MIN_CHUNK_CHARS = 500         # chunks smaller than this are folded into a neighbour
MAX_CHUNK_CHARS = 1800        # ~90s of speech; longer passages split at their weakest break
MIN_SENTENCE_CHARS = 25       # fragments this short ride along with the next sentence


def _boundaries(chapters) -> list[dict]:
    """Normalise AssemblyAI chapters into sorted {"start", "end", "headline"} dicts."""

    boundaries = [
        {
            "start": chapter["start"],
            "end": chapter["end"],
            "headline": (chapter.get("headline") or "").strip(),
        }
        for chapter in (chapters or [])
        if isinstance(chapter, dict)
        and isinstance(chapter.get("start"), int)
        and isinstance(chapter.get("end"), int)
        and chapter["end"] > chapter["start"]
    ]

    boundaries.sort(key=lambda chapter: chapter["start"])
    return boundaries


def _locate(midpoint: int, boundaries: list[dict], index: int = 0) -> int:
    """
    Index of the chapter a timestamp falls in.

    Walks forward monotonically: gaps between chapters, text before the first
    chapter and text past the last one all attach to the nearest chapter
    instead of being dropped.
    """

    while index < len(boundaries) - 1 and midpoint >= boundaries[index]["end"]:
        index += 1
    return index


def _sentences(words: list[dict]) -> list[dict]:
    """
    Rebuild sentence-level units from AssemblyAI's word timestamps.

    `utterances` is null unless speaker labels were requested, so the closing
    punctuation on each word is the only sentence signal available. Fragments
    shorter than MIN_SENTENCE_CHARS are carried into the next sentence so a
    stray "Right." can't become a chunk of its own.
    """

    sentences = []
    current = []

    for word in words:
        if not word.get("text", "").strip():
            continue

        current.append(word)

        ends_sentence = word["text"][-1] in ".!?"
        too_short = len(" ".join(w["text"] for w in current)) < MIN_SENTENCE_CHARS

        if ends_sentence and not too_short:
            sentences.append(current)
            current = []

    if current:
        if sentences and len(" ".join(w["text"] for w in current)) < MIN_SENTENCE_CHARS:
            sentences[-1].extend(current)   # trailing stub belongs with the last sentence
        else:
            sentences.append(current)       # tail with no closing punctuation

    return [
        {
            "text": " ".join(w["text"] for w in group),
            "start_ms": group[0]["start"],
            "end_ms": group[-1]["end"],
        }
        for group in sentences
    ]


def _cosine_similarities(vectors: list[list[float]]) -> list[float]:
    """Cosine similarity between each vector and the one before it."""

    similarities = []

    for previous, current in zip(vectors, vectors[1:]):
        dot = sum(a * b for a, b in zip(previous, current))
        norm_previous = math.sqrt(sum(a * a for a in previous))
        norm_current = math.sqrt(sum(b * b for b in current))

        if not norm_previous or not norm_current:
            similarities.append(0.0)
        else:
            similarities.append(dot / (norm_previous * norm_current))

    return similarities


def _chapter_groups(sentences: list[dict], embeddings: list[list[float]], chapters):
    """
    Bucket (sentence, embedding) pairs into chapters, in order.

    Returns a single chapterless group when the transcript has no usable
    chapters — semantic splitting then works across the whole video.
    """

    boundaries = _boundaries(chapters)

    if not boundaries:
        return [{
            "chapter_index": -1,
            "chapter": "",
            "pairs": list(zip(sentences, embeddings)),
        }]

    groups = [
        {"chapter_index": index, "chapter": boundary["headline"], "pairs": []}
        for index, boundary in enumerate(boundaries)
    ]

    index = 0
    for sentence, embedding in zip(sentences, embeddings):
        midpoint = (sentence["start_ms"] + sentence["end_ms"]) // 2
        index = _locate(midpoint, boundaries, index)
        groups[index]["pairs"].append((sentence, embedding))

    return [group for group in groups if group["pairs"]]


def _semantic_split(pairs: list[tuple[dict, list[float]]]) -> list[list[dict]]:
    """
    Cut one chapter's sentences where the topic shifts.

    A break needs both a similarity dip AND enough text behind it, so a run of
    terse sentences can't shatter the chapter into fragments. An undersized
    leftover (typically the tail of a chapter) is then folded into the previous
    chunk when it still fits under MAX — otherwise it stays a short chunk of its
    own rather than pushing its neighbour over the cap.
    """

    similarities = _cosine_similarities([embedding for _, embedding in pairs])

    groups = []
    current = []

    for index, (sentence, _) in enumerate(pairs):
        if current:
            # similarities[i] compares sentence i with sentence i + 1, so the
            # topic gap in front of this sentence sits at index - 1.
            similarity = similarities[index - 1]
            size = len(" ".join(s["text"] for s in current))

            topic_shift = similarity < SIMILARITY_THRESHOLD and size >= MIN_CHUNK_CHARS
            overfull = size + len(sentence["text"]) + 1 > MAX_CHUNK_CHARS

            if topic_shift or overfull:
                groups.append(current)
                current = []

        current.append(sentence)

    if current:
        groups.append(current)

    merged = []
    for group in groups:
        size = len(" ".join(s["text"] for s in group))
        if merged and size < MIN_CHUNK_CHARS:
            previous_size = len(" ".join(s["text"] for s in merged[-1]))
            if previous_size + size + 1 <= MAX_CHUNK_CHARS:
                merged[-1].extend(group)
                continue
        merged.append(group)

    return merged


def _record(number: int, sentences: list[dict], group: dict, video_id: str, source_lang: str) -> dict:
    """One semantically split chunk, timestamped and tagged with its chapter."""

    return {
        "chunk_id": f"{video_id}_c{number:03}",
        "text": " ".join(sentence["text"] for sentence in sentences),
        "start_ms": sentences[0]["start_ms"],
        "end_ms": sentences[-1]["end_ms"],
        "source_lang": source_lang,
        # Chroma metadata must be a flat scalar — "" rather than None so the
        # key is always present, including on chapterless transcripts.
        "chapter": group["chapter"],
        "chapter_index": group["chapter_index"],
    }


def _window_record(number, current_words, start_ms, end_ms, boundaries, video_id, source_lang) -> dict:
    """One fixed-window chunk, still tagged with whichever chapter it landed in."""

    chapter_index, headline = -1, ""

    if boundaries:
        chapter_index = _locate((start_ms + end_ms) // 2, boundaries)
        headline = boundaries[chapter_index]["headline"]

    return {
        "chunk_id": f"{video_id}_c{number:03}",
        "text": " ".join(w["text"] for w in current_words),
        "start_ms": start_ms,
        "end_ms": end_ms,
        "source_lang": source_lang,
        "chapter": headline,
        "chapter_index": chapter_index,
    }


def _semantic_chunks(words, chapters, video_id, source_lang) -> tuple[list[dict], dict]:
    """
    Chapter-aware, semantic chunks for one transcript.

    Returns the chunks plus counts for the caller's progress line, so all
    printing happens outside this function's caller's try block.
    """

    sentences = _sentences(words)

    if not sentences:
        return [], {"sentences": 0, "chapters": 0}

    # One embedding pass over every sentence. These vectors only decide where
    # the topic shifts — the chunks themselves are embedded again on storage.
    embeddings = get_embeddings([sentence["text"] for sentence in sentences])

    # A short response would silently misalign (or drop) sentences below, so
    # refuse it: the caller falls back to windowing, which reads words directly.
    if len(embeddings) != len(sentences):
        raise ValueError(
            f"embedding API returned {len(embeddings)} vectors for {len(sentences)} sentences"
        )

    groups = _chapter_groups(sentences, embeddings, chapters)

    chunks = []
    for group in groups:
        for split in _semantic_split(group["pairs"]):
            chunks.append(_record(len(chunks) + 1, split, group, video_id, source_lang))

    return chunks, {"sentences": len(sentences), "chapters": len(groups)}


def _window_chunks(words, chapters, video_id, source_lang) -> list[dict]:
    """Legacy 45s windows with 5s overlap — the fallback when embeddings fail."""

    boundaries = _boundaries(chapters)

    chunks = []
    current_words = []
    chunk_start = None

    for word in words:
        if chunk_start is None:
            chunk_start = word["start"]

        current_words.append(word)

        duration = word["end"] - chunk_start

        if duration >= WINDOW_MS:
            chunks.append(_window_record(
                len(chunks) + 1, current_words, chunk_start, word["end"],
                boundaries, video_id, source_lang,
            ))

            overlap_start = word["end"] - OVERLAP_MS

            current_words = [
                w for w in current_words
                if w["end"] >= overlap_start
            ]

            chunk_start = current_words[0]["start"] if current_words else None

    if current_words:
        chunks.append(_window_record(
            len(chunks) + 1, current_words, chunk_start, current_words[-1]["end"],
            boundaries, video_id, source_lang,
        ))

    return chunks


def chunk_transcript(transcript_path: str, video_id: str):
    """
    Split an AssemblyAI transcript into retrievable chunks.

    Structure first: auto_chapters give hard topic boundaries. Semantics
    second: inside each chapter, sentences are cut at the points where the
    topic actually shifts. A chunk never crosses a chapter, and every chunk
    carries start/end timestamps plus the chapter it came from.

    Returns:
        {
            "video_id": "...",
            "chunks_path": "...",
            "chunks": [...],
            "strategy": "semantic" | "window"
        }
    """

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    words = transcript.get("words") or []
    chapters = transcript.get("chapters") or []
    source_lang = transcript.get("language_code", "en")

    strategy = "semantic"
    chunks = []

    if not words:
        print("Transcript has no word timestamps, nothing to chunk.")
    else:
        try:
            chunks, stats = _semantic_chunks(words, chapters, video_id, source_lang)
        except Exception as e:  # noqa: BLE001 — never fail ingestion over chunking
            strategy = "window"
            print(f"Semantic chunking unavailable ({type(e).__name__}: {e}), falling back to fixed windows.")
            chunks = _window_chunks(words, chapters, video_id, source_lang)
        else:
            # Plain ASCII: this runs in a Windows console where the default
            # code page can't encode arrows or other typographic characters.
            print(
                f"Semantic chunking: {stats['sentences']} sentences -> "
                f"{len(chunks)} chunks in {stats['chapters']} chapter(s)."
            )

    chunks_path = CHUNKS_DIR / f"{video_id}_chunks.json"

    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"Created {len(chunks)} chunks ({strategy}).")

    return {
        "video_id": video_id,
        "chunks_path": str(chunks_path),
        "chunks": chunks,
        "strategy": strategy,
    }
