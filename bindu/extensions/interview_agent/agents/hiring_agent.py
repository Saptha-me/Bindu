class HiringDecisionAgent:
    """
    Makes final hiring decision using score consensus.
    """

    def decide(self, scores: dict) -> str:
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
        for k, v in scores.items():
            report += f"{k:<18}: {v}/10\n"

        report += "\n-----------------------------\n"
        report += f"Overall Score      : {total} / 100\n"
        report += f"Hiring Decision    : {decision}\n"

        return report