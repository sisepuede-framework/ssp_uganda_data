# RDM tool design — draft v0

*Working design, branch `rdm-tools`, 2026-09-30. It replaces the current tool architecture
(`run_simulation`, `get_scenario_variables`, …) on this branch only; the `metamodel` branch
keeps the deployed system intact. Slide version: "RDM Tool Design" deck.*

---

## Principles

1. **RDM lives in the tools, not in the prompt.** Every evaluation of a policy is an ensemble;
   no tool returns one number from one future.
2. **Levers are decided; uncertainties are sampled.** Levers outside the policy sit at 0 (a
   decision not to act). All 13 X are sampled unless the question restricts their range.
3. **Focus is what is shown, not what moves.** All 13 X move in every ensemble. The
   vulnerability map projects the ensemble onto 2 X: by default the 2 that best separate pass
   from fail for that policy, or the 2 the user picks. Each cell's pass rate already averages
   over the other 11, and the tool reports how much they contribute.
   *(Pending: which value an X takes when it is not varied — to confirm with the team's expert.)*
4. **One tool, one data source.** Questions about the *system* read real SISEPUEDE runs
   (precomputed tables); questions about *a specific policy* run the XGBoost. The agent picks
   tools, never sources.
5. **Declare before you run.** Every experiment states L, X, M and a success criterion, and the
   user confirms it. The declaration records the question category, which is scored.

Evidence behind principle 3, from the current surrogate: the 11 X outside the top two explain
at most 4.4% of any output's variance, and the 2050 electricity-emission cut from renewables
at 0.8 is 51–53% whether background X sit at 0, at 0.5 or are sampled.

---

## Data layers

| Layer | Answers | Source | Tools |
|---|---|---|---|
| Knowledge | what a lever does, what drives an output, tangible and intermediate variables | real runs (100k hypercube), precomputed tables | `query_map`, `translate_target`, `mechanism_evidence` |
| Experimentation | how this policy performs, where it fails, how it compares, which levels meet a target | XGBoost, at run time | `define_experiment`, `run_experiment`, `find_vulnerabilities`, `compare_policies`, `search_policy` |
| Reference | official strategies | real runs (pathways) | `get_pathway_results` |

Why not the XGBoost alone: 258 outcome targets and no intermediate variables, so it cannot
translate tangible targets or explain a failure. Why not the data alone: the 100k runs
randomise all 54 levers, so none holds a specific policy and none can evaluate one across
futures.

---

## Tools

| # | Tool | RDM step | Inputs | Outputs | Source |
|---|---|---|---|---|---|
| 1 | `query_map` | information | levers, or an output (metric + year) | per lever: outputs moved, 0→1 change (median, p10–p90), curve shape, headline tangible variable, X that most alter its effect. Per output: typical level and range, levers and X that explain it, 2 suggested X | response map (`lever_response_map.json`, XGBoost today; to recompute from real runs, the difference being a fidelity check) + real runs for tangible variables |
| 2 | `translate_target` | information (inverse) | tangible variable (or lever), target value, year, optional X condition | lever level needed per region of X; reachable or not; maximum reachable; variable's distribution at that level | real runs: Li × Xj → tangible-variable tables (~4,000 runs per cell) |
| 3 | `define_experiment` | 1 · frame (XLRM) | category (A1–F4); policies (lever values or ranges); X mode: `all` or `conditioned` {X: range}; `x_to_show` (≤2, optional); metrics (outputs + years); success criterion (metric, threshold, direction, minimum share of futures) | experiment id; plain-language framing for the user to confirm; warnings (unknown id, X used as a lever, missing criterion, chosen X explains <1%) | feature registry + map (validation only) |
| 4 | `run_experiment` | 2 · generate cases | experiment id, number of futures (default 1,000) | per policy: distributions (median, p10, p90), paired change vs BAU on the same futures, share of futures meeting the criterion, extrapolation flags; stores the ensemble | XGBoost |
| 5 | `find_vulnerabilities` | 3 · scenario discovery | ensemble id, policy, optional `x_to_show` | failure rules over the 13 X (CART: condition, coverage, density), the 2 most important X, X₁ × X₂ map of pass rates, share left to the other X | XGBoost (the stored ensemble) |
| 6 | `mechanism_evidence` | 3b · explain why | failure region (from 5), policy levers, intermediate variables | intermediate variables inside vs outside the failure region (e.g. electricity demand under high GDP vs the rest), with levers in a similar range | real runs (all SISEPUEDE outputs) |
| 7 | `compare_policies` | 4 · trade-offs | ensemble with 2+ policies on the same futures | per policy: robustness, emissions, costs, benefits, net; regret per future (max, p90); dominated policies | XGBoost |
| 8 | `search_policy` | 5 · design and iterate | experiment id with the target as criterion; candidate levers (+ ranges; default from the map); constraints (cost, number of levers); required robustness | a few candidate policies that meet the target in ≥ p% of futures (least ambitious first), or the maximum reachable if infeasible | XGBoost (search over L, common X ensemble) |
| 9 | `get_pathway_results` | reference | official strategy | trajectories of the strategy | real runs (pathways) |
| 10 | `get_country_context` | context | sector or topic | inventory and country context | inventory |

**Against the current system:** `run_simulation` → tools 3 + 4; `get_scenario_variables` →
absorbed by 1; new: 2, 5, 6, 7, 8; kept: 9, 10.

**Merge candidates if the pilot shows little use:** 3 + 4 (loses the confirmation step with
the user); 4 + 7 (compare only adds regret and dominance).

---

## Question categories

| Category | Example | Surrogate runs |
|---|---|---|
| A · Information | "What does the light-duty electrification lever do?" | none |
| B · Evaluate a given policy | "What if renewables go to 0.8?" · "What if half the light-duty fleet is electric?" | one ensemble |
| C · Reach a target | "Cut transport emissions 30% by 2050." | many ensembles (a search over levers) |
| D · Robustness and vulnerability | "Under which conditions does this policy fail?" · "What if GDP grows fast?" | one ensemble, X all or conditioned |
| E · Compare and trade-offs | "Is policy A better than B? What does it cost?" | paired ensembles on the same futures |
| F · Outside the surrogate | "How does the official Net Zero strategy perform?" · "How many jobs?" | none: real runs, or decline |

## Flow per category

The agent classifies the question before any tool. The category is recorded by
`define_experiment`, and in the structured final answer for A and F.

```
A · INFORMATION (no surrogate run)
  A1–A3 ──► [1 query_map] ──► answer
  A4    ──► [10 get_country_context] ──► answer

B · EVALUATE A GIVEN POLICY
  B1 (levers given) ─────────────────────────────┐
  B2 (natural language) ──► [1 query_map] ───────┤
  B3 (tangible target) ──► [2 translate_target] ─┤
  B4 (variable not in the model) ──► [1] ──► ask / propose a proxy, no run yet
                                                 ▼
                    [3 define_experiment] ──► user confirms
                                                 ▼
                                      [4 run_experiment]
                                                 ▼
                                   criterion given?
                                     yes ──► [5 find_vulnerabilities]
                                     no  ──► distributions + offer a criterion

C · REACH A TARGET
  [1 query_map] ──► target stated in a tangible variable? ── yes ──► [2 translate_target]
         │                                                                  │
         └──────────────────────────────┬───────────────────────────────────┘
                                        ▼
                     [3 define_experiment] (target = criterion)
                                        ▼
                               [8 search_policy]
                                        ▼
                   any policy meets it in ≥ p% of futures?
                     no  ──► report the maximum reachable (C3)
                     yes ──► [7 compare_policies] (costs, constraints: C4)
                                        ▼
                      [5 find_vulnerabilities] for the chosen policy

D · ROBUSTNESS AND VULNERABILITY
  D1, D2 ──► [3 define_experiment] (X: all)
  D3     ──► [3 define_experiment] (X conditioned, e.g. GDP in its top third)
                                        ▼
                               [4 run_experiment]
                                        ▼
                          [5 find_vulnerabilities]
                                        ▼
                   user asks why? ──► [6 mechanism_evidence]
  D4 ──► [3] (several policies, X conditioned) ──► [4] ──► [7 compare_policies]

E · COMPARE AND TRADE-OFFS
  E1 ──► [3 define_experiment] (2+ policies) ──► [4] (same futures) ──► [7 compare_policies]
  E2 ──► [3] ──► [4] (costs and benefits)

F · OUTSIDE THE SURROGATE
  F1 (official strategy) ──► [9 get_pathway_results]
  F2 (reference that does not exist) ──► decline + offer an alternative
  F3 (outside the model) ──► decline
  F4 (ambiguous) ──► ask for clarification before any tool
```

**Single surrogate run:** only when the user explicitly asks for one concrete future (e.g. the
official GDP and population projection). The agent presents it as one future and offers the
ensemble. No other category justifies it.

**Coverage:** every tool appears in at least one flow. Narrowest use: 6 (`mechanism_evidence`,
D only) and 10 (`get_country_context`, A4 only).

---

## What every turn records (for the evaluation)

| Signal in the log | What it measures |
|---|---|
| declared category vs the category assigned in advance | classification |
| tool sequence vs the expected flow | routing |
| declared category vs actions (e.g. declared D3, then fixed GDP) | coherence |
| calls to `query_map` / `translate_target`, with arguments and returns | information uptake |
| "why" claims, and whether `mechanism_evidence` backs each one | provenance |

## Open items

- Which value an X takes when it is not varied (ask the team's expert).
- Headline tangible variable and mechanism variables per lever (list to curate).
- Search method behind `search_policy`.
- Simulated user for automated runs (fixed reply at the confirmation step).
- Recompute the response map from real runs and compare with the XGBoost version (fidelity check).
- Saved idea: verify "why" claims before they reach the user (a tool or a second agent).
