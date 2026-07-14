# Tests — chatbot_deploy

Integration tests for the backend services. They exercise real local CSV data
and (for some tests) live S3, so they are integration tests, not pure unit tests.

## Running

All commands run from `metamodel/chatbot_deploy/` in the `uganda_metamodel_env` conda env.

**Standalone runner (recommended — no extra deps):**

```bash
conda run -n uganda_metamodel_env python -m tests.test_s3_lookup
```

Prints a PASS/SKIP/FAIL block per test and exits non-zero if anything fails.

**With pytest (optional):**

```bash
conda run -n uganda_metamodel_env python -m pytest tests/test_s3_lookup.py -v
```

`pytest` is **not** in `requirements.txt` (it is a dev-only tool, not needed to
run the server). Install it into the env first if you want this path:

```bash
conda run -n uganda_metamodel_env pip install pytest
```

The `*_pytest` wrappers in the test module import `pytest` lazily, so the
standalone runner works whether or not pytest is installed. No `conftest.py` is
needed — each test file puts the package root on `sys.path` itself.

## S3-dependent tests

Tests that read `model_input` / `model_output` rows need AWS access. The `.env`
sets `AWS_PROFILE=alexa` (SSO). If the SSO token is expired, those tests **skip
with a clear message** rather than fail. To enable them:

```bash
aws sso login --profile alexa
```

## `test_s3_lookup.py`

| Test | Needs S3 | Checks |
|------|----------|--------|
| 1 — `find_nearest_lhs_trial` | no | Nearest trial for `{8: 0.8}` at `design_id=4` lands within 0.15 of 0.8. |
| 2 — `get_model_inputs_row` | yes | Row 0 has >100 keys and `gdp_mmm_usd` is present. |
| 3 — `get_scenario_variable_trajectories` | yes | Contract of the scenario-variable engine: every requested group resolves to ≥1 input driver (VTL fallback); group 8 (LEAKS) has no mapped outputs, group 30 (SCOE) does; each record is `{field, name, by_year, pct_change}` with `by_year` keys a subset of the anchor years; both lists honor `top_n`. |

`design_id=4` is the L-and-X scenario design the 2026-05-30 run ships; the older
`design_id=3` no longer exists, so the test pins the id to the `_SCENARIO_DESIGN_ID`
module-aligned constant instead of hardcoding.

## `test_pathways_lookup.py`

Locks the contract of the real-pre-run pathways service (`pathways_lookup.py`) and
its agent wiring. **No S3 and no `ANTHROPIC_API_KEY`** — every test runs against the
*local* curated CSVs. If those CSVs are not present locally (fresh checkout with only
the S3 copies), the data-dependent tests **skip** rather than fail.

| Test | Needs data | Checks |
|------|-----------|--------|
| 1 — `resolve_pathway` | no (pure registry) | All 6 registry names + numeric `primary_id`s round-trip; aliases resolve case/whitespace-insensitively; an unknown name raises `LookupError` listing the valid pathways. |
| 2 — reader contract | local CSVs | The reason the module exists: real HBLE @2070 ≈ **6.35** (not the surrogate's ~115) and BAU far higher; emission trajectories carry only the anchor years; BAU cost-benefit is identically zero with GDP still populated; NDC 2.5 cost keys are exactly `{technical, system, fuel}` (exact membership — `technical_savings` stays a benefit); `indoor_air_pollution` is surfaced as a benefit. |
| 3 — `get_pathway_results` handler | local CSVs | Driving `agent._execute_tool_call` (no LLM) for "NDC 2.5" returns a payload that validates against `SimulationResponse`, is flagged `data_source="real_run"`, carries real BAU+HBLE references on both chart bundles, attaches real driver detail for `groups_changed=[4]`, and returns an `{"error": ...}` dict (not an exception) for an unknown pathway. |
| 4 — `_attach_real_references` | local CSVs | The shared injector adds real BAU+HBLE references to a surrogate-shaped result's chart bundles without mutating the surrogate scenario, and is a safe no-op on a result with no chart bundles. |
| 5 — `compare_series` (surrogate-like) | local CSVs | The shared delta helper, fed a surrogate-shaped scenario with an OFF-anchor year, keys `sector_deltas` by the fixed anchor years only (drops the stray year), carries the real BAU value in each delta, and computes a ≈-50% headline when the scenario is half of BAU. |
| 6 — `run_simulation` rewire | local CSVs | Drives `agent._execute_tool_call("run_simulation", …)` with a fake predictor: the throwaway surrogate baseline is replaced by the **real BAU** run (@2070=277.59), the summary carries `bau_value` + `hble_value` + `change_from_bau_pct`, real BAU+HBLE references are on both chart bundles, and the payload is `SimulationResponse`-valid. |
| 7 — process trace | local CSVs | `agent._build_trace_event` produces `TraceStep`-valid provenance: a surrogate `run_simulation` step → `data_source="surrogate_xgboost"` noting the real BAU/HBLE comparison; a named pathway → `real_run`; a bad pathway → `status="error"` with the failure surfaced in `details`. |

Run: `python -m tests.test_pathways_lookup` (7/7 pass).

The live `/api/chat` LLM-routing check (does Claude actually pick `get_pathway_results`
over `run_simulation` when a pathway is named?) and the browser eyeball are **not** in
this file — they need the full runtime (API key + model env + browser). Test 3 covers
everything up to the LLM's tool choice: given the tool *is* chosen, the handler produces
a correct, schema-valid, real-run payload.
