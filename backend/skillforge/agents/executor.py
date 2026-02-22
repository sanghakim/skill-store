"""
Executor Agent - Invokes skills to perform actual work.
The workhorse agent that calls the Skill Sandbox.
"""

from __future__ import annotations

import logging
from typing import Any

from skillforge.agents.base import BaseAgent
from skillforge.models import (
    AgentRole,
    SkillExecutionRequest,
    SkillExecutionResult,
)

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """Executes skills via the Sandbox to perform actual work."""

    role = AgentRole.EXECUTOR

    async def process(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        skill_id = context.get("skill_id")
        skill_inputs = context.get("skill_inputs", {})

        if not skill_id:
            return {
                "success": False,
                "error": "No skill_id provided for execution",
            }

        # Lookup skill
        skill = self.registry.get(skill_id)
        if not skill:
            return {
                "success": False,
                "error": f"Skill not found: {skill_id}",
            }

        logger.info("Executor running skill: %s", skill_id)

        # Build enriched context from memory
        agent_context = self.memory.build_agent_context(
            session_id, task_description, self.role
        )
        extra_context = agent_context.get("semantic_context", "")

        # Push to skill stack
        self.memory.working.push_skill(session_id, skill_id)

        try:
            # Execute via sandbox
            request = SkillExecutionRequest(
                skill_id=skill_id,
                inputs=skill_inputs,
                context={"session_id": session_id},
            )
            result: SkillExecutionResult = self.sandbox.execute(
                skill, request, extra_context=extra_context
            )

            # Store result in shared vars for other agents
            self.memory.working.set_shared_var(
                session_id,
                f"result:{skill_id}",
                result.outputs,
            )

            # Log assistant message
            if result.success:
                output_preview = str(result.outputs)[:200]
                self.memory.add_message(
                    session_id,
                    "assistant",
                    f"[{skill.name}] Execution complete: {output_preview}",
                    agent=self.role,
                )

            return {
                "success": result.success,
                "skill_id": skill_id,
                "outputs": result.outputs,
                "tokens_used": result.tokens_used,
                "execution_time_ms": result.execution_time_ms,
                "error": result.error,
                "resolved_prompt": result.resolved_prompt,
            }

        finally:
            self.memory.working.pop_skill(session_id)

    async def execute_skill_direct(
        self,
        session_id: str,
        skill_id: str,
        inputs: dict[str, Any],
    ) -> SkillExecutionResult:
        """Direct skill execution shortcut."""
        result = await self.process(
            session_id,
            f"Execute skill {skill_id}",
            context={"skill_id": skill_id, "skill_inputs": inputs},
        )

        return SkillExecutionResult(
            skill_id=skill_id,
            outputs=result.get("outputs", {}),
            success=result.get("success", False),
            error=result.get("error"),
            tokens_used=result.get("tokens_used", 0),
            execution_time_ms=result.get("execution_time_ms", 0),
        )
