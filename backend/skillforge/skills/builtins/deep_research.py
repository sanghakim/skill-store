"""
Deep Research Skill - Web-search-based deep analysis.

Multi-step research pipeline:
1. Query Expansion   → Generate sub-queries from the main topic
2. Web Search        → Search across multiple sources
3. Content Extraction → Pull key content from top results
4. Synthesis         → LLM-powered analysis & report generation

This skill is designed to work with the SkillForge multi-agent system
and integrates with the ResearchAgent for orchestrated execution.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from skillforge.engine.sandbox import LLMBackend, SimulatedLLMBackend
from skillforge.skills.builtins.web_search import (
    SearchReport,
    SearchResult,
    WebSearchProvider,
)

logger = logging.getLogger(__name__)


class DeepResearchEngine:
    """
    Orchestrates a multi-step deep research pipeline.

    Steps:
    1. Parse & expand user query into multiple search sub-queries
    2. Execute web searches across available backends
    3. Extract and rank relevant content
    4. Synthesize findings into a structured research report
    """

    def __init__(
        self,
        llm_backend: LLMBackend | None = None,
        search_provider: WebSearchProvider | None = None,
        max_sources: int = 10,
        max_sub_queries: int = 5,
        content_chars_per_source: int = 2000,
    ):
        self._llm = llm_backend or SimulatedLLMBackend()
        self._search = search_provider or WebSearchProvider(use_simulated=True)
        self._max_sources = max_sources
        self._max_sub_queries = max_sub_queries
        self._content_chars = content_chars_per_source

    def execute(
        self,
        topic: str,
        depth: str = "standard",
        perspective: str = "",
        language: str = "ko",
        output_format: str = "보고서",
    ) -> dict[str, Any]:
        """
        Run the full deep research pipeline.

        Args:
            topic: Main research topic/question
            depth: Research depth ("quick", "standard", "deep")
            perspective: Specific analysis angle or focus
            language: Output language
            output_format: Output format ("보고서", "브리핑", "SWOT", "비교분석")

        Returns:
            Dictionary with research results, report, and metadata
        """
        start_time = time.time()
        logger.info("Deep Research started: topic='%s', depth=%s", topic[:60], depth)

        # ── Step 1: Query Expansion ──
        sub_queries = self._expand_query(topic, perspective, depth)
        logger.info("Generated %d sub-queries", len(sub_queries))

        # ── Step 2: Web Search ──
        search_reports = self._execute_searches(sub_queries, language, depth)
        all_results = self._aggregate_results(search_reports)
        logger.info("Collected %d unique search results", len(all_results))

        # ── Step 3: Content Ranking & Selection ──
        ranked_sources = self._rank_sources(all_results, topic)

        # ── Step 4: Synthesis ──
        research_context = self._build_research_context(
            topic, perspective, ranked_sources, search_reports
        )
        report = self._synthesize_report(
            topic, perspective, research_context, output_format, language
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Build source list
        source_list = [
            {"title": r.title, "url": r.url, "snippet": r.snippet}
            for r in ranked_sources[:self._max_sources]
        ]

        return {
            "report": report,
            "sources": source_list,
            "metadata": {
                "topic": topic,
                "depth": depth,
                "sub_queries": sub_queries,
                "total_sources_found": len(all_results),
                "sources_analyzed": len(ranked_sources),
                "search_backends": list({
                    r.source for r in all_results
                }),
                "execution_time_ms": elapsed_ms,
            },
        }

    # ── Step 1: Query Expansion ──

    def _expand_query(
        self, topic: str, perspective: str, depth: str
    ) -> list[str]:
        """Generate sub-queries to cover different aspects of the topic."""
        count_map = {"quick": 2, "standard": 4, "deep": 6}
        target_count = count_map.get(depth, 4)

        prompt = f"""당신은 리서치 전문가입니다. 다음 주제에 대해 심층 분석을 위한 검색 쿼리를 {target_count}개 생성하세요.

