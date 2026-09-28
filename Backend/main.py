from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tutor_engine import TutorEngine
from services.video_manager import VideoManager
from orchestrators.ingestion import IngestionOrchestrator

import session
import processing

app = FastAPI()

engine = TutorEngine()
video_manager = VideoManager()
ingestion = IngestionOrchestrator()

# Allow React (Vite) to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    question: str
    video_id: str | None = None


class VideoRequest(BaseModel):
    url: str


@app.get("/")
def home():
    return {"status": "VocalScout running"}


@app.post("/ask")
def ask_question(data: Question):
    return engine.run(data.question, data.video_id)


@app.post("/process-video")
def process_video(data: VideoRequest, background_tasks: BackgroundTasks):

    # Extract YouTube ID
    video_id = video_manager.extract_video_id(data.url)

    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL."
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
        "collection": collection,
    }


@app.get("/video-status/{video_id}")
def video_status(video_id: str):
    return processing.video_status.get(
        video_id,
        {"status": "not_found"}
    )


@app.get("/current-video")
def current_video():
    return {
        "video_id": session.ACTIVE_VIDEO_ID,
        "url": session.ACTIVE_VIDEO_URL
    }