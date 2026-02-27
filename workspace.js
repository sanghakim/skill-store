/**
 * SkillForge Workspace - AI Multi-Agent Workspace
 * Real-time chat interface with agent activity visualization
 */

// ═══════════════════════════════════════
// State Management
// ═══════════════════════════════════════
const State = {
    // Connection
    ws: null,
    wsConnected: false,
    reconnectAttempts: 0,
    maxReconnectAttempts: 10,
    sessionId: null,
    userId: 'default',

    // Chat
    messages: [],
    isProcessing: false,
    messageIdCounter: 0,

    // Agent Activity
    activities: [],

    // Plan & Tasks
    currentPlan: null,
    taskStatuses: {},
    currentIteration: 0,
    qualityReview: null,
    planHistory: [],

    // Skills
    skills: [],
    filteredSkills: [],
    selectedCategory: null,
    sidebarOpen: false,

    // Sessions
    sessions: [],

    // Attachments
    pendingFiles: [],       // {file: File, id: null, name, size}
    uploadedFiles: [],      // {file_id, filename, size, mime_type, content_preview}

    // UI
    rightPanelMode: 'activity',
};

// ═══════════════════════════════════════
// Constants
// ═══════════════════════════════════════
const AGENT_NAMES = {
    planner: 'Planner',
    executor: 'Executor',
    reviewer: 'Reviewer',
    research: 'Research',
    creative: 'Creative',
    orchestrator: 'Orchestrator',
};

const AGENT_ICONS = {
    planner: '&#9998;',
    executor: '&#9881;',
    reviewer: '&#10004;',
    research: '&#128269;',
    creative: '&#10024;',
    orchestrator: '&#9733;',
};

const SKILL_ICONS = {
    document: '&#128196;',
    email: '&#9993;',
    data: '&#128202;',
    schedule: '&#128197;',
    presentation: '&#128200;',
    hr: '&#128101;',
    translation: '&#127760;',
    automation: '&#9889;',
    knowledge: '&#128218;',
    other: '&#128736;',
};

const CATEGORY_LABELS = {
    document: '&#128196; &#47928;&#49436;',
    email: '&#9993; &#51060;&#47700;&#51068;',
    data: '&#128202; &#45936;&#51060;&#53552;',
    schedule: '&#128197; &#51068;&#51221;',
    presentation: '&#128200; &#54532;&#47112;&#51232;&#53580;&#51060;&#49496;',
    hr: '&#128101; HR',
    translation: '&#127760; &#48264;&#50669;',
    automation: '&#9889; &#51088;&#46041;&#54868;',
    knowledge: '&#128218; &#47532;&#49436;&#52824;',
    other: '&#128736; &#44592;&#53440;',
};

const FILE_ICONS = {
    '.txt': '&#128196;', '.csv': '&#128202;', '.json': '&#128203;',
    '.md': '&#128221;', '.xlsx': '&#128202;', '.pdf': '&#128213;',
    '.yaml': '&#9881;', '.yml': '&#9881;', '.py': '&#128187;',
    '.html': '&#127760;', '.xml': '&#128196;', '.tsv': '&#128202;',
    '.log': '&#128196;', 'default': '&#128206;',
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const API_BASE = window.location.origin;
const WS_URL = `ws://${window.location.host}/ws/chat`;

// ═══════════════════════════════════════
// Initialization
// ═══════════════════════════════════════
function init() {
    connectWebSocket();
    loadSkills();
    restoreSession();
    setupDragDrop();

    // Setup input handlers
    const input = document.getElementById('chatInput');
    input.addEventListener('input', () => {
        const count = input.value.length;
        document.getElementById('charCount').textContent = count;
        updateSendButton();
    });
}

function updateSendButton() {
    const input = document.getElementById('chatInput');
    const hasText = input.value.trim().length > 0;
    const hasFiles = State.pendingFiles.length > 0;
    document.getElementById('sendBtn').disabled = (!hasText && !hasFiles) || State.isProcessing;
}

function restoreSession() {
    const savedSessionId = localStorage.getItem('sf_session_id');
    if (savedSessionId) {
        State.sessionId = savedSessionId;
    }
}

// ═══════════════════════════════════════
// WebSocket Connection
// ═══════════════════════════════════════
function connectWebSocket() {
    updateConnectionStatus('connecting');

    try {
        State.ws = new WebSocket(WS_URL);
    } catch (e) {
        updateConnectionStatus('disconnected');
        scheduleReconnect();
        return;
    }

    State.ws.onopen = () => {
        State.wsConnected = true;
        State.reconnectAttempts = 0;
        updateConnectionStatus('connected');
        showToast('서버에 연결되었습니다', 'success');
    };

    State.ws.onclose = () => {
        State.wsConnected = false;
        updateConnectionStatus('disconnected');
        scheduleReconnect();
    };

    State.ws.onerror = () => {
        State.wsConnected = false;
        updateConnectionStatus('disconnected');
    };

    State.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketEvent(data);
        } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
        }
    };
}

