# The SISEPUEDE network — plan and rules

*Started 2026-10-20. Goal agreed with Alexa: a network of the variables involved from lever to emissions, read from
the SISEPUEDE code, so the agent (and the user) can see how the model is wired. Relations, not causality, not
magnitudes. No new experiment runs: the values on the network come from the runs already in AWS.*

## What the network is

```
lever ──sets──► input field ──► … in-between variables … ──► emission field ──► XGBoost category
 (54)            (527, AWS model_input)   (AWS model_output)       (AWS decomposed_emissions)   (23, crosswalk)
```

- **Node = one SISEPUEDE model variable** (e.g. "Vehicle Distance Traveled"), holding its fields (one per category,
  e.g. per fuel) as they appear in AWS. Ranges are per field.
- **Edge = "variable A is used to compute variable B"** inside SISEPUEDE.
- Node attributes, from SISEPUEDE's `variable_definitions_*.csv`: full name, input or output, unit, gas (if any),
  categories, subsector, sector. Emission nodes also carry their XGBoost category.

## Rules (I follow these at every step)

1. **Relations only.** An edge says that a variable is used to compute another. No direction of effect, no size, no
   causal claim from the code.
2. **One source of code:** SISEPUEDE 1.4.0 installed in the `ssp_uganda_env` conda environment. Every edge keeps
   its provenance (model, function).
3. **Code and runs stay separate.** Edges come only from the code. The runs (mapping, correlations) are used only to
   *test* the network, never to add an edge. Name matching never adds an edge.
4. **Every node must have data in AWS** (model_input, model_output or decomposed_emissions of run 2026-05-30), so its
   range can be shown. A variable with no data (emission factors, parameters) may stay only as a pass-through
   connector, flagged `in_aws = false`, and can be hidden.
5. **Black boxes are explicit.** The electricity optimisation (NemoMod, in Julia) becomes one node with its
   inputs and outputs, never hidden or guessed inside.
6. **Do not touch** the SISEPUEDE package or the experiment code (`tools/`, `harness/`, `eval/`) while building the
   network. New code goes to `backend/rdm/network/`, one script per step, outputs as CSV.
7. **Each step ends with a number written in the log below.** If a test fails its threshold, stop and report before
   going on.
8. **No AWS spending without asking.** Ranges use the local sample (4,989 runs) until Alexa approves the 100k query.
9. **English** in code and docs.

## Steps

| # | Step | Output | Check |
|---|---|---|---|
| 1 | **Inventory.** Every model variable from `variable_definitions_*.csv` with its attributes; expanded to fields; joined to the AWS columns. | `network/<run>_variables.csv`, `<run>_fields.csv` | Share of AWS columns that map to a model variable (target ≥ 95%). |
| 2 | **Trace the data flow.** Run SISEPUEDE once on the Uganda base input with tagged arrays: every array read with `extract_model_variable` carries the name of its variable; operations merge the tags; every `array_to_df` records "tags → variable written". | `<run>_edges_traced.csv` (from, to, model, function) | Every output variable written by the run has ≥ 1 incoming edge. |
| 3 | **Fill the gaps from the code.** Where tags are lost (lists, pandas, loops, Julia), read the function (AST): variables read and written in the same function. Flagged `source = static`. | `<run>_edges_static.csv` | Count of edges by source. |
| 4 | **Assemble.** Lever → input (`VARIABLE_TRAJECTORY_GROUPS_L.csv`), the traced and static edges, emission field → category (crosswalk), NemoMod as one node. | `<run>_network.json` | No orphan nodes among AWS variables (target: 0, or listed). |
| 5 | **Test against the runs.** For each of the 4,805 lever → output links seen in the runs: is there a path lever → … → output in the network? | test report in the log | ≥ 90% of empirical links explained; the misses listed by sector. |
| 6 | **Spot check by hand.** 10 chains (L35 electric light duty, L50 landfill gas, L15 deforestation, L27 cooking energy, L3 conservation tillage …). | notes in the log | Each chain reads right to someone who knows the model. |

