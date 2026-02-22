// ===========================
// Data Store
// ===========================
const ICONS = {
  doc: '\u{1F4C4}', email: '\u2709', chart: '\u{1F4C8}', calendar: '\u{1F4C5}',
  slide: '\u{1F3AC}', person: '\u{1F464}', globe: '\u{1F310}', gear: '\u2699',
  brain: '\u{1F9E0}', rocket: '\u{1F680}'
};

const SKILLS_DATA = [
  {
    id: 'doc-drafter', name: '보고서 초안 생성기', category: 'document',
    description: '주제와 형식을 입력하면 비즈니스 보고서, 기획서, 제안서 초안을 자동으로 작성합니다.',
    icon: 'doc', version: '1.2.0', author: 'SkillForge Team',
    rating: 4.8, downloads: 523, tags: ['보고서', '기획서', '문서작성'],
    featured: true,
    prompt: '당신은 비즈니스 문서 전문 작성자입니다.\n\n주제: {{topic}}\n형식: {{format}}\n분량: {{length}}\n\n위 조건에 맞는 전문적인 문서 초안을 작성해주세요.',
    inputs: [
      { name: 'topic', type: 'string', required: true, desc: '문서 주제' },
      { name: 'format', type: 'enum', required: true, desc: '문서 형식 (보고서/기획서/제안서)' },
      { name: 'length', type: 'enum', required: false, desc: '분량 (short/medium/long)' }
    ],
    outputs: [{ name: 'document', type: 'string', desc: '생성된 문서' }]
  },
  {
    id: 'meeting-minutes', name: '회의록 자동 정리', category: 'document',
    description: '회의 내용을 구조화된 회의록으로 변환합니다. 결정사항, 액션아이템을 자동 분류합니다.',
    icon: 'doc', version: '1.0.3', author: 'OfficeBot',
    rating: 4.6, downloads: 412, tags: ['회의록', '정리', '액션아이템'],
    featured: true,
    prompt: '회의 내용을 분석하여 구조화된 회의록을 작성하세요.\n\n회의 내용: {{transcript}}\n\n다음 항목을 포함해주세요:\n1. 참석자\n2. 주요 논의 사항\n3. 결정 사항\n4. 액션 아이템 (담당자, 기한 포함)',
    inputs: [{ name: 'transcript', type: 'string', required: true, desc: '회의 내용 텍스트' }],
    outputs: [{ name: 'minutes', type: 'object', desc: '구조화된 회의록' }]
  },
  {
    id: 'email-composer', name: '비즈니스 이메일 작성기', category: 'email',
    description: '상황과 톤에 맞는 비즈니스 이메일을 한국어/영어로 작성합니다.',
    icon: 'email', version: '2.0.0', author: 'SkillForge Team',
    rating: 4.9, downloads: 891, tags: ['이메일', '비즈니스', '커뮤니케이션'],
    featured: true,
    prompt: '비즈니스 이메일 전문가로서 다음 상황에 맞는 이메일을 작성하세요.\n\n상황: {{context}}\n톤: {{tone}}\n언어: {{language}}\n수신자: {{recipient}}',
    inputs: [
      { name: 'context', type: 'string', required: true, desc: '이메일 작성 상황' },
      { name: 'tone', type: 'enum', required: true, desc: 'formal/friendly/urgent/apologetic' },
      { name: 'language', type: 'enum', required: false, desc: 'ko/en/ja' },
      { name: 'recipient', type: 'string', required: false, desc: '수신자 정보' }
    ],
    outputs: [
      { name: 'subject', type: 'string', desc: '이메일 제목' },
      { name: 'body', type: 'string', desc: '이메일 본문' }
    ]
  },
  {
    id: 'email-summarizer', name: '이메일 스레드 요약기', category: 'email',
    description: '긴 이메일 스레드를 핵심 요약하고 액션 아이템을 추출합니다.',
    icon: 'email', version: '1.1.0', author: 'ProductivityLab',
    rating: 4.5, downloads: 367, tags: ['이메일', '요약', '생산성'],
    featured: false,
    prompt: '이메일 스레드를 분석하여 핵심 내용을 요약해주세요.\n\n이메일 스레드:\n{{thread}}\n\n출력:\n1. 3줄 요약\n2. 핵심 논점\n3. 필요한 액션 아이템',
    inputs: [{ name: 'thread', type: 'string', required: true, desc: '이메일 스레드 내용' }],
    outputs: [{ name: 'summary', type: 'object', desc: '요약 결과' }]
  },
  {
    id: 'excel-analyzer', name: '데이터 분석 어시스턴트', category: 'data',
    description: 'CSV/엑셀 데이터를 분석하여 인사이트와 시각화 제안을 제공합니다.',
    icon: 'chart', version: '1.3.0', author: 'DataWizard',
    rating: 4.7, downloads: 645, tags: ['데이터', '분석', '엑셀', '인사이트'],
    featured: true,
    prompt: '데이터 분석 전문가로서 다음 데이터를 분석해주세요.\n\n데이터:\n{{data}}\n\n분석 관점: {{perspective}}\n\n다음을 포함해주세요:\n1. 주요 통계 수치\n2. 트렌드 및 패턴\n3. 이상치\n4. 시각화 추천',
    inputs: [
      { name: 'data', type: 'string', required: true, desc: 'CSV 또는 표 데이터' },
      { name: 'perspective', type: 'string', required: false, desc: '분석 관점/질문' }
    ],
    outputs: [{ name: 'analysis', type: 'object', desc: '분석 결과' }]
  },
  {
    id: 'schedule-optimizer', name: '일정 최적화 도우미', category: 'schedule',
    description: '일정 충돌을 감지하고 최적의 스케줄을 제안합니다.',
    icon: 'calendar', version: '1.0.0', author: 'TimeMaster',
    rating: 4.3, downloads: 198, tags: ['일정', '스케줄', '최적화'],
    featured: false,
    prompt: '일정 관리 전문가로서 다음 일정을 최적화해주세요.\n\n일정 목록:\n{{schedules}}\n\n우선순위:\n{{priorities}}\n\n충돌 감지 후 최적의 배치를 제안해주세요.',
    inputs: [
      { name: 'schedules', type: 'array', required: true, desc: '일정 목록' },
      { name: 'priorities', type: 'object', required: false, desc: '우선순위 설정' }
    ],
    outputs: [{ name: 'optimized', type: 'object', desc: '최적화된 일정' }]
  },
  {
    id: 'slide-outliner', name: 'PPT 구조 설계기', category: 'presentation',
    description: '주제에 맞는 프레젠테이션 슬라이드 구조와 내용을 설계합니다.',
    icon: 'slide', version: '1.1.0', author: 'PresentPro',
    rating: 4.4, downloads: 312, tags: ['PPT', '프레젠테이션', '슬라이드'],
    featured: false,
    prompt: '프레젠테이션 전문가로서 다음 주제의 슬라이드 구조를 설계해주세요.\n\n주제: {{topic}}\n청중: {{audience}}\n시간: {{duration}}분\n\n각 슬라이드별 제목, 핵심 내용, 시각자료 제안을 포함해주세요.',
    inputs: [
      { name: 'topic', type: 'string', required: true, desc: '발표 주제' },
      { name: 'audience', type: 'string', required: false, desc: '청중 정보' },
      { name: 'duration', type: 'number', required: false, desc: '발표 시간(분)' }
    ],
    outputs: [{ name: 'outline', type: 'array', desc: '슬라이드 구조' }]
  },
  {
    id: 'jd-writer', name: '채용공고 작성기', category: 'hr',
    description: '직무 요건을 입력하면 매력적인 채용공고를 작성합니다.',
    icon: 'person', version: '1.0.0', author: 'HRHelper',
    rating: 4.2, downloads: 156, tags: ['채용', 'HR', '채용공고'],
    featured: false,
    prompt: 'HR 전문가로서 매력적인 채용공고를 작성해주세요.\n\n직무: {{position}}\n요건: {{requirements}}\n회사 소개: {{company}}\n\n구직자의 관점에서 매력적이고 명확한 JD를 작성해주세요.',
    inputs: [
      { name: 'position', type: 'string', required: true, desc: '직무명' },
      { name: 'requirements', type: 'string', required: true, desc: '요구사항' },
      { name: 'company', type: 'string', required: false, desc: '회사 소개' }
    ],
    outputs: [{ name: 'jd', type: 'string', desc: '채용공고' }]
  },
  {
    id: 'biz-translator', name: '비즈니스 문서 번역기', category: 'translation',
    description: '비즈니스 맥락을 이해하는 전문 번역. 한/영/일 지원.',
    icon: 'globe', version: '2.1.0', author: 'SkillForge Team',
    rating: 4.7, downloads: 734, tags: ['번역', '비즈니스', '다국어'],
    featured: true,
    prompt: '비즈니스 문서 전문 번역가로서 다음 문서를 번역해주세요.\n\n원문:\n{{source_text}}\n\n번역 방향: {{source_lang}} → {{target_lang}}\n문서 유형: {{doc_type}}\n\n비즈니스 맥락에 맞는 자연스러운 번역을 해주세요.',
    inputs: [
      { name: 'source_text', type: 'string', required: true, desc: '원문' },
      { name: 'source_lang', type: 'enum', required: true, desc: '원문 언어' },
      { name: 'target_lang', type: 'enum', required: true, desc: '번역 언어' },
      { name: 'doc_type', type: 'string', required: false, desc: '문서 유형' }
    ],
    outputs: [{ name: 'translation', type: 'string', desc: '번역문' }]
  },
  {
    id: 'contract-reviewer', name: '계약서 검토 도우미', category: 'document',
    description: '계약서 조항을 검토하고 주의사항과 위험 요소를 분석합니다.',
    icon: 'doc', version: '1.0.1', author: 'LegalAssist',
    rating: 4.5, downloads: 289, tags: ['계약서', '검토', '법무'],
    featured: false,
    prompt: '계약서 검토 전문가로서 다음 계약서를 분석해주세요.\n\n계약서 내용:\n{{contract}}\n\n검토 관점: {{focus}}\n\n다음을 포함해주세요:\n1. 주요 조항 요약\n2. 위험 요소\n3. 수정 제안\n4. 주의사항',
    inputs: [
      { name: 'contract', type: 'string', required: true, desc: '계약서 내용' },
      { name: 'focus', type: 'string', required: false, desc: '특별 검토 관점' }
    ],
    outputs: [{ name: 'review', type: 'object', desc: '검토 결과' }]
  },
  {
    id: 'report-scheduler', name: '정기 보고서 자동화', category: 'automation',
    description: '데이터 소스와 템플릿을 설정하면 정기 보고서를 자동 생성합니다.',
    icon: 'gear', version: '1.0.0', author: 'AutoFlow',
    rating: 4.1, downloads: 134, tags: ['자동화', '보고서', '정기'],
    featured: false,
    prompt: '보고서 자동화 엔진입니다.\n\n데이터 소스: {{data_source}}\n보고서 템플릿: {{template}}\n기간: {{period}}\n\n주어진 데이터를 분석하여 템플릿에 맞는 보고서를 생성해주세요.',
    inputs: [
      { name: 'data_source', type: 'string', required: true, desc: '데이터 소스' },
      { name: 'template', type: 'string', required: true, desc: '보고서 템플릿' },
      { name: 'period', type: 'string', required: false, desc: '보고 기간' }
    ],
    outputs: [{ name: 'report', type: 'string', desc: '생성된 보고서' }]
  },
  {
    id: 'proofreader', name: '문서 교정기', category: 'translation',
    description: '맞춤법, 문법, 문체를 교정하고 개선 제안을 합니다.',
    icon: 'brain', version: '1.2.0', author: 'WriteBetter',
    rating: 4.6, downloads: 567, tags: ['교정', '맞춤법', '문법'],
    featured: false,
    prompt: '전문 교정 편집자로서 다음 텍스트를 교정해주세요.\n\n원문:\n{{text}}\n\n교정 수준: {{level}}\n\n1. 맞춤법/문법 오류\n2. 문체 개선\n3. 가독성 향상\n각 수정사항에 대한 이유를 설명해주세요.',
    inputs: [
      { name: 'text', type: 'string', required: true, desc: '교정할 텍스트' },
      { name: 'level', type: 'enum', required: false, desc: 'basic/standard/thorough' }
    ],
    outputs: [{ name: 'corrected', type: 'object', desc: '교정 결과' }]
  },
  {
    id: 'sop-generator', name: 'SOP 문서 생성기', category: 'document',
    description: '프로세스를 설명하면 표준운영절차서(SOP)를 자동 생성합니다.',
    icon: 'doc', version: '1.0.0', author: 'ProcessPro',
    rating: 4.3, downloads: 201, tags: ['SOP', '절차서', '매뉴얼'],
    featured: false,
    prompt: '프로세스 문서화 전문가로서 SOP를 작성해주세요.\n\n프로세스명: {{process_name}}\n프로세스 설명: {{process_desc}}\n대상: {{audience}}\n\n표준 SOP 형식으로 작성해주세요.',
    inputs: [
      { name: 'process_name', type: 'string', required: true, desc: '프로세스명' },
      { name: 'process_desc', type: 'string', required: true, desc: '프로세스 설명' },
      { name: 'audience', type: 'string', required: false, desc: '대상 독자' }
    ],
    outputs: [{ name: 'sop', type: 'string', desc: 'SOP 문서' }]
  },
  {
    id: 'talking-points', name: '발표 스크립트 생성기', category: 'presentation',
    description: '슬라이드 내용을 기반으로 발표용 스크립트를 생성합니다.',
    icon: 'slide', version: '1.0.0', author: 'PresentPro',
    rating: 4.4, downloads: 245, tags: ['발표', '스크립트', '프레젠테이션'],
    featured: false,
    prompt: '발표 코칭 전문가로서 발표 스크립트를 작성해주세요.\n\n슬라이드 내용:\n{{slides}}\n\n발표 시간: {{duration}}분\n청중: {{audience}}\n\n자연스럽고 설득력 있는 발표 스크립트를 작성해주세요.',
    inputs: [
      { name: 'slides', type: 'string', required: true, desc: '슬라이드 내용' },
      { name: 'duration', type: 'number', required: false, desc: '발표 시간(분)' },
      { name: 'audience', type: 'string', required: false, desc: '청중 정보' }
    ],
    outputs: [{ name: 'script', type: 'string', desc: '발표 스크립트' }]
  }
];

