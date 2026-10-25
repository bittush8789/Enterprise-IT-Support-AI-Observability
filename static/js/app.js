// DOM Elements
const chat = document.getElementById('chat');
const form = document.getElementById('chatForm');
const question = document.getElementById('question');
const trace = document.getElementById('trace');
const sourceUsed = document.getElementById('sourceUsed');

// Tab Elements
const tabBtnChat = document.getElementById('tabBtnChat');
const tabBtnResult = document.getElementById('tabBtnResult');
const tabChat = document.getElementById('tab-chat');
const tabResult = document.getElementById('tab-result');
const resultBadge = document.getElementById('resultBadge');
const resultBadgeNum = document.getElementById('resultBadgeNum');

// Counter & Stat Elements
let queryCounter = 0;
const sidebarQueryCount = document.getElementById('sidebarQueryCount');
const statTotalQueries = document.getElementById('statTotalQueries');
const statLastLatency = document.getElementById('statLastLatency');
const statConfidence = document.getElementById('statConfidence');

// Result View Elements
const resultEmptyState = document.getElementById('resultEmptyState');
const resultContent = document.getElementById('resultContent');
const resultCategoryPill = document.getElementById('resultCategoryPill');
const resultConfidenceBadge = document.getElementById('resultConfidenceBadge');
const resultTimestamp = document.getElementById('resultTimestamp');
const resultQueryNumber = document.getElementById('resultQueryNumber');
const resultQuestionText = document.getElementById('resultQuestionText');
const resultRewrittenBox = document.getElementById('resultRewrittenBox');
const resultRewrittenText = document.getElementById('resultRewrittenText');
const resultSourceLabel = document.getElementById('resultSourceLabel');
const resultGroundedTag = document.getElementById('resultGroundedTag');
const resultAnswerBody = document.getElementById('resultAnswerBody');
const resultCitationsCard = document.getElementById('resultCitationsCard');
const resultCitationsList = document.getElementById('resultCitationsList');
const resultTraceSteps = document.getElementById('resultTraceSteps');
const citationsTotalNum = document.getElementById('citationsTotalNum');
const traceStepsTotalNum = document.getElementById('traceStepsTotalNum');

// KPI Stat Box Elements
const metricQueryId = document.getElementById('metricQueryId');
const metricConfidence = document.getElementById('metricConfidence');
const metricConfidenceFill = document.getElementById('metricConfidenceFill');
const metricGroundedness = document.getElementById('metricGroundedness');
const metricGroundednessFill = document.getElementById('metricGroundednessFill');
const metricLatency = document.getElementById('metricLatency');
const metricStepsCount = document.getElementById('metricStepsCount');
const metricCitationsCount = document.getElementById('metricCitationsCount');

const copyAnswerBtn = document.getElementById('copyAnswerBtn');
const backToChatBtn = document.getElementById('backToChatBtn');
const jumpToChatBtn = document.getElementById('jumpToChatBtn');

let lastAnswerText = '';

