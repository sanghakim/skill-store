"""
Planner Agent - Decomposes complex tasks into sub-task DAGs.
Determines which agents and skills are needed for each sub-task.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from skillforge.agents.base import BaseAgent
from skillforge.models import (
    AgentRole,
    ExecutionPlan,
    SkillCategory,
    SubTask,
    TaskStatus,
)

logger = logging.getLogger(__name__)

# Keyword-to-skill mapping for intent detection
SKILL_HINTS: dict[str, list[tuple[str, AgentRole]]] = {
    # Korean keywords
    "이메일": [("email-composer", AgentRole.EXECUTOR)],
    "메일": [("email-composer", AgentRole.EXECUTOR)],
    "보고서": [("doc-drafter", AgentRole.CREATIVE)],
    "기획서": [("doc-drafter", AgentRole.CREATIVE)],
    "제안서": [("doc-drafter", AgentRole.CREATIVE)],
    "회의록": [("meeting-minutes", AgentRole.CREATIVE)],
    "계약서": [("contract-reviewer", AgentRole.RESEARCH)],
    "번역": [("biz-translator", AgentRole.EXECUTOR)],
    "교정": [("proofreader", AgentRole.EXECUTOR)],
    "분석": [("excel-analyzer", AgentRole.RESEARCH)],
    "데이터": [("excel-analyzer", AgentRole.RESEARCH)],
    "차트": [("excel-analyzer", AgentRole.RESEARCH)],
    "일정": [("schedule-optimizer", AgentRole.EXECUTOR)],
    "스케줄": [("schedule-optimizer", AgentRole.EXECUTOR)],
    "PPT": [("slide-outliner", AgentRole.CREATIVE)],
    "프레젠테이션": [("slide-outliner", AgentRole.CREATIVE)],
    "발표": [("slide-outliner", AgentRole.CREATIVE), ("talking-points", AgentRole.CREATIVE)],
    "채용": [("jd-writer", AgentRole.CREATIVE)],
    "SOP": [("sop-generator", AgentRole.CREATIVE)],
    "절차서": [("sop-generator", AgentRole.CREATIVE)],
    "자동화": [("report-scheduler", AgentRole.EXECUTOR)],
    "요약": [("email-summarizer", AgentRole.EXECUTOR)],
    # Deep Research / Web Search keywords (Korean)
    "리서치": [("deep-researcher", AgentRole.RESEARCH)],
    "조사": [("deep-researcher", AgentRole.RESEARCH)],
    "검색": [("deep-researcher", AgentRole.RESEARCH)],
    "심층": [("deep-researcher", AgentRole.RESEARCH)],
    "트렌드": [("deep-researcher", AgentRole.RESEARCH)],
    "시장조사": [("deep-researcher", AgentRole.RESEARCH)],
    "경쟁분석": [("deep-researcher", AgentRole.RESEARCH)],
    "동향": [("deep-researcher", AgentRole.RESEARCH)],
    "벤치마크": [("deep-researcher", AgentRole.RESEARCH)],
    # English keywords
    "email": [("email-composer", AgentRole.EXECUTOR)],
    "report": [("doc-drafter", AgentRole.CREATIVE)],
    "translate": [("biz-translator", AgentRole.EXECUTOR)],
    "analyze": [("excel-analyzer", AgentRole.RESEARCH)],
    "schedule": [("schedule-optimizer", AgentRole.EXECUTOR)],
    "presentation": [("slide-outliner", AgentRole.CREATIVE)],
    "research": [("deep-researcher", AgentRole.RESEARCH)],
    "search": [("deep-researcher", AgentRole.RESEARCH)],
    "trend": [("deep-researcher", AgentRole.RESEARCH)],
    "market": [("deep-researcher", AgentRole.RESEARCH)],
    "competitor": [("deep-researcher", AgentRole.RESEARCH)],
}


class PlannerAgent(BaseAgent):
    """Decomposes user requests into executable sub-task plans."""

    role = AgentRole.PLANNER

    async def process(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze the user request and generate an ExecutionPlan (DAG of SubTasks).
        """
        context = context or {}
        logger.info("Planner analyzing: %s", task_description[:80])

        # 1. Detect intents and required skills
        detected_skills = self._detect_skills(task_description)

        # 2. Build sub-tasks
        tasks = self._build_tasks(task_description, detected_skills, context)

        # 3. Always add a review task at the end
        if tasks:
            dependency_ids = [t.task_id for t in tasks if t.agent_role != AgentRole.REVIEWER]
            review_task = SubTask(
                description=f"Review and validate all outputs for: {task_description[:60]}",
                agent_role=AgentRole.REVIEWER,
                skill_id=None,
                dependencies=dependency_ids,
                priority=len(tasks) + 1,
            )
            tasks.append(review_task)

        plan = ExecutionPlan(
            user_request=task_description,
            tasks=tasks,
            iteration=context.get("iteration", 1),
        )

        logger.info(
            "Plan generated: %d tasks, skills=%s",
            len(tasks),
            [t.skill_id for t in tasks if t.skill_id],
        )

        return {
            "success": True,
            "plan": plan,
            "task_count": len(tasks),
            "skills_needed": [t.skill_id for t in tasks if t.skill_id],
        }

    def _detect_skills(self, text: str) -> list[tuple[str, AgentRole]]:
        """Detect required skills using keyword hints AND description matching."""
        detected = []
        text_lower = text.lower()

        # 1. Keyword-based detection (primary, fast, deterministic)
        for keyword, skill_pairs in SKILL_HINTS.items():
            if keyword.lower() in text_lower:
                for skill_id, agent in skill_pairs:
                    if (skill_id, agent) not in detected:
                        if self.registry.exists(skill_id):
                            detected.append((skill_id, agent))

        # 2. Description-based activation for SKILL.md skills (fallback)
        if not detected:
            detected = self._match_by_description(text_lower)

        # 3. Final fallback
        if not detected:
            detected.append((None, AgentRole.CREATIVE))

        return detected

    def _match_by_description(
        self, text_lower: str
    ) -> list[tuple[str, AgentRole]]:
        """Match user input against skill descriptions for activation.
        Primarily useful for SKILL.md skills without keyword hints."""
        from skillforge.models import SourceType

        matches = []
        words = set(text_lower.split())

        for skill in self.registry.list_all():
            desc_lower = skill.description.lower()
            desc_words = set(desc_lower.split())

            # Count overlapping significant words (>3 chars)
            overlap = words & desc_words
            significant = {w for w in overlap if len(w) > 3}

            if len(significant) >= 2:
                if skill.source_type == SourceType.SKILLMD:
                    role = AgentRole.EXECUTOR
                elif skill.category.value in ("data", "knowledge"):
                    role = AgentRole.RESEARCH
                else:
                    role = AgentRole.CREATIVE

                matches.append((skill.id, role, len(significant)))

        matches.sort(key=lambda x: x[2], reverse=True)
        return [(sid, role) for sid, role, _ in matches[:3]]

    def _build_tasks(
        self,
        description: str,
        detected_skills: list[tuple[str | None, AgentRole]],
        context: dict,
    ) -> list[SubTask]:
        """Build a list of SubTasks from detected skills."""
        tasks = []
        prev_task_ids: list[str] = []

        # If we need research first (data analysis, information gathering)
        research_skills = [
            (sid, role) for sid, role in detected_skills if role == AgentRole.RESEARCH
        ]
        other_skills = [
            (sid, role) for sid, role in detected_skills if role != AgentRole.RESEARCH
        ]

        # Research tasks first (no dependencies)
        for skill_id, agent_role in research_skills:
            skill = self.registry.get(skill_id) if skill_id else None
            task = SubTask(
                description=f"Research/Analyze: {skill.name if skill else description[:50]}",
                agent_role=agent_role,
                skill_id=skill_id,
                skill_inputs=self._extract_inputs(description, skill_id),
                dependencies=[],
                priority=1,
            )
            tasks.append(task)
            prev_task_ids.append(task.task_id)

        # Execution/Creative tasks (depend on research)
        for skill_id, agent_role in other_skills:
            skill = self.registry.get(skill_id) if skill_id else None
            task = SubTask(
                description=f"Execute: {skill.name if skill else description[:50]}",
                agent_role=agent_role,
                skill_id=skill_id,
                skill_inputs=self._extract_inputs(description, skill_id),
                dependencies=list(prev_task_ids),  # depend on research tasks
                priority=2,
            )
            tasks.append(task)

        return tasks

    def _extract_inputs(self, description: str, skill_id: str | None) -> dict[str, Any]:
        """Extract skill inputs from the task description."""
        if not skill_id:
            return {"user_input": description}

        skill = self.registry.get(skill_id)
        if not skill:
            return {"user_input": description}

        inputs = {}
        for field in skill.inputs:
            if field.required:
                # Use description as the primary input for required string fields
                if field.type.value == "string":
                    inputs[field.name] = description
                elif field.default is not None:
                    inputs[field.name] = field.default

            # Try to detect enum values from the description
            if field.values:
                for val in field.values:
                    if val.lower() in description.lower():
                        inputs[field.name] = val
                        break
                if field.name not in inputs and field.default:
                    inputs[field.name] = field.default
                elif field.name not in inputs and field.values:
                    inputs[field.name] = field.values[0]

        return inputs
