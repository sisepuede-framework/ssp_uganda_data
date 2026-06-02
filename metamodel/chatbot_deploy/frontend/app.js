/**
 * Uganda Climate Policy Simulator — Frontend
 * ============================================
 * Pure vanilla JS — no framework, no build step.
 * Edit freely. Each function has a single responsibility.
 *
 * State is kept in a simple object. The server is stateless — we send
 * the full conversation history with every request.
 *
 * To add a new feature:
 *   - New API call → add a function in the "API" section below
 *   - New UI element → add HTML in index.html, render function here
 *   - New metric type → add to METRIC_CONFIG below
 */

// ── Configuration ─────────────────────────────────────────────────────────

const API_BASE = "";  // Empty = same origin. Change to "http://localhost:8000" for dev.


// ── App state ─────────────────────────────────────────────────────────────

const state = {
  conversationHistory: [],  // [{role, content}] — sent to server each turn
  isLoading: false,
  lastSimulation: null,     // persists the most recent simulation result for follow-up renders
};

// ── Preset messages ───────────────────────────────────────────────────────

const PRESETS = {
  bau: "Run a Business as Usual simulation — what happens to Uganda's emissions, costs, and co-benefits if current minimal policies continue?",
  netzero: "Run a Net Zero scenario — what would Uganda's emissions and costs look like if all climate policies are implemented at maximum ambition?",
  compare: "Compare Business as Usual against Net Zero. Show me the difference in emissions, costs, and co-benefits.",
};

function sendPreset(key) {
  const message = PRESETS[key];
  document.getElementById("chat-input").value = message;
  sendMessage();
}

// ── API calls ─────────────────────────────────────────────────────────────

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    const badge = document.getElementById("model-status");
    if (data.model_loaded) {
      badge.textContent = "✓ Model ready";
      badge.classList.add("ready");
    } else {
      badge.textContent = "⚠ Model not loaded";
    }
  } catch {
    document.getElementById("model-status").textContent = "⚠ Server offline";
  }
}

async function sendChatRequest(messages) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Chat logic ────────────────────────────────────────────────────────────

