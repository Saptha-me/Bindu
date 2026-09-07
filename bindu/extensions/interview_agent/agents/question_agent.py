from ..llm import get_llm
from ..prompts import QUESTION_PROMPT


class QuestionAgent:
    def __init__(self):
        self.llm = get_llm()

    def generate(self, resume, role, prev_q, prev_a, difficulty):
        prompt = QUESTION_PROMPT.format(
            resume=resume,
            role=role,
            previous_questions=prev_q,
            previous_answers=prev_a,
            difficulty=difficulty
        )

        response = self.llm.invoke(prompt)
        return response.content.strip()