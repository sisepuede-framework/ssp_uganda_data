/**
 * Uganda Climate Pathways Explorer — Frontend
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
  activeTab: "official",    // official | explore | how
  started: false,           // true once the user has asked anything (hides intros, collapses panel)
};

// ── Preset messages ───────────────────────────────────────────────────────

// One entry per official pathway, keyed by the EXACT display name the backend
// registry uses (pathways_lookup.PATHWAY_REGISTRY), so the cards rendered from
// /api/pathways/summary map straight onto these. Each message NAMES its pathway
// verbatim — the agent routes to get_pathway_results (the real CDPM run) by that
// name, so do not paraphrase them.
const PATHWAY_PRESETS = {
  "BAU": "Show me the official Business as Usual (BAU) pathway result — Uganda's emissions, costs, and development benefits under minimal policy action.",
  "NDC 2.0": "Show me the official NDC 2.0 pathway result — emissions, costs, and development benefits vs BAU.",
  "NDC 2.5": "Show me the official NDC 2.5 pathway result — emissions, costs, and development benefits vs BAU.",
  "NDC2 Unconditional": "Show me the official NDC2 Unconditional pathway result — emissions, costs, and development benefits vs BAU.",
  "NDC2 Unconditional (Alt)": "Show me the official NDC2 Unconditional (Alt) pathway result — emissions, costs, and development benefits vs BAU.",
  "Candidate NDC3": "Show me the official HBLE pathway result (Candidate NDC3, the analytical basis for Uganda's NDC 3.0) — emissions, costs, and development benefits vs BAU.",
};

/** Put text in the input and send it. Every launcher button goes through here.
 *  Asking always folds the launcher away: it has done its job, and the answer —
 *  with its charts and its trace — is what the reader now wants the space for. */
function ask(text) {
  if (!text) return;
  setPanelCollapsed(true);
  document.getElementById("chat-input").value = text;
  sendMessage();
}

function sendPathway(name) {
  ask(PATHWAY_PRESETS[name] ||
      `Show me the official ${name} pathway result — emissions, costs, and development benefits vs BAU.`);
}

// ── Tabs & launcher panel ─────────────────────────────────────────────────

// Each tab swaps the launcher panel, its intro block, and the input placeholder.
// The CONVERSATION is shared — switching tabs never clears it.
const TAB_META = {
  official: {
    panel: "panel-official", intro: "intro-official", shortName: "pathways",
    placeholder: "Ask about one of the six official pathways...",
  },
  explore: {
    panel: "panel-explore", intro: "intro-explore", shortName: "questions",
    placeholder: "Describe a combination to explore — an ambition level, a delay, a country condition...",
  },
  // No intro and no input: the reference tab is a document, and asking from it
  // hands off to Explore.
  how: {
    panel: "panel-how", intro: null, shortName: "reference",
    placeholder: "Describe a combination to explore...",
  },
};

function switchTab(tab) {
  if (!TAB_META[tab]) tab = "official";
  state.activeTab = tab;

  for (const [key, meta] of Object.entries(TAB_META)) {
    const isActive = key === tab;
    document.getElementById(meta.panel).classList.toggle("hidden", !isActive);
    // Intro blocks only exist while the conversation is empty.
    if (meta.intro) {
      document.getElementById(meta.intro).classList.toggle("hidden", !isActive || state.started);
    }
  }
  document.querySelectorAll(".tab").forEach(btn => {
    const isActive = btn.dataset.tab === tab;
    btn.classList.toggle("tab--active", isActive);
    btn.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  document.getElementById("chat-input").placeholder = TAB_META[tab].placeholder;
  document.getElementById("launcher").scrollTop = 0;   // start each tab at its top
  applyReadingMode();
  setPanelCollapsed(false);            // switching tabs always reveals the panel

  // Shareable deep link (?tab=explore) — handy for pointing a reviewer at one section.
  const url = new URL(window.location);
  url.searchParams.set("tab", tab);
  window.history.replaceState({}, "", url);
}

/**
 * "How this works" is a document, always: the panel owns the whole height, the
 * transcript and the input step aside, and the collapse control disappears —
 * there is nothing to collapse it for. Questions asked from it hand off to
 * Explore (see askFromReference), so the single conversation stays in one place.
 */
function applyReadingMode() {
  const panel = document.querySelector(".chat-panel");
  const reading = state.activeTab === "how";
  panel.classList.toggle("chat-panel--reading", reading);
  document.getElementById("launcher").classList.toggle("launcher--tall", reading);
  document.getElementById("panel-toggle").classList.toggle("hidden", reading);
}

/**
 * Hand-off: a question asked from the reference page opens in Explore, where the
 * conversation lives. Switching tabs IS the feedback — it shows the reader where
 * answers land, every time, instead of hiding a second conversation behind a tab.
 */
function askFromReference(text) {
  switchTab("explore");
  ask(text);
}

function setPanelCollapsed(collapsed) {
  const launcher = document.getElementById("launcher");
  const toggle = document.getElementById("panel-toggle");
  launcher.classList.toggle("launcher--collapsed", collapsed);
  // Name what the control does — a bare "Show" gives no clue what comes back.
  const label = TAB_META[state.activeTab]?.shortName || "section";
  toggle.textContent = collapsed ? `Show ${label} ▾` : "Hide ▴";
  toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
  document.querySelector(".chat-panel").classList.toggle("chat-panel--folded", collapsed);
}

function initTabs() {
  document.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => {
      // Clicking the tab you are already on folds the panel away and back —
      // the tab itself is the most obvious thing to reach for.
      if (btn.dataset.tab === state.activeTab) {
        const collapsed = document.getElementById("launcher").classList.contains("launcher--collapsed");
        setPanelCollapsed(!collapsed);
        return;
      }
      switchTab(btn.dataset.tab);
    });
  });
  document.getElementById("panel-toggle").addEventListener("click", () => {
    const collapsed = document.getElementById("launcher").classList.contains("launcher--collapsed");
    setPanelCollapsed(!collapsed);
  });
  // Any launcher button carrying data-ask sends that question; data-ask-ref comes
  // from the reference page and hands off to Explore first.
  document.addEventListener("click", (event) => {
    const handoff = event.target.closest("[data-ask-ref]");
    if (handoff) {
      event.preventDefault();     // Ask buttons live inside <summary>; don't toggle it
      askFromReference(handoff.dataset.askRef);
      return;
    }
    const btn = event.target.closest("[data-ask]");
    if (btn) ask(btn.dataset.ask);
  });

  initDocNav();
  document.getElementById("launcher").addEventListener("scroll", updateDocNavHighlight);

  const requested = new URLSearchParams(window.location.search).get("tab");
  switchTab(requested || "official");
}

