"""
Tests for the Memory Layer (Working, Episodic, Semantic, ContextBus, Manager).
"""

from __future__ import annotations

import pytest

from skillforge.memory.working import WorkingMemory
from skillforge.memory.episodic import EpisodicMemory
from skillforge.memory.semantic import SemanticMemory
from skillforge.memory.context_bus import ContextBus
from skillforge.memory.manager import MemoryManager
from skillforge.models import AgentMessage, AgentRole


# ═══════════════════════════════════════
# Working Memory
# ═══════════════════════════════════════

class TestWorkingMemory:
    def test_create_session(self):
        wm = WorkingMemory()
        sid = wm.create_session(user_id="user1")
        assert sid is not None
        assert wm.get_session(sid) is not None
        assert wm.get_session(sid).user_id == "user1"

    def test_add_and_get_messages(self):
        wm = WorkingMemory()
        sid = wm.create_session()
        wm.add_message(sid, "user", "Hello")
        wm.add_message(sid, "assistant", "Hi there!")
        wm.add_message(sid, "user", "How are you?")

        msgs = wm.get_messages(sid)
        assert len(msgs) == 3
        assert msgs[0].role == "user"
        assert msgs[0].content == "Hello"
        assert msgs[1].role == "assistant"

    def test_get_messages_last_n(self):
        wm = WorkingMemory()
        sid = wm.create_session()
        for i in range(10):
            wm.add_message(sid, "user", f"Message {i}")

        msgs = wm.get_messages(sid, last_n=3)
        assert len(msgs) == 3
        assert msgs[-1].content == "Message 9"

    def test_shared_vars(self):
        wm = WorkingMemory()
        sid = wm.create_session()
        wm.set_shared_var(sid, "key1", "value1")
        wm.set_shared_var(sid, "key2", {"nested": True})

        assert wm.get_shared_var(sid, "key1") == "value1"
        assert wm.get_shared_var(sid, "key2") == {"nested": True}
        assert wm.get_shared_var(sid, "nonexistent") is None

        all_vars = wm.get_all_shared_vars(sid)
        assert "key1" in all_vars
        assert "key2" in all_vars

    def test_skill_stack(self):
        wm = WorkingMemory()
        sid = wm.create_session()
        wm.push_skill(sid, "skill-a")
        wm.push_skill(sid, "skill-b")

        state = wm.get_session(sid)
        assert len(state.skill_stack) == 2

        wm.pop_skill(sid)
        state = wm.get_session(sid)
        assert len(state.skill_stack) == 1

    def test_active_agents(self):
        wm = WorkingMemory()
        sid = wm.create_session()
        wm.activate_agent(sid, AgentRole.PLANNER)
        wm.activate_agent(sid, AgentRole.EXECUTOR)

        state = wm.get_session(sid)
        assert AgentRole.PLANNER in state.active_agents
        assert AgentRole.EXECUTOR in state.active_agents

        wm.deactivate_agent(sid, AgentRole.PLANNER)
        state = wm.get_session(sid)
        assert AgentRole.PLANNER not in state.active_agents

    def test_delete_session(self):
        wm = WorkingMemory()
        sid = wm.create_session()
        wm.add_message(sid, "user", "Test")
        wm.delete_session(sid)
        assert wm.get_session(sid) is None

    def test_list_sessions(self):
        wm = WorkingMemory()
        sid1 = wm.create_session(user_id="user1")
        sid2 = wm.create_session(user_id="user2")
        sessions = wm.list_sessions()
        assert sid1 in sessions
        assert sid2 in sessions

    def test_context_string(self):
        wm = WorkingMemory()
        sid = wm.create_session()
        wm.add_message(sid, "user", "Hello")
        wm.add_message(sid, "assistant", "Hi")
        ctx = wm.get_context_string(sid)
        assert "[USER]: Hello" in ctx
        assert "[ASSISTANT]: Hi" in ctx


# ═══════════════════════════════════════
# Episodic Memory
# ═══════════════════════════════════════

