from services.embeddings import get_embedding
from services.retriever import search_chunks
from services.chat import generate_answer
import session


def ask(question: str, plan=None, video_id: str | None = None):
    if video_id is None:
        video_id = session.ACTIVE_VIDEO_ID

    if video_id is None:
        return {
            "answer": "Please process a YouTube video first.",
            "timestamp": 0,
            "quote": ""
        }

    query_embedding = get_embedding(question)

    retrieved = search_chunks(
        query_embedding,
        video_id
    )

    # Shape the answer with the planner's lesson plan when available
    style_instructions = ""
    if plan is not None:
        if plan.strategy == "quiz":
            style_instructions = """
Mode: QUIZ. Test the viewer on the transcript content.
- Write exactly 3 numbered questions based ONLY on the transcript below.
- EVERY question MUST be immediately followed by a line in the exact format:
  Answer: <the correct answer, stated fully>
- Never leave an Answer line empty.
- Do not answer the user's question directly; quiz them on the topic they asked about."""
        else:
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
