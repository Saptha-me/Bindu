# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Embedding utility for semantic skill matching.

This module provides embedding computation for skills and tasks
to enable semantic similarity matching during negotiation.
"""

from __future__ import annotations

import httpx
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import numpy as np
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    from bindu.common.protocol.types import Skill

logger = get_logger("bindu.server.negotiation.embedder")


class SkillEmbedder:
    """Lazy-loading embedder for semantic skill matching.

    Computes embeddings using OpenRouter API.
    Automatically recalculated when skills change.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize embedder with OpenRouter API key.

        Args:
            api_key: OpenRouter API key (optional, falls back to settings)
        """
        self._api_key = api_key or app_settings.negotiation.embedding_api_key
        self._model_name = app_settings.negotiation.embedding_model
        self._provider = app_settings.negotiation.embedding_provider
        self._client = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def _embed_with_openrouter(self, texts: list[str]) -> np.ndarray:
        """Embed texts using OpenRouter API.

        Args:
            texts: List of texts to embed

        Returns:
            Array of embedding vectors
        """
        if not self._api_key:
            raise ValueError(
                "OpenRouter API key not configured. "
                "Set NEGOTIATION__EMBEDDING_API_KEY or pass api_key to constructor."
            )

        client = self._get_client()

        try:
            response = client.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model_name,
                    "input": texts,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract embeddings from response
            embeddings = [item["embedding"] for item in data["data"]]
            return np.array(embeddings, dtype=np.float32)

        except httpx.HTTPError as e:
            logger.error(f"OpenRouter API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get embeddings from OpenRouter: {e}")
            raise

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed multiple text strings in batch.

        Args:
            texts: List of texts to embed

        Returns:
            Array of embedding vectors
        """
        if not texts:
            return np.array([])

        # Route to appropriate provider
        if self._provider == "openrouter":
            return self._embed_with_openrouter(texts)
        elif self._provider == "sentence-transformers":
            logger.warning(
                f"Unknown embedding provider: {self._provider}, falling back to OpenRouter"
            )
            return self._embed_with_openrouter(texts)
            # return self._embed_with_sentence_transformers(texts)
        else:
            logger.warning(
                f"Unknown embedding provider: {self._provider}, falling back to OpenRouter"
            )
            return self._embed_with_openrouter(texts)

    def compute_skill_embeddings(
        self, skills: list[Skill]
    ) -> dict[str, dict[str, Any]]:
        """Compute embeddings for all skills.

        For each skill, creates a composite text from:
        - Skill name
        - Description
        - Tags
        - Assessment keywords (if available)
        - Capability names

        Args:
            skills: List of skill definitions

        Returns:
            Dict mapping skill_id to embedding data:
            {
                "skill_id": {
                    "embedding": np.ndarray,
                    "text": str,
                    "keywords": set[str]
                }
            }
        """
        if not skills:
            return {}

        skill_texts = []
        skill_ids = []
        skill_keywords = []

        for skill in skills:
            # Build composite text for embedding
            parts = []

            # Add name and description
            if skill.get("name"):
                parts.append(skill["name"])
            if skill.get("description"):
                parts.append(skill["description"])

            # Add tags
            tags = skill.get("tags", [])
            if tags:
                parts.append(" ".join(tags))

            # Add assessment keywords if available
            assessment = skill.get("assessment", {})
            if isinstance(assessment, dict):
                keywords = assessment.get("keywords", [])
                if keywords:
                    parts.append(" ".join(keywords))
                    skill_keywords.append(set(k.lower() for k in keywords))
                else:
                    skill_keywords.append(set())
            else:
                skill_keywords.append(set())

            # Add capability names
            caps = skill.get("capabilities_detail", {})
            if isinstance(caps, dict):
                parts.append(" ".join(caps.keys()))

            text = " ".join(parts)
            skill_texts.append(text)
            skill_ids.append(skill.get("id", "unknown"))

        # Compute embeddings in batch
        logger.debug(f"Computing embeddings for {len(skills)} skills")
        embeddings = self.embed_texts(skill_texts)

        # Build result dict
        result = {}
        for skill_id, embedding, text, keywords in zip(
            skill_ids, embeddings, skill_texts, skill_keywords
        ):
            result[skill_id] = {
                "embedding": embedding,
                "text": text,
                "keywords": keywords,
            }

        logger.info(f"Computed embeddings for {len(result)} skills")
        return result

    @lru_cache(maxsize=1000)
    def embed_task_cached(
        self, task_summary: str, task_details: str = ""
    ) -> np.ndarray:
        """Embed task with LRU caching.

        Args:
            task_summary: Task summary text
            task_details: Optional task details

        Returns:
            Task embedding vector
        """
        text = task_summary
        if task_details:
            text = f"{task_summary} {task_details}"
        return self.embed_text(text)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity score (0.0 to 1.0)
    """
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))
