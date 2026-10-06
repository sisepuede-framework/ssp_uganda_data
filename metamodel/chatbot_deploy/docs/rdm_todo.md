# RDM agent redesign — to-do list

*Build order: `rdm_build_plan.md` (phases 0–5, run manifest so new runs only change paths).*

*Branch `rdm-tools`. Started 2026-09-30. Draft due before DMDU, 9 November 2026.
Companion to `rdm_tools_design.md`. Tick items as they land.*

Legend: **[blocked: new run]** = needs the new SISEPUEDE run that stores intermediate
variables; everything else can start now with the current surrogate and data.

---

## 0. Data foundations (Athena)

**★ Priority — the (L, X) → outputs object (core of the agent's infrastructure)**

The experiment's data is, for every pair (L_i, X_j): how **every** emission and **every**
variable in `model_output` that L_i moves responds as L_i and X_j vary, with all other L and X
still varying in the background. Only L and X are on the 0–1 scale; emissions and variables
stay in their original units (Mt CO₂e, PJ, ha, vehicle-km, …). No pre-selection of "the one
that moves most": everything is stored, and only the tool's reply is filtered.

- [ ] **Update the lever → output mapping** so every lever has its full list of emissions and
      variables in `model_output`. Today (2026-10-06): 35 levers have both, 7 emissions only,
      2 variables only (28, 32), 10 none (1, 5, 6, 7, 8, 17, 18, 38, 50, 51). Fill the gaps
      from the runs (empirical response) and from SISEPUEDE (structural).
- [ ] Map the X groups to the outputs they move too (the structural map covers levers only).
- [ ] Review spreadsheet for Alexa: every lever and X with the outputs it moves, kind, units,
      source (structural / empirical), and the gaps. Draft: `docs/lever_x_output_mapping.xlsx`.
- [ ] One store, not hundreds of tables: a run-level Parquet table (primary_id, the 67 L/X
      values, year, mapped outputs) queried by the tools; bins (e.g. 5 × 5) and summaries
      (median, p10–p90, n) computed on request or cached in one long table
      (lever, x, L_bin, X_bin, year, variable, value stats).

**Lever definitions and structural maps** (files in `metamodel/data/ssp/`):

- [ ] Validate how `VARIABLE_TRAJECTORY_GROUPS_L.csv` was generated (the run's own definition
      of the 54 L groups: group → transformation → input fields it sets, 547 rows). It is the
      source for "which transformation is each lever" and "which inputs it sets", and for
      Object 1. *(Alexa)*
- [ ] Document `transformation_output_variable_map.csv`: extracted by Alexa from SISEPUEDE
      itself; transformation → output variables it affects (5,333 rows, incl. 2,046 emission
      fields and intermediate variables). Structural: says *which* outputs, not *how much*.
- [ ] Join the output map to the levers by transformation code, stripping the run's
      `_STRATEGY_NZ` / `_NZ` suffix. Coverage today: 43 of 54 levers fully covered; group 15
      only partly (1 of its 3 transformations); 10 levers absent (CH4 rice, grid losses, clean
      hydrogen, renewable target, leaks, secondary forests max, wetlands minimum, powered bikes,
      waste capture biogas, waste energy from biogas). Find out why (e.g. the NemoMod
      electricity model not being traceable this way).
- [ ] Check why some covered levers list intermediate variables but no emission fields.
- [ ] Combine: *which* from the structural map where it exists; *how much* and *with which X*
      from the runs (below); fill the 11 uncovered levers from the runs alone. Report where
      the two disagree (structurally linked but empirically flat; moved but not listed =
      indirect coupling).
- [ ] Use the output map's intermediate variables as the starting list of candidate tangible
      and mechanism variables per lever.
- [ ] Prefer `VARIABLE_TRAJECTORY_GROUPS_L.csv` over `transformation_variable_map.csv` for
      inputs: the latter is generic (150 transformations, incl. NDC/LEP variants) and differs
      from the run (e.g. group 11: 186 vs 206 fields).

**Run data:**

- [x] Renew the AWS SSO session (`aws sso login --profile alexa`).
- [x] Read the CSV headers of `model_output`, `decomposed_emissions` and `cb` (free) and list
      what the current run actually stores beyond emissions.
- [x] Measure each table's size in S3 and estimate the one-off Parquet conversion cost.

  *Findings (2026-10-06), run `2026-05-30t21;35;56.244639`, 747 CSV files per table, all 56
  time periods (0–55):*

  | Table | Size | Columns | Content |
  |---|---|---|---|
  | `model_output` | 110.8 GB | 1,678 | 638 `emission_co2e_*` + **~1,028 intermediate variables** (energy demand 167, land-use area 160, energy consumption 121, NemoMod 76, waste 67, vehicle distance 54, fuel values 51, wastewater 47, crops/livestock/IPPU, …) |
  | `decomposed_emissions` | 35.3 GB | 654 | 638 `emission_co2e_*`, 12 `emission_nongas_*`, `total_emissions`, ids |
  | `cb` | 1.8 GB | 21 | 19 cost/benefit fields + ids |

  **All 493 intermediate variables and all 244 emission fields listed in
  `transformation_output_variable_map.csv` are already in `model_output`.** The current run
  very likely makes the "new run" unnecessary for the mechanism/tangible variables. Still to
  confirm: whether `model_output` intermediates are final (it holds *pre*-post-processing
  emissions, but intermediates should be unaffected).
  Cost: Athena bills $5/TB scanned, so one full scan of `model_output` ≈ $0.55, of
  `decomposed_emissions` ≈ $0.18. A one-off CTAS to Parquet of both is ≈ $1, and later
  column-pruned queries cost cents.
- [ ] Convert `decomposed_emissions` (6 target years) to Parquet with CTAS; register the
      per-run L/X sample table (100k × 67) in Glue.
- [ ] Lever → granular-emission map from real runs (~620 `emission_co2e_*` fields): effect
      (top vs bottom lever quintile, everything else varying), variance share, "impacted" rule
      identical to the surrogate map's.
- [ ] Fidelity check: aggregate that map to the 23 categories and compare with
      `lever_response_map.json` (the XGBoost version).
- [ ] Reusable Athena helper (`query(sql) → DataFrame`, prints bytes scanned and cost) plus a
      short how-to guide with example queries.
- [ ] Curate, per lever, the headline tangible variable and the mechanism variables. This list
      also tells the new run what it must store at minimum.
- [ ] Ask that the new run store the full `model_output` (or at least the curated list), in
      Parquet if the pipeline allows.
- [ ] **[was blocked: new run — likely unblocked, see findings above]** Re-run the mapping with intermediate variables; build the
      Li × Xj → tangible-variable tables (the 4-D object).

## 1. Question bank

*Draft v0 of the charter, sub-types, 20 questions and expert instrument:
`decision_charter_and_question_bank.md` (2026-10-06). Boxes below stay open until Alexa
signs off.*

- [ ] Decision charter (one page): decision maker, L, X, M, and the default success criterion
      (e.g. share of futures meeting an emissions threshold in 2050). Every C and D question
      needs it.
- [ ] Draft 15–20 questions covering categories A–F and the magnitude sub-types (tangible
      variable available / not available, sector target, total target, infeasible, constraint,
      side effect, dead lever, target year, L/X trap, ambiguous).
- [ ] Pair some questions: the same policy intent in lever terms and in tangible terms.
- [ ] For each question, fix in advance: category, expected tool sequence, referent (expert,
      surrogate ensemble, SISEPUEDE run) and success rule.
- [ ] Expert instrument: lever selection, sectors, direction, which X should be sampled,
      under-specification. Send to both experts.
- [ ] Freeze the bank (target: 10–12 questions for the full run).

## 2. Build the tools (new AI system)

- [ ] Write the input/output schema and the description of each of the 10 tools.
- [ ] Shared machinery: ensemble generator (all 13 X sampled, conditioned ranges, fixed seed),
      stored ensembles by id, paired BAU on the same futures.
- [ ] `define_experiment` + `run_experiment` (replace `run_simulation`).
- [ ] `find_vulnerabilities` (CART over the 13 X, X₁ × X₂ map, share left to the other X).
- [ ] `compare_policies` (robustness, costs, benefits, regret, dominance).
- [ ] Tool set v1 (2026-10-06, `rdm_tools_design.md`): one tool = one capability. 12 tools:
      `declare_plan`; `search_catalog`; knowledge `get_lever_effects`, `get_output_drivers`,
      `solve_lever_level`, `explain_failure` (replace `query_map`, `translate_target`,
      `mechanism_evidence`); experimentation `define_experiment`, `run_experiment`,
      `find_vulnerabilities`, `compare_policies`, `search_policy`; `get_country_context`.
      `get_pathway_results` removed.
- [ ] Knowledge tools as structured queries over the run-level table; the agent never writes
      SQL (free Athena queries = future work).
- [ ] Descriptions state each tool's boundary (solve_lever_level = one lever from data vs
      search_policy = combinations with XGBoost; define frames vs run computes).