function scheduleReconnect() {
    if (State.reconnectAttempts >= State.maxReconnectAttempts) {
        showToast('서버 연결에 실패했습니다. 페이지를 새로고침하세요.', 'error');
        return;
    }
    const delay = Math.min(1000 * Math.pow(2, State.reconnectAttempts), 30000);
    State.reconnectAttempts++;
    setTimeout(connectWebSocket, delay);
}

function updateConnectionStatus(status) {
    const el = document.getElementById('connectionStatus');
    const dot = el.querySelector('.status-dot');
    const text = el.querySelector('.status-text');

    dot.className = 'status-dot ' + status;
    const labels = {
        connected: '연결됨',
        disconnected: '연결 끊김',
        connecting: '연결 중...',
    };
    text.textContent = labels[status] || status;
}

// ═══════════════════════════════════════
// WebSocket Event Router
// ═══════════════════════════════════════
function handleWebSocketEvent(data) {
    switch (data.type) {
        case 'session_created':
            State.sessionId = data.session_id;
            localStorage.setItem('sf_session_id', data.session_id);
            break;

        case 'session_switched':
            State.sessionId = data.session_id;
            localStorage.setItem('sf_session_id', data.session_id);
            break;

        case 'pong':
            break;

        case 'processing_started':
            State.isProcessing = true;
            showTypingIndicator('요청을 분석하고 있습니다...');
            clearWorkspace();
            break;

        case 'intent_analyzed':
            addActivity('system', '의도 분석 완료', 'analyzing',
                `의도: ${data.intent} | 복잡도: ${data.complexity} | 신뢰도: ${(data.confidence * 100).toFixed(0)}%`);
            showTypingIndicator('실행 계획을 수립 중...');
            break;

        case 'plan_created':
            State.currentPlan = data;
            State.taskStatuses = {};
            data.tasks.forEach(t => { State.taskStatuses[t.task_id] = 'pending'; });
            addActivity('system', `실행 계획 생성 (${data.task_count}개 작업)`, 'completed',
                data.tasks.map(t => `${AGENT_NAMES[t.agent_role] || t.agent_role}: ${t.skill_id || t.description}`).join(', '));
            renderTasks();
            showTypingIndicator('작업을 실행 중...');
            break;

        case 'iteration_start':
            State.currentIteration = data.iteration;
            addActivity('system', `반복 ${data.iteration}/${data.max_iterations} 시작`, 'executing', '');
            break;

        case 'task_started':
            State.taskStatuses[data.task_id] = 'executing';
            addActivity(data.agent, `${data.skill_id || data.description} 실행 중`, 'executing',
                data.description);
            renderTasks();
            showTypingIndicator(`${AGENT_NAMES[data.agent] || data.agent} 에이전트 실행 중...`);
            break;

        case 'task_completed':
            State.taskStatuses[data.task_id] = 'completed';
            addActivity(data.agent,
                `${data.skill_id || '작업'} 완료`,
                'completed',
                `토큰: ${data.tokens_used} | 시간: ${data.execution_time_ms}ms`);
            renderTasks();
            break;

        case 'task_failed':
            State.taskStatuses[data.task_id] = 'failed';
            addActivity(data.agent,
                `${data.skill_id || '작업'} 실패`,
                'failed',
                data.error || '알 수 없는 오류');
            renderTasks();
            break;

        case 'review_completed':
            State.qualityReview = data;
            addActivity('reviewer', `품질 리뷰 완료`, data.passed ? 'completed' : 'failed',
                `점수: ${(data.score * 100).toFixed(0)}% | ${data.passed ? '통과' : '미달'}`);
            renderPlan();
            break;

        case 'replanning':
            addActivity('system', `재계획 수립 (반복 ${data.iteration})`, 'analyzing',
                data.reason);
            break;

        case 'iteration_complete':
            addActivity('system',
                `반복 ${data.iteration} 완료`,
                data.passed ? 'completed' : 'failed',
                `품질: ${(data.quality_score * 100).toFixed(0)}% | 토큰: ${data.total_tokens}`);
            break;

        case 'response':
            State.isProcessing = false;
            hideTypingIndicator();
            addAssistantMessage(data.response, data);
            addActivity('system', '응답 완료', 'completed',
                `반복: ${data.iterations} | 토큰: ${data.total_tokens} | 시간: ${data.total_time_ms}ms`);
            renderPlan();
            break;

        case 'processing_complete':
            State.isProcessing = false;
            hideTypingIndicator();
            break;

        case 'error':
            State.isProcessing = false;
            hideTypingIndicator();
            addActivity('system', `오류: ${data.code || 'ERROR'}`, 'failed', data.error);
            showToast(`오류: ${data.error}`, 'error');
            break;

        default:
            console.log('Unknown event:', data.type, data);
    }
}

