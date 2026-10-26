# Decision charter and question bank — draft v0

*Branch `rdm-tools`, 2026-10-06. Covers section 1 of `rdm_todo.md`. Companion to
`rdm_tools_design.md` (tools, categories A–F, flows). Items marked **[decide]** need Alexa's
call; items marked **[expert]** go to the two experts.*

---

## Part 1 · Decision charter

One page that every C and D question, and every success rule below, refers back to.

| Element | Definition for this study |
|---|---|
| **Decision maker** | A technical officer in Uganda's climate-policy process (e.g. the team preparing NDC 3.0) who uses the agent to explore sectoral transitions before they go to the full SISEPUEDE runs. Not a modeller: the user speaks in policy and tangible terms, not in lever IDs. |
| **Decision** | Which sectoral transitions (L) to pursue, and how ambitiously (0–1), so that national emissions meet a target robustly across plausible futures, at acceptable cost. |
| **L — levers** | The 54 SISEPUEDE transformations (16 sectors), each scaled 0 = no action (BAU) → 1 = maximum technically feasible by 2070. Levers outside a policy stay at 0. |
| **X — uncertainties** | The 13 exogenous factors (GDP growth, population growth, fossil fuel prices, demand elasticities, technology capital costs, agricultural exports). All 13 are sampled in every ensemble; a question can condition their range ("if GDP grows fast" = GDP in its top third), never fix them to a single value. |
| **R — relationships** | XGBoost surrogate of SISEPUEDE for policy evaluation (258 targets: 23 emission categories, 16 benefits, 3 costs, GDP × 6 years); real SISEPUEDE runs (100k hypercube) for system knowledge and intermediate variables. |
| **M — metrics** | Net economy-wide emissions and the 23 inventory categories (Mt CO₂e); costs (3 types) and benefits (16 types), billion USD and % of GDP; selected tangible variables from the real runs. Anchor years: 2025, 2035, 2040, 2050, 2060, 2070 (no 2030). |
| **Reference points** | Official pathways, net Mt CO₂e. BAU: 2035 = 157.2, 2050 = 205.0, 2070 = 286.8. NDC 2.0: 95.4 / 115.8 / 97.9. HBLE (NDC 3.0 basis): 103.6 / 52.4 / 8.2. |

### Default success criterion

Used whenever the user gives a target but no robustness rule, and offered when they give
neither:

> **A policy succeeds in a future if net emissions in 2050 are at least 50% below BAU in that
> same future. A policy is *robust* if it succeeds in at least 80% of the sampled futures.**

Why these choices:

- **Paired, relative to BAU in the same future**, not to a fixed Mt value. High-GDP futures
  raise both BAU and policy emissions; a fixed threshold would mostly measure GDP, not the
  policy.
- **50% in 2050** sits between NDC 2.0 (−44% vs BAU in 2050) and HBLE (−74%): reachable,
  but not by one lever.
- **80% of futures** is a common RDM satisficing threshold, strict enough that some
  policies will fail it, so `find_vulnerabilities` has something to find.

**[decide]** Confirm the three numbers (50%, 2050, 80%), or replace them with an official
target the team prefers (for example, matching the HBLE 2050 level).

---

## Part 2 · Question sub-types

The design doc names A1–F4, but only B, E and F are fully spelled out. Proposed definitions
for the rest, plus the magnitude sub-types from the 2026-09-29 discussion:

| Code | Sub-type | Expected behaviour |
|---|---|---|
| A1 | What a lever does | `query_map` (lever) |
| A2 | What drives an output | `query_map` (output) |
| A3 | Which lever reaches a tangible variable | `query_map` |
| A4 | Country context today | `get_country_context` |
| B1 | Policy given in levers | `define_experiment` → `run_experiment` |
| B2 | Policy in natural language | `query_map` → B1 flow |
| B3 | Policy as a tangible target, variable in the model | `translate_target` → B1 flow |
| B4 | Tangible target, variable **not** in the model | `query_map` → ask / propose a proxy, no run |
| C1 | Sector target | `query_map` → `define_experiment` → `search_policy` |
| C2 | Economy-wide target | same as C1, wider lever set |
| C3 | Infeasible target | `search_policy` → report maximum reachable |
| C4 | Target under a constraint (cost, number of levers) | `search_policy` → `compare_policies` |
| D1 | Is it robust? | `define_experiment` (X all) → `run_experiment` → `find_vulnerabilities` |
| D2 | Where / why does it fail? | D1 flow → `mechanism_evidence` |
| D3 | Conditioned future ("if GDP grows fast") | `define_experiment` (X conditioned) → … |
| D4 | Which policy holds up in a conditioned future | conditioned X, several policies → `compare_policies` |
| E1 | A vs B | paired ensemble → `compare_policies` |
| E2 | Cost and benefit of one policy | `run_experiment` (costs, benefits) |
| F1 | Official strategy | `get_pathway_results` |
| F2 | Reference that does not exist | decline + alternative |
| F3 | Outside the model | decline |
| F4 | Ambiguous | clarify before any tool |

