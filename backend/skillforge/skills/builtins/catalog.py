"""
Built-in Skills Catalog - 15 office productivity skills.
Each skill is defined as a SkillDefinition with full prompt template.
"""

from skillforge.models import (
    FieldType,
    SkillCategory,
    SkillDefinition,
    SkillField,
    SkillSettings,
)


def get_all_builtin_skills() -> list[SkillDefinition]:
    """Return all built-in skill definitions."""
    return [
        _email_composer(),
        _email_summarizer(),
        _doc_drafter(),
        _meeting_minutes(),
        _contract_reviewer(),
        _sop_generator(),
        _excel_analyzer(),
        _schedule_optimizer(),
        _slide_outliner(),
        _talking_points(),
        _jd_writer(),
        _biz_translator(),
        _proofreader(),
        _report_scheduler(),
        _deep_researcher(),
    ]


def _email_composer() -> SkillDefinition:
    return SkillDefinition(
        id="email-composer",
        name="비즈니스 이메일 작성기",
        version="2.0.0",
        author="SkillForge",
        category=SkillCategory.EMAIL,
        description="상황과 톤에 맞는 비즈니스 이메일을 한국어/영어로 작성합니다.",
        icon="email",
        inputs=[
            SkillField(name="context", type=FieldType.STRING, required=True, description="이메일 작성 상황 설명"),
            SkillField(name="tone", type=FieldType.ENUM, required=True, description="이메일 톤", values=["formal", "friendly", "urgent", "apologetic"], default="formal"),
            SkillField(name="language", type=FieldType.ENUM, required=False, description="작성 언어", values=["ko", "en", "ja"], default="ko"),
            SkillField(name="recipient", type=FieldType.STRING, required=False, description="수신자 정보"),
        ],
        outputs=[
            SkillField(name="subject", type=FieldType.STRING, description="이메일 제목"),
            SkillField(name="body", type=FieldType.STRING, description="이메일 본문"),
        ],
        prompt_template="""당신은 비즈니스 이메일 전문 작성자입니다.

[상황]
{{context}}

[요구사항]
- 톤: {{tone}}
- 언어: {{language}}
- 수신자: {{recipient}}

[출력 형식]
제목: (한 줄)

본문:
(전문적이고 상황에 적합한 이메일 본문을 작성하세요. 인사말, 본론, 맺음말을 포함합니다.)""",
        settings=SkillSettings(max_tokens=1500, temperature=0.7),
        tags=["이메일", "비즈니스", "커뮤니케이션", "email"],
        rating=4.9,
        downloads=891,
    )


def _email_summarizer() -> SkillDefinition:
    return SkillDefinition(
        id="email-summarizer",
        name="이메일 스레드 요약기",
        version="1.1.0",
        author="SkillForge",
        category=SkillCategory.EMAIL,
        description="긴 이메일 스레드를 핵심 요약하고 액션 아이템을 추출합니다.",
        icon="email",
        inputs=[
            SkillField(name="thread", type=FieldType.STRING, required=True, description="이메일 스레드 내용"),
        ],
        outputs=[
            SkillField(name="summary", type=FieldType.STRING, description="요약 결과"),
        ],
        prompt_template="""당신은 이메일 분석 전문가입니다.

아래 이메일 스레드를 분석하여 핵심 내용을 요약해주세요.

[이메일 스레드]
{{thread}}

[출력 형식]
## 3줄 요약
1.
2.
3.

## 핵심 논점
-

## 액션 아이템
| 담당자 | 항목 | 기한 |
|--------|------|------|""",
        settings=SkillSettings(max_tokens=1500, temperature=0.5),
        tags=["이메일", "요약", "생산성"],
        rating=4.5,
        downloads=367,
    )


