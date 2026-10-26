# RDM agent — build plan

*Branch `rdm-tools`, 2026-10-06. **Built on the current run (30 May 2026); new runs will keep the same structure.** Draft due before DMDU, 9 November 2026 (≈ 5 weeks).
**Data sources:** emissions come from `decomposed_emissions` (final, post-processed); the
variables that explain them come from `model_output`.
Design: `rdm_tools_design.md` (draft v1). Experiment: `paper1/md_to_claude/study_plan.md` §2.
Task list: `rdm_todo.md`. This file says **in what order** we build, and how the system stays
independent of any one SISEPUEDE run.*

---

## The rule that makes new runs cheap

**No code names a run.** Everything run-specific lives in one manifest file. When the new
runs arrive, we edit the manifest and re-run the pipeline; no tool, prompt or test changes.

```yaml
# backend/rdm/runs/<run_name>.yaml   (one file per run; RDM_RUN or the ACTIVE file selects it)
run_id: "2026-05-30t21;35;56.244639"
region: uganda
s3:
  bucket: sisepuede-data
  run_prefix: "run_database/sisepuede_run_{run_id}/"
  tables:
    emissions: decomposed_emissions   # final emissions
    variables: model_output           # variables that explain the emissions
    inputs: model_input
    costs_benefits: cb
local:
  run_dir: "data/ssp/sisepuede_run_{run_id}/"     # LHC design, group definitions, primary ids
  structural_map: "data/ssp/transformation_output_variable_map.csv"
surrogate: "surrogate_model_sector/trained_models/xgb_pipeline_sector_independent_{run_id}.pkl"
years: [2025, 2035, 2040, 2050, 2060, 2070]
```

Also read from the run, never hard-coded: the number and ids of L and X groups, their
variables, and which outputs exist.

**What "only change the paths" does and does not cover.** Code: yes, nothing else changes.
Data artifacts: they are *regenerated* by re-running the pipeline (mapping, run-level store,
response map) and the **XGBoost must be retrained** on the new run (existing Athena pipeline in
`surrogate_model_sector/athena/`). Plan for that time when the runs land.

Today the run id is hard-coded in `backend/config.py`, `backend/services/s3_lookup.py`,
`scripts/build_lever_digest.py`, `scripts/build_lever_response_map.py` and
`surrogate_model_sector/config/ml_training_workflow_config.yaml`. The new code reads the
manifest instead; the deployed `services/` stay untouched on `metamodel`.

---

## Code layout (new, on `rdm-tools`)

```
backend/rdm/
  runs/            one manifest per run (+ loader: get_run())
  data/            lhc.py (L/X per future), groups.py (variables per group), store.py (queries)
  mapping/         build_mapping.py → lever_x_output_map.csv + review .xlsx
  tools/           catalog.py, knowledge.py (v0/v1 switch), experiment.py, context.py, schemas.py
  harness/         loop.py, state.py, rules.py, log.py
  prompt/          system_prompt.md (written from scratch, identical in v0 and v1)
tests/rdm/
```

The experimentation tools wrap the existing `services/predictor.py` (XGBoost) rather than
rewrite it.

---

## Phases

### Phase 0 · Foundations (week 1: 7–12 Oct) — start here

