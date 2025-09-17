# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
# QDRANT VECTOR STORAGE IMPLEMENTATION:
#
# This is the Qdrant vector database implementation of the Storage interface for the Pebbling framework.
# It provides semantic search, vector similarity, and AI-powered task/context retrieval capabilities.
#
# BURGER STORE ANALOGY:
#
# Think of this as the restaurant's AI-powered recommendation system:
#
# 1. SMART RECOMMENDATION ENGINE (QdrantStorage):
#    - Orders stored as semantic vectors based on content meaning
#    - "Find similar orders to this customer's preferences"
#    - "What orders are semantically related to 'spicy vegetarian'?"
#    - AI understands context and meaning, not just exact matches
#
# 2. VECTOR COLLECTIONS:
#    - tasks_collection: Order vectors with embedded content and metadata
#    - contexts_collection: Customer preference vectors for personalization
#    - Semantic similarity search across all historical orders
#    - Content-based recommendations and clustering
#
# 3. AI-POWERED FEATURES:
#    - Semantic search: "Find tasks similar to 'customer complaint handling'"
#    - Context matching: "Find customers with similar preferences"
#    - Content clustering: "Group related orders by semantic similarity"
#    - Intelligent retrieval: Beyond keyword matching to meaning understanding
#
# WHEN TO USE QDRANT STORAGE:
# - AI-powered agent systems requiring semantic search
# - Content recommendation and similarity matching
# - Large-scale task databases with intelligent retrieval
# - Multi-modal content (text, embeddings, metadata)
# - Research and analytics on agent interactions
# - Personalization based on conversation context
#
# VECTOR FEATURES:
# - High-dimensional vector storage and search
# - Multiple distance metrics (cosine, euclidean, dot product)
# - Efficient approximate nearest neighbor (ANN) search
# - Payload filtering combined with vector similarity
# - Clustering and content analysis capabilities
# - Real-time vector updates and deletions
#
#  Thank you users! We ❤️ you! - 🐧

from __future__ import annotations as _annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from typing_extensions import TypeVar

from pebbling.common.protocol.types import Artifact, Message, Task, TaskState, TaskStatus

from .base import Storage

ContextT = TypeVar("ContextT", default=Any)


