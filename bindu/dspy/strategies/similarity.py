# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Text similarity functions for KeyTurnsStrategy.

This module provides different text similarity methods that can be used
to identify semantically important turns in a conversation.

Available methods:
- jaccard: Jaccard similarity coefficient (intersection / union of word sets)
- weighted: TF-IDF style weighting that prioritizes less common terms
- overlap: Overlap coefficient (intersection / min of set sizes)
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Literal

SimilarityMethod = Literal["jaccard", "weighted", "overlap"]


def tokenize(text: str) -> list[str]:
    """Simple tokenization by splitting on whitespace and lowercasing.

    Args:
        text: Input text to tokenize

    Returns:
        List of lowercase tokens (words)
    """
    return text.lower().split()


def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts.

    Jaccard similarity is the size of intersection divided by size of union.

    Formula: J(A, B) = |A ∩ B| / |A ∪ B|

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score between 0.0 and 1.0
    """
    words1 = set(tokenize(text1))
    words2 = set(tokenize(text2))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def overlap_similarity(text1: str, text2: str) -> float:
    """Calculate overlap coefficient between two texts.

    Overlap coefficient is the size of intersection divided by size of smaller set.
    This is useful when one text is much shorter than the other.

    Formula: O(A, B) = |A ∩ B| / min(|A|, |B|)

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score between 0.0 and 1.0
    """
    words1 = set(tokenize(text1))
    words2 = set(tokenize(text2))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    min_size = min(len(words1), len(words2))

    return len(intersection) / min_size if min_size else 0.0


def weighted_similarity(text1: str, text2: str, corpus: list[str] | None = None) -> float:
    """Calculate TF-IDF style weighted similarity between two texts.

    This method gives higher weight to terms that are less common in the corpus.
    If no corpus is provided, uses both texts as the corpus.

    The weighting is based on inverse document frequency (IDF):
    - Common words (appear in many documents) get lower weight
    - Rare words (appear in few documents) get higher weight

    Args:
        text1: First text
        text2: Second text
        corpus: Optional list of all documents for IDF calculation

    Returns:
        Similarity score between 0.0 and 1.0
    """
    words1 = tokenize(text1)
    words2 = tokenize(text2)

    if not words1 or not words2:
        return 0.0

    # Build corpus if not provided
    if corpus is None:
        corpus = [text1, text2]

    # Calculate document frequency for each term
    doc_freq: Counter[str] = Counter()
    for doc in corpus:
        unique_words = set(tokenize(doc))
        doc_freq.update(unique_words)

    num_docs = len(corpus)

    # Calculate IDF for each term
    def idf(term: str) -> float:
        df = doc_freq.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(num_docs / df) + 1.0  # Add 1 to avoid zero weights

    # Create weighted vectors
    all_terms = set(words1) | set(words2)

    # Calculate term frequencies
    tf1 = Counter(words1)
    tf2 = Counter(words2)

    # Calculate TF-IDF weighted dot product
    dot_product = 0.0
    for term in all_terms:
        weight = idf(term)
        score1 = tf1.get(term, 0) * weight
        score2 = tf2.get(term, 0) * weight
        dot_product += score1 * score2

    # Calculate magnitudes
    mag1 = math.sqrt(sum((tf1.get(term, 0) * idf(term)) ** 2 for term in all_terms))
    mag2 = math.sqrt(sum((tf2.get(term, 0) * idf(term)) ** 2 for term in all_terms))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


def compute_similarity(
    text1: str,
    text2: str,
    method: SimilarityMethod = "jaccard",
    corpus: list[str] | None = None,
) -> float:
    """Compute similarity between two texts using the specified method.

    Args:
        text1: First text
        text2: Second text
        method: Similarity method to use ("jaccard", "weighted", or "overlap")
        corpus: Optional corpus for weighted similarity IDF calculation

    Returns:
        Similarity score between 0.0 and 1.0

    Raises:
        ValueError: If method is not recognized
    """
    if method == "jaccard":
        return jaccard_similarity(text1, text2)
    elif method == "overlap":
        return overlap_similarity(text1, text2)
    elif method == "weighted":
        return weighted_similarity(text1, text2, corpus)
    else:
        raise ValueError(f"Unknown similarity method: {method}. Use 'jaccard', 'weighted', or 'overlap'")


# Available similarity methods for documentation
SIMILARITY_METHODS = {
    "jaccard": "Jaccard similarity coefficient (intersection / union of word sets)",
    "weighted": "TF-IDF style weighting that prioritizes less common terms",
    "overlap": "Overlap coefficient (intersection / min of set sizes)",
}
