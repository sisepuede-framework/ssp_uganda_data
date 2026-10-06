# RDM tool design — draft v1

*Branch `rdm-tools`, 2026-10-06 (v0: 2026-09-30). Replaces the current tool architecture
(`run_simulation`, `get_scenario_variables`, …) on this branch only; the `metamodel` branch
keeps the deployed system intact. Slide version: `docs/rdm_tool_design_v1.pptx`.
Experiment design: `paper1/md_to_claude/study_plan.md` §2.*

**What changed from v0:** the user is the policy maker (never 0–1 values); `query_map` and
`translate_target` are split into four single-purpose knowledge tools plus a catalog;
`mechanism_evidence` becomes `explain_failure`; `declare_plan` is added; `get_pathway_results`
is removed; a harness is specified; the experiment is v0 / v1 with a placebo knowledge layer.

---

## Principles

1. **RDM lives in the tools, not in the prompt.** Every evaluation is an ensemble; no tool
   returns one number from one future.
2. **Levers are decided; uncertainties are sampled.** Levers outside the policy sit at 0 (BAU).
   All 13 X are sampled unless the question restricts their range.
3. **Focus is what is shown, not what moves.** All 13 X move in every ensemble; vulnerability
   maps project onto the 2 X that matter most, or the 2 the user picks.
4. **One tool, one capability, one data source.** Each tool answers one question. No question
   can be answered by two tools, and each description says when *not* to use it.
5. **Declare before you run.** Every experiment states L, X, M and a success criterion, and
   the user confirms it in plain language.
6. **Policy-maker language in, real units out.** The user never needs a 0–1 value; the agent
   translates objectives into lever levels and uncertainty ranges, and results back into real
   units.

---

## Data

| Source | What it holds |
|---|---|
| LHC design (run folder) | 0–1 value of every L and X group in each of the 100k futures; `ATTRIBUTE_PRIMARY` links runs to futures |
| Group definitions | Input variables each group sets (547 in L, 93 in X) |
| Raw runs (S3) | Every input and output per run and year, original units: `model_input` 145 GB, `model_output` 111 GB, `decomposed_emissions` 35 GB, `cb` 2 GB |
| Lever → output mapping | Which emissions (from `decomposed_emissions`) and which variables (from `model_output`, the ones that explain the emissions) each lever and uncertainty moves, from SISEPUEDE's structural map and from the runs (|Spearman rho| ≥ 0.10 on a 5,000-run sample): 4,805 links; 46 of 54 levers and 5 of 13 uncertainties move both. Built by `backend/rdm/mapping/`; review file `lever_x_output_mapping.xlsx` |
| XGBoost surrogate | 67 L/X → 258 outputs (23 emission categories, costs, benefits, GDP; 6 years) |

**The (L, X) object** (the information under test): for every pair (L_i, X_j), how every
mapped emission and variable responds as L_i and X_j vary, the other inputs still varying.
Only L and X are 0–1; outputs keep their units. Stored once as a run-level table; a pair is a
query.

---

## Tools

| Group | Tool | The one question it answers | Data | v0 / v1 |
|---|---|---|---|---|
| Process | `declare_plan(category, planned_steps)` | "What kind of question is this, and what will I do?" Must come first | — | identical |
| Catalog | `search_catalog(text)` | "What is the user's word called in the model?" | Registry, mapping, units | identical |
| Knowledge | `get_lever_effects(levers, [X], year)` | "What does this lever move, and how much; how does X change it?" | (L, X) object | v0 names / v1 values |
| Knowledge | `get_output_drivers(output, year)` | "Which levers and X move this emission or variable?" | (L, X) object | v0 unranked names / v1 ranked effects |
| Knowledge | `solve_lever_level(output, target, year, [X])` | "What level of one lever reaches this target?" | (L, X) object | v0 levers, no level / v1 level per X region, range, reachable |
| Knowledge | `explain_failure(region, policy)` | "Why does the policy fail in this region?" | (L, X) object, raw runs | v0 candidate variables / v1 which differ and by how much |
| Experimentation | `define_experiment(policies, X ranges, metrics, criterion)` | "Is this experiment well framed?" Frames, does not compute | Registry; X in real units | identical |
| Experimentation | `run_experiment(experiment_id, n_futures)` | "How does this policy perform across futures?" | XGBoost | identical |
| Experimentation | `find_vulnerabilities(ensemble_id, policy, [x_to_show])` | "Where does it fail?" | Stored ensemble | identical |
| Experimentation | `compare_policies(ensemble_id)` | "Which policy is better, at what cost?" | Stored ensemble | identical |
| Experimentation | `search_policy(experiment_id, candidates, constraints)` | "Which combination of levers meets the target robustly?" | XGBoost | identical |
| Context | `get_country_context(topic)` | "What does the country look like today?" | Inventory | identical |