Only after step 5 passes: node ranges by lever level and by each X low / high (layers 1–2 of the X design), the
viewer with the lever + X filter, then the agent's tool.

## Log

- 2026-10-20 — plan written.
- 2026-10-20 — **Step 1 passed.** The full model_input header (2,444 columns) was saved from S3 (AWS_PROFILE=alexa)
  to `out/run_2026_05_30_model_input_header.txt`. Coverage: model_input 2,441 of 2,441 columns map to a model
  variable (100%), model_output 1,025 of 1,025 (100%), decomposed_emissions 623 of 638 (97.6%; the 15 misses are
  `emission_co2e_subsector_total_*` aggregates). 714 model variables, 711 with a field in AWS.
- 2026-10-20 — **Step 2, first passes.** Input: `data_processing/transformations/input_data_uganda_base.csv`
  (older than 1.4.0: 7 input fields missing, set to their default 0; values do not matter for relations).
  Fixes needed for tags to survive: arrays created with `np.zeros` and filled by item (patched only for calls from
  `sisepuede/models/`, pandas breaks otherwise); `zeros_like` and similar copy only a shape and add no tag; two
  Circular Economy functions check `type(x) == np.ndarray` and get plain arrays; every ModelAttributes helper
  keeps the tags of the arrays it receives (`merge_array_var_partial_cat_to_array_all_cats` was dropping the
  transport fuel fractions). Without electricity: 209 variables written, 14 with no incoming edge (to fill in
  step 3). Spot check: Vehicle Distance Traveled from Electricity ← fuel fraction electricity, mode shares,
  occupancy, freight load, passenger-km and tonne-km demand (correct); CH₄ from manure ← manure management
  fractions, volatile solids, methane correction factor, biogas recovery, animal weight, livestock demand drivers
  (correct). Electricity (NemoMod) needs the reference tables from the local SISEPUEDE repository
  (`sisepuede/ref/nemo_mod`, not shipped in the 1.4.0 package).
- 2026-10-20 — **Steps 2–5, test passed: 93.9%** of the run links (4,290 of 4,568) have a path in the network
  (structural links 96.6%, links seen in both 94.3%, empirical only 93.5%; levers → emissions 97.8%). The run
  includes electricity (NemoMod solved every year with HiGHS, ~40 s). Network: 804 nodes, 4,379 edges (4,137
  computes, 152 sets, 90 sums_to). How the score went up, each fix in `trace.py`: first pass 36% → electricity
  41% → arrays created in utilities, DataFrame column reads 44% → land use adjustment, in-place writes (np.put),
  single elements 52% → GDP growth rates handed between models in an internal frame 58% → the integrated land
  use loop as one step 65% → AFOLU's own writer for conversion areas, NemoMod declared inputs, subsector totals
  out of the test 75% → every output of the electricity model out of NemoMod 79% → declared NemoMod outputs 94%.
  - **Rules added while building:** functions treated as one step (everything in relates to everything out):
    `CircularEconomy.fod`, `get_waso_historical_solid_waste` (strict type checks), `AFOLU.qadj_adjust_transitions`
    (a solver), `AFOLU.project_integrated_land_use` (land use, crops, livestock and pasture coupled each period).
    NemoMod is one node: in = every variable its wrapper reads + every input of Energy Technology, Storage and
    Fuels; out = every variable its wrapper writes + every output of those subsectors. Static step (step 3) only
    from functions that mention ≤ 40 variables (AFOLU.project mentions 128: too coarse, not used).
  - **Specificity check** (a network linking everything would also pass): a lever or X reaches a median 27% of
    the 262 output variables; 21% of the pairs with no relation in the runs have a path (real but tiny effects, or
    over-connection, mostly through the NemoMod box). 56 of 67 groups reach NemoMod.
  - **Step 6, spot checks (read right):** L35 → fuel fractions → vehicle-km by fuel → CH₄/CO₂/N₂O from
    transportation; L50 → landfill gas recovered → CH₄ from landfills; L15 → land use transition probabilities →
    CO₂ from land use conversion; L27 → SCOE heat demand scalar → SCOE emissions; L3 → residues burned → biomass
    burning; L7 → minimum renewable share → NemoMod → electricity generation emissions; X57 GDP → GDP per capita →
    enteric fermentation.
  - **Known limits:** (1) in-between outputs computed in the same function as the emissions are on the chain only
    when the code reuses the written array (vehicle-km by fuel yes; energy consumption by fuel not yet, so it shows
    beside the chain, not on it); (2) the fuel fractions of a mode are normalised together, so each fraction links
    to every fuel's vehicle-km; (3) 9 outputs with AWS data have no edge (harvested wood CO₂, mineral soil carbon,
    4 HFC/HCFC from product use, adjusted livestock/agriculture imports and exports, synthetic fertilizer N); 28
    inputs with AWS data are never read in this run; (4) the input file predates 1.4.0 (7 fields at default 0).