class QdrantStorage(Storage[ContextT]):
    """A vector storage implementation using Qdrant for semantic search and AI-powered retrieval.

    This implementation provides vector-based storage with support for:
    - Semantic similarity search across tasks and contexts
    - AI-powered content recommendations
    - Multi-modal vector storage (text embeddings + metadata)
    - Efficient approximate nearest neighbor search
    - Content clustering and analysis
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        vector_size: int = 1536,  # OpenAI ada-002 embedding size
        distance_metric: Distance = Distance.COSINE,
        embedding_function: Optional[callable] = None,
    ):
        """Initialize Qdrant vector storage.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            api_key: Optional API key for Qdrant Cloud
            vector_size: Dimension of embedding vectors
            distance_metric: Vector distance metric (COSINE, EUCLIDEAN, DOT)
            embedding_function: Function to generate embeddings from text
        """
        self.host = host
        self.port = port
        self.api_key = api_key
        self.vector_size = vector_size
        self.distance_metric = distance_metric
        self.embedding_function = embedding_function or self._default_embedding

        self.client: Optional[AsyncQdrantClient] = None
        self.tasks_collection = "pebbling_tasks"
        self.contexts_collection = "pebbling_contexts"

    async def initialize(self) -> None:
        """Initialize Qdrant client and create collections."""
        self.client = AsyncQdrantClient(host=self.host, port=self.port, api_key=self.api_key)

        await self._create_collections()

    async def close(self) -> None:
        """Close the Qdrant client connection."""
        if self.client:
            await self.client.close()

    def _default_embedding(self, text: str) -> List[float]:
        """Default embedding function using simple hash-based vectors.

        In production, replace with actual embedding model like:
        - OpenAI ada-002
        - Sentence Transformers
        - Cohere embeddings
        """
        # Simple hash-based embedding for demo purposes
        import hashlib

        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()

        # Convert to vector of specified size
        vector = []
        for i in range(self.vector_size):
            vector.append(float(int(hash_hex[i % len(hash_hex)], 16) / 15.0 - 0.5))

        return vector

    async def _create_collections(self) -> None:
        """Create Qdrant collections for tasks and contexts."""
        # Create tasks collection
        await self.client.create_collection(
            collection_name=self.tasks_collection,
            vectors_config=VectorParams(size=self.vector_size, distance=self.distance_metric),
        )

        # Create contexts collection
        await self.client.create_collection(
            collection_name=self.contexts_collection,
            vectors_config=VectorParams(size=self.vector_size, distance=self.distance_metric),
        )

    def _extract_text_content(self, task_or_message: Any) -> str:
        """Extract text content from task or message for embedding."""
        if isinstance(task_or_message, dict):
            # Extract text from message parts
            content_parts = []
            if "parts" in task_or_message:
                for part in task_or_message["parts"]:
                    if part.get("type") == "text":
                        content_parts.append(part.get("content", ""))
            return " ".join(content_parts)
        return str(task_or_message)

    async def load_task(self, task_id: str, history_length: int | None = None) -> Task | None:
        """Load a task from Qdrant vector storage.

        Args:
            task_id: The id of the task to load.
            history_length: The number of messages to return in the history.

        Returns:
            The task or None if not found.
        """
        try:
            points = await self.client.retrieve(collection_name=self.tasks_collection, ids=[task_id], with_payload=True)

            if not points:
                return None

            point = points[0]
            payload = point.payload

            history = payload.get("history", [])
            if history_length and len(history) > history_length:
                history = history[-history_length:]

            task_status = TaskStatus(state=payload["state"], timestamp=payload["timestamp"])

            task = Task(
                id=payload["id"],
                context_id=payload["context_id"],
                kind=payload.get("kind", "task"),
                status=task_status,
                history=history,
                artifacts=payload.get("artifacts", []),
            )

            return task

        except Exception:
            return None

    async def submit_task(self, context_id: str, message: Message) -> Task:
        """Submit a task to Qdrant vector storage."""
        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Add IDs to the message for Pebble protocol
        message["task_id"] = task_id
        message["context_id"] = context_id

        # Extract text content for embedding
        text_content = self._extract_text_content(message)
        embedding = self.embedding_function(text_content)

        task_status = TaskStatus(state="submitted", timestamp=datetime.now().isoformat())

        # Create point for vector storage
        point = PointStruct(
            id=task_id,
            vector=embedding,
            payload={
                "id": task_id,
                "context_id": context_id,
                "kind": "task",
                "state": "submitted",
                "timestamp": task_status.timestamp,
                "history": [message],
                "artifacts": [],
                "text_content": text_content,
                "created_at": datetime.now().isoformat(),
            },
        )

        await self.client.upsert(collection_name=self.tasks_collection, points=[point])

        task = Task(id=task_id, context_id=context_id, kind="task", status=task_status, history=[message])

        return task

    async def update_task(
        self,
        task_id: str,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
    ) -> Task:
        """Update the state of a task in Qdrant."""
        # Get current task
        points = await self.client.retrieve(collection_name=self.tasks_collection, ids=[task_id], with_payload=True)

        if not points:
            raise ValueError(f"Task {task_id} not found")

        point = points[0]
        payload = point.payload

        # Update payload
        payload["state"] = state
        payload["timestamp"] = datetime.now().isoformat()

        history = payload.get("history", [])
        artifacts = payload.get("artifacts", [])

        if new_messages:
            # Add IDs to messages for consistency
            for message in new_messages:
                message["task_id"] = task_id
                message["context_id"] = payload["context_id"]
            history.extend(new_messages)
            payload["history"] = history

            # Update embedding with new content
            all_text = " ".join([self._extract_text_content(msg) for msg in history])
            new_embedding = self.embedding_function(all_text)
            payload["text_content"] = all_text
        else:
            new_embedding = point.vector

        if new_artifacts:
            artifacts.extend(new_artifacts)
            payload["artifacts"] = artifacts

        # Update point in Qdrant
        updated_point = PointStruct(id=task_id, vector=new_embedding, payload=payload)

        await self.client.upsert(collection_name=self.tasks_collection, points=[updated_point])

        # Return updated task
        task_status = TaskStatus(state=state, timestamp=payload["timestamp"])
        task = Task(
            id=task_id,
            context_id=payload["context_id"],
            kind=payload.get("kind", "task"),
            status=task_status,
            history=history,
            artifacts=artifacts,
        )

        return task

    async def load_context(self, context_id: str) -> ContextT | None:
        """Retrieve the stored context from Qdrant."""
        try:
            points = await self.client.retrieve(
                collection_name=self.contexts_collection, ids=[context_id], with_payload=True
            )

            if not points:
                return None

            return points[0].payload.get("context_data")

        except Exception:
            return None

    async def update_context(self, context_id: str, context: ContextT) -> None:
        """Update the context in Qdrant."""
        # Generate embedding for context
        context_text = str(context) if context else ""
        embedding = self.embedding_function(context_text)

        point = PointStruct(
            id=context_id,
            vector=embedding,
            payload={
                "id": context_id,
                "context_data": context,
                "text_content": context_text,
                "updated_at": datetime.now().isoformat(),
            },
        )

        await self.client.upsert(collection_name=self.contexts_collection, points=[point])

    async def search_similar_tasks(
        self, query_text: str, limit: int = 10, context_id: Optional[str] = None, state_filter: Optional[str] = None
    ) -> List[Task]:
        """Search for semantically similar tasks using vector similarity.

        Args:
            query_text: Text to search for similar tasks
            limit: Maximum number of results
            context_id: Optional filter by context
            state_filter: Optional filter by task state

        Returns:
            List of similar tasks ordered by similarity score
        """
        query_embedding = self.embedding_function(query_text)

        # Build filter conditions
        filter_conditions = []
        if context_id:
            filter_conditions.append(FieldCondition(key="context_id", match=MatchValue(value=context_id)))
        if state_filter:
            filter_conditions.append(FieldCondition(key="state", match=MatchValue(value=state_filter)))

        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Perform vector search
        results = await self.client.search(
            collection_name=self.tasks_collection,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            with_payload=True,
        )

        # Convert results to Task objects
        tasks = []
        for result in results:
            payload = result.payload
            task_status = TaskStatus(state=payload["state"], timestamp=payload["timestamp"])

            task = Task(
                id=payload["id"],
                context_id=payload["context_id"],
                kind=payload.get("kind", "task"),
                status=task_status,
                history=payload.get("history", []),
                artifacts=payload.get("artifacts", []),
            )
            tasks.append(task)

        return tasks

    async def get_tasks_by_context(self, context_id: str, limit: int = 100) -> list[Task]:
        """Get all tasks for a specific context using vector storage."""
        return await self.search_similar_tasks(
            query_text="",  # Empty query to get all
            limit=limit,
            context_id=context_id,
        )

    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up tasks older than specified days."""
        cutoff_date = datetime.now() - datetime.timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        # Get all points to check dates (Qdrant doesn't have date range filters built-in)
        all_points = await self.client.scroll(
            collection_name=self.tasks_collection,
            with_payload=True,
            limit=10000,  # Adjust based on your needs
        )

        old_point_ids = []
        for point in all_points[0]:
            created_at = point.payload.get("created_at", "")
            if created_at < cutoff_iso:
                old_point_ids.append(point.id)

        if old_point_ids:
            await self.client.delete(collection_name=self.tasks_collection, points_selector=old_point_ids)

        return len(old_point_ids)