// ═══════════════════════════════════════
// Chat - Sending Messages
// ═══════════════════════════════════════
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    const hasFiles = State.pendingFiles.length > 0;
    if ((!message && !hasFiles) || State.isProcessing || !State.wsConnected) return;

    // Upload pending files first
    const uploadedIds = [];
    const fileNames = [];
    if (hasFiles) {
        for (const pf of State.pendingFiles) {
            try {
                const result = await uploadFile(pf.file);
                uploadedIds.push(result.file_id);
                fileNames.push({ name: pf.name, size: pf.size });
            } catch (e) {
                showToast(`파일 업로드 실패: ${pf.name}`, 'error');
            }
        }
    }

    // Add user message to UI (with attachment info)
    addUserMessage(message || '(파일 첨부)', fileNames);

    // Hide welcome message
    const welcome = document.getElementById('welcomeMessage');
    if (welcome) welcome.style.display = 'none';

    // Send via WebSocket
    State.ws.send(JSON.stringify({
        type: 'message',
        message: message || '첨부된 파일을 분석해주세요',
        session_id: State.sessionId,
        user_id: State.userId,
        attachments: uploadedIds,
    }));

    // Clear input and attachments
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('charCount').textContent = '0';
    clearAttachments();
    updateSendButton();
}

function sendSuggestion(text) {
    const input = document.getElementById('chatInput');
    input.value = text;
    document.getElementById('charCount').textContent = String(text.length);
    document.getElementById('sendBtn').disabled = false;
    sendMessage();
}

function handleInputKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResizeInput(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

// ═══════════════════════════════════════
// Chat - Message Rendering
// ═══════════════════════════════════════
function addUserMessage(content, attachments = []) {
    const id = ++State.messageIdCounter;
    State.messages.push({ id, role: 'user', content, attachments, timestamp: new Date() });

    const container = document.getElementById('chatMessages');
    let attachHtml = '';
    if (attachments.length > 0) {
        attachHtml = '<div class="message-attachments">';
        attachments.forEach(a => {
            const ext = '.' + (a.name || '').split('.').pop().toLowerCase();
            const icon = FILE_ICONS[ext] || FILE_ICONS['default'];
            attachHtml += `<span class="msg-attachment"><span class="att-icon">${icon}</span>${escapeHtml(a.name)} (${formatFileSize(a.size)})</span>`;
        });
        attachHtml += '</div>';
    }

    const html = `
        <div class="message user" id="msg-${id}">
            <div class="message-avatar">U</div>
            <div>
                <div class="message-body">${escapeHtml(content)}${attachHtml}</div>
                <div class="message-meta">
                    <span>${formatTime(new Date())}</span>
                </div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
    scrollToBottom(container);
}

function addAssistantMessage(content, meta = {}) {
    const id = ++State.messageIdCounter;
    State.messages.push({ id, role: 'assistant', content, meta, timestamp: new Date() });

    const container = document.getElementById('chatMessages');
    const metaHtml = meta.total_tokens
        ? `<span class="tokens">${meta.total_tokens} tokens</span> &middot; <span>${meta.total_time_ms}ms</span> &middot; <span>${meta.iterations}회 반복</span>`
        : '';

    const html = `
        <div class="message assistant" id="msg-${id}">
            <div class="message-avatar">&#9881;</div>
            <div>
                <div class="message-body">${renderMarkdown(content)}</div>
                <div class="message-meta">
                    <span>${formatTime(new Date())}</span>
                    ${metaHtml}
                </div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
    scrollToBottom(container);
}

// ═══════════════════════════════════════
// Markdown Renderer (Lightweight)
// ═══════════════════════════════════════
function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);

    // Code blocks (```...```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h5>$1</h5>');
    html = html.replace(/^## (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^# (.+)$/gm, '<h3>$1</h3>');

    // Bold & Italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Horizontal rule
    html = html.replace(/^---$/gm, '<hr>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Tables
    html = html.replace(/^(\|.+\|)\n(\|[-: |]+\|)\n((?:\|.+\|\n?)*)/gm, (_, header, sep, body) => {
        const heads = header.split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
        const rows = body.trim().split('\n').map(row => {
            const cells = row.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('');
            return `<tr>${cells}</tr>`;
        }).join('');
        return `<table><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table>`;
    });

    // Unordered lists
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>(\n|$))+/g, (match) => `<ul>${match}</ul>`);

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Paragraphs - convert double newlines
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Clean up
    html = html.replace(/<br><h/g, '<h');
    html = html.replace(/<\/h(\d)><br>/g, '</h$1>');
    html = html.replace(/<br><ul>/g, '<ul>');
    html = html.replace(/<\/ul><br>/g, '</ul>');
    html = html.replace(/<br><pre>/g, '<pre>');
    html = html.replace(/<\/pre><br>/g, '</pre>');
    html = html.replace(/<br><table>/g, '<table>');
    html = html.replace(/<\/table><br>/g, '</table>');
    html = html.replace(/<br><hr>/g, '<hr>');
    html = html.replace(/<hr><br>/g, '<hr>');

    return html;
}

// ═══════════════════════════════════════
// Typing Indicator
// ═══════════════════════════════════════
function showTypingIndicator(text) {
    const el = document.getElementById('typingIndicator');
    el.style.display = 'flex';
    document.getElementById('typingText').textContent = text || '에이전트가 작업 중...';
    scrollToBottom(document.getElementById('chatMessages'));
}

function hideTypingIndicator() {
    document.getElementById('typingIndicator').style.display = 'none';
}

// ═══════════════════════════════════════
// Agent Activity Stream
// ═══════════════════════════════════════
function addActivity(agent, title, status, detail) {
    const activity = {
        id: Date.now(),
        agent: agent,
        title: title,
        status: status,
        detail: detail,
        timestamp: new Date(),
    };
    State.activities.push(activity);

    const stream = document.getElementById('activityStream');
    // Remove empty state on first activity
    const empty = stream.querySelector('.activity-empty');
    if (empty) empty.remove();

    const agentClass = agent || 'system';
    const statusLabel = {
        executing: '실행 중',
        completed: '완료',
        failed: '실패',
        analyzing: '분석 중',
    };

    const html = `
        <div class="activity-card ${agentClass}">
            <div class="activity-header">
                <span class="activity-agent">
                    <span class="agent-dot ${agentClass}"></span>
                    ${AGENT_NAMES[agent] || '시스템'}
                </span>
                <span class="activity-status ${status}">${statusLabel[status] || status}</span>
            </div>
            <div class="activity-detail">${escapeHtml(title)}${detail ? '<br>' + escapeHtml(detail) : ''}</div>
            <div class="activity-time">${formatTime(new Date())}</div>
        </div>
    `;
    stream.insertAdjacentHTML('beforeend', html);
    stream.scrollTop = stream.scrollHeight;
}

