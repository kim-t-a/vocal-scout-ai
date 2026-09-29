import json
import re

from services.embeddings import get_embedding
from services.retriever import search_chunks
from services.chat import generate_answer
import session


HISTORY_TURNS = 5          # conversation exchanges sent to the model
HISTORY_CHAR_BUDGET = 2000  # rough cap so history can't crowd out the transcript

# Best chunk's cosine similarity must clear this, else the question is
# treated as off-topic for the video. Conservative: better to admit "not
# covered" than to confidently hallucinate from weak context.
OFF_TOPIC_THRESHOLD = 0.35


def parse_quiz_json(text: str):
    """
    Parse the model's quiz output into structured multiple-choice questions.

    The prompt demands a bare JSON array, but models occasionally wrap it in
    markdown fences or prose — so extract the first JSON array substring,
    then validate the shape strictly. Returns a list of
    {"question": str, "options": [4 strings], "answer_index": int}
    or None when nothing usable parses (caller falls back to plain text).
    """

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, list):
        return None

    questions = []
    for item in data:
        if not isinstance(item, dict):
            continue
        question = item.get("question")
        options = item.get("options")
        index = item.get("answer_index")

        if not isinstance(question, str) or not question.strip():
            continue
        if (
            not isinstance(options, list)
            or len(options) < 2
            or not all(isinstance(o, str) and o.strip() for o in options)
        ):
            continue
        if not isinstance(index, int) or not 0 <= index < len(options):
            continue

        questions.append({
            "question": question.strip(),
            "options": [o.strip() for o in options],
            "answer_index": index,
        })

    return questions or None


def build_suggestions(answer: str) -> list[str]:
    """
    Clickable follow-up questions shown under the latest answer.

    Deterministic, template-based — cheap and never wrong. Draw from the
    answer text itself where possible so the suggestions feel relevant.
    """

    words = re.findall(r"[a-zA-Z']{4,}", answer.lower())
    stop = {
        "this", "that", "with", "from", "have", "what", "when", "your",
        "about", "which", "there", "their", "would", "could", "should",
        "these", "those", "because", "video", "transcript", "answer",
    }
    keywords = [w for w in words if w not in stop]

    # Longest keywords first — they tend to be the most specific/meaningful.
    keyword = keywords[0] if keywords else "this topic"
    seen = set()
    suggestions = [
        f"Explain {keyword} more simply",
        f"Give me an example of {keyword}",
        f"Quiz me on {keyword}",
    ]
    return [s for s in suggestions if not (s in seen or seen.add(s))]


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

    # Off-topic guard: the best chunk doesn't resemble the question closely
    # enough for this video to plausibly contain an answer. score is None for
    # legacy l2 collections — skip the check rather than guess.
    score = retrieved.get("score")
    if score is not None and score < OFF_TOPIC_THRESHOLD:
        return {
            "type": "notice",
            "answer": (
                "That doesn't seem to be covered in this video. "
                "Try asking about something the video explains."
            ),
            "timestamp": 0,
            "quote": ""
        }

    # Shape the answer with the planner's lesson plan when available
    style_instructions = ""
    if plan is not None:
        if plan.strategy == "quiz":
            style_instructions = """
Mode: QUIZ. Test the viewer on the transcript content.
- Respond with ONLY a JSON array — no prose before or after, no markdown fences.
- Write exactly 3 multiple-choice questions based ONLY on the transcript below.
- Exact JSON shape:
  [{"question": "...", "options": ["...", "...", "...", "..."], "answer_index": 0}]
- "answer_index" is the 0-based index of the correct option.
- Exactly 4 options per question; exactly one correct.
- Distractors must be plausible but clearly wrong to someone who watched.
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

    # Quiz mode: the model returns strict JSON which we validate and hand to
    # the frontend as structured multiple-choice questions. If parsing fails
    # we fall back to showing the raw text as a plain answer.
    if plan is not None and plan.strategy == "quiz":
        questions = parse_quiz_json(answer)
        if questions:
            return {
                "type": "quiz",
                "questions": questions,  # {question, options[4], answer_index}
                "answer": answer,        # raw text, kept for history / fallback
                "timestamp": retrieved["timestamp"],
                "quote": retrieved["quote"],
            }

    return {
        "type": "answer",
        "answer": answer,
        "timestamp": retrieved["timestamp"],           # Milliseconds (frontend expects ms)
        "quote": retrieved["quote"],
        "suggestions": build_suggestions(answer),
    }
