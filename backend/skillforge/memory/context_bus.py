"""
Shared Context Bus - Inter-agent communication channel.
- Pub/Sub message routing
- State snapshot management
- Concurrency control with locks
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Callable

from skillforge.models import AgentMessage, AgentRole

logger = logging.getLogger(__name__)

Subscriber = Callable[[AgentMessage], None]


class ContextBus:
    """Pub/Sub message bus for agent-to-agent communication."""

    def __init__(self):
        self._subscribers: dict[AgentRole, list[Subscriber]] = defaultdict(list)
        self._broadcast_subscribers: list[Subscriber] = []
        self._message_log: list[AgentMessage] = []
        self._locks: dict[str, asyncio.Lock] = {}

    # ── Subscribe ──

    def subscribe(self, agent_role: AgentRole, callback: Subscriber) -> None:
        """Subscribe to messages targeted at a specific agent role."""
        self._subscribers[agent_role].append(callback)
        logger.debug("Subscriber added for %s", agent_role.value)

    def subscribe_all(self, callback: Subscriber) -> None:
        """Subscribe to all messages (broadcast)."""
        self._broadcast_subscribers.append(callback)

    def unsubscribe(self, agent_role: AgentRole, callback: Subscriber) -> None:
        subs = self._subscribers.get(agent_role, [])
        if callback in subs:
            subs.remove(callback)

    # ── Publish ──

    def publish(self, message: AgentMessage) -> None:
        """Publish a message to the bus."""
        self._message_log.append(message)

        # Deliver to targeted agent
        if message.to_agent:
            for sub in self._subscribers.get(message.to_agent, []):
                try:
                    sub(message)
                except Exception as exc:
                    logger.error("Subscriber error for %s: %s", message.to_agent.value, exc)

        # Broadcast
        for sub in self._broadcast_subscribers:
            try:
                sub(message)
            except Exception as exc:
                logger.error("Broadcast subscriber error: %s", exc)

        logger.debug(
            "Message published: %s -> %s [%s]",
            message.from_agent.value,
            message.to_agent.value if message.to_agent else "broadcast",
            message.type.value,
        )

    # ── Message Log ──

    def get_message_log(
        self,
        context_ref: str | None = None,
        from_agent: AgentRole | None = None,
        last_n: int | None = None,
    ) -> list[AgentMessage]:
        """Retrieve logged messages with optional filters."""
        msgs = self._message_log
        if context_ref:
            msgs = [m for m in msgs if m.context_ref == context_ref]
        if from_agent:
            msgs = [m for m in msgs if m.from_agent == from_agent]
        if last_n:
            msgs = msgs[-last_n:]
        return msgs

    def clear_log(self, context_ref: str | None = None) -> int:
        """Clear message log, optionally for a specific context."""
        if context_ref:
            before = len(self._message_log)
            self._message_log = [m for m in self._message_log if m.context_ref != context_ref]
            return before - len(self._message_log)
        else:
            count = len(self._message_log)
            self._message_log.clear()
            return count

    # ── Locks (Concurrency Control) ──

    def get_lock(self, resource_id: str) -> asyncio.Lock:
        """Get or create a lock for a shared resource."""
        if resource_id not in self._locks:
            self._locks[resource_id] = asyncio.Lock()
        return self._locks[resource_id]
