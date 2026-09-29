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
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadata = results["metadatas"][0]
    distances = results["distances"][0]

    # Relevance score in [0, 1] — higher is better. Only meaningful for
    # collections created with cosine space (vector_store does this now).
    # Legacy l2 collections report hnswlib's squared euclidean distance,
    # which can't be converted reliably, so they report no score and the
    # caller skips the off-topic check for them.
    space = (collection.metadata or {}).get("hnsw:space", "l2")
    score = (1.0 - distances[0]) if space == "cosine" else None

    return {
        "context": "\n\n".join(documents),
        "timestamp": metadata[0]["start_ms"],
        "quote": documents[0][:200],
        "score": score,
    }