def _doc_drafter() -> SkillDefinition:
    return SkillDefinition(
        id="doc-drafter",
        name="보고서 초안 생성기",
        version="1.2.0",
        author="SkillForge",
        category=SkillCategory.DOCUMENT,
        description="주제와 형식을 입력하면 비즈니스 보고서, 기획서, 제안서 초안을 자동으로 작성합니다.",
        icon="doc",
        inputs=[
            SkillField(name="topic", type=FieldType.STRING, required=True, description="문서 주제"),
            SkillField(name="format", type=FieldType.ENUM, required=True, description="문서 형식", values=["보고서", "기획서", "제안서", "분석서"], default="보고서"),
            SkillField(name="length", type=FieldType.ENUM, required=False, description="분량", values=["short", "medium", "long"], default="medium"),
        ],
        outputs=[
            SkillField(name="document", type=FieldType.STRING, description="생성된 문서"),
        ],
        prompt_template="""당신은 비즈니스 문서 전문 작성자입니다.

[요청]
주제: {{topic}}
형식: {{format}}
분량: {{length}}

[작성 지침]
1. 명확한 제목과 부제를 포함하세요
2. 개요, 본론, 결론 구조를 따르세요
3. 데이터와 근거를 포함하세요
4. 전문적이고 간결한 문체를 사용하세요

전문적인 {{format}} 초안을 작성해주세요.""",
        settings=SkillSettings(max_tokens=3000, temperature=0.7),
        tags=["보고서", "기획서", "문서작성", "document"],
        rating=4.8,
        downloads=523,
    )


def _meeting_minutes() -> SkillDefinition:
    return SkillDefinition(
        id="meeting-minutes",
        name="회의록 자동 정리",
        version="1.0.3",
        author="SkillForge",
        category=SkillCategory.DOCUMENT,
        description="회의 내용을 구조화된 회의록으로 변환합니다. 결정사항, 액션아이템을 자동 분류합니다.",
        icon="doc",
        inputs=[
            SkillField(name="transcript", type=FieldType.STRING, required=True, description="회의 내용 텍스트"),
        ],
        outputs=[
            SkillField(name="minutes", type=FieldType.STRING, description="구조화된 회의록"),
        ],
        prompt_template="""당신은 회의록 작성 전문가입니다.

아래 회의 내용을 분석하여 구조화된 회의록을 작성하세요.

[회의 내용]
{{transcript}}

[출력 형식]
## 회의록

**일시:**
**참석자:**

### 주요 논의사항
1.
2.

### 결정사항
-

### Action Items
| 담당자 | 항목 | 기한 | 상태 |
|--------|------|------|------|""",
        settings=SkillSettings(max_tokens=2000, temperature=0.5),
        tags=["회의록", "정리", "액션아이템"],
        rating=4.6,
        downloads=412,
    )


def _contract_reviewer() -> SkillDefinition:
    return SkillDefinition(
        id="contract-reviewer",
        name="계약서 검토 도우미",
        version="1.0.1",
        author="SkillForge",
        category=SkillCategory.DOCUMENT,
        description="계약서 조항을 검토하고 주의사항과 위험 요소를 분석합니다.",
        icon="doc",
        inputs=[
            SkillField(name="contract", type=FieldType.STRING, required=True, description="계약서 내용"),
            SkillField(name="focus", type=FieldType.STRING, required=False, description="특별 검토 관점"),
        ],
        outputs=[
            SkillField(name="review", type=FieldType.STRING, description="검토 결과"),
        ],
        prompt_template="""당신은 계약서 검토 전문가입니다.

[계약서 내용]
{{contract}}

[특별 검토 관점]
{{focus}}

다음 항목을 포함하여 검토해주세요:
1. 주요 조항 요약
2. 위험 요소 (상/중/하)
3. 수정 제안 사항
4. 특별 주의사항""",
        settings=SkillSettings(max_tokens=2500, temperature=0.3),
        tags=["계약서", "검토", "법무"],
        rating=4.5,
        downloads=289,
    )


def _sop_generator() -> SkillDefinition:
    return SkillDefinition(
        id="sop-generator",
        name="SOP 문서 생성기",
        version="1.0.0",
        author="SkillForge",
        category=SkillCategory.DOCUMENT,
        description="프로세스를 설명하면 표준운영절차서(SOP)를 자동 생성합니다.",
        icon="doc",
        inputs=[
            SkillField(name="process_name", type=FieldType.STRING, required=True, description="프로세스명"),
            SkillField(name="process_desc", type=FieldType.STRING, required=True, description="프로세스 설명"),
            SkillField(name="audience", type=FieldType.STRING, required=False, description="대상 독자"),
        ],
        outputs=[
            SkillField(name="sop", type=FieldType.STRING, description="SOP 문서"),
        ],
        prompt_template="""당신은 프로세스 문서화 전문가입니다.

[프로세스명] {{process_name}}
[프로세스 설명] {{process_desc}}
[대상 독자] {{audience}}

표준 SOP 형식으로 작성해주세요:
1. 목적
2. 적용 범위
3. 용어 정의
4. 책임과 권한
5. 절차 (단계별 상세)
6. 관련 양식
7. 개정 이력""",
        settings=SkillSettings(max_tokens=3000, temperature=0.5),
        tags=["SOP", "절차서", "매뉴얼"],
        rating=4.3,
        downloads=201,
    )


