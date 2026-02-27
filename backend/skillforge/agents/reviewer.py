"""
Reviewer Agent - Validates execution results and ensures quality.
Implements multi-aspect scoring and pass/fail determination.
"""

from __future__ import annotations

import logging
from typing import Any

from skillforge.agents.base import BaseAgent
from skillforge.models import (
    AgentRole,
    QualityReview,
    QualityVerdict,
    ReviewItem,
)

logger = logging.getLogger(__name__)

# Review aspect definitions with weight
REVIEW_ASPECTS = [
    {"aspect": "completeness", "weight": 0.3, "desc": "Does the output address all parts of the request?"},
    {"aspect": "accuracy", "weight": 0.25, "desc": "Is the output factually correct and consistent?"},
    {"aspect": "format", "weight": 0.15, "desc": "Is the output well-structured and formatted?"},
    {"aspect": "tone", "weight": 0.15, "desc": "Is the tone appropriate for the context?"},
    {"aspect": "relevance", "weight": 0.15, "desc": "Is the output relevant to the original request?"},
]


class ReviewerAgent(BaseAgent):
    """Validates outputs from other agents and enforces quality standards."""

    role = AgentRole.REVIEWER

    def __init__(self, *args, quality_threshold: float = 0.75, **kwargs):
        super().__init__(*args, **kwargs)
        self.quality_threshold = quality_threshold

    async def process(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        task_id = context.get("task_id", "unknown")
        outputs = context.get("outputs", {})
        original_request = context.get("original_request", task_description)
        skill_id = context.get("skill_id", "")

        logger.info("Reviewer evaluating task=%s skill=%s", task_id, skill_id)

        # Run multi-aspect review
        review_items = self._evaluate_aspects(original_request, outputs, skill_id)

        # Calculate weighted overall score
        total_weight = sum(a["weight"] for a in REVIEW_ASPECTS)
        weighted_sum = 0.0
        for item, aspect_def in zip(review_items, REVIEW_ASPECTS):
            weighted_sum += item.score * aspect_def["weight"]
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        passed = overall_score >= self.quality_threshold

        # Build feedback message
        feedback_parts = []
        for item in review_items:
            if item.verdict == QualityVerdict.FAIL:
                feedback_parts.append(f"[FAIL] {item.aspect}: {item.comment}")
            elif item.verdict == QualityVerdict.WARN:
                feedback_parts.append(f"[WARN] {item.aspect}: {item.comment}")
        if not feedback_parts:
            feedback_parts.append("All quality checks passed.")

        review = QualityReview(
            task_id=task_id,
            overall_score=round(overall_score, 3),
            passed=passed,
            items=review_items,
            feedback="\n".join(feedback_parts),
        )

        # Log the review
        self.memory.add_message(
            session_id,
            "assistant",
            f"[Review] Score: {overall_score:.2f} | {'PASS' if passed else 'FAIL'} | {review.feedback[:150]}",
            agent=self.role,
        )

        logger.info("Review complete: score=%.2f passed=%s", overall_score, passed)

        return {
            "success": True,
            "review": review,
            "passed": passed,
            "overall_score": overall_score,
            "feedback": review.feedback,
        }

    def _evaluate_aspects(
        self,
        original_request: str,
        outputs: dict[str, Any],
        skill_id: str,
    ) -> list[ReviewItem]:
        """Evaluate the output across all quality aspects."""
        items = []
        output_str = self._flatten_output(outputs)
        output_len = len(output_str)

        for aspect_def in REVIEW_ASPECTS:
            aspect = aspect_def["aspect"]
            score, verdict, comment = self._score_aspect(
                aspect, original_request, output_str, output_len, skill_id
            )
            items.append(ReviewItem(
                aspect=aspect,
                verdict=verdict,
                score=round(score, 2),
                comment=comment,
            ))

        return items

    def _score_aspect(
        self,
        aspect: str,
        request: str,
        output: str,
        output_len: int,
        skill_id: str,
    ) -> tuple[float, QualityVerdict, str]:
        """Score a single quality aspect. Returns (score, verdict, comment)."""

        if aspect == "completeness":
            if output_len < 10:
                return 0.2, QualityVerdict.FAIL, "Output is empty or minimal"
            if output_len < 50:
                return 0.5, QualityVerdict.WARN, "Output may be too brief"
            if output_len < 200:
                return 0.75, QualityVerdict.PASS, "Output is reasonably complete"
            return 0.9, QualityVerdict.PASS, "Output appears complete"

        elif aspect == "accuracy":
            # Check for placeholder patterns that indicate incomplete generation
            placeholders = ["[", "TODO", "placeholder", "여기에", "TBD"]
            placeholder_count = sum(1 for p in placeholders if p in output)
            if placeholder_count > 3:
                return 0.4, QualityVerdict.FAIL, f"Found {placeholder_count} placeholders - may be inaccurate"
            if placeholder_count > 0:
                return 0.7, QualityVerdict.WARN, f"Found {placeholder_count} placeholder(s)"
            return 0.9, QualityVerdict.PASS, "No accuracy issues detected"

        elif aspect == "format":
            has_structure = any(marker in output for marker in ["#", "##", "-", "1.", "•", "|"])
            if has_structure:
                return 0.9, QualityVerdict.PASS, "Output is well-structured"
            if output_len > 200:
                return 0.6, QualityVerdict.WARN, "Long output lacks structure"
            return 0.8, QualityVerdict.PASS, "Format is acceptable"

        elif aspect == "tone":
            # Basic tone check
            informal_markers = ["ㅋㅋ", "ㅎㅎ", "lol", "haha", "!!!", "???"]
            has_informal = any(m in output.lower() for m in informal_markers)
            if has_informal:
                return 0.5, QualityVerdict.WARN, "Informal tone detected"
            return 0.9, QualityVerdict.PASS, "Tone is appropriate"

        elif aspect == "relevance":
            # Check if key request words appear in output
            # Filter out very short words (Korean particles, common words)
            request_words = {w for w in request.lower().split() if len(w) > 1}
            output_lower = output.lower()

            if not request_words:
                return 0.8, QualityVerdict.PASS, "Request too short for relevance check"

            # Count how many request words appear anywhere in the output text
            # (substring match, not just word boundary match)
            found = sum(1 for w in request_words if w in output_lower)
            relevance_ratio = found / len(request_words)

            if relevance_ratio < 0.05 and output_len > 100:
                # Output is substantial but totally unrelated
                return 0.5, QualityVerdict.WARN, "Output may have limited relevance"
            if found == 0 and output_len < 50:
                return 0.4, QualityVerdict.FAIL, "Output seems unrelated to the request"
            if relevance_ratio < 0.1:
                return 0.7, QualityVerdict.PASS, "Partial relevance detected"
            return 0.9, QualityVerdict.PASS, "Output is relevant to the request"

        return 0.8, QualityVerdict.PASS, "Default pass"

    @staticmethod
    def _flatten_output(outputs: dict[str, Any]) -> str:
        """Flatten output dict into a single string for analysis."""
        parts = []
        for key, value in outputs.items():
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, dict):
                parts.append(str(value))
            elif isinstance(value, list):
                parts.append(", ".join(str(v) for v in value))
            else:
                parts.append(str(value))
        return "\n".join(parts)