class TestEpisodicMemory:
    def test_record_and_search(self):
        em = EpisodicMemory()
        em.record_session(
            user_id="user1",
            session_id="s1",
            summary="Created an email about project deadline",
            skills_used=["email-composer"],
        )
        em.record_session(
            user_id="user1",
            session_id="s2",
            summary="Analyzed Q3 sales data",
            skills_used=["excel-analyzer"],
        )

        results = em.search_history("user1", "email")
        assert len(results) >= 1
        assert any("email" in r.summary.lower() for r in results)

    def test_recent_summaries(self):
        em = EpisodicMemory()
        for i in range(5):
            em.record_session("user1", f"s{i}", f"Summary {i}", [])

        recent = em.get_recent_summaries("user1", last_n=3)
        assert len(recent) == 3

    def test_frequent_skills(self):
        em = EpisodicMemory()
        em.record_session("user1", "s1", "Test", ["email-composer"])
        em.record_session("user1", "s2", "Test", ["email-composer", "doc-drafter"])
        em.record_session("user1", "s3", "Test", ["email-composer"])

        freq = em.get_frequent_skills("user1", top_n=2)
        assert freq[0][0] == "email-composer"
        assert freq[0][1] == 3

    def test_get_stats(self):
        em = EpisodicMemory()
        em.record_session("user1", "s1", "Test", ["skill-a"])
        assert em.get_session_count("user1") >= 1
        assert em.get_success_rate("user1") >= 0.0


# ═══════════════════════════════════════
# Semantic Memory
# ═══════════════════════════════════════

class TestSemanticMemory:
    def test_add_and_search(self):
        sm = SemanticMemory()
        sm.add_entry("Python programming language", category="tech")
        sm.add_entry("Business email writing tips", category="skill")
        sm.add_entry("Data analysis with Excel", category="skill")

        results = sm.search("email writing", top_k=2)
        assert len(results) > 0

    def test_namespaces(self):
        sm = SemanticMemory()
        sm.add_entry("Content A", namespace="ns1")
        sm.add_entry("Content B", namespace="ns2")

        ns = sm.get_namespaces()
        assert "ns1" in ns
        assert "ns2" in ns

    def test_user_preferences(self):
        sm = SemanticMemory()
        sm.add_user_preference("user1", "language", "ko")
        sm.add_user_preference("user1", "tone", "formal")

        prefs = sm.get_user_preferences("user1")
        assert any(p["key"] == "language" and p["value"] == "ko" for p in prefs)
        assert any(p["key"] == "tone" and p["value"] == "formal" for p in prefs)

    def test_build_context(self):
        sm = SemanticMemory()
        sm.add_entry("Email composition best practices", category="knowledge")
        sm.add_entry("Report writing guidelines", category="knowledge")

        ctx = sm.build_context("email", user_id="user1", top_k=2)
        assert isinstance(ctx, str)

    def test_entry_count(self):
        sm = SemanticMemory()
        sm.add_entry("Entry 1")
        sm.add_entry("Entry 2")
        sm.add_entry("Entry 3")
        assert sm.get_entry_count() == 3


# ═══════════════════════════════════════
# Context Bus
# ═══════════════════════════════════════

class TestContextBus:
    def test_subscribe_and_publish(self):
        bus = ContextBus()
        received = []

        def handler(msg):
            received.append(msg)

        bus.subscribe(AgentRole.EXECUTOR, handler)
        message = AgentMessage(
            from_agent=AgentRole.PLANNER,
            to_agent=AgentRole.EXECUTOR,
            payload={"task": "test"},
        )
        bus.publish(message)

        assert len(received) == 1
        assert received[0].payload["task"] == "test"

    def test_broadcast(self):
        bus = ContextBus()
        received_a = []
        received_b = []

        def handler_a(msg):
            received_a.append(msg)

        def handler_b(msg):
            received_b.append(msg)

        bus.subscribe_all(handler_a)
        bus.subscribe_all(handler_b)
        message = AgentMessage(
            from_agent=AgentRole.ORCHESTRATOR,
            to_agent=None,
            payload={"broadcast": True},
        )
        bus.publish(message)

        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_message_log(self):
        bus = ContextBus()
        log = bus.get_message_log()
        assert isinstance(log, list)


# ═══════════════════════════════════════
# Memory Manager
# ═══════════════════════════════════════

class TestMemoryManager:
    def test_session_lifecycle(self, memory: MemoryManager):
        sid = memory.start_session("user1")
        assert sid is not None

        memory.add_message(sid, "user", "Hello")
        msgs = memory.get_messages(sid)
        assert len(msgs) == 1

        memory.end_session(sid)
        # Session should be deleted from working memory
        assert memory.working.get_session(sid) is None

    def test_build_agent_context(self, memory: MemoryManager):
        sid = memory.start_session("user1")
        memory.add_message(sid, "user", "이메일 작성해줘")

        ctx = memory.build_agent_context(sid, "이메일 작성해줘", AgentRole.EXECUTOR)

        assert "session_id" in ctx
        assert "conversation" in ctx
        assert "shared_vars" in ctx
        assert "recent_history" in ctx
        assert "semantic_context" in ctx

    def test_get_stats(self, memory: MemoryManager):
        stats = memory.get_stats()
        assert "working_sessions" in stats
        assert "semantic_entries" in stats
