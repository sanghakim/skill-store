"""
Tests for the Skill Engine (Registry, Loader, Sandbox, Validator).
"""

from __future__ import annotations

import pytest

from skillforge.engine.loader import SkillLoader
from skillforge.engine.registry import SkillRegistry
from skillforge.engine.sandbox import SkillSandbox, SimulatedLLMBackend
from skillforge.engine.validator import SkillValidator
from skillforge.models import (
    FieldType,
    SkillCategory,
    SkillDefinition,
    SkillExecutionRequest,
    SkillField,
    SkillSettings,
)


# ═══════════════════════════════════════
# Skill Registry
# ═══════════════════════════════════════

class TestSkillRegistry:
    def test_register_and_get(self, registry: SkillRegistry, sample_skill: SkillDefinition):
        registry.register(sample_skill)
        retrieved = registry.get("test-skill")
        assert retrieved is not None
        assert retrieved.id == "test-skill"
        assert retrieved.name == "Test Skill"

    def test_exists(self, registry: SkillRegistry, sample_skill: SkillDefinition):
        assert not registry.exists("test-skill")
        registry.register(sample_skill)
        assert registry.exists("test-skill")

    def test_unregister(self, registry: SkillRegistry, sample_skill: SkillDefinition):
        registry.register(sample_skill)
        assert registry.unregister("test-skill")
        assert not registry.exists("test-skill")
        assert not registry.unregister("nonexistent")

    def test_list_all(self, registry: SkillRegistry, sample_skill: SkillDefinition, email_skill: SkillDefinition):
        registry.register(sample_skill)
        registry.register(email_skill)
        all_skills = registry.list_all()
        assert len(all_skills) == 2

    def test_search_by_query(self, registry: SkillRegistry, sample_skill: SkillDefinition, email_skill: SkillDefinition):
        registry.register(sample_skill)
        registry.register(email_skill)

        results = registry.search(query="email")
        assert len(results) == 1
        assert results[0].id == "email-composer"

    def test_search_by_category(self, registry: SkillRegistry, sample_skill: SkillDefinition, email_skill: SkillDefinition):
        registry.register(sample_skill)
        registry.register(email_skill)

        results = registry.search(category=SkillCategory.EMAIL)
        assert len(results) == 1
        assert results[0].category == SkillCategory.EMAIL

    def test_search_by_tags(self, registry: SkillRegistry, sample_skill: SkillDefinition, email_skill: SkillDefinition):
        registry.register(sample_skill)
        registry.register(email_skill)

        results = registry.search(tags=["email"])
        assert len(results) == 1

    def test_install_and_uninstall(self, registry: SkillRegistry, sample_skill: SkillDefinition):
        registry.register(sample_skill)
        assert registry.install("user1", "test-skill")
        assert registry.is_installed("user1", "test-skill")

        installed = registry.get_installed("user1")
        assert len(installed) == 1

        registry.uninstall("user1", "test-skill")
        assert not registry.is_installed("user1", "test-skill")

    def test_install_increments_downloads(self, registry: SkillRegistry, sample_skill: SkillDefinition):
        registry.register(sample_skill)
        original = registry.get("test-skill").downloads
        registry.install("user1", "test-skill")
        assert registry.get("test-skill").downloads == original + 1

    def test_get_categories(self, registry: SkillRegistry, sample_skill: SkillDefinition, email_skill: SkillDefinition):
        registry.register(sample_skill)
        registry.register(email_skill)

        cats = registry.get_categories()
        assert cats["other"] == 1
        assert cats["email"] == 1

    def test_get_stats(self, registry: SkillRegistry, sample_skill: SkillDefinition):
        registry.register(sample_skill)
        stats = registry.get_stats()
        assert stats["total_skills"] == 1


# ═══════════════════════════════════════
# Skill Loader
# ═══════════════════════════════════════

class TestSkillLoader:
    def test_from_dict(self):
        data = {
            "id": "test-loader",
            "name": "Loader Test",
            "version": "1.0.0",
            "category": "other",
            "description": "Test skill for loader",
            "prompt_template": "You are a test. Query: {{query}}",
            "inputs": [
                {"name": "query", "type": "string", "required": True}
            ],
            "outputs": [
                {"name": "result", "type": "string"}
            ],
        }
        skill = SkillLoader.from_dict(data)
        assert skill.id == "test-loader"
        assert skill.name == "Loader Test"
        assert len(skill.inputs) == 1
        assert skill.inputs[0].name == "query"

    def test_from_yaml(self):
        yaml_str = """
id: yaml-test
name: YAML Test Skill
version: 2.0.0
category: document
description: A skill loaded from YAML for testing
prompt_template: |
  You are a document writer.
  Topic: {{topic}}
  Write a professional document.
inputs:
  - name: topic
    type: string
    required: true
    description: Document topic
outputs:
  - name: document
    type: string
    description: Generated document
settings:
  max_tokens: 2000
  temperature: 0.7
tags:
  - document
  - test
"""
        skill = SkillLoader.from_yaml_string(yaml_str)
        assert skill.id == "yaml-test"
        assert skill.version == "2.0.0"
        assert skill.category == SkillCategory.DOCUMENT
        assert len(skill.inputs) == 1
        assert "{{topic}}" in skill.prompt_template

    def test_to_yaml(self, sample_skill: SkillDefinition):
        yaml_str = SkillLoader.to_yaml(sample_skill)
        assert "test-skill" in yaml_str
        assert "Test Skill" in yaml_str

    def test_roundtrip(self, sample_skill: SkillDefinition):
        """Test YAML export then re-import preserves key fields."""
        yaml_str = SkillLoader.to_yaml(sample_skill)
        reloaded = SkillLoader.from_yaml_string(yaml_str)
        assert reloaded.id == sample_skill.id
        assert reloaded.name == sample_skill.name
        assert reloaded.version == sample_skill.version
        assert len(reloaded.inputs) == len(sample_skill.inputs)


