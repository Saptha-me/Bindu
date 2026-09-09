import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Source registry
# Each intent maps to an ordered list of sources (free first, premium second).
# Add premium entries for legal/tech when those DB files exist.
# ---------------------------------------------------------------------------
SOURCES = {
    "finance": [
        {"path": os.path.join(BASE_DIR, "db", "finance.txt"),         "type": "free"},
        {"path": os.path.join(BASE_DIR, "db", "finance_premium.txt"), "type": "premium"},
    ],
    "legal": [
        {"path": os.path.join(BASE_DIR, "db", "legal.txt"),           "type": "free"},
        # Uncomment when premium legal DB is available:
        # {"path": os.path.join(BASE_DIR, "db", "legal_premium.txt"), "type": "premium"},
    ],
    "tech": [
        {"path": os.path.join(BASE_DIR, "db", "tech.txt"),            "type": "free"},
        # Uncomment when premium tech DB is available:
        # {"path": os.path.join(BASE_DIR, "db", "tech_premium.txt"),  "type": "premium"},
    ],
}

# FIX: broader keyword set reduces mis-classification risk.
# "update/updates" added so "latest GST updates" reliably hits premium.
PREMIUM_KEYWORDS = {
    "latest", "premium", "advanced",
    "update", "updates", "recent", "new", "exclusive",
}


def select_source(intent: str, query: str):
    """
    Return the best source dict for (intent, query), or None if no sources
    are registered for this intent.

    Selection logic:
      1. If the query contains a premium keyword AND a premium source exists
         for this intent → return premium source.
      2. Otherwise → return the first free source.
      3. Hard fallback → return sources[0] (never return None when sources
         exist, avoiding a silent KeyError-style failure in the caller).
    """
    sources = SOURCES.get(intent, [])
    if not sources:
        return None

    tokens = set(re.findall(r"\w+", query.lower()))

    if tokens & PREMIUM_KEYWORDS:
        for s in sources:
            if s["type"] == "premium":
                return s

    for s in sources:
        if s["type"] == "free":
            return s

    # FIX: explicit final fallback — never silently return None when sources exist.
    return sources[0]
