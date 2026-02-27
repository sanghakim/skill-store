"""
Tests for Anthropic Agent Skills (SKILL.md) format support.
Covers: parser, loader, validator, progressive disclosure, sandbox, planner activation.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from skillforge.engine.loader import SkillLoader
from skillforge.engine.registry import SkillRegistry
from skillforge.engine.sandbox import SkillSandbox, SimulatedLLMBackend
from skillforge.engine.skill_md_parser import SkillMdParser, SkillMdData, SkillMdFrontmatter
from skillforge.engine.validator import SkillValidator
from skillforge.models import (
    SkillCategory,
    SkillDefinition,
    SkillExecutionRequest,
    SkillSettings,
    SourceType,
)

# ── Path to example skills ──

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def skillmd_content():
    """Minimal valid SKILL.md content."""
    return textwrap.dedent("""\
        ---
        name: test-skill
        description: A test skill for unit tests with enough description text
        license: MIT
        compatibility: ">=0.1.0"
        allowed-tools: Read Edit
        metadata:
          version: "2.0.0"
          author: tester
        ---

        # Test Skill

        You are a test assistant. Follow user instructions.
    """)


@pytest.fixture
def skillmd_dir(tmp_path):
    """Create a temporary skill directory with SKILL.md, scripts/, references/."""
    skill_dir = tmp_path / "my-test-skill"
    skill_dir.mkdir()

    # SKILL.md
    (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: my-test-skill
        description: A comprehensive test skill for directory loading with scripts and references
        license: Apache-2.0
        compatibility: ">=0.1.0"
        allowed-tools: Read Edit Bash
        metadata:
          version: "1.2.3"
          author: test-author
          category: data
        ---

        # My Test Skill

        You are a helpful assistant. Process data as instructed.

        ## Steps
        1. Read the input
        2. Process with scripts/process.py
        3. Return formatted output
    """), encoding="utf-8")

    # scripts/
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "process.py").write_text("print('hello')\n", encoding="utf-8")
    (scripts_dir / "utils.sh").write_text("echo 'util'\n", encoding="utf-8")

    # references/
    refs_dir = skill_dir / "references"
    refs_dir.mkdir()
    (refs_dir / "GUIDE.md").write_text("# Guide\nSome reference content.\n", encoding="utf-8")

    return skill_dir


@pytest.fixture
def multi_skill_dir(tmp_path):
    """Create a base directory with multiple skill folders."""
    base = tmp_path / "skills"
    base.mkdir()

    # Skill A
    a = base / "skill-alpha"
    a.mkdir()
    (a / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: skill-alpha
        description: Alpha skill for testing multi-directory loading
        ---

        You are Alpha. Help with alpha tasks.
    """), encoding="utf-8")

    # Skill B
    b = base / "skill-beta"
    b.mkdir()
    (b / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: skill-beta
        description: Beta skill for testing multi-directory loading
        ---

        You are Beta. Help with beta tasks.
    """), encoding="utf-8")

    # Non-skill directory (no SKILL.md)
    c = base / "not-a-skill"
    c.mkdir()
    (c / "README.md").write_text("This is not a skill.", encoding="utf-8")

    return base


# ═══════════════════════════════════════════
# Parser Tests
# ═══════════════════════════════════════════

