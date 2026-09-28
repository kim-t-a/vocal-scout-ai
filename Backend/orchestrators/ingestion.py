from ingest import download_audio
from services.transcriber import transcribe_audio
from services.chunker import chunk_transcript
from services.vector_store import store_chunks

import processing


class IngestionOrchestrator:

    def process_video(self, url: str, video_id: str):

        print("\n========== INGESTION STARTED ==========")

        # Step 1 — set status BEFORE the work so the UI reflects reality
        processing.video_status[video_id] = {"status": "downloading"}
        print("Step 1/5: Downloading...")

        video = download_audio(url)

        # Step 2
        processing.video_status[video_id] = {"status": "transcribing"}
        print("Step 2/5: Transcribing...")

        transcript = transcribe_audio(
            video["audio_path"],
            video_id
        )

        # Step 3
        processing.video_status[video_id] = {"status": "chunking"}
        print("Step 3/5: Chunking...")

        chunk_result = chunk_transcript(
            transcript["transcript_path"],
            video_id
        )

        print(f"Created {len(chunk_result['chunks'])} chunks.")

        # Step 4
        processing.video_status[video_id] = {"status": "embedding"}
        print("Step 4/5: Embedding...")

        vector_result = store_chunks(
            chunk_result["chunks_path"],
            video_id
        )

        print(
            f"Stored {vector_result['stored_chunks']} chunks "
            f"in {vector_result['collection']}."
        )

        # Step 5
        processing.video_status[video_id] = {
            "status": "ready",
            "collection": vector_result["collection"]
        }
        print("Step 5/5: Finished.")

        return {
            "status": "ready",
            "video_id": video_id,
            "title": video["title"],
            "audio_path": video["audio_path"],
            "transcript_path": transcript["transcript_path"],
            "chunks_path": chunk_result["chunks_path"],
            "collection": vector_result["collection"],
            "stored_chunks": vector_result["stored_chunks"],
            "chunks_created": len(chunk_result["chunks"]),
        }
