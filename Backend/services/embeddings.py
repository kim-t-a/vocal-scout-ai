import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")

EMBED_URL = "https://integrate.api.nvidia.com/v1/embeddings"


def get_embedding(text: str):
    response = requests.post(
        EMBED_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "nvidia/nemotron-3-embed-1b",
            "input": [text],
            "input_type": "query",
            "modality": "text",
            "encoding_format": "float",
        },
    )

    if response.status_code != 200:
        print("Embedding error:", response.status_code)
        print(response.text)

    response.raise_for_status()
    return response.json()["data"][0]["embedding"]