function clearWorkspace() {
    State.activities = [];
    State.currentPlan = null;
    State.taskStatuses = {};
    State.qualityReview = null;
    State.currentIteration = 0;

    // Clear activity stream
    const stream = document.getElementById('activityStream');
    stream.innerHTML = '';

    // Clear tasks
    document.getElementById('tasksContainer').innerHTML = `
        <div class="activity-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            </svg>
            <p>실행 계획이 생성되면<br>작업 흐름이 표시됩니다</p>
        </div>
    `;

    // Clear plan
    document.getElementById('planContainer').innerHTML = `
        <div class="activity-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <p>품질 리뷰 결과와<br>실행 계획이 표시됩니다</p>
        </div>
    `;
}

// ═══════════════════════════════════════
// Task DAG Visualization
// ═══════════════════════════════════════
function renderTasks() {
    if (!State.currentPlan || !State.currentPlan.tasks) return;

    const container = document.getElementById('tasksContainer');
    const tasks = State.currentPlan.tasks;

    // Build dependency tiers
    const tiers = buildTiers(tasks);

    let html = '';

    tiers.forEach((tier, tierIndex) => {
        if (tierIndex > 0) {
            html += `
                <div class="task-connector">
                    <svg width="24" height="20" viewBox="0 0 24 20">
                        <path d="M12 0 L12 20" stroke="currentColor" stroke-width="1.5" stroke-dasharray="4 3" fill="none"/>
                        <path d="M8 14 L12 20 L16 14" stroke="currentColor" stroke-width="1.5" fill="none"/>
                    </svg>
                </div>
            `;
        }

        html += '<div class="task-tier">';
        tier.forEach(task => {
            const status = State.taskStatuses[task.task_id] || 'pending';
            const agentName = AGENT_NAMES[task.agent_role] || task.agent_role;

            html += `
                <div class="task-node ${status}">
                    <div class="task-node-header">
                        <span class="task-status-dot ${status}"></span>
                        <span class="task-agent-name" style="color: var(--agent-${task.agent_role})">${agentName}</span>
                    </div>
                    <div class="task-description">${escapeHtml(task.description)}</div>
                    ${task.skill_id ? `<span class="task-skill-badge">${task.skill_id}</span>` : ''}
                </div>
            `;
        });
        html += '</div>';
    });

    container.innerHTML = html;
}

function buildTiers(tasks) {
    const taskMap = {};
    tasks.forEach(t => { taskMap[t.task_id] = t; });

    const tiers = [];
    const placed = new Set();

    while (placed.size < tasks.length) {
        const tier = tasks.filter(t =>
            !placed.has(t.task_id) &&
            t.dependencies.every(d => placed.has(d))
        );

        if (tier.length === 0) break; // Prevent infinite loop

        tier.forEach(t => placed.add(t.task_id));
        tiers.push(tier);
    }

    return tiers;
}