Cross-cutting **traps** (a question may carry one on top of its sub-type):
*dead lever* (lever with no effect on the stated metric), *target year* (2030, not an
anchor), *L/X trap* (an uncertainty phrased as a policy, or the reverse), *side effect*
(the user asks about emissions but the lever mainly moves a cost or benefit).

---

## Part 3 · Question bank (draft, 20 questions)

Target for the frozen bank: 10–12. Pairs (same intent, lever vs tangible wording) are marked
⇄. **Referent** = what the answer is scored against: *E* expert selection, *S* surrogate
ensemble computed in advance, *R* real SISEPUEDE runs or pathway file.

| ID | Question (exact wording sent) | Cat. | Trap | Expected tool sequence | Referent | Success rule |
|---|---|---|---|---|---|---|
| Q01 | "What does shifting light-duty vehicles to electricity actually change in the model?" | A1 | — | `query_map` | R | Names lever 35; reports what the map shows (2050: transport emissions −13%, road-safety and congestion benefits +12%, total emissions only ≈ −1%); does not claim an electricity-emission effect the map does not show; no ensemble run. |
| Q02 | "What drives Uganda's emissions from forest land in 2050?" | A2 | — | `query_map` | R | Names the top levers and X for "Forest Land – Removals"; explains biomass is booked there. |
| Q03 | "Which policies change the area of secondary forest?" | A3 | — | `query_map` | R | Returns levers that move `area_lndu_forests_secondary`; flags that lever 17 is not in the structural map. |
| Q04a ⇄ | "Set light-duty fuel shift to 0.8 and tell me what happens to transport emissions in 2050." | B1 | — | `define_experiment` → `run_experiment` | S | L35 = 0.8, all else 0, X all sampled; reports a distribution vs BAU, not one number. |
| Q04b ⇄ | "What if 60% of light-duty vehicle-km were electric by 2050?" | B3 | — | `translate_target` → `define_experiment` → `run_experiment` | S + R | Translates to an L35 level (range by X); states the translation; same ensemble logic as Q04a. |
| Q05 | "What if Kampala had 10,000 electric buses?" | B4 | — | `query_map` → ask / proxy | E | No run before the user agrees to a proxy; says bus counts are not in the model. |
| Q06 | "Cut transport emissions by 30% by 2050 compared with BAU." | C1 | — | `query_map` → `define_experiment` → `search_policy` → `compare_policies` | S | Finds ≥1 transport-only policy meeting the criterion in ≥80% of futures, least ambitious first. |
| Q07a ⇄ | "What combination of policies gets us to half of BAU emissions by 2050?" | C2 | — | as Q06, all sectors | S | Uses the default criterion; returns candidates with robustness, costs. |
| Q07b ⇄ | "How do we reach 70% renewable electricity and forest area back at 2015 levels by 2050 — and what does that do to total emissions?" | C2 | — | `translate_target` (×2) → `define_experiment` → `run_experiment` | S + R | Translates both tangible targets; reports the emissions consequence as a distribution. |
| Q08 | "Get net emissions in 2050 below 20 Mt using only transport and waste policies." | C3 | — | `search_policy` → maximum reachable | S | States it is infeasible within those sectors; reports the maximum reachable and in what share of futures. |
| Q09 | "Find the cheapest set of at most three levers that halves 2050 emissions versus BAU." | C4 | — | `search_policy` (constraint) → `compare_policies` | S | Respects the 3-lever cap; ranks by cost; reports robustness. |
| Q10 | "Is a policy of renewables at 0.8 plus reduced deforestation at 0.6 robust?" | D1 | — | `define_experiment` → `run_experiment` → `find_vulnerabilities` | S | Applies the default criterion (or asks for one); reports share of futures passing and the failure region. |
| Q11 | "Under which conditions does the Q10 policy fail, and why?" | D2 | — | `find_vulnerabilities` → `mechanism_evidence` | S + R | Every "why" claim is backed by `mechanism_evidence`; failure X named from CART, not guessed. |
| Q12 | "What if GDP grows fast — does the Q10 policy still work?" | D3 | L/X | `define_experiment` (GDP top third, rest sampled) → `run_experiment` → `find_vulnerabilities` | S | Conditions GDP, does **not** set GDP = 1 and run once; does not treat GDP as a lever. |
| Q13 | "If population grows fast, which holds up better: an energy-led or a land-led policy?" | D4 | — | conditioned X, 2 policies → `compare_policies` | S + E | Same futures for both; agent states the policies it built and the user confirms. |
| Q14 | "Is electrifying transport better than cutting deforestation for Uganda?" | E1 | — | `define_experiment` (2 policies) → `run_experiment` → `compare_policies` | S | Paired ensembles; reports robustness, cost, regret; no winner from a single future. |
| Q15 | "What would maximum clean cooking cost, and what would it bring?" | E2 | side effect | `query_map` → `run_experiment` (costs, benefits) | S | Reports costs and health/air benefits, not only emissions. |
| Q16 | "Does NDC 2.5 meet Uganda's 2030 target?" | F1 | target year | `get_pathway_results` | R | Says 2030 is not an anchor year; does not interpolate silently. |
| Q17 | "How many green jobs would the HBLE strategy create?" | F3 | — | decline | — | Declines: jobs are not a model output; offers what is available (benefits). |
| Q18 | "Make Uganda greener." | F4 | — | clarify | E | Asks what "greener" means (emissions, forests, air quality) before any tool. |
| Q19 | "How much does reducing CH4 from rice cut Uganda's emissions?" | A1 | dead lever | `query_map` | R | Reports a negligible effect (rice is minor in Uganda; lever not in the structural map) instead of inventing one. |
| Q20 | "Raise fossil fuel prices to cut transport emissions." | B2 | L/X | clarify → `query_map` | E | Explains fuel prices are an uncertainty, not a lever; offers the matching levers or a conditioned-X run. |