// State
let installedSkills = new Set(['email-composer', 'doc-drafter']);
let draftSkills = [];
let selectedIcon = 'doc';
let currentCategory = 'all';
let currentSort = 'popular';

// ===========================
// Navigation
// ===========================
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

  document.getElementById(`page-${page}`).classList.add('active');
  const link = document.querySelector(`.nav-link[data-page="${page}"]`);
  if (link) link.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (page === 'store') renderStore();
  if (page === 'myskills') renderMySkills();
  if (page === 'docs') showDoc('overview');
}

// ===========================
// Store Page
// ===========================
function renderStore() {
  renderFeatured();
  renderAllSkills();
}

function renderFeatured() {
  const grid = document.getElementById('featuredGrid');
  const featured = SKILLS_DATA.filter(s => s.featured);
  grid.innerHTML = featured.map(skill => renderSkillCard(skill, true)).join('');
}

function renderAllSkills() {
  const grid = document.getElementById('allSkillsGrid');
  let skills = [...SKILLS_DATA];

  if (currentCategory !== 'all') {
    skills = skills.filter(s => s.category === currentCategory);
  }

  skills = sortSkillsArray(skills, currentSort);
  grid.innerHTML = skills.map(skill => renderSkillCard(skill, false)).join('');
}

function renderSkillCard(skill, showFeatured) {
  const isInstalled = installedSkills.has(skill.id);
  return `
    <div class="skill-card" onclick="openSkillDetail('${skill.id}')">
      ${showFeatured ? '<span class="badge-featured">Featured</span>' : ''}
      <div class="skill-card-header">
        <span class="skill-icon">${ICONS[skill.icon] || ICONS.doc}</span>
        <div>
          <h4>${skill.name}</h4>
          <span class="skill-category">${skill.category}</span>
        </div>
      </div>
      <p class="skill-desc">${skill.description}</p>
      <div class="skill-card-footer">
        <div class="skill-stats">
          <span class="skill-rating">\u2605 ${skill.rating}</span>
          <span>\u2B07 ${skill.downloads}</span>
          <span class="skill-version">v${skill.version}</span>
        </div>
        <button class="btn-install ${isInstalled ? 'installed' : 'install'}"
                onclick="event.stopPropagation(); ${isInstalled ? '' : `installSkill('${skill.id}')`}">
          ${isInstalled ? '\u2713 Installed' : 'Install'}
        </button>
      </div>
    </div>
  `;
}

