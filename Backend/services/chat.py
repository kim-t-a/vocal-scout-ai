import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def generate_answer(prompt: str):
    MAX_RETRIES = 3
    response = None

    for attempt in range(MAX_RETRIES):
        response = requests.post(
            CHAT_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "nvidia/nemotron-3-super-120b-a12b",
                "messages": [
                    {"role": "system", "content": "You are VocalScout."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
        )

        if response.status_code == 200:
            break

        if response.status_code == 503:
            print(f"NVIDIA busy... retry {attempt+1}/{MAX_RETRIES}")
            time.sleep(2)
            continue

        print(response.text)
        response.raise_for_status()

    if response.status_code != 200:
        return None

    return response.json()["choices"][0]["message"]["content"]