"""
Skill Validator - Validates skill definitions against the schema.
11 validation checks matching the design document.
"""

from __future__ import annotations

import re
from pathlib import Path

from skillforge.models import SkillDefinition, SkillValidationResult, SourceType


class SkillValidator:
    """Validate skill definitions for correctness and best practices."""

    ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
    VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
    SKILLMD_NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

    @classmethod
    def validate(cls, skill: SkillDefinition) -> SkillValidationResult:
        """Route to appropriate validation based on source_type."""
        if skill.source_type == SourceType.SKILLMD:
            return cls._validate_skillmd(skill)
        return cls._validate_legacy(skill)

    @classmethod
    def _validate_skillmd(cls, skill: SkillDefinition) -> SkillValidationResult:
        """Validate a SKILL.md-sourced skill against the Anthropic spec."""
        errors: list[str] = []
        warnings: list[str] = []
        checks_passed = 0
        checks_total = 0

        def check(condition: bool, error_msg: str, is_warning: bool = False) -> None:
            nonlocal checks_passed, checks_total
            checks_total += 1
            if condition:
                checks_passed += 1
            elif is_warning:
                warnings.append(error_msg)
                checks_passed += 1
            else:
                errors.append(error_msg)

        # 1. Name format
        name = skill.id
        check(
            bool(cls.SKILLMD_NAME_PATTERN.match(name)) and len(name) <= 64 and "--" not in name,
            f'Skill name "{name}" must be 1-64 lowercase chars/hyphens, no leading/trailing/consecutive hyphens',
        )

        # 2. Description length
        check(
            0 < len(skill.description) <= 1024,
            f"Description must be 1-1024 characters (got {len(skill.description)})",
        )

        # 3. Description quality
        check(
            len(skill.description) >= 20,
            "Description is very short; include keywords for activation",
            is_warning=True,
        )

        # 4. Instructions exist
        check(
            len(skill.instructions) > 0,
            "SKILL.md body (instructions) is empty",
        )

        # 5. Instructions size
        check(
            len(skill.instructions) < 20000,
            "Instructions exceed recommended 5000 tokens; consider using references/",
            is_warning=True,
        )

        # 6. Compatibility length
        if skill.compatibility:
            check(
                len(skill.compatibility) <= 500,
                f"Compatibility must be <= 500 characters (got {len(skill.compatibility)})",
            )
        else:
            checks_total += 1
            checks_passed += 1

        # 7. Name matches directory name
        if skill.skill_dir:
            dir_name = Path(skill.skill_dir).name
            check(
                name == dir_name,
                f'Skill name "{name}" must match directory name "{dir_name}"',
                is_warning=True,
            )
        else:
            checks_total += 1
            checks_passed += 1

        return SkillValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            checks_passed=checks_passed,
            checks_total=checks_total,
        )

    @classmethod
    def _validate_legacy(cls, skill: SkillDefinition) -> SkillValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        checks_passed = 0
        checks_total = 0

        def check(condition: bool, error_msg: str, is_warning: bool = False) -> None:
            nonlocal checks_passed, checks_total
            checks_total += 1
            if condition:
                checks_passed += 1
            elif is_warning:
                warnings.append(error_msg)
                checks_passed += 1  # warnings still count as "soft pass"
            else:
                errors.append(error_msg)

        # 1. Skill ID format
        check(
            bool(cls.ID_PATTERN.match(skill.id)),
            f'Skill ID "{skill.id}" must be lowercase letters, numbers, and hyphens only',
        )

        # 2. Display name not empty
        check(bool(skill.name.strip()), "Display name is required")

        # 3. Category valid
        check(bool(skill.category), "Category is required")

        # 4. Description length
        check(
            len(skill.description) >= 10,
            "Description should be at least 10 characters",
            is_warning=len(skill.description) > 0,
        )

        # 5. Version format
        check(
            bool(cls.VERSION_PATTERN.match(skill.version)),
            f'Version "{skill.version}" must follow semver (e.g., 1.0.0)',
        )

        # 6. Prompt template exists
        check(
            len(skill.prompt_template) >= 20,
            "Prompt template is too short (minimum 20 characters)",
        )

        # 7. At least one input defined
        check(
            len(skill.inputs) > 0,
            "No input fields defined",
            is_warning=True,
        )

        # 8. At least one output defined
        check(
            len(skill.outputs) > 0,
            "No output fields defined",
            is_warning=True,
        )

        # 9. Prompt variables match inputs
        prompt_vars = set(re.findall(r"\{\{(\w+)\}\}", skill.prompt_template))
        input_names = {f.name for f in skill.inputs}

        unmatched_vars = prompt_vars - input_names
        for var in unmatched_vars:
            check(
                False,
                f'Prompt variable "{{{{{var}}}}}" has no matching input definition',
                is_warning=True,
            )

        unused_inputs = input_names - prompt_vars
        for inp in unused_inputs:
            check(
                False,
                f'Input "{inp}" is not used in prompt template',
                is_warning=True,
            )

        # 10. Settings validation
        check(
            0 < skill.settings.max_tokens <= 16000,
            f"max_tokens ({skill.settings.max_tokens}) must be between 1 and 16000",
        )
        check(
            0.0 <= skill.settings.temperature <= 2.0,
            f"temperature ({skill.settings.temperature}) must be between 0.0 and 2.0",
        )

        # 11. No duplicate input/output names
        input_dup = len(input_names) != len(skill.inputs)
        check(not input_dup, "Duplicate input field names detected")

        output_names = [f.name for f in skill.outputs]
        output_dup = len(set(output_names)) != len(output_names)
        check(not output_dup, "Duplicate output field names detected")

        return SkillValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            checks_passed=checks_passed,
            checks_total=checks_total,
        )