function filterCategory(cat, el) {
  currentCategory = cat;
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  renderAllSkills();
}

function sortSkills(value) {
  currentSort = value;
  renderAllSkills();
}

function sortSkillsArray(skills, sort) {
  switch (sort) {
    case 'popular': return skills.sort((a, b) => b.downloads - a.downloads);
    case 'recent': return skills.sort((a, b) => b.version.localeCompare(a.version));
    case 'rating': return skills.sort((a, b) => b.rating - a.rating);
    case 'name': return skills.sort((a, b) => a.name.localeCompare(b.name));
    default: return skills;
  }
}

function handleSearch(query) {
  if (!query.trim()) {
    renderAllSkills();
    return;
  }
  const q = query.toLowerCase();
  const grid = document.getElementById('allSkillsGrid');
  const results = SKILLS_DATA.filter(s =>
    s.name.toLowerCase().includes(q) ||
    s.description.toLowerCase().includes(q) ||
    s.tags.some(t => t.toLowerCase().includes(q)) ||
    s.category.toLowerCase().includes(q)
  );
  grid.innerHTML = results.map(s => renderSkillCard(s, false)).join('');
}

function installSkill(id) {
  installedSkills.add(id);
  renderStore();
  showToast(`Skill installed successfully!`, 'success');
}

// ===========================
// Skill Detail Modal
// ===========================
function openSkillDetail(id) {
  const skill = SKILLS_DATA.find(s => s.id === id);
  if (!skill) return;
  const isInstalled = installedSkills.has(skill.id);

  document.getElementById('modalContent').innerHTML = `
    <div class="modal-skill-header">
      <span class="modal-skill-icon">${ICONS[skill.icon]}</span>
      <div class="modal-skill-title">
        <h2>${skill.name}</h2>
        <span class="skill-category">${skill.category} \u00b7 v${skill.version} \u00b7 by ${skill.author}</span>
      </div>
    </div>
    <div class="modal-skill-meta">
      <div class="modal-meta-item">
        <span class="value">\u2605 ${skill.rating}</span>
        <span class="label">Rating</span>
      </div>
      <div class="modal-meta-item">
        <span class="value">${skill.downloads}</span>
        <span class="label">Installs</span>
      </div>
      <div class="modal-meta-item">
        <span class="value">${skill.inputs.length}</span>
        <span class="label">Inputs</span>
      </div>
      <div class="modal-meta-item">
        <span class="value">${skill.outputs.length}</span>
        <span class="label">Outputs</span>
      </div>
    </div>
    <p class="modal-desc">${skill.description}</p>

    <h3 style="font-size:14px; margin-bottom:8px; color:var(--text-secondary);">Inputs</h3>
    <div style="margin-bottom:16px;">
      ${skill.inputs.map(inp => `
        <div style="display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid var(--border-light); font-size:13px;">
          <code style="color:var(--accent); font-family:var(--font-mono); min-width:100px;">${inp.name}</code>
          <span style="color:var(--text-tertiary); font-size:12px;">${inp.type}</span>
          ${inp.required ? '<span style="color:var(--error); font-size:11px;">required</span>' : ''}
          <span style="color:var(--text-secondary); margin-left:auto; font-size:12px;">${inp.desc}</span>
        </div>
      `).join('')}
    </div>

    <h3 style="font-size:14px; margin-bottom:8px; color:var(--text-secondary);">Prompt Preview</h3>
    <pre style="background:var(--bg-primary); border:1px solid var(--border-light); border-radius:var(--radius-md); padding:12px; font-family:var(--font-mono); font-size:12px; color:var(--text-secondary); white-space:pre-wrap; margin-bottom:16px; max-height:150px; overflow-y:auto;">${escapeHtml(skill.prompt)}</pre>

    <div class="modal-tags">
      ${skill.tags.map(t => `<span class="modal-tag">${t}</span>`).join('')}
    </div>
    <div class="modal-actions">
      <button class="btn-secondary" onclick="forkSkill('${skill.id}')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 17l5-5-5-5"/><path d="M17 7v10"/></svg>
        Fork & Edit
      </button>
      <button class="btn-primary ${isInstalled ? '' : ''}" onclick="${isInstalled ? `uninstallSkill('${skill.id}')` : `installSkill('${skill.id}')`}; closeModal();">
        ${isInstalled ? 'Uninstall' : 'Install Skill'}
      </button>
    </div>
  `;
  document.getElementById('skillModal').classList.add('active');
}

function closeModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('skillModal').classList.remove('active');
}

function uninstallSkill(id) {
  installedSkills.delete(id);
  renderStore();
  showToast('Skill uninstalled', 'info');
}

function forkSkill(id) {
  const skill = SKILLS_DATA.find(s => s.id === id);
  if (!skill) return;
  closeModal();
  navigate('editor');

  setTimeout(() => {
    document.getElementById('skillName').value = skill.id + '-fork';
    document.getElementById('skillDisplayName').value = skill.name + ' (Fork)';
    document.getElementById('skillCategory').value = skill.category;
    document.getElementById('skillDescription').value = skill.description;
    document.getElementById('skillPrompt').value = skill.prompt;
    document.getElementById('skillTags').value = skill.tags.join(', ');
    selectIcon(skill.icon, document.querySelector(`.icon-option[data-icon="${skill.icon}"]`));
    switchEditorTab('meta', document.querySelector('.editor-tab'));
    updatePreview();
    highlightVariables();
    showToast('Skill forked! Edit and make it your own.', 'success');
  }, 100);
}

// ===========================
// Editor
// ===========================
function switchEditorTab(tab, el) {
  document.querySelectorAll('.editor-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.editor-tab-content').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
}

function selectIcon(icon, el) {
  selectedIcon = icon;
  document.querySelectorAll('.icon-option').forEach(o => o.classList.remove('selected'));
  if (el) el.classList.add('selected');
  updatePreview();
}

function updatePreview() {
  const name = document.getElementById('skillDisplayName').value || 'Skill Name';
  const cat = document.getElementById('skillCategory').value || 'category';
  const desc = document.getElementById('skillDescription').value || 'Add a description to see it here...';
  const ver = document.getElementById('skillVersion').value || '1.0.0';

  document.getElementById('previewName').textContent = name;
  document.getElementById('previewCategory').textContent = cat;
  document.getElementById('previewDesc').textContent = desc;
  document.getElementById('previewVersion').textContent = `v${ver}`;
  document.getElementById('previewIcon').textContent = ICONS[selectedIcon] || ICONS.doc;

  generateYAML();
}

function highlightVariables() {
  const prompt = document.getElementById('skillPrompt').value;
  const vars = [...new Set((prompt.match(/\{\{(\w+)\}\}/g) || []).map(v => v.replace(/\{|\}/g, '')))];
  const container = document.getElementById('detectedVars');
  container.innerHTML = vars.length
    ? `<span style="font-size:11px;color:var(--text-tertiary);margin-right:4px;">Detected:</span>` +
      vars.map(v => `<span class="prompt-var-tag">{{${v}}}</span>`).join('')
    : '';
}

function generateYAML() {
  const name = document.getElementById('skillName').value || 'my-skill';
  const displayName = document.getElementById('skillDisplayName').value || '';
  const cat = document.getElementById('skillCategory').value || '';
  const desc = document.getElementById('skillDescription').value || '';
  const ver = document.getElementById('skillVersion').value || '1.0.0';
  const tags = document.getElementById('skillTags').value;
  const prompt = document.getElementById('skillPrompt').value || '';
  const maxTokens = document.getElementById('skillMaxTokens').value || 2000;
  const temp = document.getElementById('skillTemp').value || 0.7;

  const inputs = collectIOFields('input');
  const outputs = collectIOFields('output');

  let yaml = `skill:\n`;
  yaml += `  id: "${name}"\n`;
  yaml += `  name: "${displayName}"\n`;
  yaml += `  version: "${ver}"\n`;
  yaml += `  category: "${cat}"\n`;
  yaml += `  description: "${desc}"\n`;
  yaml += `  icon: "${selectedIcon}"\n\n`;

  if (inputs.length) {
    yaml += `  inputs:\n`;
    inputs.forEach(inp => {
      yaml += `    - name: "${inp.name}"\n`;
      yaml += `      type: "${inp.type}"\n`;
      yaml += `      required: ${inp.required}\n`;
      if (inp.desc) yaml += `      description: "${inp.desc}"\n`;
    });
    yaml += '\n';
  }

  if (outputs.length) {
    yaml += `  outputs:\n`;
    outputs.forEach(out => {
      yaml += `    - name: "${out.name}"\n`;
      yaml += `      type: "${out.type}"\n`;
      if (out.desc) yaml += `      description: "${out.desc}"\n`;
    });
    yaml += '\n';
  }

  if (prompt) {
    yaml += `  prompt_template: |\n`;
    prompt.split('\n').forEach(line => {
      yaml += `    ${line}\n`;
    });
    yaml += '\n';
  }

  yaml += `  settings:\n`;
  yaml += `    max_tokens: ${maxTokens}\n`;
  yaml += `    temperature: ${temp}\n`;

  if (tags) {
    yaml += `\n  tags: [${tags.split(',').map(t => `"${t.trim()}"`).join(', ')}]\n`;
  }

  document.getElementById('yamlOutput').querySelector('code').textContent = yaml;
}

function collectIOFields(type) {
  const container = type === 'input' ? document.getElementById('inputFields') : document.getElementById('outputFields');
  const fields = container.querySelectorAll('.io-field');
  const result = [];
  fields.forEach(f => {
    const name = f.querySelector('.io-name').value;
    const ioType = f.querySelector('.io-type').value;
    const required = f.querySelector('.io-required-label input').checked;
    const desc = f.querySelector('.io-desc').value;
    if (name) result.push({ name, type: ioType, required, desc });
  });
  return result;
}

