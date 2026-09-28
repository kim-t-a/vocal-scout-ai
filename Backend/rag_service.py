from services.embeddings import get_embedding
from services.retriever import search_chunks
from services.chat import generate_answer
import session


def ask(question: str, plan=None):
    if session.ACTIVE_VIDEO_ID is None:
        return {
            "answer": "Please process a YouTube video first.",
            "timestamp": 0,
            "quote": ""
        }

    query_embedding = get_embedding(question)

    retrieved = search_chunks(
        query_embedding,
        session.ACTIVE_VIDEO_ID
    )

    # Shape the answer with the planner's lesson plan when available
    style_instructions = ""
    if plan is not None:
        style_instructions = "\nStructure your answer by covering, in order: " + \
            ", ".join(plan.order) + "."

    prompt = f"""
You are VocalScout, a friendly AI tutor.

Answer ONLY using the transcript below.

Transcript:
{retrieved["context"]}

Question:
{question}
{style_instructions}
"""

    answer = generate_answer(prompt)

    if answer is None:
        answer = "The AI tutor is temporarily busy."

    return {
    "answer": answer,
    "timestamp": retrieved["timestamp"],           # Milliseconds (frontend expects ms)
    "quote": retrieved["quote"],
}