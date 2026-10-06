import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "nvidia/nemotron-3-super-120b-a12b"

MAX_RETRIES = 3
# An answer can take tens of seconds; keep the socket open while it streams.
REQUEST_TIMEOUT = 120


def _payload(prompt: str, stream: bool):
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are VocalScout."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "stream": stream,
    }


def _post(prompt: str, stream: bool):
    """
    POST to the chat API, retrying while the model is temporarily unavailable.

    NVIDIA answers 503 when the model is cold or busy, so back off and retry a
    few times. Returns the open response, or None when every attempt failed;
    either way the caller owns the response and must close it.
    """

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                CHAT_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json=_payload(prompt, stream),
                stream=stream,
                timeout=REQUEST_TIMEOUT,
            )
        except (requests.Timeout, requests.ConnectionError) as e:
            # NVIDIA sometimes just hangs instead of answering 503 — the read
            # times out client-side. Same treatment: back off and retry.
            print(f"NVIDIA {type(e).__name__}... retry {attempt + 1}/{MAX_RETRIES}")
            time.sleep(2)
            continue

        if response.status_code == 200:
            return response

        if response.status_code == 503:
            print(f"NVIDIA busy... retry {attempt + 1}/{MAX_RETRIES}")
            response.close()
            time.sleep(2)
            continue

        print(response.text)
        status = response.status_code
        response.close()
        raise requests.HTTPError(f"Chat API returned {status}")

    return None


def generate_answer(prompt: str):
    """Whole answer in one call. Returns None while the model stays unavailable."""

    response = _post(prompt, stream=False)

    if response is None:
        return None

    try:
        return response.json()["choices"][0]["message"]["content"]
    finally:
        response.close()


def stream_answer(prompt: str):
    """
    Yield the answer in chunks as the model writes it.

    Streaming mode makes the server emit one `data:` line per delta, ending
    with `data: [DONE]`. Yields nothing at all when the model never became
    available, so the caller can treat "no text" as a failure.
    """

    response = _post(prompt, stream=True)

    if response is None:
        return

    try:
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue

            data = line[len("data:"):].strip()

            if data == "[DONE]":
                break

            try:
                delta = json.loads(data)["choices"][0]["delta"]
            except (json.JSONDecodeError, IndexError, KeyError, TypeError):
                continue  # keep-alive, usage trailer, or malformed frame

            content = delta.get("content") if isinstance(delta, dict) else None
            if content:
                yield content
    finally:
        response.close()
