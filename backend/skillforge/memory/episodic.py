"""
Layer 2: Episodic Memory
- Persistent storage of past session summaries, task history, usage patterns
- Write once per session end, read on-demand
- In production: PostgreSQL; here: in-memory with file persistence
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from skillforge.models import EpisodicEntry

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """Stores and retrieves past session histories and task patterns."""

    def __init__(self, persist_path: str | None = None):
        # user_id -> list[EpisodicEntry]
        self._store: dict[str, list[EpisodicEntry]] = defaultdict(list)
        # user_id -> {pattern_key: count}
        self._patterns: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._persist_path = Path(persist_path) if persist_path else None

        if self._persist_path and self._persist_path.exists():
            self._load_from_disk()

    # ── Write ──

    def record_session(
        self,
        user_id: str,
        session_id: str,
        summary: str,
        skills_used: list[str] | None = None,
        outcome: str = "success",
        metadata: dict | None = None,
    ) -> EpisodicEntry:
        """Record a completed session as an episodic memory entry."""
        entry = EpisodicEntry(
            session_id=session_id,
            summary=summary,
            skills_used=skills_used or [],
            outcome=outcome,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
        self._store[user_id].append(entry)

        # Update usage patterns
        for skill in entry.skills_used:
            self._patterns[user_id][f"skill:{skill}"] += 1
        self._patterns[user_id][f"outcome:{outcome}"] += 1

        logger.info("Episodic entry recorded for user=%s session=%s", user_id, session_id)

        self._persist_to_disk()
        return entry

    # ── Read ──

    def get_user_history(
        self,
        user_id: str,
        last_n: int | None = None,
        skill_filter: str | None = None,
    ) -> list[EpisodicEntry]:
        """Retrieve past session entries for a user."""
        entries = self._store.get(user_id, [])
        if skill_filter:
            entries = [e for e in entries if skill_filter in e.skills_used]
        if last_n:
            entries = entries[-last_n:]
        return entries

    def get_recent_summaries(self, user_id: str, last_n: int = 5) -> list[str]:
        """Get recent session summaries as context strings."""
        entries = self.get_user_history(user_id, last_n=last_n)
        return [
            f"[{e.timestamp.strftime('%Y-%m-%d')}] {e.summary} (skills: {', '.join(e.skills_used)})"
            for e in entries
        ]

    def get_user_patterns(self, user_id: str) -> dict[str, int]:
        """Get frequency patterns for a user."""
        return dict(self._patterns.get(user_id, {}))

    def get_frequent_skills(self, user_id: str, top_n: int = 5) -> list[tuple[str, int]]:
        """Get the most frequently used skills for a user."""
        patterns = self._patterns.get(user_id, {})
        skill_counts = [
            (k.replace("skill:", ""), v)
            for k, v in patterns.items()
            if k.startswith("skill:")
        ]
        return sorted(skill_counts, key=lambda x: x[1], reverse=True)[:top_n]

    def search_history(self, user_id: str, query: str) -> list[EpisodicEntry]:
        """Search through session summaries."""
        entries = self._store.get(user_id, [])
        query_lower = query.lower()
        return [
            e for e in entries
            if query_lower in e.summary.lower()
            or any(query_lower in s.lower() for s in e.skills_used)
        ]

    # ── Stats ──

    def get_session_count(self, user_id: str) -> int:
        return len(self._store.get(user_id, []))

    def get_success_rate(self, user_id: str) -> float:
        entries = self._store.get(user_id, [])
        if not entries:
            return 0.0
        successes = sum(1 for e in entries if e.outcome == "success")
        return successes / len(entries)

    # ── Persistence ──

    def _persist_to_disk(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {}
            for user_id, entries in self._store.items():
                data[user_id] = [e.model_dump(mode="json") for e in entries]
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(json.dumps(data, default=str, indent=2))
        except Exception as exc:
            logger.warning("Failed to persist episodic memory: %s", exc)

    def _load_from_disk(self) -> None:
        try:
            raw = json.loads(self._persist_path.read_text())
            for user_id, entries in raw.items():
                for entry_data in entries:
                    entry = EpisodicEntry(**entry_data)
                    self._store[user_id].append(entry)
                    for skill in entry.skills_used:
                        self._patterns[user_id][f"skill:{skill}"] += 1
                    self._patterns[user_id][f"outcome:{entry.outcome}"] += 1
            logger.info("Loaded episodic memory from disk: %d users", len(self._store))
        except Exception as exc:
            logger.warning("Failed to load episodic memory: %s", exc)
