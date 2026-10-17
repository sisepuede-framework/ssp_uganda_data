# Information layer — plan and decisions log

*Branch `rdm-tools`. Started 2026-10-13. What the information tools show the agent, how that data
is built, and the experiment arms. Tool design: `rdm_tools_design.md`; first evaluation:
`rdm_tools_evaluation.md`. Update the log whenever a decision is made.*

## The idea in one paragraph

For each lever, the agent should see the chain **lever → inputs it sets → in-between variables →
emissions (by category)**, and how the chain looks when an uncertainty is low or high. The
relations are always shown; the values are what the experiment varies. The data is built once
per run by code (Athena where needed), saved as tables, and read by the tools.

---

## Road to the full experiment (consolidated 2026-10-14)

Everything still open before running the experiment with all the questions, in dependency order.
**A** = Alexa decides or reviews · **T** = the team or the experts · **C** = Claude builds.

**Open questions for Alexa (asked 2026-10-14, not yet answered)**
- Q10 / D2 fail the 50% test in every future (the policy cuts ≈ 5%): weaker threshold (e.g. 5% below BAU) or a stronger policy?
- Wait for the variables review before rebuilding the tables from the 100,000 runs (item 13)? (my proposal: yes)
- The range from BAU is shown only in the arms that show input values — right, or should v0 get the BAU end too?
- Update the slides and `study_plan.md` §2 (item 21) after the revisions? (my proposal: yes)

State on 2026-10-14: 39 RDM tests and the full suite (59) pass; four pilots done (Opus pilot 1, Sonnet pilots 2–4).

**Update 2026-10-16** (session log; resume here)
- **Surrogate retrained** (commit `38bf7da`): S3 `decomposed_emissions`/`cb` were re-uploaded 10-14/15, but
  only the subsector totals changed (biomass CO₂ moved entc → frst); the granular fields the crosswalk sums
  did not, so the training data was identical. Then: **z-score outlier filter removed** (it cut 24% of
  futures, all for their targets; ablation showed no gain); **3 blow-up runs dropped** (253003xx block);
  train/test split saved (`trained_models/split_<run>.csv`) and uploaded to
  `s3://sisepuede-data/queries/<run>/surrogate_split/`. Median R² 0.9937 (2035–2070, 19,918 untruncated
  test rows), 15 targets < 0.8 (fuel production, wetland services, deforestation 2070, other conversion).
  The filtered model is kept locally as `…_zfilter.pkl`. 39 RDM tests pass on the new model.
- **Consequence: the answer keys are stale** (`bank_reference.json`, `pairs_reference.json`,
  `scenario_reference.json`, `evaluate_tools.py`): recompute with the new surrogate; recheck Q10/D2.
- **Green flag from Alexa** on the current drivers, inputs, outputs and the 32 questions → item 9 closed
  as is; item 13 (rebuild from the 100k runs) unblocked; P14 not needed (no multi-lever T2 question).
- **Slides** (DMDU deck): new slide 9 "What the agent sees of the SISEPUEDE pipeline" (pipeline row
  levers → inputs → [SISEPUEDE: drivers + emissions] → categories; one row per tool; key message: the
  input → driver link is never given, it is SISEPUEDE), slide 10 "What each tool reads", slide 11 "How the
  variables in the chain were selected"; file paths in the speaker notes.
- **Open, proposed 10-16, not decided:** add the driver → sub-emission link to `lever_x_profile` (data in
  `links/<run>_drivers_by_source.csv`; ~1 h; makes the chain lever → drivers → sub-emissions → category
  explicit). Inputs → drivers stays "linked through the lever" (response graph = future work).
- **Next (C):** recompute answer keys → rebuild tables from the 100k runs (~$0.72) → commit all untracked
  RDM code + freeze (item 20) → smoke test (1 question × 4 arms) → full run.