// ═══════════════════════════════════════
// Plan & Quality View
// ═══════════════════════════════════════
function renderPlan() {
    const container = document.getElementById('planContainer');

    if (!State.currentPlan && !State.qualityReview) {
        return;
    }

    let html = '';

    // Current iteration info
    html += `<div class="plan-iteration">`;
    html += `<div class="plan-iteration-header">`;
    html += `<span class="plan-iteration-title">반복 ${State.currentIteration || 1}</span>`;

    if (State.qualityReview) {
        const passed = State.qualityReview.passed;
        html += `<span class="plan-iteration-badge ${passed ? 'passed' : 'failed'}">
            ${passed ? '통과' : '미달'}
        </span>`;
    }
    html += `</div>`;

    // Quality gauge
    if (State.qualityReview) {
        const score = State.qualityReview.score;
        const pct = score * 100;
        const circumference = 2 * Math.PI * 24;
        const offset = circumference - (score * circumference);
        const color = score >= 0.75 ? 'var(--success)' : score >= 0.5 ? 'var(--warning)' : 'var(--error)';

        html += `
            <div class="quality-gauge">
                <div class="gauge-circle">
                    <svg width="60" height="60" viewBox="0 0 60 60">
                        <circle class="gauge-bg" cx="30" cy="30" r="24"/>
                        <circle class="gauge-fill" cx="30" cy="30" r="24"
                            stroke="${color}"
                            stroke-dasharray="${circumference}"
                            stroke-dashoffset="${offset}"/>
                    </svg>
                    <div class="gauge-text" style="color: ${color}">${pct.toFixed(0)}%</div>
                </div>
                <div class="quality-aspects">
                    ${renderAspects(State.qualityReview.aspects)}
                </div>
            </div>
        `;

        if (State.qualityReview.feedback) {
            html += `<div class="plan-summary">${escapeHtml(State.qualityReview.feedback)}</div>`;
        }
    }

    // Stats
    const lastResponse = State.messages.filter(m => m.role === 'assistant').pop();
    if (lastResponse && lastResponse.meta) {
        const m = lastResponse.meta;
        html += `
            <div class="plan-stats">
                <div class="plan-stat">
                    <div class="plan-stat-value">${m.iterations || '-'}</div>
                    <div class="plan-stat-label">반복</div>
                </div>
                <div class="plan-stat">
                    <div class="plan-stat-value">${m.total_tokens || '-'}</div>
                    <div class="plan-stat-label">토큰</div>
                </div>
                <div class="plan-stat">
                    <div class="plan-stat-value">${m.total_time_ms ? (m.total_time_ms / 1000).toFixed(1) + 's' : '-'}</div>
                    <div class="plan-stat-label">소요시간</div>
                </div>
                <div class="plan-stat">
                    <div class="plan-stat-value">${State.currentPlan ? State.currentPlan.task_count : '-'}</div>
                    <div class="plan-stat-label">작업 수</div>
                </div>
            </div>
        `;
    }

    html += '</div>';
    container.innerHTML = html;
}

function renderAspects(aspects) {
    if (!aspects || !Array.isArray(aspects) || aspects.length === 0) {
        // Default aspects
        const defaults = ['completeness', 'accuracy', 'format', 'tone', 'relevance'];
        const labels = { completeness: '완전성', accuracy: '정확성', format: '형식', tone: '어조', relevance: '관련성' };
        return defaults.map(a => `
            <div class="aspect-row">
                <span class="aspect-label">${labels[a]}</span>
                <div class="aspect-bar"><div class="aspect-bar-fill" style="width: 0%; background: var(--border)"></div></div>
                <span class="aspect-score">-</span>
            </div>
        `).join('');
    }

    const labels = { completeness: '완전성', accuracy: '정확성', format: '형식', tone: '어조', relevance: '관련성' };

    return aspects.map(a => {
        const score = a.score || 0;
        const pct = score * 100;
        const color = score >= 0.75 ? 'var(--success)' : score >= 0.5 ? 'var(--warning)' : 'var(--error)';
        const label = labels[a.aspect] || a.aspect;
        return `
            <div class="aspect-row">
                <span class="aspect-label">${label}</span>
                <div class="aspect-bar"><div class="aspect-bar-fill" style="width: ${pct}%; background: ${color}"></div></div>
                <span class="aspect-score">${pct.toFixed(0)}%</span>
            </div>
        `;
    }).join('');
}

