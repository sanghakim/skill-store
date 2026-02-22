"""
Tests for the SkillForgeApp (main application class).
"""

from __future__ import annotations

import pytest

from skillforge.app import SkillForgeApp, create_app
from skillforge.models import SkillCategory


# ═══════════════════════════════════════
# Initialization
# ═══════════════════════════════════════

class TestSkillForgeAppInit:
    def test_create_and_initialize(self):
        sf = SkillForgeApp()
        sf.initialize()
        assert sf._initialized
        assert sf.memory is not None
        assert sf.registry is not None
        assert sf.sandbox is not None
        assert sf.loop is not None
        sf.shutdown()

    def test_idempotent_initialize(self):
        sf = SkillForgeApp()
        sf.initialize()
        sf.initialize()  # Should not fail
        assert sf._initialized
        sf.shutdown()

    def test_factory_function(self):
        sf = create_app(max_iterations=1, quality_threshold=0.3)
        assert sf._initialized
        assert sf.loop is not None
        sf.shutdown()

    def test_builtin_skills_loaded(self, app: SkillForgeApp):
        skills = app.registry.list_all()
        assert len(skills) == 15

        # Check specific skills exist
        assert app.registry.exists("email-composer")
        assert app.registry.exists("doc-drafter")
        assert app.registry.exists("excel-analyzer")
        assert app.registry.exists("biz-translator")
        assert app.registry.exists("deep-researcher")

    def test_no_builtins(self):
        sf = SkillForgeApp(load_builtins=False)
        sf.initialize()
        assert len(sf.registry.list_all()) == 0
        sf.shutdown()

    def test_semantic_memory_seeded(self, app: SkillForgeApp):
        # Semantic memory should have entries for all registered skills
        count = app.memory.semantic.get_entry_count()
        assert count >= 15  # At least one per builtin skill


# ═══════════════════════════════════════
# System Info
# ═══════════════════════════════════════

class TestSystemInfo:
    def test_get_system_info(self, app: SkillForgeApp):
        info = app.get_system_info()
        assert info["initialized"]
        assert info["version"] == "1.0.0"
        assert info["skills"]["total"] == 15
        assert "config" in info
        assert "memory" in info
        assert "agents" in info

    def test_system_info_before_init(self):
        sf = SkillForgeApp()
        info = sf.get_system_info()
        assert not info["initialized"]


# ═══════════════════════════════════════
# Skill Management
# ═══════════════════════════════════════

class TestSkillManagement:
    def test_validate_skill(self, app: SkillForgeApp):
        skill = app.registry.get("email-composer")
        result = app.validate_skill(skill)
        assert result.valid
        assert result.checks_passed > 0

    def test_publish_skill_dict(self, app: SkillForgeApp):
        data = {
            "id": "custom-skill",
            "name": "Custom Test Skill",
            "version": "1.0.0",
            "category": "other",
            "description": "A custom skill published via API",
            "prompt_template": "You are a custom assistant. Task: {{task}}. Please provide help.",
            "inputs": [
                {"name": "task", "type": "string", "required": True}
            ],
            "outputs": [
                {"name": "result", "type": "string"}
            ],
        }
        success, skill, validation = app.publish_skill(data)
        assert success
        assert skill is not None
        assert skill.id == "custom-skill"
        assert app.registry.exists("custom-skill")

    def test_publish_invalid_skill(self, app: SkillForgeApp):
        data = {
            "id": "INVALID ID!!!",
            "name": "Bad Skill",
            "version": "not-semver",
            "description": "Bad",
            "prompt_template": "short",
        }
        success, skill, validation = app.publish_skill(data)
        assert not success
        assert validation is not None
        assert not validation.valid

    def test_publish_skill_yaml(self, app: SkillForgeApp):
        yaml_content = """
id: yaml-published
name: YAML Published Skill
version: 1.0.0
category: document
description: A skill published from YAML content for testing
prompt_template: |
  You are a document specialist.
  Topic: {{topic}}
  Generate a professional document about the topic.
inputs:
  - name: topic
    type: string
    required: true
outputs:
  - name: document
    type: string
tags:
  - document
  - test
"""
        success, skill, validation = app.publish_skill_yaml(yaml_content)
        assert success
        assert skill.id == "yaml-published"
        assert app.registry.exists("yaml-published")


# ═══════════════════════════════════════
# Shutdown
# ═══════════════════════════════════════

class TestShutdown:
    def test_shutdown_cleans_sessions(self):
        sf = SkillForgeApp(load_builtins=False)
        sf.initialize()

        # Create some sessions
        sid1 = sf.memory.start_session("user1")
        sid2 = sf.memory.start_session("user2")
        sf.memory.add_message(sid1, "user", "Hello")

        sf.shutdown()
        assert not sf._initialized

    def test_shutdown_before_init(self):
        sf = SkillForgeApp()
        sf.shutdown()  # Should not raise