# ═══════════════════════════════════════
# Skill Sandbox
# ═══════════════════════════════════════

class TestSkillSandbox:
    def test_execute_skill(self, sandbox: SkillSandbox, sample_skill: SkillDefinition):
        request = SkillExecutionRequest(
            skill_id="test-skill",
            inputs={"query": "Write a test report", "mode": "basic"},
        )
        result = sandbox.execute(sample_skill, request)

        assert result.success
        assert result.skill_id == "test-skill"
        assert "result" in result.outputs
        assert result.tokens_used > 0
        assert result.execution_time_ms >= 0

    def test_execute_missing_required_input(self, sandbox: SkillSandbox, sample_skill: SkillDefinition):
        request = SkillExecutionRequest(
            skill_id="test-skill",
            inputs={"mode": "basic"},  # missing required 'query'
        )
        result = sandbox.execute(sample_skill, request)
        assert not result.success
        assert "query" in result.error

    def test_execute_with_extra_context(self, sandbox: SkillSandbox, sample_skill: SkillDefinition):
        request = SkillExecutionRequest(
            skill_id="test-skill",
            inputs={"query": "Test with context", "mode": "advanced"},
        )
        result = sandbox.execute(sample_skill, request, extra_context="User prefers Korean language")
        assert result.success

    def test_template_resolution(self, sandbox: SkillSandbox):
        """Test that {{variable}} placeholders are replaced."""
        skill = SkillDefinition(
            id="template-test",
            name="Template Test",
            category=SkillCategory.OTHER,
            description="Test template resolution",
            inputs=[
                SkillField(name="name", type=FieldType.STRING, required=True),
            ],
            outputs=[
                SkillField(name="result", type=FieldType.STRING),
            ],
            prompt_template="Hello {{name}}, how are you?",
        )
        request = SkillExecutionRequest(
            skill_id="template-test",
            inputs={"name": "SkillForge"},
        )
        result = sandbox.execute(skill, request)
        assert result.success
        # The resolved prompt should contain the actual name
        assert "SkillForge" in result.resolved_prompt
        assert "{{name}}" not in result.resolved_prompt

    def test_multi_output_skill(self, sandbox: SkillSandbox, email_skill: SkillDefinition):
        request = SkillExecutionRequest(
            skill_id="email-composer",
            inputs={"context": "Meeting follow-up", "tone": "formal"},
        )
        result = sandbox.execute(email_skill, request)
        assert result.success
        assert "subject" in result.outputs
        assert "body" in result.outputs


# ═══════════════════════════════════════
# Skill Validator
# ═══════════════════════════════════════

class TestSkillValidator:
    def test_valid_skill(self, validator: SkillValidator, sample_skill: SkillDefinition):
        result = validator.validate(sample_skill)
        assert result.valid
        assert result.checks_passed > 0
        assert len(result.errors) == 0

    def test_invalid_id(self, validator: SkillValidator):
        skill = SkillDefinition(
            id="Invalid ID!",
            name="Bad ID",
            description="Testing invalid ID format",
            prompt_template="This is a test prompt template for validation.",
        )
        result = validator.validate(skill)
        assert not result.valid
        assert any("ID" in e for e in result.errors)

    def test_short_prompt(self, validator: SkillValidator):
        skill = SkillDefinition(
            id="short-prompt",
            name="Short Prompt",
            description="Testing short prompt",
            prompt_template="Too short",
        )
        result = validator.validate(skill)
        assert not result.valid
        assert any("Prompt" in e for e in result.errors)

    def test_bad_version(self, validator: SkillValidator):
        skill = SkillDefinition(
            id="bad-version",
            name="Bad Version",
            version="abc",
            description="Testing bad version format",
            prompt_template="This is a sufficiently long prompt template for testing.",
        )
        result = validator.validate(skill)
        assert not result.valid
        assert any("semver" in e.lower() or "version" in e.lower() for e in result.errors)

    def test_missing_name(self, validator: SkillValidator):
        skill = SkillDefinition(
            id="no-name",
            name="",
            description="Testing missing name",
            prompt_template="This is a sufficiently long prompt template for testing.",
        )
        result = validator.validate(skill)
        assert not result.valid

    def test_unmatched_variable_warning(self, validator: SkillValidator):
        skill = SkillDefinition(
            id="unmatched-var",
            name="Unmatched Variable",
            description="Testing unmatched variable detection",
            prompt_template="Hello {{name}} and {{unknown_var}}, this is a test.",
            inputs=[
                SkillField(name="name", type=FieldType.STRING, required=True),
            ],
            outputs=[
                SkillField(name="result", type=FieldType.STRING),
            ],
        )
        result = validator.validate(skill)
        # Should still be valid (unmatched vars are warnings, not errors)
        assert result.valid
        assert any("unknown_var" in w for w in result.warnings)

    def test_settings_out_of_range(self, validator: SkillValidator):
        skill = SkillDefinition(
            id="bad-settings",
            name="Bad Settings",
            description="Testing settings validation",
            prompt_template="This is a sufficiently long prompt template for testing.",
            settings=SkillSettings(max_tokens=99999, temperature=5.0),
        )
        result = validator.validate(skill)
        assert not result.valid
