import json
import chromadb

from services.embeddings import get_embedding


client = chromadb.PersistentClient(path="chroma_db")


def store_chunks(chunks_path: str, video_id: str):
    """
    Create embeddings for every chunk and store them in
    a Chroma collection dedicated to this video.
    """

    collection_name = f"video_{video_id}"

    collection = client.get_or_create_collection(collection_name)

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    for chunk in chunks:

        embedding = get_embedding(chunk["text"])

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