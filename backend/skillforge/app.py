"""
SkillForge Application - Main entry point that wires all components together.
Initializes Memory, Registry, Sandbox, Agents, and the Agentic Loop.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from skillforge.engine.loader import SkillLoader
from skillforge.engine.registry import SkillRegistry
from skillforge.engine.sandbox import SkillSandbox, LLMBackend, SimulatedLLMBackend
from skillforge.engine.validator import SkillValidator
from skillforge.memory.manager import MemoryManager
from skillforge.models import SkillDefinition, SkillValidationResult
from skillforge.orchestrator.loop import AgenticLoop
from skillforge.skills.builtins.catalog import get_all_builtin_skills

# Load .env file (if present) for ANTHROPIC_API_KEY, CLAUDE_MODEL, etc.
# Search: backend dir (where .env lives) → cwd
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env", override=True)
load_dotenv(override=True)  # also try cwd

logger = logging.getLogger(__name__)


class SkillForgeApp:
    """
    The main application orchestrator for the SkillForge multi-agent system.

    Wires together:
    - MemoryManager  (3-layer memory)
    - SkillRegistry  (skill catalog)
    - SkillSandbox   (isolated execution)
    - AgenticLoop    (Plan-Execute-Review cycle)

    Usage:
        app = SkillForgeApp()
        app.initialize()
        result = await app.loop.run("이메일 작성해줘", user_id="user-1")
    """

    def __init__(
        self,
        *,
        # Memory settings
        episodic_persist_path: str | None = None,
        token_limit: int = 128_000,
        # Sandbox settings
        llm_backend: LLMBackend | None = None,
        sandbox_timeout_ms: int = 120_000,
        # Loop settings
        max_iterations: int = 3,
        quality_threshold: float = 0.75,
        loop_timeout_ms: int = 300_000,
        max_parallel: int = 5,
        # Skill settings
        load_builtins: bool = True,
        custom_skills_dir: str | None = None,
        skills_dir: str | None = None,
    ):
        self._config = {
            "episodic_persist_path": episodic_persist_path,
            "token_limit": token_limit,
            "llm_backend": llm_backend,
            "sandbox_timeout_ms": sandbox_timeout_ms,
            "max_iterations": max_iterations,
            "quality_threshold": quality_threshold,
            "loop_timeout_ms": loop_timeout_ms,
            "max_parallel": max_parallel,
            "load_builtins": load_builtins,
            "custom_skills_dir": custom_skills_dir,
            "skills_dir": skills_dir,
        }

        # Components (initialized in .initialize())
        self.memory: MemoryManager | None = None
        self.registry: SkillRegistry | None = None
        self.sandbox: SkillSandbox | None = None
        self.loop: AgenticLoop | None = None
        self.validator: SkillValidator = SkillValidator()

        self._initialized = False

    # ── Initialization ──

    def initialize(self) -> None:
        """
        Wire up all components. Must be called before using the app.
        Idempotent — calling multiple times is safe.
        """
        if self._initialized:
            logger.debug("SkillForgeApp already initialized, skipping")
            return

        logger.info("=" * 50)
        logger.info("SkillForge Initialization Starting")
        logger.info("=" * 50)

        # ── 1. Memory Manager ──
        self.memory = MemoryManager(
            episodic_persist_path=self._config["episodic_persist_path"],
            token_limit=self._config["token_limit"],
        )
        logger.info("[1/5] MemoryManager initialized")

        # ── 2. Skill Registry ──
        self.registry = SkillRegistry()
        logger.info("[2/5] SkillRegistry initialized")

        # ── 3. Skill Sandbox ──
        llm_backend = self._config["llm_backend"] or self._resolve_llm_backend()
        self.sandbox = SkillSandbox(
            llm_backend=llm_backend,
            default_timeout_ms=self._config["sandbox_timeout_ms"],
        )
        backend_name = type(llm_backend).__name__
        logger.info("[3/5] SkillSandbox initialized (backend=%s)", backend_name)

        # ── 4. Register Built-in Skills ──
        if self._config["load_builtins"]:
            self._register_builtin_skills()

        # ── 5. Load Custom Skills (YAML) ──
        if self._config["custom_skills_dir"]:
            self._load_custom_skills(self._config["custom_skills_dir"])

        # ── 5b. Load Anthropic-format Skills (SKILL.md) ──
        if self._config["skills_dir"]:
            self._load_skillmd_skills(self._config["skills_dir"])

        # ── 6. Agentic Loop ──
        self.loop = AgenticLoop(
            memory=self.memory,
            registry=self.registry,
            sandbox=self.sandbox,
            max_iterations=self._config["max_iterations"],
            quality_threshold=self._config["quality_threshold"],
            timeout_ms=self._config["loop_timeout_ms"],
            max_parallel=self._config["max_parallel"],
        )
        logger.info("[4/5] AgenticLoop initialized")

        # ── 7. Seed Semantic Memory ──
        self._seed_semantic_memory()
        logger.info("[5/5] Semantic memory seeded")

        self._initialized = True

        logger.info("=" * 50)
        logger.info(
            "SkillForge Ready! Skills=%d, Agents=%d",
            len(self.registry.list_all()),
            len(self.loop.agents),
        )
        logger.info("=" * 50)

    # ── Skill Management ──

    def validate_skill(self, skill: SkillDefinition) -> SkillValidationResult:
        """Validate a skill definition against the schema."""
        return self.validator.validate(skill)

    def publish_skill(
        self,
        skill_data: dict[str, Any],
        validate: bool = True,
    ) -> tuple[bool, SkillDefinition | None, SkillValidationResult | None]:
        """
        Parse, validate, and register a skill from a dictionary.
        Returns (success, skill, validation_result).
        """
        try:
            skill = SkillLoader.from_dict(skill_data)
        except Exception as exc:
            return (
                False,
                None,
                SkillValidationResult(
                    valid=False,
                    errors=[f"Parsing error: {exc}"],
                ),
            )

        if validate:
            result = self.validate_skill(skill)
            if not result.valid:
                return (False, skill, result)
        else:
            result = None

        self.registry.register(skill)
        logger.info("Skill published: %s v%s", skill.id, skill.version)
        return (True, skill, result)

    def publish_skill_yaml(
        self,
        yaml_content: str,
        validate: bool = True,
    ) -> tuple[bool, SkillDefinition | None, SkillValidationResult | None]:
        """
        Parse, validate, and register a skill from YAML.
        Returns (success, skill, validation_result).
        """
        try:
            skill = SkillLoader.from_yaml_string(yaml_content)
        except Exception as exc:
            return (
                False,
                None,
                SkillValidationResult(
                    valid=False,
                    errors=[f"YAML parsing error: {exc}"],
                ),
            )

        if validate:
            result = self.validate_skill(skill)
            if not result.valid:
                return (False, skill, result)
        else:
            result = None

        self.registry.register(skill)
        logger.info("Skill published from YAML: %s v%s", skill.id, skill.version)
        return (True, skill, result)

    def publish_skill_md(
        self,
        skill_dir: str,
        validate: bool = True,
    ) -> tuple[bool, SkillDefinition | None, SkillValidationResult | None]:
        """Load, validate, and register a skill from a SKILL.md directory."""
        try:
            skill = SkillLoader.from_skill_directory(skill_dir)
        except Exception as exc:
            return (
                False,
                None,
                SkillValidationResult(
                    valid=False,
                    errors=[f"SKILL.md loading error: {exc}"],
                ),
            )

        if validate:
            result = self.validate_skill(skill)
            if not result.valid:
                return (False, skill, result)
        else:
            result = None

        self.registry.register(skill)
        logger.info("SKILL.md skill published: %s", skill.id)
        return (True, skill, result)

    # ── System Info ──

    def get_system_info(self) -> dict[str, Any]:
        """Return overall system status and configuration."""
        llm_info = "unknown"
        if self.sandbox:
            backend = self.sandbox._llm
            llm_info = type(backend).__name__
            if hasattr(backend, "model"):
                llm_info += f" ({backend.model})"

        return {
            "initialized": self._initialized,
            "version": "1.0.0",
            "llm_backend": llm_info,
            "config": {
                "max_iterations": self._config["max_iterations"],
                "quality_threshold": self._config["quality_threshold"],
                "loop_timeout_ms": self._config["loop_timeout_ms"],
                "max_parallel": self._config["max_parallel"],
                "token_limit": self._config["token_limit"],
            },
            "skills": {
                "total": len(self.registry.list_all()) if self.registry else 0,
                "categories": self.registry.get_categories() if self.registry else {},
            },
            "memory": self.memory.get_stats() if self.memory else {},
            "agents": (
                [r.value for r in self.loop.agents.keys()]
                if self.loop
                else []
            ),
        }

    # ── Internal ──

    def _resolve_llm_backend(self) -> LLMBackend:
        """
        Auto-detect which LLM backend to use.
        Priority: ANTHROPIC_API_KEY env → SimulatedLLMBackend fallback.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY", "")

        if api_key:
            try:
                from skillforge.engine.claude_backend import ClaudeLLMBackend
                backend = ClaudeLLMBackend(api_key=api_key)
                logger.info(
                    "Claude LLM backend activated: model=%s",
                    backend.model,
                )
                return backend
            except Exception as exc:
                logger.warning(
                    "Failed to initialize Claude backend, falling back to simulated: %s",
                    exc,
                )
                return SimulatedLLMBackend()
        else:
            logger.info(
                "No ANTHROPIC_API_KEY found — using SimulatedLLMBackend. "
                "Set ANTHROPIC_API_KEY in .env to enable Claude API."
            )
            return SimulatedLLMBackend()

    def _register_builtin_skills(self) -> None:
        """Register all 14 built-in office productivity skills."""
        builtin_skills = get_all_builtin_skills()
        registered = 0

        for skill in builtin_skills:
            # Validate before registering
            validation = self.validate_skill(skill)
            if validation.valid:
                self.registry.register(skill)
                registered += 1
            else:
                logger.warning(
                    "Built-in skill validation failed: %s errors=%s",
                    skill.id,
                    validation.errors,
                )

        logger.info("Built-in skills registered: %d/%d", registered, len(builtin_skills))

    def _load_custom_skills(self, directory: str) -> None:
        """Load skills from a directory of YAML files."""
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning("Custom skills directory not found: %s", directory)
            return

        try:
            skills = SkillLoader.load_directory(directory)
            loaded = 0

            for skill in skills:
                validation = self.validate_skill(skill)
                if validation.valid:
                    self.registry.register(skill)
                    loaded += 1
                else:
                    logger.warning(
                        "Custom skill validation failed: %s errors=%s",
                        skill.id,
                        validation.errors,
                    )

            logger.info("Custom skills loaded: %d/%d from %s", loaded, len(skills), directory)

        except Exception as exc:
            logger.error("Failed to load custom skills from %s: %s", directory, exc)

    def _load_skillmd_skills(self, directory: str) -> None:
        """Load Anthropic-format skills from a directory of skill folders."""
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning("Skills directory not found: %s", directory)
            return

        try:
            skills = SkillLoader.load_skills_directory(directory)
            loaded = 0

            for skill in skills:
                validation = self.validate_skill(skill)
                if validation.valid:
                    self.registry.register(skill)
                    loaded += 1
                else:
                    logger.warning(
                        "SKILL.md skill validation failed: %s errors=%s warnings=%s",
                        skill.id,
                        validation.errors,
                        validation.warnings,
                    )

            logger.info(
                "Anthropic-format skills loaded: %d/%d from %s",
                loaded, len(skills), directory,
            )
        except Exception as exc:
            logger.error(
                "Failed to load skills directory %s: %s", directory, exc
            )

    def _seed_semantic_memory(self) -> None:
        """Pre-populate semantic memory with skill knowledge for RAG."""
        if not self.memory or not self.registry:
            return

        for skill in self.registry.list_all():
            # Store skill knowledge in semantic memory
            content = (
                f"Skill: {skill.name} ({skill.id})\n"
                f"Category: {skill.category.value}\n"
                f"Description: {skill.description}\n"
                f"Inputs: {', '.join(f.name for f in skill.inputs)}\n"
                f"Tags: {', '.join(skill.tags)}"
            )
            self.memory.semantic.add_entry(
                content=content,
                category="skill_knowledge",
                namespace="skills",
                metadata={
                    "skill_id": skill.id,
                    "category": skill.category.value,
                },
            )

        logger.info(
            "Semantic memory seeded with %d skill entries",
            len(self.registry.list_all()),
        )

    # ── Cleanup ──

    def shutdown(self) -> None:
        """Graceful shutdown — flush memory, save state."""
        if not self._initialized:
            return

        logger.info("SkillForge shutting down...")

        # End all active sessions
        if self.memory:
            active_sessions = self.memory.working.list_sessions()
            for session_id in active_sessions:
                try:
                    self.memory.end_session(session_id)
                except Exception:
                    pass

        # Persist episodic memory
        if self.memory and self.memory.episodic:
            self.memory.episodic._persist_to_disk()

        self._initialized = False
        logger.info("SkillForge shutdown complete")


def create_app(**kwargs) -> SkillForgeApp:
    """Factory function to create and initialize a SkillForgeApp."""
    app = SkillForgeApp(**kwargs)
    app.initialize()
    return app