**Boundaries to state in the descriptions:**
- `solve_lever_level` solves **one** lever from the data, approximately, without evaluating a
  policy. `search_policy` searches **combinations** with XGBoost ensembles and robustness.
- `define_experiment` frames (no computation); `run_experiment` computes. The user's
  confirmation between them is a dialogue step, not a tool.
- `get_lever_effects` goes from a lever to its outputs; `get_output_drivers` goes from an output
  to its levers.
- `search_policy` never proposes default candidate levers (that would leak v1 data into v0).

---

## The harness

The agent decides which tool to use; the harness never does. A deterministic orchestrator that
fixes the sequence per category would remove what the experiment measures: whether the
information changes the agent's choices.

| Function | What it does |
|---|---|
| State | Stores experiments and ensembles by id, so tools chain without the agent copying data |
| Rules (in code) | No `run_experiment` without a confirmed `define_experiment`; no X fixed at one value; C and D require a success criterion; levers in [0, 1]; `declare_plan` before any other tool |
| Log | Every turn: plan, tool sequence, arguments, returns, "why" claims |
| Limits | Same `max_iterations` and timeouts in v0 and v1 |

---

## Flow per category

```
A · INFORMATION        declare_plan → search_catalog → get_output_drivers | get_lever_effects → answer
B · EVALUATE A POLICY  declare_plan → search_catalog → solve_lever_level → define_experiment
                       → user confirms → run_experiment → find_vulnerabilities (if a criterion is given)
   B · not in model    search_catalog finds nothing → ask, or propose a proxy; no run until agreed
C · REACH A TARGET     declare_plan → get_output_drivers → define_experiment (target = criterion)
                       → search_policy → none meets it: report the maximum reachable
                                       → some meet it: compare_policies → find_vulnerabilities
D · ROBUSTNESS         declare_plan → define_experiment (X all, or conditioned: "boom" = GDP high range)
                       → run_experiment → find_vulnerabilities → explain_failure (if asked why)
E · COMPARE            declare_plan → get_lever_effects → define_experiment (2+ policies)
                       → run_experiment (same futures) → compare_policies
F · OUTSIDE THE MODEL  declare_plan → decline (not in the model) or ask for clarification (ambiguous)
```

**Single surrogate run:** only when the user asks for one concrete future; presented as one
future, with the ensemble offered.

---

## v0 and v1

Same prompt, same 12 tools with the same names, schemas and descriptions. The only difference:
in v0 the four knowledge tools return names only; in v1 they return values across L_i and X_j.
The prompt is written from scratch, carries no lever-effect information, and never mentions a
capability only one version has. Details and hypotheses: `study_plan.md` §2.

## What every turn records

| Signal | Measures |
|---|---|
| `declare_plan` category vs the category assigned in advance | classification |
| Plan vs tools actually called | adherence |
| Tool sequence vs the expected flow | routing |
| Knowledge-tool calls, arguments and returns | information uptake |
| "Why" claims, and whether `explain_failure` backs each one | provenance |

## Open items

- Value an X takes when it is not varied (team's expert).
- Complete the lever → output mapping (19 levers), map X → outputs, add units.
- Real units for the 13 uncertainties.
- Search method behind `search_policy`.
- Simulated user for automated runs (fixed reply at the confirmation step).
- Whether `explain_failure` is part of the v1 payload only (current proposal) or partly shared.
