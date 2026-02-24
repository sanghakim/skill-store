"""
Skill Sandbox - Isolated execution environment for skills.
- Prompt template resolution (variable substitution)
- Resource limits (tokens, timeout)
- Simulated LLM execution (pluggable backend)
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Protocol

from skillforge.models import (
    SkillDefinition,
    SkillExecutionRequest,
    SkillExecutionResult,
)

logger = logging.getLogger(__name__)


class LLMBackend(Protocol):
    """Protocol for pluggable LLM backends."""

    def generate(self, prompt: str, max_tokens: int, temperature: float) -> str: ...


class SimulatedLLMBackend:
    """Simulated LLM backend for demo/testing purposes."""

    def generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
        # Simulate intelligent response based on prompt content
        lines = prompt.strip().split("\n")
        role_line = next((l for l in lines if "전문가" in l or "expert" in l.lower()), "")

        response_parts = []

        if "이메일" in prompt or "email" in prompt.lower():
            response_parts.append("제목: [상황에 맞는 전문적인 이메일 제목]")
            response_parts.append("")
            response_parts.append("존경하는 담당자님께,")
            response_parts.append("")
            response_parts.append("항상 귀사와의 협력에 감사드립니다.")
            response_parts.append("[본문 내용 - 상황에 맞게 작성됨]")
            response_parts.append("")
            response_parts.append("감사합니다.")
            response_parts.append("[발신자명]")
        elif "보고서" in prompt or "report" in prompt.lower() or "문서" in prompt:
            response_parts.append("# 보고서 제목")
            response_parts.append("")
            response_parts.append("## 1. 개요")
            response_parts.append("[프로젝트/주제에 대한 개요 설명]")
            response_parts.append("")
            response_parts.append("## 2. 현황 분석")
            response_parts.append("[데이터 기반 현황 분석 내용]")
            response_parts.append("")
            response_parts.append("## 3. 핵심 발견사항")
            response_parts.append("- 발견사항 1: [상세 내용]")
            response_parts.append("- 발견사항 2: [상세 내용]")
            response_parts.append("")
            response_parts.append("## 4. 결론 및 제언")
            response_parts.append("[종합 결론 및 향후 제안사항]")
        elif "번역" in prompt or "translat" in prompt.lower():
            response_parts.append("[전문 번역 결과]")
            response_parts.append("")
            response_parts.append("번역 노트: 비즈니스 맥락에 맞게 의역 처리하였습니다.")
        elif "분석" in prompt or "analyz" in prompt.lower() or "데이터" in prompt:
            response_parts.append("## 분석 결과")
            response_parts.append("")
            response_parts.append("### 주요 통계")
            response_parts.append("- 총 건수: [N건]")
            response_parts.append("- 평균: [값]")
            response_parts.append("- 트렌드: [상승/하락/유지]")
            response_parts.append("")
            response_parts.append("### 인사이트")
            response_parts.append("1. [핵심 인사이트 1]")
            response_parts.append("2. [핵심 인사이트 2]")
            response_parts.append("")
            response_parts.append("### 권장 조치")
            response_parts.append("- [실행 가능한 제안]")
        elif "회의록" in prompt or "meeting" in prompt.lower():
            response_parts.append("## 회의록")
            response_parts.append("")
            response_parts.append("**참석자:** [참석자 목록]")
            response_parts.append("**일시:** [회의 일시]")
            response_parts.append("")
            response_parts.append("### 주요 논의사항")
            response_parts.append("1. [논의사항 1]")
            response_parts.append("2. [논의사항 2]")
            response_parts.append("")
            response_parts.append("### 결정사항")
            response_parts.append("- [결정 1]")
            response_parts.append("")
            response_parts.append("### Action Items")
            response_parts.append("| 담당자 | 항목 | 기한 |")
            response_parts.append("|--------|------|------|")
            response_parts.append("| [이름] | [항목] | [기한] |")
        elif "리서치" in prompt or "심층" in prompt or "검색 쿼리" in prompt or "research" in prompt.lower():
            # Handle deep research prompts
            if "검색 쿼리" in prompt and "생성" in prompt:
                # Query expansion request
                response_parts.append("AI 기술 동향 최신 분석 2025")
                response_parts.append("AI 시장 규모 성장률 전망")
                response_parts.append("AI 주요 기업 경쟁 현황 비교")
                response_parts.append("AI 활용 사례 산업별 분석")
                response_parts.append("AI 규제 정책 글로벌 동향")
            else:
                # Research report synthesis
                response_parts.append("## 심층 분석 보고서")
                response_parts.append("")
                response_parts.append("### Executive Summary")
                response_parts.append("수집된 다수의 자료를 종합 분석한 결과, 해당 분야는 빠르게 성장하고 있으며")
                response_parts.append("주요 트렌드와 시사점을 도출하였습니다.")
                response_parts.append("")
                response_parts.append("### 1. 현황 분석")
                response_parts.append("- 시장 규모: 전년 대비 15% 성장 [출처 1]")
                response_parts.append("- 주요 플레이어: A사(35%), B사(25%), C사(15%) [출처 2]")
                response_parts.append("- 기술 성숙도: 도입기 → 성장기 전환 단계 [출처 3]")
                response_parts.append("")
                response_parts.append("### 2. 핵심 발견사항")
                response_parts.append("1. **트렌드 1**: 데이터 기반 의사결정 확산 [출처 1]")
                response_parts.append("2. **트렌드 2**: 자동화 및 AI 통합 가속 [출처 2]")
                response_parts.append("3. **트렌드 3**: 규제 환경 변화와 대응 필요 [출처 4]")
                response_parts.append("")
                response_parts.append("### 3. 심층 분석")
                response_parts.append("[수집 자료 기반 상세 분석 내용]")
                response_parts.append("")
                response_parts.append("### 4. 전략적 시사점")
                response_parts.append("- 조기 시장 진입으로 선점 효과 확보 권장")
                response_parts.append("- 핵심 기술 역량 확보를 위한 투자 필요")
                response_parts.append("- 파트너십 전략을 통한 생태계 구축 고려")
                response_parts.append("")
                response_parts.append("### 5. 향후 전망 및 제언")
                response_parts.append("- 단기(6개월): 파일럿 프로젝트 추진 권장")
                response_parts.append("- 중기(1-2년): 본격 사업화 및 확장")
                response_parts.append("- 장기(3년+): 시장 리더십 확보 목표")
                response_parts.append("")
                response_parts.append("### 참고 자료")
                response_parts.append("- [출처 1] 시장 트렌드 분석 보고서")
                response_parts.append("- [출처 2] 산업 보고서 - 글로벌 시장 전망")
                response_parts.append("- [출처 3] 전문가 의견 종합")
                response_parts.append("- [출처 4] 규제 동향 자료")
        else:
            response_parts.append(f"[{role_line or 'AI 어시스턴트'}의 전문적인 응답]")
            response_parts.append("")
            response_parts.append("요청하신 내용을 분석하여 다음과 같이 결과를 생성했습니다:")
            response_parts.append("")
            response_parts.append("1. [핵심 내용 1]")
            response_parts.append("2. [핵심 내용 2]")
            response_parts.append("3. [핵심 내용 3]")

        return "\n".join(response_parts)


class SkillSandbox:
    """Execute skills in an isolated environment with resource controls."""

    def __init__(
        self,
        llm_backend: LLMBackend | None = None,
        default_timeout_ms: int = 120_000,
        max_retries: int = 3,
    ):
        self._llm = llm_backend or SimulatedLLMBackend()
        self._default_timeout_ms = default_timeout_ms
        self._max_retries = max_retries

    def execute(
        self,
        skill: SkillDefinition,
        request: SkillExecutionRequest,
        extra_context: str = "",
    ) -> SkillExecutionResult:
        """
        Execute a skill:
        1. Validate inputs against schema
        2. Resolve prompt template with variables
        3. Inject extra context (user prefs, history)
        4. Call LLM backend
        5. Return structured result
        """
        start_time = time.time()

        try:
            # Step 1: Validate inputs
            self._validate_inputs(skill, request.inputs)

            # Step 2: Resolve prompt template
            resolved_prompt = self._resolve_template(
                skill.prompt_template, request.inputs
            )

            # Step 3: Inject extra context
            if extra_context:
                resolved_prompt = f"{extra_context}\n\n---\n\n{resolved_prompt}"

            # Step 4: Call LLM
            raw_output = self._llm.generate(
                prompt=resolved_prompt,
                max_tokens=skill.settings.max_tokens,
                temperature=skill.settings.temperature,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)
            tokens_used = len(resolved_prompt) // 4 + len(raw_output) // 4

            # Step 5: Build result
            # Map output to defined output fields
            outputs = {}
            if skill.outputs:
                # For single output field, map the whole response
                if len(skill.outputs) == 1:
                    outputs[skill.outputs[0].name] = raw_output
                else:
                    # Try to split output by sections
                    outputs = self._parse_output_sections(raw_output, skill.outputs)
            else:
                outputs["result"] = raw_output

            return SkillExecutionResult(
                skill_id=skill.id,
                outputs=outputs,
                success=True,
                tokens_used=tokens_used,
                execution_time_ms=elapsed_ms,
                resolved_prompt=resolved_prompt,
            )

        except Exception as exc:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error("Skill execution failed: %s - %s", skill.id, exc)
            return SkillExecutionResult(
                skill_id=skill.id,
                success=False,
                error=str(exc),
                execution_time_ms=elapsed_ms,
                resolved_prompt="",
            )

    def _validate_inputs(self, skill: SkillDefinition, inputs: dict) -> None:
        """Validate inputs against skill's input schema."""
        for field in skill.inputs:
            if field.required and field.name not in inputs:
                raise ValueError(f"Required input missing: {field.name}")

    def _resolve_template(self, template: str, variables: dict[str, Any]) -> str:
        """Replace {{variable}} placeholders with actual values."""
        resolved = template
        for key, value in variables.items():
            pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
            resolved = re.sub(pattern, str(value), resolved)
        return resolved

    def _parse_output_sections(
        self, raw_output: str, output_fields: list
    ) -> dict[str, Any]:
        """Attempt to parse multi-field output."""
        outputs = {}
        field_names = [f.name for f in output_fields]

        # Simple heuristic: split by field name patterns
        remaining = raw_output
        for i, field in enumerate(output_fields):
            if i == len(output_fields) - 1:
                outputs[field.name] = remaining.strip()
            else:
                # Try to find a natural split point
                next_field = output_fields[i + 1].name
                split_idx = remaining.lower().find(next_field.lower())
                if split_idx > 0:
                    outputs[field.name] = remaining[:split_idx].strip()
                    remaining = remaining[split_idx:]
                else:
                    # Fallback: give first line to first field
                    lines = remaining.split("\n", 1)
                    outputs[field.name] = lines[0].strip()
                    remaining = lines[1] if len(lines) > 1 else ""

        return outputs
