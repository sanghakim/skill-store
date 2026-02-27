/**
 * SkillForge Dashboard - Real-time Monitoring
 *
 * Fetches from /api/v1/monitoring/* endpoints and renders
 * KPI cards, SVG charts, health panel, error list.
 * Auto-refreshes every 30 seconds.
 */

// ═══════════════════════════════════════
// Configuration
// ═══════════════════════════════════════

const API_BASE = '/api/v1/monitoring';
const REFRESH_INTERVAL = 30_000; // 30s
const AGENT_COLORS = {
    planner:      '#3b82f6',
    executor:     '#6366f1',
    reviewer:     '#22c55e',
    research:     '#06b6d4',
    creative:     '#a855f7',
    orchestrator: '#f59e0b',
};

// ═══════════════════════════════════════
// State
// ═══════════════════════════════════════

let refreshTimer = null;
let isRefreshing = false;

// ═══════════════════════════════════════
// Tooltip
// ═══════════════════════════════════════

const tooltip = (() => {
    let el = null;

    function init() {
        el = document.createElement('div');
        el.className = 'chart-tooltip';
        document.body.appendChild(el);

        document.addEventListener('mousemove', (e) => {
            if (!el.classList.contains('visible')) return;
            el.style.left = (e.clientX + 14) + 'px';
            el.style.top = (e.clientY - 10) + 'px';
        });
    }

    function show(html) {
        if (!el) init();
        el.innerHTML = html;
        el.classList.add('visible');
    }

    function hide() {
        if (el) el.classList.remove('visible');
    }

    return { show, hide, init };
})();


// ═══════════════════════════════════════
// API Helpers
// ═══════════════════════════════════════

async function fetchJSON(path) {
    try {
        const res = await fetch(API_BASE + path);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.warn(`[Dashboard] Fetch error ${path}:`, err.message);
        return null;
    }
}

function formatNumber(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
    return n.toString();
}

function formatUptime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
}

