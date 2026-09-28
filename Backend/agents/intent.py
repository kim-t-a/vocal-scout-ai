from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str
    difficulty: str
    confidence: float
    needs_clarification: bool
    clarification_question: str | None = None


class IntentAgent:
    def analyze(self, question: str, history: list[dict] | None = None) -> IntentResult:
        text = question.lower().strip()

        # -----------------------------
        # 0. Follow-up awareness
        # -----------------------------
        # Short questions that only make sense with the previous turn's
        # context ("why?", "what about X?") are treated as follow-ups when
        # a conversation exists, instead of bouncing the user for detail.
        has_history = bool(history)
        words = text.split()
        short_follow_up = (
            has_history
            and len(words) <= 4
            and any(word in text for word in ("why", "how", "example", "more", "that"))
            and text not in {"hi", "hello"}
        )

        if short_follow_up:
            return IntentResult(
                intent="explain",
                difficulty="normal",
                confidence=0.75,
                needs_clarification=False,
            )

        # -----------------------------
        # 1. Single-word questions
        # -----------------------------
        single_word_questions = {
            "what",
            "why",
            "how",
            "when",
            "where",
            "who",
            "which",
        }

        if text in single_word_questions:
            return IntentResult(
                intent="clarify",
                difficulty="normal",
                confidence=0.10,
                needs_clarification=True,
                clarification_question="Could you tell me what you're referring to?",
            )

        # -----------------------------
        # 2. Very short questions
        # -----------------------------
        # Only bounce short questions when there is no conversation to
        # resolve them against.
        if len(text.split()) <= 2 and not has_history and text not in {"hi", "hello"}:
            return IntentResult(
                intent="clarify",
                difficulty="normal",
                confidence=0.30,
                needs_clarification=True,
                clarification_question="Could you give me a little more context so I can answer accurately?",
            )

        # -----------------------------
        # 3. User is confused
        # -----------------------------
        confusion_words = [
            "don't understand",
            "dont understand",
            "confused",
            "explain simply",
            "explain like i'm five",
            "make it easier",
            "simplify",
        ]

        if any(word in text for word in confusion_words):
            return IntentResult(
                intent="explain",
                difficulty="beginner",
                confidence=0.95,
                needs_clarification=False,
            )

        # -----------------------------
        # 4. Comparison questions
        # -----------------------------
        if "difference" in text or "compare" in text:
            return IntentResult(
                intent="compare",
                difficulty="normal",
                confidence=0.95,
                needs_clarification=False,
            )

        # -----------------------------
        # 5. Quiz requests
        # -----------------------------
        if "quiz" in text or "test me" in text:
            return IntentResult(
                intent="quiz",
                difficulty="normal",
                confidence=0.95,
                needs_clarification=False,
            )

        # -----------------------------
        # 6. Vague references
        # -----------------------------
        vague_questions = {
            "explain that",
            "what does it mean",
            "what is that",
            "tell me about it",
        }

        if text in vague_questions and not has_history:
            return IntentResult(
                intent="clarify",
                difficulty="normal",
                confidence=0.20,
                needs_clarification=True,
                clarification_question="Could you tell me what 'that' refers to?",
            )

        # -----------------------------
        # 7. Default behavior
        # -----------------------------
        return IntentResult(
            intent="explain",
            difficulty="normal",
            confidence=0.80,
            needs_clarification=False,
        )