- [ ] `search_policy` (choose and document the search method).
- [ ] Harness (no orchestrator choosing tools): state store for experiments and ensembles;
      rules checked in code (confirmation before run, no X fixed at one value, criterion for
      C/D, levers in [0, 1], `declare_plan` first); per-turn log; same limits in v0 and v1.
- [ ] Version switch v0 / v1 (placebo design): the four knowledge tools are present in **both**
      versions with identical name, schema and description; v0 returns names only (which
      emissions and variables move), v1 returns their values across L_i and X_j.
- [ ] Structured final answer that records the question category (needed for A and F).
- [ ] Logging per turn: category, tool sequence, arguments, returns, "why" claims.
- [ ] Raise `max_iterations` to fit the longest flow (C); same value in v0 and v1.

## 3. Test that everything works

- [ ] Unit tests per tool: fixed seed gives identical ensembles; conditioned X stays in range;
      paired BAU uses the same futures; schema validation rejects bad input.
- [ ] One scripted run per category flow (A–F), checking the tool sequence end to end.
- [ ] Simulated user with a fixed reply at the confirmation step, so runs are automatic.
- [ ] Pilot: 2–3 questions × 3 repetitions.
- [ ] Stochasticity gate: if within-question variance beats the v0–v1 difference,
      add repetitions or cut questions before the full run.