function formatTime(ts) {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

function formatTimeFull(ts) {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}


// ═══════════════════════════════════════
// KPI Cards
// ═══════════════════════════════════════

async function updateKPIs() {
    const [metrics, health] = await Promise.all([
        fetchJSON('/metrics'),
        fetchJSON('/health'),
    ]);

    if (metrics) {
        document.getElementById('kpiTotalRequests').textContent = formatNumber(metrics.requests.total);
        document.getElementById('kpiSuccessRate').textContent = metrics.requests.success_rate + '%';
        document.getElementById('kpiAvgLatency').textContent = Math.round(metrics.latency.avg_ms) + 'ms';
        document.getElementById('kpiTotalTokens').textContent = formatNumber(metrics.tokens.total);
    }

    if (health) {
        document.getElementById('kpiActiveSessions').textContent = health.active_sessions || 0;
    }
}


// ═══════════════════════════════════════
// Timeline Chart (SVG)
// ═══════════════════════════════════════

function renderTimeline(data) {
    const container = document.getElementById('timelineChart');
    if (!data || data.length === 0) {
        container.innerHTML = '<div class="chart-empty">데이터를 수집 중...</div>';
        return;
    }

    const W = container.clientWidth;
    const H = container.clientHeight || 200;
    const PAD = { top: 20, right: 16, bottom: 36, left: 48 };
    const chartW = W - PAD.left - PAD.right;
    const chartH = H - PAD.top - PAD.bottom;

    const maxReq = Math.max(1, ...data.map(d => d.requests));
    const barW = Math.max(4, Math.min(24, (chartW / data.length) - 2));
    const gap = (chartW - barW * data.length) / Math.max(1, data.length - 1);

    let svg = `<svg class="chart-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;

    // Grid lines
    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
        const y = PAD.top + (chartH / gridLines) * i;
        const val = Math.round(maxReq - (maxReq / gridLines) * i);
        svg += `<line x1="${PAD.left}" y1="${y}" x2="${W - PAD.right}" y2="${y}" stroke="#1f1f2a" stroke-width="1"/>`;
        svg += `<text x="${PAD.left - 8}" y="${y + 4}" fill="#6b7280" font-size="10" text-anchor="end" font-family="JetBrains Mono">${val}</text>`;
    }

    // Bars
    data.forEach((d, i) => {
        const x = PAD.left + i * (barW + gap);
        const successH = (d.requests / maxReq) * chartH;
        const errorH = (d.errors / maxReq) * chartH;
        const yBase = PAD.top + chartH;

        // Success bar
        svg += `<rect class="timeline-bar" x="${x}" y="${yBase - successH}" width="${barW}" height="${successH}" rx="2" fill="#6366f1" opacity="0.8"
            onmouseenter="tooltip.show('<div class=\\'tt-label\\'>${formatTime(d.timestamp)}</div><div class=\\'tt-value\\'>${d.requests} 요청 / ${d.errors} 오류</div><div style=\\'font-size:10px;color:#9ca3af\\'>avg ${d.avg_latency_ms}ms</div>')"
            onmouseleave="tooltip.hide()"/>`;

        // Error overlay
        if (d.errors > 0) {
            svg += `<rect class="timeline-error-bar" x="${x}" y="${yBase - errorH}" width="${barW}" height="${errorH}" rx="2" fill="#ef4444" opacity="0.9"/>`;
        }

        // Time labels (every 5th or at edges)
        if (i === 0 || i === data.length - 1 || i % 5 === 0) {
            svg += `<text x="${x + barW / 2}" y="${H - 6}" fill="#6b7280" font-size="10" text-anchor="middle" font-family="JetBrains Mono">${formatTime(d.timestamp)}</text>`;
        }
    });

    svg += '</svg>';
    container.innerHTML = svg;
}


// ═══════════════════════════════════════
// Agent Performance
// ═══════════════════════════════════════

function renderAgents(data) {
    const container = document.getElementById('agentChart');
    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<div class="chart-empty">데이터를 수집 중...</div>';
        return;
    }

    const agents = Object.entries(data).sort((a, b) => b[1].count - a[1].count);
    const maxCount = Math.max(1, ...agents.map(([, v]) => v.count));

    let html = '<div style="width:100%; display:flex; flex-direction:column; gap:0;">';

    agents.forEach(([name, stats]) => {
        const pct = (stats.count / maxCount) * 100;
        const color = AGENT_COLORS[name] || '#6b7280';

        html += `
            <div class="agent-row">
                <span class="agent-name">${name}</span>
                <div class="agent-bar-wrap">
                    <div class="agent-bar" style="width: ${pct}%; background: ${color};"></div>
                </div>
                <span class="agent-stats">
                    <span>${stats.count}x</span>
                    <span>${Math.round(stats.avg_time_ms)}ms</span>
                </span>
            </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
}


// ═══════════════════════════════════════
// Skill Usage
// ═══════════════════════════════════════

function renderSkills(data) {
    const container = document.getElementById('skillChart');
    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<div class="chart-empty">데이터를 수집 중...</div>';
        return;
    }

    const skills = Object.entries(data)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 10);
    const maxCount = Math.max(1, ...skills.map(([, v]) => v.count));

    let html = '<div style="width:100%; display:flex; flex-direction:column; gap:0;">';

    skills.forEach(([name, stats]) => {
        const pct = (stats.count / maxCount) * 100;

        html += `
            <div class="skill-row">
                <span class="skill-name" title="${name}">${name}</span>
                <div class="skill-bar-wrap">
                    <div class="skill-bar" style="width: ${pct}%;"></div>
                </div>
                <span class="skill-count">${stats.count}</span>
            </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
}


// ═══════════════════════════════════════
// System Health
// ═══════════════════════════════════════

function renderHealth(data) {
    const container = document.getElementById('healthPanel');
    if (!data) {
        container.innerHTML = '<div class="chart-empty">데이터를 수집 중...</div>';
        return;
    }

    function statusDot(status) {
        const colorMap = { healthy: 'green', online: 'green', connected: 'green', degraded: 'yellow', error: 'red', unknown: 'gray' };
        return `<span class="health-dot ${colorMap[status] || 'gray'}"></span>`;
    }

    function statusLabel(status) {
        const labelMap = {
            healthy: '정상',
            online: '온라인',
            connected: '연결됨',
            degraded: '저하',
            error: '오류',
            unknown: '확인 중',
        };
        return labelMap[status] || status;
    }

    const items = [
        {
            label: '시스템 상태',
            status: data.status || 'unknown',
            value: statusLabel(data.status || 'unknown'),
        },
        {
            label: 'LLM 서비스',
            status: data.llm === 'connected' ? 'connected' : data.llm === 'unknown' ? 'unknown' : 'error',
            value: statusLabel(data.llm === 'connected' ? 'connected' : data.llm || 'unknown'),
        },
        {
            label: '로드된 스킬',
            status: data.skills_loaded > 0 ? 'healthy' : 'unknown',
            value: `${data.skills_loaded}개`,
        },
        {
            label: '활성 세션',
            status: 'healthy',
            value: `${data.active_sessions || 0}개`,
        },
        {
            label: '업타임',
            status: 'healthy',
            value: formatUptime(data.uptime_seconds || 0),
        },
        {
            label: '총 요청',
            status: data.error_rate > 10 ? 'degraded' : 'healthy',
            value: `${data.total_requests || 0} (오류율 ${data.error_rate || 0}%)`,
        },
    ];

    let html = '<div class="health-grid">';
    items.forEach(item => {
        html += `
            <div class="health-item" data-status="${item.status}">
                <span class="health-label">${item.label}</span>
                <span class="health-value">
                    ${item.value}
                    ${statusDot(item.status)}
                </span>
            </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}


// ═══════════════════════════════════════
// Recent Errors
// ═══════════════════════════════════════

function renderErrors(errors) {
    const container = document.getElementById('errorList');
    const countEl = document.getElementById('errorCount');

    if (!errors || errors.length === 0) {
        container.innerHTML = `
            <div class="no-errors">
                <span class="icon">&#10004;</span>
                <span class="text">오류가 없습니다</span>
            </div>`;
        countEl.textContent = '0건';
        return;
    }

    countEl.textContent = errors.length + '건';

    let html = '';
    errors.forEach(err => {
        html += `
            <div class="error-item">
                <span class="error-time">${formatTimeFull(err.timestamp)}</span>
                <span class="error-code">${err.code}</span>
                <span class="error-message">${escapeHtml(err.message)}</span>
            </div>`;
    });

    container.innerHTML = html;
}

function escapeHtml(str) {
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
}


// ═══════════════════════════════════════
// Quality Histogram
// ═══════════════════════════════════════

function renderQuality(data) {
    const container = document.getElementById('qualityChart');
    if (!data || data.total === 0) {
        container.innerHTML = '<div class="chart-empty">데이터를 수집 중...</div>';
        return;
    }

    const { labels, counts } = data;
    const maxCount = Math.max(1, ...counts);

    let html = '<div class="quality-chart">';

    counts.forEach((count, i) => {
        const pct = (count / maxCount) * 100;
        const hue = (i / 9) * 120; // red(0) → green(120)
        const color = `hsl(${hue}, 65%, 55%)`;

        html += `
            <div class="quality-bar-group">
                <span class="quality-bar-count">${count || ''}</span>
                <div class="quality-bar" style="height: ${Math.max(2, pct)}%; background: ${color};"
                     onmouseenter="tooltip.show('<div class=\\'tt-label\\'>${labels[i]}</div><div class=\\'tt-value\\'>${count}건</div>')"
                     onmouseleave="tooltip.hide()"></div>
                <span class="quality-bar-label">${labels[i]}</span>
            </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
}


// ═══════════════════════════════════════
// Refresh Cycle
// ═══════════════════════════════════════

async function refreshAll() {
    if (isRefreshing) return;
    isRefreshing = true;

    const btn = document.querySelector('.btn-refresh');
    if (btn) btn.classList.add('spinning');

    const dot = document.getElementById('refreshDot');
    if (dot) dot.style.background = '#f59e0b';

    try {
        // Fetch all data in parallel
        const [metrics, health, timeline, agents, skills, errors, quality] = await Promise.all([
            fetchJSON('/metrics'),
            fetchJSON('/health'),
            fetchJSON('/timeline'),
            fetchJSON('/agents'),
            fetchJSON('/skills'),
            fetchJSON('/errors'),
            fetchJSON('/quality'),
        ]);

        // Update KPIs
        if (metrics) {
            document.getElementById('kpiTotalRequests').textContent = formatNumber(metrics.requests.total);
            document.getElementById('kpiSuccessRate').textContent = metrics.requests.success_rate + '%';
            document.getElementById('kpiAvgLatency').textContent = Math.round(metrics.latency.avg_ms) + 'ms';
            document.getElementById('kpiTotalTokens').textContent = formatNumber(metrics.tokens.total);
        }
        if (health) {
            document.getElementById('kpiActiveSessions').textContent = health.active_sessions || 0;
        }

        // Render charts
        renderTimeline(timeline ? timeline.timeline : []);
        renderAgents(agents ? agents.agents : {});
        renderSkills(skills ? skills.skills : {});
        renderHealth(health);
        renderErrors(errors ? errors.errors : []);
        renderQuality(quality);

    } catch (err) {
        console.error('[Dashboard] Refresh error:', err);
    } finally {
        isRefreshing = false;
        if (btn) {
            setTimeout(() => btn.classList.remove('spinning'), 800);
        }
        if (dot) dot.style.background = '#22c55e';
    }
}


// ═══════════════════════════════════════
// Countdown Display
// ═══════════════════════════════════════

function startCountdown() {
    let remaining = REFRESH_INTERVAL / 1000;
    const textEl = document.getElementById('refreshText');

    function tick() {
        if (textEl) {
            textEl.textContent = `${remaining}s 자동 새로고침`;
        }
        remaining--;

        if (remaining < 0) {
            remaining = REFRESH_INTERVAL / 1000;
            refreshAll();
        }
    }

    tick();
    setInterval(tick, 1000);
}


// ═══════════════════════════════════════
// Window Resize Handler
// ═══════════════════════════════════════

let resizeTimeout = null;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        // Re-render charts that depend on container size
        refreshAll();
    }, 300);
});


// ═══════════════════════════════════════
// Init
// ═══════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    tooltip.init();
    refreshAll();
    startCountdown();
});
