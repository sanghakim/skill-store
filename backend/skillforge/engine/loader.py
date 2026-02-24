"""
Skill Loader - Parses YAML definitions and loads skills dynamically.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from skillforge.models import (
    FieldType,
    SkillCategory,
    SkillDefinition,
    SkillField,
    SkillSettings,
)

logger = logging.getLogger(__name__)


class SkillLoader:
    """Load skill definitions from YAML strings, dicts, or files."""

    @staticmethod
    def from_yaml_string(yaml_str: str) -> SkillDefinition:
        """Parse a YAML string into a SkillDefinition."""
        raw = yaml.safe_load(yaml_str)
        return SkillLoader._parse_raw(raw)

    @staticmethod
    def from_yaml_file(path: str | Path) -> SkillDefinition:
        """Load a skill definition from a YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Skill file not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return SkillLoader._parse_raw(raw)

    @staticmethod
    def from_dict(data: dict) -> SkillDefinition:
        """Parse a dict (e.g., from JSON API) into a SkillDefinition."""
        return SkillLoader._parse_raw(data)

    @staticmethod
    def load_directory(directory: str | Path) -> list[SkillDefinition]:
        """Load all .yaml/.yml skill files from a directory."""
        directory = Path(directory)
        skills = []
        for path in sorted(directory.glob("*.y*ml")):
            try:
                skill = SkillLoader.from_yaml_file(path)
                skills.append(skill)
                logger.info("Loaded skill from file: %s -> %s", path.name, skill.id)
            except Exception as exc:
                logger.warning("Failed to load skill from %s: %s", path.name, exc)
        return skills

    @staticmethod
    def to_yaml(skill: SkillDefinition) -> str:
        """Export a SkillDefinition back to YAML format."""
        data = {
            "skill": {
                "id": skill.id,
                "name": skill.name,
                "version": skill.version,
                "author": skill.author,
                "category": skill.category.value,
                "description": skill.description,
                "icon": skill.icon,
                "inputs": [
                    {
                        "name": f.name,
                        "type": f.type.value,
                        "required": f.required,
                        "description": f.description,
                        **({"values": f.values} if f.values else {}),
                        **({"default": f.default} if f.default is not None else {}),
                    }
                    for f in skill.inputs
                ],
                "outputs": [
                    {
                        "name": f.name,
                        "type": f.type.value,
                        "description": f.description,
                    }
                    for f in skill.outputs
                ],
                "prompt_template": skill.prompt_template,
                "settings": {
                    "max_tokens": skill.settings.max_tokens,
                    "temperature": skill.settings.temperature,
                    "requires_review": skill.settings.requires_review,
                },
                "permissions": skill.permissions,
                "tags": skill.tags,
            }
        }
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # ── Internal Parser ──

    @staticmethod
    def _parse_raw(raw: dict) -> SkillDefinition:
        """Parse raw dict (from YAML or API) into a SkillDefinition."""
        # Support both {"skill": {...}} and flat format
        skill_data = raw.get("skill", raw)

        # Parse inputs
        inputs = []
        for inp in skill_data.get("inputs", []):
            inputs.append(SkillField(
                name=inp["name"],
                type=FieldType(inp.get("type", "string")),
                required=inp.get("required", False),
                description=inp.get("description", ""),
                values=inp.get("values", []),
                default=inp.get("default"),
            ))

        # Parse outputs
        outputs = []
        for out in skill_data.get("outputs", []):
            outputs.append(SkillField(
                name=out["name"],
                type=FieldType(out.get("type", "string")),
                description=out.get("description", ""),
            ))

        # Parse settings
        raw_settings = skill_data.get("settings", {})
        settings = SkillSettings(
            max_tokens=raw_settings.get("max_tokens", 2000),
            temperature=raw_settings.get("temperature", 0.7),
            model=raw_settings.get("model", "default"),
            timeout_ms=raw_settings.get("timeout_ms", 120000),
            requires_review=raw_settings.get("requires_review", True),
        )

        # Parse category safely
        cat_str = skill_data.get("category", "other")
        try:
            category = SkillCategory(cat_str)
        except ValueError:
            category = SkillCategory.OTHER

        return SkillDefinition(
            id=skill_data["id"],
            name=skill_data.get("name", skill_data["id"]),
            version=skill_data.get("version", "1.0.0"),
            author=skill_data.get("author", "unknown"),
            category=category,
            description=skill_data.get("description", ""),
            icon=skill_data.get("icon", "doc"),
            inputs=inputs,
            outputs=outputs,
            prompt_template=skill_data.get("prompt_template", ""),
            settings=settings,
            permissions=skill_data.get("permissions", []),
            tags=skill_data.get("tags", []),
        )