- 2026-10-20 — **Node ranges (2050)**, `ranges.py` → `out/<run>_ranges.parquet` (1.6 M cells, 21 MB): for each
  lever, every field it reaches in the network, by lever level (low / mid / high thirds) × uncertainty filter (any,
  or each uncertainty with a path to the field, bottom / top third). Runs per cell: median 1,659 (any X), 552 (one
  X low or high), minimum 486. Checks: L35 → electric light-duty vehicle-km 17.7 → 22.6 billion (low → high
  lever), 25.4 billion with GDP high; L50 → CH₄ from landfilled food 5.1 → 3.2 Mt CO₂e. Covered: the 2,138 network
  fields with values in the local sample (618 emissions, 993 model_output, 527 lever inputs). **Not covered yet:**
  1,819 input fields no lever sets (93 set by the uncertainties, ~1,726 constant across runs): need one Athena query
  on model_input (rule 8, asked).
- 2026-10-20 — **Node attributes**, `attributes.py` → `out/<run>_node_attributes.csv` (711 variables: readable
  name, type, sector, subsector, gas, units, XGBoost categories, description) and `<run>_field_attributes.csv`
  (4,089 fields: SISEPUEDE category, gas, unit and its source, XGBoost category). Units known for 3,698 of 4,089
  fields (config 942, field name 2,196, no-unit by name 501, schema 59); 391 unknown, mostly NemoMod costs and
  production, left unknown rather than guessed.
- 2026-10-20 — **Other inputs read from AWS** (`other_inputs.py`, AWS_PROFILE=alexa, two scans of model_input,
  145 GB each, ≈ $1.46 in total): the 93 fields the uncertainties set, for the 4,989 sampled runs at the anchor years;
  the 1,726 other input fields for 5 runs, to confirm they are constant. 5 of them vary (the land use
  self-transition probabilities, e.g. croplands → croplands, adjusted when a lever changes the other transitions)
  and were read for every run. Ranges recomputed: 1.69 M cells, 1,539 fields.
- 2026-10-20 — **Network map published**: https://claude.ai/artifact/1QSs18DUqmS6eV2yo18qwB (private). Source page
  `backend/rdm/network/viewer/index.html`; data built by `viewer_data.py` into `out/viewer/` (network.json + one
  file of ranges per lever, 35 MB; published in batches because large uploads failed). Filter: lever + uncertainty
  (any / low / high); columns: inputs the lever sets → in-between variables by step → emissions → XGBoost
  categories; optional "other inputs that feed these variables" (constants with their value, uncertainty inputs
  with their range); variables that are zero in every run hidden by default. Click a node: attributes and, per
  field, median and p10–p90 at lever low / mid / high. L12 (clinker) reaches nothing: its input is never read in
  the traced run (gap).
- 2026-10-21 — **Uncertainty filter in three thirds** (Alexa: do not exclude any run): low 0–⅓, middle ⅓–⅔, high ⅔–1,
  so every run falls in one; "any" stays as the total. Ranges 2.49 M cells (minimum 482 runs per cell); the map
  (same link) has a Low / Middle / High selector. The agent's tool still defines only low and high thirds (v1
  note in the pre-registration of bank v3): decide when the tool is rebuilt on this network.
