from ingest import download_audio
from services.transcriber import transcribe_audio
from services.chunker import chunk_transcript
from services.vector_store import store_chunks, delete_collection

import processing


class IngestionOrchestrator:

    def process_video(self, url: str, video_id: str):

        print("\n========== INGESTION STARTED ==========")

        try:
            return self._run(url, video_id)
        except ValueError as e:
            # Friendly, user-facing errors (bad/unavailable video, etc.)
            processing.video_status[video_id] = {
                "status": "error",
                "detail": str(e),
            }
            print(f"INGESTION FAILED: {e}")
        except Exception as e:  # noqa: BLE001 — background task must never die silently
            processing.video_status[video_id] = {
                "status": "error",
                "detail": "Something went wrong while building this tutor. Check the server logs.",
            }
            print(f"INGESTION CRASHED: {type(e).__name__}: {e}")
        finally:
            # Any failure after storage began can leave a PARTIAL collection
            # behind — /process-video would then report it as "cached" forever
            # and serve an incomplete tutor. Remove it so the next attempt
            # starts clean. On success _run has already returned, so the
            # status check below distinguishes the two cases.
            if processing.video_status.get(video_id, {}).get("status") == "error":
                try:
                    delete_collection(video_id)
                    print(f"Deleted partial collection for {video_id}.")
                except Exception as cleanup_error:  # noqa: BLE001
                    print(f"Could not delete partial collection: {cleanup_error}")

        return {
            "status": "error",
            "video_id": video_id,
            "detail": processing.video_status[video_id]["detail"],
        }

    def _run(self, url: str, video_id: str):
        print("Step 1/5: Downloading...")

        processing.video_status[video_id] = {"status": "downloading"}
        video = download_audio(url)

        # Step 2
        processing.video_status[video_id] = {"status": "transcribing"}
        print("Step 2/5: Transcribing...")
        transcript = transcribe_audio(video["audio_path"], video_id)

        # Step 3
        processing.video_status[video_id] = {"status": "chunking"}
        print("Step 3/5: Chunking...")
        chunk_result = chunk_transcript(transcript["transcript_path"], video_id)
        print(
            f"Created {len(chunk_result['chunks'])} chunks "
            f"({chunk_result['strategy']} chunking)."
        )

        # Step 4
        processing.video_status[video_id] = {"status": "embedding"}
        print("Step 4/5: Embedding...")
        vector_result = store_chunks(chunk_result["chunks_path"], video_id)
        print(
            f"Stored {vector_result['stored_chunks']} chunks "
            f"in {vector_result['collection']}."
        )

        # Step 5
        processing.video_status[video_id] = {
            "status": "ready",
            "collection": vector_result["collection"],
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
            "chunking_strategy": chunk_result["strategy"],
        }
