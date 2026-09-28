import processing
import session

from agents.intent import IntentAgent
from agents.planner import PlannerAgent
from rag_service import ask


class TutorEngine:

    def __init__(self):
        self.intent_agent = IntentAgent()
        self.planner_agent = PlannerAgent()

    def run(self, question: str):

        # No video selected yet
        if session.ACTIVE_VIDEO_ID is None:
            return {
                "answer": "Please paste a YouTube video first.",
                "timestamp": 0,
                "quote": ""
            }

        status = processing.video_status.get(
            session.ACTIVE_VIDEO_ID,
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
                "answer": messages.get(status, "The video is still processing."),
                "timestamp": 0,
                "quote": ""
            }

        # Intent Agent
        intent = self.intent_agent.analyze(question)

        # Ask for clarification if needed
        if intent.needs_clarification:
            return {
                "answer": intent.clarification_question,
                "timestamp": 0,
                "quote": ""
            }

        # Planner Agent
        plan = self.planner_agent.create_plan(
            intent.intent,
            intent.difficulty
        )

        # Retrieve and generate answer using the plan
        return ask(question, plan)