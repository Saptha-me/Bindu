# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Unit tests for SkillEmbedder and cosine_similarity.

Covers embedding computation, skill embedding generation,
task caching, provider routing, and similarity scoring —
all in isolation using mocks (no real API calls made).
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from bindu.server.negotiation.embedder import SkillEmbedder, cosine_similarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(
    skill_id: str = "skill-1",
    name: str = "Research Skill",
    description: str = "Finds and summarizes information",
    tags: list[str] | None = None,
    keywords: list[str] | None = None,
) -> dict:
    """Build a minimal skill dict for testing."""
    return {
        "id": skill_id,
        "name": name,
        "description": description,
        "tags": tags or ["research", "summarization"],
        "assessment": {"keywords": keywords or ["research", "summarize"]},
        "capabilities_detail": {"question_answering": {}, "summarization": {}},
        "input_modes": ["text/plain"],
        "output_modes": ["text/plain"],
    }


def _fake_embedding(dim: int = 8) -> np.ndarray:
    """Return a deterministic unit-norm embedding vector."""
    vec = np.ones(dim, dtype=np.float32)
    return vec / np.linalg.norm(vec)


def _mock_embed_texts(embedder: SkillEmbedder, embedding: np.ndarray | None = None):
    """Patch embedder.embed_texts to return fake embeddings."""
    fake = embedding if embedding is not None else _fake_embedding()

    def _side_effect(texts):
        return np.array([fake for _ in texts], dtype=np.float32)

    embedder.embed_texts = MagicMock(side_effect=_side_effect)
    return embedder


