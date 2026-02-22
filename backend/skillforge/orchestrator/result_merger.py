"""
Result Merger - Combines outputs from multiple agents into a coherent response.
"""

from __future__ import annotations

import logging
from typing import Any

from skillforge.models import AgentRole, QualityReview

logger = logging.getLogger(__name__)


class ResultMerger:
    """Merges multi-agent outputs into a single coherent response."""

    def merge(
        self,
        user_request: str,
        task_results: dict[str, dict[str, Any]],
        plan_tasks: list | None = None,
    ) -> dict[str, Any]:
        """
        Merge all task results into a final output.

        Strategy:
        1. Collect all successful outputs
        2. Extract review feedback
        3. Assemble into a structured final response
        """
        successful_outputs: list[dict[str, Any]] = []
        review_data: dict[str, Any] | None = None
        all_outputs: dict[str, Any] = {}
        total_tokens = 0

        for task_id, result in task_results.items():
            if not result.get("success", False):
                continue

            # Extract review
            if "review" in result:
                review_obj = result["review"]
                if isinstance(review_obj, QualityReview):
                    review_data = {
                        "score": review_obj.overall_score,
                        "passed": review_obj.passed,
                        "feedback": review_obj.feedback,
                    }
                elif isinstance(review_obj, dict):
                    review_data = review_obj
                continue

            # Collect outputs
            outputs = result.get("outputs", {})
            if outputs:
                successful_outputs.append({
                    "task_id": task_id,
                    "skill_id": result.get("skill_id", ""),
                    "outputs": outputs,
                })
                all_outputs.update(outputs)

            total_tokens += result.get("tokens_used", 0)

        # Build final text output
        final_text = self._assemble_text(user_request, successful_outputs)

        return {
            "final_output": final_text,
            "all_outputs": all_outputs,
            "review": review_data,
            "total_tokens": total_tokens,
            "sources_count": len(successful_outputs),
        }

    def _assemble_text(
        self,
        user_request: str,
        successful_outputs: list[dict[str, Any]],
    ) -> str:
        """Assemble successful outputs into a single text response."""
        if not successful_outputs:
            return "요청을 처리했지만 결과를 생성하지 못했습니다."

        parts = []

        for i, entry in enumerate(successful_outputs):
            outputs = entry["outputs"]
            skill_id = entry.get("skill_id", "")

            for key, value in outputs.items():
                if isinstance(value, str) and value.strip():
                    if len(successful_outputs) > 1 and skill_id:
                        parts.append(f"--- [{skill_id}] ---")
                    parts.append(value.strip())

        if not parts:
            return "작업이 완료되었습니다."

        return "\n\n".join(parts)
