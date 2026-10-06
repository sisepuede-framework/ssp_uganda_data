# RDM agent — build plan

*Branch `rdm-tools`, 2026-10-06. Draft due before DMDU, 9 November 2026 (≈ 5 weeks).
Design: `rdm_tools_design.md` (draft v1). Experiment: `paper1/md_to_claude/study_plan.md` §2.
Task list: `rdm_todo.md`. This file says **in what order** we build, and how the system stays
independent of any one SISEPUEDE run.*

---

## The rule that makes new runs cheap

**No code names a run.** Everything run-specific lives in one manifest file. When the new
runs arrive, we edit the manifest and re-run the pipeline; no tool, prompt or test changes.

```yaml
# backend/rdm/runs/<run_name>.yaml   (one file per run; RDM_RUN=<run_name> selects it)
run_id: "2026-05-30t21;35;56.244639"
region: uganda
s3:
  bucket: sisepuede-data
  run_prefix: "run_database/sisepuede_run_{run_id}/"
  tables: [model_input, model_output, decomposed_emissions, cb]
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
| 0.1 | Run manifest + loader | `rdm/runs/`, `get_run()` | A test switches manifests and every path follows |
| 0.2 | Data access: LHC, groups, primary ids | `rdm/data/lhc.py`, `groups.py` | Returns L/X values per run and variables per group for the current run |
| 0.3 | **Mapping pipeline** (priority) | `build_mapping.py` → `lever_x_output_map.csv` + review xlsx | Every lever and X has its emissions and variables, each tagged structural / empirical; the 19 incomplete levers filled; Alexa reviews |
| 0.4 | Run-level store (development sample first) | Parquet: primary_id, L/X values, year, mapped outputs | Sample of ~2,000 runs locally; full CTAS in Athena later (≈ $1) |

0.3 has two sources: the structural map (which outputs a transformation touches in
SISEPUEDE) and an empirical pass on the runs (which outputs actually move with each L and X).
Where they disagree, both are kept and flagged for review.

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

- When will the new runs be ready, and will the L and X groups keep their ids and definitions?
- Will `model_output` store the same variables (we need the mapped ones at minimum)?
- Who retrains the XGBoost on the new run?
