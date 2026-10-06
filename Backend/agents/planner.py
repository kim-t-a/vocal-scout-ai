from dataclasses import dataclass


DEFAULT_QUIZ_COUNT = 3
MIN_QUIZ_COUNT = 1
MAX_QUIZ_COUNT = 10


@dataclass
class LessonPlan:
    strategy: str
    order: list[str]
    include_quiz: bool
    quiz_count: int = DEFAULT_QUIZ_COUNT


class PlannerAgent:
    def create_plan(self, intent: str, difficulty: str, quiz_count: int | None = None) -> LessonPlan:

        if intent == "quiz":
            # User-chosen question count, clamped to a sane range.
            # NB: `quiz_count or DEFAULT` would wrongly treat 0 as "unset".
            count = (
                DEFAULT_QUIZ_COUNT
                if quiz_count is None
                else max(MIN_QUIZ_COUNT, min(MAX_QUIZ_COUNT, int(quiz_count)))
            )
            return LessonPlan(
                strategy="quiz",
                order=[
                    f"{count} multiple-choice quiz questions",
                    "4 options per question with one correct answer",
                ],
                include_quiz=True,
                quiz_count=count,
            )

        if intent == "compare":
            return LessonPlan(
                strategy="comparison_table",
                order=[
                    "simple explanation",
                    "comparison table",
                    "real-world example",
                ],
                include_quiz=True,
            )

        if difficulty == "beginner":
            return LessonPlan(
                strategy="analogy_first",
                order=[
                    "simple explanation",
                    "everyday analogy",
                    "small example",
                    "why it matters",
                ],
                include_quiz=True,
            )

        return LessonPlan(
            strategy="standard",
            order=[
                "explanation",
                "example",
            ],
            include_quiz=True,
        )