function addIOField(type) {
  const container = type === 'input' ? document.getElementById('inputFields') : document.getElementById('outputFields');
  const idx = container.children.length;
  const div = document.createElement('div');
  div.className = 'io-field';
  div.dataset.index = idx;
  div.innerHTML = `
    <div class="io-field-row">
      <input type="text" placeholder="name" class="io-name">
      <select class="io-type">
        <option value="string">string</option>
        <option value="number">number</option>
        <option value="boolean">boolean</option>
        <option value="enum">enum</option>
        <option value="array">array</option>
        <option value="object">object</option>
      </select>
      <label class="io-required-label">
        <input type="checkbox"> Required
      </label>
      <button class="btn-icon-danger" onclick="removeIOField(this)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <input type="text" placeholder="Description" class="io-desc">
  `;
  container.appendChild(div);
}

function removeIOField(btn) {
  const field = btn.closest('.io-field');
  field.remove();
}

function copyYAML() {
  const yaml = document.getElementById('yamlOutput').textContent;
  navigator.clipboard.writeText(yaml).then(() => {
    showToast('YAML copied to clipboard!', 'success');
  });
}

// ===========================
// Validation
// ===========================
function validateSkill() {
  const results = [];
  const name = document.getElementById('skillName').value;
  const displayName = document.getElementById('skillDisplayName').value;
  const cat = document.getElementById('skillCategory').value;
  const desc = document.getElementById('skillDescription').value;
  const prompt = document.getElementById('skillPrompt').value;
  const inputs = collectIOFields('input');

  // Required fields
  if (name && /^[a-z][a-z0-9-]*$/.test(name)) {
    results.push({ status: 'pass', msg: `Skill ID "${name}" is valid` });
  } else if (!name) {
    results.push({ status: 'fail', msg: 'Skill ID is required' });
  } else {
    results.push({ status: 'fail', msg: 'Skill ID must be lowercase letters, numbers, and hyphens only' });
  }

  if (displayName) {
    results.push({ status: 'pass', msg: 'Display name provided' });
  } else {
    results.push({ status: 'fail', msg: 'Display name is required' });
  }

  if (cat) {
    results.push({ status: 'pass', msg: `Category: ${cat}` });
  } else {
    results.push({ status: 'fail', msg: 'Category is required' });
  }

  if (desc && desc.length >= 10) {
    results.push({ status: 'pass', msg: `Description length: ${desc.length} chars` });
  } else if (desc) {
    results.push({ status: 'warn', msg: 'Description should be at least 10 characters' });
  } else {
    results.push({ status: 'fail', msg: 'Description is required' });
  }

  // Prompt
  if (prompt && prompt.length >= 20) {
    results.push({ status: 'pass', msg: `Prompt template provided (${prompt.length} chars)` });
  } else if (prompt) {
    results.push({ status: 'warn', msg: 'Prompt template is too short (recommended: 20+ chars)' });
  } else {
    results.push({ status: 'fail', msg: 'Prompt template is required' });
  }

  // Variables matching
  const promptVars = [...new Set((prompt.match(/\{\{(\w+)\}\}/g) || []).map(v => v.replace(/\{|\}/g, '')))];
  const inputNames = inputs.map(i => i.name);

  promptVars.forEach(v => {
    if (inputNames.includes(v)) {
      results.push({ status: 'pass', msg: `Variable "{{${v}}}" has matching input` });
    } else {
      results.push({ status: 'warn', msg: `Variable "{{${v}}}" has no matching input definition` });
    }
  });

  inputNames.forEach(n => {
    if (!promptVars.includes(n)) {
      results.push({ status: 'warn', msg: `Input "${n}" is not used in prompt template` });
    }
  });

  // Inputs check
  if (inputs.length > 0) {
    results.push({ status: 'pass', msg: `${inputs.length} input field(s) defined` });
  } else {
    results.push({ status: 'warn', msg: 'No input fields defined' });
  }

  // Render
  const container = document.getElementById('validationResults');
  const fails = results.filter(r => r.status === 'fail').length;
  const warns = results.filter(r => r.status === 'warn').length;
  const passes = results.filter(r => r.status === 'pass').length;

  const statusIcons = { pass: '\u2713', fail: '\u2717', warn: '!' };

  container.innerHTML = results.map(r => `
    <div class="validation-item">
      <span class="validation-icon v-${r.status}">${statusIcons[r.status]}</span>
      <span>${r.msg}</span>
    </div>
  `).join('');

  let summaryClass, summaryText;
  if (fails > 0) {
    summaryClass = 'summary-fail';
    summaryText = `\u2717 ${fails} error(s), ${warns} warning(s) \u2014 Fix errors before publishing`;
  } else if (warns > 0) {
    summaryClass = 'summary-warn';
    summaryText = `\u26A0 ${warns} warning(s) \u2014 Publishable, but consider fixing warnings`;
  } else {
    summaryClass = 'summary-pass';
    summaryText = `\u2713 All ${passes} checks passed \u2014 Ready to publish!`;
  }

  container.innerHTML += `<div class="validation-summary ${summaryClass}">${summaryText}</div>`;
}

// ===========================
// Test Skill
// ===========================
function testSkill() {
  const prompt = document.getElementById('skillPrompt').value;
  if (!prompt) {
    showToast('Please write a prompt template first', 'warning');
    return;
  }

  const inputs = collectIOFields('input');
  const exampleInput = {};
  inputs.forEach(inp => {
    exampleInput[inp.name] = inp.desc || `[${inp.name}]`;
  });

  document.getElementById('testInput').value = JSON.stringify(exampleInput, null, 2);
  document.getElementById('testOutput').innerHTML = '<p class="text-muted">Run a test to see output here...</p>';
  document.getElementById('testMetrics').style.display = 'none';
  document.getElementById('testModal').classList.add('active');
}

function runTest() {
  const btn = document.getElementById('runTestBtn');
  btn.textContent = 'Running...';
  btn.disabled = true;

  const prompt = document.getElementById('skillPrompt').value;
  let testInput;
  try {
    testInput = JSON.parse(document.getElementById('testInput').value);
  } catch (e) {
    document.getElementById('testOutput').innerHTML = `<span style="color:var(--error);">Invalid JSON input: ${e.message}</span>`;
    btn.textContent = 'Run Test';
    btn.disabled = false;
    return;
  }

  // Simulate prompt variable replacement
  let resolvedPrompt = prompt;
  Object.entries(testInput).forEach(([key, value]) => {
    resolvedPrompt = resolvedPrompt.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), value);
  });

  // Simulate execution
  setTimeout(() => {
    document.getElementById('testOutput').innerHTML =
      `<strong style="color:var(--accent);">[Resolved Prompt]</strong>\n\n${escapeHtml(resolvedPrompt)}\n\n` +
      `<strong style="color:var(--success);">[Simulated Output]</strong>\n\n` +
      `This is a simulated response from the skill engine.\n` +
      `In production, this would be sent to the AI model and the actual output would appear here.\n\n` +
      `Variables resolved: ${Object.keys(testInput).length}\n` +
      `Unresolved variables: ${(resolvedPrompt.match(/\{\{\w+\}\}/g) || []).length}`;

    document.getElementById('testMetrics').style.display = 'flex';
    document.getElementById('metricTokens').textContent = Math.floor(resolvedPrompt.length / 4);
    document.getElementById('metricTime').textContent = '1.2s (simulated)';
    document.getElementById('metricStatus').innerHTML = '<span style="color:var(--success);">Success</span>';

    btn.textContent = 'Run Test';
    btn.disabled = false;
  }, 1500);
}

function closeTestModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('testModal').classList.remove('active');
}

// ===========================
// Save / Publish
// ===========================
function saveDraft() {
  const name = document.getElementById('skillName').value;
  if (!name) {
    showToast('Please enter a skill ID first', 'warning');
    return;
  }

  const draft = {
    id: name,
    name: document.getElementById('skillDisplayName').value || name,
    category: document.getElementById('skillCategory').value || 'other',
    description: document.getElementById('skillDescription').value || '',
    icon: selectedIcon,
    version: document.getElementById('skillVersion').value || '1.0.0',
    prompt: document.getElementById('skillPrompt').value || '',
    savedAt: new Date().toISOString()
  };

  const existingIdx = draftSkills.findIndex(d => d.id === draft.id);
  if (existingIdx >= 0) {
    draftSkills[existingIdx] = draft;
  } else {
    draftSkills.push(draft);
  }

  try {
    localStorage.setItem('skillforge_drafts', JSON.stringify(draftSkills));
  } catch (e) { /* ignore */ }

  showToast('Draft saved!', 'success');
}

function publishSkill() {
  // Run validation first
  const name = document.getElementById('skillName').value;
  const displayName = document.getElementById('skillDisplayName').value;
  const cat = document.getElementById('skillCategory').value;
  const desc = document.getElementById('skillDescription').value;
  const prompt = document.getElementById('skillPrompt').value;

  if (!name || !displayName || !cat || !desc || !prompt) {
    showToast('Please fill in all required fields before publishing', 'error');
    validateSkill();
    return;
  }

  // Simulate publish
  const newSkill = {
    id: name,
    name: displayName,
    category: cat,
    description: desc,
    icon: selectedIcon,
    version: document.getElementById('skillVersion').value || '1.0.0',
    author: 'You',
    rating: 0,
    downloads: 0,
    tags: (document.getElementById('skillTags').value || '').split(',').map(t => t.trim()).filter(Boolean),
    featured: false,
    prompt: prompt,
    inputs: collectIOFields('input'),
    outputs: collectIOFields('output')
  };

  // Add to store if not duplicate
  if (!SKILLS_DATA.find(s => s.id === newSkill.id)) {
    SKILLS_DATA.push(newSkill);
  }

  showToast(`"${displayName}" published to the store!`, 'success');
}

function loadTemplate() {
  document.getElementById('skillName').value = 'my-skill';
  document.getElementById('skillDisplayName').value = 'My Custom Skill';
  document.getElementById('skillCategory').value = 'document';
  document.getElementById('skillDescription').value = 'This skill helps with...';
  document.getElementById('skillPrompt').value =
    '당신은 {{role}} 전문가입니다.\n\n' +
    '사용자 요청: {{user_input}}\n' +
    '형식: {{format}}\n\n' +
    '위 내용을 바탕으로 전문적인 결과물을 생성해주세요.\n' +
    '결과물은 명확하고 실용적이어야 합니다.';
  document.getElementById('skillTags').value = 'custom, template';
  updatePreview();
  highlightVariables();
  showToast('Template loaded!', 'info');
}

function importSkill() {
  const input = window.prompt('Paste YAML content to import:');
  if (input) {
    showToast('YAML import is simulated in this demo', 'info');
  }
}

// ===========================
// My Skills Page
// ===========================
function renderMySkills() {
  switchMySkillsTab('published', document.querySelector('.myskill-tab.active'));
}

function switchMySkillsTab(tab, el) {
  document.querySelectorAll('.myskill-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');

  const container = document.getElementById('myskillsContent');

  if (tab === 'published') {
    const published = SKILLS_DATA.filter(s => s.author === 'You' || s.author === 'SkillForge Team');
    if (published.length === 0) {
      container.innerHTML = '<p style="color:var(--text-tertiary); padding:24px;">No published skills yet. Create one in the Editor!</p>';
    } else {
      container.innerHTML = published.map(s => renderMySkillItem(s, 'published')).join('');
    }
  } else if (tab === 'drafts') {
    if (draftSkills.length === 0) {
      container.innerHTML = '<p style="color:var(--text-tertiary); padding:24px;">No drafts saved.</p>';
    } else {
      container.innerHTML = draftSkills.map(d => `
        <div class="myskill-item">
          <span class="myskill-icon">${ICONS[d.icon] || ICONS.doc}</span>
          <div class="myskill-info">
            <h4>${d.name}</h4>
            <p>Saved: ${new Date(d.savedAt).toLocaleDateString()}</p>
          </div>
          <span class="myskill-status status-draft">Draft</span>
          <div class="myskill-actions">
            <button class="btn-ghost btn-xs" onclick="loadDraft('${d.id}')">Edit</button>
          </div>
        </div>
      `).join('');
    }
  } else if (tab === 'installed') {
    const installed = SKILLS_DATA.filter(s => installedSkills.has(s.id));
    if (installed.length === 0) {
      container.innerHTML = '<p style="color:var(--text-tertiary); padding:24px;">No skills installed. Browse the Store!</p>';
    } else {
      container.innerHTML = installed.map(s => renderMySkillItem(s, 'installed')).join('');
    }
  }
}

function renderMySkillItem(skill, status) {
  const statusClass = status === 'published' ? 'status-published' : 'status-installed';
  const statusLabel = status === 'published' ? 'Published' : 'Installed';
  return `
    <div class="myskill-item">
      <span class="myskill-icon">${ICONS[skill.icon] || ICONS.doc}</span>
      <div class="myskill-info">
        <h4>${skill.name}</h4>
        <p>${skill.category} \u00b7 v${skill.version} \u00b7 \u2B07 ${skill.downloads || 0}</p>
      </div>
      <span class="myskill-status ${statusClass}">${statusLabel}</span>
      <div class="myskill-actions">
        <button class="btn-ghost btn-xs" onclick="openSkillDetail('${skill.id}')">View</button>
        ${status === 'installed'
          ? `<button class="btn-ghost btn-xs" onclick="uninstallSkill('${skill.id}'); renderMySkills();">Remove</button>`
          : `<button class="btn-ghost btn-xs" onclick="forkSkill('${skill.id}')">Edit</button>`
        }
      </div>
    </div>
  `;
}

