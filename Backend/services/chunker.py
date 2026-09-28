import json
from pathlib import Path

WINDOW_MS = 45000      # 45 seconds
OVERLAP_MS = 5000      # 5 seconds

CHUNKS_DIR = Path("chunks")
CHUNKS_DIR.mkdir(exist_ok=True)


def chunk_transcript(transcript_path: str, video_id: str):
    """
    Split an AssemblyAI transcript into overlapping chunks.

    Returns:
        {
            "video_id": "...",
            "chunks_path": "...",
            "chunks": [...]
        }
    """

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    words = transcript["words"]

    chunks = []
    current_words = []
    chunk_start = None

    for word in words:

        if chunk_start is None:
            chunk_start = word["start"]

        current_words.append(word)

        duration = word["end"] - chunk_start

        if duration >= WINDOW_MS:

            chunks.append({
                "chunk_id": f"{video_id}_c{len(chunks)+1:03}",
                "text": " ".join(w["text"] for w in current_words),
                "start_ms": chunk_start,
                "end_ms": word["end"],
                "source_lang": transcript.get("language_code", "en")
            })

            overlap_start = word["end"] - OVERLAP_MS

            current_words = [
                w for w in current_words
                if w["end"] >= overlap_start
            ]

            chunk_start = current_words[0]["start"] if current_words else None

    if current_words:
        chunks.append({
            "chunk_id": f"{video_id}_c{len(chunks)+1:03}",
            "text": " ".join(w["text"] for w in current_words),
            "start_ms": chunk_start,
            "end_ms": current_words[-1]["end"],
            "source_lang": transcript.get("language_code", "en")
        })

    chunks_path = CHUNKS_DIR / f"{video_id}_chunks.json"

    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"Created {len(chunks)} chunks.")

    return {
        "video_id": video_id,
        "chunks_path": str(chunks_path),
        "chunks": chunks
    }