# ---------------------------------------------------------------------------
# cosine_similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    """Tests for the cosine_similarity utility function."""

    def test_identical_vectors_return_one(self):
        """Identical vectors should have similarity of 1.0."""
        vec = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        assert cosine_similarity(vec, vec) == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_vectors_return_zero(self):
        """Orthogonal vectors should have similarity of 0.0."""
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-5)

    def test_opposite_vectors_return_negative_one(self):
        """Opposite vectors should have similarity of -1.0."""
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(-1.0, abs=1e-5)

    def test_zero_vector_a_returns_zero(self):
        """Zero vector in position a should return 0.0 safely."""
        a = np.array([0.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 2.0], dtype=np.float32)
        assert cosine_similarity(a, b) == 0.0

    def test_zero_vector_b_returns_zero(self):
        """Zero vector in position b should return 0.0 safely."""
        a = np.array([1.0, 2.0], dtype=np.float32)
        b = np.array([0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == 0.0

    def test_returns_float(self):
        """cosine_similarity must return a Python float."""
        a = np.array([1.0, 0.5], dtype=np.float32)
        b = np.array([0.5, 1.0], dtype=np.float32)
        result = cosine_similarity(a, b)
        assert isinstance(result, float)

    def test_similarity_is_symmetric(self):
        """cosine_similarity(a, b) == cosine_similarity(b, a)."""
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        b = np.array([4.0, 5.0, 6.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(
            cosine_similarity(b, a), abs=1e-6
        )


# ---------------------------------------------------------------------------
# SkillEmbedder — initialization
# ---------------------------------------------------------------------------


class TestSkillEmbedderInit:
    """Tests for SkillEmbedder initialization."""

    def test_uses_provided_api_key(self):
        """Constructor should store the provided API key."""
        embedder = SkillEmbedder(api_key="test-key-123")
        assert embedder._api_key == "test-key-123"

    def test_client_is_none_before_first_use(self):
        """HTTP client should be lazily initialized."""
        embedder = SkillEmbedder(api_key="key")
        assert embedder._client is None

    def test_get_client_creates_httpx_client(self):
        """_get_client should create and cache an httpx.Client."""
        import httpx

        embedder = SkillEmbedder(api_key="key")
        client = embedder._get_client()
        assert isinstance(client, httpx.Client)
        assert embedder._client is client

    def test_get_client_returns_same_instance(self):
        """_get_client should return the same client on repeated calls."""
        embedder = SkillEmbedder(api_key="key")
        client1 = embedder._get_client()
        client2 = embedder._get_client()
        assert client1 is client2


# ---------------------------------------------------------------------------
# SkillEmbedder — embed_texts / embed_text
# ---------------------------------------------------------------------------


class TestSkillEmbedderEmbedTexts:
    """Tests for embed_texts and embed_text."""

    def test_embed_texts_empty_returns_empty_array(self):
        """embed_texts with empty list should return empty numpy array."""
        embedder = SkillEmbedder(api_key="key")
        result = embedder.embed_texts([])
        assert isinstance(result, np.ndarray)
        assert result.size == 0

    def test_embed_text_calls_embed_texts(self):
        """embed_text should delegate to embed_texts and return first row."""
        embedder = SkillEmbedder(api_key="key")
        fake = _fake_embedding()
        embedder.embed_texts = MagicMock(
            return_value=np.array([fake], dtype=np.float32)
        )
        result = embedder.embed_text("hello")
        embedder.embed_texts.assert_called_once_with(["hello"])
        np.testing.assert_array_equal(result, fake)

    def test_embed_texts_routes_to_openrouter(self):
        """embed_texts should call _embed_with_openrouter for openrouter provider."""
        embedder = SkillEmbedder(api_key="key")
        embedder._provider = "openrouter"
        fake = np.array([_fake_embedding(), _fake_embedding()], dtype=np.float32)
        with patch.object(embedder, "_embed_with_openrouter", return_value=fake) as mock:
            result = embedder.embed_texts(["text1", "text2"])
            mock.assert_called_once_with(["text1", "text2"])
            np.testing.assert_array_equal(result, fake)

    def test_embed_texts_unknown_provider_falls_back_to_openrouter(self):
        """Unknown provider should fall back to OpenRouter."""
        embedder = SkillEmbedder(api_key="key")
        embedder._provider = "unknown-provider"
        fake = np.array([_fake_embedding()], dtype=np.float32)
        with patch.object(embedder, "_embed_with_openrouter", return_value=fake) as mock:
            embedder.embed_texts(["text"])
            mock.assert_called_once()


# ---------------------------------------------------------------------------
# SkillEmbedder — _embed_with_openrouter
# ---------------------------------------------------------------------------


class TestEmbedWithOpenrouter:
    """Tests for _embed_with_openrouter."""

    def test_raises_if_no_api_key(self):
        """Should raise ValueError when API key is missing."""
        embedder = SkillEmbedder(api_key=None)
        embedder._api_key = None
        with pytest.raises(ValueError, match="API key not configured"):
            embedder._embed_with_openrouter(["text"])

    def test_returns_numpy_array_on_success(self):
        """Should return numpy array from successful API response."""
        embedder = SkillEmbedder(api_key="valid-key")

        fake_response = MagicMock()
        fake_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        }
        fake_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = fake_response
        embedder._client = mock_client

        result = embedder._embed_with_openrouter(["text1", "text2"])
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 3)

    def test_raises_on_http_error(self):
        """Should propagate httpx.HTTPError on API failure."""
        import httpx

        embedder = SkillEmbedder(api_key="valid-key")
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.HTTPError("connection failed")
        embedder._client = mock_client

        with pytest.raises(httpx.HTTPError):
            embedder._embed_with_openrouter(["text"])


# ---------------------------------------------------------------------------
# SkillEmbedder — compute_skill_embeddings
# ---------------------------------------------------------------------------


class TestComputeSkillEmbeddings:
    """Tests for compute_skill_embeddings."""

    def test_empty_skills_returns_empty_dict(self):
        """No skills should return empty dict immediately."""
        embedder = SkillEmbedder(api_key="key")
        result = embedder.compute_skill_embeddings([])
        assert result == {}

    def test_returns_dict_keyed_by_skill_id(self):
        """Result should be keyed by skill id."""
        embedder = SkillEmbedder(api_key="key")
        _mock_embed_texts(embedder)
        skill = _make_skill(skill_id="skill-abc")
        result = embedder.compute_skill_embeddings([skill])
        assert "skill-abc" in result

    def test_each_entry_has_embedding_text_keywords(self):
        """Each result entry should contain embedding, text, and keywords."""
        embedder = SkillEmbedder(api_key="key")
        _mock_embed_texts(embedder)
        skill = _make_skill()
        result = embedder.compute_skill_embeddings([skill])
        entry = result["skill-1"]
        assert "embedding" in entry
        assert "text" in entry
        assert "keywords" in entry

    def test_embedding_is_numpy_array(self):
        """Embedding value should be a numpy array."""
        embedder = SkillEmbedder(api_key="key")
        _mock_embed_texts(embedder)
        skill = _make_skill()
        result = embedder.compute_skill_embeddings([skill])
        assert isinstance(result["skill-1"]["embedding"], np.ndarray)

    def test_keywords_extracted_from_assessment(self):
        """Keywords from assessment should appear in the result."""
        embedder = SkillEmbedder(api_key="key")
        _mock_embed_texts(embedder)
        skill = _make_skill(keywords=["python", "analysis"])
        result = embedder.compute_skill_embeddings([skill])
        assert "python" in result["skill-1"]["keywords"]
        assert "analysis" in result["skill-1"]["keywords"]

    def test_multiple_skills_all_returned(self):
        """All skills should be present in the result."""
        embedder = SkillEmbedder(api_key="key")
        _mock_embed_texts(embedder)
        skills = [
            _make_skill(skill_id="skill-1"),
            _make_skill(skill_id="skill-2"),
            _make_skill(skill_id="skill-3"),
        ]
        result = embedder.compute_skill_embeddings(skills)
        assert set(result.keys()) == {"skill-1", "skill-2", "skill-3"}

    def test_skill_without_assessment_has_empty_keywords(self):
        """Skill with no assessment field should have empty keyword set."""
        embedder = SkillEmbedder(api_key="key")
        _mock_embed_texts(embedder)
        skill = {
            "id": "bare-skill",
            "name": "Bare",
            "description": "No assessment",
            "tags": [],
            "capabilities_detail": {},
        }
        result = embedder.compute_skill_embeddings([skill])
        assert result["bare-skill"]["keywords"] == set()

    def test_composite_text_includes_name_and_tags(self):
        """The composite text sent for embedding should include name and tags."""
        embedder = SkillEmbedder(api_key="key")
        captured_texts = []

        def _capture(texts):
            captured_texts.extend(texts)
            return np.array([_fake_embedding() for _ in texts], dtype=np.float32)

        embedder.embed_texts = MagicMock(side_effect=_capture)
        skill = _make_skill(name="MySkill", tags=["tagA", "tagB"])
        embedder.compute_skill_embeddings([skill])
        assert len(captured_texts) == 1
        assert "MySkill" in captured_texts[0]
        assert "tagA" in captured_texts[0]


# ---------------------------------------------------------------------------
# SkillEmbedder — embed_task_cached
# ---------------------------------------------------------------------------


class TestEmbedTaskCached:
    """Tests for embed_task_cached with LRU caching."""

    def test_returns_embedding_for_task(self):
        """embed_task_cached should return an embedding array."""
        embedder = SkillEmbedder(api_key="key")
        fake = _fake_embedding()
        embedder.embed_text = MagicMock(return_value=fake)
        result = embedder.embed_task_cached("Summarize this document")
        assert isinstance(result, np.ndarray)

    def test_combines_summary_and_details(self):
        """embed_task_cached should concatenate summary and details."""
        embedder = SkillEmbedder(api_key="key")
        captured = []

        def _capture(text):
            captured.append(text)
            return _fake_embedding()

        embedder.embed_text = MagicMock(side_effect=_capture)
        embedder.embed_task_cached("summary", "details")
        assert "summary" in captured[0]
        assert "details" in captured[0]

    def test_summary_only_no_concat(self):
        """With no details, only summary text should be embedded."""
        embedder = SkillEmbedder(api_key="key")
        captured = []

        def _capture(text):
            captured.append(text)
            return _fake_embedding()

        embedder.embed_text = MagicMock(side_effect=_capture)
        embedder.embed_task_cached("just summary", "")
        assert captured[0] == "just summary"