class TestSkillMdParser:
    """Tests for the SKILL.md file parser."""

    def test_parse_string_basic(self, skillmd_content):
        data = SkillMdParser.parse_string(skillmd_content)
        assert isinstance(data, SkillMdData)
        assert data.frontmatter.name == "test-skill"
        assert "test skill" in data.frontmatter.description.lower()
        assert data.frontmatter.license == "MIT"
        assert data.frontmatter.compatibility == ">=0.1.0"
        assert "# Test Skill" in data.instructions
        assert "test assistant" in data.instructions

    def test_parse_allowed_tools_string(self, skillmd_content):
        data = SkillMdParser.parse_string(skillmd_content)
        assert data.frontmatter.allowed_tools == ["Read", "Edit"]

    def test_parse_allowed_tools_list(self):
        content = textwrap.dedent("""\
            ---
            name: list-tools
            description: Test with list-format allowed-tools
            allowed-tools:
              - Read
              - Edit
              - Bash
            ---

            Instructions here.
        """)
        data = SkillMdParser.parse_string(content)
        assert data.frontmatter.allowed_tools == ["Read", "Edit", "Bash"]

    def test_parse_metadata(self, skillmd_content):
        data = SkillMdParser.parse_string(skillmd_content)
        assert data.frontmatter.metadata["version"] == "2.0.0"
        assert data.frontmatter.metadata["author"] == "tester"

    def test_parse_metadata_values_coerced_to_string(self):
        content = textwrap.dedent("""\
            ---
            name: coerce-test
            description: Test metadata value coercion
            metadata:
              count: 42
              flag: true
            ---

            Body.
        """)
        data = SkillMdParser.parse_string(content)
        assert data.frontmatter.metadata["count"] == "42"
        assert data.frontmatter.metadata["flag"] == "True"

    def test_parse_no_frontmatter_raises(self):
        with pytest.raises(ValueError, match="YAML frontmatter"):
            SkillMdParser.parse_string("Just some markdown\nNo frontmatter.")

    def test_parse_invalid_frontmatter_raises(self):
        with pytest.raises(ValueError, match="YAML mapping"):
            SkillMdParser.parse_string("---\njust a string\n---\nBody.")

    def test_parse_empty_body(self):
        content = textwrap.dedent("""\
            ---
            name: empty-body
            description: Skill with empty body
            ---
        """)
        data = SkillMdParser.parse_string(content)
        assert data.instructions == ""

    def test_parse_file(self, skillmd_dir):
        skill_md_path = skillmd_dir / "SKILL.md"
        data = SkillMdParser.parse_file(skill_md_path)
        assert data.frontmatter.name == "my-test-skill"
        assert data.source_path == str(skill_md_path)

    def test_parse_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            SkillMdParser.parse_file("/nonexistent/SKILL.md")

    def test_parse_missing_optional_fields(self):
        content = textwrap.dedent("""\
            ---
            name: minimal
            description: A minimal skill with only required fields
            ---

            Minimal instructions.
        """)
        data = SkillMdParser.parse_string(content)
        assert data.frontmatter.license == ""
        assert data.frontmatter.compatibility == ""
        assert data.frontmatter.allowed_tools == []
        assert data.frontmatter.metadata == {}


# ═══════════════════════════════════════════
# Loader Tests
# ═══════════════════════════════════════════