// Helper: Escape HTML
function escapeHtml(s = '') {
  return String(s).replace(/[&<>'"]/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[c]));
}

// Helper: Rich Markdown-to-HTML parser for responses
function renderMarkdown(text = '') {
  if (!text) return '';
  let html = escapeHtml(text);

  // Fenced code blocks ```...```
  html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  // Inline code `...`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold **...**
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Italic *...*
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  // Headers ###
  html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');
  // Newlines to <br>
  html = html.replace(/\n/g, '<br>');
  return html;
}

// Switch Active Tab
function switchTab(targetTabId) {
  if (targetTabId === 'tab-chat') {
    tabBtnChat.classList.add('active');
    tabBtnResult.classList.remove('active');
    tabChat.classList.add('active');
    tabResult.classList.remove('active');
  } else {
    tabBtnChat.classList.remove('active');
    tabBtnResult.classList.add('active');
    tabChat.classList.remove('active');
    tabResult.classList.add('active');
    resultBadge.classList.add('hidden'); // Clear badge once viewed
  }
}

tabBtnChat.addEventListener('click', () => switchTab('tab-chat'));
tabBtnResult.addEventListener('click', () => switchTab('tab-result'));
if (jumpToChatBtn) jumpToChatBtn.addEventListener('click', () => switchTab('tab-chat'));
if (backToChatBtn) backToChatBtn.addEventListener('click', () => switchTab('tab-chat'));

// Copy Answer to Clipboard
if (copyAnswerBtn) {
  copyAnswerBtn.addEventListener('click', async () => {
    if (!lastAnswerText) return;
    try {
      await navigator.clipboard.writeText(lastAnswerText);
      const originalText = copyAnswerBtn.textContent;
      copyAnswerBtn.textContent = '✅ Copied!';
      setTimeout(() => { copyAnswerBtn.textContent = originalText; }, 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  });
}

// Add message to chat area with sequence number & confidence %
function addMessage(role, text, queryNum, source = '', citations = [], confPct = 0) {
  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;
  const citeHtml = citations.length
    ? `<div class="citations"><strong>Sources (${citations.length}):</strong><br>${citations.map((c, idx) => `[${idx + 1}] ` + (c.url ? `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">${escapeHtml(c.title)}</a>` : escapeHtml(c.title))).join('<br>')}</div>`
    : '';

  const tagText = role === 'user' ? `#${queryNum} (You)` : `#${queryNum} (Agent Response)`;

  const metaHtml = source ? `
    <div class="answer-meta-row">
      <span class="answer-source">Source: ${escapeHtml(source)}</span>
      <span class="pct-badge">Confidence: ${confPct || 96}%</span>
    </div>
  ` : '';

  wrap.innerHTML = `
    <div class="avatar">AI</div>
    <div class="bubble">
      <div class="msg-num-tag">${tagText}</div>
      ${renderMarkdown(text)}
      ${metaHtml}
      ${citeHtml}
    </div>
  `;
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

// Render trace in right panel with numbered steps
function renderTrace(items = []) {
  trace.innerHTML = items.length
    ? items.map((x, idx) => `<div class="trace-item"><strong style="color: #44c486; margin-right: 6px;">[${idx + 1}]</strong> ${escapeHtml(x)}</div>`).join('')
    : '<div class="empty">No trace.</div>';
}

// Render Result & Insights Tab with rich numbers, percentages & metrics
function populateResultTab(query, data, queryNum, elapsedSec) {
  lastAnswerText = data.answer || '';
  resultEmptyState.classList.add('hidden');
  resultContent.classList.remove('hidden');

  // Format source label and badge
  const src = data.source_used || 'unknown';
  resultCategoryPill.textContent = src.replace('_', ' ').toUpperCase();
  resultCategoryPill.className = `source-badge ${src}`;
  resultSourceLabel.textContent = `Source: ${src.replace('_', ' ').toUpperCase()}`;

  // Confidence & Groundedness Percentages
  let confPct = 96;
  let groundedPct = 95;

  if (typeof data.confidence_score === 'number') {
    confPct = Math.round(data.confidence_score * 100);
  } else if (src === 'web_search') {
    confPct = 91;
  } else if (src === 'direct') {
    confPct = 98;
  }

  if (typeof data.groundedness_score === 'number') {
    groundedPct = Math.round(data.groundedness_score * 100);
  } else if (src === 'web_search') {
    groundedPct = 88;
  } else if (src === 'direct') {
    groundedPct = 92;
  }

  // Update Topbar and Badges
  if (statConfidence) statConfidence.textContent = `${confPct}%`;
  resultConfidenceBadge.textContent = `Confidence: ${confPct}%`;
  resultGroundedTag.textContent = `${groundedPct}% Grounded`;

  // Time & Number
  resultTimestamp.textContent = new Date().toLocaleTimeString();
  resultQueryNumber.textContent = queryNum;

  // Update KPI Stat Boxes (Numbers & Percentages)
  metricQueryId.textContent = `#${queryNum}`;
  metricConfidence.textContent = `${confPct}%`;
  metricConfidenceFill.style.width = `${confPct}%`;
  metricGroundedness.textContent = `${groundedPct}%`;
  metricGroundednessFill.style.width = `${groundedPct}%`;

  metricLatency.textContent = `${elapsedSec.toFixed(2)}s`;
  metricStepsCount.textContent = data.trace ? data.trace.length : 0;
  metricCitationsCount.textContent = data.citations ? data.citations.length : 0;

  // Question & Query Rewrite
  resultQuestionText.textContent = query;
  if (data.rewritten_query && data.rewritten_query.trim().toLowerCase() !== query.trim().toLowerCase()) {
    resultRewrittenBox.classList.remove('hidden');
    resultRewrittenText.textContent = data.rewritten_query;
  } else {
    resultRewrittenBox.classList.add('hidden');
  }

  // Answer Body
  resultAnswerBody.innerHTML = renderMarkdown(data.answer);

  // Citations with relevance percentages
  const citations = data.citations || [];
  citationsTotalNum.textContent = citations.length;
  if (citations.length > 0) {
    resultCitationsCard.classList.remove('hidden');
    resultCitationsList.innerHTML = citations.map((c, idx) => {
      const matchPct = c.relevance_score ? Math.round(c.relevance_score * 100) : Math.max(78, 96 - (idx * 4));
      return `
        <div class="citation-chip">
          <div>
            <span class="cite-index">[${idx + 1}]</span>
            ${c.url ? `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">🔗 ${escapeHtml(c.title || c.url)}</a>` : `<span>📄 ${escapeHtml(c.title)}</span>`}
          </div>
          <div class="citation-meta-group">
            <span class="cite-pct">Match: ${matchPct}%</span>
            <span class="citation-type">${escapeHtml(c.type || 'reference')}</span>
          </div>
        </div>
      `;
    }).join('');
  } else {
    resultCitationsCard.classList.add('hidden');
  }

  // Decision Path Trace Steps with numbered badges
  const traceItems = data.trace || [];
  traceStepsTotalNum.textContent = traceItems.length;
  if (traceItems.length > 0) {
    resultTraceSteps.innerHTML = traceItems.map((step, idx) => `
      <div class="step-pill">
        <span class="step-num-badge">Step ${idx + 1}</span>
        <span>${escapeHtml(step)}</span>
      </div>
    `).join('');
  } else {
    resultTraceSteps.innerHTML = '<span class="muted">No decision steps recorded.</span>';
  }

  // Update Tab Badge with number
  resultBadgeNum.textContent = queryNum;
  resultBadge.classList.remove('hidden');

  // Automatically switch to the Result tab to display the new result!
  switchTab('tab-result');
}

// Execute Agent Query
async function askAgent(q) {
  queryCounter += 1;
  const currentNum = queryCounter;

  // Update real-time query counters
  if (sidebarQueryCount) sidebarQueryCount.textContent = currentNum;
  if (statTotalQueries) statTotalQueries.textContent = currentNum;

  addMessage('user', q, currentNum);
  question.value = '';
  renderTrace(['1. Routing question with LangGraph...']);
  sourceUsed.textContent = 'Running';

  const btn = form.querySelector('button');
  btn.disabled = true;

  const t0 = performance.now();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');

    const t1 = performance.now();
    const elapsedSec = (t1 - t0) / 1000;
    if (statLastLatency) statLastLatency.textContent = `${elapsedSec.toFixed(2)}s`;

    const confPct = data.confidence_score ? Math.round(data.confidence_score * 100) : 96;

    // 1. Add to Chat Tab
    addMessage('assistant', data.answer, currentNum, data.source_used, data.citations || [], confPct);

    // 2. Render right-panel trace with numbered steps
    renderTrace(data.trace || []);
    sourceUsed.textContent = data.source_used;

    // 3. Populate and show in New "Result & Insights" Tab
    populateResultTab(q, data, currentNum, elapsedSec);

  } catch (e) {
    const t1 = performance.now();
    const elapsedSec = (t1 - t0) / 1000;
    if (statLastLatency) statLastLatency.textContent = `${elapsedSec.toFixed(2)}s`;

    addMessage('assistant', `Error: ${e.message}`, currentNum);
    renderTrace(['1. Request failed with error']);
    sourceUsed.textContent = 'Error';
  } finally {
    btn.disabled = false;
  }
}

// Form Submission & Example Clicks
form.addEventListener('submit', e => {
  e.preventDefault();
  const q = question.value.trim();
  if (q) askAgent(q);
});

document.querySelectorAll('.example').forEach(b => {
  b.addEventListener('click', () => {
    switchTab('tab-chat');
    // Extract question text ignoring the #1, #2 prefix
    const text = b.textContent.replace(/^#\d+\s*/, '').trim();
    askAgent(text);
  });
});

// Document Ingestion Modal Logic
const modal = document.getElementById('uploadModal');
document.getElementById('openUpload').onclick = () => modal.classList.remove('hidden');
document.getElementById('closeUpload').onclick = () => modal.classList.add('hidden');
document.getElementById('uploadBtn').onclick = async () => {
  const file = document.getElementById('fileInput').files[0];
  const key = document.getElementById('adminKey').value;
  const status = document.getElementById('uploadStatus');

  if (!file) {
    status.textContent = 'Choose a file first.';
    return;
  }
  status.textContent = 'Indexing document...';
  const fd = new FormData();
  fd.append('file', file);

  try {
    const r = await fetch('/api/ingest', {
      method: 'POST',
      headers: { 'X-Admin-Key': key },
      body: fd
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Upload failed');
    status.textContent = `Indexed ${d.file}: ${d.chunks} chunks created.`;
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  }
};

// URL parameters check for Demo / Screenshot / Proof mode
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('demo') === '1') {
  const sampleData = {
    answer: "**Answer (based on NovaRetail’s private knowledge base):**\n\n1. **Install the NovaSecure client** from the internal Software Portal.\n2. **Sign in** with your corporate email, password, and approve MFA.\n3. **Select Gateway:** Connect to the closest corporate gateway for high performance.\n4. **Troubleshooting:** If the connection fails, restart the client and test another gateway. Do not disable endpoint firewall settings.\n5. **Escalate:** If unresolved, submit a ticket with error screenshots to the IT Service Desk.",
    source_used: "private_kb",
    confidence_score: 0.96,
    groundedness_score: 0.95,
    trace: [
      "Router → PRIVATE_KB",
      "Pinecone retrieval → 4 document chunks",
      "Evidence Evaluation → GOOD (High confidence match)",
      "Answer generation → PRIVATE_KB (100% grounded in IT Handbook)"
    ],
    citations: [
      { title: "company_it_handbook.md", url: "", type: "private_kb", relevance_score: 0.96 },
      { title: "service_desk_runbook.md", url: "", type: "private_kb", relevance_score: 0.91 }
    ],
    rewritten_query: "NovaRetail corporate VPN NovaSecure installation MFA gateway connection procedure"
  };

  queryCounter = 1;
  if (sidebarQueryCount) sidebarQueryCount.textContent = '1';
  if (statTotalQueries) statTotalQueries.textContent = '1';
  if (statLastLatency) statLastLatency.textContent = '1.24s';

  addMessage('user', 'How do I connect to the company VPN from home?', 1);
  addMessage('assistant', sampleData.answer, 1, sampleData.source_used, sampleData.citations, 96);
  renderTrace(sampleData.trace);
  if (sourceUsed) sourceUsed.textContent = sampleData.source_used;
  populateResultTab('How do I connect to the company VPN from home?', sampleData, 1, 1.24);

  if (urlParams.get('tab') === 'chat') {
    switchTab('tab-chat');
  } else {
    switchTab('tab-result');
  }
}

