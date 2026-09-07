class FollowupEngine:
    def generate(self, answer: str) -> str:
        if len(answer.split()) < 35:
            return "Can you explain this with more internal details or pseudo-code?"

        if "security" in answer.lower() and "jwt" not in answer.lower():
            return "How would you securely implement authentication using JWT and secret management?"

        if "database" in answer.lower() and "transaction" not in answer.lower():
            return "How would you ensure data consistency and transactional safety?"

        return ""