import chromadb

client = chromadb.PersistentClient(path="chroma_db")


def search_chunks(query_embedding, video_id: str, n_results: int = 3):
    """
    Search the Chroma collection belonging to one video.
    """

    collection_name = f"video_{video_id}"

    collection = client.get_collection(collection_name)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    documents = results["documents"][0]
    metadata = results["metadatas"][0]

    return {
        "context": "\n\n".join(documents),
        "timestamp": metadata[0]["start_ms"],
        "quote": documents[0][:200]
    }