def _excel_analyzer() -> SkillDefinition:
    return SkillDefinition(
        id="excel-analyzer",
        name="데이터 분석 어시스턴트",
        version="1.3.0",
        author="SkillForge",
        category=SkillCategory.DATA,
        description="CSV/엑셀 데이터를 분석하여 인사이트와 시각화 제안을 제공합니다.",
        icon="chart",
        inputs=[
            SkillField(name="data", type=FieldType.STRING, required=True, description="CSV 또는 표 데이터"),
            SkillField(name="perspective", type=FieldType.STRING, required=False, description="분석 관점/질문"),
        ],
        outputs=[
            SkillField(name="analysis", type=FieldType.STRING, description="분석 결과"),
        ],
        prompt_template="""당신은 데이터 분석 전문가입니다.

[데이터]
{{data}}

[분석 관점]
{{perspective}}

다음을 포함하여 분석해주세요:
1. 주요 통계 수치
2. 트렌드 및 패턴
3. 이상치 탐지
4. 시각화 추천 (차트 유형 제안)
5. 실행 가능한 인사이트""",
        settings=SkillSettings(max_tokens=2500, temperature=0.4),
        tags=["데이터", "분석", "엑셀", "인사이트"],
        rating=4.7,
        downloads=645,
    )


def _schedule_optimizer() -> SkillDefinition:
    return SkillDefinition(
        id="schedule-optimizer",
        name="일정 최적화 도우미",
        version="1.0.0",
        author="SkillForge",
        category=SkillCategory.SCHEDULE,
        description="일정 충돌을 감지하고 최적의 스케줄을 제안합니다.",
        icon="calendar",
        inputs=[
            SkillField(name="schedules", type=FieldType.STRING, required=True, description="일정 목록"),
            SkillField(name="priorities", type=FieldType.STRING, required=False, description="우선순위 설정"),
        ],
        outputs=[
            SkillField(name="optimized", type=FieldType.STRING, description="최적화된 일정"),
        ],
        prompt_template="""당신은 일정 관리 전문가입니다.

[일정 목록]
{{schedules}}

[우선순위]
{{priorities}}

다음을 수행해주세요:
1. 일정 충돌 감지
2. 우선순위 기반 최적 배치
3. 여유 시간 확보 제안
4. 최종 최적화 일정표 출력""",
        settings=SkillSettings(max_tokens=1500, temperature=0.4),
        tags=["일정", "스케줄", "최적화"],
        rating=4.3,
        downloads=198,
    )


def _slide_outliner() -> SkillDefinition:
    return SkillDefinition(
        id="slide-outliner",
        name="PPT 구조 설계기",
        version="1.1.0",
        author="SkillForge",
        category=SkillCategory.PRESENTATION,
        description="주제에 맞는 프레젠테이션 슬라이드 구조와 내용을 설계합니다.",
        icon="slide",
        inputs=[
            SkillField(name="topic", type=FieldType.STRING, required=True, description="발표 주제"),
            SkillField(name="audience", type=FieldType.STRING, required=False, description="청중 정보"),
            SkillField(name="duration", type=FieldType.STRING, required=False, description="발표 시간(분)"),
        ],
        outputs=[
            SkillField(name="outline", type=FieldType.STRING, description="슬라이드 구조"),
        ],
        prompt_template="""당신은 프레젠테이션 전문가입니다.

[발표 주제] {{topic}}
[청중] {{audience}}
[발표 시간] {{duration}}분

각 슬라이드별로 다음을 포함하여 구조를 설계해주세요:
- 슬라이드 번호 및 제목
- 핵심 내용 (3-5 bullet points)
- 시각자료 제안 (차트, 이미지, 다이어그램)
- 발표자 노트""",
        settings=SkillSettings(max_tokens=2500, temperature=0.7),
        tags=["PPT", "프레젠테이션", "슬라이드"],
        rating=4.4,
        downloads=312,
    )


