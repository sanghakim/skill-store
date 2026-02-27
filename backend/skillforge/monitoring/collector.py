"""
MetricsCollector - Centralized metrics collection for SkillForge.

Collects:
- Request counts (total, success, error) with time-series
- Response latency histograms
- Agent execution stats (count, avg_time per agent)
- Skill usage stats (count, avg_tokens per skill)
- Session counts
- Quality score distribution
- Recent error log
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimeSeriesBucket:
    """One-minute bucket of aggregated metrics."""
    timestamp: float  # start of the minute (epoch)
    requests: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0


@dataclass
class ErrorEntry:
    """A single error record."""
    timestamp: float
    code: str
    message: str
    session_id: str = ""
    skill_id: str = ""


class MetricsCollector:
    """
    Thread-safe singleton for collecting system metrics.

    Usage:
        mc = MetricsCollector()
        mc.record_request(latency_ms=1200, success=True, tokens=800)
        mc.record_agent_execution("planner", latency_ms=400)
        mc.record_skill_usage("email-composer", tokens=800)
        metrics = mc.get_metrics()
    """

    _instance: MetricsCollector | None = None
    _lock = threading.Lock()

    def __new__(cls) -> MetricsCollector:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._data_lock = threading.Lock()

        # ── Counters ──
        self.total_requests: int = 0
        self.success_count: int = 0
        self.error_count: int = 0
        self.total_tokens: int = 0
        self.total_latency_ms: float = 0.0

        # ── Agent stats: agent_name → {count, total_time_ms} ──
        self.agent_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_time_ms": 0.0}
        )

        # ── Skill stats: skill_id → {count, total_tokens, total_time_ms} ──
        self.skill_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_tokens": 0, "total_time_ms": 0.0}
        )

        # ── Quality score histogram buckets ──
        # Buckets: [0-0.1), [0.1-0.2), ... [0.9-1.0]
        self.quality_histogram: list[int] = [0] * 10

        # ── Iteration stats ──
        self.iteration_counts: dict[int, int] = defaultdict(int)  # iterations → count

        # ── Time-series (1-minute buckets, keep 60 = 1 hour) ──
        self.time_series: list[TimeSeriesBucket] = []
        self._max_buckets: int = 60

        # ── Error log (keep last 100) ──
        self.errors: list[ErrorEntry] = []
        self._max_errors: int = 100

        # ── Start time ──
        self.started_at: float = time.time()

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._data_lock:
            self.total_requests = 0
            self.success_count = 0
            self.error_count = 0
            self.total_tokens = 0
            self.total_latency_ms = 0.0
            self.agent_stats.clear()
            self.skill_stats.clear()
            self.quality_histogram = [0] * 10
            self.iteration_counts.clear()
            self.time_series.clear()
            self.errors.clear()
            self.started_at = time.time()

    # ── Recording methods ──

    def record_request(
        self,
        latency_ms: float,
        success: bool,
        tokens: int = 0,
        iterations: int = 1,
    ) -> None:
        """Record a completed request."""
        with self._data_lock:
            self.total_requests += 1
            self.total_latency_ms += latency_ms
            self.total_tokens += tokens
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
            self.iteration_counts[iterations] += 1
            self._update_timeseries(success, latency_ms, tokens)

    def record_agent_execution(self, agent: str, latency_ms: float) -> None:
        """Record an agent execution."""
        with self._data_lock:
            stats = self.agent_stats[agent]
            stats["count"] += 1
            stats["total_time_ms"] += latency_ms

    def record_skill_usage(
        self, skill_id: str, tokens: int = 0, latency_ms: float = 0.0
    ) -> None:
        """Record a skill execution."""
        with self._data_lock:
            stats = self.skill_stats[skill_id]
            stats["count"] += 1
            stats["total_tokens"] += tokens
            stats["total_time_ms"] += latency_ms

    def record_quality_score(self, score: float) -> None:
        """Record a quality review score."""
        with self._data_lock:
            bucket = min(int(score * 10), 9)
            self.quality_histogram[bucket] += 1

    def record_error(
        self,
        code: str,
        message: str,
        session_id: str = "",
        skill_id: str = "",
    ) -> None:
        """Record an error."""
        with self._data_lock:
            entry = ErrorEntry(
                timestamp=time.time(),
                code=code,
                message=message[:500],
                session_id=session_id,
                skill_id=skill_id,
            )
            self.errors.append(entry)
            if len(self.errors) > self._max_errors:
                self.errors = self.errors[-self._max_errors:]

    # ── Timeseries ──

    def _current_minute(self) -> float:
        """Return the start of the current minute as epoch."""
        now = time.time()
        return now - (now % 60)

    def _update_timeseries(
        self, success: bool, latency_ms: float, tokens: int
    ) -> None:
        """Add data to the current timeseries bucket (must hold _data_lock)."""
        minute = self._current_minute()

        if self.time_series and self.time_series[-1].timestamp == minute:
            bucket = self.time_series[-1]
        else:
            bucket = TimeSeriesBucket(timestamp=minute)
            self.time_series.append(bucket)
            if len(self.time_series) > self._max_buckets:
                self.time_series = self.time_series[-self._max_buckets:]

        bucket.requests += 1
        if not success:
            bucket.errors += 1
        bucket.total_latency_ms += latency_ms
        bucket.total_tokens += tokens

    # ── Query methods ──

    def get_metrics(self) -> dict[str, Any]:
        """Return all metrics as a dictionary."""
        with self._data_lock:
            uptime = time.time() - self.started_at
            avg_latency = (
                self.total_latency_ms / self.total_requests
                if self.total_requests > 0
                else 0
            )
            success_rate = (
                self.success_count / self.total_requests * 100
                if self.total_requests > 0
                else 0
            )

            return {
                "uptime_seconds": round(uptime, 1),
                "requests": {
                    "total": self.total_requests,
                    "success": self.success_count,
                    "error": self.error_count,
                    "success_rate": round(success_rate, 1),
                },
                "latency": {
                    "avg_ms": round(avg_latency, 1),
                    "total_ms": round(self.total_latency_ms, 1),
                },
                "tokens": {
                    "total": self.total_tokens,
                    "avg_per_request": (
                        round(self.total_tokens / self.total_requests)
                        if self.total_requests > 0
                        else 0
                    ),
                },
                "iterations": dict(self.iteration_counts),
            }

    def get_agent_stats(self) -> dict[str, Any]:
        """Return per-agent statistics."""
        with self._data_lock:
            result = {}
            for agent, stats in self.agent_stats.items():
                count = stats["count"]
                result[agent] = {
                    "count": count,
                    "total_time_ms": round(stats["total_time_ms"], 1),
                    "avg_time_ms": (
                        round(stats["total_time_ms"] / count, 1)
                        if count > 0
                        else 0
                    ),
                }
            return result

    def get_skill_stats(self) -> dict[str, Any]:
        """Return per-skill statistics."""
        with self._data_lock:
            result = {}
            for skill, stats in self.skill_stats.items():
                count = stats["count"]
                result[skill] = {
                    "count": count,
                    "total_tokens": stats["total_tokens"],
                    "avg_tokens": (
                        round(stats["total_tokens"] / count)
                        if count > 0
                        else 0
                    ),
                    "total_time_ms": round(stats["total_time_ms"], 1),
                    "avg_time_ms": (
                        round(stats["total_time_ms"] / count, 1)
                        if count > 0
                        else 0
                    ),
                }
            return result

    def get_timeline(self, minutes: int = 60) -> list[dict[str, Any]]:
        """Return time-series data for the last N minutes."""
        with self._data_lock:
            cutoff = time.time() - (minutes * 60)
            result = []
            for bucket in self.time_series:
                if bucket.timestamp >= cutoff:
                    avg_latency = (
                        bucket.total_latency_ms / bucket.requests
                        if bucket.requests > 0
                        else 0
                    )
                    result.append({
                        "timestamp": bucket.timestamp,
                        "requests": bucket.requests,
                        "errors": bucket.errors,
                        "avg_latency_ms": round(avg_latency, 1),
                        "tokens": bucket.total_tokens,
                    })
            return result

    def get_errors(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent errors."""
        with self._data_lock:
            return [
                {
                    "timestamp": e.timestamp,
                    "code": e.code,
                    "message": e.message,
                    "session_id": e.session_id,
                    "skill_id": e.skill_id,
                }
                for e in reversed(self.errors[-limit:])
            ]

    def get_quality_histogram(self) -> dict[str, Any]:
        """Return quality score distribution."""
        with self._data_lock:
            labels = [
                f"{i*10}-{(i+1)*10}%" for i in range(10)
            ]
            return {
                "labels": labels,
                "counts": list(self.quality_histogram),
                "total": sum(self.quality_histogram),
            }

    def get_health(
        self,
        *,
        llm_status: str = "unknown",
        skills_count: int = 0,
        sessions_count: int = 0,
        memory_stats: dict | None = None,
    ) -> dict[str, Any]:
        """Return detailed health status."""
        with self._data_lock:
            uptime = time.time() - self.started_at
            return {
                "status": "healthy",
                "uptime_seconds": round(uptime, 1),
                "llm": llm_status,
                "skills_loaded": skills_count,
                "active_sessions": sessions_count,
                "memory": memory_stats or {},
                "total_requests": self.total_requests,
                "error_rate": (
                    round(self.error_count / self.total_requests * 100, 1)
                    if self.total_requests > 0
                    else 0
                ),
            }
