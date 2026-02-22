"""
Base Agent - Abstract base class for all worker agents.
Defines the common interface and lifecycle.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from skillforge.engine.registry import SkillRegistry
from skillforge.engine.sandbox import SkillSandbox
from skillforge.memory.manager import MemoryManager
from skillforge.models import AgentMessage, AgentRole, MessageType

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all agents in the pool."""

    role: AgentRole

    def __init__(
        self,
        memory: MemoryManager,
        registry: SkillRegistry,
        sandbox: SkillSandbox,
    ):
        self.memory = memory
        self.registry = registry
        self.sandbox = sandbox
        self._status = "idle"  # idle | assigned | executing | reviewing | complete

    @property
    def status(self) -> str:
        return self._status

    @abstractmethod
    async def process(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Main processing method. Each agent type implements this differently.

        Args:
            session_id: Working memory session ID
            task_description: What needs to be done
            context: Additional context (shared vars, previous results, etc.)

        Returns:
            Result dict with agent-specific outputs
        """
        ...

    def send_message(
        self,
        to_agent: AgentRole,
        msg_type: MessageType,
        payload: dict,
        session_id: str = "",
    ) -> AgentMessage:
        """Send a message to another agent via the context bus."""
        message = AgentMessage(
            from_agent=self.role,
            to_agent=to_agent,
            type=msg_type,
            payload=payload,
            context_ref=session_id,
        )
        self.memory.bus.publish(message)
        return message

    async def activate(self, session_id: str) -> None:
        """Mark this agent as active for the session."""
        self._status = "assigned"
        self.memory.working.activate_agent(session_id, self.role)
        logger.info("Agent activated: %s for session %s", self.role.value, session_id)

    async def deactivate(self, session_id: str) -> None:
        """Mark this agent as idle."""
        self._status = "idle"
        self.memory.working.deactivate_agent(session_id, self.role)

    async def run(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Full lifecycle: activate → process → deactivate."""
        await self.activate(session_id)
        try:
            self._status = "executing"
            result = await self.process(session_id, task_description, context)
            self._status = "complete"
            return result
        except Exception as exc:
            self._status = "idle"
            logger.error("Agent %s failed: %s", self.role.value, exc)
            return {"error": str(exc), "success": False}
        finally:
            await self.deactivate(session_id)
