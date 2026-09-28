import processing
import session

from agents.intent import IntentAgent
from agents.planner import PlannerAgent
from rag_service import ask
from services.video_manager import VideoManager


class TutorEngine:

    def __init__(self):
        self.intent_agent = IntentAgent()
        self.planner_agent = PlannerAgent()
        self.video_manager = VideoManager()

    def run(self, question: str, video_id: str | None = None, history: list[dict] | None = None):

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
            return {
                "type": "notice",
                "answer": "Please paste a YouTube video first.",
                "timestamp": 0,
                "quote": ""
            }

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

            return {
                "type": "notice",
                "answer": messages.get(status, "The video is still processing."),
                "timestamp": 0,
                "quote": ""
            }

        # Guard: status says ready but the index is missing
        # (e.g. fresh database or someone else's video_id)
        if not self.video_manager.collection_exists(video_id):
            return {
                "type": "notice",
                "answer": "I haven't built a tutor for this video yet — paste its YouTube URL above to build one.",
                "timestamp": 0,
                "quote": ""
            }

        # Intent Agent — history lets short follow-ups like "why?" resolve
        # against what was just said instead of asking for clarification
        intent = self.intent_agent.analyze(question, history=history)

        # Ask for clarification if needed — the frontend renders this as
        # "the tutor is asking YOU something", not as a transcript answer
        if intent.needs_clarification:
            return {
                "type": "clarification",
                "answer": intent.clarification_question,
                "timestamp": 0,
                "quote": ""
            }

        # Planner Agent
        plan = self.planner_agent.create_plan(
            intent.intent,
            intent.difficulty
        )

        # Retrieve and generate answer using the plan and conversation context
        return ask(question, plan, video_id, history=history)