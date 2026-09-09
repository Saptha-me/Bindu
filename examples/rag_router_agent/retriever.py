import re
import logging

logger = logging.getLogger(__name__)

STOPWORDS = {"the", "is", "a", "an", "what", "are", "of", "in", "on"}


def retrieve_docs(db_path, query, k=2):
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            docs = f.readlines()
    except (OSError, UnicodeDecodeError):
        return []

    query_words = {w for w in re.findall(r"\w+", query.lower()) if w not in STOPWORDS}

    scored = []
    for doc in docs:
        doc_words = {w for w in re.findall(r"\w+", doc.lower()) if w not in STOPWORDS}
        score = len(query_words & doc_words)

        if score > 0:
            scored.append((score, doc))

    scored.sort(reverse=True)
    return [doc for _, doc in scored[:k]]