// ═══════════════════════════════════════
// Workspace Tab Switching
// ═══════════════════════════════════════
function switchWorkspaceTab(tab) {
    State.rightPanelMode = tab;

    // Update tab buttons
    document.querySelectorAll('.ws-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });

    // Update content
    document.querySelectorAll('.ws-content').forEach(c => {
        c.classList.remove('active');
    });

    const contentMap = {
        activity: 'activityView',
        tasks: 'tasksView',
        plan: 'planView',
    };
    const content = document.getElementById(contentMap[tab]);
    if (content) content.classList.add('active');
}

// ═══════════════════════════════════════
// Skill Sidebar
// ═══════════════════════════════════════
function toggleSidebar() {
    State.sidebarOpen = !State.sidebarOpen;
    document.getElementById('workspaceLayout').classList.toggle('sidebar-open', State.sidebarOpen);
}

async function loadSkills() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/skills`);
        if (!res.ok) return;
        const data = await res.json();
        State.skills = data.skills || [];
        State.filteredSkills = State.skills;
        renderSidebarCategories();
        renderSidebarSkills();
    } catch (e) {
        console.log('Skills not loaded (server may not be running):', e.message);
    }
}

function renderSidebarCategories() {
    const cats = {};
    State.skills.forEach(s => {
        const cat = s.category || 'other';
        cats[cat] = (cats[cat] || 0) + 1;
    });

    const container = document.getElementById('sidebarCategories');
    let html = `<button class="category-chip ${!State.selectedCategory ? 'active' : ''}" onclick="filterByCategory(null)">전체 (${State.skills.length})</button>`;
    Object.entries(cats).forEach(([cat, count]) => {
        const label = CATEGORY_LABELS[cat] || cat;
        html += `<button class="category-chip ${State.selectedCategory === cat ? 'active' : ''}" onclick="filterByCategory('${cat}')">${label} (${count})</button>`;
    });
    container.innerHTML = html;
}

function renderSidebarSkills() {
    const container = document.getElementById('sidebarSkills');
    if (State.filteredSkills.length === 0) {
        container.innerHTML = '<div class="activity-empty"><p>스킬이 없습니다</p></div>';
        return;
    }

    let html = '';
    State.filteredSkills.forEach(skill => {
        const icon = SKILL_ICONS[skill.category] || '&#128736;';
        html += `
            <div class="sidebar-skill-item" onclick="showSkillDetail('${skill.id}')" title="${skill.description || ''}">
                <span class="skill-icon">${icon}</span>
                <div class="skill-info">
                    <div class="skill-name">${escapeHtml(skill.name)}</div>
                    <div class="skill-category">${skill.category}</div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function filterByCategory(category) {
    State.selectedCategory = category;
    if (category) {
        State.filteredSkills = State.skills.filter(s => s.category === category);
    } else {
        State.filteredSkills = State.skills;
    }
    renderSidebarCategories();
    renderSidebarSkills();
}

function filterSkills(query) {
    const q = query.toLowerCase();
    State.filteredSkills = State.skills.filter(s => {
        if (State.selectedCategory && s.category !== State.selectedCategory) return false;
        return s.name.toLowerCase().includes(q) ||
               (s.description || '').toLowerCase().includes(q) ||
               (s.tags || []).some(t => t.toLowerCase().includes(q));
    });
    renderSidebarSkills();
}

function showSkillDetail(skillId) {
    const skill = State.skills.find(s => s.id === skillId);
    if (!skill) return;
    showToast(`${skill.name}: ${skill.description || skillId}`, 'info');
}

// ═══════════════════════════════════════
// Session Management
// ═══════════════════════════════════════
function createNewSession() {
    if (State.ws && State.wsConnected) {
        State.ws.send(JSON.stringify({
            type: 'create_session',
            user_id: State.userId,
        }));

        // Clear chat
        State.messages = [];
        State.messageIdCounter = 0;
        const container = document.getElementById('chatMessages');
        container.innerHTML = `
            <div class="welcome-message" id="welcomeMessage">
                <div class="welcome-icon">&#9881;</div>
                <h2>SkillForge Workspace</h2>
                <p>AI 멀티 에이전트 시스템이 준비되었습니다.<br>무엇을 도와드릴까요?</p>
                <div class="welcome-suggestions">
                    <button class="suggestion-chip" onclick="sendSuggestion('비즈니스 이메일을 작성해줘')">비즈니스 이메일 작성</button>
                    <button class="suggestion-chip" onclick="sendSuggestion('프로젝트 보고서 초안을 만들어줘')">보고서 초안 생성</button>
                    <button class="suggestion-chip" onclick="sendSuggestion('AI 트렌드에 대해 심층 분석해줘')">심층 리서치</button>
                    <button class="suggestion-chip" onclick="sendSuggestion('팀 회의 안건을 정리해줘')">회의록 정리</button>
                </div>
            </div>
        `;

        clearWorkspace();
        showToast('새 세션이 시작되었습니다', 'success');
    }
}

function switchSession(sessionId) {
    if (!sessionId || !State.ws || !State.wsConnected) return;

    State.ws.send(JSON.stringify({
        type: 'switch_session',
        session_id: sessionId,
    }));
}

// ═══════════════════════════════════════
// File Attachments
// ═══════════════════════════════════════

function setupDragDrop() {
    const area = document.getElementById('chatInputArea');
    const overlay = document.getElementById('dragOverlay');
    let dragCounter = 0;

    area.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dragCounter++;
        area.classList.add('drag-over');
        overlay.style.display = 'flex';
    });

    area.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragCounter--;
        if (dragCounter <= 0) {
            dragCounter = 0;
            area.classList.remove('drag-over');
            overlay.style.display = 'none';
        }
    });

    area.addEventListener('dragover', (e) => {
        e.preventDefault();
    });

    area.addEventListener('drop', (e) => {
        e.preventDefault();
        dragCounter = 0;
        area.classList.remove('drag-over');
        overlay.style.display = 'none';
        if (e.dataTransfer.files.length > 0) {
            addFiles(e.dataTransfer.files);
        }
    });
}