def _talking_points() -> SkillDefinition:
    return SkillDefinition(
        id="talking-points",
        name="발표 스크립트 생성기",
        version="1.0.0",
        author="SkillForge",
        category=SkillCategory.PRESENTATION,
        description="슬라이드 내용을 기반으로 발표용 스크립트를 생성합니다.",
        icon="slide",
        inputs=[
            SkillField(name="slides", type=FieldType.STRING, required=True, description="슬라이드 내용"),
            SkillField(name="duration", type=FieldType.STRING, required=False, description="발표 시간(분)"),
            SkillField(name="audience", type=FieldType.STRING, required=False, description="청중 정보"),
        ],
        outputs=[
            SkillField(name="script", type=FieldType.STRING, description="발표 스크립트"),
        ],
        prompt_template="""당신은 발표 코칭 전문가입니다.

[슬라이드 내용]
{{slides}}

[발표 시간] {{duration}}분
[청중] {{audience}}

자연스럽고 설득력 있는 발표 스크립트를 작성해주세요.
각 슬라이드별 발표 멘트, 전환 문구, 강조 포인트를 포함합니다.""",
        settings=SkillSettings(max_tokens=2500, temperature=0.7),
        tags=["발표", "스크립트", "프레젠테이션"],
        rating=4.4,
        downloads=245,
    )


def _jd_writer() -> SkillDefinition:
    return SkillDefinition(
        id="jd-writer",
        name="채용공고 작성기",
        version="1.0.0",
        author="SkillForge",
        category=SkillCategory.HR,
        description="직무 요건을 입력하면 매력적인 채용공고를 작성합니다.",
        icon="person",
        inputs=[
            SkillField(name="position", type=FieldType.STRING, required=True, description="직무명"),
            SkillField(name="requirements", type=FieldType.STRING, required=True, description="요구사항"),
            SkillField(name="company", type=FieldType.STRING, required=False, description="회사 소개"),
        ],
        outputs=[
            SkillField(name="jd", type=FieldType.STRING, description="채용공고"),
        ],
        prompt_template="""당신은 HR 채용 전문가입니다.

[직무] {{position}}
[요구사항] {{requirements}}
[회사 소개] {{company}}

매력적이고 명확한 채용공고를 작성해주세요:
1. 포지션 소개
2. 주요 업무
3. 자격 요건 (필수/우대)
4. 복리후생
5. 지원 방법""",
        settings=SkillSettings(max_tokens=2000, temperature=0.7),
        tags=["채용", "HR", "채용공고"],
        rating=4.2,
        downloads=156,
    )


def _biz_translator() -> SkillDefinition:
    return SkillDefinition(
        id="biz-translator",
        name="비즈니스 문서 번역기",
        version="2.1.0",
        author="SkillForge",
        category=SkillCategory.TRANSLATION,
        description="비즈니스 맥락을 이해하는 전문 번역. 한/영/일 지원.",
        icon="globe",
        inputs=[
            SkillField(name="source_text", type=FieldType.STRING, required=True, description="원문"),
            SkillField(name="source_lang", type=FieldType.ENUM, required=True, description="원문 언어", values=["ko", "en", "ja"], default="ko"),
            SkillField(name="target_lang", type=FieldType.ENUM, required=True, description="번역 언어", values=["ko", "en", "ja"], default="en"),
            SkillField(name="doc_type", type=FieldType.STRING, required=False, description="문서 유형"),
        ],
        outputs=[
            SkillField(name="translation", type=FieldType.STRING, description="번역문"),
        ],
        prompt_template="""당신은 비즈니스 문서 전문 번역가입니다.

[원문] ({{source_lang}})
{{source_text}}

[번역 방향] {{source_lang}} → {{target_lang}}
[문서 유형] {{doc_type}}

비즈니스 맥락에 맞는 자연스러운 번역을 해주세요.
전문 용어는 해당 분야의 표준 번역을 사용합니다.""",
        settings=SkillSettings(max_tokens=3000, temperature=0.3),
        tags=["번역", "비즈니스", "다국어"],
        rating=4.7,
        downloads=734,
    )


def _proofreader() -> SkillDefinition:
    return SkillDefinition(
        id="proofreader",
        name="문서 교정기",
        version="1.2.0",
        author="SkillForge",
        category=SkillCategory.TRANSLATION,
        description="맞춤법, 문법, 문체를 교정하고 개선 제안을 합니다.",
        icon="brain",
        inputs=[
            SkillField(name="text", type=FieldType.STRING, required=True, description="교정할 텍스트"),
            SkillField(name="level", type=FieldType.ENUM, required=False, description="교정 수준", values=["basic", "standard", "thorough"], default="standard"),
        ],
        outputs=[
            SkillField(name="corrected", type=FieldType.STRING, description="교정 결과"),
        ],
        prompt_template="""당신은 전문 교정 편집자입니다.

[원문]
{{text}}

[교정 수준] {{level}}

다음을 포함하여 교정해주세요:
1. 맞춤법/문법 오류 수정
2. 문체 개선 제안
3. 가독성 향상
각 수정사항에 대한 이유를 간단히 설명해주세요.""",
        settings=SkillSettings(max_tokens=2000, temperature=0.3),
        tags=["교정", "맞춤법", "문법"],
        rating=4.6,
        downloads=567,
    )


