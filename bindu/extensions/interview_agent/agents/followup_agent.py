from ..llm import get_llm

class FollowupAgent:
    """
    Generates deep technical follow-up questions.
    """

    def __init__(self):
        self.llm = get_llm()

    def generate(self, answer: str):
        prompt = f"""
You are a senior backend interviewer.
Based on this answer, ask one deep technical follow-up question
if clarity, depth, or correctness is missing.

Answer:
{answer}

If no follow-up is needed, respond ONLY with: NONE
"""

        res = self.llm.invoke(prompt).content.strip()

        if res.upper() == "NONE":
            return None
        return res