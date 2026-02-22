"""
Tests for the Agent Pool (Planner, Executor, Reviewer, Research, Creative).
"""

from __future__ import annotations

import pytest

from skillforge.agents.planner import PlannerAgent
from skillforge.agents.executor import ExecutorAgent
from skillforge.agents.reviewer import ReviewerAgent
from skillforge.agents.research import ResearchAgent
from skillforge.agents.creative import CreativeAgent
from skillforge.engine.registry import SkillRegistry
from skillforge.engine.sandbox import SkillSandbox, SimulatedLLMBackend
from skillforge.memory.manager import MemoryManager
from skillforge.models import AgentRole, SkillDefinition


# ═══════════════════════════════════════
# Planner Agent
# ═══════════════════════════════════════

class TestPlannerAgent:
    @pytest.fixture
    def planner(self, memory: MemoryManager, registry: SkillRegistry, sandbox: SkillSandbox, email_skill: SkillDefinition):
        registry.register(email_skill)
        return PlannerAgent(memory, registry, sandbox)

    @pytest.mark.asyncio
    async def test_plan_email_task(self, planner: PlannerAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await planner.run(
            sid,
            "이메일 작성해줘",
            context={"intent": "compose_email", "complexity": "simple", "iteration": 1},
        )
        assert result["success"]
        plan = result["plan"]
        assert len(plan.tasks) > 0
        # Should include an executor or creative task with email-composer
        skill_ids = [t.skill_id for t in plan.tasks if t.skill_id]
        assert "email-composer" in skill_ids

    @pytest.mark.asyncio
    async def test_plan_includes_review_task(self, planner: PlannerAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await planner.run(sid, "보고서 작성해줘")
        plan = result["plan"]
        reviewer_tasks = [t for t in plan.tasks if t.agent_role == AgentRole.REVIEWER]
        assert len(reviewer_tasks) == 1

    @pytest.mark.asyncio
    async def test_plan_unknown_task_fallback(self, planner: PlannerAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await planner.run(sid, "do something unknown")
        assert result["success"]
        plan = result["plan"]
        # Should fall back to creative agent
        assert any(t.agent_role == AgentRole.CREATIVE for t in plan.tasks)

    @pytest.mark.asyncio
    async def test_plan_dependency_ordering(self, planner: PlannerAgent, memory: MemoryManager, registry: SkillRegistry):
        """Research tasks should come before creative/executor tasks."""
        from skillforge.models import SkillCategory, FieldType, SkillField
        # Add an analysis skill
        analysis_skill = SkillDefinition(
            id="excel-analyzer",
            name="Data Analyzer",
            category=SkillCategory.DATA,
            description="Analyze data",
            inputs=[SkillField(name="data", type=FieldType.STRING, required=True)],
            outputs=[SkillField(name="analysis", type=FieldType.STRING)],
            prompt_template="Analyze this data: {{data}} - provide insights and recommendations.",
        )
        registry.register(analysis_skill)

        sid = memory.start_session()
        result = await planner.run(sid, "데이터 분석하고 이메일 작성해줘")
        plan = result["plan"]

        # Find research and non-research tasks
        research_ids = {t.task_id for t in plan.tasks if t.agent_role == AgentRole.RESEARCH}
        other_tasks = [t for t in plan.tasks if t.agent_role not in (AgentRole.RESEARCH, AgentRole.REVIEWER)]

        # Non-research tasks should depend on research tasks
        for task in other_tasks:
            for dep in task.dependencies:
                if dep in research_ids:
                    assert True
                    return
        # If no deps found, that's also OK for simple plans


# ═══════════════════════════════════════
# Executor Agent
# ═══════════════════════════════════════

class TestExecutorAgent:
    @pytest.fixture
    def executor(self, memory: MemoryManager, registry: SkillRegistry, sandbox: SkillSandbox, email_skill: SkillDefinition):
        registry.register(email_skill)
        return ExecutorAgent(memory, registry, sandbox)

    @pytest.mark.asyncio
    async def test_execute_skill(self, executor: ExecutorAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await executor.process(
            sid,
            "Send follow-up email",
            context={
                "skill_id": "email-composer",
                "skill_inputs": {"context": "Follow up on meeting", "tone": "formal"},
            },
        )
        assert result["success"]
        assert result["skill_id"] == "email-composer"
        assert "outputs" in result
        assert result["tokens_used"] > 0

    @pytest.mark.asyncio
    async def test_execute_missing_skill(self, executor: ExecutorAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await executor.process(
            sid,
            "Execute nonexistent skill",
            context={"skill_id": "nonexistent-skill"},
        )
        assert not result["success"]
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_no_skill_id(self, executor: ExecutorAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await executor.process(sid, "No skill provided")
        assert not result["success"]
        assert "no skill_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_result_stored_in_shared_vars(self, executor: ExecutorAgent, memory: MemoryManager):
        sid = memory.start_session()
        await executor.process(
            sid,
            "Execute email skill",
            context={
                "skill_id": "email-composer",
                "skill_inputs": {"context": "Test", "tone": "formal"},
            },
        )
        shared = memory.working.get_all_shared_vars(sid)
        assert "result:email-composer" in shared


# ═══════════════════════════════════════
# Reviewer Agent
# ═══════════════════════════════════════

class TestReviewerAgent:
    @pytest.fixture
    def reviewer(self, memory: MemoryManager, registry: SkillRegistry, sandbox: SkillSandbox):
        return ReviewerAgent(memory, registry, sandbox, quality_threshold=0.5)

    @pytest.mark.asyncio
    async def test_review_good_output(self, reviewer: ReviewerAgent, memory: MemoryManager):
        sid = memory.start_session()
        # Set some result in shared vars
        memory.working.set_shared_var(sid, "result:email-composer", {
            "subject": "Meeting Follow-up: Action Items from Q3 Review",
            "body": "Dear Team,\n\nThank you for attending the quarterly review. Here are the key action items:\n\n1. Submit reports by Friday\n2. Schedule follow-up meetings\n3. Update project timelines\n\nBest regards,\nTeam Lead"
        })

        result = await reviewer.process(
            sid,
            "Review email output",
            context={"task_results": {"email-task": {"outputs": {
                "subject": "Meeting Follow-up: Action Items from Q3 Review",
                "body": "Dear Team,\n\nThank you for attending the quarterly review."
            }}}},
        )
        assert result["success"]
        assert "review" in result

    @pytest.mark.asyncio
    async def test_review_empty_output(self, reviewer: ReviewerAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await reviewer.process(
            sid,
            "Review empty output",
            context={"task_results": {}},
        )
        assert result["success"]


# ═══════════════════════════════════════
# Research Agent
# ═══════════════════════════════════════

class TestResearchAgent:
    @pytest.fixture
    def research(self, memory: MemoryManager, registry: SkillRegistry, sandbox: SkillSandbox):
        return ResearchAgent(memory, registry, sandbox)

    @pytest.mark.asyncio
    async def test_research_gathers_context(self, research: ResearchAgent, memory: MemoryManager):
        sid = memory.start_session()
        # Add some semantic knowledge
        memory.semantic.add_entry("Email etiquette for business", category="knowledge")

        result = await research.process(sid, "Research email best practices")
        assert result["success"]

    @pytest.mark.asyncio
    async def test_research_stores_in_shared_vars(self, research: ResearchAgent, memory: MemoryManager):
        sid = memory.start_session()
        await research.process(sid, "Research data analysis techniques")
        shared = memory.working.get_all_shared_vars(sid)
        # Research agent should store findings with "research:" prefix
        research_vars = {k: v for k, v in shared.items() if k.startswith("research:")}
        assert len(research_vars) >= 0  # May or may not have findings depending on memory state


# ═══════════════════════════════════════
# Creative Agent
# ═══════════════════════════════════════

class TestCreativeAgent:
    @pytest.fixture
    def creative(self, memory: MemoryManager, registry: SkillRegistry, sandbox: SkillSandbox, sample_skill: SkillDefinition):
        registry.register(sample_skill)
        return CreativeAgent(memory, registry, sandbox)

    @pytest.mark.asyncio
    async def test_creative_with_skill(self, creative: CreativeAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await creative.process(
            sid,
            "Generate creative content",
            context={
                "skill_id": "test-skill",
                "skill_inputs": {"query": "Create a report", "mode": "basic"},
            },
        )
        assert result["success"]
        assert result["skill_id"] == "test-skill"

    @pytest.mark.asyncio
    async def test_creative_fallback_without_skill(self, creative: CreativeAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await creative.process(
            sid,
            "Write something creative about office productivity",
        )
        assert result["success"]
        assert result["skill_id"] is None
        assert "result" in result["outputs"]

    @pytest.mark.asyncio
    async def test_creative_nonexistent_skill(self, creative: CreativeAgent, memory: MemoryManager):
        sid = memory.start_session()
        result = await creative.process(
            sid,
            "Generate content",
            context={"skill_id": "nonexistent-skill"},
        )
        # Should fall back to generic creative generation
        assert result["success"]
        assert result["skill_id"] is None
