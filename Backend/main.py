from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from tutor_engine import TutorEngine
from services.video_manager import VideoManager
from orchestrators.ingestion import IngestionOrchestrator

import os
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


class VideoRequest(BaseModel):
    url: str


@app.get("/")
def home():
    return {"status": "VocalScout running"}


@app.post("/ask")
@limiter.limit("30/minute")
def ask_question(request: Request, data: Question):
    return engine.run(data.question, data.video_id, data.history)


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


@app.get("/video-status/{video_id}")
def video_status(video_id: str):
    return processing.video_status.get(
        video_id,
        {"status": "not_found", "detail": "No processing run found for this video."}
    )


@app.get("/current-video")
def current_video():
    return {
        "video_id": session.ACTIVE_VIDEO_ID,
        "url": session.ACTIVE_VIDEO_URL
    }