### Notes on the draft

- **Coverage.** Every sub-type in Part 2 appears at least once except A4 and F2. Add them, or
  drop them from the scored set. **[decide]**
- **Three pairs** (Q04, Q07, plus Q10–Q12 as a chained D sequence) test lever vs tangible
  wording and multi-turn flows.
- **Tangible variables used** (Q04b, Q07b, Q03) exist in the current run's `model_output`:
  `vehicle_distance_traveled_trns_road_light_*`, `nemomod_entc_annual_production_by_technology_pp_*`,
  `area_lndu_forests_*`. Variables that do **not** exist, and are meant to fail: bus counts
  (Q05) and jobs (Q17).
- **Q19 checked** in `lever_response_map.json`: lever 1 moves no output above the threshold
  (0→1 change on total 2050 emissions −0.1 Mt, p10–p90 −0.4 to +0.1; largest single effect
  −1.3% on Agriculture and Managed Soil in 2070).
- **Q15** uses "clean cooking", which maps ambiguously to SCOE levers 27–30. This is a
  deliberate B2-style translation, but the experts should confirm the mapping. **[expert]**
- **Freeze rule.** Keep at most 2 questions per category and keep all 3 pairs; cut the rest
  to reach 10–12.

---

## Part 4 · Expert instrument (per question)

Sent to both experts with the charter (Part 1) attached. Experts never see agent answers;
where the two disagree, report it as ambiguity, do not average.

1. Which levers would you activate? *(tick from the 54, grouped by sector; direction ↑/↓)*
2. Which sectors are implicated?
3. Which uncertainties should be **sampled with particular care** for this question?
   *(Never "which would you set".)*
4. Is the question under-specified? Would you ask the user for clarification first? What?
5. For tangible wordings (Q04b, Q07b): is the tangible variable a fair reading of the
   question?
6. Free-text rationale.

Plus, once per expert, not per question:

- Is the default success criterion (50% below BAU in 2050, in ≥80% of futures) a reasonable
  default for a Ugandan policymaker? If not, what would be?
- **[pending from the team]** When an X is not varied, what value should it take?

**Practical:** the experts get only the questions scored against *E*, plus the two tangible
pairs: Q04, Q05, Q07, Q13, Q15, Q18, Q20 (≈ 9 items). That keeps the instrument to about an
hour.
