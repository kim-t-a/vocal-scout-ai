import json
import re

from services.embeddings import get_embedding
from services.retriever import search_chunks
from services.chat import generate_answer, stream_answer
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


def _notice(answer: str):
    """A response that never reached the model (no video, off-topic, still building)."""

    return {
        "type": "notice",
        "answer": answer,
        "timestamp": 0,
        "quote": ""
    }


def _busy_response():
    """The model produced nothing — rendered like any other transient failure."""

    return {
        "type": "error",
        "answer": "The AI tutor is temporarily busy. Please try again in a moment.",
        "timestamp": 0,
        "quote": ""
    }


def _prepare(question: str, plan=None, video_id: str | None = None, history: list[dict] | None = None):
    """
    Shared front half of `ask` and `ask_stream`: resolve the video, retrieve the
    transcript context and build the model prompt.

    Returns (early_response, retrieved, prompt). `early_response` is a finished
    response dict when the question must not reach the model (no video selected,
    or the topic isn't in the transcript); otherwise it is None.
    """

    if video_id is None:
        video_id = session.ACTIVE_VIDEO_ID

    if video_id is None:
        return _notice("Please process a YouTube video first."), None, None

    query_embedding = get_embedding(question)

    retrieved = search_chunks(
        query_embedding,
        question,
        video_id
    )

    # Off-topic guard: the best chunk doesn't resemble the question closely
    # enough for this video to plausibly contain an answer. score is None for
    # legacy l2 collections — skip the check rather than guess.
    score = retrieved.get("score")
    if score is not None and score < OFF_TOPIC_THRESHOLD:
        return _notice(
            "That doesn't seem to be covered in this video. "
            "Try asking about something the video explains."
        ), None, None

    # Shape the answer with the planner's lesson plan when available
    style_instructions = ""
    if plan is not None:
        if plan.strategy == "quiz":
            count = getattr(plan, "quiz_count", 3)
            style_instructions = f"""
Mode: QUIZ. Test the viewer on the transcript content.
- Respond with ONLY a JSON array — no prose before or after, no markdown fences.
- Write exactly {count} multiple-choice questions based ONLY on the transcript below.
- Exact JSON shape:
  [{{"question": "...", "options": ["...", "...", "...", "..."], "answer_index": 0}}]
- "answer_index" is the 0-based index of the correct option.
- Exactly 4 options per question; exactly one correct.

What makes a question RELEVANT (quiz the CONTENT, not the video itself):
- Test the subject matter the video teaches — its concepts, how they work,
  when to use them, and why they matter.
- FORBIDDEN — questions about the video or creator as an artifact: what the
  creator suggests doing next, what viewers should watch after this, how the
  course/video is structured, what the speaker said about learning itself,
  promotional or meta-commentary. If a question could be answered WITHOUT
  understanding the subject matter, it is irrelevant — drop it.
- No trivia about exact wording someone said; no fill-in-the-blank of a
  sentence from the transcript.

How to write the questions (this is what makes them feel natural):
- Sound like a friendly tutor quizzing a friend — never like an exam paper.
  FORBIDDEN phrases: "as stated in the video", "according to the transcript",
  "in this lesson", "the speaker mentions".
- Mix up the styles across the {count} questions, for example:
  one direct concept check ("What happens to a tuple once it's created?"),
  one scenario ("Which would you reach for when the data must not change?"),
  one practical ("Why might you pick one over the other in real code?").
- Keep each question under 20 words and self-contained — the reader sees only
  the question, not the transcript.
- Distractors must be plausible but clearly wrong to someone who watched.
- If the request is a general "quiz me" with no specific topic, quiz on the
  most important ideas across the transcript. Otherwise quiz on the topic
  the user asked about, and never answer their question directly."""
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

    return None, retrieved, prompt


def ask(question: str, plan=None, video_id: str | None = None, history: list[dict] | None = None):
    """Whole answer in one response — used by /ask and by quiz mode."""

    early, retrieved, prompt = _prepare(question, plan, video_id, history)

    if early is not None:
        return early

    answer = generate_answer(prompt)

    if answer is None:
        return _busy_response()

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


def ask_stream(question: str, plan=None, video_id: str | None = None, history: list[dict] | None = None):
    """
    Same answer as `ask`, but emitted while the model is still writing it.

    Yields dicts shaped like the /ask response. The frontend appends `token`
    text to the growing message and treats any other type as final:
      {"type": "meta", ...}        sent first, before any text
      {"type": "token", ...}       repeated as the answer arrives
      {"type": "suggestions", ...} follow-up chips once it's finished
      {"type": "quiz"|"notice"|"error", ...}  single-shot responses
    """

    early, retrieved, prompt = _prepare(question, plan, video_id, history)

    if early is not None:
        yield early
        return

    yield {
        "type": "meta",
        "timestamp": retrieved["timestamp"],
        "quote": retrieved["quote"],
    }

    # A quiz renders as an interactive card, not as prose — streaming half a
    # JSON array at the viewer would only flicker. Build it in one shot.
    if plan is not None and plan.strategy == "quiz":
        yield from _stream_quiz(prompt)
        return

    collected = []

    for delta in stream_answer(prompt):
        collected.append(delta)
        yield {"type": "token", "text": delta}

    answer = "".join(collected).strip()

    if not answer:
        yield _busy_response()
        return

    yield {
        "type": "suggestions",
        "suggestions": build_suggestions(answer),
    }


def _stream_quiz(prompt: str):
    """Quiz questions can't be shown until the JSON parses, so buffer them."""

    answer = generate_answer(prompt)

    if answer is None:
        yield _busy_response()
        return

    # Unparseable JSON falls back to the raw text so the viewer isn't stuck.
    questions = parse_quiz_json(answer)

    if questions:
        yield {
            "type": "quiz",
            "questions": questions,
            "answer": answer,
        }
        return

    yield {"type": "token", "text": answer}
    yield {
        "type": "suggestions",
        "suggestions": build_suggestions(answer),
    }
