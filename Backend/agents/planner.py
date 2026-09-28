from dataclasses import dataclass


@dataclass
class LessonPlan:
    strategy: str
    order: list[str]
    include_quiz: bool


class PlannerAgent:
    def create_plan(self, intent: str, difficulty: str) -> LessonPlan:

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