| # | Step | Output | Done when |
|---|---|---|---|
| 0.1 ✅ | Run manifest + loader (2026-10-06) | `rdm/runs/run_2026_05_30.yaml`, `get_run()`, `tests/rdm/test_runs.py` | A test switches manifests and every path follows (4 tests pass; S3 tables verified) |
| 0.2 ✅ | Data access: LHC, groups, primary ids (2026-10-06) | `rdm/data/lhc.py`, `groups.py`, `tests/rdm/test_data.py` | 100,000 runs with all 54 L and 13 X in [0, 1]; 2 runs without LHC values (primary 0, future 0) and 5 LHC columns without a group (1682, 1707, 1725, 1734, 1740) reported |
| 0.3 🔶 | **Mapping pipeline** (built 2026-10-06; awaiting Alexa's review) | `rdm/data/sample.py` (5,000-run sample, ≈ $0.73 once), `rdm/mapping/build_mapping.py` → `rdm/mapping/maps/<run>.csv`, `review_xlsx.py` → `docs/lever_x_output_mapping.xlsx` | 4,805 links; 46 of 54 levers move emissions and variables; lever 6 moves nothing; 11 of 13 X move outputs; Alexa signs off the review |
| 0.4 🔶 | Run-level store (sample done 2026-10-06; full store pending) | `rdm/data/store.py`: `Store.values`, `curve` (one group), `pair` (L × X grid: n, p10, median, p90 in original units) over the 5,000-run sample | Same interface over the full 100k runs before the freeze (≈ 4,000 runs per 5 × 5 cell instead of ≈ 200) |

0.3 has two sources: the structural map (which outputs a transformation touches in
SISEPUEDE) and an empirical pass on the runs (which outputs actually move with each L and X).
Where they disagree, both are kept and flagged for review.

**Before Phase 1 (2026-10-07):** decide the knowledge layer's data format — the response graph
proposed in `rdm_response_graph.md` — and prototype it on the lever 35 chain.

### Phase 1 · Tools (week 2: 13–19 Oct)

| # | Step | Done when |
|---|---|---|
| 1.1 | `search_catalog` over registry + mapping + units | Policy-maker words return the right ids and units on a test list |
| 1.2 | The four knowledge tools with the v0 / v1 switch | Same schema in both; v0 returns names, v1 values; unit tests on the sample store |
| 1.3 | Experimentation tools over `predictor.py`: define, run, find_vulnerabilities, compare, search | Fixed seed → identical ensembles; paired BAU on the same futures |
| 1.4 | Tool descriptions with boundaries | Reviewed against the "one question per tool" rule |

### Phase 2 · Harness and prompt (weeks 2–3: 16–24 Oct)

| # | Step | Done when |
|---|---|---|
| 2.1 | Loop, state store, rules as validations, per-turn log | A scripted run per category passes end to end |
| 2.2 | `declare_plan` gate | No other tool runs before it |
| 2.3 | System prompt from scratch | Identical in v0 and v1; no lever effects; diffed against the v1 payload |
| 2.4 | Simulated user for automated runs | Confirmation answered with a fixed reply |

### Phase 3 · Question bank and experts (in parallel, start now)

The experts need lead time, so this runs alongside phases 0–2.

| # | Step | When |
|---|---|---|
| 3.1 | Rewrite the bank in policy-maker language; drop the pathway question | week 1 |
| 3.2 | Settle the default success criterion (now relative to the surrogate's BAU) | week 1 |
| 3.3 | Send the expert instrument | end of week 1 |

### Phase 4 · Test and pilot (week 3: 20–26 Oct)

Unit tests, one scripted flow per category, pilot of 2–3 questions × 3 repetitions in v0 and
v1, stochasticity gate.

### Phase 5 · Freeze and run (week 4: 27 Oct – 2 Nov)

Freeze commit, model hash, prompt, tools, question bank, manifest. Full run: 10–12 questions ×
2 versions × repetitions. Score and write in the last week.

---

## When the new runs arrive

1. Add `rdm/runs/<new_run>.yaml`; set `RDM_RUN=<new_run>`.
2. Retrain the XGBoost with the Athena pipeline (`surrogate_model_sector/athena/`).
3. Re-run `build_mapping.py`; Alexa reviews the diff against the previous run.
4. Rebuild the run-level store (sample, then full).
5. Re-run the test suite. Nothing else changes.

If they arrive after the freeze (≈ 27 Oct), the experiment runs on the current run and the new
run becomes a robustness check. Decide the cut-off date with the team.

## Open questions for the team

- The lever LHC file has 5 columns with no group definition (1682, 1707, 1725, 1734, 1740).
  What are they? They are left out of the design for now.

- When will the new runs be ready, and will the L and X groups keep their ids and definitions?
- Will `model_output` store the same variables (we need the mapped ones at minimum)?
- Who retrains the XGBoost on the new run?
