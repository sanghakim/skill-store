"""
Agentic Loop - The core execution cycle:
  User Input → Intent Analysis → Plan Generation → [Loop Start]
    → Agent Dispatch → Skill Execution → Quality Review
    → (FAIL: Re-plan) → [Loop Start]
    → (PASS: Result Assembly) → User Output

Control parameters:
  - max_iterations: Maximum retry cycles (default: 3)
  - quality_threshold: Minimum score to pass (default: 0.75)
  - timeout_ms: Global timeout (default: 300000, 5 minutes)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Awaitable

from skillforge.agents.base import BaseAgent
from skillforge.agents.planner import PlannerAgent
from skillforge.agents.executor import ExecutorAgent
from skillforge.agents.reviewer import ReviewerAgent
from skillforge.agents.research import ResearchAgent
from skillforge.agents.creative import CreativeAgent
from skillforge.engine.registry import SkillRegistry
from skillforge.engine.sandbox import SkillSandbox
from skillforge.memory.manager import MemoryManager
from skillforge.models import (
    AgentRole,
    ExecutionPlan,
    OrchestrationResult,
)
from skillforge.orchestrator.intent_analyzer import IntentAnalyzer
from skillforge.orchestrator.dispatcher import AgentDispatcher
from skillforge.orchestrator.result_merger import ResultMerger

logger = logging.getLogger(__name__)

# Type alias for the event callback
EventCallback = Callable[[dict[str, Any]], Awaitable[None]] | None


class AgenticLoop:
    """
    The main orchestration engine. Implements the Plan-Execute-Review loop.
    """

    def __init__(
        self,
        memory: MemoryManager,
        registry: SkillRegistry,
        sandbox: SkillSandbox,
        max_iterations: int = 3,
        quality_threshold: float = 0.75,
        timeout_ms: int = 300_000,
        max_parallel: int = 5,
    ):
        self.memory = memory
        self.registry = registry
        self.sandbox = sandbox
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        self.timeout_ms = timeout_ms

        # Initialize components
        self.intent_analyzer = IntentAnalyzer()
        self.result_merger = ResultMerger()

        # Initialize agents
        self.agents: dict[AgentRole, BaseAgent] = {
            AgentRole.PLANNER: PlannerAgent(memory, registry, sandbox),
            AgentRole.EXECUTOR: ExecutorAgent(memory, registry, sandbox),
            AgentRole.REVIEWER: ReviewerAgent(
                memory, registry, sandbox,
                quality_threshold=quality_threshold,
            ),
            AgentRole.RESEARCH: ResearchAgent(memory, registry, sandbox),
            AgentRole.CREATIVE: CreativeAgent(memory, registry, sandbox),
        }

        self.dispatcher = AgentDispatcher(self.agents, max_parallel=max_parallel)

        logger.info(
            "AgenticLoop initialized: max_iter=%d, threshold=%.2f, timeout=%dms",
            max_iterations, quality_threshold, timeout_ms,
        )

    async def _emit(self, callback: EventCallback, event: dict[str, Any]) -> None:
        """Safely emit an event via the callback, if provided."""
        if callback:
            try:
                await callback(event)
            except Exception as exc:
                logger.warning("Event callback error: %s", exc)

    async def run(
        self,
        user_input: str,
        session_id: str | None = None,
        user_id: str = "default",
        event_callback: EventCallback = None,
    ) -> OrchestrationResult:
        """
        Main entry point: process a user request through the full agentic loop.

        Args:
            user_input: The user's natural language request.
            session_id: Optional session ID to reuse.
            user_id: User identifier (default: "default").
            event_callback: Optional async callback for real-time event streaming.
                           Called with dict events at each lifecycle stage.
        """
        start_time = time.time()

        # Create or reuse session
        if not session_id:
            session_id = self.memory.start_session(user_id)

        # Record user message
        self.memory.add_message(session_id, "user", user_input)

        logger.info("=== AgenticLoop START === session=%s input=%s", session_id, user_input[:80])

        await self._emit(event_callback, {
            "type": "processing_started",
            "session_id": session_id,
            "message": user_input[:200],
        })

        try:
            result = await asyncio.wait_for(
                self._run_loop(user_input, session_id, event_callback),
                timeout=self.timeout_ms / 1000,
            )
            result.session_id = session_id
            result.total_time_ms = int((time.time() - start_time) * 1000)

            # Emit final response event
            await self._emit(event_callback, {
                "type": "processing_complete",
                "session_id": session_id,
                "success": result.success,
                "total_time_ms": result.total_time_ms,
            })

            return result

        except asyncio.TimeoutError:
            logger.error("AgenticLoop timed out after %dms", self.timeout_ms)
            await self._emit(event_callback, {
                "type": "error",
                "error": f"Execution timed out after {self.timeout_ms}ms",
                "code": "TIMEOUT",
            })
            return OrchestrationResult(
                session_id=session_id,
                user_request=user_input,
                success=False,
                error=f"Execution timed out after {self.timeout_ms}ms",
                total_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as exc:
            logger.exception("AgenticLoop unexpected error")
            await self._emit(event_callback, {
                "type": "error",
                "error": str(exc),
                "code": "INTERNAL_ERROR",
            })
            return OrchestrationResult(
                session_id=session_id,
                user_request=user_input,
                success=False,
                error=str(exc),
                total_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _run_loop(
        self,
        user_input: str,
        session_id: str,
        event_callback: EventCallback = None,
    ) -> OrchestrationResult:
        """Inner loop with retry logic."""

        # ── Step 1: Intent Analysis ──
        intent = self.intent_analyzer.analyze(user_input)
        logger.info(
            "Intent: %s (complexity=%s, confidence=%.2f)",
            intent.primary_intent, intent.complexity, intent.confidence,
        )

        await self._emit(event_callback, {
            "type": "intent_analyzed",
            "intent": intent.primary_intent,
            "complexity": intent.complexity,
            "confidence": intent.confidence,
            "suggested_agents": [a.value for a in intent.suggested_agents],
            "language": intent.language,
        })

        # ── Step 2: Plan Generation ──
        plan_result = await self.agents[AgentRole.PLANNER].run(
            session_id,
            user_input,
            context={
                "intent": intent.primary_intent,
                "complexity": intent.complexity,
                "iteration": 1,
            },
        )
        plan: ExecutionPlan = plan_result.get("plan")
        if not plan or not plan.tasks:
            return OrchestrationResult(
                session_id=session_id,
                user_request=user_input,
                final_output="요청을 분석했지만 실행 가능한 작업을 생성하지 못했습니다.",
                success=False,
                error="Empty execution plan",
            )

        await self._emit(event_callback, {
            "type": "plan_created",
            "plan_id": plan.plan_id,
            "iteration": plan.iteration,
            "task_count": len(plan.tasks),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "agent_role": t.agent_role.value,
                    "skill_id": t.skill_id,
                    "dependencies": t.dependencies,
                    "priority": t.priority,
                }
                for t in plan.tasks
            ],
        })

        # ── Step 3: Iterative Execute → Review Loop ──
        final_result: OrchestrationResult | None = None
        total_tokens = 0

        for iteration in range(1, self.max_iterations + 1):
            logger.info("=== Iteration %d/%d ===", iteration, self.max_iterations)

            await self._emit(event_callback, {
                "type": "iteration_start",
                "iteration": iteration,
                "max_iterations": self.max_iterations,
            })

            # Execute plan
            dispatch_result = await self.dispatcher.execute_plan(
                plan, session_id, event_callback=event_callback,
                original_request=user_input,
            )
            task_results = dispatch_result["task_results"]
            total_tokens += dispatch_result["total_tokens"]

            # Merge results
            merged = self.result_merger.merge(
                user_input, task_results, plan.tasks
            )
            total_tokens += merged.get("total_tokens", 0)

            # Check review verdict
            review = merged.get("review")
            passed = True
            quality_score = 1.0

            if review:
                passed = review.get("passed", True)
                quality_score = review.get("score", 1.0)
                logger.info(
                    "Review: score=%.2f passed=%s feedback=%s",
                    quality_score, passed, review.get("feedback", "")[:100],
                )

                await self._emit(event_callback, {
                    "type": "review_completed",
                    "iteration": iteration,
                    "score": quality_score,
                    "passed": passed,
                    "feedback": review.get("feedback", ""),
                    "aspects": review.get("items", []),
                })

            if passed or iteration == self.max_iterations:
                # Build final result
                final_result = OrchestrationResult(
                    session_id=session_id,
                    user_request=user_input,
                    plan=plan,
                    final_output=merged["final_output"],
                    agent_outputs=merged["all_outputs"],
                    total_tokens=total_tokens,
                    iterations=iteration,
                    success=True,
                )

                if review:
                    from skillforge.models import QualityReview
                    if isinstance(review, dict):
                        final_result.quality_review = QualityReview(
                            task_id="final",
                            overall_score=review.get("score", 0),
                            passed=review.get("passed", True),
                            feedback=review.get("feedback", ""),
                        )

                # Record assistant output
                self.memory.add_message(
                    session_id,
                    "assistant",
                    merged["final_output"][:500],
                    agent=AgentRole.ORCHESTRATOR,
                )

                if not passed:
                    logger.warning(
                        "Max iterations reached. Returning best-effort result (score=%.2f)",
                        quality_score,
                    )
                    final_result.error = f"Quality threshold not met after {iteration} iterations (score={quality_score:.2f})"

                await self._emit(event_callback, {
                    "type": "iteration_complete",
                    "iteration": iteration,
                    "passed": passed,
                    "quality_score": quality_score,
                    "total_tokens": total_tokens,
                })

                break

            else:
                # ── Re-plan for next iteration ──
                logger.info("Re-planning for iteration %d...", iteration + 1)
                feedback = review.get("feedback", "") if review else ""

                await self._emit(event_callback, {
                    "type": "replanning",
                    "iteration": iteration + 1,
                    "reason": feedback or "Quality threshold not met",
                })

                plan_result = await self.agents[AgentRole.PLANNER].run(
                    session_id,
                    user_input,
                    context={
                        "intent": intent.primary_intent,
                        "complexity": intent.complexity,
                        "iteration": iteration + 1,
                        "previous_feedback": feedback,
                    },
                )
                plan = plan_result.get("plan", plan)

                await self._emit(event_callback, {
                    "type": "plan_created",
                    "plan_id": plan.plan_id,
                    "iteration": plan.iteration,
                    "task_count": len(plan.tasks),
                    "tasks": [
                        {
                            "task_id": t.task_id,
                            "description": t.description,
                            "agent_role": t.agent_role.value,
                            "skill_id": t.skill_id,
                            "dependencies": t.dependencies,
                            "priority": t.priority,
                        }
                        for t in plan.tasks
                    ],
                })

        logger.info(
            "=== AgenticLoop END === iterations=%d tokens=%d success=%s",
            final_result.iterations if final_result else 0,
            total_tokens,
            final_result.success if final_result else False,
        )

        return final_result or OrchestrationResult(
            session_id=session_id,
            user_request=user_input,
            success=False,
            error="No result produced",
        )

    # ── Direct Skill Execution (bypass loop) ──

    async def execute_skill(
        self,
        skill_id: str,
        inputs: dict[str, Any],
        session_id: str | None = None,
        user_id: str = "default",
    ) -> dict[str, Any]:
        """Execute a single skill directly without the full agentic loop."""
        if not session_id:
            session_id = self.memory.start_session(user_id)

        return await self.dispatcher.execute_single(
            AgentRole.EXECUTOR,
            session_id,
            f"Execute skill: {skill_id}",
            context={"skill_id": skill_id, "skill_inputs": inputs},
        )

    def get_agent(self, role: AgentRole) -> BaseAgent | None:
        return self.agents.get(role)