function handleInputKey(event) {
  // Submit on Enter (without Shift)
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

async function sendMessage() {
  if (state.isLoading) return;

  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  setLoading(true);

  // Add user message to UI + history
  appendMessage("user", text);
  state.conversationHistory.push({ role: "user", content: text });

  try {
    const response = await sendChatRequest(state.conversationHistory);

    // Add assistant reply to UI + history
    if (response.simulation) state.lastSimulation = response.simulation;
    appendMessage("assistant", response.reply, response.simulation || null);
    state.conversationHistory.push({ role: "assistant", content: response.reply });

  } catch (error) {
    appendMessage("assistant", `⚠ Error: ${error.message}. Please check the server is running and try again.`);
  } finally {
    setLoading(false);
  }
}

// ── UI rendering ──────────────────────────────────────────────────────────

function appendMessage(role, content, simulationData = null) {
  const container = document.getElementById("chat-messages");

  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}-message`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "user" ? "You" : "UG";

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";

  // Strip chart block and variable lines from text before rendering (assistant only)
  let chartData = null;
  let varPairs  = [];
  let displayContent = content;
  if (role === "assistant") {
    const extracted = extractChartBlock(content);
    displayContent  = extracted.cleanText;
    chartData       = extracted.chartData;

    const varExtracted = extractVariableLines(displayContent);
    displayContent = varExtracted.cleanText;
    varPairs       = varExtracted.pairs;
  }

  contentDiv.innerHTML = formatMessageContent(displayContent);

  // Variable table — rendered before the chart, directly below prose
  if (varPairs.length > 0) {
    renderVariableTable(contentDiv, varPairs);
  }

  // Insert into DOM first so Chart.js can read canvas dimensions correctly
  msgDiv.appendChild(avatar);
  msgDiv.appendChild(contentDiv);
  container.appendChild(msgDiv);

  // Fall back to last simulation when this response has no new simulation data
  const effectiveSimData = simulationData || (role === "assistant" ? state.lastSimulation : null);

  // Sector stacked area chart — rendered after DOM insertion so canvas has real dimensions
  const hasSectors = effectiveSimData && effectiveSimData.sector_comparison;
  if (hasSectors) {
    renderStackedSectorChart(contentDiv, effectiveSimData.sector_comparison);
  }

  // Projected year totals — shown below stacked chart when sector data present
  if (hasSectors) {
    renderProjectedTotals(contentDiv, effectiveSimData.sector_comparison);
  }

  // Cost/benefit diverging bar chart — benefits up, costs down, by year
  if (effectiveSimData && effectiveSimData.cost_benefit_comparison) {
    renderCostBenefitChart(contentDiv, effectiveSimData.cost_benefit_comparison);
  }

  // Follow-up suggestion chips — outside the bubble, below the message row
  if (hasSectors) {
    renderFollowUpChips(container, msgDiv);
  }

  // Scroll to bottom
  container.scrollTop = container.scrollHeight;
}

/**
 * Convert plain text with markdown-like syntax to HTML.
 * Supports: tables, **bold**, *italic*, bullet lists, numbered lists, line breaks.
 */
function formatMessageContent(text) {
  // Escape HTML
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Extract markdown tables before paragraph processing so they don't get
  // wrapped in <p> tags or have newlines converted to <br>.
  const tables = [];
  html = html.replace(/((?:^[ \t]*\|[^\n]+\n?)+)/gm, (block) => {
    tables.push(_parseMdTable(block));
    return `\x00TABLE_${tables.length - 1}\x00`;
  });

  // Headings: ### h3, ## h2, # h1 — must run before bold so ** inside headers works
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm,  "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm,   "<h1>$1</h1>");
  // Bold: **text** — [^*\n]+ avoids crossing asterisks or line breaks
  html = html.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  // Italic: *text*
  html = html.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
  // Bullet lists: lines starting with - or •
  html = html.replace(/^[-•] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>");
  // Numbered lists
  html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");
  // Paragraph breaks (double newline)
  html = html.replace(/\n\n/g, "</p><p>");
  // Single newlines
  html = html.replace(/\n/g, "<br>");

  html = `<p>${html}</p>`;

  // Re-insert rendered tables — replace whole <p>PLACEHOLDER</p> so the
  // table sits as a block sibling, not nested inside a paragraph.
  html = html.replace(/<p>\x00TABLE_(\d+)\x00<\/p>/g, (_, i) => tables[parseInt(i, 10)]);
  html = html.replace(/\x00TABLE_(\d+)\x00/g, (_, i) => tables[parseInt(i, 10)]);

  return html;
}

/**
 * Convert a raw markdown table block (already HTML-escaped) into a <table>.
 * The separator row (|---|---|) is detected and skipped.
 */
function _parseMdTable(block) {
  const rows = block.trim().split("\n").map(r => r.trim()).filter(Boolean);
  if (rows.length < 1) return block;

  let html = '<table class="md-table">';
  let bodyOpen = false;

  rows.forEach((row, i) => {
    // Separator row: only dashes, pipes, colons, spaces
    if (/^\|[\s\-:|]+\|$/.test(row)) {
      if (!bodyOpen) { html += "<tbody>"; bodyOpen = true; }
      return;
    }
    const cells = row.replace(/^\||\|$/g, "").split("|").map(c => {
      let s = c.trim();
      s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
      s = s.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
      return s;
    });
    if (i === 0) {
      html += "<thead><tr>" + cells.map(c => `<th>${c}</th>`).join("") + "</tr></thead>";
    } else {
      if (!bodyOpen) { html += "<tbody>"; bodyOpen = true; }
      html += "<tr>" + cells.map(c => `<td>${c}</td>`).join("") + "</tr>";
    }
  });

  if (bodyOpen) html += "</tbody>";
  html += "</table>";
  return html;
}

const THINKING_PHRASES = [
  "Running the model…",
  "Crunching 1,933 scenarios…",
  "Consulting the surrogate…",
  "Simulating Uganda's future…",
  "Checking the LHS samples…",
  "Computing emissions trajectory…",
  "Asking the XGBoost oracle…",
  "Projecting to 2070…",
  "Comparing against BAU…",
  "Almost there…",
];

let _thinkingTimer = null;

function setLoading(loading) {
  state.isLoading = loading;
  const indicator = document.getElementById("typing-indicator");
  const btn       = document.getElementById("send-btn");
  const input     = document.getElementById("chat-input");
  const textEl    = document.getElementById("thinking-text");

  if (loading) {
    // Pick a random starting phrase, then cycle every 3 s
    let idx = Math.floor(Math.random() * THINKING_PHRASES.length);
    textEl.textContent = THINKING_PHRASES[idx];

    _thinkingTimer = setInterval(() => {
      idx = (idx + 1) % THINKING_PHRASES.length;
      textEl.textContent = THINKING_PHRASES[idx];
    }, 3000);

    indicator.classList.remove("hidden");
    btn.disabled   = true;
    input.disabled = true;
    document.getElementById("chat-messages").scrollTop = 99999;
  } else {
    clearInterval(_thinkingTimer);
    _thinkingTimer = null;

    indicator.classList.add("hidden");
    btn.disabled   = false;
    input.disabled = false;
    input.focus();
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Find and strip lines matching "variable_name = value" from raw text.
 * A valid line: identifier chars (a-z, 0-9, _) = any non-empty value.
 * Returns { cleanText: string, pairs: [{name, value}] }.
 *
 * Lines are removed from cleanText so they don't also appear as prose.
 */
function extractVariableLines(text) {
  // Match lines of the form:  some_variable_name = 0.1234  (leading whitespace ok)
  const re = /^[ \t]*([a-zA-Z_][a-zA-Z0-9_]*)[ \t]*=[ \t]*([^\n]+)$/gm;
  const pairs = [];
  const seen = new Set();

  let match;
  while ((match = re.exec(text)) !== null) {
    const name  = match[1].trim();
    const value = match[2].trim();
    // Skip duplicates (same name) — keep first occurrence
    if (!seen.has(name)) {
      seen.add(name);
      pairs.push({ name, value });
    }
  }

  if (pairs.length === 0) return { cleanText: text, pairs: [] };

  // Strip matched lines from text, then clean up orphaned blank lines
  const cleanText = text
    .replace(/^[ \t]*[a-zA-Z_][a-zA-Z0-9_]*[ \t]*=[ \t]*[^\n]+$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return { cleanText, pairs };
}

/**
 * Render a compact variable-name = value table inside a message bubble.
 */
function renderVariableTable(container, pairs) {
  const wrapper = document.createElement("div");
  wrapper.className = "var-table-wrapper";

  const label = document.createElement("div");
  label.className = "var-table-label";
  label.textContent = "variables changed";
  wrapper.appendChild(label);

  const table = document.createElement("table");
  table.className = "var-table";

  for (const { name, value } of pairs) {
    const tr = document.createElement("tr");
    const tdName = document.createElement("td");
    tdName.className = "var-name";
    tdName.textContent = name;

    const tdVal = document.createElement("td");
    tdVal.className = "var-value";
    tdVal.textContent = value;

    tr.appendChild(tdName);
    tr.appendChild(tdVal);
    table.appendChild(tr);
  }

  wrapper.appendChild(table);
  container.appendChild(wrapper);
}

/**
 * Render follow-up suggestion chips below a message row (outside the bubble).
 * Each chip fires sendMessage() with its suggestion text when clicked.
 */
function renderFollowUpChips(container, afterNode) {
  const SUGGESTIONS = [
    "Show sector breakdown",
    "What if GDP grows faster?",
    "What drives the biggest emission reductions?",
  ];

  const row = document.createElement("div");
  row.className = "followup-chips";

  for (const text of SUGGESTIONS) {
    const btn = document.createElement("button");
    btn.className = "followup-chip";
    btn.textContent = text;
    btn.addEventListener("click", () => {
      document.getElementById("chat-input").value = text;
      sendMessage();
    });
    row.appendChild(btn);
  }

  // Insert immediately after the message row that triggered this
  if (afterNode.nextSibling) {
    container.insertBefore(row, afterNode.nextSibling);
  } else {
    container.appendChild(row);
  }
}

/**
 * Find and strip the first ```chart ... ``` fenced block from raw text.
 * Returns { cleanText: string, chartData: object|null }.
 * On JSON parse failure the block is stripped but chartData is null.
 */
function extractChartBlock(text) {
  // Match ```chart ... ``` (greedy-safe, handles Windows line endings)
  const re = /```chart\s*([\s\S]*?)```/;
  const match = text.match(re);
  if (!match) return { cleanText: text, chartData: null };

  const cleanText = text.replace(match[0], "").replace(/\n{3,}/g, "\n\n").trim();
  try {
    const chartData = JSON.parse(match[1].trim());
    return { cleanText, chartData };
  } catch {
    return { cleanText, chartData: null };
  }
}

/**
 * Render a Chart.js line chart inside a message bubble.
 *
 * Expected chartData shape (from agent system prompt):
 *   { years: number[], bau?: number[], scenario: number[], ndc_target?: number[] }
 *
 * ndc_target may be:
 *   - same length as years  → used directly
 *   - 2 elements [v0, v1]   → linearly interpolated across the year range
 */
function renderInlineChart(container, chartData) {
  const { years, bau, nz, scenario } = chartData;
  if (!Array.isArray(years)) return;

  const wrapper = document.createElement("div");
  wrapper.className = "inline-chart-container";
  const canvas = document.createElement("canvas");
  wrapper.appendChild(canvas);
  container.appendChild(wrapper);

  const MUTED  = "#6B5E50";
  const GRID   = "#E4DDD0";
  const BORDER = "#DDD5C4";
  const MONO   = "'JetBrains Mono', monospace";
  const SANS   = "'Epilogue', sans-serif";

  const datasets = [];

  // 1. BAU — red dashed reference
  if (Array.isArray(bau)) {
    datasets.push({
      label: "Business as Usual",
      data: bau,
      borderColor: "#A8222E",
      borderWidth: 1.5,
      borderDash: [6, 4],
      pointRadius: 0,
      tension: 0.3,
      fill: false,
      order: 3,
    });
  }

  // 2. Net Zero pathway — teal solid reference
  if (Array.isArray(nz)) {
    datasets.push({
      label: "Net Zero Pathway",
      data: nz,
      borderColor: "#007A6F",
      borderWidth: 2,
      borderDash: [],
      pointRadius: 0,
      tension: 0.3,
      fill: false,
      order: 2,
    });
  }

  // 3. Simulated scenario — amber solid, only for user what-if runs
  if (Array.isArray(scenario)) {
    datasets.push({
      label: chartData.scenario_label || "Simulated Scenario",
      data: scenario,
      borderColor: "#B8860B",
      borderWidth: 2.5,
      borderDash: [],
      pointRadius: 0,
      tension: 0.3,
      fill: false,
      order: 1,
    });
  }


  new Chart(canvas, {
    type: "line",
    data: { labels: years, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 900,
        easing: "easeInOutQuart",
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: MUTED,
            font: { family: MONO, size: 10 },
            boxWidth: 22,
            padding: 12,
            usePointStyle: false,
          },
        },
        tooltip: {
          backgroundColor: "#FFFFFF",
          borderColor: BORDER,
          borderWidth: 1,
          titleColor: MUTED,
          bodyColor: "#26211A",
          titleFont: { family: MONO, size: 10 },
          bodyFont: { family: MONO, size: 11 },
          callbacks: {
            label: (ctx) =>
              `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)} Mt CO₂e/yr`,
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: MUTED,
            font: { family: MONO, size: 9 },
            maxTicksLimit: 8,
            maxRotation: 0,
          },
          grid: { color: GRID },
          border: { color: BORDER },
        },
        y: {
          title: {
            display: true,
            text: "Mt CO₂e / year",
            color: MUTED,
            font: { family: SANS, size: 10 },
          },
          ticks: {
            color: MUTED,
            font: { family: MONO, size: 9 },
          },
          grid: { color: GRID },
          border: { color: BORDER },
        },
      },
    },
  });

}

// ── Sector stacked area chart ─────────────────────────────────────────────

const SECTOR_META = {
  scoe:  { label: "Cooking & Buildings",       short: "Cooking/Bldgs",    color: "#E8C547" },
  lndu:  { label: "Land Use",                  short: "Land Use",          color: "#8FBC6A" },
  lvst:  { label: "Livestock",                 short: "Livestock",         color: "#F4A460" },
  trww:  { label: "Wastewater",                short: "Wastewater",        color: "#B0C9E0" },
  trns:  { label: "Transportation",            short: "Transport",         color: "#A0A0A0" },
  soil:  { label: "Soil",                      short: "Soil",              color: "#E8913A" },
  waso:  { label: "Solid Waste",               short: "Solid Waste",       color: "#D2B48C" },
  lsmm:  { label: "Manure Management",         short: "Manure Mgmt",       color: "#C8A87A" },
  inen:  { label: "Industrial Energy",         short: "Ind. Energy",       color: "#9370DB" },
  ippu:  { label: "Industrial Processes",      short: "Ind. Processes",    color: "#C8A2C8" },
  agrc:  { label: "Agriculture",               short: "Agriculture",       color: "#FF8C00" },
  frst:  { label: "Forestry (sequestration)",  short: "Forestry (seq.)",   color: "#2E8B57" },
};

// Ordered for stacking — frst last so it renders below zero
const SECTOR_STACK_ORDER = ["scoe","lndu","lvst","trww","trns","soil","waso","lsmm","inen","ippu","agrc","frst"];

/**
 * Render two side-by-side stacked area charts: BAU (left) and Policy Scenario (right).
 * Both share the same Y-axis scale so the visual comparison is direct.
 *
 * sectorComparison shape:
 *   { scenario: { sector_trajectories: {sector: {2030,2040,2050,2070}} },
 *     baseline: { sector_trajectories: ... },
 *     sector_deltas: {sector: {year: {scenario, bau, delta, pct_change}}} }
 */

function renderProjectedTotals(container, sectorComparison) {
  if (!sectorComparison || !sectorComparison.sector_deltas) return;
  const deltas = sectorComparison.sector_deltas;

  // Collect years dynamically from data (exclude 2019 anchor — delta is always 0 there)
  const years = [...new Set(
    Object.values(deltas).flatMap(s => Object.keys(s).map(Number))
  )].sort((a, b) => a - b).filter(yr => yr >= 2030);

  // Sum scenario and BAU totals per year across all sectors
  const totals = {};
  years.forEach(yr => {
    let scenTotal = 0, bauTotal = 0;
    Object.values(deltas).forEach(sectorData => {
      const entry = sectorData[yr];
      if (entry) { scenTotal += entry.scenario; bauTotal += entry.bau; }
    });
    const pct = bauTotal !== 0 ? ((scenTotal - bauTotal) / Math.abs(bauTotal) * 100) : 0;
    totals[yr] = {
      scenario: Math.round(scenTotal),
      bau: Math.round(bauTotal),
      delta: Math.round(scenTotal - bauTotal),
      pct: pct.toFixed(1),
      isReduction: pct < 0,
    };
  });

  const wrap = document.createElement("div");
  wrap.className = "projected-totals";

  const headCols = years.map(yr => `<th>${yr}</th>`).join("");
  const bauRow   = years.map(yr => `<td class="pt-bau">${totals[yr].bau.toLocaleString()}</td>`).join("");
  const scenRow  = years.map(yr => `<td class="pt-scen">${totals[yr].scenario.toLocaleString()}</td>`).join("");
  const deltaRow = years.map(yr => {
    const t = totals[yr];
    const cls = t.isReduction ? "pt-delta-good" : "pt-delta-bad";
    const sign = t.delta > 0 ? "+" : "";
    return `<td class="${cls}">${sign}${t.delta.toLocaleString()} <span class="pt-pct">(${sign}${t.pct}%)</span></td>`;
  }).join("");

  wrap.innerHTML = `
    <div class="pt-title">Total GHG Emissions (MtCO₂e)</div>
    <table class="pt-table">
      <thead><tr><th></th>${headCols}</tr></thead>
      <tbody>
        <tr><td class="pt-label">BAU</td>${bauRow}</tr>
        <tr><td class="pt-label">Scenario</td>${scenRow}</tr>
        <tr><td class="pt-label">Δ vs BAU</td>${deltaRow}</tr>
      </tbody>
    </table>
  `;
  container.appendChild(wrap);
}

function renderStackedSectorChart(container, sectorComparison) {
  if (!sectorComparison) return;

  const YEARS = [2019, 2030, 2040, 2050, 2070];
  const MUTED  = "#6B5E50";
  const GRID   = "#E4DDD0";
  const BORDER = "#DDD5C4";
  const MONO   = "'JetBrains Mono', monospace";
  const SANS   = "'Epilogue', sans-serif";

  const scenarioTrajectories = sectorComparison.scenario?.sector_trajectories || {};
  const bauTrajectories      = sectorComparison.baseline?.sector_trajectories || {};

  // Build stacked area datasets + net-total line
  function buildDatasets(trajectories, isBau) {
    // Sector area datasets (order: 1 renders behind the total line)
    const datasets = SECTOR_STACK_ORDER.map(sector => {
      const meta   = SECTOR_META[sector] || { label: sector, color: "#888" };
      const traj   = trajectories[sector] || {};
      const values = YEARS.map(y => traj[y] ?? null);
      return {
        label:           meta.label,
        _sector:         sector,
        _shortLabel:     meta.short,
        data:            values,
        fill:            true,
        tension:         0,
        order:           1,
        stack:           sector === "frst" ? "negative" : "positive",
        backgroundColor: meta.color + "CC",
        borderColor:     meta.color,
        borderWidth:     1,
        pointRadius:     0,
        pointHoverRadius: 4,
        pointBackgroundColor: meta.color,
      };
    });

    // Net total per year (sum of all sectors including frst sequestration)
    const totals = YEARS.map(y =>
      SECTOR_STACK_ORDER.reduce((sum, s) => sum + ((trajectories[s] || {})[y] ?? 0), 0)
    );
    const totalColor = "#26211A";
    datasets.push({
      label:           isBau ? "BAU net total" : "Scenario net total",
      _sector:         "__total__",
      data:            totals,
      yAxisID:         "y2",
      order:           0,
      fill:            false,
      tension:         0,
      borderColor:     totalColor,
      borderWidth:     2.5,
      borderDash:      isBau ? [5, 4] : [],
      pointRadius:     3,
      pointHoverRadius: 5,
      pointBackgroundColor: totalColor,
      backgroundColor: "transparent",
    });

    return datasets;
  }

  // Compute shared Y bounds across both views
  function stackBounds(traj) {
    let posMax = 0, negMin = 0;
    for (const y of YEARS) {
      let pos = 0;
      for (const s of SECTOR_STACK_ORDER) {
        const v = (traj[s] || {})[y] ?? 0;
        if (s === "frst") negMin = Math.min(negMin, v);
        else pos += v;
      }
      posMax = Math.max(posMax, pos);
    }
    return { posMax, negMin };
  }
  const b1 = stackBounds(bauTrajectories), b2 = stackBounds(scenarioTrajectories);
  const yMax = Math.ceil(Math.max(b1.posMax, b2.posMax) * 1.08 / 50) * 50;
  const yMin = Math.floor(Math.min(b1.negMin, b2.negMin) * 1.2 / 10) * 10;

  function makeOptions(title, showYAxis) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 500, easing: "easeInOutQuart" },
      interaction: { mode: "index", intersect: false },
      plugins: {
        title: {
          display: true,
          text: title,
          color: "#26211A",
          font: { family: SANS, size: 11, weight: "600" },
          padding: { bottom: 6 },
        },
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(255, 255, 255, 0.6)",
          borderColor: BORDER,
          borderWidth: 1,
          titleColor: "#26211A",
          bodyColor: MUTED,
          titleFont: { family: MONO, size: 10 },
          bodyFont: { family: MONO, size: 10 },
          callbacks: {
            label: ctx => ctx.parsed.y != null
              ? `${ctx.dataset._shortLabel ?? ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)} Mt`
              : null,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: MUTED, font: { family: MONO, size: 9 } },
          grid:  { display: false },
          border: { color: BORDER },
        },
        y: {
          stacked: true,
          min: yMin,
          max: yMax,
          display: showYAxis,
          title: showYAxis
            ? { display: true, text: "Mt CO₂e / yr", color: MUTED, font: { family: SANS, size: 10 } }
            : { display: false },
          ticks: { color: MUTED, font: { family: MONO, size: 9 } },
          grid:  { display: false },
          border: { color: BORDER },
        },
        // Non-stacked axis for the net-total overlay line (same range, hidden)
        y2: {
          stacked: false,
          min: yMin,
          max: yMax,
          display: false,
          grid: { display: false },
        },
      },
    };
  }

  // DOM: [panelRow (flex:1)] [legendDiv (right column)]
  const outerDiv  = document.createElement("div");
  outerDiv.className = "stacked-chart-outer";

  const panelRow  = document.createElement("div");
  panelRow.className = "stacked-chart-panels";
  outerDiv.appendChild(panelRow);

  const charts = [];
  function makePanel(datasets, title, showYAxis) {
    const wrap   = document.createElement("div");
    wrap.className = "stacked-chart-panel";
    const canvas = document.createElement("canvas");
    wrap.appendChild(canvas);
    panelRow.appendChild(wrap);
    const chart = new Chart(canvas, {
      type: "line",
      data: { labels: YEARS, datasets },
      options: makeOptions(title, showYAxis),
    });
    charts.push(chart);
    return chart;
  }

  makePanel(buildDatasets(bauTrajectories,       true),  "Business as Usual", true);
  makePanel(buildDatasets(scenarioTrajectories,  false), "Policy Scenario",   false);

  // Right-side legend with click toggle
  const legendDiv = document.createElement("div");
  legendDiv.className = "stacked-chart-legend-right";

  for (const sector of SECTOR_STACK_ORDER) {
    const meta = SECTOR_META[sector] || { label: sector, color: "#888" };
    const item = document.createElement("div");
    item.className = "stacked-legend-item";
    item.innerHTML =
      `<span class="stacked-legend-swatch" style="background:${meta.color}"></span>` +
      `<span class="stacked-legend-label">${meta.label}</span>`;
    item.addEventListener("click", () => {
      item.classList.toggle("legend-hidden");
      const hidden = item.classList.contains("legend-hidden");
      for (const chart of charts) {
        const idx = chart.data.datasets.findIndex(d => d._sector === sector);
        if (idx !== -1) {
          chart.getDatasetMeta(idx).hidden = hidden;
          chart.update("none");
        }
      }
    });
    legendDiv.appendChild(item);
  }

  outerDiv.appendChild(legendDiv);
  container.appendChild(outerDiv);
}

// ── Cost / benefit diverging bar chart ────────────────────────────────────

// Benefit types (positive, stack up) in render order, with display labels + colors.
const CB_BENEFIT_META = [
  { key: "human_health",       label: "Human Health",        color: "#2E8B57" },
  { key: "air_pollution",      label: "Air Quality",         color: "#3CB371" },
  { key: "consumer_savings",   label: "Consumer Savings",    color: "#8FBC6A" },
  { key: "technical_savings",  label: "Technical Savings",   color: "#9ACD32" },
  { key: "congestion",         label: "Reduced Congestion",  color: "#5F9EA0" },
  { key: "road_safety",        label: "Road Safety",         color: "#4682B4" },
  { key: "crop_value",         label: "Crop Value",          color: "#E8C547" },
  { key: "lvst_value",         label: "Livestock Value",     color: "#DAA520" },
  { key: "ippu_value",         label: "Industrial Value",    color: "#B8860B" },
  { key: "ecosystem_services", label: "Ecosystem Services",  color: "#66CDAA" },
  { key: "env_pollution",      label: "Env. Pollution",      color: "#20B2AA" },
  { key: "land_pollution",     label: "Land Pollution",      color: "#8FBC8F" },
  { key: "water_pollution",    label: "Water Pollution",     color: "#7EC8C8" },
  { key: "sector_specific",    label: "Sector-Specific",     color: "#9370DB" },
];

// Cost types (negative, stack down) with display labels + colors.
const CB_COST_META = [
  { key: "technical", label: "Technical Cost", color: "#C0392B" },
  { key: "system",    label: "System Cost",    color: "#E67E22" },
  { key: "fuel",      label: "Fuel Cost",      color: "#A93226" },
];

/**
 * Diverging stacked bar chart of the Policy Scenario's cost/benefit by year:
 * benefits stack upward (positive), costs stack downward (negative), with a net
 * line and a dashed BAU-net line for comparison. Cost-as-%-of-GDP per year is
 * shown in the tooltip footer.
 *
 * costBenefitComparison shape:
 *   { years: [2030,2040,2050,2070],
 *     scenario: { "<year>": {benefits:{type:val}, costs:{type:val}, net, cost_pct_gdp, ...} },
 *     baseline: { "<year>": {...} } }
 */
function renderCostBenefitChart(container, cbc) {
  if (!cbc || !cbc.scenario) return;

  const MUTED = "#6B5E50", BORDER = "#DDD5C4";
  const MONO = "'JetBrains Mono', monospace", SANS = "'Epilogue', sans-serif";
  const YEARS = (cbc.years || [2030, 2040, 2050, 2070]).map(Number);
  const scen = cbc.scenario, base = cbc.baseline || {};
  const at = (obj, y) => obj[String(y)] || obj[y] || {};

  const benDatasets = CB_BENEFIT_META.map(m => ({
    label: m.label, _cbkey: m.key, stack: "cb", order: 1,
    data: YEARS.map(y => (at(scen, y).benefits || {})[m.key] ?? 0),
    backgroundColor: m.color + "DD", borderColor: m.color, borderWidth: 0.5,
  }));
  const costDatasets = CB_COST_META.map(m => ({
    label: m.label, _cbkey: m.key, stack: "cb", order: 1,
    data: YEARS.map(y => (at(scen, y).costs || {})[m.key] ?? 0),
    backgroundColor: m.color + "DD", borderColor: m.color, borderWidth: 0.5,
  }));

  const netLine = {
    type: "line", label: "Net (benefits − costs)", _cbkey: "__net__", order: 0,
    yAxisID: "y2", data: YEARS.map(y => at(scen, y).net ?? 0),
    borderColor: "#26211A", borderWidth: 2.5, pointRadius: 3, pointHoverRadius: 5,
    pointBackgroundColor: "#26211A", fill: false, tension: 0,
  };
  const bauNetLine = {
    type: "line", label: "BAU net", _cbkey: "__baunet__", order: 0,
    yAxisID: "y2", data: YEARS.map(y => at(base, y).net ?? 0),
    borderColor: "#26211A", borderWidth: 1.5, borderDash: [5, 4],
    pointRadius: 2, pointBackgroundColor: "#26211A", fill: false, tension: 0,
  };

  const datasets = [...benDatasets, ...costDatasets, netLine, bauNetLine];

  // Y bounds from stacked sums (benefits up, costs down) + net line.
  let posMax = 0, negMin = 0;
  YEARS.forEach(y => {
    posMax = Math.max(posMax, at(scen, y).total_benefit ?? 0);
    negMin = Math.min(negMin, at(scen, y).total_cost ?? 0,
                              at(scen, y).net ?? 0, at(base, y).net ?? 0);
  });
  const yMax = Math.ceil(posMax * 1.08 / 5) * 5;
  const yMin = Math.floor(negMin * 1.2 / 5) * 5;

  const outerDiv = document.createElement("div");
  outerDiv.className = "stacked-chart-outer";
  const panelRow = document.createElement("div");
  panelRow.className = "stacked-chart-panels";
  outerDiv.appendChild(panelRow);

  const wrap = document.createElement("div");
  wrap.className = "stacked-chart-panel";
  const canvas = document.createElement("canvas");
  wrap.appendChild(canvas);
  panelRow.appendChild(wrap);

  const chart = new Chart(canvas, {
    type: "bar",
    data: { labels: YEARS, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 500, easing: "easeInOutQuart" },
      interaction: { mode: "index", intersect: false },
      plugins: {
        title: {
          display: true, text: "Annual Cost & Benefit by Year (Policy Scenario)",
          color: "#26211A", font: { family: SANS, size: 11, weight: "600" },
          padding: { bottom: 6 },
        },
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(255,255,255,0.92)", borderColor: BORDER, borderWidth: 1,
          titleColor: "#26211A", bodyColor: MUTED, footerColor: "#26211A",
          titleFont: { family: MONO, size: 10 }, bodyFont: { family: MONO, size: 10 },
          footerFont: { family: MONO, size: 10, weight: "600" },
          filter: ctx => ctx.parsed.y !== 0 && ctx.parsed.y != null,
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)} B USD`,
            footer: items => {
              const y = items[0]?.label;
              const d = at(scen, y);
              return `cost: ${(d.cost_pct_gdp ?? 0).toFixed(2)}% of GDP`;
            },
          },
        },
      },
      scales: {
        x: { stacked: true, ticks: { color: MUTED, font: { family: MONO, size: 9 } },
             grid: { display: false }, border: { color: BORDER } },
        y: { stacked: true, min: yMin, max: yMax,
             title: { display: true, text: "Billion USD / yr", color: MUTED, font: { family: SANS, size: 10 } },
             ticks: { color: MUTED, font: { family: MONO, size: 9 } },
             grid: { color: "#E4DDD0" }, border: { color: BORDER } },
        y2: { stacked: false, min: yMin, max: yMax, display: false, grid: { display: false } },
      },
    },
  });

  // Right-side legend with click toggle (benefits, then costs, then net).
  const legendDiv = document.createElement("div");
  legendDiv.className = "stacked-chart-legend-right";
  const legendItems = [
    ...CB_BENEFIT_META, ...CB_COST_META,
    { key: "__net__", label: "Net", color: "#26211A" },
  ];
  for (const m of legendItems) {
    const item = document.createElement("div");
    item.className = "stacked-legend-item";
    item.innerHTML =
      `<span class="stacked-legend-swatch" style="background:${m.color}"></span>` +
      `<span class="stacked-legend-label">${m.label}</span>`;
    item.addEventListener("click", () => {
      item.classList.toggle("legend-hidden");
      const hidden = item.classList.contains("legend-hidden");
      const idx = chart.data.datasets.findIndex(d => d._cbkey === m.key);
      if (idx !== -1) { chart.getDatasetMeta(idx).hidden = hidden; chart.update("none"); }
    });
    legendDiv.appendChild(item);
  }
  outerDiv.appendChild(legendDiv);
  container.appendChild(outerDiv);
}

