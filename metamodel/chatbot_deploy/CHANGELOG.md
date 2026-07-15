# Changelog — chatbot_deploy

## 2026-07-14 — Fix: surrogate what-if sector panels disagreed at 2019

### Problem
On a custom (surrogate) what-if, the stacked emissions chart's two panels (BAU vs Policy
Scenario) showed completely different sector compositions — even at 2019, which is shared
pre-policy history and identical across all real pathways.

### Cause
The **surrogate model and the real-run pathways attribute sub-sector emissions differently**:
energy sits in `entc` (~62 Mt @2019) in the real runs but in `scoe` (~59 Mt @2019) in the
surrogate's own 2019 baseline (`_load_sector_emissions_2019`). The 2026-07-14 real-BAU rewire
had made the BAU panel = *real* BAU while the Policy panel = *surrogate* — so the two stacks no
longer lined up (energy showed as `entc` in one panel and `scoe` in the other).

### Fix (`backend/services/agent.py` `_run_simulation_tool`)
The sector-stack **composition** must come from one source, so the two panels are now surrogate
scenario vs **surrogate BAU** (`result["sector_comparison"] = sim`) — internally consistent and
sharing the 2019 anchor. Real BAU + HBLE remain as overlaid net-total reference lines. The
**headline emissions %** and the **cost-benefit** block still compare against the **real BAU** run
(totals are comparable across sources; compositions are not). No frontend change.

Follow-up (not done here): harmonise the surrogate's per-sector convention with the real runs'
so a surrogate what-if's BAU panel matches a real pathway's — a data question (which mapping is
canonical), out of scope for this fix.

## 2026-07-14 — Process trace: show the user HOW an answer was produced

