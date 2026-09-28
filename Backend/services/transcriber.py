import os
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"

HEADERS = {
    "authorization": API_KEY
}

TRANSCRIPTS_DIR = Path("transcripts")
TRANSCRIPTS_DIR.mkdir(exist_ok=True)


def delete_audio(audio_path: str):
    """Remove a downloaded audio file — it's not needed once transcribed."""

    try:
        Path(audio_path).unlink(missing_ok=True)
        print(f"Deleted audio file: {audio_path}")
    except OSError as e:
        # Cleanup is best-effort; never fail ingestion over it
        print(f"Could not delete audio file {audio_path}: {e}")


def transcribe_audio(audio_path: str, video_id: str):
    """
    Upload an audio file to AssemblyAI and save the transcript.
    The local audio file is deleted afterwards (success or failure) —
    only the transcript is needed from here on.

    Returns:
        {
            "video_id": "...",
            "transcript_path": "...",
            "text": "..."
        }
    """

    print("Uploading audio...")

    try:
        with open(audio_path, "rb") as f:
            upload_response = requests.post(
                UPLOAD_URL,
                headers=HEADERS,
                data=f
            )

        upload_response.raise_for_status()

        audio_url = upload_response.json()["upload_url"]
        print("Audio uploaded.")

        print("Starting transcription...")

        transcript_response = requests.post(
            TRANSCRIPT_URL,
            headers=HEADERS,
            json={
                "audio_url": audio_url,
                "auto_chapters": True,
                "punctuate": True,
                "format_text": True
            }
        )

        transcript_response.raise_for_status()

        transcript_id = transcript_response.json()["id"]
        status_url = f"{TRANSCRIPT_URL}/{transcript_id}"

        while True:
            status_response = requests.get(
                status_url,
                headers=HEADERS
            )

            status_response.raise_for_status()

            result = status_response.json()

            print("Status:", result["status"])

            if result["status"] == "completed":
                break

            if result["status"] == "error":
                raise Exception(result["error"])

            time.sleep(3)
    finally:
        # The audio is never needed again — free the disk either way.
        delete_audio(audio_path)

    transcript_path = TRANSCRIPTS_DIR / f"{video_id}.json"

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Transcript saved to {transcript_path}")

    return {
        "video_id": video_id,
        "transcript_path": str(transcript_path),
        "text": result["text"],
    }