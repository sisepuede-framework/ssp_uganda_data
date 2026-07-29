# Design brief — Uganda Climate Pathways Explorer

**For: Claude Design · From: the CDPM chatbot team · 28 July 2026**

> **Status, 29 July 2026 — Option 3 (tabbed workspace) was chosen and has been built.** The live
> layout is three tabs (Official pathways · Explore · How this works) over a shared conversation,
> with the launcher panel folding away after the first question. Screenshots:
> `docs/images/tab-1-official-pathways.png`, `tab-2-explore.png`, `tab-3-how-this-works.png`.
> This brief is kept as the record
> of what was asked for; any further design work should start from the built screens, not from
> section 4 below.

We need visual prototypes of three layout options for an existing, working tool. Pick nothing yet —
we want to see the three side by side, choose one, and only then build it. Deliverable per option:
a static prototype plus a screenshot we can drop into a review document.

---

## 1. What the tool is

The **Uganda Climate Pathways Explorer** (renamed this week from *Uganda Climate Policy Simulator*)
lets policymakers explore how different levels of sectoral transition, and different assumptions
about Uganda's future, affect emissions, costs, and development benefits between 2025 and 2070.

It answers from **two different sources**, and the entire design problem follows from this:

| | Where it comes from | How it must read |
|---|---|---|
| **Official pathway result** | One of 6 stored simulations from Uganda's Country Development Pathway Model (CDPM), built with SISEPUEDE. Includes the **HBLE pathway**, which underpins Uganda's **NDC 3.0**. | Authoritative. Official. |
| **Metamodel estimate** | A live metamodel trained on ~99,000 CDPM simulations, answering combinations nobody officially ran. | Useful and fast, but an estimate — clearly secondary to the official runs. |

The novelty we are selling: those six official pathways used to live in a PDF. Now they can be
interrogated in conversation **and** extended to a very large range of combinations that were never
simulated. A user should understand that within ten seconds of landing on the page.

## 2. Vocabulary — please do not deviate

| Never write | Write instead |
|---|---|
| "Simulator", "Policy Simulator" | **Uganda Climate Pathways Explorer** |
| "simulation" as a generic word for any answer | **official pathway result** / **metamodel estimate** |
| "Quick start" | **Official pathways** |
| "infinite" / "unlimited" combinations | **a very large range of pathway combinations** |
| "HBLE" bare | **High Benefits, Low Emission (HBLE) pathway** — the analytical basis for Uganda's NDC 3.0 |
| "the model", "the AI" | Uganda's **Country Development Pathway Model (CDPM)**, **SISEPUEDE** framework, the **metamodel** |

## 3. The problem to solve

Two reviewers looked at the current single-column chat and said the same thing in different words:

1. **Users don't know what they can ask**, so they ask nothing and leave. The question space is
   actually large and structured: **54 sectoral-transition levers (L)** across 16 sectors, and
   **13 country conditions (X)** — the L and X of an XLRM table (see
   `rdm_levers_and_uncertainties.md`). None of that is visible.
2. **The buttons are in the wrong place and do only one job.** Today six pathway buttons sit above
   the chat. We want the tool introduced first, then *several* groups of clickable prompts a user can
   work through: official pathways, then ambition questions (the L's), then conditions questions
   (the X's) — ideally always visible, e.g. in a left sidebar.

## 4. Three options to prototype

Use the same content in all three so we compare layouts, not copy.

### Option 1 — Persistent left rail
Introduction at the top of the chat column. An always-visible left sidebar, roughly 260–300px, with
three collapsible groups of prompt buttons:
- **Official pathways** — BAU, NDC 2.0, NDC 2.5, NDC2 Unconditional, NDC2 Unconditional (Alt),
  HBLE (NDC 3.0 basis). Each needs a one-line explanation on hover or beneath the label.
- **Ambition — the sectoral transitions (L)** — e.g. *"What happens if Uganda reaches only part of
  the HBLE ambition in transport and electricity?"*, *"What are the effects of delaying the
  transition in one or more sectors?"*
- **Conditions — the country assumptions (X)** — e.g. *"How would faster GDP growth affect emissions
  and implementation costs?"*, *"What if fossil fuel prices stay high?"*
Each group needs a visible marker of what kind of answer it returns (official vs estimate).

### Option 2 — Guided landing, then chat
A full-width introduction screen first: what the tool is, the two answer types side by side, a small
XLRM diagram (Uganda decides the L's; the world decides the X's), and a short 3–4 step "how to use
this" walkthrough. It collapses into a slim rail (Option 1's sidebar) as soon as the user asks
anything. Best for a first-time World Bank reviewer who has never seen the tool.

### Option 3 — Tabbed workspace
Tabs across the top — *Explore* · *Official pathways* · *Ambition* · *Conditions* · *How this works*
— with the chat persistent underneath. Each tab is a browsable set of prompts; clicking one drops the
question into the chat. Best if we later add non-chat content (documentation, the lever catalogue).

## 5. What must not change

These already work and were specifically praised — keep them, restyle at most:

- **"How I got this answer"** — a collapsible panel under each answer with a source badge
  (*Official pathway result* teal / *Metamodel estimate* amber) and the numbered steps the system
  actually executed. This is our credibility feature. It must stay prominent.
- **Charts render inline, mid-answer**, wherever the assistant placed them — not collected at the
  bottom. Stacked emissions by sector (two panels: BAU vs selected pathway), an emissions time series,
  and a diverging cost/benefit bar chart, each with a right-hand clickable legend.
- **Follow-up suggestion chips** below an answer that produced a chart.
- The **BAU** and **HBLE** reference lines on every chart.

## 6. States to design (for the chosen option, all three at least sketched)

Empty / first load · loading (the assistant can take 10–30s) · an answer with two charts and the
trace panel open · an error ("the model could not be reached") · a declined question (out of scope,
e.g. another country) · mobile / narrow.

## 7. Technical constraints

- Vanilla **HTML + CSS + JS**. No framework, no build step, no bundler. The app is three files:
  `frontend/index.html`, `frontend/style.css`, `frontend/app.js`.
- Reuse the existing design tokens in the `:root` block of `frontend/style.css` (editorial serif
  headlines, Libre Franklin sans, IBM Plex Mono for model voice; amber accent, teal for official
  results). The team's Design Guide PDF is in `design/`.
- Charts are Chart.js 4.4 via CDN — keep the existing canvas containers.
- Respect the existing 900px breakpoint; below it the sidebar must collapse rather than squeeze.
- Accessibility: keyboard-reachable prompt buttons, visible focus, and colour is never the only
  signal distinguishing official results from estimates (add a word or an icon).

## 8. What comes with this brief

Attach all of these — the redesign should start from the real thing, not from a description of it:

| Attachment | Why it is needed |
|---|---|
| `docs/images/before-single-column.png` | The layout as it was before the tabs — the single column this work replaced. |
| A screenshot of an answered question, with charts and the **"How I got this answer"** panel expanded | The single most important reference: it shows the elements that must survive the redesign. |
| `frontend/index.html` | The full current markup — 88 lines, no framework. |
| `frontend/style.css` | The design tokens live in the `:root` block at the top; reuse them rather than inventing a palette. |
| `frontend/app.js` | Only needed for how charts, the trace panel, and the follow-up chips are constructed. |
| `design/Design Guide.pdf` | The team's existing visual language. |

## 9. What to send back

Per option: a static prototype and one screenshot at desktop width. Keep the option numbering above —
the screenshots go straight into section 5 of `change_proposal.md`, which is what our experts review.
