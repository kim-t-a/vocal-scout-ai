import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")

EMBED_URL = "https://integrate.api.nvidia.com/v1/embeddings"

BATCH_SIZE = 32   # texts per API call
MAX_RETRIES = 3   # retry 503s with backoff, same policy as chat.py


def _request_embeddings(texts: list[str], input_type: str):
    """One embeddings API call for a list of texts, with 503 retry."""

    payload = {
        "model": "nvidia/nemotron-3-embed-1b",
        "input": texts,
        "input_type": input_type,   # "query" for questions, "passage" for storage
        "modality": "text",
        "encoding_format": "float",
    }

    for attempt in range(MAX_RETRIES):
        response = requests.post(
            EMBED_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if response.status_code == 200:
            # API returns data in input order: data[i] corresponds to texts[i]
            return [item["embedding"] for item in response.json()["data"]]

        if response.status_code == 503:
            print(f"Embedding API busy... retry {attempt + 1}/{MAX_RETRIES}")
            time.sleep(2)
            continue

        print("Embedding error:", response.status_code)
        print(response.text)
        response.raise_for_status()

    response.raise_for_status()   # exhausted retries on 503


def get_embedding(text: str):
    """Embed a single query text (kept for the question side of RAG)."""
    return _request_embeddings([text], input_type="query")[0]


def get_embeddings(texts: list[str]):
    """
    Embed many texts in batches. Returns embeddings in the same order as the
    input list. "passage" input type matches how the texts will be stored.
    """

    all_embeddings = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        all_embeddings.extend(_request_embeddings(batch, input_type="passage"))
        print(f"Embedded {min(start + BATCH_SIZE, len(texts))}/{len(texts)} chunks")
    return all_embeddings