/**
 * Render three metric summary cards in a row below an inline chart.
 *
 * Reads: total_reduction_pct, near_term_vs_bau_pct, long_term_vs_bau_pct
 * from the metrics object. Missing keys are shown as "—".
 */
function renderChartMetrics(container, metrics) {
  const CARDS = [
    { key: "total_reduction_pct",    label: "total reduction vs BAU" },
    { key: "near_term_vs_bau_pct",   label: "near-term 2033–37" },
    { key: "long_term_vs_bau_pct",   label: "long-term 2066–70" },
  ];

  const row = document.createElement("div");
  row.className = "chart-metrics-row";

  for (const { key, label } of CARDS) {
    const raw = metrics[key];
    let valueText;
    if (raw === undefined || raw === null) {
      valueText = "—";
    } else {
      const num = Number(raw);
      // Always show a minus sign for reductions; clamp display to 1 decimal
      const sign = num <= 0 ? "−" : "+";
      valueText = `${sign}${Math.abs(num).toFixed(1)}%`;
    }

    const card = document.createElement("div");
    card.className = "chart-metric-card";
    card.innerHTML =
      `<div class="chart-metric-value">${valueText}</div>` +
      `<div class="chart-metric-label">${label}</div>`;
    row.appendChild(card);
  }

  container.appendChild(row);
}

// ── Init ──────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  document.getElementById("chat-input").focus();
});