- 2026-10-21 — **The agent's tool rebuilt on the network** (`backend/rdm/tools/network.py`; `information.model_network`
  delegates to it). One call = one node: its attributes, what it is computed from (one step back), what it is used to
  compute (one step forward), the levers and uncertainties that reach it; the agent walks the network by asking for
  any name listed. Lever and uncertainty nodes: what they set, how many variables and which categories they reach.
  Optional `lever` (values by its thirds) and `uncertainty` + `third` (low / mid / high). Arms (Alexa: v0 / v1 is
  the difference): v0 relations only; v1_inputs + a lever's inputs at BAU / middle / top; v1_outputs + medians and
  p10–p90 of variables, emissions and categories, and for a category each lever's change from its low to high
  third; v1 both. Ranges now for every anchor year, with category totals (`emissions_<slug>`) and a "no lever"
  split (lever 0): 15.3 M cells, 187 MB. Gaps say so (L12; a lever or uncertainty that does not reach the node; a
  year with no values). Replies 0.7–4 k characters. Old weighted tool and its viewer removed. Registry, prompt
  (arm-neutral), evaluate_tools, tests (52 pass), bank v3 note and harness text updated. **Deck slides 9–14 still
  describe the previous tool.**
- 2026-10-21 — **Smoke test with the real agent** (claude-sonnet-5-5, saved in
  `backend/rdm/eval/pilot_runs/smoke_network_2026_10_21/`, not part of the bank run). P50i (landfills 40%, key
  L50 = 0.688): v1 called model_network("L50"), read BAU 0.07 → top 0.55, set 0.69 and ran it (right); v0 walked
  L50 → its input, found no values, said it could not map 40% and ran 0.4 / 0.7 / 1.0 as a bracket (the expected
  v0 behaviour). AG2 (cut farming + livestock a quarter): both arms went straight to exploratory_modeling with the
  catalogue's levers and never called model_network (no backward walk); both answered with packages reaching
  −39% or more. The tool works; whether the agent uses it for targets is a finding to watch.
- 2026-10-21 — **Deck updated**: slides 8–10, 12–15 and 18 describe the new tool; new slide 13 "Both arms walk the
  same network; only v1 sees numbers" (the lever 35 example, five levels, the walked path ①–⑤, what v0 and v1
  receive at each step, real 2050 numbers). 29 slides.
- 2026-10-21 — **Readiness check (questions and logs).** Logs keep what RQ2 measures: every call with tool,
  arguments, normalised params (model_network: node, year, lever, uncertainty, third, node kind; exploratory:
  levers and levels per policy, x_ranges), status, error code, user turn, reply and its size. Failure-mode checks run
  on the new tool (smoke runs scored with BANK_SPECS: P50i v1 clean at 0.69; P50i v0 flagged literal translation and
  level off key, as expected; AG2 v1 flags check 15 on a derived share, a known false positive). **Found:** the
  S-question keys (S50, S3, S35) were computed with the lever ≥ 0.9; the tool reports the lever's top third (⅔–1),
  whose median is lower (S3: tool 2.63 M ha vs key range 2.7–3.3 M ha), so a correct answer read from the tool could
  be scored outside the range. Decide: recompute the keys on the top third, or accept the top-third p10–p90.
  Still open from 10-19: X1 key in hectares, X2 key (2035), NDC 24.7% check.
- 2026-10-21 — **Pending (Alexa): review the XGBoost surrogate for overfitting** — the scores look very good
  (median R² 0.994). A teammate proposed k-fold. Facts so far: each of the 100,002 runs has its own future (100,001
  future ids), so the random 80/20 split does not put the same future in train and test.