def _report_scheduler() -> SkillDefinition:
    return SkillDefinition(
        id="report-scheduler",
        name="정기 보고서 자동화",
        version="1.0.0",
        author="SkillForge",
        category=SkillCategory.AUTOMATION,
        description="데이터 소스와 템플릿을 설정하면 정기 보고서를 자동 생성합니다.",
        icon="gear",
        inputs=[
            SkillField(name="data_source", type=FieldType.STRING, required=True, description="데이터 소스"),
            SkillField(name="template", type=FieldType.STRING, required=True, description="보고서 템플릿"),
            SkillField(name="period", type=FieldType.STRING, required=False, description="보고 기간"),
        ],
        outputs=[
            SkillField(name="report", type=FieldType.STRING, description="생성된 보고서"),
        ],
        prompt_template="""당신은 보고서 자동화 엔진입니다.

[데이터 소스]
{{data_source}}

[보고서 템플릿]
{{template}}

[보고 기간] {{period}}

주어진 데이터를 분석하여 템플릿에 맞는 보고서를 생성해주세요.
수치 데이터는 정확히 반영하고, 트렌드 분석을 포함하세요.""",
        settings=SkillSettings(max_tokens=3000, temperature=0.5),
        tags=["자동화", "보고서", "정기"],
        rating=4.1,
        downloads=134,
    )


def _deep_researcher() -> SkillDefinition:
    return SkillDefinition(
        id="deep-researcher",
        name="웹검색 심층분석기",
        version="1.0.0",
        author="SkillForge",
        category=SkillCategory.KNOWLEDGE,
        description="웹 검색을 통해 다양한 소스에서 정보를 수집하고, 심층 분석 보고서를 자동 생성합니다. 시장 조사, 경쟁 분석, 트렌드 리서치에 활용합니다.",
        icon="search",
        inputs=[
            SkillField(name="topic", type=FieldType.STRING, required=True, description="리서치 주제 또는 질문"),
            SkillField(name="depth", type=FieldType.ENUM, required=False, description="분석 깊이", values=["quick", "standard", "deep"], default="standard"),
            SkillField(name="perspective", type=FieldType.STRING, required=False, description="분석 관점 (예: 기술적, 비즈니스, 경쟁사 비교)"),
            SkillField(name="output_format", type=FieldType.ENUM, required=False, description="출력 형식", values=["보고서", "브리핑", "SWOT", "비교분석"], default="보고서"),
            SkillField(name="language", type=FieldType.ENUM, required=False, description="출력 언어", values=["ko", "en", "ja"], default="ko"),
        ],
        outputs=[
            SkillField(name="report", type=FieldType.STRING, description="심층 분석 보고서"),
            SkillField(name="sources", type=FieldType.ARRAY, description="참고 자료 목록"),
        ],
        prompt_template="""당신은 심층 리서치 분석가입니다. 웹 검색 결과를 바탕으로 전문적인 분석 보고서를 작성합니다.

[연구 주제]
{{topic}}

[분석 깊이] {{depth}}
[분석 관점] {{perspective}}
[출력 형식] {{output_format}}
[언어] {{language}}

※ 이 스킬은 웹 검색 엔진과 연동하여 실시간 데이터를 수집한 뒤,
   LLM을 통해 종합 분석 보고서를 자동 생성합니다.

다음 단계로 심층 분석을 수행합니다:
1. 쿼리 확장: 주제를 다각적으로 분석하기 위한 하위 검색 쿼리 생성
2. 웹 검색: 다중 소스(Brave/Google/DuckDuckGo) 검색 실행
3. 콘텐츠 추출: 상위 결과에서 핵심 내용 추출
4. 종합 분석: 수집된 자료를 기반으로 심층 분석 보고서 작성""",
        settings=SkillSettings(max_tokens=4000, temperature=0.5, timeout_ms=60000),
        permissions=["web_search"],
        tags=["리서치", "검색", "분석", "시장조사", "트렌드", "경쟁분석", "심층분석", "web search", "research"],
        rating=4.8,
        downloads=456,
    )