function triggerFileSelect() {
    document.getElementById('fileInput').click();
}

function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        addFiles(files);
    }
    event.target.value = ''; // Reset so same file can be selected again
}

function addFiles(fileList) {
    for (const file of fileList) {
        if (file.size > MAX_FILE_SIZE) {
            showToast(`파일이 너무 큽니다: ${file.name} (최대 10MB)`, 'error');
            continue;
        }
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        const allowed = ['.txt','.csv','.json','.md','.xlsx','.pdf','.yaml','.yml','.py','.html','.xml','.tsv','.log','.conf','.ini','.toml'];
        if (!allowed.includes(ext)) {
            showToast(`지원하지 않는 파일 형식: ${ext}`, 'error');
            continue;
        }
        // Check duplicate
        if (State.pendingFiles.some(p => p.name === file.name && p.size === file.size)) {
            continue;
        }
        State.pendingFiles.push({ file, name: file.name, size: file.size });
    }
    renderAttachmentPreview();
    updateSendButton();
}

function removeAttachment(index) {
    State.pendingFiles.splice(index, 1);
    renderAttachmentPreview();
    updateSendButton();
}

function clearAttachments() {
    State.pendingFiles = [];
    State.uploadedFiles = [];
    renderAttachmentPreview();
}

function renderAttachmentPreview() {
    const container = document.getElementById('attachmentPreview');
    if (State.pendingFiles.length === 0) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    container.style.display = 'flex';
    container.innerHTML = State.pendingFiles.map((pf, i) => {
        const ext = '.' + pf.name.split('.').pop().toLowerCase();
        const icon = FILE_ICONS[ext] || FILE_ICONS['default'];
        return `
            <div class="attachment-chip">
                <span class="att-icon">${icon}</span>
                <span class="att-name" title="${escapeHtml(pf.name)}">${escapeHtml(pf.name)}</span>
                <span class="att-size">${formatFileSize(pf.size)}</span>
                <button class="att-remove" onclick="removeAttachment(${i})" title="삭제">&times;</button>
            </div>
        `;
    }).join('');
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const sessionId = State.sessionId || 'default';
    const res = await fetch(`${API_BASE}/api/v1/upload?session_id=${sessionId}`, {
        method: 'POST',
        body: formData,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
    }

    return await res.json();
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + 'B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB';
    return (bytes / (1024 * 1024)).toFixed(1) + 'MB';
}

// ═══════════════════════════════════════
// Utilities
// ═══════════════════════════════════════
function escapeHtml(text) {
    if (!text) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return String(text).replace(/[&<>"']/g, c => map[c]);
}

function formatTime(date) {
    return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function scrollToBottom(el) {
    requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 200);
    }, 3000);
}

// ═══════════════════════════════════════
// Start
// ═══════════════════════════════════════
document.addEventListener('DOMContentLoaded', init);
