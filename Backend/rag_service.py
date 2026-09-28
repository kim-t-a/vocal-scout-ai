import re

from services.embeddings import get_embedding
from services.retriever import search_chunks
from services.chat import generate_answer
import session


HISTORY_TURNS = 5          # conversation exchanges sent to the model
HISTORY_CHAR_BUDGET = 2000  # rough cap so history can't crowd out the transcript


def parse_quiz(text: str):
    """
    Parse the model's quiz text into structured questions.

    Expects pairs like:
        1. What is a list?
        Answer: An ordered, mutable collection of items.

    Tolerates markdown bolding ("**1. Question**", "**Answer:** ...") and
    multi-line questions/answers. Returns a list of
    {"question": str, "answer": str}, or None when nothing usable parses
    (caller falls back to showing the raw text as a plain answer).
    """

    questions = []
    current = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        answer_match = re.match(
            r"^\*{0,2}answer\*{0,2}\s*[:\-]\s*(.+)$", line, re.IGNORECASE
        )
        if answer_match and current is not None:
            current["answer"] = (current.get("answer") or "") + answer_match.group(1).strip().rstrip("*").strip()
            questions.append(current)
            current = None
            continue

        question_match = re.match(
            r"^\*{0,2}(?:question\s*)?\d{1,2}[\.\)]\s*(.+?)\*{0,2}$", line
        )
        if question_match:
            current = {"question": question_match.group(1).strip(), "answer": None}
            continue

        # Continuation of the previous question or answer line
        if current is not None:
            if current.get("answer") is None:
                current["question"] += " " + line
            else:
                current["answer"] += " " + line

    if current is not None:
        questions.append(current)  # unanswered trailing question -> filtered below

    questions = [q for q in questions if q["question"] and q.get("answer")]

    return questions or None


def build_history_block(history: list[dict] | None) -> str:
    """Render the recent conversation for the prompt, newest last."""

    turns = [
        h for h in (history or [])
        if isinstance(h, dict)
        and h.get("role") in ("user", "assistant")
        and isinstance(h.get("content"), str)
        and h.get("content").strip()
    ][-HISTORY_TURNS:]

    if not turns:
        return ""

    lines = []
    budget = HISTORY_CHAR_BUDGET
    for turn in reversed(turns):  # keep the newest turns if over budget
        label = "Viewer" if turn["role"] == "user" else "Tutor"
        line = f"{label}: {turn['content'].strip()}"
        if len(line) > budget:
            break
        budget -= len(line)
        lines.append(line)

    return "Earlier in this conversation (newest last):\n" + "\n".join(reversed(lines))


def ask(question: str, plan=None, video_id: str | None = None, history: list[dict] | None = None):
    if video_id is None:
        video_id = session.ACTIVE_VIDEO_ID

    if video_id is None:
        return {
            "type": "notice",
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
{build_history_block(history)}
Transcript:
{retrieved["context"]}

Question:
{question}
{style_instructions}
"""

    answer = generate_answer(prompt)

    if answer is None:
        return {
            "type": "error",
            "answer": "The AI tutor is temporarily busy. Please try again in a moment.",
            "timestamp": 0,
            "quote": ""
        }

    # Quiz mode: try to hand the frontend structured questions it can render
    # as an interactive quiz. Fall back to plain text if parsing fails.
    if plan is not None and plan.strategy == "quiz":
        questions = parse_quiz(answer)
        if questions:
            return {
                "type": "quiz",
                "questions": questions,
                "answer": answer,  # raw text, kept for history / fallback
                "timestamp": retrieved["timestamp"],
                "quote": retrieved["quote"],
            }

    return {
        "type": "answer",
        "answer": answer,
        "timestamp": retrieved["timestamp"],           # Milliseconds (frontend expects ms)
        "quote": retrieved["quote"],
    }
