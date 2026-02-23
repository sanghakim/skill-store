"""
Agent Dispatcher - Routes tasks to appropriate agents.
Handles parallel/sequential execution based on dependency DAG.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Awaitable

from skillforge.agents.base import BaseAgent
from skillforge.models import AgentRole, ExecutionPlan, SubTask, TaskStatus

logger = logging.getLogger(__name__)

# Type alias for the event callback
EventCallback = Callable[[dict[str, Any]], Awaitable[None]] | None


class AgentDispatcher:
    """Dispatches sub-tasks to agents based on the execution plan DAG."""

    def __init__(self, agents: dict[AgentRole, BaseAgent], max_parallel: int = 5):
        self.agents = agents
        self.max_parallel = max_parallel

    async def _emit(self, callback: EventCallback, event: dict[str, Any]) -> None:
        """Safely emit an event via the callback, if provided."""
        if callback:
            try:
                await callback(event)
            except Exception as exc:
                logger.warning("Event callback error: %s", exc)

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        session_id: str,
        event_callback: EventCallback = None,
    ) -> dict[str, Any]:
        """
        Execute all tasks in the plan respecting dependency order.
        Tasks without dependencies run in parallel.
        """
        start_time = time.time()
        results: dict[str, dict[str, Any]] = {}
        total_tokens = 0

        # Build dependency sets
        remaining = {t.task_id: t for t in plan.tasks}
        completed_ids: set[str] = set()

        logger.info(
            "Dispatcher executing plan: %d tasks, parallel_limit=%d",
            len(plan.tasks), self.max_parallel,
        )

        while remaining:
            # Find tasks whose dependencies are all completed
            ready = [
                t for t in remaining.values()
                if all(dep in completed_ids for dep in t.dependencies)
            ]

            if not ready:
                # Deadlock detection
                logger.error("Deadlock detected: no tasks ready but %d remaining", len(remaining))
                for tid, task in remaining.items():
                    task.status = TaskStatus.FAILED
                    results[tid] = {"success": False, "error": "Deadlock - unresolvable dependencies"}
                break

            # Limit parallel execution
            batch = ready[:self.max_parallel]

            logger.info(
                "Dispatching batch: %d tasks [%s]",
                len(batch),
                ", ".join(f"{t.agent_role.value}:{t.skill_id or 'no-skill'}" for t in batch),
            )

            # Emit task_started events for each task in the batch
            for task in batch:
                await self._emit(event_callback, {
                    "type": "task_started",
                    "task_id": task.task_id,
                    "agent": task.agent_role.value,
                    "skill_id": task.skill_id,
                    "description": task.description,
                    "priority": task.priority,
                })

            # Execute batch in parallel
            coros = [
                self._execute_task(task, session_id, results)
                for task in batch
            ]
            batch_results = await asyncio.gather(*coros, return_exceptions=True)

            # Process results
            for task, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    results[task.task_id] = {"success": False, "error": str(result)}
                    logger.error("Task %s failed with exception: %s", task.task_id, result)

                    await self._emit(event_callback, {
                        "type": "task_failed",
                        "task_id": task.task_id,
                        "agent": task.agent_role.value,
                        "skill_id": task.skill_id,
                        "error": str(result),
                    })
                else:
                    results[task.task_id] = result
                    task.status = TaskStatus.COMPLETED if result.get("success") else TaskStatus.FAILED
                    total_tokens += result.get("tokens_used", 0)

                    await self._emit(event_callback, {
                        "type": "task_completed" if result.get("success") else "task_failed",
                        "task_id": task.task_id,
                        "agent": task.agent_role.value,
                        "skill_id": task.skill_id,
                        "success": result.get("success", False),
                        "tokens_used": result.get("tokens_used", 0),
                        "execution_time_ms": result.get("execution_time_ms", 0),
                        "output_preview": str(result.get("outputs", {}))[:300],
                    })

                completed_ids.add(task.task_id)
                remaining.pop(task.task_id, None)

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "task_results": results,
            "total_tokens": total_tokens,
            "total_time_ms": elapsed_ms,
            "tasks_completed": len(completed_ids),
            "tasks_failed": sum(1 for r in results.values() if not r.get("success", True)),
        }

    async def _execute_task(
        self,
        task: SubTask,
        session_id: str,
        previous_results: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Execute a single sub-task by routing to the appropriate agent."""
        agent = self.agents.get(task.agent_role)
        if not agent:
            return {"success": False, "error": f"No agent for role: {task.agent_role.value}"}

        task.status = TaskStatus.EXECUTING

        # Build context with previous task results
        context: dict[str, Any] = {
            "task_id": task.task_id,
            "skill_id": task.skill_id,
            "skill_inputs": dict(task.skill_inputs),
            "previous_results": {
                tid: res.get("outputs", {})
                for tid, res in previous_results.items()
                if res.get("success")
            },
        }

        # For reviewer, inject outputs to review
        if task.agent_role == AgentRole.REVIEWER:
            all_outputs = {}
            for dep_id in task.dependencies:
                dep_result = previous_results.get(dep_id, {})
                if dep_result.get("outputs"):
                    all_outputs.update(dep_result["outputs"])
            context["outputs"] = all_outputs
            context["original_request"] = task.description

        logger.info(
            "Executing task: %s (%s, skill=%s)",
            task.task_id[:8], task.agent_role.value, task.skill_id or "none",
        )

        result = await agent.run(session_id, task.description, context)
        task.status = TaskStatus.COMPLETED if result.get("success") else TaskStatus.FAILED

        return result

    async def execute_single(
        self,
        agent_role: AgentRole,
        session_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a single task directly on an agent (no plan needed)."""
        agent = self.agents.get(agent_role)
        if not agent:
            return {"success": False, "error": f"No agent for role: {agent_role.value}"}
        return await agent.run(session_id, task_description, context)