/** Hide the intro blocks and fold the launcher away — called on the first question. */
function markConversationStarted() {
  if (state.started) return;
  state.started = true;
  document.querySelectorAll(".intro-block").forEach(el => el.classList.add("hidden"));
  applyReadingMode();   // reading mode ends — the transcript takes the space back
  setPanelCollapsed(true);
}

// ── API calls ─────────────────────────────────────────────────────────────

async function checkHealth() {
  // The visible status badge was removed from the header; this still pings the
  // server and updates the badge only if one is present (guarded, no-ops otherwise).
  const badge = document.getElementById("model-status");
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    if (!badge) return;
    badge.textContent = data.model_loaded ? "✓ Model ready" : "⚠ Model not loaded";
    if (data.model_loaded) badge.classList.add("ready");
  } catch {
    if (badge) badge.textContent = "⚠ Server offline";
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

// ── Launcher content (loaded from the API — never hardcoded) ──────────────

/**
 * Official-pathway cards. Every figure comes from /api/pathways/summary, which
 * reads the same stored CDPM runs the cards open — so a card can never show a
 * number that disagrees with the answer behind it.
 */
async function loadPathwayCards() {
  const mount = document.getElementById("pathway-cards");
  let pathways;
  try {
    const res = await fetch(`${API_BASE}/api/pathways/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    ({ pathways } = await res.json());
  } catch (err) {
    // Degrade to plain buttons rather than showing nothing — the pathways still work.
    mount.innerHTML = "";
    for (const name of Object.keys(PATHWAY_PRESETS)) {
      const btn = document.createElement("button");
      btn.className = "pathway-card pathway-card--bare";
      btn.innerHTML = `<span class="pc-name">${escapeHtml(name)}</span>`;
      btn.addEventListener("click", () => sendPathway(name));
      mount.appendChild(btn);
    }
    return;
  }

  // One shared vertical scale across all six sparklines, so the cards are
  // comparable at a glance (HBLE really does sit near the floor).
  const peak = Math.max(...pathways.flatMap(p => p.net_by_year));
  mount.innerHTML = "";

  for (const p of pathways) {
    const card = document.createElement("button");
    card.className = "pathway-card" + (p.is_baseline ? " pathway-card--baseline" : "");
    card.title = `${p.name} · strategy ${p.strategy_code}`;

    const delta = p.pct_vs_bau_2070 == null
      ? `<span class="pc-delta pc-delta--base">baseline</span>`
      : `<span class="pc-delta">${p.pct_vs_bau_2070 < 0 ? "−" : "+"}${Math.abs(Math.round(p.pct_vs_bau_2070))}% vs BAU</span>`;

    card.innerHTML =
      `<div class="pc-top">
         <span class="pc-name">${p.icon ? escapeHtml(p.icon) + " " : ""}${escapeHtml(p.short_label)}</span>
         ${sparklineSVG(p.net_by_year, peak, p.is_baseline)}
       </div>
       <p class="pc-desc">${escapeHtml(p.description)}</p>
       <div class="pc-figs">
         <span class="pc-value">${p.net_2070}</span>
         <span class="pc-unit">${escapeHtml(p.unit || "Mt CO₂e")} · 2070</span>
         ${delta}
       </div>`;
    card.addEventListener("click", () => sendPathway(p.name));
    mount.appendChild(card);
  }
}

/**
 * Tiny inline SVG trajectory. Baseline (BAU) draws in the rising red; every other
 * pathway falls relative to it and draws in the action green (Design Guide: red =
 * rising/BAU, green = falling/action).
 */
function sparklineSVG(series, peak, isBaseline) {
  const W = 92, H = 30, PAD = 3;
  const max = peak > 0 ? peak : 1;
  const points = series.map((v, i) => {
    const x = PAD + (i * (W - 2 * PAD)) / (series.length - 1);
    const y = H - PAD - (Math.max(v, 0) / max) * (H - 2 * PAD);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const colour = isBaseline ? "#B0413E" : "#4E8F5B";
  return `<svg class="pc-spark" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true">
      <polyline points="${points}" fill="none" stroke="${colour}" stroke-width="1.6"
                stroke-linecap="round" stroke-linejoin="round" />
    </svg>`;
}

/**
 * Explore chips and the How-this-works catalogue, both built from /api/features —
 * the same registry the assistant reads. Counts on screen therefore cannot drift
 * from the levers that actually exist.
 */
async function loadFeatureRegistry() {
  let registry;
  try {
    const res = await fetch(`${API_BASE}/api/features`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    registry = await res.json();
  } catch (err) {
    console.warn("Could not load the feature registry:", err);
    return;
  }

  const levers = Object.values(registry.lever_features || {});
  const exogenous = Object.values(registry.exogenous_features || {})
    .sort((a, b) => a.group_id - b.group_id);

  // Chip order for the conditions: the ones a policymaker recognises come first
  // (growth, population, fuel prices, exports), then technology costs and the
  // elasticities. The full list stays behind "N more" and in the catalogue.
  const X_HEADLINE = [57, 60, 56, 55];
  const exogenousForChips = [...exogenous].sort((a, b) => {
    const rank = x => {
      const i = X_HEADLINE.indexOf(x.group_id);
      return i === -1 ? X_HEADLINE.length + x.group_id : i;
    };
    return rank(a) - rank(b);
  });

  // sector → levers, biggest sector first
  const bySector = new Map();
  for (const lever of levers) {
    if (!bySector.has(lever.sector)) bySector.set(lever.sector, []);
    bySector.get(lever.sector).push(lever);
  }
  const sectors = [...bySector.entries()].sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));

  document.getElementById("ambition-count").textContent = `${levers.length} L · ${sectors.length} sectors`;
  document.getElementById("conditions-count").textContent = `${exogenous.length} X`;
  document.getElementById("how-levers-count").textContent = `${levers.length} across ${sectors.length} sectors`;
  document.getElementById("how-conditions-count").textContent = `${exogenous.length} in total`;

  renderSectorChips(sectors);
  renderConditionChips(exogenousForChips);
  renderLeverCatalogue(sectors);
  renderConditionCatalogue(exogenous);
  initLeverFilter();          // wired after the rows exist
}

const CHIPS_SHOWN = 6;   // the rest hide behind a "N more" chip

function renderSectorChips(sectors) {
  const mount = document.getElementById("explore-sectors");
  mount.innerHTML = "";
  const makeChip = ([sector, group]) => {
    const chip = document.createElement("button");
    chip.className = "mini-chip";
    chip.innerHTML = `${escapeHtml(sector)} <span class="mini-chip-n">${group.length}</span>`;
    chip.dataset.ask =
      `What can Uganda change in the ${sector} sector, and what would the ambitious end of the ` +
      `range there do to emissions, costs and development benefits?`;
    return chip;
  };
  sectors.slice(0, CHIPS_SHOWN).forEach(entry => mount.appendChild(makeChip(entry)));

  const rest = sectors.slice(CHIPS_SHOWN);
  if (!rest.length) return;
  const more = document.createElement("button");
  more.className = "mini-chip mini-chip--more";
  more.textContent = `${rest.length} more sectors`;
  more.addEventListener("click", () => {
    more.remove();
    rest.forEach(entry => mount.appendChild(makeChip(entry)));
  });
  mount.appendChild(more);
}

function renderConditionChips(exogenous) {
  const mount = document.getElementById("explore-conditions");
  mount.innerHTML = "";
  const makeChip = (x) => {
    const chip = document.createElement("button");
    chip.className = "mini-chip";
    chip.textContent = x.display_name;
    chip.dataset.ask =
      `What happens to emissions, costs and development benefits if ${x.display_name} sits at the ` +
      `high end of its uncertainty range instead of the median future?`;
    return chip;
  };
  exogenous.slice(0, CHIPS_SHOWN).forEach(x => mount.appendChild(makeChip(x)));

  const rest = exogenous.slice(CHIPS_SHOWN);
  if (!rest.length) return;
  const more = document.createElement("button");
  more.className = "mini-chip mini-chip--more";
  more.textContent = `${rest.length} more`;
  more.addEventListener("click", () => {
    more.remove();
    rest.forEach(x => mount.appendChild(makeChip(x)));
  });
  mount.appendChild(more);
}

function renderLeverCatalogue(sectors) {
  const mount = document.getElementById("how-levers");
  mount.innerHTML = "";
  for (const [sector, group] of sectors) {
    const details = document.createElement("details");
    details.className = "cat-group";
    // Clean names only. The raw SISEPUEDE transformation code
    // (TX:TRNS:INC_EFFICIENCY_ELECTRIC_STRATEGY_NZ) means nothing to a reader and
    // its _NZ suffix is unexplained jargon — it stays on hover for the modellers.
    // Each row carries an Ask that hands the question off to Explore.
    const rows = group
      .sort((a, b) => a.group_id - b.group_id)
      .map(l => {
        const q = `What does the "${l.display_name}" lever (${l.sector}) actually change in the model, ` +
                  `and what happens to emissions, costs and development benefits at the ambitious ` +
                  `end of its range?`;
        return `<li title="${escapeAttr(l.transformation_code || "")}">
                  <span class="cat-id">${l.group_id}</span>
                  <span class="cat-name">${escapeHtml(l.display_name)}</span>
                  <button class="cat-ask" data-ask-ref="${escapeAttr(q)}">Ask</button>
                </li>`;
      })
      .join("");
    const sectorQ = `What can Uganda change in the ${sector} sector, and what would the ambitious end ` +
                    `of the range there do to emissions, costs and development benefits?`;
    details.innerHTML =
      `<summary>${escapeHtml(sector)} <span class="cat-count">${group.length}</span>
         <button class="cat-ask cat-ask--sector" data-ask-ref="${escapeAttr(sectorQ)}">Ask about this sector</button>
       </summary>
       <ul class="cat-list">${rows}</ul>`;
    mount.appendChild(details);
  }
}

function renderConditionCatalogue(exogenous) {
  const mount = document.getElementById("how-conditions");
  const rows = exogenous.map(x => {
    const domain = (x.sector || "").replace("Exogenous / ", "");
    const q = `What happens to emissions, costs and development benefits if ${x.display_name} sits at ` +
              `the high end of its uncertainty range instead of the median future?`;
    return `<li><span class="cat-id">${x.group_id}</span>
              <span class="cat-name">${escapeHtml(x.display_name)}</span>
              <span class="cat-domain">${escapeHtml(domain)}</span>
              <button class="cat-ask" data-ask-ref="${escapeAttr(q)}">Ask</button>
            </li>`;
  }).join("");
  mount.innerHTML = `<ul class="cat-list cat-list--flat">${rows}</ul>`;
}

/**
 * Filter over the 54 levers. With 16 collapsed sectors, browsing is the only way
 * in — and people don't browse, they look for the thing they already have in mind.
 * A sector-name match reveals that whole sector.
 */
function initLeverFilter() {
  const input = document.getElementById("lever-filter");
  const countEl = document.getElementById("lever-filter-count");
  if (!input) return;

  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    let shown = 0;

    document.querySelectorAll("#how-levers .cat-group").forEach(group => {
      const summary = group.querySelector("summary");
      const sectorHit = !!q && summary.textContent.toLowerCase().includes(q);
      let matches = 0;

      group.querySelectorAll("li").forEach(li => {
        const hit = !q || sectorHit || li.textContent.toLowerCase().includes(q);
        li.classList.toggle("filtered-out", !hit);
        if (hit) matches++;
      });

      group.classList.toggle("filtered-out", q ? matches === 0 : false);
      group.open = !!q && matches > 0;      // open what matched, close again when cleared
      shown += q ? matches : 0;
    });

    countEl.textContent = q ? `${shown} lever${shown === 1 ? "" : "s"}` : "";
  });
}

/** Keep the nav in step with where the reader actually is. */
function updateDocNavHighlight() {
  if (state.activeTab !== "how") return;
  const launcher = document.getElementById("launcher");
  const links = [...document.querySelectorAll(".doc-nav-link")];
  let current = links[0];
  for (const link of links) {
    const section = document.getElementById(link.dataset.section);
    if (section && section.getBoundingClientRect().top - launcher.getBoundingClientRect().top <= 60) {
      current = link;
    }
  }
  links.forEach(l => l.classList.toggle("doc-nav-link--active", l === current));
}

/** Section navigation — scrolls within the reference page's own scroll container. */
function initDocNav() {
  document.querySelectorAll(".doc-nav-link").forEach(link => {
    link.addEventListener("click", () => {
      const target = document.getElementById(link.dataset.section);
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      document.querySelectorAll(".doc-nav-link").forEach(l => l.classList.remove("doc-nav-link--active"));
      link.classList.add("doc-nav-link--active");
    });
  });
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
  markConversationStarted();   // hide the intros, fold the launcher away

  // Add user message to UI + history
  appendMessage("user", text);
  state.conversationHistory.push({ role: "user", content: text });

  try {
    const response = await sendChatRequest(state.conversationHistory);

    // Add assistant reply to UI + history
    if (response.simulation) state.lastSimulation = response.simulation;
    appendMessage("assistant", response.reply, response.simulation || null, response.trace || null);
    state.conversationHistory.push({ role: "assistant", content: response.reply });

  } catch (error) {
    appendMessage("assistant", `⚠ Error: ${error.message}. Please check the server is running and try again.`);
  } finally {
    setLoading(false);
  }
}

// ── UI rendering ──────────────────────────────────────────────────────────

function appendMessage(role, content, simulationData = null, traceData = null) {
  const container = document.getElementById("chat-messages");

  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}-message`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "user" ? "You" : "UG";

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";

  // Assistant messages are split into ordered segments (prose + inline ```chart blocks)
  // so charts render exactly where the model placed them. Variable lines are pulled out
  // globally and shown once, before the body.
  let varPairs  = [];
  let segments  = [{ type: "text", text: content }];
  if (role === "assistant") {
    const varExtracted = extractVariableLines(content);
    varPairs = varExtracted.pairs;
    segments = parseChartSegments(varExtracted.cleanText);
  }

  // Variable table — rendered first, directly below the avatar
  if (varPairs.length > 0) {
    renderVariableTable(contentDiv, varPairs);
  }

  // Fall back to last simulation when this response carries no new simulation data
  const effectiveSimData = simulationData || (role === "assistant" ? state.lastSimulation : null);

  // Render text and charts in order. Charts are placeholders here; they are drawn after
  // DOM insertion (below) so Chart.js can read real canvas dimensions.
  const pendingCharts = [];
  for (const seg of segments) {
    if (seg.type === "text") {
      if (!seg.text.trim()) continue;
      const block = document.createElement("div");
      block.innerHTML = formatMessageContent(seg.text.trim());
      contentDiv.appendChild(block);
    } else if (seg.type === "chart") {
      const mount = document.createElement("div");
      contentDiv.appendChild(mount);
      if (seg.spec) pendingCharts.push({ mount, spec: seg.spec });
    }
  }

  // Insert into DOM first so Chart.js can read canvas dimensions correctly
  msgDiv.appendChild(avatar);
  msgDiv.appendChild(contentDiv);
  container.appendChild(msgDiv);

  // Now draw each chart into its in-place mount point.
  for (const { mount, spec } of pendingCharts) {
    if (effectiveSimData) renderChartFromSpec(mount, spec, effectiveSimData);
  }

  // Process trace — the factual record of how this answer was produced (source
  // badge + collapsible steps). Assistant messages only, when the backend sent one.
  // This is the LAST thing under an answer: nothing follows it competing for the
  // reader's attention.
  if (role === "assistant" && Array.isArray(traceData) && traceData.length > 0) {
    renderTrace(contentDiv, traceData);
  }

  // Scroll to bottom
  container.scrollTop = container.scrollHeight;
}

/**
 * Convert plain text with markdown-like syntax to HTML.
 * Supports: tables, **bold**, *italic*, bullet lists, numbered lists, line breaks.
 */
function formatMessageContent(text) {
  // Drop markdown horizontal rules (---, ***, ___ on their own line). We don't render
  // them as dividers, and unhandled they'd show up as literal dashes between sections.
  text = text
    .replace(/^[ \t]*([-*_])\1{2,}[ \t]*$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

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

function setLoading(loading) {
  state.isLoading = loading;
  const indicator = document.getElementById("typing-indicator");
  const btn       = document.getElementById("send-btn");
  const input     = document.getElementById("chat-input");

  if (loading) {
    // Wordless bouncing-dots indicator (see .typing-dots in style.css).
    indicator.classList.remove("hidden");
    btn.disabled   = true;
    input.disabled = true;
    document.getElementById("chat-messages").scrollTop = 99999;
  } else {
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

/** Escape for use INSIDE an attribute value. escapeHtml leaves quotes alone, which
 *  silently truncates any attribute containing one — e.g. a lever question that
 *  quotes the lever's own name. */
function escapeAttr(text) {
  return escapeHtml(text).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
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

// Per-data-source display metadata for the process trace. `cls` maps to the CSS
// colour variants (real=teal, surrogate=amber, everything else=muted).
const TRACE_SOURCE_META = {
  real_run:          { badge: "Official pathway result", cls: "real",      tag: "Official" },
  surrogate_xgboost: { badge: "Metamodel estimate",      cls: "surrogate", tag: "Metamodel" },
  reference:         { badge: "Reference lookup",   cls: "ref",       tag: "Reference" },
  context:           { badge: "Baseline context",   cls: "ref",       tag: "Context" },
  lookup:            { badge: "Registry lookup",    cls: "ref",       tag: "Lookup" },
};
// The headline badge reflects the strongest data source the answer relied on.
const TRACE_BADGE_PRIORITY = ["real_run", "surrogate_xgboost", "reference", "context", "lookup"];

/**
 * Render the agent's process trace: an always-visible source badge plus a
 * collapsible ordered list of the steps the agent actually took. The data is the
 * backend's factual record of execution (schemas.TraceStep) — NOT the model
 * narrating itself — so the user can verify how an answer was produced.
 */
function renderTrace(container, trace) {
  if (!Array.isArray(trace) || trace.length === 0) return;

  let headline = TRACE_BADGE_PRIORITY.find(src => trace.some(s => s.data_source === src));
  const meta = TRACE_SOURCE_META[headline] || { badge: "Process", cls: "ref" };
  const n = trace.length;

  const wrap = document.createElement("div");
  wrap.className = "trace";

  const summary = document.createElement("button");
  summary.type = "button";
  summary.className = "trace-summary";
  summary.setAttribute("aria-expanded", "false");
  summary.innerHTML =
    `<span class="trace-badge trace-badge--${meta.cls}">${meta.badge}</span>` +
    `<span class="trace-toggle">How I got this answer` +
    `<span class="trace-count">${n} step${n > 1 ? "s" : ""}</span>` +
    `<span class="trace-caret" aria-hidden="true">▾</span></span>`;

  const body = document.createElement("div");
  body.className = "trace-body";
  const ol = document.createElement("ol");
  ol.className = "trace-steps";

  for (const step of trace) {
    const sm = TRACE_SOURCE_META[step.data_source] || { cls: "ref", tag: step.data_source };
    const li = document.createElement("li");
    li.className = "trace-step" + (step.status === "error" ? " trace-step--error" : "");
    let html =
      `<div class="trace-step-head">` +
      `<span class="trace-step-label">${escapeHtml(step.label)}</span>` +
      `<span class="trace-tag trace-tag--${sm.cls}">${escapeHtml(sm.tag || "")}</span>` +
      `</div>` +
      `<div class="trace-step-origin">${escapeHtml(step.origin)}</div>`;
    if (Array.isArray(step.details) && step.details.length) {
      html += `<ul class="trace-step-details">` +
        step.details.map(d => `<li>${escapeHtml(d)}</li>`).join("") + `</ul>`;
    }
    li.innerHTML = html;
    ol.appendChild(li);
  }
  body.appendChild(ol);

  summary.addEventListener("click", () => {
    const open = wrap.classList.toggle("trace--open");
    summary.setAttribute("aria-expanded", open ? "true" : "false");
  });

  wrap.appendChild(summary);
  wrap.appendChild(body);
  container.appendChild(wrap);
}

/**
 * (Removed) Follow-up suggestion chips used to appear under every charted answer.
 * They now live in the Explore tab instead: canned questions belong in the
 * launcher, not stacked under the trace panel where they crowd the answer.
 */

/**
 * Split assistant text into ordered segments so charts render inline, exactly where
 * the model placed each ```chart block — not all bunched at the end.
 *
 * Returns an array of { type:"text", text } and { type:"chart", spec } in document
 * order. A chart block whose JSON fails to parse becomes { type:"chart", spec:null }
 * and is skipped at render time (the rest of the message still renders).
 */
function parseChartSegments(text) {
  const re = /```chart\s*([\s\S]*?)```/g;
  const segments = [];
  let lastIndex = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > lastIndex) {
      segments.push({ type: "text", text: text.slice(lastIndex, m.index) });
    }
    let spec = null;
    try { spec = JSON.parse(m[1].trim()); } catch { spec = null; }
    segments.push({ type: "chart", spec });
    lastIndex = m.index + m[0].length;
  }
  if (lastIndex < text.length) {
    segments.push({ type: "text", text: text.slice(lastIndex) });
  }
  return segments;
}

/**
 * Render a single chart from an assistant-authored spec, pulling the data from the
 * attached simulation bundle. Spec shape:
 *   { template: "emissions_by_sector" | "emissions_timeseries" | "cost_benefit",
 *     scenario: "current" | "scenario" | "both", title?: string }
 * Unknown templates / missing data render nothing.
 */
function renderChartFromSpec(container, spec, simData) {
  if (!spec || !simData) return;

  // Back-compat: a raw line-chart block ({years, bau, scenario, ...}) with no template.
  if (!spec.template && Array.isArray(spec.years)) {
    renderInlineChart(container, spec);
    return;
  }

  const view = spec.scenario || "both";
  const opts = { view, title: spec.title };

  switch (spec.template) {
    case "emissions_by_sector":
      if (simData.sector_comparison) {
        renderStackedSectorChart(container, simData.sector_comparison, opts);
        // The BAU-vs-scenario totals table only makes sense with a comparison.
        if (view === "both") renderProjectedTotals(container, simData.sector_comparison);
      }
      break;
    case "emissions_timeseries":
      if (simData.sector_comparison) {
        renderEmissionsTimeseries(container, simData.sector_comparison, opts);
      }
      break;
    case "cost_benefit":
      if (simData.cost_benefit_comparison) {
        renderCostBenefitChart(container, simData.cost_benefit_comparison, opts);
      }
      break;
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

  const MUTED  = "#6E6455";
  const GRID   = "#F2EADD";
  const BORDER = "#E5D9C8";
  const MONO   = "'IBM Plex Mono', monospace";
  const SANS   = "'Libre Franklin', system-ui, sans-serif";

  const datasets = [];

  // 1. BAU — red dashed reference
  if (Array.isArray(bau)) {
    datasets.push({
      label: "Business as Usual",
      data: bau,
      borderColor: "#B0413E",
      borderWidth: 1.5,
      borderDash: [6, 4],
      pointRadius: 0,
      tension: 0.3,
      fill: false,
      order: 3,
    });
  }

  // 2. HBLE pathway — teal solid reference
  if (Array.isArray(nz)) {
    datasets.push({
      label: "HBLE",
      data: nz,
      borderColor: "#4E8F5B",
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
      label: chartData.scenario_label || "Selected pathway",
      data: scenario,
      borderColor: "#E3B505",
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
          bodyColor: "#262421",
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

/**
 * Aggregate total-emissions trajectory (sum across all sectors per year), drawn as a
 * line chart via renderInlineChart. opts.view selects which lines to show:
 *   "current"  → BAU only   "scenario" → scenario only   "both" → both
 */
function renderEmissionsTimeseries(container, sectorComparison, opts = {}) {
  const view = opts.view || "both";
  const YEARS = [2019, 2025, 2035, 2040, 2050, 2060, 2070];

  const sumTraj = (trajectories) => {
    const t = trajectories || {};
    return YEARS.map((y) => {
      let sum = 0, any = false;
      for (const sector in t) {
        const v = t[sector][y];
        if (v != null) { sum += v; any = true; }
      }
      return any ? Math.round(sum * 10) / 10 : null;
    });
  };

  const bauT  = sectorComparison.baseline?.sector_trajectories || {};
  const scenT = sectorComparison.scenario?.sector_trajectories || {};

  const chartData = { years: YEARS };
  if (view === "current" || view === "both")  chartData.bau = sumTraj(bauT);
  if (view === "scenario" || view === "both") chartData.scenario = sumTraj(scenT);
  if (view === "current") chartData.scenario_label = "Current (BAU)";

  renderInlineChart(container, chartData);
}

// ── Sector stacked area chart ─────────────────────────────────────────────

// Emissions chart uses the team's Tableau SUBSECTOR colour scale — each app sector
// takes the colour of its closest Tableau subsector, with distinct shades within a
// family (energy=red/yellow, buildings=blue, transport=grey, industry=purple,
// waste=brown/tan, agriculture/livestock=orange/peach, land/forest=green). This
// deliberately overrides the Design Guide's sector palette for the emissions chart;
// the cost-benefit chart keeps the guide's gold/slate palette.
// 23 official inventory categories — source of truth: backend/sector_categories.json
// (generated from the team's crosswalk + Tableau legend). The backend also delivers
// these via `sector_meta_overrides` on every result bundle, which is merged OVER this
// map — so this is the built-in fallback; keep the two in sync.
const SECTOR_META = {
  fugitive_emissions:                 { label: "Fugitive Emissions",              short: "Fugitive",          color: "#E15759" },
  fuel_production:                    { label: "Fuel Production",                 short: "Fuel Production",   color: "#FF9DA7" },
  electricity_and_heat_generation:    { label: "Electricity and Heat Generation", short: "Electricity",       color: "#EDC948" },
  commercial:                         { label: "Commercial",                      short: "Commercial",        color: "#4E79A7" },
  residential:                        { label: "Residential",                     short: "Residential",       color: "#A0CBE8" },
  transportation:                     { label: "Transportation",                  short: "Transport",         color: "#79706E" },
  industrial_combustion:              { label: "Industrial Combustion",           short: "Ind. Combustion",   color: "#B07AA1" },
  ippu:                               { label: "IPPU",                            short: "IPPU",              color: "#D4A6C8" },
  solid_waste:                        { label: "Solid Waste",                     short: "Solid Waste",       color: "#9D7660" },
  wastewater_treatment:               { label: "Wastewater Treatment",            short: "Wastewater",        color: "#D7B5A6" },
  agriculture_and_managed_soil:       { label: "Agriculture and Managed Soil",    short: "Agriculture",       color: "#F28E2B" },
  livestock:                          { label: "Livestock",                       short: "Livestock",         color: "#FFBE7D" },
  deforestation:                      { label: "Deforestation",                   short: "Deforestation",     color: "#C7E9B4" },
  forest_land_removals:               { label: "Forest Land - Removals",          short: "Forest Removals",   color: "#A1D99B" },
  forest_land_methane:                { label: "Forest Land Methane",             short: "Forest CH4",        color: "#74C476" },
  other_land_use_conversion:          { label: "Other Land Use Conversion",       short: "Other Land Use",    color: "#4CAF50" },
  other_not_estimated_conversion:     { label: "Other Not Estimated Conversion",  short: "Other Conversion",  color: "#41A845" },
  other_not_estimated_sequestration:  { label: "Other Not Estimated Sequestration", short: "Other Seq.",      color: "#2E8B37" },
  other_not_estimated_soils:          { label: "Other Not Estimated Soils",       short: "Other Soils",       color: "#237A2E" },
  forest_land_sequestration:          { label: "Forest Land - Sequestration",     short: "Forest Seq.",       color: "#14602A" },
  carbon_capture_industries:          { label: "Carbon Capture Industries",       short: "Carbon Capture",    color: "#F5921B" },
  other_combustion:                   { label: "Other Combustion",                short: "Other Combustion",  color: "#B07AA1" },
  wetlands:                           { label: "Wetlands",                        short: "Wetlands",          color: "#86BCDA" },
};
// Colours drawn from the team's Tableau emissions scale, but spread across
// DISTINCT hues (blue, green, peach, tan, grey, olive, brown, pink, purple,
// lavender, yellow, coral, orange, teal, dark-green) so no two adjacent bands
// read as the same colour — distinguishability is prioritised over exact
// family-matching for the near-identical warm sectors.

// Stacking order = the team's legend order (from backend/sector_categories.json).
const SECTOR_STACK_ORDER = ["fugitive_emissions","fuel_production","electricity_and_heat_generation","commercial","residential","transportation","industrial_combustion","ippu","solid_waste","wastewater_treatment","agriculture_and_managed_soil","livestock","deforestation","forest_land_removals","forest_land_methane","other_land_use_conversion","other_not_estimated_conversion","other_not_estimated_sequestration","other_not_estimated_soils","forest_land_sequestration","carbon_capture_industries","other_combustion","wetlands"];
// Carbon-sink categories render in the "negative" stack (below zero). These are the
// sequestration categories; everything else (incl. Forest Land - Removals, a +source) is positive.
const SECTOR_NEGATIVE = new Set(["forest_land_sequestration","other_not_estimated_sequestration"]);

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
  )].sort((a, b) => a - b).filter(yr => yr >= 2025);

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

function renderStackedSectorChart(container, sectorComparison, opts = {}) {
  if (!sectorComparison) return;

  // view: "both" (BAU + scenario panels) | "current" (BAU only) | "scenario" (scenario only)
  const view = opts.view || "both";
  const YEARS = [2019, 2025, 2035, 2040, 2050, 2060, 2070];
  const MUTED  = "#6E6455";
  const GRID   = "#F2EADD";
  const BORDER = "#E5D9C8";
  const MONO   = "'IBM Plex Mono', monospace";
  const SANS   = "'Libre Franklin', system-ui, sans-serif";

  const scenarioTrajectories = sectorComparison.scenario?.sector_trajectories || {};
  const bauTrajectories      = sectorComparison.baseline?.sector_trajectories || {};

  // Per-result label/colour for the 23 inventory categories, sent by the backend
  // on every bundle (surrogate + real pathways) and merged over the built-in
  // SECTOR_META. Both flows now use the same categories, so no per-source relabel.
  const overrides = sectorComparison.sector_meta_overrides || {};
  const sectorMeta = sector =>
    ({ ...(SECTOR_META[sector] || { label: sector, color: "#888" }), ...(overrides[sector] || {}) });

  // Build stacked area datasets + net-total line
  function buildDatasets(trajectories, isBau) {
    // Sector area datasets (order: 1 renders behind the total line)
    const datasets = SECTOR_STACK_ORDER.map(sector => {
      const meta   = sectorMeta(sector);
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
        stack:           SECTOR_NEGATIVE.has(sector) ? "negative" : "positive",
        backgroundColor: meta.color + "D9",
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
    const totalColor = "#262421";
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
      borderDash:      isBau ? [6, 4] : [],
      pointRadius:     3,
      pointHoverRadius: 5,
      pointBackgroundColor: totalColor,
      backgroundColor: "transparent",
    });

    return datasets;
  }

  // Real BAU + HBLE reference net-total lines. These are attached to every payload
  // (both real-pathway and surrogate results). Guarded: a surrogate-only payload
  // without `references` simply renders without them.
  const HBLE_COLOR    = "#4E8F5B";   // action green — the aggressive frontier
  const BAU_REF_COLOR = "#C9BBA4";   // reference tan — ghost/comparison line
  const refs = sectorComparison.references || {};
  const refNet = series => {
    const traj = series?.sector_trajectories || {};
    return YEARS.map(y => SECTOR_STACK_ORDER.reduce((s, sec) => s + ((traj[sec] || {})[y] ?? 0), 0));
  };
  const referenceLines = [];
  if (refs.bau) referenceLines.push({
    label: "Official BAU net", _sector: "__refbau__", data: refNet(refs.bau),
    yAxisID: "y2", order: 0, fill: false, tension: 0, backgroundColor: "transparent",
    borderColor: BAU_REF_COLOR, borderWidth: 1.5, borderDash: [6, 4],
    pointRadius: 0, pointHoverRadius: 4, pointBackgroundColor: BAU_REF_COLOR,
  });
  if (refs.hble) referenceLines.push({
    label: "HBLE net (frontier)", _sector: "__refhble__", data: refNet(refs.hble),
    yAxisID: "y2", order: 0, fill: false, tension: 0, backgroundColor: "transparent",
    borderColor: HBLE_COLOR, borderWidth: 1.5, borderDash: [2, 3],
    pointRadius: 0, pointHoverRadius: 4, pointBackgroundColor: HBLE_COLOR,
  });

  // Compute shared Y bounds across both views
  function stackBounds(traj) {
    let posMax = 0, negMin = 0;
    for (const y of YEARS) {
      let pos = 0;
      for (const s of SECTOR_STACK_ORDER) {
        const v = (traj[s] || {})[y] ?? 0;
        if (SECTOR_NEGATIVE.has(s)) negMin = Math.min(negMin, v);
        else pos += v;
      }
      posMax = Math.max(posMax, pos);
    }
    return { posMax, negMin };
  }
  const b1 = stackBounds(bauTrajectories), b2 = stackBounds(scenarioTrajectories);
  // Fold the reference net lines into the bounds so the dashed lines never clip.
  const refVals = referenceLines.flatMap(d => d.data).filter(v => v != null);
  const refMax = refVals.length ? Math.max(...refVals) : 0;
  const refMin = refVals.length ? Math.min(...refVals) : 0;
  const yMax = Math.ceil(Math.max(b1.posMax, b2.posMax, refMax) * 1.08 / 50) * 50;
  const yMin = Math.floor(Math.min(b1.negMin, b2.negMin, refMin) * 1.2 / 10) * 10;

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
          color: "#262421",
          font: { family: SANS, size: 11, weight: "600" },
          padding: { bottom: 6 },
        },
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(255, 255, 255, 0.6)",
          borderColor: BORDER,
          borderWidth: 1,
          titleColor: "#262421",
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

  if (view === "current") {
    makePanel(buildDatasets(bauTrajectories, true), opts.title || "Current Emissions (BAU)", true);
  } else if (view === "scenario") {
    makePanel([...buildDatasets(scenarioTrajectories, false), ...referenceLines], opts.title || "Selected pathway", true);
  } else {
    makePanel(buildDatasets(bauTrajectories,       true),  "Business as Usual", true);
    makePanel([...buildDatasets(scenarioTrajectories, false), ...referenceLines], "Selected pathway", false);
  }

  // Right-side legend with click toggle
  const legendDiv = document.createElement("div");
  legendDiv.className = "stacked-chart-legend-right";

  for (const sector of SECTOR_STACK_ORDER) {
    const meta = sectorMeta(sector);
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

  // Static legend entries for the real BAU + HBLE reference net-lines (dashed).
  for (const rl of referenceLines) {
    const item = document.createElement("div");
    item.className = "stacked-legend-item";
    item.innerHTML =
      `<span class="stacked-legend-swatch" style="background:${rl.borderColor}"></span>` +
      `<span class="stacked-legend-label">${rl.label}</span>`;
    legendDiv.appendChild(item);
  }

  outerDiv.appendChild(legendDiv);
  container.appendChild(outerDiv);
}

// ── Cost / benefit diverging bar chart ────────────────────────────────────

// Benefit types (positive, stack up) in render order, with display labels + colors.
// Benefits use the team's Tableau cost-benefit legend colours — each key takes the
// colour of its matching legend entry by name. The four keys with no legend entry
// (congestion, road_safety, water_pollution, sector_specific) borrow the legend's
// "Other costs/benefits" teal / "Fuel cost savings" peach or a close tint.
const CB_BENEFIT_META = [
  { key: "human_health",       label: "Human Health",        color: "#5FA84C" },  // Human Health (green)
  { key: "air_pollution",      label: "Air Quality",         color: "#85C6C3" },  // Pollution (air) — light teal
  { key: "indoor_air_pollution", label: "Indoor Air Quality", color: "#9E4A86" },  // Air pollution (indoor) — magenta
  { key: "consumer_savings",   label: "Consumer Savings",    color: "#4E7CB5" },  // Consumer savings (blue)
  { key: "technical_savings",  label: "Technical Savings",   color: "#E6D24E" },  // O&M savings (yellow)
  { key: "congestion",         label: "Reduced Congestion",  color: "#2E8B85" },  // Other costs/benefits (teal)
  { key: "road_safety",        label: "Road Safety",         color: "#57A8A2" },  // Other (teal tint)
  { key: "crop_value",         label: "Crop Value",          color: "#A9CCE8" },  // Crop value (light blue)
  { key: "lvst_value",         label: "Livestock Value",     color: "#AF922B" },  // Livestock value (olive)
  { key: "ippu_value",         label: "Industrial Value",    color: "#ADD99E" },  // IPPU value (light green)
  { key: "ecosystem_services", label: "Ecosystem Services",  color: "#E8862E" },  // Ecosystem services (orange)
  { key: "ecosystem_services_grasslands", label: "Grasslands", color: "#E3C4DD" },  // Ecosystem services grasslands (pink)
  { key: "ecosystem_services_wetlands",   label: "Wetlands",   color: "#8B6D58" },  // Ecosystem services wetlands (brown)
  { key: "env_pollution",      label: "Env. Pollution",      color: "#D74A4A" },  // Pollution (environment) — red
  { key: "land_pollution",     label: "Land Pollution",      color: "#F2A0A0" },  // Pollution (land) — salmon
  { key: "water_pollution",    label: "Water Pollution",     color: "#9CCFCC" },  // pollution-family teal tint
  { key: "sector_specific",    label: "Sector-Specific",     color: "#F5C99A" },  // Fuel cost savings (peach) — generic
];

// SISEPUEDE's monetary costs (technical/system/fuel) aren't in the Tableau
// cost-benefit legend, so they stay slate — distinct from the benefit stack.
const CB_COST_META = [
  { key: "technical", label: "Technical Cost", color: "#7A93AC" },
  { key: "system",    label: "System Cost",    color: "#93A7BC" },
  { key: "fuel",      label: "Fuel Cost",      color: "#64809A" },
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
function renderCostBenefitChart(container, cbc, opts = {}) {
  if (!cbc || !cbc.scenario) return;

  // view: "both" (scenario bars + BAU net reference) | "scenario" (scenario, no reference)
  //       | "current" (BAU bars only)
  const view = opts.view || "both";
  const MUTED = "#6E6455", BORDER = "#E5D9C8";
  const MONO = "'IBM Plex Mono', monospace", SANS = "'Libre Franklin', system-ui, sans-serif";
  const YEARS = (cbc.years || [2025, 2035, 2040, 2050, 2070]).map(Number);
  const scen = cbc.scenario, base = cbc.baseline || {};
  const at = (obj, y) => obj[String(y)] || obj[y] || {};
  // Which series fills the bars: BAU for "current", otherwise the scenario.
  const primary = (view === "current") ? base : scen;

  const benDatasets = CB_BENEFIT_META.map(m => ({
    label: m.label, _cbkey: m.key, stack: "cb", order: 1,
    data: YEARS.map(y => (at(primary, y).benefits || {})[m.key] ?? 0),
    backgroundColor: m.color + "D9", borderColor: m.color, borderWidth: 0.5,
  }));
  const costDatasets = CB_COST_META.map(m => ({
    label: m.label, _cbkey: m.key, stack: "cb", order: 1,
    data: YEARS.map(y => (at(primary, y).costs || {})[m.key] ?? 0),
    backgroundColor: m.color + "D9", borderColor: m.color, borderWidth: 0.5,
  }));

  const netLine = {
    type: "line", label: "Net (benefits − costs)", _cbkey: "__net__", order: 0,
    yAxisID: "y2", data: YEARS.map(y => at(primary, y).net ?? 0),
    borderColor: "#262421", borderWidth: 2.5, pointRadius: 3, pointHoverRadius: 5,
    pointBackgroundColor: "#262421", fill: false, tension: 0,
  };
  // Real BAU + HBLE reference net-lines (per-year cost_benefit maps). Attached to
  // every payload; guarded so surrogate-only payloads still render. Draw the BAU
  // reference from the REAL run (references.bau), falling back to the payload
  // baseline if references are absent.
  const cbRefs = cbc.references || {};
  const refBau = cbRefs.bau || base;
  const bauNetLine = {
    type: "line", label: "Official BAU net", _cbkey: "__baunet__", order: 0,
    yAxisID: "y2", data: YEARS.map(y => at(refBau, y).net ?? 0),
    borderColor: "#C9BBA4", borderWidth: 1.5, borderDash: [6, 4],
    pointRadius: 2, pointBackgroundColor: "#C9BBA4", fill: false, tension: 0,
  };
  const hbleNetLine = cbRefs.hble ? {
    type: "line", label: "HBLE net (frontier)", _cbkey: "__hblenet__", order: 0,
    yAxisID: "y2", data: YEARS.map(y => at(cbRefs.hble, y).net ?? 0),
    borderColor: "#4E8F5B", borderWidth: 1.5, borderDash: [2, 3],
    pointRadius: 2, pointBackgroundColor: "#4E8F5B", fill: false, tension: 0,
  } : null;

  // Reference net lines only when explicitly comparing against BAU ("both").
  const datasets = [...benDatasets, ...costDatasets, netLine];
  if (view === "both") {
    datasets.push(bauNetLine);
    if (hbleNetLine) datasets.push(hbleNetLine);
  }

  // Y bounds from stacked sums (benefits up, costs down) + net line + references.
  let posMax = 0, negMin = 0;
  YEARS.forEach(y => {
    posMax = Math.max(posMax, at(primary, y).total_benefit ?? 0);
    negMin = Math.min(negMin, at(primary, y).total_cost ?? 0, at(primary, y).net ?? 0);
    if (view === "both") {
      const bn = at(refBau, y).net ?? 0, hn = at(cbRefs.hble || {}, y).net ?? 0;
      negMin = Math.min(negMin, bn, hn);
      posMax = Math.max(posMax, bn, hn);
    }
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
          display: true,
          text: opts.title || (view === "current"
            ? "Annual Cost & Benefit by Year (Current / BAU)"
            : "Annual Cost & Benefit by Year (Selected pathway)"),
          color: "#262421", font: { family: SANS, size: 11, weight: "600" },
          padding: { bottom: 6 },
        },
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(255,255,255,0.92)", borderColor: BORDER, borderWidth: 1,
          titleColor: "#262421", bodyColor: MUTED, footerColor: "#262421",
          titleFont: { family: MONO, size: 10 }, bodyFont: { family: MONO, size: 10 },
          footerFont: { family: MONO, size: 10, weight: "600" },
          filter: ctx => ctx.parsed.y !== 0 && ctx.parsed.y != null,
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)} B USD`,
            footer: items => {
              const y = items[0]?.label;
              const d = at(primary, y);
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
             grid: { color: "#F2EADD" }, border: { color: BORDER } },
        y2: { stacked: false, min: yMin, max: yMax, display: false, grid: { display: false } },
      },
    },
  });

  // Right-side legend with click toggle (benefits, then costs, then net).
  const legendDiv = document.createElement("div");
  legendDiv.className = "stacked-chart-legend-right";
  const legendItems = [
    ...CB_BENEFIT_META, ...CB_COST_META,
    { key: "__net__", label: "Net", color: "#262421" },
    ...(view === "both" ? [
      { key: "__baunet__", label: "Official BAU net", color: "#C9BBA4" },
      ...(cbRefs.hble ? [{ key: "__hblenet__", label: "HBLE net", color: "#4E8F5B" }] : []),
    ] : []),
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
  initTabs();
  loadPathwayCards();
  loadFeatureRegistry();
  document.getElementById("chat-input").focus();
});