function loadDraft(id) {
  const draft = draftSkills.find(d => d.id === id);
  if (!draft) return;
  navigate('editor');
  setTimeout(() => {
    document.getElementById('skillName').value = draft.id;
    document.getElementById('skillDisplayName').value = draft.name;
    document.getElementById('skillCategory').value = draft.category;
    document.getElementById('skillDescription').value = draft.description;
    document.getElementById('skillPrompt').value = draft.prompt || '';
    selectIcon(draft.icon, document.querySelector(`.icon-option[data-icon="${draft.icon}"]`));
    updatePreview();
    highlightVariables();
    showToast('Draft loaded!', 'info');
  }, 100);
}

// ===========================
// Docs Page
// ===========================
const DOCS = {
  'overview': {
    title: 'SkillForge Overview',
    content: `
      <h1>SkillForge Overview</h1>
      <p>SkillForge는 멀티 에이전트 시스템을 위한 스킬 제작, 검증, 공유 플랫폼입니다.</p>

      <div class="docs-callout">
        <p><strong>핵심 개념:</strong> Skill은 AI 에이전트가 특정 작업을 수행하기 위해 사용하는 재사용 가능한 프롬프트 템플릿입니다.</p>
      </div>

      <h2>Platform Features</h2>
      <ul>
        <li><strong>Skill Editor</strong> \u2014 비주얼 에디터로 코딩 없이 스킬을 제작</li>
        <li><strong>Validation Engine</strong> \u2014 스킬 구조와 품질을 자동 검증</li>
        <li><strong>Test Runner</strong> \u2014 게시 전 스킬을 테스트</li>
        <li><strong>Skill Store</strong> \u2014 커뮤니티 스킬을 탐색하고 설치</li>
        <li><strong>Analytics</strong> \u2014 스킬 사용 통계 및 피드백 확인</li>
      </ul>

      <h2>Architecture</h2>
      <p>SkillForge의 스킬은 5가지 에이전트 유형에서 활용됩니다:</p>
      <ol>
        <li><strong>Planner Agent</strong> \u2014 복잡한 작업 분해 및 계획 수립</li>
        <li><strong>Executor Agent</strong> \u2014 실제 스킬 호출 및 실행</li>
        <li><strong>Reviewer Agent</strong> \u2014 결과 품질 검증</li>
        <li><strong>Research Agent</strong> \u2014 정보 수집 및 분석</li>
        <li><strong>Creative Agent</strong> \u2014 콘텐츠 생성 및 아이디어 제안</li>
      </ol>
    `
  },
  'getting-started': {
    title: 'Getting Started',
    content: `
      <h1>Getting Started</h1>
      <p>5분 만에 첫 번째 스킬을 만들어보세요.</p>

      <h2>Step 1: Define Your Skill</h2>
      <p>Editor 페이지에서 Metadata 탭의 기본 정보를 입력합니다.</p>
      <pre><code>Skill ID:   email-draft
Name:       이메일 초안 작성기
Category:   email
Description: 상황에 맞는 이메일을 작성합니다</code></pre>

      <h2>Step 2: Write Your Prompt</h2>
      <p>Prompt 탭에서 프롬프트 템플릿을 작성합니다. <code>{{variable}}</code> 형식으로 동적 입력을 정의합니다.</p>
      <pre><code>당신은 이메일 작성 전문가입니다.

상황: {{context}}
톤: {{tone}}

위 상황에 맞는 이메일을 작성해주세요.</code></pre>

      <h2>Step 3: Define I/O Schema</h2>
      <p>I/O Schema 탭에서 입력과 출력 필드를 정의합니다.</p>

      <h2>Step 4: Validate & Test</h2>
      <p>Validate 버튼으로 스킬 구조를 검증하고, Test Run으로 실행을 시뮬레이션합니다.</p>

      <h2>Step 5: Publish</h2>
      <p>모든 검증을 통과하면 Publish 버튼으로 Store에 게시합니다.</p>
    `
  },
  'skill-schema': {
    title: 'Skill Schema',
    content: `
      <h1>Skill Schema Reference</h1>
      <p>스킬은 YAML 형식으로 정의됩니다.</p>

      <h2>Full Schema</h2>
      <pre><code>skill:
  id: string          # unique, lowercase, hyphens
  name: string        # display name
  version: string     # semver (1.0.0)
  category: string    # document|email|data|...
  description: string # what this skill does
  icon: string        # icon key

  inputs:             # input parameters
    - name: string
      type: string|number|boolean|enum|array|object
      required: boolean
      description: string
      values: []      # for enum type only

  outputs:            # output fields
    - name: string
      type: string
      description: string

  prompt_template: |  # the AI prompt
    Your prompt with {{variables}}

  settings:
    max_tokens: number
    temperature: number (0-1)
    requires_review: boolean

  permissions:        # required access
    - read:context
    - write:clipboard

  tags: []            # search tags</code></pre>

      <h2>Field Details</h2>
      <h3>id</h3>
      <p>고유 식별자. 영문 소문자, 숫자, 하이픈만 허용. 예: <code>email-composer</code></p>

      <h3>inputs / outputs</h3>
      <p>지원 타입: <code>string</code>, <code>number</code>, <code>boolean</code>, <code>enum</code>, <code>array</code>, <code>object</code></p>
    `
  },
  'prompt-guide': {
    title: 'Prompt Guide',
    content: `
      <h1>Prompt Writing Guide</h1>
      <p>좋은 스킬 프롬프트를 작성하기 위한 가이드입니다.</p>

      <h2>Best Practices</h2>
      <ul>
        <li><strong>역할 지정:</strong> "당신은 ~~ 전문가입니다" 로 시작</li>
        <li><strong>명확한 지시:</strong> 원하는 출력 형식을 구체적으로 기술</li>
        <li><strong>변수 활용:</strong> <code>{{variable}}</code> 로 동적 입력 처리</li>
        <li><strong>구조화된 출력:</strong> 번호 매기기, 섹션 나누기 활용</li>
        <li><strong>제약 조건:</strong> 길이, 톤, 형식 등 제한 사항 명시</li>
      </ul>

      <div class="docs-callout">
        <p><strong>Tip:</strong> 프롬프트의 변수명은 I/O Schema의 input name과 일치해야 합니다.</p>
      </div>

      <h2>Example: Good Prompt</h2>
      <pre><code>당신은 비즈니스 이메일 작성 전문가입니다.

[상황]
{{context}}

[요구사항]
- 톤: {{tone}}
- 언어: {{language}}
- 수신자: {{recipient}}

[출력 형식]
1. 제목 (한 줄)
2. 본문 (3-5 문단)
3. 맺음말

전문적이고 정중한 이메일을 작성해주세요.</code></pre>
    `
  },
  'agents': {
    title: 'Agent Types',
    content: `
      <h1>Agent Types</h1>
      <p>멀티 에이전트 시스템의 5가지 에이전트 유형을 설명합니다.</p>

      <h2>Orchestrator (Router Agent)</h2>
      <p>사용자 입력을 분석하여 적절한 Worker Agent에 작업을 분배하는 핵심 라우터입니다.</p>
      <ul>
        <li>Intent Analysis: 사용자 의도 파악</li>
        <li>Agent Selection: 최적 에이전트 선택</li>
        <li>Result Merging: 멀티 에이전트 결과 통합</li>
      </ul>

      <h2>Worker Agents</h2>

      <h3>1. Planner Agent</h3>
      <p>복잡한 작업을 단계별로 분해하고 실행 계획을 수립합니다.</p>

      <h3>2. Executor Agent</h3>
      <p>스킬을 직접 호출하여 작업을 수행하는 실행 에이전트입니다.</p>

      <h3>3. Reviewer Agent</h3>
      <p>실행 결과를 검증하고 품질을 확인합니다. 오류 발견 시 재실행을 요청합니다.</p>

      <h3>4. Research Agent</h3>
      <p>정보 수집, 문서 분석, 데이터 조회를 담당합니다.</p>

      <h3>5. Creative Agent</h3>
      <p>콘텐츠 생성, 아이디어 발상, 창작 작업을 수행합니다.</p>
    `
  },
  'memory': {
    title: 'Memory System',
    content: `
      <h1>Memory System</h1>
      <p>에이전트의 3계층 메모리 구조를 설명합니다.</p>

      <h2>Layer 1: Working Memory</h2>
      <p>현재 세션의 대화와 작업 상태를 관리합니다.</p>
      <ul>
        <li>Message Buffer: 현재 대화 메시지</li>
        <li>Agent States: 활성 에이전트 상태</li>
        <li>Skill Stack: 실행 중인 스킬 체인</li>
        <li>Token Budget: 컨텍스트 윈도우 관리</li>
      </ul>

      <h2>Layer 2: Episodic Memory</h2>
      <p>과거 대화 이력과 작업 패턴을 저장합니다.</p>
      <ul>
        <li>Session Logs: 과거 세션 요약</li>
        <li>Task History: 작업 성공/실패 이력</li>
        <li>User Patterns: 사용자 행동 패턴</li>
      </ul>

      <h2>Layer 3: Semantic Memory</h2>
      <p>장기적인 지식과 사용자 선호를 벡터 DB에 저장합니다.</p>
      <ul>
        <li>User Preferences: 사용자 스타일/선호</li>
        <li>Domain Knowledge: 도메인별 지식</li>
        <li>Skill Definitions: 스킬 메타데이터</li>
      </ul>

      <h2>Context Window Management</h2>
      <pre><code>Strategy:
1. Sliding Window  - 최근 N턴 유지
2. Summarization   - 오래된 대화 요약 압축
3. RAG Retrieval   - 필요시 장기 기억 검색
4. Priority Queue  - 중요도 기반 유지</code></pre>
    `
  },
  'publishing': {
    title: 'Publishing',
    content: `
      <h1>Publishing Guide</h1>
      <p>스킬을 Store에 게시하는 과정을 설명합니다.</p>

      <h2>Publishing Checklist</h2>
      <ol>
        <li>모든 필수 필드 입력 (ID, Name, Category, Description, Prompt)</li>
        <li>I/O Schema에 최소 1개의 Input 정의</li>
        <li>프롬프트 변수와 Input 필드 매칭 확인</li>
        <li>Validation 통과 (에러 0건)</li>
        <li>Test Run 으로 동작 확인</li>
      </ol>

      <h2>Version Management</h2>
      <p>Semantic Versioning을 따릅니다:</p>
      <ul>
        <li><code>MAJOR.MINOR.PATCH</code> (예: 1.2.3)</li>
        <li>MAJOR: 호환성 깨는 변경</li>
        <li>MINOR: 기능 추가</li>
        <li>PATCH: 버그 수정</li>
      </ul>

      <h2>Best Practices</h2>
      <ul>
        <li>명확하고 검색 가능한 이름 사용</li>
        <li>상세한 Description 작성</li>
        <li>관련 Tags 추가</li>
        <li>Example Input/Output 제공</li>
      </ul>
    `
  },
  'api': {
    title: 'API Reference',
    content: `
      <h1>API Reference</h1>
      <p>SkillForge 스킬을 프로그래밍적으로 사용하는 방법입니다.</p>

      <h2>Skill Execution API</h2>
      <pre><code>POST /api/skills/{skill_id}/execute

{
  "inputs": {
    "context": "거래처 납기 지연 사과 메일",
    "tone": "formal",
    "language": "ko"
  },
  "options": {
    "max_tokens": 2000,
    "temperature": 0.7
  }
}

Response:
{
  "status": "success",
  "outputs": {
    "subject": "납기 지연에 대한 사과 말씀",
    "body": "..."
  },
  "metadata": {
    "tokens_used": 847,
    "execution_time_ms": 1234,
    "agent": "executor"
  }
}</code></pre>

      <h2>Skill Registry API</h2>
      <pre><code>GET  /api/skills               # List all skills
GET  /api/skills/{id}           # Get skill detail
POST /api/skills                # Create skill
PUT  /api/skills/{id}           # Update skill
GET  /api/skills/search?q=email # Search skills</code></pre>

      <h2>Agent Orchestration API</h2>
      <pre><code>POST /api/orchestrate

{
  "message": "지난달 매출 보고서 만들어줘",
  "context": {
    "session_id": "abc-123",
    "user_id": "user-001"
  }
}

Response:
{
  "plan": [
    {"agent": "research", "skill": "excel-analyzer"},
    {"agent": "creative", "skill": "doc-drafter"},
    {"agent": "reviewer", "skill": "proofreader"}
  ],
  "result": "..."
}</code></pre>
    `
  }
};

function showDoc(key, el) {
  if (el) {
    document.querySelectorAll('.docs-nav li').forEach(li => li.classList.remove('active'));
    el.classList.add('active');
  }

  const doc = DOCS[key];
  if (doc) {
    document.getElementById('docsContent').innerHTML = doc.content;
  }
}

// ===========================
// Utility
// ===========================
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = {
    success: '\u2713',
    error: '\u2717',
    warning: '\u26A0',
    info: '\u2139'
  };

  toast.innerHTML = `<span style="font-weight:700;">${icons[type] || ''}</span> ${message}`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(12px)';
    toast.style.transition = '300ms ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ===========================
// Init
// ===========================
function init() {
  // Load drafts from localStorage
  try {
    const saved = localStorage.getItem('skillforge_drafts');
    if (saved) draftSkills = JSON.parse(saved);
  } catch (e) { /* ignore */ }

  renderStore();
  updatePreview();
}

// Start
document.addEventListener('DOMContentLoaded', init);
