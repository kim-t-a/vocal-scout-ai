import json
import chromadb

from services.embeddings import get_embeddings


client = chromadb.PersistentClient(path="chroma_db")


def store_chunks(chunks_path: str, video_id: str):
    """
    Create embeddings for every chunk and store them in
    a Chroma collection dedicated to this video.
    """

    collection_name = f"video_{video_id}"

    # Cosine space: makes Chroma's distances convertible to a 0-1 relevance
    # score (1 - distance), which the retriever uses for the off-topic guard.
    collection = client.get_or_create_collection(
        collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # One batched API call per ~32 chunks instead of one call per chunk.
    embeddings = get_embeddings([chunk["text"] for chunk in chunks])

    for chunk, embedding in zip(chunks, embeddings):

        collection.add(
            ids=[chunk["chunk_id"]],
            documents=[chunk["text"]],
            embeddings=[embedding],
            metadatas=[{
                "start_ms": chunk["start_ms"],
                "end_ms": chunk["end_ms"],
                "source_lang": chunk["source_lang"]
            }]
        )

    return {
        "collection": collection_name,
        "stored_chunks": len(chunks)
    }


def delete_collection(video_id: str):
    """
    Remove a video's Chroma collection entirely.

    Used when ingestion fails midway: a partially-filled collection would
    otherwise look "cached" to /process-video and serve an incomplete tutor
    forever.
    """

    client.delete_collection(f"video_{video_id}")