- **Decisions waiting for Alexa, with my proposed defaults:** Q10/D2 threshold [5% below BAU]; arms [2 × 2];
  reps [3 → 384 conversations, ≈ $12–100]; scoring [routing automatic + reader model with hand check];
  scripted user [one "go ahead", then stop]; items 14/15 [freeze as is, open details as limitations];
  P10/P3 [leave as is]. Slide 10 still says `decomposed_emissions` for output_levers (rename to
  "SISEPUEDE emissions"?).

**1 · Questions** (`docs/question_bank_v1.md`)
1. A — Revise the 30 draft questions: wording, category, translation label (T0–T4), scripted replies; cut to the frozen size.
2. ✅ C — Answer keys computed (`backend/rdm/eval/bank_reference.py` → `bank_reference.json`); written into the bank. Q10/D2 fail the 50% test in every future — see the bank note.
3. ✅ C — Expected flows in `rdm_tools_design.md` rewritten by translation (T0–T4) + category step.

**2 · Information the agent sees**
4. ✅ C — P13: inputs now show `range_from_bau` (BAU = lever 0, maximum = lever 1, direction, per year) in the arms that show inputs.
5. A — P10: reply size of the largest levers (lever 11 sets 162 inputs): group inputs or leave.
6. A — P3: input years shown (2050 and 2070 now).
7. A — P2/P2b: crosswalk as a separate reference (on hold).
8. A — P14: several levers at once for in-between quantities (needed only if the bank keeps multi-lever T2 questions).

**3 · Data quality**
9. T — P4/P7: expert review of the drivers file (21 sources with no candidate; manure choices; 315 unlinked fuel-demand variables).
10. ✅ C — P6: rule exact for levers 35 and 34 via output proxies. Found 9 broken runs (one id block, light-duty vehicle-km ≈ 1): now dropped entirely by the store; drivers and values rebuilt (151 driver variables).
11. T — P8: cost-type signs; units for the remaining variables; real units for the 13 uncertainties (D questions need them).
12. T — P11: what `est_from_sisepuede = 0` means for "Other Land Use Conversion".
13. C — P5: rebuild the tables from all 100,000 runs (≈ $0.72 in Athena) — after the variables review (9), so the query selects the final variables.

**4 · Tools and harness**
14. A — Review every harness file by hand (prompt, tool descriptions, state, loop, tools per arm).
15. A — Open technical-tool details (design doc): threshold format; number of futures; value of an X not varied; which costs in trade_off_analysis; scenario_discovery variables (only the 13 X?); CART vs PRIM; single-run requests.
16. A — The scripted user: the neutral "go ahead" reply pushes some agents further (pilot 2); keep, change, or stop after one reply.

**5 · Experiment design and scoring**
17. A — P1: arms for the full run — 2 × 2 (v0, v1_inputs, v1_outputs, v1), as in pilots 3–4.
18. A — P12: how stated answers are scored (a reader model + a hand check, or by hand); plus the routing score against the expected flows.
19. A — Repetitions per question × arm (pilots used 3) and the budget (Sonnet 5.5: ≈ $0.03–0.27 per conversation).

**6 · Freeze and run**
20. C — Freeze: commit, model hash, prompt, tools, tables, question bank, manifest; then the full run and scoring.

**7 · Documents**
21. C — DMDU talk slides and `study_plan.md` §2 to the current design (D14–D19, the 2 × 2, the T labels).

## Decisions made

