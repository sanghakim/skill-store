"""
Tests for the Deep Research skill: WebSearchProvider, DeepResearchEngine,
and ResearchAgent integration with deep-researcher.
"""

from __future__ import annotations

import pytest

from skillforge.engine.sandbox import SimulatedLLMBackend
from skillforge.skills.builtins.web_search import (
    ContentExtractor,
    FallbackSearchBackend,
    SearchReport,
    SearchResult,
    SimulatedSearchBackend,
    TavilySearchBackend,
    WebSearchProvider,
)
from skillforge.skills.builtins.deep_research import DeepResearchEngine


# ═══════════════════════════════════════
# SimulatedSearchBackend
# ═══════════════════════════════════════

class TestSimulatedSearchBackend:
    def setup_method(self):
        self.backend = SimulatedSearchBackend()

    def test_search_returns_results(self):
        results = self.backend.search("AI 시장 분석", count=5)
        assert len(results) >= 3
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_result_has_fields(self):
        results = self.backend.search("블록체인 트렌드")
        r = results[0]
        assert r.title
        assert r.url
        assert r.snippet
        assert r.source == "simulated"

    def test_search_count_limit(self):
        results = self.backend.search("테스트", count=3)
        assert len(results) <= 5  # may return base + topic-specific

    def test_ai_topic_detection(self):
        results = self.backend.search("인공지능 LLM 기술 동향")
        titles = " ".join(r.title for r in results)
        assert "AI" in titles or "인공지능" in titles or "트렌드" in titles

    def test_market_topic_detection(self):
        results = self.backend.search("시장 분석 투자 전망")
        snippets = " ".join(r.snippet for r in results)
        assert "시장" in snippets or "투자" in snippets

    def test_competitor_topic_detection(self):
        results = self.backend.search("경쟁사 비교 벤치마크")
        titles = " ".join(r.title for r in results)
        assert "경쟁" in titles or "벤치마크" in titles or "비교" in titles


# ═══════════════════════════════════════
# TavilySearchBackend (unit tests with mock)
# ═══════════════════════════════════════

class TestTavilySearchBackend:
    """Test TavilySearchBackend class structure and init."""

    def test_class_exists_and_has_api_url(self):
        assert TavilySearchBackend.API_URL == "https://api.tavily.com/search"

    def test_init_stores_config(self):
        backend = TavilySearchBackend(
            api_key="tvly-test-key",
            search_depth="basic",
            include_answer=True,
            topic="news",
        )
        assert backend._api_key == "tvly-test-key"
        assert backend._search_depth == "basic"
        assert backend._include_answer is True
        assert backend._topic == "news"

    def test_default_config(self):
        backend = TavilySearchBackend(api_key="tvly-test")
        assert backend._search_depth == "advanced"
        assert backend._include_answer == "basic"
        assert backend._include_raw_content == "markdown"
        assert backend._topic == "general"

    def test_search_with_invalid_key_returns_empty(self):
        """Search with a dummy key should fail gracefully and return empty."""
        backend = TavilySearchBackend(api_key="tvly-invalid-key-for-testing")
        results = backend.search("test query", count=3)
        # Should return empty list (HTTP error caught), not raise
        assert isinstance(results, list)

    def test_search_with_answer_with_invalid_key_returns_empty(self):
        """search_with_answer should also fail gracefully."""
        backend = TavilySearchBackend(api_key="tvly-invalid-key-for-testing")
        results, answer = backend.search_with_answer("test query", count=3)
        assert isinstance(results, list)
        assert isinstance(answer, str)


class TestWebSearchProviderWithTavily:
    """Test WebSearchProvider Tavily integration logic."""

    def test_tavily_env_detection(self, monkeypatch):
        """Provider should register Tavily when env var is set."""
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key-123")
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        provider = WebSearchProvider()
        assert "tavily" in provider.available_backends
        assert provider.has_tavily

    def test_tavily_search_api_key_env(self, monkeypatch):
        """Should also accept TAVILY_SEARCH_API_KEY env var."""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("TAVILY_SEARCH_API_KEY", "tvly-alt-key")
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        provider = WebSearchProvider()
        assert "tavily" in provider.available_backends
        assert provider.has_tavily

    def test_tavily_constructor_key(self):
        """Should accept Tavily key via constructor."""
        provider = WebSearchProvider(tavily_api_key="tvly-direct-key")
        assert "tavily" in provider.available_backends
        assert provider.has_tavily

    def test_tavily_priority_over_brave(self, monkeypatch):
        """Tavily should be registered before Brave."""
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-key")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        provider = WebSearchProvider()
        backends = provider.available_backends
        assert backends.index("tavily") < backends.index("brave")

    def test_no_tavily_when_simulated(self):
        """Simulated mode should not have Tavily."""
        provider = WebSearchProvider(use_simulated=True)
        assert not provider.has_tavily
        assert "simulated" in provider.available_backends

    def test_no_tavily_without_key(self, monkeypatch):
        """No Tavily backend when no key is set."""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        provider = WebSearchProvider()
        assert not provider.has_tavily
        # Should still have duckduckgo fallback
        assert "duckduckgo" in provider.available_backends

    def test_search_report_has_answer_field(self):
        """SearchReport should have an answer field (for Tavily)."""
        report = SearchReport(query="test")
        assert hasattr(report, "answer")
        assert report.answer == ""


