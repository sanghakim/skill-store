"""
Layer 3: Semantic Memory
- Permanent vector-based knowledge storage
- Stores user preferences, domain knowledge, skill metadata
- RAG retrieval for enriching agent context
- In production: Pinecone / Qdrant / ChromaDB; here: in-memory cosine similarity
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict

from skillforge.models import SemanticEntry

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _simple_embedding(text: str, dim: int = 64) -> list[float]:
    """
    Simple hash-based pseudo-embedding for demo purposes.
    In production, replace with real embedding model (e.g., OpenAI, sentence-transformers).
    """
    vec = [0.0] * dim
    for i, ch in enumerate(text.lower()):
        idx = ord(ch) % dim
        vec[idx] += 1.0 / (1 + i * 0.01)
    # Normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class SemanticMemory:
    """Vector-based long-term knowledge store with RAG retrieval."""

    def __init__(self, embedding_dim: int = 64):
        self._embedding_dim = embedding_dim
        # namespace -> list[SemanticEntry]
        self._store: dict[str, list[SemanticEntry]] = defaultdict(list)

    # ── Write ──

    def add_entry(
        self,
        content: str,
        category: str = "general",
        namespace: str = "default",
        metadata: dict | None = None,
    ) -> SemanticEntry:
        """Add a knowledge entry with auto-generated embedding."""
        embedding = _simple_embedding(content, self._embedding_dim)
        entry = SemanticEntry(
            content=content,
            category=category,
            embedding=embedding,
            metadata=metadata or {},
        )
        self._store[namespace].append(entry)
        logger.debug("Semantic entry added: ns=%s cat=%s", namespace, category)
        return entry

    def add_user_preference(
        self, user_id: str, key: str, value: str
    ) -> SemanticEntry:
        """Store a user preference as semantic knowledge."""
        content = f"User preference: {key} = {value}"
        return self.add_entry(
            content=content,
            category="user_preference",
            namespace=f"user:{user_id}",
            metadata={"pref_key": key, "pref_value": value},
        )

    def add_domain_knowledge(
        self, domain: str, content: str, namespace: str = "global"
    ) -> SemanticEntry:
        """Store domain-specific knowledge."""
        return self.add_entry(
            content=content,
            category=f"domain:{domain}",
            namespace=namespace,
        )

    # ── RAG Retrieval ──

    def search(
        self,
        query: str,
        namespace: str = "default",
        top_k: int = 5,
        min_score: float = 0.1,
        category_filter: str | None = None,
    ) -> list[tuple[SemanticEntry, float]]:
        """Search for relevant entries using cosine similarity."""
        query_embedding = _simple_embedding(query, self._embedding_dim)
        entries = self._store.get(namespace, [])

        if category_filter:
            entries = [e for e in entries if e.category == category_filter]

        scored = []
        for entry in entries:
            score = _cosine_similarity(query_embedding, entry.embedding)
            if score >= min_score:
                scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search_all_namespaces(
        self, query: str, top_k: int = 5, min_score: float = 0.1
    ) -> list[tuple[SemanticEntry, float, str]]:
        """Search across all namespaces."""
        all_results = []
        for ns in self._store:
            results = self.search(query, namespace=ns, top_k=top_k, min_score=min_score)
            for entry, score in results:
                all_results.append((entry, score, ns))
        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:top_k]

    def get_user_preferences(self, user_id: str) -> list[dict]:
        """Retrieve all stored preferences for a user."""
        namespace = f"user:{user_id}"
        entries = self._store.get(namespace, [])
        return [
            {"key": e.metadata.get("pref_key", ""), "value": e.metadata.get("pref_value", "")}
            for e in entries
            if e.category == "user_preference"
        ]

    # ── Context Building (for RAG) ──

    def build_context(
        self,
        query: str,
        user_id: str | None = None,
        top_k: int = 3,
    ) -> str:
        """Build a context string from relevant semantic memories for prompt enrichment."""
        parts = []

        # Search global knowledge
        global_results = self.search(query, namespace="global", top_k=top_k)
        if global_results:
            parts.append("[Domain Knowledge]")
            for entry, score in global_results:
                parts.append(f"- {entry.content}")

        # Search user-specific knowledge
        if user_id:
            user_results = self.search(query, namespace=f"user:{user_id}", top_k=top_k)
            if user_results:
                parts.append("[User Preferences]")
                for entry, score in user_results:
                    parts.append(f"- {entry.content}")

        return "\n".join(parts)

    # ── Stats ──

    def get_entry_count(self, namespace: str | None = None) -> int:
        if namespace:
            return len(self._store.get(namespace, []))
        return sum(len(v) for v in self._store.values())

    def get_namespaces(self) -> list[str]:
        return list(self._store.keys())