- 2026-10-21 — **Question keys done** (bank v3 note and rows updated, `BANK_SPECS` in questions.py): S50 / S3 / S35
  keyed on the lever's top third (the cell the tool reports); X1 accepts L15 = 0.50–0.65 (rates halved at 0.5;
  forest loss in hectares halved at about 0.60 in 2035 and 0.65 in 2050); X2 reachable at 2035 (every lever −31.0%,
  smallest package L30, L29, L9, L15, L23 −26.1% for +1.37 bn USD); 24.7% NDC figure confirmed (updated NDC 2022,
  5.9% unconditional + 18.8% conditional; NDC BAU 2030 ≈ 143 Mt vs model BAU 2035 139 Mt). The "100k tables" step
  is no longer needed: the tool's values come from the network ranges on the 4,989-run sample, with at least 482
  runs per cell. Left before the full run: commit and freeze, then the full bank run (Alexa's go).
- 2026-10-21 — **Frozen in git** (network, tool, keys, tests, deck). Not in git, regenerable: `out/run_2026_05_30_ranges.parquet`
  (187 MB, over GitHub's limit; `python -m backend.rdm.network.ranges`, ~7 min), SHA-256 `e3945e9999a05e167b5b7dfca84b88c90296ee68a6a12447e8cf16117a9d03dc`; the map data
  (`out/viewer/`, `viewer_data.py`); NemoMod's working database.
- 2026-10-21 — **Bank v3.1: five hypothesis questions** (HA1–HE1), pre-registered and committed (66a813e) before their
  keys; keys computed by the pre-registered rules and added to BANK / BANK_SPECS and the bank doc; new check 25
  (required node visited with model_network) and the count of model_network calls in the failure-mode table; 53
  tests pass. The bank is now 31 questions in 29 conversations. Not yet smoke-tested with the agent.

## Next meeting (set 2026-10-21)

State: everything up to the network tool, the S / X1 / X2 keys and the deck is committed (1292e0b); the v3.1
pre-registration is committed (66a813e). **Uncommitted, on purpose until the meeting:** the five hypothesis
questions' wording, specs and keys (`backend/rdm/eval/questions.py`, `docs/question_bank_v3.md`, key table), check 25
and the network-call count (`backend/rdm/eval/failure_modes.py`, `tests/rdm/test_failure_modes.py`), and this log.

1. **Smoke test of HA1–HE1**: each question once in v0 and v1 (10 conversations, small API cost), saved apart from
   the bank run (as `pilot_runs/smoke_network_2026_10_21/` was). Check that the questions read as intended and that
   the failure-mode table scores them (check 25, x_ranges_set for HC1, levels for HA1 / HE1, network_calls).
   Command: the smoke script pattern of 2026-10-21 (`converse(...)` per question and arm, PYTHONPATH=.), then
   `python -m backend.rdm.eval.failure_modes <dir>` scored with BANK_SPECS (set question_set="bank" in the saved
   runs, or call `check(run, BANK_SPECS[qid])`).
2. **Commit** the keys, check 25 and the docs (one commit; the pre-registration commit 66a813e already dates the
   hypotheses before the keys).

After that: the full bank run (31 questions in 29 conversations × 4 arms × 3 reps, Alexa's go on the cost) and the
XGBoost overfitting review (separate).

## Update 2026-10-26

- Smoke test of HA1–HE1 done (v0/v1; `pilot_runs/smoke_hypotheses_2026_10_26_thinking/`), committed with the keys,
  check 25, two scoring fixes (checks 5 and 15), the HD1 PJ mention, summarized thinking in the logs and the reader
  fix (d0d32e4). Finding: HD1 v1 receives transport electricity (56.0 → 59.9 PJ) from the network but tells the user
  it cannot report it, because the surrogate does not.
- Source-label test (pre-registered, `docs/preregistration_source_labels.md`; results `docs/results_source_labels.md`):
  `country_context`'s GDP is the base future 0, above the runs' p90; unlabelled, half of HC1's answers concluded
  "580 bn covers most futures". **Decision (Alexa, 2026-10-26): the full bank run uses the labelled version**
  (`backend/rdm/tools/context.py`, `GDP_LABEL`, in the code since c3bcf15). Logs from before c3bcf15 used the
  unlabelled reply.
- Open: team question on X57's range (base path at the top of it); GDP unit labels differ between `model_network`
  ("billion USD") and `country_context` ("PPP"); Alexa hand-checks X1 and 10 P2 answers.

Next: the full bank run (Alexa's go on the cost) and the XGBoost overfitting review (separate).
