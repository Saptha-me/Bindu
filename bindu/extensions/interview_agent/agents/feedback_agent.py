from ..llm import get_llm
from ..prompts import FINAL_FEEDBACK_PROMPT


class FeedbackAgent:
    def __init__(self):
        self.llm = get_llm()

    def generate(self, history):
        prompt = FINAL_FEEDBACK_PROMPT.format(
            history=history
        )

        response = self.llm.invoke(prompt)
        return response.content.strip()