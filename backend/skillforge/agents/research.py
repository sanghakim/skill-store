"""
Research Agent - Gathers information, analyzes data, searches context.
Leverages Semantic Memory for RAG retrieval and Episodic Memory for history.
Integrates with WebSearchProvider for real-time web research (deep-researcher skill).
"""

from __future__ import annotations

import logging
from typing import Any

from skillforge.agents.base import BaseAgent
from skillforge.models import AgentRole

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Gathers information and context to support other agents."""

    role = AgentRole.RESEARCH

    async def process(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        skill_id = context.get("skill_id")
        skill_inputs = context.get("skill_inputs", {})

        logger.info("Research agent working: %s", task_description[:80])

        results: dict[str, Any] = {
            "success": True,
            "research_data": {},
            "context_enrichment": "",
        }

        # 1. Search semantic memory for relevant knowledge
        semantic_context = self.memory.semantic.build_context(
            task_description,
            user_id=self.memory.working.get_session(session_id).user_id
            if self.memory.working.get_session(session_id) else None,
            top_k=5,
        )
        results["research_data"]["semantic_knowledge"] = semantic_context

        # 2. Search episodic memory for similar past tasks
        state = self.memory.working.get_session(session_id)
        if state:
            history = self.memory.episodic.search_history(state.user_id, task_description)
            if history:
                past_summaries = [
                    f"[{e.timestamp.strftime('%Y-%m-%d')}] {e.summary}"
                    for e in history[:3]
                ]
                results["research_data"]["past_experience"] = past_summaries

        # 3. Deep Research: if skill is deep-researcher, run the full pipeline
        if skill_id == "deep-researcher":
            deep_result = self._run_deep_research(session_id, skill_inputs, semantic_context)
            results["research_data"]["deep_research"] = deep_result
            if deep_result.get("report"):
                results["tokens_used"] = len(deep_result["report"]) // 4
                # Store for other agents
                self.memory.working.set_shared_var(
                    session_id,
                    "research:deep-researcher",
                    deep_result,
                )
        # 4. Other skills: execute via sandbox as before
        elif skill_id:
            skill = self.registry.get(skill_id)
            if skill:
                from skillforge.models import SkillExecutionRequest
                request = SkillExecutionRequest(
                    skill_id=skill_id,
                    inputs=skill_inputs,
                )
                exec_result = self.sandbox.execute(skill, request, extra_context=semantic_context)
                if exec_result.success:
                    results["research_data"]["skill_output"] = exec_result.outputs
                    results["tokens_used"] = exec_result.tokens_used
                    # Store for other agents
                    self.memory.working.set_shared_var(
                        session_id,
                        f"research:{skill_id}",
                        exec_result.outputs,
                    )
                else:
                    results["research_data"]["skill_error"] = exec_result.error

        # 5. Build context enrichment string
        enrichment_parts = []
        if semantic_context:
            enrichment_parts.append(f"[Relevant Knowledge]\n{semantic_context}")
        past = results["research_data"].get("past_experience", [])
        if past:
            enrichment_parts.append(f"[Past Experience]\n" + "\n".join(past))
        skill_out = results["research_data"].get("skill_output", {})
        if skill_out:
            enrichment_parts.append(f"[Research Results]\n{str(skill_out)[:500]}")
        deep = results["research_data"].get("deep_research", {})
        if deep.get("report"):
            enrichment_parts.append(
                f"[Deep Research Report]\n{deep['report'][:1000]}"
            )
            if deep.get("sources"):
                src_text = "\n".join(
                    f"- {s['title']} ({s['url']})" for s in deep["sources"][:5]
                )
                enrichment_parts.append(f"[Sources]\n{src_text}")

        results["context_enrichment"] = "\n\n".join(enrichment_parts)

        # Log
        self.memory.add_message(
            session_id,
            "assistant",
            f"[Research] Gathered context: {len(enrichment_parts)} sources, "
            f"{len(results['context_enrichment'])} chars"
            + (f", deep_research=True" if "deep_research" in results["research_data"] else ""),
            agent=self.role,
        )

        return results

    def _run_deep_research(
        self,
        session_id: str,
        skill_inputs: dict[str, Any],
        semantic_context: str,
    ) -> dict[str, Any]:
        """
        Execute the deep research pipeline using the DeepResearchEngine.
        This integrates web search → content extraction → LLM synthesis.
        """
        from skillforge.skills.builtins.deep_research import DeepResearchEngine
        from skillforge.skills.builtins.web_search import WebSearchProvider

        topic = skill_inputs.get("topic", "")
        depth = skill_inputs.get("depth", "standard")
        perspective = skill_inputs.get("perspective", "")
        output_format = skill_inputs.get("output_format", "보고서")
        language = skill_inputs.get("language", "ko")

        if not topic:
            return {"report": "", "sources": [], "error": "No topic provided"}

        try:
            # Determine if we should use simulated or real search
            from skillforge.engine.sandbox import SimulatedLLMBackend
            use_simulated = isinstance(self.sandbox._llm, SimulatedLLMBackend)

            search_provider = WebSearchProvider(use_simulated=use_simulated)

            engine = DeepResearchEngine(
                llm_backend=self.sandbox._llm,
                search_provider=search_provider,
            )

            result = engine.execute(
                topic=topic,
                depth=depth,
                perspective=perspective,
                language=language,
                output_format=output_format,
            )

            logger.info(
                "Deep research completed: topic='%s', sources=%d, time=%dms",
                topic[:40],
                len(result.get("sources", [])),
                result.get("metadata", {}).get("execution_time_ms", 0),
            )

            return result

        except Exception as exc:
            logger.error("Deep research pipeline failed: %s", exc)
            return {
                "report": "",
                "sources": [],
                "error": str(exc),
            }