| # | Date | Decision | Why / evidence |
|---|---|---|---|
| D1 | 10-12 | 7 tools: 4 technical (surrogate), `lever_x_profile`, `output_levers`, `country_context` | `rdm_tools_design.md` v2 |
| D2 | 10-12 | Only the 505 crosswalk emission fields | the surrogate sees nothing else |
| D3 | 10-12 | No plan step; only final actions are measured, from the log | |
| D4 | 10-13 | GDP labelled "billion international $, PPP, constant prices". PPP vs market rate and the cost-share issue are known and left as is for now | World Bank: model growth = constant-price series; level ≈ PPP |
| D5 | 10-13 | Code queries Athena **once per run** to build tables; the tools read the tables, never Athena | cost, minutes per scan, AWS logins expire, reproducibility |
| D6 | 10-13 | Uncertainty shown as **low vs high X** (as in the current design) | X is sampled independently of L; it is an axis, not a lever property |
| D7 | 10-13 | Lever **input values** at **2050 and 2070** | user |
| D8 | 10-13 | "Important" in-between variables = variables linked to emissions by the **subsector-name rule**; reviewed by experts in a CSV; experts can add links | user; `backend/rdm/links/` |
| D9 | 10-13 | Emissions reported **by category** (the 23 the surrogate predicts) | user |
| D10 | 10-13 | **v0 is always relations only**, in every experiment | user |
| D12 | 10-13 | **Pilot first with two arms:** relations only (v0) vs relations + inputs + outputs. The 2 × 2 comes after, if the pilot shows an effect | cost and power; see P1 |
| D13 | 10-13 | The crosswalk goes **inside the replies**: each category the lever moves, with its fields under it, in every arm | it is a relation |
| D14 | 10-13 | In-between variables are chosen **per emission source inside each XGBoost category**: exact name → group (when the source adds up a fuel/crop/… dimension) → correlation; 1–2 per source; judged at the **last run year (2070)**; listed **once per category** (a variable may feed two categories) | `backend/rdm/links/drivers.py`; replaces the subsector list (D8) as what the tools show |
| D15 | 10-13 | Experiment model: **`claude-sonnet-5-5`** (effort medium), the same in every arm | newest and cheapest; resolves P9 |
| D16 | 10-13 | Keep the routing **nudge** in the prompt and tool descriptions ("use the information tools … before running anything", "exploratory_modeling, then …"), identical in every arm | user |
| D17 | 10-13 | **Pairs experiment, 2 × 2 arms** (v0, v1_inputs, v1_outputs, v1) × target kind: **input** target (a quantity the lever sets; answer exact) vs **output** target (an emission change it causes; answer from the surrogate, other levers at 0). Pairs on levers 35 (light-duty electric share / transport −5%), 50 (landfill gas recovered 40% / solid waste −10%), 12 (clinker share 65% / IPPU −6%). Scored by: committed to one level or bracketed; error vs reference; number of exploratory runs | `backend/rdm/eval/questions.py`, `pairs_reference.json` |
| D18 | 10-14 | **The mechanism the agent works by:** all the information we want can come from the input and output data (the runs), but **validation is only possible with the levers the XGBoost takes** (it reports emissions, costs, benefits, GDP). The agent looks for information in the available sources and tests whatever it can by running the XGBoost. Written into the system prompt (identical in every arm) | user |
| D19 | 10-14 | Translation 3 (scenario → in-between quantity) is answered and scored **from the runs as they are**: the lever at its maximum with the other levers as they varied in the runs (frame 1). No extra model | user: "that is the data we have"; no run has the other levers near BAU |
| D11 | 10-13 | Input values come from the rule **value(L) = BASE + L × (HBLE − BASE)**, not from model_input | verified exact on 291 fields × 4,989 runs; model_input lacks 236 of the 527 fields (30 levers) |

## How the run data reaches the tools (the primary-id route)

Filtering primary ids by strategy cannot isolate a transformation: all 100,000 runs are the HBLE strategy with every
lever at an LHC-drawn level. Instead, all runs are kept and grouped by each lever's level and each uncertainty's level:
primary_id → (design_id, future_id) → LHC values (`data/lhc.py`) → that run's outputs.

