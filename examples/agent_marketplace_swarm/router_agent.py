"""
Router Agent

Routes incoming requests to the appropriate agent.
Simple keyword-based routing.
"""


class RouterAgent:

    def route(self, request: str):
        """
        Route the request to the correct agent based on keywords.
        """

        request = request.lower()

        # Summarization / Explanation tasks
        if "summarize" in request or "summary" in request:
            return "summarizer_agent"

        if "explain" in request or "what is" in request:
            return "summarizer_agent"

        # Translation tasks
        if "translate" in request:
            return "translator_agent"

        # Default fallback
        return "summarizer_agent"