### Summary
Every assistant answer now carries a **process trace** — an always-visible source badge
(*Official pathway* / *Surrogate estimate* / *Reference lookup*) plus a collapsible
"How I got this answer" list of the exact steps the agent took: which tool ran, whether the
data came from the stored 6-pathway runs or the XGBoost surrogate, what external data was
consulted (AWS run database, stored CSVs), and what was compared. For a surrogate run the trace
**names the specific levers/conditions changed and their values** (e.g. "Policy levers set —
Reduce LOSSES: 0.90; Target RENEWABLE ELEC: 0.80"), resolved from the feature registry. It is
transparency the user can *verify* — the same information that goes to the logs, surfaced in the UI.

(Badge naming: the official named-pathway runs are labelled *"Official pathway"*, not "Real …",
so the surrogate isn't implied to be fake — the honest distinction is a full stored model run vs
its ML approximation.)

### Why
Users (and reviewers) need to confirm the agent's process looks sound, not just trust the
prose. Logs aren't visible to them mid-conversation.

### Key design decision
The trace is built from **actual tool execution**, never from the model narrating its own
steps. The model cannot author or fabricate it — so it is trustworthy for verification.

### What changed
**`backend/services/agent.py`** — new `_build_trace_event(step, tool, input, result, interp)`
turns each real tool call into a `{step, tool, label, data_source, origin, details, status}`
event (plain-language "logical source": stored pathway data / surrogate / AWS run database /
registry). `run()` accumulates a `trace` list across the agentic loop and returns it;
`_run_simulation_tool` now reports `data_source` / `compared` / `baseline_source` in its
interpretation so the trace can state what the surrogate was compared against.

**`backend/schemas.py`** — new `TraceStep` model; `ChatResponse.trace: list[TraceStep]`.
**`backend/app.py`** — `/api/chat` returns `trace`.

**`frontend/app.js` + `style.css`** — `renderTrace()` draws the badge + collapsible step
timeline under each assistant message (real=teal, surrogate=amber, reference=muted; error
steps flagged). Wired through `appendMessage(…, traceData)`. Cache version bumped to `20260714c`.

### Verification
`tests/test_pathways_lookup.py` **7/7** — new Test 7 locks the trace: surrogate step →
`surrogate_xgboost` noting the real BAU/HBLE compare; named pathway → `real_run`; bad pathway →
`status="error"` with the failure surfaced; all `TraceStep`-valid. `renderTrace` driven under a
JavaScriptCore DOM shim across real/surrogate/error/empty cases (headline badge priority,
step count, no-op on empty) — no runtime errors. `app.js` parses; full FastAPI app imports.
Live browser eyeball still to do.

## 2026-07-14 — Named pathways in the UI + real-BAU/HBLE comparisons

### Summary
Four policymaker-facing changes on top of the real-pathways work:
1. **Quick-start bar** now exposes the **6 named pathways** (BAU, NDC 2.0, NDC 2.5, NDC2
   Unconditional, NDC2 Uncond. (Alt), HBLE) as one-click buttons, each routing to
   `get_pathway_results`. "Net Zero" is renamed **HBLE** everywhere in the UI.
2. **Data-source logging** — every model run logs where its numbers came from:
   `run_simulation: data_source=surrogate_xgboost (… baseline=real_bau|surrogate_bau)` and
   `get_pathway_results: … (data_source=real_run)`.
3. **Cost-benefit labels** — `Ecosystem Svcs (Grasslands/Wetlands)` → **Grasslands** / **Wetlands**;
   the generic **Ecosystem Services** line is unchanged. Rename only — no field removed, totals intact.
4. **Custom what-ifs now compare against the REAL BAU (baseline) + REAL HBLE (frontier)**, not the
   surrogate's own BAU. This is the substantive change (see below).

### Why (#4)
Previously a `run_simulation` what-if was compared surrogate-vs-surrogate BAU so the surrogate's
~+8% bias cancelled, with real BAU/HBLE drawn only as reference lines. Policymakers asking "what if"
need a **real** comparison, so the headline "% vs BAU" and all deltas are now measured against the
real BAU run, with real HBLE as the ambition frontier. This knowingly folds the surrogate's model
error into the comparison — an accepted, temporary trade-off (to be revisited).

### What changed
**`backend/services/pathways_lookup.py`** — extracted the delta math from `build_pathway_comparison`
into a shared **`compare_series(scenario, baseline)`** (returns `comparison` / `sector_deltas` /
`cost_benefit_deltas`). It iterates the **fixed anchor years** (`EMISSION_YEARS` / `CB_YEARS`), so it
is robust to the surrogate emitting a denser year grid than the anchor-only real BAU. Named-pathway
behaviour is unchanged (locked by the existing test).

**`backend/services/agent.py`**
- `_run_simulation_tool`: run the surrogate for the **scenario only**, then compare it against
  `build_reference_bundle()["bau"]` (real BAU) via `compare_series`; carry real HBLE as the frontier.
  Falls back to the surrogate's own BAU if the curated real runs can't load (never breaks a run).
  Added the `data_source=surrogate_xgboost` log line.
- `_build_result_summary`: added per-metric `hble_value` (from the real HBLE reference) so Claude can
  narrate where a scenario lands between real BAU and the HBLE frontier. BAU stays the % baseline.
- System prompt: triage B, RULE 7, the reference-pathways note and the ambition scale updated — custom
  what-ifs compare to real BAU + real HBLE, with the model-error caveat; "Net Zero" → "HBLE".

**`frontend/index.html` / `app.js`** — 6 preset buttons + `PRESETS` messages that name each pathway
(so they route to `get_pathway_results`); welcome copy and the legacy `renderInlineChart` label
"Net Zero" → "HBLE"; `CB_BENEFIT_META` label renames. The stacked & CB charts already carried real
BAU/HBLE reference lines from the 2026-07-13 work — no dedup was needed (the real-BAU line overlays
the *scenario* panel for in-panel comparison; removing it would regress the UX).

**`backend/services/predictor.py`** — `COST_BENEFIT_LABELS` grassland/wetland renames (kept in sync
with the chart's `CB_BENEFIT_META`, the user-visible source).

### Verification
`tests/test_pathways_lookup.py` extended to **6/6** (no S3, no API key): the original 4 still pass
(proves the `compare_series` refactor didn't disturb named pathways), plus **Test 5** (`compare_series`
on a surrogate-like denser-year scenario → deltas keyed by anchors, off-anchor year dropped, real-BAU
values carried, ≈-50% headline) and **Test 6** (drives `agent._execute_tool_call("run_simulation", …)`
with a fake predictor → baseline swapped to real BAU @2070=277.59, `hble_value` narrated, real BAU+HBLE
references on both bundles, `SimulationResponse`-valid). `app.js` parses (JavaScriptCore), full FastAPI
app imports. Live `/api/chat` routing + browser eyeball still need the full runtime (API key + model).

## 2026-07-13 — Serve REAL pre-run data for the 6 named pathways

### Summary
The 6 officially named pathways (BAU, NDC 2.0, NDC 2.5, NDC2 Unconditional, NDC2 Unconditional
(Alt), Candidate NDC3 / HBLE) are now answered from **real SISEPUEDE runs**, not the XGBoost
surrogate, via a new `get_pathway_results` tool. Every chart is now anchored by **real BAU + real
HBLE reference lines** — attached to surrogate results too. The surrogate stays for custom
"what-if" exploration only.

### Why
The surrogate cannot reproduce the coordinated high-ambition pathways: for HBLE it predicted ~115
MtCO₂e @2070 where the real run is **6.4**. It was trained only on the independent random LHS, whose
mean-lever ambition never reaches the coordinated corner these pathways occupy. Real runs already
exist for all 6, so we serve them directly and keep the surrogate where it is accurate (near BAU).

### What changed
**`backend/services/pathways_lookup.py`** (new)
- `PATHWAY_REGISTRY` (single source of truth: display_name → primary_id / strategy_id / aliases).
- Cached local-first→S3 loaders for `uganda_pathways.csv` (WIDE emissions, indexed by `time_period`)
  and `cba_data_air_pollution.csv` (LONG cost-benefit). `gdp_mmm_usd` read straight from the column.
- `get_pathway_emissions`, `get_pathway_cost_benefit`, `_build_series` (predict()-shaped),
  `build_reference_bundle` (real BAU+HBLE), `build_pathway_comparison` (predict_comparison()-shaped
  + references), `get_pathway_driver_variables` (real per-lever trajectories, no KNN).
- Cost-benefit: costs are the exact set `{technical_cost, system_cost, fuel_cost}` summed and passed
  through **as-is** (mixed sign — matches the training convention; `technical_savings` stays a
  benefit). BAU has zero cost-benefit by construction.

**`backend/services/agent.py`**
- New `get_pathway_results` tool (enum of the 6 pathways, derived from `PATHWAY_REGISTRY`) +
  `_get_pathway_results_tool` handler (reuses `_build_result_summary` unchanged; `data_source="real_run"`).
- `_attach_real_references` injects real BAU+HBLE reference series into every `run_simulation` result
  too — the surrogate baseline and narrated "% vs BAU" are left untouched (that ratio stays
  surrogate-vs-surrogate, where the bias cancels).
- System prompt: triage category A routes named pathways to `get_pathway_results`; references are now
  real BAU + HBLE; new RULE 7 (named→real, custom→surrogate, never mix). Removed the dead
  `PREDEFINED_PATHWAYS`/`netzero`-preset routing.

**`frontend/app.js`**
- `renderStackedSectorChart` / `renderCostBenefitChart`: real BAU + HBLE reference net-lines
  (dark dashed + teal `#007A6F` dashed), folded into y-bounds, legend entries — all **guarded** so
  surrogate-only payloads without `references` still render.
- Added `indoor_air_pollution` to `CB_BENEFIT_META` (was silently dropped).

### Verification
Read-only smoke (real HBLE @2070 = 6.348 ✓), `SimulationResponse` schema validation, agent handler +
reference-injection tests, and a JavaScriptCore integration test running the real `app.js` render
functions against real payloads (reference lines + `indoor_air_pollution` render; guards hold on
no-reference payloads). Full FastAPI app imports cleanly. Live `/api/chat` LLM routing + browser
eyeball still to be run in the full runtime (needs API key + model env).

**Automated regression test (added 2026-07-14):** `tests/test_pathways_lookup.py` locks the whole
contract against the local curated CSVs (no S3, no API key): registry/alias resolution; the reader
invariants (real HBLE @2070 = 6.348 not ~115, BAU cb ≡ 0 w/ GDP, exact cost-key membership,
`indoor_air_pollution` surfaced, anchor-year-only); the `get_pathway_results` handler producing a
`SimulationResponse`-valid `data_source="real_run"` payload with real BAU+HBLE refs on both charts +
driver detail + graceful error on a bad name; and `_attach_real_references` inject/guard behaviour.
Run: `python -m tests.test_pathways_lookup` (4/4 pass). This covers everything up to the LLM's tool
choice — the live routing decision itself still needs the full runtime.

### Open blocker (deploy)
The two curated CSVs are local-only (gitignored). `_read_curated_csv` falls back to S3 at
`run_database/<run>/pathways/<file>` but that key is **provisional** — confirm it with the run
producers, and ship the CSVs wherever the run's `ATTRIBUTE_*` files already ship.

## 2026-07-06 — Repurpose `get_scenario_variables` to explain the physical "how"

### Summary
`get_scenario_variables` no longer re-fetches aggregate emissions. It now returns, per changed
lever, the **input driver variables** the transformation moves (from `model_input`, all 54 lever
groups, 2015→2070) plus the **downstream output variables** it affects (from `model_output`, the
44 groups that have them, 2019→2070). Headline emissions/GDP/cost are now owned solely by
`run_simulation` (the XGBoost surrogate).

### Why
The old behaviour retrieved `emission_co2e_subsector_total_*` — which the surrogate already
predicts. Worse, those came from the *nearest-neighbour* scenario, so they could **contradict** the
surrogate-driven chart. The surrogate can never expose *which physical variables* a lever moves;
that "how" is the genuinely additive thing this tool now provides.

### What changed
**`backend/services/s3_lookup.py`**
- Removed `get_scenario_outcomes` (emissions retrieval), the broken orphaned `get_changed_variables`,
  and the now-unused sector-inference helpers (`_infer_sector`, `_sector_for_group`, etc.).
- Added map loaders/resolvers: `_load_variable_maps`, `_load_vtl`, `_normalize_tcode`,
  `_input_fields_for_group` (with fallback), `_output_fields_for_group`.
- Added engine `get_scenario_variable_trajectories(group_ids, l_values, top_n=6)`: one KNN
  (`find_nearest_lhs_trial`, design_id=4) → reads **both** `get_model_inputs_row` and
  `get_model_outputs_row` for the matched `primary_id` → per lever returns input + output variable
  trajectories, each top-N by |% change| with a total count.

**`backend/services/agent.py`**
- `_get_scenario_variables_tool` now calls the new engine and formats a two-section block per lever
  ("Input variables changed 2015→2070" + "Downstream output variables affected 2019→2070"), with
  "…and N more" capping and the `design_note` caveat.
- Rewrote the tool schema `description` and system-prompt rule #2 to describe the new behaviour.
- Fixed two stale prompt/label bugs:
  - handler strings now say "design_id=4 (L and X both vary)" (were "design_id=3 — L-only");
  - the L-transform block no longer references the nonexistent `transformer_default_magnitude`;
    it now points Claude to `semantic_min`/`semantic_max`/`policy_description` and to this tool.

### Data sources (read-only)
- `metamodel/data/ssp/transformation_variable_map.csv` — input drivers (`transformation_code →
  variable → variable_field`), 575/575 present in `model_input`.
- `metamodel/data/ssp/transformation_output_variable_map.csv` — downstream outputs, 737/737 in
  `model_output`.
- `.../sisepuede_run_<RUN>/VARIABLE_TRAJECTORY_GROUPS_L.csv` — input fallback keyed by integer
  `variable_trajectory_group` (guarantees all 54 groups resolve).
- Registry join: normalize `transformation_code` with `_normalize_tcode` (strip
  `(_STRATEGY)?(_NZ)?$`). NB: the registry's `variables` field holds LaTeX *display names*, not
  column codes — the real codes are `variable_field`; that mismatch (0/547) is why the old
  `get_changed_variables` silently returned nothing.
- Deployment: ship the two map CSVs wherever the run dir's `ATTRIBUTE_*` CSVs already ship.

### Coverage
- Input variables: **54/54** groups (with fallback).
- Output variables: **44/54** groups. The 10 without downstream outputs — **1, 5, 6, 7, 8, 17, 18,
  38, 50, 51** (incl. rice-CH4 group 1) — return input variables only.

### Verification (all passed)
- Coverage check (no S3): 54/54 inputs, 44/54 outputs.
- Direct-call trace vs live S3: group 1 input `ef_agrc_anaerobicdom_rice_kg_ch4_ha` ~-37% by 2070,
  empty outputs; group 4 (`INC_PRODUCTIVITY`) 7 inputs + 45 outputs, top-N capped.
- Tool-level formatting: two sections per lever, caveat present, no `emission_co2e_subsector_total`.
- **Full live LLM query**: `run_simulation` then `get_scenario_variables`; Claude narrated headline
  emissions (surrogate) plus the crop-yield driver ramp and downstream industrial-energy outputs.
- No regressions: `run_simulation`/sector chart and `predictor._load_sector_emissions_2019` unchanged.
- **Automated test**: `tests/test_s3_lookup.py::test_get_scenario_variable_trajectories` locks the
  engine contract (fallback → ≥1 input per group; LEAKS has no outputs / SCOE does; record shape;
  anchor years; `top_n` cap). Ported Tests 1–2 too; Test 1 now uses `design_id=4` (the 2026-05-30
  run dropped `design_id=3`). Run: `python -m tests.test_s3_lookup` (3/3 pass). See `tests/README.md`.

### Notes
- design_id=4 neighbours also vary the exogenous X conditions, so some output % changes are extreme
  (near-zero-base variables). Correct, but a future refinement could cap/annotate very large %s.
- A teaching walkthrough lives at `docs/tutorial_scenario_variables_and_L_transform.html` (the
  `docs/` dir is gitignored, so it is local-only).
