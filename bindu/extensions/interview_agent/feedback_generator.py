class FeedbackGenerator:
    def generate(self, scores: dict):
        total = sum(scores.values())
        avg = total / len(scores)

        if avg >= 8:
            decision = "Strong Hire"
        elif avg >= 7:
            decision = "Hire"
        elif avg >= 6:
            decision = "Conditional Hire"
        else:
            decision = "Reject"

        report = "\n📊 Final Interview Report\n\n"
        for skill, score in scores.items():
            report += f"{skill:<18}: {score}/10\n"

        report += "\n-----------------------------\n"
        report += f"Overall Score      : {int(avg * 10)} / 100\n"
        report += f"Hiring Decision    : {decision}\n"

        return report