## 4. Review the tools in detail

- [ ] Check each tool against the five principles (ensemble only, L decided / X sampled,
      focus = shown, one source per tool, declare before run).
- [ ] Payload sizes fit a tool response; descriptions are neutral and leak no answer.
- [ ] Merge decisions from pilot usage: `define_experiment` + `run_experiment`;
      `run_experiment` + `compare_policies`.
- [ ] Code review of the branch before freezing.
- [ ] Walk the team's expert through the flows; settle the pending value for unvaried X.

## 5. Clean up `agent.py` so nothing is duplicated and the experiment is not biased

Rule: **every fact lives in exactly one place.** Either in the system prompt (identical in v0
and v1) or in a tool payload (the treatment), never both.

- [ ] **Write the prompt from scratch** (decided 2026-10-06), identical in v0 and v1: role, RDM
      method, data schema, and the L/X mapping (which emissions and variables each lever moves,
      without values). It must not mention any capability that exists in only one version (no
      "you can query the data" in v0), and must carry no lever-effect information.
- [ ] Use the old prompt only as a checklist: keep / move into a tool / remove.
- [ ] Known items to resolve:
  - Sector notes that say which levers cut which sector (e.g. biomass booked as forest-land
    removals and the levers that reduce it). That is lever → impact information, which is the
    treatment: it belongs to the knowledge tools (v1 payload); drop it from the prompt.
  - Lever scale guidance ("0.9–1.0 = maximum ambition") and any wording → value table.
    Magnitude information: it belongs to v1 (tool payload), so remove it from the prompt.
  - Request triage and method text that name `run_simulation` / `get_scenario_variables`:
    rewrite for the new tools and the A–F categories.
  - The rule on "when you may move an X": replace with principle 2 (X sampled, conditioned only
    on request).
  - Lever 15 is registered as "Reduce DEFORESTATION" but bundles three transformations
    (deforestation, wetland loss, reforestation). Fix its name and description in the
    registry so the agent knows what it moves (applies to v0 and v1, not a treatment).
- [ ] Diff the prompt against the v1 payload and confirm there is no overlap.
- [ ] Freeze the prompt with the tools (same commit).

## 6. Experiment design updates (needed before the freeze)

- [x] Research question, versions and hypotheses: two versions, v0 (structure only) and v1
      (structure and responses), placebo knowledge tool; written in `study_plan.md` §2
      (2026-10-06). The four-condition C0–C3 design is superseded.
- [x] Update `study_plan.md` to the new design (2026-10-06).
- [x] `explain_failure` follows the placebo rule like the other knowledge tools (v0 names,
      v1 values) — proposed 2026-10-06, confirm.
- [ ] Declare in the paper: v1 reads real runs while policies are evaluated with the XGBoost;
      state the referent for each scored dimension and report disagreements.
- [ ] Pre-register the hypotheses (v1 vs v0, with direction) and the manipulation checks.
- [ ] Freeze: commit, model hash, prompt, tools, question bank. Then the full run.
