from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from tutor_engine import TutorEngine
from services.video_manager import VideoManager
from orchestrators.ingestion import IngestionOrchestrator

import json
import os
from pathlib import Path

import session
import processing

app = FastAPI()

# Rate limiting — the pipeline calls paid APIs (AssemblyAI, NVIDIA), so one
# noisy client could drain the quota. Limits are per client IP.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

engine = TutorEngine()
video_manager = VideoManager()
ingestion = IngestionOrchestrator()

# CORS: dev servers often change ports (5173 -> 5174, preview, LAN testing).
# Default to allowing any origin locally; lock down with CORS_ORIGINS in prod,
# e.g. CORS_ORIGINS="https://myapp.com,https://www.myapp.com"
_origins = os.getenv("CORS_ORIGINS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()]
        if _origins else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    question: str
    video_id: str | None = None
    # Recent conversation so follow-up questions ("why?", "and for tuples?")
    # can be understood. Each item: {"role": "user"|"assistant", "content": str}
    history: list[dict] | None = None
    # How many questions a quiz request should generate (None = default 3)
    quiz_count: int | None = None


class VideoRequest(BaseModel):
    url: str


@app.get("/")
def home():
    return {"status": "VocalScout running"}


@app.post("/ask")
@limiter.limit("30/minute")
def ask_question(request: Request, data: Question):
    return engine.run(data.question, data.video_id, data.history, data.quiz_count)


@app.post("/process-video")
@limiter.limit("10/hour")
def process_video(request: Request, data: VideoRequest, background_tasks: BackgroundTasks):

    # Extract YouTube ID
    video_id = video_manager.extract_video_id(data.url)

    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Try a youtube.com/watch, youtube.com/shorts, or youtu.be link."
        )

    collection = video_manager.collection_name(video_id)

    # If already processed
    if video_manager.collection_exists(video_id):

        session.ACTIVE_VIDEO_ID = video_id
        session.ACTIVE_VIDEO_URL = data.url

        processing.video_status[video_id] = {
            "status": "ready",
            "collection": collection
        }

        return {
            "status": "cached",
            "video_id": video_id,
            "collection": collection,
        }

    # Mark as queued
    processing.video_status[video_id] = {
        "status": "queued"
    }

    # Remember current video
    session.ACTIVE_VIDEO_ID = video_id
    session.ACTIVE_VIDEO_URL = data.url

    # Run the ingestion pipeline in the background
    background_tasks.add_task(
        ingestion.process_video,
        data.url,
        video_id
    )

    return {
        "status": "processing",
        "video_id": video_id,
    }


def _sse(event: dict) -> str:
    """Encode one event as a Server-Sent Events frame."""

    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.post("/ask-stream")
@limiter.limit("30/minute")
def ask_question_stream(request: Request, data: Question):
    """
    The question from /ask, but answered as the tutor writes it.

    Server-Sent Events: one JSON frame per event — `meta` (timestamp + quote),
    then `token` deltas, then `suggestions`/`quiz`. Always terminated by a
    `done` frame so the client can tell a finished answer from a dropped
    connection.
    """

    def event_stream():
        try:
            for event in engine.run_stream(
                data.question, data.video_id, data.history, data.quiz_count
            ):
                yield _sse(event)
        except Exception as exc:
            # Streaming may already be under way, so the failure can't become an
            # HTTP status any more — report it in-band as an error card instead.
            print(f"/ask-stream failed: {exc}")
            yield _sse({
                "type": "error",
                "answer": "The AI tutor is temporarily busy. Please try again in a moment.",
                "timestamp": 0,
                "quote": "",
            })

        yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Ask proxies (nginx, cloudflared…) to pass frames straight through.
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/video-status/{video_id}")
def video_status(video_id: str):
    return processing.video_status.get(
        video_id,
        {"status": "not_found", "detail": "No processing run found for this video."}
    )


@app.get("/transcript/{video_id}")
def transcript(video_id: str):
    """
    The video's timestamped transcript chunks, for the clickable transcript
    panel. Served straight from the chunker's on-disk output — no database,
    same file the embeddings were built from.
    """

    chunks_path = Path("chunks") / f"{video_id}_chunks.json"

    if not chunks_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No transcript stored for this video yet — process the video first.",
        )

    try:
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except (json.JSONDecodeError, OSError):
        raise HTTPException(
            status_code=500,
            detail="The transcript file for this video is corrupted — process the video again.",
        )

    normalized = [
        {
            "chunk_id": chunk.get("chunk_id", ""),
            "text": chunk.get("text", ""),
            "start_ms": chunk.get("start_ms", 0),
            "end_ms": chunk.get("end_ms", 0),
            # Legacy chunks predate chapter metadata — normalize so the
            # frontend contract holds for every video.
            "chapter": chunk.get("chapter", ""),
            "chapter_index": chunk.get("chapter_index", -1),
        }
        for chunk in chunks
        if isinstance(chunk, dict)
    ]
    normalized.sort(key=lambda chunk: chunk["start_ms"])

    return {"video_id": video_id, "chunks": normalized}


@app.get("/current-video")
def current_video():
    return {
        "video_id": session.ACTIVE_VIDEO_ID,
        "url": session.ACTIVE_VIDEO_URL
    }