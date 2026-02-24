"""
Web Search Provider - Multi-source web search engine for the Deep Research skill.

Supports:
- Tavily Search API (requires TAVILY_API_KEY) — optimized for LLM/AI agents
- Brave Search API  (requires BRAVE_SEARCH_API_KEY)
- Google Custom Search (requires GOOGLE_API_KEY + GOOGLE_CX)
- Fallback: DuckDuckGo HTML (no API key needed)

Architecture:
    WebSearchProvider (facade)
    ├── TavilySearchBackend   (highest priority — built for AI agents)
    ├── BraveSearchBackend
    ├── GoogleSearchBackend
    └── FallbackSearchBackend (no API key needed)
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ─────────────────────────────────────
# Data Models
# ─────────────────────────────────────


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str = ""         # e.g. "tavily", "brave", "google", "duckduckgo"
    published_date: str = ""
    relevance_score: float = 0.0
    raw_content: str = ""    # extracted page content (optional)


@dataclass
class SearchReport:
    """Aggregated search results with metadata."""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_found: int = 0
    search_time_ms: int = 0
    sources_used: list[str] = field(default_factory=list)
    answer: str = ""         # LLM-generated answer (Tavily only)
    error: str | None = None


# ─────────────────────────────────────
# Search Backends
# ─────────────────────────────────────


class TavilySearchBackend:
    """
    Tavily Search API backend — purpose-built for AI agents.

    Features over other backends:
    - Returns clean, LLM-ready content (no HTML parsing needed)
    - Optional LLM-generated answer from search results
    - Relevance scoring per result
    - Raw page content extraction built-in
    - Optimised for agentic RAG pipelines

    Env: TAVILY_API_KEY (or TAVILY_SEARCH_API_KEY)
    Docs: https://docs.tavily.com/documentation/api-reference/endpoint/search
    """

    API_URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        *,
        search_depth: str = "advanced",
        include_answer: bool | str = "basic",
        include_raw_content: bool | str = "markdown",
        topic: str = "general",
    ):
        self._api_key = api_key
        self._search_depth = search_depth
        self._include_answer = include_answer
        self._include_raw_content = include_raw_content
        self._topic = topic

    def search(
        self,
        query: str,
        count: int = 10,
        language: str = "ko",
    ) -> list[SearchResult]:
        """Execute a Tavily web search."""
        payload: dict[str, Any] = {
            "query": query,
            "search_depth": self._search_depth,
            "max_results": min(count, 20),
            "topic": self._topic,
            "include_answer": self._include_answer,
            "include_raw_content": self._include_raw_content,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(self.API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            results: list[SearchResult] = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source="tavily",
                    published_date=item.get("published_date", ""),
                    relevance_score=item.get("score", 0.0),
                    raw_content=item.get("raw_content", "") or "",
                ))

            # Store the answer on the first result as metadata (for caller)
            answer = data.get("answer", "")
            if answer and results:
                results[0]._tavily_answer = answer  # type: ignore[attr-defined]

            logger.info(
                "Tavily search: query='%s', results=%d, depth=%s, answer=%s",
                query[:50],
                len(results),
                self._search_depth,
                bool(answer),
            )
            return results

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Tavily search HTTP error [%d]: %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            return []
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            return []

    def search_with_answer(
        self,
        query: str,
        count: int = 5,
    ) -> tuple[list[SearchResult], str]:
        """
        Execute search and return both results and LLM-generated answer.
        Convenience method for callers that need the Tavily answer.
        """
        payload: dict[str, Any] = {
            "query": query,
            "search_depth": self._search_depth,
            "max_results": min(count, 20),
            "topic": self._topic,
            "include_answer": "advanced",
            "include_raw_content": self._include_raw_content,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(self.API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            results: list[SearchResult] = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source="tavily",
                    published_date=item.get("published_date", ""),
                    relevance_score=item.get("score", 0.0),
                    raw_content=item.get("raw_content", "") or "",
                ))

            answer = data.get("answer", "")
            return results, answer

        except Exception as exc:
            logger.warning("Tavily search_with_answer failed: %s", exc)
            return [], ""


class BraveSearchBackend:
    """Brave Search API backend."""

    API_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str):
        self._api_key = api_key

    def search(self, query: str, count: int = 10, language: str = "ko") -> list[SearchResult]:
        """Execute a Brave web search."""
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        params = {
            "q": query,
            "count": min(count, 20),
            "search_lang": language,
            "text_decorations": False,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(self.API_URL, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("web", {}).get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source="brave",
                    published_date=item.get("page_age", ""),
                ))
            return results

        except Exception as exc:
            logger.warning("Brave search failed: %s", exc)
            return []


class GoogleSearchBackend:
    """Google Custom Search JSON API backend."""

    API_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, cx: str):
        self._api_key = api_key
        self._cx = cx

    def search(self, query: str, count: int = 10, language: str = "ko") -> list[SearchResult]:
        """Execute a Google Custom Search."""
        lang_map = {"ko": "lang_ko", "en": "lang_en", "ja": "lang_ja"}
        params = {
            "key": self._api_key,
            "cx": self._cx,
            "q": query,
            "num": min(count, 10),
            "lr": lang_map.get(language, ""),
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(self.API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("items", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="google",
                ))
            return results

        except Exception as exc:
            logger.warning("Google search failed: %s", exc)
            return []


class FallbackSearchBackend:
    """
    Fallback search backend - no API key needed.
    Uses DuckDuckGo HTML lite search as a public endpoint.
    """

    DDG_URL = "https://html.duckduckgo.com/html/"

    def search(self, query: str, count: int = 10, language: str = "ko") -> list[SearchResult]:
        """Execute a DuckDuckGo HTML search (no API key)."""
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                resp = client.post(
                    self.DDG_URL,
                    data={"q": query, "kl": f"{language}-{language}"},
                    headers={"User-Agent": "Mozilla/5.0 (compatible; SkillForge/1.0)"},
                )
                resp.raise_for_status()
                html = resp.text

            # Simple HTML parsing (no BS4 dependency)
            results = []
            # Find result blocks
            snippets_raw = re.findall(
                r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
                r'class="result__snippet"[^>]*>(.*?)</(?:td|div)',
                html,
                re.DOTALL,
            )
            for url, title, snippet in snippets_raw[:count]:
                # Clean HTML tags
                clean_title = re.sub(r"<[^>]+>", "", title).strip()
                clean_snippet = re.sub(r"<[^>]+>", "", snippet).strip()
                # DuckDuckGo wraps URLs
                actual_url = url
                if "uddg=" in url:
                    match = re.search(r"uddg=([^&]+)", url)
                    if match:
                        from urllib.parse import unquote
                        actual_url = unquote(match.group(1))

                if clean_title:
                    results.append(SearchResult(
                        title=clean_title,
                        url=actual_url,
                        snippet=clean_snippet,
                        source="duckduckgo",
                    ))

            return results

        except Exception as exc:
            logger.warning("Fallback (DuckDuckGo) search failed: %s", exc)
            return []


class SimulatedSearchBackend:
    """
    Simulated search backend for demo/testing (no network calls).
    Returns realistic-looking mock search results.
    """

    def search(self, query: str, count: int = 10, language: str = "ko") -> list[SearchResult]:
        """Return simulated search results based on query keywords."""
        results = []

        # Generate context-aware mock results
        topics = self._detect_topics(query)

        for i, topic in enumerate(topics[:count]):
            results.append(SearchResult(
                title=topic["title"],
                url=topic["url"],
                snippet=topic["snippet"],
                source="simulated",
                published_date="2025-01-15",
                relevance_score=0.95 - (i * 0.05),
            ))

        return results

    def _detect_topics(self, query: str) -> list[dict[str, str]]:
        """Generate topic-appropriate mock results."""
        query_lower = query.lower()

        base_results = [
            {
                "title": f"'{query}' 관련 최신 트렌드 분석 (2025)",
                "url": f"https://research.example.com/trends/{query.replace(' ', '-')}",
                "snippet": f"{query}에 대한 포괄적인 시장 분석 자료입니다. 최근 동향, 주요 플레이어, 성장 전망을 다룹니다.",
            },
            {
                "title": f"{query} 산업 보고서 - 글로벌 시장 전망",
                "url": f"https://reports.example.com/industry/{query.replace(' ', '-')}",
                "snippet": f"글로벌 {query} 시장 규모, 성장률, 지역별 분석, 주요 기업 동향을 포함한 종합 보고서입니다.",
            },
            {
                "title": f"{query}: 전문가 의견 종합",
                "url": f"https://experts.example.com/opinions/{query.replace(' ', '-')}",
                "snippet": f"업계 전문가들이 분석한 {query}의 현재와 미래. 기술적 관점, 비즈니스 영향, 전략적 시사점을 제공합니다.",
            },
            {
                "title": f"[데이터] {query} 통계 및 수치 정리",
                "url": f"https://data.example.com/stats/{query.replace(' ', '-')}",
                "snippet": f"{query} 관련 핵심 통계 자료 모음. 시장 점유율, 성장률, 투자 현황 등 정량적 데이터를 제공합니다.",
            },
            {
                "title": f"{query} 성공/실패 사례 연구 (Case Study)",
                "url": f"https://casestudy.example.com/{query.replace(' ', '-')}",
                "snippet": f"국내외 기업들의 {query} 관련 성공 사례와 실패 사례를 분석합니다. 교훈과 Best Practice를 도출합니다.",
            },
        ]

        # Add topic-specific results
        if any(kw in query_lower for kw in ["ai", "인공지능", "llm", "gpt"]):
            base_results.insert(0, {
                "title": f"AI 기술 동향: {query} 최신 연구 현황",
                "url": f"https://ai-research.example.com/{query.replace(' ', '-')}",
                "snippet": "최신 AI 연구 논문과 기술 트렌드를 분석합니다. GPT, Claude, Gemini 등 주요 모델의 발전 동향을 포함합니다.",
            })
        if any(kw in query_lower for kw in ["시장", "market", "경제", "투자"]):
            base_results.insert(0, {
                "title": f"2025년 {query} 시장 전망 및 투자 분석",
                "url": f"https://market.example.com/{query.replace(' ', '-')}",
                "snippet": "시장 규모 $XXB 전망, CAGR XX%, 주요 투자 기회와 리스크 요인을 분석한 보고서입니다.",
            })
        if any(kw in query_lower for kw in ["경쟁", "competitor", "비교", "벤치마크"]):
            base_results.insert(0, {
                "title": f"{query} 경쟁사 분석 및 벤치마킹 보고서",
                "url": f"https://competitive.example.com/{query.replace(' ', '-')}",
                "snippet": "주요 경쟁사 비교 분석, SWOT 분석, 차별화 전략, 시장 포지셔닝 현황을 다룹니다.",
            })

        return base_results


# ─────────────────────────────────────
# Content Extractor
# ─────────────────────────────────────


class ContentExtractor:
    """Extract main text content from a web page URL."""

    @staticmethod
    def extract(url: str, max_chars: int = 3000) -> str:
        """
        Fetch a URL and extract its main text content.
        Strips HTML tags, scripts, styles, etc.
        """
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                resp = client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; SkillForge/1.0)"},
                )
                resp.raise_for_status()
                html = resp.text

            # Remove scripts, styles, comments
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
            # Remove HTML tags
            text = re.sub(r"<[^>]+>", " ", text)
            # Collapse whitespace
            text = re.sub(r"\s+", " ", text).strip()
            # Decode HTML entities
            text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")

            return text[:max_chars]

        except Exception as exc:
            logger.debug("Content extraction failed for %s: %s", url, exc)
            return ""


# ─────────────────────────────────────
# WebSearchProvider (Facade)
# ─────────────────────────────────────


class WebSearchProvider:
    """
    Unified web search facade — auto-selects the best available backend.

    Priority:
    1. Tavily Search API (if TAVILY_API_KEY is set) — best for AI agents
    2. Brave Search API  (if BRAVE_SEARCH_API_KEY is set)
    3. Google Custom Search (if GOOGLE_API_KEY + GOOGLE_CX are set)
    4. DuckDuckGo fallback (no API key needed)
    5. Simulated backend (for testing/demo)
    """

    def __init__(
        self,
        *,
        tavily_api_key: str | None = None,
        brave_api_key: str | None = None,
        google_api_key: str | None = None,
        google_cx: str | None = None,
        use_simulated: bool = False,
        extract_content: bool = True,
        max_content_chars: int = 2000,
    ):
        self._backends: list[tuple[str, Any]] = []
        self._extract_content = extract_content
        self._max_content_chars = max_content_chars
        self._extractor = ContentExtractor()
        self._tavily: TavilySearchBackend | None = None

        if use_simulated:
            self._backends.append(("simulated", SimulatedSearchBackend()))
        else:
            # Auto-detect available backends (priority order)

            # 1. Tavily — best for AI/LLM agents
            tavily_key = tavily_api_key or os.getenv("TAVILY_API_KEY", "") or os.getenv("TAVILY_SEARCH_API_KEY", "")
            if tavily_key:
                tavily = TavilySearchBackend(tavily_key)
                self._backends.append(("tavily", tavily))
                self._tavily = tavily
                logger.info("Tavily Search backend registered (primary)")

            # 2. Brave
            brave_key = brave_api_key or os.getenv("BRAVE_SEARCH_API_KEY", "")
            if brave_key:
                self._backends.append(("brave", BraveSearchBackend(brave_key)))
                logger.info("Brave Search backend registered")

            # 3. Google
            google_key = google_api_key or os.getenv("GOOGLE_API_KEY", "")
            google_cx_val = google_cx or os.getenv("GOOGLE_CX", "")
            if google_key and google_cx_val:
                self._backends.append(("google", GoogleSearchBackend(google_key, google_cx_val)))
                logger.info("Google Search backend registered")

            # 4. Always add DuckDuckGo fallback
            self._backends.append(("duckduckgo", FallbackSearchBackend()))
            logger.info("DuckDuckGo fallback backend registered")

    def search(
        self,
        query: str,
        count: int = 10,
        language: str = "ko",
        extract_top_n: int = 3,
    ) -> SearchReport:
        """
        Execute a web search using available backends.

        Args:
            query: Search query string
            count: Max results per backend
            language: Search language code (ko, en, ja)
            extract_top_n: Number of top results to extract full content from

        Returns:
            SearchReport with aggregated results
        """
        start_time = time.time()
        all_results: list[SearchResult] = []
        sources_used: list[str] = []
        tavily_answer: str = ""

        for name, backend in self._backends:
            try:
                results = backend.search(query, count=count, language=language)
                if results:
                    # Capture Tavily answer if available
                    if name == "tavily" and results:
                        tavily_answer = getattr(results[0], "_tavily_answer", "")
                    all_results.extend(results)
                    sources_used.append(name)
                    logger.info("Search backend '%s' returned %d results", name, len(results))
                    # If we got enough results from a premium backend, skip fallback
                    if len(all_results) >= count and name not in ("duckduckgo",):
                        break
            except Exception as exc:
                logger.warning("Search backend '%s' failed: %s", name, exc)
                continue

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_results: list[SearchResult] = []
        for r in all_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        # Extract content from top N results (skip if Tavily already provided raw_content)
        if self._extract_content and extract_top_n > 0:
            for result in unique_results[:extract_top_n]:
                if result.source not in ("simulated", "tavily") and not result.raw_content:
                    content = self._extractor.extract(result.url, self._max_content_chars)
                    result.raw_content = content

        elapsed_ms = int((time.time() - start_time) * 1000)

        return SearchReport(
            query=query,
            results=unique_results[:count],
            total_found=len(unique_results),
            search_time_ms=elapsed_ms,
            sources_used=sources_used,
            answer=tavily_answer,
        )

    def multi_search(
        self,
        queries: list[str],
        count_per_query: int = 5,
        language: str = "ko",
    ) -> list[SearchReport]:
        """
        Execute multiple search queries (for multi-faceted research).
        """
        reports = []
        for query in queries:
            report = self.search(query, count=count_per_query, language=language)
            reports.append(report)
        return reports

    @property
    def available_backends(self) -> list[str]:
        return [name for name, _ in self._backends]

    @property
    def has_tavily(self) -> bool:
        """Check if Tavily backend is available."""
        return self._tavily is not None
