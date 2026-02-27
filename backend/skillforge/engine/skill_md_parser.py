"""
SKILL.md Parser - Parses Anthropic Agent Skills format SKILL.md files.
Extracts YAML frontmatter and markdown body content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SkillMdFrontmatter:
    """Parsed YAML frontmatter from a SKILL.md file."""
    name: str = ""
    description: str = ""
    license: str = ""
    compatibility: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    allowed_tools: list[str] = field(default_factory=list)


@dataclass
class SkillMdData:
    """Complete parsed SKILL.md data."""
    frontmatter: SkillMdFrontmatter
    instructions: str  # The markdown body
    source_path: str   # Absolute path to the SKILL.md file


# Regex for YAML frontmatter: starts with ---, content, ends with ---
_FRONTMATTER_RE = re.compile(
    r"\A\s*---\s*\n(.*?)\n---\s*\n?(.*)",
    re.DOTALL,
)


class SkillMdParser:
    """Parse SKILL.md files with YAML frontmatter + markdown body."""

    @staticmethod
    def parse_file(path: str | Path) -> SkillMdData:
        """Parse a SKILL.md file from disk."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"SKILL.md not found: {path}")
        content = path.read_text(encoding="utf-8")
        return SkillMdParser.parse_string(content, source_path=str(path))

    @staticmethod
    def parse_string(content: str, source_path: str = "") -> SkillMdData:
        """Parse SKILL.md content from a string."""
        match = _FRONTMATTER_RE.match(content)
        if not match:
            raise ValueError(
                "SKILL.md must start with YAML frontmatter delimited by ---"
            )

        yaml_str = match.group(1)
        body = match.group(2).strip()

        raw = yaml.safe_load(yaml_str)
        if not isinstance(raw, dict):
            raise ValueError("SKILL.md frontmatter must be a YAML mapping")

        frontmatter = SkillMdParser._parse_frontmatter(raw)
        return SkillMdData(
            frontmatter=frontmatter,
            instructions=body,
            source_path=source_path,
        )

    @staticmethod
    def _parse_frontmatter(raw: dict) -> SkillMdFrontmatter:
        """Parse and validate frontmatter fields."""
        # Parse allowed-tools: space-delimited string -> list
        allowed_tools_raw = raw.get("allowed-tools", "")
        if isinstance(allowed_tools_raw, str):
            allowed_tools = allowed_tools_raw.split() if allowed_tools_raw else []
        elif isinstance(allowed_tools_raw, list):
            allowed_tools = allowed_tools_raw
        else:
            allowed_tools = []

        # Parse metadata: must be dict[str, str]
        metadata_raw = raw.get("metadata", {})
        metadata = {}
        if isinstance(metadata_raw, dict):
            metadata = {str(k): str(v) for k, v in metadata_raw.items()}

        return SkillMdFrontmatter(
            name=str(raw.get("name", "")),
            description=str(raw.get("description", "")),
            license=str(raw.get("license", "")),
            compatibility=str(raw.get("compatibility", "")),
            metadata=metadata,
            allowed_tools=allowed_tools,
        )
