"""
Layer 1: Working Memory
- Session-scoped, stored in Redis (or in-memory fallback)
- Manages current conversation, active agents, skill stack, shared vars
- Implements context window management strategies:
  1. Sliding Window  - Keep recent N turns
  2. Summarization   - Compress old turns
  3. Priority Queue  - Drop low-priority when near limit
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from skillforge.models import (
    AgentRole,
    ChatMessage,
    TokenBudget,
    WorkingMemoryState,
)

logger = logging.getLogger(__name__)


class WorkingMemory:
    """In-process working memory for session state management."""

    def __init__(self, max_turns: int = 50, token_limit: int = 128_000):
        self._sessions: dict[str, WorkingMemoryState] = {}
        self._max_turns = max_turns
        self._token_limit = token_limit

    # ── Session Management ──

    def create_session(self, user_id: str = "default") -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = WorkingMemoryState(
            session_id=session_id,
            user_id=user_id,
            token_budget=TokenBudget(limit=self._token_limit),
        )
        logger.info("Working memory session created: %s", session_id)
        return session_id

    def get_session(self, session_id: str) -> WorkingMemoryState | None:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())

    # ── Messages ──

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: AgentRole | None = None,
    ) -> None:
        state = self._sessions.get(session_id)
        if not state:
            raise KeyError(f"Session {session_id} not found")

        msg = ChatMessage(
            role=role,
            content=content,
            agent=agent,
            timestamp=datetime.utcnow(),
        )
        state.messages.append(msg)

        # Update token budget estimate (rough: ~4 chars per token)
        state.token_budget.used += len(content) // 4

        # Apply sliding window if over max turns
        self._apply_sliding_window(state)

        # Compress if approaching token limit
        if state.token_budget.used >= state.token_budget.compression_threshold:
            self._apply_compression(state)

    def get_messages(
        self, session_id: str, last_n: int | None = None
    ) -> list[ChatMessage]:
        state = self._sessions.get(session_id)
        if not state:
            return []
        if last_n:
            return state.messages[-last_n:]
        return state.messages

    def get_context_string(self, session_id: str, last_n: int = 10) -> str:
        """Get recent conversation as a formatted string for prompt injection."""
        messages = self.get_messages(session_id, last_n)
        parts = []
        for msg in messages:
            prefix = msg.role.upper()
            if msg.agent:
                prefix += f" ({msg.agent.value})"
            parts.append(f"[{prefix}]: {msg.content}")
        return "\n".join(parts)

    # ── Active Agents ──

    def activate_agent(self, session_id: str, agent: AgentRole) -> None:
        state = self._sessions.get(session_id)
        if state and agent not in state.active_agents:
            state.active_agents.append(agent)

    def deactivate_agent(self, session_id: str, agent: AgentRole) -> None:
        state = self._sessions.get(session_id)
        if state and agent in state.active_agents:
            state.active_agents.remove(agent)

    def get_active_agents(self, session_id: str) -> list[AgentRole]:
        state = self._sessions.get(session_id)
        return state.active_agents if state else []

    # ── Shared Variables (cross-agent state) ──

    def set_shared_var(self, session_id: str, key: str, value: any) -> None:
        state = self._sessions.get(session_id)
        if state:
            state.shared_vars[key] = value

    def get_shared_var(self, session_id: str, key: str) -> any:
        state = self._sessions.get(session_id)
        return state.shared_vars.get(key) if state else None

    def get_all_shared_vars(self, session_id: str) -> dict:
        state = self._sessions.get(session_id)
        return dict(state.shared_vars) if state else {}

    # ── Skill Stack ──

    def push_skill(self, session_id: str, skill_id: str) -> None:
        state = self._sessions.get(session_id)
        if state:
            state.skill_stack.append({
                "skill_id": skill_id,
                "status": "executing",
                "started_at": datetime.utcnow().isoformat(),
            })

    def pop_skill(self, session_id: str) -> dict | None:
        state = self._sessions.get(session_id)
        if state and state.skill_stack:
            return state.skill_stack.pop()
        return None

    # ── Token Budget ──

    def get_token_budget(self, session_id: str) -> TokenBudget | None:
        state = self._sessions.get(session_id)
        return state.token_budget if state else None

    def get_remaining_tokens(self, session_id: str) -> int:
        state = self._sessions.get(session_id)
        if not state:
            return 0
        return state.token_budget.limit - state.token_budget.used

    # ── Context Window Strategies ──

    def _apply_sliding_window(self, state: WorkingMemoryState) -> None:
        """Strategy 1: Keep only the most recent N turns."""
        if len(state.messages) > self._max_turns:
            dropped = len(state.messages) - self._max_turns
            state.messages = state.messages[-self._max_turns:]
            logger.debug("Sliding window dropped %d messages", dropped)

    def _apply_compression(self, state: WorkingMemoryState) -> None:
        """Strategy 2: Summarize older messages to reclaim tokens."""
        if len(state.messages) <= 4:
            return

        # Keep recent 4 messages, summarize the rest
        old_messages = state.messages[:-4]
        recent_messages = state.messages[-4:]

        summary_parts = []
        for msg in old_messages:
            summary_parts.append(f"{msg.role}: {msg.content[:100]}...")

        summary = ChatMessage(
            role="system",
            content=f"[Compressed History] {len(old_messages)} previous messages summarized:\n"
            + "\n".join(summary_parts[:5])
            + (f"\n... and {len(summary_parts) - 5} more" if len(summary_parts) > 5 else ""),
        )

        state.messages = [summary] + recent_messages

        # Recalculate token usage
        total_chars = sum(len(m.content) for m in state.messages)
        state.token_budget.used = total_chars // 4

        logger.info(
            "Compressed %d messages, tokens: %d",
            len(old_messages),
            state.token_budget.used,
        )

    def get_full_state(self, session_id: str) -> dict | None:
        state = self._sessions.get(session_id)
        if not state:
            return None
        return state.model_dump()