[연구 주제]
{topic}

[분석 관점]
{perspective or '종합 분석'}

[요구사항]
- 각 쿼리는 주제의 서로 다른 측면을 다뤄야 합니다
- 한 줄에 하나의 쿼리만 작성하세요
- 시장 동향, 기술 분석, 경쟁 현황, 전망 등 다양한 관점을 포함하세요
- 번호나 기호 없이 쿼리만 작성하세요

검색 쿼리:"""

        try:
            raw = self._llm.generate(prompt, max_tokens=500, temperature=0.7)
            queries = [
                line.strip().lstrip("0123456789.-) ")
                for line in raw.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ]
            # Always include the original topic
            if topic not in queries:
                queries.insert(0, topic)
            return queries[:target_count + 1]  # +1 for original

        except Exception as exc:
            logger.warning("Query expansion failed, using defaults: %s", exc)
            return self._default_sub_queries(topic, perspective)

    def _default_sub_queries(self, topic: str, perspective: str) -> list[str]:
        """Fallback sub-queries when LLM expansion fails."""
        queries = [topic]
        queries.append(f"{topic} 최신 트렌드 2025")
        queries.append(f"{topic} 시장 분석 현황")
        if perspective:
            queries.append(f"{topic} {perspective}")
        queries.append(f"{topic} 전망 전략")
        return queries

    # ── Step 2: Web Search ──

    def _execute_searches(
        self, queries: list[str], language: str, depth: str
    ) -> list[SearchReport]:
        """Execute searches for all sub-queries."""
        count_map = {"quick": 3, "standard": 5, "deep": 8}
        count = count_map.get(depth, 5)

        extract_map = {"quick": 1, "standard": 2, "deep": 3}
        extract_n = extract_map.get(depth, 2)

        reports = []
        for query in queries:
            report = self._search.search(
                query=query,
                count=count,
                language=language,
                extract_top_n=extract_n,
            )
            reports.append(report)

        return reports

    # ── Step 3: Aggregate & Rank ──

    def _aggregate_results(
        self, reports: list[SearchReport]
    ) -> list[SearchResult]:
        """Deduplicate and aggregate results from all search reports."""
        seen_urls: set[str] = set()
        unique: list[SearchResult] = []

        for report in reports:
            for result in report.results:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    unique.append(result)

        return unique

    def _rank_sources(
        self, results: list[SearchResult], topic: str
    ) -> list[SearchResult]:
        """Rank sources by relevance to the topic."""
        topic_lower = topic.lower()
        topic_words = set(topic_lower.split())

        for r in results:
            score = 0.0
            text = f"{r.title} {r.snippet}".lower()

            # Title match
            for word in topic_words:
                if word in r.title.lower():
                    score += 0.3
            # Snippet match
            for word in topic_words:
                if word in r.snippet.lower():
                    score += 0.1
            # Has extracted content
            if r.raw_content:
                score += 0.2
            # Freshness bonus
            if r.published_date and "2025" in r.published_date:
                score += 0.1
            # Source reliability bonus (Tavily highest — built for AI)
            if r.source == "tavily":
                score += 0.2
            elif r.source in ("brave", "google"):
                score += 0.1

            r.relevance_score = min(score, 1.0)

        # Sort by relevance score (descending)
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results

    # ── Step 4: Build Context & Synthesize ──

    def _build_research_context(
        self,
        topic: str,
        perspective: str,
        sources: list[SearchResult],
        reports: list[SearchReport],
    ) -> str:
        """Build a structured context string from all gathered data."""
        parts = []

        parts.append(f"[연구 주제] {topic}")
        if perspective:
            parts.append(f"[분석 관점] {perspective}")
        parts.append("")

        # Include Tavily AI-generated answer if available
        tavily_answers = [r.answer for r in reports if r.answer]
        if tavily_answers:
            parts.append("=" * 40)
            parts.append("[AI 검색 요약 (Tavily)]")
            parts.append("=" * 40)
            for answer in tavily_answers[:2]:
                parts.append(answer)
            parts.append("")

        # Source summaries
        parts.append("=" * 40)
        parts.append("[수집된 자료]")
        parts.append("=" * 40)

        for i, src in enumerate(sources[:self._max_sources], 1):
            parts.append(f"\n--- 자료 {i}: {src.title} ---")
            parts.append(f"출처: {src.url}")
            if src.snippet:
                parts.append(f"요약: {src.snippet}")
            if src.raw_content:
                # Truncate content for context window
                content = src.raw_content[:self._content_chars]
                parts.append(f"본문 발췌:\n{content}")

        # Search metadata
        parts.append("")
        parts.append("=" * 40)
        parts.append("[검색 메타데이터]")
        parts.append(f"- 총 검색 결과: {sum(r.total_found for r in reports)}건")
        parts.append(f"- 분석 대상 소스: {min(len(sources), self._max_sources)}건")
        backends = set()
        for r in reports:
            backends.update(r.sources_used)
        parts.append(f"- 검색 엔진: {', '.join(backends)}")

        return "\n".join(parts)

    def _synthesize_report(
        self,
        topic: str,
        perspective: str,
        research_context: str,
        output_format: str,
        language: str,
    ) -> str:
        """Use LLM to synthesize a comprehensive research report."""
        format_instructions = self._get_format_instructions(output_format)

        prompt = f"""당신은 심층 리서치 분석가입니다. 수집된 웹 검색 자료를 바탕으로 전문적인 분석 보고서를 작성하세요.

