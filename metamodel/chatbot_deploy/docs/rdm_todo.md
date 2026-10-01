# RDM agent redesign — to-do list

*Branch `rdm-tools`. Started 2026-09-30. Draft due before DMDU, 9 November 2026.
Companion to `rdm_tools_design.md`. Tick items as they land.*

Legend: **[blocked: new run]** = needs the new SISEPUEDE run that stores intermediate
variables; everything else can start now with the current surrogate and data.

---

## 0. Data foundations (Athena)

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

- [ ] Renew the AWS SSO session (`aws sso login --profile alexa`).
- [ ] Read the CSV headers of `model_output`, `decomposed_emissions` and `cb` (free) and list
      what the current run actually stores beyond emissions.
- [ ] Measure each table's size in S3 and estimate the one-off Parquet conversion cost.
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
- [ ] **[blocked: new run]** Re-run the mapping with intermediate variables; build the
      Li × Xj → tangible-variable tables (the 4-D object).

## 1. Question bank

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
- [ ] `query_map` on top of the response map (replaces `get_scenario_variables`).
- [ ] `search_policy` (choose and document the search method).
- [ ] **[blocked: new run]** `translate_target` and `mechanism_evidence`.
- [ ] Condition switch for the experiment: same tool signature in every arm, payload varies,
      tool absent in C0.
- [ ] Structured final answer that records the question category (needed for A and F).
- [ ] Logging per turn: category, tool sequence, arguments, returns, "why" claims.
- [ ] Raise `max_iterations` to fit the longest flow (C); same value in every arm.

## 3. Test that everything works

- [ ] Unit tests per tool: fixed seed gives identical ensembles; conditioned X stays in range;
      paired BAU uses the same futures; schema validation rejects bad input.
- [ ] One scripted run per category flow (A–F), checking the tool sequence end to end.
- [ ] Simulated user with a fixed reply at the confirmation step, so runs are automatic.
- [ ] Pilot: 2–3 questions × 3 repetitions.
- [ ] Stochasticity gate: if within-question variance beats between-condition differences,
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

Rule: **every fact lives in exactly one place.** Either in the system prompt (identical in every
condition) or in a tool payload (the treatment), never both.

- [ ] Audit the system prompt section by section: keep / move into a tool / remove.
- [ ] Known items to resolve:
  - Sector notes that say which levers cut which sector (e.g. biomass booked as forest-land
    removals and the levers that reduce it). That is lever → impact information, which is the
    treatment: move it into `query_map` or drop it.
  - Lever scale guidance ("0.9–1.0 = maximum ambition") and any wording → value table.
    Magnitude information: decide whether it is part of the baseline for every arm or removed.
  - Request triage and method text that name `run_simulation` / `get_scenario_variables`:
    rewrite for the new tools and the A–F categories.
  - The rule on "when you may move an X": replace with principle 2 (X sampled, conditioned only
    on request).
  - Lever 15 is registered as "Reduce DEFORESTATION" but bundles three transformations
    (deforestation, wetland loss, reforestation). Fix its name and description in the
    registry so the agent knows what it moves (applies to every condition, not a treatment).
- [ ] Diff the C0 prompt against each condition's payload and confirm there is no overlap.
- [ ] Freeze the prompt with the tools (same commit).

## 6. Experiment design updates (needed before the freeze)

- [ ] Define what `query_map` returns in each condition (C0 absent / C1 emissions / C2 +
      tangible variable / C3 + X axis), or the simplified contrast if we cut arms.
- [ ] Rewrite the hypotheses (the old triple dissociation no longer fits) and pre-register them.
- [ ] Update `study_plan.md` to the new design.
- [ ] Freeze: commit, model hash, prompt, tools, question bank. Then the full run.
