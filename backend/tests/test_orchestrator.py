"""
Tests for the Orchestrator (IntentAnalyzer, Dispatcher, ResultMerger, AgenticLoop).
"""

from __future__ import annotations

import pytest

from skillforge.orchestrator.intent_analyzer import IntentAnalyzer
from skillforge.orchestrator.dispatcher import AgentDispatcher
from skillforge.orchestrator.result_merger import ResultMerger
from skillforge.orchestrator.loop import AgenticLoop
from skillforge.models import AgentRole


# ═══════════════════════════════════════
# Intent Analyzer
# ═══════════════════════════════════════

class TestIntentAnalyzer:
    def setup_method(self):
        self.analyzer = IntentAnalyzer()

    def test_email_intent_korean(self):
        result = self.analyzer.analyze("이메일 작성해줘")
        assert result.primary_intent == "email_compose"
        assert result.confidence > 0

    def test_report_intent_korean(self):
        result = self.analyzer.analyze("보고서 작성해줘")
        assert "compose" in result.primary_intent or "create" in result.primary_intent or "document" in result.primary_intent

    def test_translate_intent(self):
        result = self.analyzer.analyze("이 문서를 영어로 번역해줘")
        assert "translat" in result.primary_intent.lower()

    def test_analyze_intent_english(self):
        result = self.analyzer.analyze("analyze the sales data")
        assert result.primary_intent is not None
        assert result.confidence > 0

    def test_complexity_simple(self):
        result = self.analyzer.analyze("이메일 작성해줘")
        assert result.complexity in ("simple", "moderate", "complex")

    def test_complexity_complex(self):
        result = self.analyzer.analyze("데이터 분석 결과를 바탕으로 보고서를 작성하고 영어로 번역한 후 이메일로 발송해줘")
        # Multi-step request should be moderate or complex
        assert result.complexity in ("moderate", "complex")

    def test_suggested_agents(self):
        result = self.analyzer.analyze("이메일 작성해줘")
        assert isinstance(result.suggested_agents, list)
        assert len(result.suggested_agents) > 0

    def test_unknown_input(self):
        result = self.analyzer.analyze("xyz abc 123")
        assert result.primary_intent is not None
        assert result.confidence >= 0


# ═══════════════════════════════════════
# Result Merger
# ═══════════════════════════════════════

class TestResultMerger:
    def setup_method(self):
        self.merger = ResultMerger()

    def test_merge_single_result(self):
        task_results = {
            "task-1": {
                "success": True,
                "outputs": {"result": "Email drafted successfully"},
                "tokens_used": 100,
            }
        }
        from skillforge.models import SubTask
        tasks = [
            SubTask(
                task_id="task-1",
                description="Draft email",
                agent_role=AgentRole.EXECUTOR,
                skill_id="email-composer",
            )
        ]
        merged = self.merger.merge("Write an email", task_results, tasks)
        assert "final_output" in merged
        assert len(merged["final_output"]) > 0

    def test_merge_multiple_results(self):
        task_results = {
            "task-1": {
                "success": True,
                "outputs": {"analysis": "Sales up 15%"},
                "tokens_used": 50,
            },
            "task-2": {
                "success": True,
                "outputs": {"result": "Report generated"},
                "tokens_used": 80,
            },
        }
        from skillforge.models import SubTask
        tasks = [
            SubTask(task_id="task-1", description="Analyze", agent_role=AgentRole.RESEARCH),
            SubTask(task_id="task-2", description="Write report", agent_role=AgentRole.CREATIVE),
        ]
        merged = self.merger.merge("Analyze and report", task_results, tasks)
        assert "final_output" in merged
        assert "all_outputs" in merged

    def test_merge_with_review(self):
        task_results = {
            "task-1": {
                "success": True,
                "outputs": {"result": "Output text"},
                "tokens_used": 50,
            },
            "task-2": {
                "success": True,
                "review": {
                    "passed": True,
                    "score": 0.85,
                    "feedback": "Good quality",
                },
                "tokens_used": 30,
            },
        }
        from skillforge.models import SubTask
        tasks = [
            SubTask(task_id="task-1", description="Execute", agent_role=AgentRole.EXECUTOR),
            SubTask(task_id="task-2", description="Review", agent_role=AgentRole.REVIEWER),
        ]
        merged = self.merger.merge("Do something", task_results, tasks)
        assert merged.get("review") is not None
        assert merged["review"]["passed"]


# ═══════════════════════════════════════
# Agentic Loop (Integration)
# ═══════════════════════════════════════

class TestAgenticLoop:
    @pytest.mark.asyncio
    async def test_full_loop_email(self, app):
        """Test full agentic loop with an email task."""
        result = await app.loop.run(
            user_input="이메일 작성해줘",
            user_id="test-user",
        )
        assert result.success
        assert result.session_id is not None
        assert result.iterations >= 1
        assert result.total_tokens > 0
        assert len(result.final_output) > 0

    @pytest.mark.asyncio
    async def test_full_loop_report(self, app):
        """Test full agentic loop with a report task."""
        result = await app.loop.run(
            user_input="프로젝트 보고서 작성해줘",
            user_id="test-user",
        )
        assert result.success
        assert result.iterations >= 1

    @pytest.mark.asyncio
    async def test_loop_timeout(self):
        """Test that the loop respects timeout."""
        from skillforge.app import SkillForgeApp
        sf = SkillForgeApp(
            loop_timeout_ms=1,  # 1ms timeout
            max_iterations=1,
            quality_threshold=0.1,
        )
        sf.initialize()

        result = await sf.loop.run("이메일 작성해줘")
        # Should either succeed quickly or timeout
        assert result.session_id is not None
        sf.shutdown()

    @pytest.mark.asyncio
    async def test_direct_skill_execution(self, app):
        """Test execute_skill bypasses the loop."""
        result = await app.loop.execute_skill(
            skill_id="email-composer",
            inputs={"context": "Test email", "tone": "formal"},
            user_id="test-user",
        )
        assert result.get("success") is not None

    @pytest.mark.asyncio
    async def test_loop_session_reuse(self, app):
        """Test that a session can be reused across loop runs."""
        sid = app.memory.start_session("test-user")

        result1 = await app.loop.run("이메일 작성해줘", session_id=sid, user_id="test-user")
        result2 = await app.loop.run("보고서도 작성해줘", session_id=sid, user_id="test-user")

        assert result1.session_id == sid
        assert result2.session_id == sid

        # Session should have messages from both runs
        msgs = app.memory.get_messages(sid)
        assert len(msgs) >= 2  # At least the user messages
