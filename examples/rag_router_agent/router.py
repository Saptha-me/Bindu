import os
import re
import sys
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------
def classify_intent(query: str) -> str | None:
    words = re.findall(r"\w+", query.lower())

    if any(w in words for w in ["tax", "gst", "finance", "money"]):
        return "finance"
    elif any(w in words for w in ["law", "legal", "court"]):
        return "legal"
    elif any(w in words for w in ["code", "api", "server", "computer", "tech"]):
        return "tech"
    else:
        return None


# ---------------------------------------------------------------------------
# DB path routing (kept for backward compatibility)
# ---------------------------------------------------------------------------
def route_db(intent: str) -> str | None:
    if intent is None:
        return None
    return os.path.join(BASE_DIR, "db", f"{intent}.txt")


# ---------------------------------------------------------------------------
# Domain agent routing
# FIX: use lazy imports so missing agent files cause a clear ImportError at
# call-time rather than a module-level crash that breaks unrelated queries.
# FIX: return None explicitly for unknown intents (was falling off the end
# silently), and document that callers must handle None.
# ---------------------------------------------------------------------------
def route_agent(intent: str):
    """
    Return the callable agent for *intent*, or None if unrecognised.
    Callers are responsible for handling the None case.
    """
    if intent == "finance":
        from agents.finance_agent import finance_agent   # noqa: PLC0415
        return finance_agent
    elif intent == "legal":
        from agents.legal_agent import legal_agent       # noqa: PLC0415
        return legal_agent
    elif intent == "tech":
        from agents.tech_agent import tech_agent         # noqa: PLC0415
        return tech_agent
    else:
        logger.warning("route_agent: unknown intent '%s' — returning None.", intent)
        return None
