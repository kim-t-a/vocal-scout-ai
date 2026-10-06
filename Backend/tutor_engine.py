import processing
import session

from agents.intent import IntentAgent
from agents.planner import PlannerAgent
from rag_service import ask, ask_stream
from services.video_manager import VideoManager


def _notice(answer: str) -> dict:
    """A response that never reaches the model (nothing to answer yet)."""

    return {
        "type": "notice",
        "answer": answer,
        "timestamp": 0,
        "quote": ""
    }


class TutorEngine:

    def __init__(self):
        self.intent_agent = IntentAgent()
        self.planner_agent = PlannerAgent()
        self.video_manager = VideoManager()

    def _resolve(self, question: str, video_id: str | None = None, history: list[dict] | None = None, quiz_count: int | None = None):
        """
        Front half shared by run() and run_stream(): pick the video, make sure
        its tutor is built, read the intent and draw up a lesson plan.

        Returns (early, video_id, history, plan). `early` is a finished response
        dict when the question can't reach the model yet; otherwise None.
        """

        # Per-request video wins; otherwise fall back to the session default
        if video_id is None:
            video_id = session.ACTIVE_VIDEO_ID

        # Keep only the last few exchanges and drop malformed entries
        history = [
            h for h in (history or [])
            if isinstance(h, dict)
            and h.get("role") in ("user", "assistant")
            and isinstance(h.get("content"), str)
            and h.get("content").strip()
        ][-5:]

        # No video selected yet
        if video_id is None:
            return _notice("Please paste a YouTube video first."), video_id, history, None

        status = processing.video_status.get(
            video_id,
            {"status": "ready"}
        )["status"]

        # If the tutor is still being built
        if status != "ready":

            messages = {
                "queued": "I'm preparing your AI tutor.",
                "downloading": "I'm downloading the video's audio.",
                "transcribing": "I'm transcribing the lesson.",
                "chunking": "I'm organizing the lesson into study sections.",
                "embedding": "I'm building the searchable AI tutor.",
            }

            return (
                _notice(messages.get(status, "The video is still processing.")),
                video_id,
                history,
                None,
            )

        # Guard: status says ready but the index is missing
        # (e.g. fresh database or someone else's video_id)
        if not self.video_manager.collection_exists(video_id):
            return (
                _notice("I haven't built a tutor for this video yet — paste its YouTube URL above to build one."),
                video_id,
                history,
                None,
            )

        # Intent Agent — history lets short follow-ups like "why?" resolve
        # against what was just said instead of asking for clarification
        intent = self.intent_agent.analyze(question, history=history)

        # Ask for clarification if needed — the frontend renders this as
        # "the tutor is asking YOU something", not as a transcript answer
        if intent.needs_clarification:
            return (
                {
                    "type": "clarification",
                    "answer": intent.clarification_question,
                    "timestamp": 0,
                    "quote": ""
                },
                video_id,
                history,
                None,
            )

        # Planner Agent
        plan = self.planner_agent.create_plan(
            intent.intent,
            intent.difficulty,
            quiz_count=quiz_count,
        )

        return None, video_id, history, plan


    def run(self, question: str, video_id: str | None = None, history: list[dict] | None = None, quiz_count: int | None = None):
        """Answer a question in one shot (used by POST /ask)."""

        early, video_id, history, plan = self._resolve(question, video_id, history, quiz_count)

        if early is not None:
            return early

        # Retrieve and generate the answer using the plan and conversation context
        return ask(question, plan, video_id, history=history)


    def run_stream(self, question: str, video_id: str | None = None, history: list[dict] | None = None, quiz_count: int | None = None):
        """
        Answer a question as it is written (used by POST /ask-stream).

        Yields the same events as `rag_service.ask_stream`. The guard responses
        (no video, still building, needs clarification) arrive as one event
        instead of a stream of tokens.
        """

        early, video_id, history, plan = self._resolve(question, video_id, history, quiz_count)

        if early is not None:
            yield early
            return

        yield from ask_stream(question, plan, video_id, history=history)