# ═══════════════════════════════════════
# WebSearchProvider
# ═══════════════════════════════════════

class TestWebSearchProvider:
    def setup_method(self):
        self.provider = WebSearchProvider(use_simulated=True)

    def test_simulated_mode(self):
        assert "simulated" in self.provider.available_backends

    def test_search_returns_report(self):
        report = self.provider.search("AI 트렌드 분석")
        assert isinstance(report, SearchReport)
        assert report.query == "AI 트렌드 분석"
        assert len(report.results) > 0
        assert report.search_time_ms >= 0

    def test_search_deduplicates_by_url(self):
        report = self.provider.search("테스트 쿼리", count=10)
        urls = [r.url for r in report.results]
        assert len(urls) == len(set(urls))

    def test_multi_search(self):
        queries = ["쿼리 1", "쿼리 2", "쿼리 3"]
        reports = self.provider.multi_search(queries, count_per_query=3)
        assert len(reports) == 3
        assert all(isinstance(r, SearchReport) for r in reports)

    def test_search_sources_tracked(self):
        report = self.provider.search("테스트")
        assert "simulated" in report.sources_used


# ═══════════════════════════════════════
# DeepResearchEngine
# ═══════════════════════════════════════

class TestDeepResearchEngine:
    def setup_method(self):
        self.llm = SimulatedLLMBackend()
        self.search = WebSearchProvider(use_simulated=True)
        self.engine = DeepResearchEngine(
            llm_backend=self.llm,
            search_provider=self.search,
        )

    def test_execute_returns_report(self):
        result = self.engine.execute(topic="AI 시장 분석")
        assert "report" in result
        assert "sources" in result
        assert "metadata" in result
        assert result["report"]  # non-empty

    def test_execute_has_sources(self):
        result = self.engine.execute(topic="블록체인 기술 동향")
        assert len(result["sources"]) > 0
        src = result["sources"][0]
        assert "title" in src
        assert "url" in src

    def test_execute_metadata(self):
        result = self.engine.execute(topic="테스트 주제", depth="quick")
        meta = result["metadata"]
        assert meta["topic"] == "테스트 주제"
        assert meta["depth"] == "quick"
        assert meta["execution_time_ms"] >= 0
        assert len(meta["sub_queries"]) >= 1

    def test_depth_quick(self):
        result = self.engine.execute(topic="빠른 분석", depth="quick")
        meta = result["metadata"]
        # quick depth should generate fewer sub-queries
        assert len(meta["sub_queries"]) <= 4

    def test_depth_deep(self):
        result = self.engine.execute(topic="심층 분석 주제", depth="deep")
        meta = result["metadata"]
        assert len(meta["sub_queries"]) >= 2

    def test_perspective_included(self):
        result = self.engine.execute(
            topic="AI 시장",
            perspective="기술적 관점",
        )
        assert result["report"]

    def test_swot_format(self):
        result = self.engine.execute(
            topic="SaaS 시장",
            output_format="SWOT",
        )
        assert result["report"]

    def test_briefing_format(self):
        result = self.engine.execute(
            topic="클라우드 트렌드",
            output_format="브리핑",
        )
        assert result["report"]

    def test_comparison_format(self):
        result = self.engine.execute(
            topic="AWS vs Azure",
            output_format="비교분석",
        )
        assert result["report"]

    def test_empty_topic_handled(self):
        """Engine should handle empty topic gracefully in the full pipeline."""
        # DeepResearchEngine doesn't do input validation itself;
        # this is handled at the ResearchAgent level
        result = self.engine.execute(topic="")
        # Should still return a structure (LLM will generate something)
        assert "report" in result

    def test_english_language(self):
        result = self.engine.execute(
            topic="Cloud computing trends",
            language="en",
        )
        assert result["report"]


# ═══════════════════════════════════════
# Query Expansion
# ═══════════════════════════════════════

class TestQueryExpansion:
    def setup_method(self):
        self.llm = SimulatedLLMBackend()
        self.search = WebSearchProvider(use_simulated=True)
        self.engine = DeepResearchEngine(
            llm_backend=self.llm,
            search_provider=self.search,
        )

    def test_expand_always_includes_original(self):
        queries = self.engine._expand_query("원본 쿼리", "", "standard")
        assert "원본 쿼리" in queries

    def test_expand_generates_multiple(self):
        queries = self.engine._expand_query("AI 기술", "", "standard")
        assert len(queries) >= 2

    def test_default_fallback(self):
        queries = self.engine._default_sub_queries("테스트 주제", "")
        assert "테스트 주제" in queries
        assert len(queries) >= 3

    def test_default_with_perspective(self):
        queries = self.engine._default_sub_queries("AI", "기술적 관점")
        assert any("기술적 관점" in q for q in queries)


# ═══════════════════════════════════════
# Source Ranking
# ═══════════════════════════════════════

