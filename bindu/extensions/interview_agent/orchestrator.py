from .agents.question_agent import QuestionAgent
from .agents.followup_agent import FollowupAgent
from .agents.evaluation_agent import EvaluationAgent
from .agents.hiring_agent import HiringDecisionAgent
from .skill_matrix import SKILLS


class InterviewOrchestrator:
    def __init__(self, resume: str, role: str):
        self.resume = resume
        self.role = role

        self.q_agent = QuestionAgent()
        self.followup_agent = FollowupAgent()
        self.eval_agent = EvaluationAgent()
        self.hiring_agent = HiringDecisionAgent()

        self.answers = {}
        self.scores = {}

    def run(self):
        print("\n🧠 Starting Multi-Agent Intelligent Interview...\n")

        prev_q, prev_a = "", ""

        for skill in SKILLS:
            difficulty = "medium"

            q = self.q_agent.generate(
                resume=self.resume,
                role=self.role,
                prev_q=prev_q,
                prev_a=prev_a,
                difficulty=difficulty
            )

            print(f"\n🧠 [{skill.upper()} AGENT]: {q}")
            ans = input("Your answer: ").strip()

            self.answers[skill] = ans

            follow = self.followup_agent.generate(ans)
            if follow:
                print(f"\n🔍 [FOLLOW-UP AGENT]: {follow}")
                follow_ans = input("Your answer: ")
                self.answers[skill] += " " + follow_ans

            prev_q, prev_a = q, ans

        print("\n📊 Evaluation Agents analyzing your responses...\n")

        self.scores = self.eval_agent.evaluate(self.answers)

        final_report = self.hiring_agent.decide(self.scores)

        print(final_report)
        return final_report