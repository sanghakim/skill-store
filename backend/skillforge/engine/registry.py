"""
Skill Registry - Central catalog for all registered skills.
Handles CRUD, search, install tracking, and versioning.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from skillforge.models import SkillCategory, SkillDefinition

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Central skill catalog with search, filtering, and install tracking."""

    def __init__(self):
        self._skills: dict[str, SkillDefinition] = {}
        # user_id -> set of installed skill_ids
        self._installed: dict[str, set[str]] = defaultdict(set)

    # ── CRUD ──

    def register(self, skill: SkillDefinition) -> None:
        """Register or update a skill in the catalog."""
        skill.updated_at = datetime.utcnow()
        if skill.id not in self._skills:
            skill.created_at = datetime.utcnow()
        self._skills[skill.id] = skill
        logger.info("Skill registered: %s v%s", skill.id, skill.version)

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self._skills.get(skill_id)

    def unregister(self, skill_id: str) -> bool:
        if skill_id in self._skills:
            del self._skills[skill_id]
            logger.info("Skill unregistered: %s", skill_id)
            return True
        return False

    def exists(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def list_all(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    # ── Search & Filter ──

    def search(
        self,
        query: str | None = None,
        category: SkillCategory | None = None,
        tags: list[str] | None = None,
        author: str | None = None,
        sort_by: str = "downloads",  # downloads | rating | name | created_at
        limit: int = 50,
    ) -> list[SkillDefinition]:
        results = list(self._skills.values())

        if category:
            results = [s for s in results if s.category == category]
        if author:
            results = [s for s in results if s.author == author]
        if tags:
            tag_set = set(t.lower() for t in tags)
            results = [
                s for s in results
                if tag_set & set(t.lower() for t in s.tags)
            ]
        if query:
            q = query.lower()
            results = [
                s for s in results
                if q in s.id.lower()
                or q in s.name.lower()
                or q in s.description.lower()
                or any(q in t.lower() for t in s.tags)
            ]

        # Sort
        sort_keys = {
            "downloads": lambda s: s.downloads,
            "rating": lambda s: s.rating,
            "name": lambda s: s.name.lower(),
            "created_at": lambda s: s.created_at,
        }
        key_fn = sort_keys.get(sort_by, sort_keys["downloads"])
        reverse = sort_by != "name"
        results.sort(key=key_fn, reverse=reverse)

        return results[:limit]

    def get_by_category(self, category: SkillCategory) -> list[SkillDefinition]:
        return [s for s in self._skills.values() if s.category == category]

    def get_categories(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for skill in self._skills.values():
            counts[skill.category.value] += 1
        return dict(counts)

    # ── Install Tracking ──

    def install(self, user_id: str, skill_id: str) -> bool:
        if skill_id not in self._skills:
            return False
        self._installed[user_id].add(skill_id)
        self._skills[skill_id].downloads += 1
        logger.info("Skill installed: user=%s skill=%s", user_id, skill_id)
        return True

    def uninstall(self, user_id: str, skill_id: str) -> bool:
        if skill_id in self._installed.get(user_id, set()):
            self._installed[user_id].discard(skill_id)
            return True
        return False

    def get_installed(self, user_id: str) -> list[SkillDefinition]:
        ids = self._installed.get(user_id, set())
        return [self._skills[sid] for sid in ids if sid in self._skills]

    def is_installed(self, user_id: str, skill_id: str) -> bool:
        return skill_id in self._installed.get(user_id, set())

    # ── Stats ──

    def get_stats(self) -> dict:
        return {
            "total_skills": len(self._skills),
            "total_installs": sum(s.downloads for s in self._skills.values()),
            "categories": self.get_categories(),
            "top_skills": [
                {"id": s.id, "name": s.name, "downloads": s.downloads}
                for s in sorted(self._skills.values(), key=lambda x: x.downloads, reverse=True)[:5]
            ],
        }