{research_context}

[출력 형식]
{format_instructions}

[작성 지침]
1. 수집된 자료의 핵심 내용을 종합 분석하세요
2. 각 주장에 대해 출처를 [출처 N]으로 표기하세요
3. 데이터와 근거 중심으로 작성하세요
4. 객관적 분석과 함께 전략적 시사점을 제시하세요
5. 언어: {"한국어" if language == "ko" else "English" if language == "en" else "日本語"}

보고서를 작성해주세요:"""

        try:
            report = self._llm.generate(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.5,
            )
            return report

        except Exception as exc:
            logger.error("Report synthesis failed: %s", exc)
            return f"[보고서 생성 오류]\n자료 수집은 완료되었으나 보고서 합성 중 오류가 발생했습니다: {exc}"

    def _get_format_instructions(self, output_format: str) -> str:
        """Return format-specific instructions."""
        formats = {
            "보고서": """## 심층 분석 보고서: [주제]

### Executive Summary
(3-5줄 핵심 요약)

### 1. 현황 분석
(현재 상황, 주요 데이터, 트렌드)

### 2. 핵심 발견사항
(검색 자료 기반 주요 인사이트 3-5개)

### 3. 심층 분석
(데이터 기반 상세 분석)

### 4. 전략적 시사점
(비즈니스/실무 관점 시사점)

### 5. 향후 전망 및 제언
(미래 예측, 권장 조치사항)

### 참고 자료
(출처 목록)""",

            "브리핑": """## 브리핑 노트: [주제]

**핵심 요약** (3줄)
**배경** (2-3문장)
**주요 발견** (bullet 5개)
**시사점** (bullet 3개)
**권장 액션** (bullet 3개)""",

            "SWOT": """## SWOT 분석: [주제]

### Strengths (강점)
-

### Weaknesses (약점)
-

### Opportunities (기회)
-

### Threats (위협)
-

### 전략 방향
(SO/ST/WO/WT 전략 도출)""",

            "비교분석": """## 비교 분석 보고서: [주제]

### 비교 대상 개요
(비교 대상 소개)

### 비교 매트릭스
| 항목 | A | B | C |
|------|---|---|---|

### 상세 비교
(항목별 심층 비교)

### 종합 평가 및 권장사항
(최종 결론)""",
        }

        return formats.get(output_format, formats["보고서"])