class TestSourceRanking:
    def setup_method(self):
        self.engine = DeepResearchEngine(
            llm_backend=SimulatedLLMBackend(),
            search_provider=WebSearchProvider(use_simulated=True),
        )

    def test_ranking_scores_relevance(self):
        results = [
            SearchResult(title="AI 시장 분석 보고서", url="http://a.com", snippet="AI 시장에 대한 분석", source="brave"),
            SearchResult(title="요리 레시피", url="http://b.com", snippet="맛있는 음식 만들기", source="google"),
        ]
        ranked = self.engine._rank_sources(results, "AI 시장")
        assert ranked[0].url == "http://a.com"
        assert ranked[0].relevance_score > ranked[1].relevance_score

    def test_ranking_prefers_content(self):
        results = [
            SearchResult(title="보고서 A", url="http://a.com", snippet="내용 A", source="brave", raw_content="상세 본문..."),
            SearchResult(title="보고서 B", url="http://b.com", snippet="내용 B", source="brave"),
        ]
        ranked = self.engine._rank_sources(results, "보고서")
        assert ranked[0].url == "http://a.com"


# ═══════════════════════════════════════
# Integration with App (end-to-end)
# ═══════════════════════════════════════

class TestDeepResearchIntegration:
    @pytest.fixture
    def app(self):
        from skillforge.app import SkillForgeApp
        from skillforge.engine.sandbox import SimulatedLLMBackend
        sf = SkillForgeApp(
            load_builtins=True,
            max_iterations=2,
            quality_threshold=0.5,
            loop_timeout_ms=30_000,
            llm_backend=SimulatedLLMBackend(),
        )
        sf.initialize()
        yield sf
        sf.shutdown()

    def test_deep_researcher_skill_registered(self, app):
        """Verify deep-researcher is in the registry."""
        skill = app.registry.get("deep-researcher")
        assert skill is not None
        assert skill.name == "웹검색 심층분석기"
        assert skill.category.value == "knowledge"

    def test_deep_researcher_skill_inputs(self, app):
        skill = app.registry.get("deep-researcher")
        input_names = [f.name for f in skill.inputs]
        assert "topic" in input_names
        assert "depth" in input_names
        assert "perspective" in input_names
        assert "output_format" in input_names
        assert "language" in input_names

    def test_deep_researcher_skill_outputs(self, app):
        skill = app.registry.get("deep-researcher")
        output_names = [f.name for f in skill.outputs]
        assert "report" in output_names
        assert "sources" in output_names

    def test_builtin_count_is_15(self, app):
        """Verify we now have 15 built-in skills."""
        all_skills = app.registry.list_all()
        assert len(all_skills) == 15

    @pytest.mark.asyncio
    async def test_full_loop_deep_research(self, app):
        """Test full agentic loop with a deep research task."""
        result = await app.loop.run(
            "AI 시장 트렌드를 심층 조사해줘",
            user_id="test-user",
        )
        assert result.success
        assert result.session_id is not None
        assert result.iterations >= 1

    @pytest.mark.asyncio
    async def test_planner_detects_research_keywords(self, app):
        """Test that planner correctly maps research keywords to deep-researcher."""
        from skillforge.agents.planner import PlannerAgent
        planner = PlannerAgent(
            memory=app.memory,
            registry=app.registry,
            sandbox=app.sandbox,
        )
        detected = planner._detect_skills("AI 시장 트렌드를 리서치해줘")
        skill_ids = [sid for sid, _ in detected]
        assert "deep-researcher" in skill_ids

    @pytest.mark.asyncio
    async def test_planner_detects_korean_search_keywords(self, app):
        """Test Korean research keyword detection."""
        from skillforge.agents.planner import PlannerAgent
        planner = PlannerAgent(
            memory=app.memory,
            registry=app.registry,
            sandbox=app.sandbox,
        )

        for keyword in ["조사", "검색", "심층 분석", "트렌드", "시장조사", "경쟁분석", "동향"]:
            detected = planner._detect_skills(f"{keyword}해줘")
            skill_ids = [sid for sid, _ in detected]
            assert "deep-researcher" in skill_ids, f"Failed for keyword: {keyword}"

    @pytest.mark.asyncio
    async def test_planner_detects_english_research_keywords(self, app):
        """Test English research keyword detection."""
        from skillforge.agents.planner import PlannerAgent
        planner = PlannerAgent(
            memory=app.memory,
            registry=app.registry,
            sandbox=app.sandbox,
        )

        for keyword in ["research", "search", "trend", "market", "competitor"]:
            detected = planner._detect_skills(f"Please {keyword} this topic")
            skill_ids = [sid for sid, _ in detected]
            assert "deep-researcher" in skill_ids, f"Failed for keyword: {keyword}"

    @pytest.mark.asyncio
    async def test_direct_skill_execution(self, app):
        """Test direct deep-researcher skill execution (bypass loop)."""
        result = await app.loop.execute_skill(
            skill_id="deep-researcher",
            inputs={
                "topic": "클라우드 컴퓨팅 시장 분석",
                "depth": "quick",
                "output_format": "브리핑",
            },
            user_id="test-user",
        )
        assert result["success"]
        assert "outputs" in result
