"""
Creative Agent - Generates content, proposes ideas, handles creation tasks.
Uses skills like doc-drafter, slide-outliner, brainstormer, template-engine.
"""

from __future__ import annotations

import logging
from typing import Any

from skillforge.agents.base import BaseAgent
from skillforge.models import AgentRole, SkillExecutionRequest

logger = logging.getLogger(__name__)


class CreativeAgent(BaseAgent):
    """Generates content and performs creative tasks via skills."""

    role = AgentRole.CREATIVE

    async def process(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        skill_id = context.get("skill_id")
        skill_inputs = context.get("skill_inputs", {})

        logger.info("Creative agent working: %s", task_description[:80])

        # Gather any research data from shared vars
        shared = self.memory.working.get_all_shared_vars(session_id)
        research_data = {
            k.replace("research:", ""): v
            for k, v in shared.items()
            if k.startswith("research:")
        }

        # Build enriched context
        agent_context = self.memory.build_agent_context(
            session_id, task_description, self.role
        )
        extra_context_parts = []
        if agent_context.get("semantic_context"):
            extra_context_parts.append(agent_context["semantic_context"])
        if research_data:
            extra_context_parts.append(
                "[Research Data]\n" + "\n".join(
                    f"- {k}: {str(v)[:300]}" for k, v in research_data.items()
                )
            )
        extra_context = "\n\n".join(extra_context_parts)

        # If a specific skill is assigned, use it
        if skill_id:
            skill = self.registry.get(skill_id)
            if skill:
                # Enrich inputs with research data if applicable
                enriched_inputs = dict(skill_inputs)
                if research_data and not enriched_inputs.get("data"):
                    # Inject research findings into skill inputs
                    for key, val in research_data.items():
                        if isinstance(val, dict):
                            for k, v in val.items():
                                if k not in enriched_inputs:
                                    enriched_inputs[k] = str(v)[:500]

                request = SkillExecutionRequest(
                    skill_id=skill_id,
                    inputs=enriched_inputs,
                )
                result = self.sandbox.execute(skill, request, extra_context=extra_context)

                # Store output
                self.memory.working.set_shared_var(
                    session_id, f"result:{skill_id}", result.outputs
                )

                self.memory.add_message(
                    session_id,
                    "assistant",
                    f"[Creative/{skill.name}] Generated content ({result.tokens_used} tokens)",
                    agent=self.role,
                )

                return {
                    "success": result.success,
                    "skill_id": skill_id,
                    "outputs": result.outputs,
                    "tokens_used": result.tokens_used,
                    "execution_time_ms": result.execution_time_ms,
                    "error": result.error,
                }

        # Fallback: Generic creative generation without a specific skill
        # Use the sandbox's configured LLM backend directly
        fallback_prompt = (
            f"You are a creative content specialist.\n\n"
            f"Task: {task_description}\n\n"
        )
        if extra_context:
            fallback_prompt += f"Context:\n{extra_context}\n\n"
        fallback_prompt += "Generate a well-structured, professional result."

        output = self.sandbox._llm.generate(fallback_prompt, max_tokens=2000, temperature=0.7)

        self.memory.add_message(
            session_id,
            "assistant",
            f"[Creative] Generated content ({len(output)} chars)",
            agent=self.role,
        )

        return {
            "success": True,
            "skill_id": None,
            "outputs": {"result": output},
            "tokens_used": len(fallback_prompt) // 4 + len(output) // 4,
            "execution_time_ms": 500,
        }
