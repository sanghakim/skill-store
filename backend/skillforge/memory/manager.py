"""
Memory Manager - Unified interface for all three memory layers.
Coordinates Working, Episodic, and Semantic memory access.
"""

from __future__ import annotations

import logging

from skillforge.memory.working import WorkingMemory
from skillforge.memory.episodic import EpisodicMemory
from skillforge.memory.semantic import SemanticMemory
from skillforge.memory.context_bus import ContextBus
from skillforge.models import AgentRole

logger = logging.getLogger(__name__)


class MemoryManager:
    """Unified facade over the three-layer memory architecture."""

    def __init__(
        self,
        episodic_persist_path: str | None = None,
        token_limit: int = 128_000,
    ):
        self.working = WorkingMemory(token_limit=token_limit)
        self.episodic = EpisodicMemory(persist_path=episodic_persist_path)
        self.semantic = SemanticMemory()
        self.bus = ContextBus()

        logger.info("MemoryManager initialized (3-layer + context bus)")

    # ── Session Lifecycle ──

    def start_session(self, user_id: str = "default") -> str:
        """Create a new working memory session and return the session_id."""
        return self.working.create_session(user_id=user_id)

    def end_session(
        self,
        session_id: str,
        summary: str = "",
        skills_used: list[str] | None = None,
    ) -> None:
        """End a session: save to episodic, clean up working memory."""
        state = self.working.get_session(session_id)
        if not state:
            return

        # Auto-generate summary if not provided
        if not summary and state.messages:
            user_msgs = [m.content for m in state.messages if m.role == "user"]
            summary = f"Session with {len(state.messages)} messages. Topics: {'; '.join(user_msgs[:3])}"

        # Record in episodic memory
        self.episodic.record_session(
            user_id=state.user_id,
            session_id=session_id,
            summary=summary,
            skills_used=skills_used or [],
        )

        # Clean up working memory
        self.working.delete_session(session_id)
        self.bus.clear_log(context_ref=session_id)

        logger.info("Session ended: %s", session_id)

    # ── Enriched Context Building ──

    def build_agent_context(
        self,
        session_id: str,
        query: str,
        agent_role: AgentRole | None = None,
    ) -> dict:
        """Build a rich context dict for an agent, pulling from all layers."""
        state = self.working.get_session(session_id)
        user_id = state.user_id if state else "default"

        context = {
            "session_id": session_id,
            "user_id": user_id,
        }

        # Layer 1: Working memory — recent conversation
        context["conversation"] = self.working.get_context_string(
            session_id, last_n=10
        )
        context["shared_vars"] = self.working.get_all_shared_vars(session_id)
        context["remaining_tokens"] = self.working.get_remaining_tokens(session_id)

        # Layer 2: Episodic — past patterns
        context["recent_history"] = self.episodic.get_recent_summaries(
            user_id, last_n=3
        )
        context["frequent_skills"] = self.episodic.get_frequent_skills(
            user_id, top_n=5
        )

        # Layer 3: Semantic — relevant knowledge
        context["semantic_context"] = self.semantic.build_context(
            query, user_id=user_id, top_k=3
        )
        context["user_preferences"] = self.semantic.get_user_preferences(user_id)

        return context

    # ── Convenience Methods ──

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: AgentRole | None = None,
    ) -> None:
        self.working.add_message(session_id, role, content, agent)

    def get_messages(self, session_id: str, last_n: int | None = None):
        return self.working.get_messages(session_id, last_n)

    def get_stats(self) -> dict:
        """Get overall memory system statistics."""
        return {
            "working_sessions": len(self.working.list_sessions()),
            "semantic_entries": self.semantic.get_entry_count(),
            "semantic_namespaces": self.semantic.get_namespaces(),
            "bus_messages": len(self.bus.get_message_log()),
        }