class TestSkillMdLoader:
    """Tests for loading SKILL.md files into SkillDefinition."""

    def test_from_skill_md(self, skillmd_dir):
        skill = SkillLoader.from_skill_md(skillmd_dir / "SKILL.md")
        assert isinstance(skill, SkillDefinition)
        assert skill.id == "my-test-skill"
        assert skill.source_type == SourceType.SKILLMD
        assert skill.version == "1.2.3"
        assert skill.author == "test-author"
        assert skill.license_text == "Apache-2.0"
        assert "Read" in skill.allowed_tools
        assert skill.instructions != ""
        # prompt_template should be set to instructions for backward compat
        assert skill.prompt_template == skill.instructions

    def test_from_skill_directory(self, skillmd_dir):
        skill = SkillLoader.from_skill_directory(skillmd_dir)
        assert skill.id == "my-test-skill"
        assert skill.skill_dir == str(skillmd_dir)
        # Should discover scripts
        assert len(skill.scripts) == 2
        script_names = [Path(s).name for s in skill.scripts]
        assert "process.py" in script_names
        assert "utils.sh" in script_names
        # Should discover references
        assert len(skill.references) == 1
        assert "GUIDE.md" in skill.references[0]

    def test_from_skill_directory_no_skillmd(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="No SKILL.md"):
            SkillLoader.from_skill_directory(empty_dir)

    def test_load_skills_directory(self, multi_skill_dir):
        skills = SkillLoader.load_skills_directory(multi_skill_dir)
        assert len(skills) == 2
        ids = {s.id for s in skills}
        assert "skill-alpha" in ids
        assert "skill-beta" in ids

    def test_load_skills_directory_nonexistent(self, tmp_path):
        skills = SkillLoader.load_skills_directory(tmp_path / "nope")
        assert skills == []

    def test_load_skills_directory_skips_non_skill_dirs(self, multi_skill_dir):
        # "not-a-skill" has no SKILL.md, should be skipped
        skills = SkillLoader.load_skills_directory(multi_skill_dir)
        ids = {s.id for s in skills}
        assert "not-a-skill" not in ids

    def test_category_defaults_to_other(self, skillmd_dir):
        skill = SkillLoader.from_skill_md(skillmd_dir / "SKILL.md")
        assert skill.category == SkillCategory.OTHER

    def test_default_version_and_author(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            name: no-meta
            description: Skill without metadata for version/author
            ---

            Instructions.
        """)
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(content, encoding="utf-8")
        skill = SkillLoader.from_skill_md(str(skill_file))
        assert skill.version == "1.0.0"
        assert skill.author == "unknown"


# ═══════════════════════════════════════════
# Validator Tests
# ═══════════════════════════════════════════

class TestSkillMdValidator:
    """Tests for SKILL.md validation rules."""

    def _make_skillmd(self, **overrides) -> SkillDefinition:
        """Helper to create a SKILL.md-sourced SkillDefinition."""
        defaults = {
            "id": "valid-skill",
            "name": "valid-skill",
            "version": "1.0.0",
            "author": "tester",
            "category": SkillCategory.OTHER,
            "description": "A valid skill description for testing purposes",
            "instructions": "You are a helpful assistant. Follow user instructions carefully.",
            "prompt_template": "You are a helpful assistant.",
            "source_type": SourceType.SKILLMD,
            "settings": SkillSettings(),
        }
        defaults.update(overrides)
        return SkillDefinition(**defaults)

    def test_valid_skill_passes(self):
        skill = self._make_skillmd()
        result = SkillValidator.validate(skill)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_invalid_name_uppercase(self):
        skill = self._make_skillmd(id="InvalidName", name="InvalidName")
        result = SkillValidator.validate(skill)
        assert result.valid is False
        assert any("name" in e.lower() for e in result.errors)

    def test_invalid_name_consecutive_hyphens(self):
        skill = self._make_skillmd(id="bad--name", name="bad--name")
        result = SkillValidator.validate(skill)
        assert result.valid is False

    def test_invalid_name_too_long(self):
        long_name = "a" * 65
        skill = self._make_skillmd(id=long_name, name=long_name)
        result = SkillValidator.validate(skill)
        assert result.valid is False

    def test_empty_description_fails(self):
        skill = self._make_skillmd(description="")
        result = SkillValidator.validate(skill)
        assert result.valid is False
        assert any("description" in e.lower() for e in result.errors)

    def test_description_too_long_fails(self):
        skill = self._make_skillmd(description="x" * 1025)
        result = SkillValidator.validate(skill)
        assert result.valid is False

    def test_short_description_warning(self):
        skill = self._make_skillmd(description="Short desc")
        result = SkillValidator.validate(skill)
        # Still valid but has warnings
        assert result.valid is True
        assert any("short" in w.lower() for w in result.warnings)

    def test_empty_instructions_fails(self):
        skill = self._make_skillmd(instructions="")
        result = SkillValidator.validate(skill)
        assert result.valid is False
        assert any("instructions" in e.lower() or "empty" in e.lower() for e in result.errors)

    def test_long_instructions_warning(self):
        skill = self._make_skillmd(instructions="x" * 20001)
        result = SkillValidator.validate(skill)
        # Still valid but has a warning about size
        assert result.valid is True
        assert any("instructions" in w.lower() or "token" in w.lower() for w in result.warnings)

    def test_name_directory_mismatch_warning(self):
        skill = self._make_skillmd(
            id="my-skill",
            name="my-skill",
            skill_dir="/path/to/different-name",
        )
        result = SkillValidator.validate(skill)
        assert result.valid is True
        assert any("match" in w.lower() and "directory" in w.lower() for w in result.warnings)

    def test_name_directory_match_no_warning(self):
        skill = self._make_skillmd(
            id="my-skill",
            name="my-skill",
            skill_dir="/path/to/my-skill",
        )
        result = SkillValidator.validate(skill)
        assert result.valid is True
        assert not any("directory" in w.lower() for w in result.warnings)

    def test_legacy_skill_uses_legacy_validator(self):
        """Ensure BUILTIN/YAML skills still go through legacy validation."""
        skill = SkillDefinition(
            id="legacy-skill",
            name="Legacy Skill",
            version="1.0.0",
            author="tester",
            category=SkillCategory.OTHER,
            description="A legacy skill for testing",
            prompt_template="You are a legacy assistant.\n\n{{query}}",
            source_type=SourceType.BUILTIN,
            inputs=[],
            outputs=[],
        )
        result = SkillValidator.validate(skill)
        # Legacy validation checks prompt template length (>=20), version format, etc.
        assert result.checks_total >= 8  # Legacy has 11 checks


# ═══════════════════════════════════════════
# Progressive Disclosure Tests
# ═══════════════════════════════════════════

class TestProgressiveDisclosure:
    """Tests for the 3-tier progressive loading in SkillRegistry."""

    def _register_skillmd(self, registry: SkillRegistry) -> SkillDefinition:
        skill = SkillDefinition(
            id="progressive-skill",
            name="progressive-skill",
            version="1.0.0",
            author="tester",
            category=SkillCategory.OTHER,
            description="A skill for progressive disclosure testing",
            instructions="Detailed instructions for the skill that are much longer.",
            prompt_template="Same as instructions.",
            source_type=SourceType.SKILLMD,
            skill_dir="/path/to/progressive-skill",
            scripts=["scripts/run.py"],
            references=["references/GUIDE.md"],
        )
        registry.register(skill)
        return skill

    def test_get_metadata(self, registry):
        self._register_skillmd(registry)
        meta = registry.get_metadata("progressive-skill")
        assert meta is not None
        assert meta["id"] == "progressive-skill"
        assert "description" in meta
        assert meta["source_type"] == "skillmd"
        # Metadata should NOT include instructions (that's tier 2)
        assert "instructions" not in meta

    def test_get_instructions(self, registry):
        self._register_skillmd(registry)
        instructions = registry.get_instructions("progressive-skill")
        assert instructions is not None
        assert "Detailed instructions" in instructions

    def test_get_scripts(self, registry):
        self._register_skillmd(registry)
        scripts = registry.get_scripts("progressive-skill")
        assert len(scripts) == 1
        assert "run.py" in scripts[0]

    def test_get_references(self, registry):
        self._register_skillmd(registry)
        refs = registry.get_references("progressive-skill")
        assert len(refs) == 1
        assert "GUIDE.md" in refs[0]

    def test_get_all_metadata(self, registry):
        self._register_skillmd(registry)
        all_meta = registry.get_all_metadata()
        assert len(all_meta) == 1
        assert all_meta[0]["id"] == "progressive-skill"

    def test_nonexistent_skill_returns_none_or_empty(self, registry):
        assert registry.get_metadata("nonexistent") is None
        assert registry.get_instructions("nonexistent") is None
        assert registry.get_scripts("nonexistent") == []
        assert registry.get_references("nonexistent") == []


# ═══════════════════════════════════════════
# Sandbox Execution Tests
# ═══════════════════════════════════════════

class TestSkillMdSandbox:
    """Tests for executing SKILL.md skills in the sandbox."""

    def _make_skillmd_skill(self) -> SkillDefinition:
        return SkillDefinition(
            id="sandbox-test",
            name="sandbox-test",
            version="1.0.0",
            author="tester",
            category=SkillCategory.OTHER,
            description="Sandbox execution test skill",
            instructions="You are a professional email writer.\n\nWrite a formal email.",
            prompt_template="You are a professional email writer.\n\nWrite a formal email.",
            source_type=SourceType.SKILLMD,
            skill_dir="/path/to/sandbox-test",
            scripts=["scripts/format.py"],
        )

    def test_execute_skillmd_skill(self, sandbox):
        skill = self._make_skillmd_skill()
        request = SkillExecutionRequest(
            skill_id="sandbox-test",
            inputs={"user_input": "이메일 작성해줘"},
        )
        result = sandbox.execute(skill, request)
        assert result.success is True
        assert result.skill_id == "sandbox-test"
        assert result.execution_time_ms >= 0
        assert result.tokens_used > 0
        # Resolved prompt should include instructions
        assert "email writer" in result.resolved_prompt.lower()

    def test_execute_skillmd_includes_scripts_in_prompt(self, sandbox):
        skill = self._make_skillmd_skill()
        request = SkillExecutionRequest(
            skill_id="sandbox-test",
            inputs={"user_input": "process this data"},
        )
        result = sandbox.execute(skill, request)
        assert result.success is True
        # The prompt should mention available scripts
        assert "scripts/format.py" in result.resolved_prompt

    def test_execute_skillmd_with_extra_context(self, sandbox):
        skill = self._make_skillmd_skill()
        request = SkillExecutionRequest(
            skill_id="sandbox-test",
            inputs={"user_input": "이메일 작성"},
        )
        result = sandbox.execute(skill, request, extra_context="User prefers formal Korean.")
        assert result.success is True
        assert "User prefers formal Korean" in result.resolved_prompt

    def test_execute_skillmd_no_input_validation(self, sandbox):
        """SKILL.md skills have no defined inputs, so validation should be skipped."""
        skill = self._make_skillmd_skill()
        # Pass any inputs - should not fail validation
        request = SkillExecutionRequest(
            skill_id="sandbox-test",
            inputs={"arbitrary_key": "arbitrary_value"},
        )
        result = sandbox.execute(skill, request)
        assert result.success is True


# ═══════════════════════════════════════════
# Backward Compatibility Tests
# ═══════════════════════════════════════════

class TestBackwardCompatibility:
    """Ensure existing BUILTIN/YAML skills are not affected by SKILL.md changes."""

    def test_builtin_skill_default_source_type(self, sample_skill):
        assert sample_skill.source_type == SourceType.BUILTIN

    def test_builtin_skill_validation(self, sample_skill, validator):
        result = validator.validate(sample_skill)
        assert result.valid is True

    def test_builtin_skill_execution(self, sample_skill, sandbox):
        request = SkillExecutionRequest(
            skill_id="test-skill",
            inputs={"query": "test query", "mode": "basic"},
        )
        result = sandbox.execute(sample_skill, request)
        assert result.success is True

    def test_builtin_skill_has_empty_skillmd_fields(self, sample_skill):
        assert sample_skill.instructions == ""
        assert sample_skill.scripts == []
        assert sample_skill.references == []
        assert sample_skill.skill_dir is None
        assert sample_skill.license_text == ""

    def test_registry_works_with_both_types(self, registry, sample_skill):
        # Register a builtin skill
        registry.register(sample_skill)

        # Register a SKILL.md skill
        skillmd = SkillDefinition(
            id="md-skill",
            name="md-skill",
            version="1.0.0",
            author="tester",
            category=SkillCategory.OTHER,
            description="A SKILL.md skill",
            instructions="Instructions here.",
            prompt_template="Instructions here.",
            source_type=SourceType.SKILLMD,
        )
        registry.register(skillmd)

        assert registry.exists("test-skill")
        assert registry.exists("md-skill")
        assert len(registry.list_all()) == 2

        # Metadata should include source_type
        meta = registry.get_metadata("md-skill")
        assert meta["source_type"] == "skillmd"
        meta_builtin = registry.get_metadata("test-skill")
        assert meta_builtin["source_type"] == "builtin"


# ═══════════════════════════════════════════
# Integration Tests with Example Skills
# ═══════════════════════════════════════════

class TestExampleSkills:
    """Integration tests using the actual example skills in skills/ directory."""

    @pytest.mark.skipif(
        not (SKILLS_DIR / "email-composer" / "SKILL.md").exists(),
        reason="Example skills not found",
    )
    def test_load_email_composer(self):
        skill = SkillLoader.from_skill_directory(SKILLS_DIR / "email-composer")
        assert skill.id == "email-composer"
        assert skill.source_type == SourceType.SKILLMD
        assert "email" in skill.description.lower()
        result = SkillValidator.validate(skill)
        assert result.valid is True

    @pytest.mark.skipif(
        not (SKILLS_DIR / "doc-drafter" / "SKILL.md").exists(),
        reason="Example skills not found",
    )
    def test_load_doc_drafter(self):
        skill = SkillLoader.from_skill_directory(SKILLS_DIR / "doc-drafter")
        assert skill.id == "doc-drafter"
        assert skill.source_type == SourceType.SKILLMD
        assert len(skill.references) >= 1
        assert any("TEMPLATES.md" in r for r in skill.references)
        result = SkillValidator.validate(skill)
        assert result.valid is True

    @pytest.mark.skipif(
        not (SKILLS_DIR / "data-analyzer" / "SKILL.md").exists(),
        reason="Example skills not found",
    )
    def test_load_data_analyzer(self):
        skill = SkillLoader.from_skill_directory(SKILLS_DIR / "data-analyzer")
        assert skill.id == "data-analyzer"
        assert skill.source_type == SourceType.SKILLMD
        assert len(skill.scripts) >= 1
        assert any("format_table.py" in s for s in skill.scripts)
        result = SkillValidator.validate(skill)
        assert result.valid is True

    @pytest.mark.skipif(
        not SKILLS_DIR.exists(),
        reason="Skills directory not found",
    )
    def test_load_all_example_skills(self):
        skills = SkillLoader.load_skills_directory(SKILLS_DIR)
        assert len(skills) >= 3
        ids = {s.id for s in skills}
        assert "email-composer" in ids
        assert "doc-drafter" in ids
        assert "data-analyzer" in ids

    @pytest.mark.skipif(
        not (SKILLS_DIR / "email-composer" / "SKILL.md").exists(),
        reason="Example skills not found",
    )
    def test_execute_example_skill(self):
        skill = SkillLoader.from_skill_directory(SKILLS_DIR / "email-composer")
        sandbox = SkillSandbox(llm_backend=SimulatedLLMBackend())
        request = SkillExecutionRequest(
            skill_id="email-composer",
            inputs={"user_input": "거래처에 미팅 요청 이메일 작성해줘"},
        )
        result = sandbox.execute(skill, request)
        assert result.success is True
        assert result.tokens_used > 0


# ═══════════════════════════════════════════
# App Integration Tests
# ═══════════════════════════════════════════

class TestAppSkillMdIntegration:
    """Test SkillForgeApp with skills_dir loading."""

    def test_app_with_skills_dir(self):
        from skillforge.app import SkillForgeApp

        if not SKILLS_DIR.exists():
            pytest.skip("Skills directory not found")

        app = SkillForgeApp(
            load_builtins=True,
            skills_dir=str(SKILLS_DIR),
            llm_backend=SimulatedLLMBackend(),
            max_iterations=1,
            quality_threshold=0.3,
        )
        app.initialize()

        try:
            # Should have builtins + SKILL.md skills
            all_skills = app.registry.list_all()
            ids = {s.id for s in all_skills}
            assert "email-composer" in ids
            assert "doc-drafter" in ids
            assert "data-analyzer" in ids

            # System info should reflect the loaded skills
            info = app.get_system_info()
            assert info["skills"]["total"] >= 3
        finally:
            app.shutdown()

    def test_publish_skill_md(self):
        from skillforge.app import SkillForgeApp

        email_dir = SKILLS_DIR / "email-composer"
        if not email_dir.exists():
            pytest.skip("Example skills not found")

        app = SkillForgeApp(
            load_builtins=False,
            llm_backend=SimulatedLLMBackend(),
        )
        app.initialize()

        try:
            success, skill, result = app.publish_skill_md(str(email_dir))
            assert success is True
            assert skill is not None
            assert skill.id == "email-composer"
            assert app.registry.exists("email-composer")
        finally:
            app.shutdown()

    def test_publish_skill_md_invalid_dir(self):
        from skillforge.app import SkillForgeApp

        app = SkillForgeApp(
            load_builtins=False,
            llm_backend=SimulatedLLMBackend(),
        )
        app.initialize()

        try:
            success, skill, result = app.publish_skill_md("/nonexistent/dir")
            assert success is False
            assert result is not None
            assert len(result.errors) > 0
        finally:
            app.shutdown()
