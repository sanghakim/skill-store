"""
Intent Analyzer - Classifies user intent, determines complexity,
and identifies required capabilities.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from skillforge.models import AgentRole

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """Result of intent analysis."""
    primary_intent: str          # e.g., "email_compose", "report_generate"
    sub_intents: list[str] = field(default_factory=list)
    complexity: str = "simple"   # simple | moderate | complex
    suggested_agents: list[AgentRole] = field(default_factory=list)
    detected_keywords: list[str] = field(default_factory=list)
    language: str = "ko"
    requires_research: bool = False
    requires_review: bool = True
    confidence: float = 0.0


# Intent patterns: regex -> (intent_name, agents, complexity)
INTENT_PATTERNS: list[tuple[str, str, list[AgentRole], str]] = [
    # Email
    (r"이메일|메일|mail|email", "email_compose",
     [AgentRole.EXECUTOR], "simple"),
    (r"이메일.*요약|메일.*요약|summarize.*mail", "email_summarize",
     [AgentRole.EXECUTOR], "simple"),

    # Documents
    (r"보고서|report|기획서|제안서", "document_generate",
     [AgentRole.CREATIVE, AgentRole.REVIEWER], "moderate"),
    (r"회의록|meeting.*minutes", "meeting_minutes",
     [AgentRole.CREATIVE], "simple"),
    (r"계약서.*검토|review.*contract", "contract_review",
     [AgentRole.RESEARCH, AgentRole.REVIEWER], "moderate"),
    (r"SOP|절차서|매뉴얼", "sop_generate",
     [AgentRole.CREATIVE], "moderate"),

    # Data
    (r"분석|analyze|데이터|data|엑셀|excel|차트|chart", "data_analysis",
     [AgentRole.RESEARCH, AgentRole.EXECUTOR], "moderate"),

    # Presentation
    (r"PPT|프레젠테이션|슬라이드|발표|presentation|slide", "presentation",
     [AgentRole.CREATIVE, AgentRole.REVIEWER], "moderate"),

    # Schedule
    (r"일정|스케줄|schedule|calendar", "schedule_manage",
     [AgentRole.EXECUTOR], "simple"),

    # HR
    (r"채용|공고|JD|job.*description|recruit", "hr_jd",
     [AgentRole.CREATIVE], "simple"),

    # Translation
    (r"번역|translate|영어로|한국어로|일본어로", "translate",
     [AgentRole.EXECUTOR], "simple"),
    (r"교정|proofread|맞춤법|문법", "proofread",
     [AgentRole.EXECUTOR], "simple"),

    # Automation
    (r"자동화|automat|정기|반복|스케줄링", "automation",
     [AgentRole.PLANNER, AgentRole.EXECUTOR], "complex"),
]

# Complexity boosters
COMPLEXITY_BOOSTERS = [
    (r"그리고|and|또한|also|추가로", 0.3),
    (r"먼저.*그.*다음|first.*then", 0.4),
    (r"비교|compare|대비", 0.2),
    (r"종합|overall|전체", 0.2),
    (r"매주|매월|정기|weekly|monthly|recurring", 0.3),
]


class IntentAnalyzer:
    """Analyzes user input to determine intent, complexity, and required agents."""

    def analyze(self, user_input: str, context: dict[str, Any] | None = None) -> IntentResult:
        context = context or {}
        input_lower = user_input.lower()

        # Detect language
        language = "ko" if any('\uAC00' <= ch <= '\uD7A3' for ch in user_input) else "en"

        # Match intents
        matched_intents: list[tuple[str, list[AgentRole], str, float]] = []
        detected_keywords: list[str] = []

        for pattern, intent, agents, complexity in INTENT_PATTERNS:
            match = re.search(pattern, input_lower)
            if match:
                matched_intents.append((intent, agents, complexity, match.start()))
                detected_keywords.append(match.group())

        if not matched_intents:
            # Fallback to generic creative task
            return IntentResult(
                primary_intent="general",
                complexity="simple",
                suggested_agents=[AgentRole.CREATIVE],
                language=language,
                confidence=0.3,
            )

        # Primary intent = first match (most relevant)
        primary = matched_intents[0]
        sub_intents = [m[0] for m in matched_intents[1:]]

        # Collect all suggested agents
        all_agents = set()
        for _, agents, _, _ in matched_intents:
            all_agents.update(agents)

        # Determine complexity
        base_complexity = primary[2]
        complexity_score = {"simple": 1.0, "moderate": 2.0, "complex": 3.0}[base_complexity]

        # Apply boosters
        for pattern, boost in COMPLEXITY_BOOSTERS:
            if re.search(pattern, input_lower):
                complexity_score += boost

        # Multiple intents increase complexity
        complexity_score += len(matched_intents) * 0.3

        if complexity_score >= 3.0:
            final_complexity = "complex"
        elif complexity_score >= 1.8:
            final_complexity = "moderate"
        else:
            final_complexity = "simple"

        # Determine if research is needed
        requires_research = AgentRole.RESEARCH in all_agents or final_complexity == "complex"

        # Add planner for complex tasks
        if final_complexity in ("moderate", "complex"):
            all_agents.add(AgentRole.PLANNER)
        # Always include reviewer for non-simple
        if final_complexity != "simple":
            all_agents.add(AgentRole.REVIEWER)

        confidence = min(0.95, 0.5 + len(matched_intents) * 0.15 + len(detected_keywords) * 0.05)

        result = IntentResult(
            primary_intent=primary[0],
            sub_intents=sub_intents,
            complexity=final_complexity,
            suggested_agents=sorted(all_agents, key=lambda a: a.value),
            detected_keywords=detected_keywords,
            language=language,
            requires_research=requires_research,
            requires_review=final_complexity != "simple",
            confidence=round(confidence, 2),
        )

        logger.info(
            "Intent: %s (complexity=%s, agents=%s, confidence=%.2f)",
            result.primary_intent,
            result.complexity,
            [a.value for a in result.suggested_agents],
            result.confidence,
        )

        return result
