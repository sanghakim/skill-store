"""
Shared test fixtures for the SkillForge test suite.
"""

from __future__ import annotations

import pytest

from skillforge.app import SkillForgeApp
from skillforge.engine.registry import SkillRegistry
from skillforge.engine.sandbox import SkillSandbox, SimulatedLLMBackend
from skillforge.engine.validator import SkillValidator
from skillforge.memory.manager import MemoryManager
from skillforge.models import (
    FieldType,
    SkillCategory,
    SkillDefinition,
    SkillField,
    SkillSettings,
)


@pytest.fixture
def memory():
    """Create a fresh MemoryManager."""
    return MemoryManager(token_limit=128_000)


@pytest.fixture
def registry():
    """Create a fresh SkillRegistry."""
    return SkillRegistry()


@pytest.fixture
def sandbox():
    """Create a SkillSandbox with SimulatedLLMBackend."""
    return SkillSandbox(llm_backend=SimulatedLLMBackend())


@pytest.fixture
def validator():
    """Return the SkillValidator."""
    return SkillValidator()


@pytest.fixture
def sample_skill():
    """Create a sample skill for testing."""
    return SkillDefinition(
        id="test-skill",
        name="Test Skill",
        version="1.0.0",
        author="tester",
        category=SkillCategory.OTHER,
        description="A test skill for unit testing purposes",
        inputs=[
            SkillField(
                name="query",
                type=FieldType.STRING,
                required=True,
                description="Test query input",
            ),
            SkillField(
                name="mode",
                type=FieldType.ENUM,
                required=False,
                description="Operation mode",
                values=["basic", "advanced"],
                default="basic",
            ),
        ],
        outputs=[
            SkillField(
                name="result",
                type=FieldType.STRING,
                description="Test output",
            ),
        ],
        prompt_template="""You are a test assistant.

[Query]
{{query}}

[Mode]
{{mode}}

Provide a professional response to the query.""",
        settings=SkillSettings(max_tokens=1000, temperature=0.5),
        tags=["test", "demo"],
    )


@pytest.fixture
def email_skill():
    """Create an email skill for testing."""
    return SkillDefinition(
        id="email-composer",
        name="Email Composer",
        version="1.0.0",
        author="SkillForge",
        category=SkillCategory.EMAIL,
        description="Compose professional business emails",
        inputs=[
            SkillField(name="context", type=FieldType.STRING, required=True, description="Email context"),
            SkillField(name="tone", type=FieldType.ENUM, required=True, values=["formal", "friendly"], default="formal"),
        ],
        outputs=[
            SkillField(name="subject", type=FieldType.STRING, description="Subject line"),
            SkillField(name="body", type=FieldType.STRING, description="Email body"),
        ],
        prompt_template="""You are a business email expert.

[Context]
{{context}}

[Tone]
{{tone}}

Write a professional email with subject and body.""",
        settings=SkillSettings(max_tokens=1500, temperature=0.7),
        tags=["email", "business"],
    )


@pytest.fixture
def app():
    """Create a fully initialized SkillForgeApp with SimulatedLLMBackend (no real API)."""
    sf = SkillForgeApp(
        load_builtins=True,
        max_iterations=2,
        quality_threshold=0.5,
        loop_timeout_ms=30_000,
        llm_backend=SimulatedLLMBackend(),  # Always use simulated for tests
    )
    sf.initialize()
    yield sf
    sf.shutdown()
