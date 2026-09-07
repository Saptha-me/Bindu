from .skill_matrix import SKILLS

class ScoringEngine:
    def __init__(self):
        self.scores = {skill: 0 for skill in SKILLS}

    def evaluate(self, answers: dict):
        """
        answers = {
            "FastAPI": "...",
            "Security": "...",
        }
        """
        for skill, answer in answers.items():
            self.scores[skill] = self._score_answer(answer)

        return self.scores

    def _score_answer(self, answer: str) -> int:
        word_count = len(answer.split())

        if word_count > 120:
            return 9
        elif word_count > 90:
            return 8
        elif word_count > 60:
            return 7
        elif word_count > 40:
            return 6
        elif word_count > 25:
            return 5
        else:
            return 4