| Piece | Source | Athena |
|---|---|---|
| Lever input values | BASE + L × (HBLE − BASE) from the two pathway runs | none (one query, $0.73, proved the rule) |
| Drivers and category emissions | `model_output`, `decomposed_emissions` for the sampled primary ids | once per run, cached; tools read files |
| Full 100k for the freeze (P5) | same, all primary ids; categories summed inside the query, only the 153 drivers selected | ≈ $0.55 + $0.17, once |

## Decisions pending

**Alexa's review task:** read every harness file by hand and check it matches what you expect —
`backend/rdm/harness/prompt.py` (what the agent is told), `registry.py` (the 7 tool descriptions and how calls run),
`state.py` (ensembles and labels), `agent.py` (the loop and the scripted user), plus `backend/rdm/tools/` (what each tool
returns in each arm).

| # | Question | Options | My recommendation | Blocks |
|---|---|---|---|---|
| P1 | After the pilot: run the full 2 × 2 (R, R+I, R+O, R+I+O)? | | decide on the pilot's results | |
| P2 | Beyond the replies, can the agent consult the crosswalk on its own? Not in the prompt (user). | (a) a reference tool that serves static tables (crosswalk now; units, lever catalogue later); (b) a crosswalk-only tool; (c) nothing beyond the replies | (a) | the tool list, the prompt's instructions |
| P3 | Input year | 2050, 2070, or both | both until the pilot shows size; then the target year of the question | reply size |
| P4 | Experts' review of the drivers | — | send `links/<run>_drivers_by_category.csv` (179 rows, 153 variables) and `…_drivers_by_source.csv`; ask first about the 21 sources with no candidate (forest methane and sequestration, crop residues, biomass burning) and the manure-management choices | final list of in-between variables |
| P5 | Sample (4,989 runs) or full 100,000 for the frozen tables | | full before the freeze; sample to develop | Athena cost (~1 scan per table) |
| P6 | Validate the input rule for the 30 levers not in model_input | trust the mechanism / spot-check from model_output proxies | spot-check 3–4 levers via output proxies (e.g. vkm by fuel) | confidence in the input values |
| P7 | Fuel-demand variables the rule misses (315 unlinked, mostly energy demand by fuel) | expert additions / a second rule (same sector, any fuel → that sector's combustion emissions) | ask the experts first | completeness of the in-between |
| P10 | Reply size of the largest levers. With the drivers (D14): median v0 2.3k / v1 4.9k characters; max 25k / 55k — lever 11 (Shift FUEL HEAT) sets 162 input fields | group the inputs of large levers; leave as is | look at the Sonnet pilot first | context use, arm comparability |
| P13 | **The range each lever can move, measured from BAU**, saved as information for the agent: for every quantity a lever sets (and its key in-between variables), the BAU value (lever at 0) and the reachable range up to maximum ambition (lever at 1), per year — so the agent can say "BAU already has 50% electric light-duty travel in 2050; the lever can take it to 72%; a 45% target needs no extra action". The input table already holds both ends (`tables/<run>_lever_inputs.csv`: at_0, at_1) | which arms see it (it is a value: v1 only?); where it lives (inside `lever_x_profile`, or its own table the agent can consult) | | translation of targets below BAU or beyond maximum |
| P14 | Translation 3 for **several levers at once** (scenario → in-between quantity): (a) look up the nearby runs among the 100,000; (b) a small model per in-between variable trained on the runs | (a) for a few chosen variables first | | multi-lever questions like "how much electric travel in this package?" |
| P11 | "Other Land Use Conversion" is marked `est_from_sisepuede = 0` in the team's crosswalk, and it is one of the surrogate's weakest targets (R² 0.66 in 2070) | ask the team what the flag means | | trust in that category |
| P2b | Crosswalk as a separate reference (tool) | on hold until the pilot shows whether it is needed | — | — |
| P8 | From the first evaluation | cost-type signs; units for the remaining variables; real units for the 13 X | | trade-off numbers; v1 readability |

---

## Steps

| # | Step | State |
|---|---|---|
| S1 | Register `model_input` in Athena; query the lever inputs for the sample (`backend/rdm/data/inputs.py`) | ✅ 10-13 — 145 GB scanned, $0.73; 291 of 527 fields exist |
| S2 | Test the input rule (`tests/rdm/test_inputs.py`) | ✅ exact on all 512 changing field-years |
| S3 | Lever input table (`backend/rdm/data/lever_inputs.py` → `tables/<run>_lever_inputs.csv`) | ✅ 527 fields × 2 years |
| S4 | Variable → emission links by subsector (`backend/rdm/links/subsector.py`) | ✅ draft: 1,205 variable–category rows for review, 315 unlinked |
| S5 | Expert review of S4 (P4, P7) | to do |
| S6 | Values table (`backend/rdm/data/values.py` → `tables/<run>_values.parquet`): lever × year × X bin × lever level → whole-category emissions and in-between variables | ✅ 10-13 — 737,748 rows from the sample; every cell ≥ 475 runs |
| S7 | `lever_x_profile` reads the input table, the values table and the links; arms v0 / v1 / v1_inputs / v1_outputs | ✅ 39 tests pass |
| S8 | Reply size per arm (lever_x_profile, uncertainty = GDP, 2050) | ✅ median v0 4.5k / v1 12k characters; max v0 35k / v1 84k (levers 11, 15, 25) |
| S9 | System prompt (`harness/prompt.py`, identical in every arm) + agent loop (`harness/agent.py`) + pilot runner and summary (`eval/run_pilot.py`, `eval/summarize_pilot.py`) | ✅ built; pilot Q04b, Q10, Q14 × v0, v1 × 3 reps |

---

## Pilot 1 — 2026-10-13 (claude-opus-5-5, effort medium; Q04b, Q10, Q14 × v0, v1 × 3 reps; $4.73)

Runs: `backend/rdm/eval/pilot_runs/`; table: `pilot_runs/summary.csv` (`python -m backend.rdm.eval.summarize_pilot`).

- **Q04b ("60% of light-duty vehicle-km electric by 2050") — a clear effect of the inputs.** v1: 3 of 3 translated
  60% into lever 35 at 0.45–0.46 (correct: 50% + L × 21.9 points = 60% → L ≈ 0.46). v0: 3 of 3 could not translate and
  bracketed with 0.5 / 0.75 / 1.0.
- **Q10 (robustness) — not measured: harness bug.** All 6 agents ran the policy and asked the user for a failure
  threshold, but the scripted user only replied to answers ending in "?". Fixed; Q10 must be rerun.
- **Q14 (compare) — same policies in every run** (transport levers 35, 37, 38, 39 vs deforestation 15). v1 information
  replies were 93–100k characters (lever 15 is one of the three largest; P10), making those runs the most expensive
  (≈ $0.70). One v1 run used no information tool at all.
- `output_levers` rejected the metric name `emissions_transportation` (2 runs; the agent recovered). Fixed: both forms accepted.
- Cost: v0 ≈ $0.28, v1 ≈ $0.24 per conversation; 17–59 s each.

## Pilot 2 — 2026-10-13 (claude-sonnet-5-5, effort medium; drivers as in-between; fixes applied; $1.20)

Runs: `backend/rdm/eval/pilot_runs/claude-sonnet-5-5/`; table: `summary.csv` there.

- **Q04b — the same effect as with Opus.** v1: 3 of 3 set lever 35 at 0.46 (correct). v0: 3 of 3 bracketed (0.5 / 0.75 / 1.0
  or 0.5 / 0.6 / 0.8). Across both pilots: 6 of 6 vs 0 of 6.
- **Q10 — now complete.** All 6 asked for the threshold and used it (50% below BAU in 2050). Depth varied: 3 stopped after
  vulnerability_analysis; 3 built broader packages and re-tested (one ran scenario_discovery). Part of this comes from the
  scripted "go ahead" reply. Only one run (v0) called an information tool.
- **Q14 — Sonnet skips both information tools and trade_off_analysis.** 5 of 6 runs made a single exploratory_modeling call
  with both policies and compared the results themselves (answers were sound: trade-off by year, no winner named).
  Opus called trade_off_analysis in 6 of 6.
- Information tools were used in 0 of 6 v1 runs for Q10 and Q14: the treatment can only act when the tool is called
  (total effect = P(call) × effect given the call).
- Cost per conversation $0.03–0.27; 13–49 s.

## Pilot 3 — pairs, 2 × 2 arms — 2026-10-13 (claude-sonnet-5-5; 6 questions × 4 arms × 3 reps = 72 runs; $2.47)

Runs: `backend/rdm/eval/pilot_runs/claude-sonnet-5-5/pairs/`; reference answers: `backend/rdm/eval/pairs_reference.json`.

**Input targets** (60% electric / 40% landfill gas recovered / 65% clinker):

| | v0 | v1_inputs | v1_outputs | v1 |
|---|---|---|---|---|
| committed to one level | 38% | 100% | 50% | 100% |
| mean error of that level | 0.15 | 0.008 | 0.15 | 0.003 |

- With the inputs, all 18 runs landed on the reference (0.45–0.46, 0.58, 0.69).
- Without them, the agent often **took the target number as the lever level**: "40% recovered" → 0.4 (reference 0.69);
  "60% electric" → 0.6 (reference 0.46). Otherwise it bracketed (0.5 / 0.75 / 1).
- The outputs alone did not help with input targets (same as v0).

**Output targets** (transport −5% / solid waste −10% / IPPU −6%): in every arm the agent swept the lever in one
exploratory_modeling call (e.g. 0.25 / 0.5 / 0.75 / 1) and interpolated the answer in its text ("55–60% of maximum";
reference 0.54). The information tools are not needed for these: the experiment answers the question. Scoring these
needs the level stated in the text (pending: P12).

| P12 | Score the output targets: read the level each answer states | (a) a small reader model (Claude Haiku 5.5) + a hand check of ~10 answers; (b) read the 36 answers by hand | (a) | the output half of pilot 3 |

## Pilot 4 — translation 3, scenario → in-between quantity — 2026-10-14 (claude-sonnet-5-5; new prompt paragraph D18; 3 questions × 4 arms × 3 reps = 36 runs; $1.05)

Runs: `backend/rdm/eval/pilot_runs/claude-sonnet-5-5/scenario/`; answer key from the runs only: `backend/rdm/eval/scenario_reference.json`.

| Question (lever at maximum, 2050) | v0 | v1_inputs | v1_outputs | v1 | Answer key (runs, lever ≥ 0.9) |
|---|---|---|---|---|---|
| S35 electric light-duty travel | no number 3/3 | no number 3/3 | 22.6–23 billion vkm 2/3 | 22.6 billion vkm 3/3 | 24 billion (19–30) |
| S50 landfill gas recovered | no number 3/3 | no number 3/3 | 706,000 t 3/3 | 706,000 t 3/3 | 800,000 t (190,000–1.5 M) |
| S3 improved cropland | no number 3/3 | 3.7 M ha 1/3 (own estimate) | 2.6 M ha 2/3 | 2.6 M ha 3/3 | 3.0 M ha (2.7–3.3) |

- Answers come only where output values are shown, and sit close to the key (the reply's "high" level is 0.67–1; the key is ≥ 0.9).
- Without them, agents said the quantity is not available and cannot be tested on the surrogate, then tested what they could
  (the emissions change) — the D18 mechanism. One v1_inputs run built its own estimate (no-till shares from the inputs × crop
  areas from country_context = 3.7 M ha) and labelled it "not a model output".
- Together with pilot 3: **inputs translate input targets; outputs translate in-between quantities; emission targets are
  reached by testing on the surrogate in every arm.**
