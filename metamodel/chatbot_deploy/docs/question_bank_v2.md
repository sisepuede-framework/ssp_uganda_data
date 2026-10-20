# Question bank — draft v2 (for Alexa's revision)

*2026-10-19. Replaces `question_bank_v1.md` (kept for reference). Built from the critical review
(`review_questions_vs_rqs.md`) with two extra rules from Alexa: **spread the questions across sectors** (v1 had 7 of 32
on light-duty vehicles), and assign tools with **the guide on deck slide 11** ("Which tool for which question").
21 questions.*

*Updated 2026-10-19 after the review against the final RQs (`review_bank_vs_final_rqs.md`): plainer wording for a
non-technical user (the number and what it is a share of are kept, so the keys do not change). Decided: the
**uncertainty ranges** part of RQ2 is an **expected null** — no arm gives the uncertainties in real units and the
prompt translates "fast growth" the same way in every arm, so the arms are not expected to differ there. Pending:
adding TO1 (trade-off) and N2 (livestock strategy improvement); the cost-sign audit (`review_cost_signs.md`).*

Keys were computed on 2026-10-19 with the **retrained** surrogate (2050, other levers at 0, 1,000 futures, all 13
uncertainties sampled) or exactly from the lever input table. Keys for questions kept from v1 come from v1 and are
marked *(v1)*; those are exact or from the runs, so the retrain does not change them.

## How to read a row

- **Kind** (what has to be translated, the label that decides whether the experiment's arms can differ):
  - **T1**: the question names a quantity a lever *sets* ("40% of landfill gas recovered") → the input values translate it.
  - **T2**: it names an *in-between* quantity the model computes (vehicle-km, hectares) → the output values translate it.
  - **T3**: it names an *emissions* target → only testing on the surrogate answers it (same in every arm: a control).
  - **T0**: nothing to translate (control). **T4**: not in the model → the agent must say so.
- **Tools**: from the slide-11 guide, in order. **Must / must not** is what we score (not the exact order): an
  action that has to happen, and one that must not.
- **Levels** go from 0 (business as usual, BAU) to 1 (the most ambitious level explored in the experiment's
  runs).

## Sectors covered

| Sector | Questions |
|---|---|
| Solid waste | P50i, S50, C4b |
| Wastewater | WW1, C4b |
| Industry (cement) | P12i |
| Agriculture | AG1, S3, AG2 |
| Livestock and diets | LV1, LV2, AG2, D3b |
| Buildings (cooking, heating) | BLD1, Q14b |
| Transport | B6, S35 |
| Electricity | Q10b, D2b, N1, B8b |
| Forests and land use | Q10b, D2b, N1, Q14b |
| The economy (an uncertainty) | F3b |

---

## 1 · Evaluate a policy given in real-world units (T1) — 7 questions

The core of RQ2: does the agent translate the user's words into the right lever level?

| ID | Sector | Question (exact wording) | Tools | Must / must not | Answer key |
|---|---|---|---|---|---|
| P50i | Solid waste | "What if Uganda's landfills captured 40% of the methane their rubbish gives off (landfill gas) by 2050?" | lever_x_profile → exploratory_modeling | must read lever 50 before running · must not use 0.4 as the level | exact: L50 = 0.688 (BAU 7% → 55%) *(v1)* |
| P12i | Industry | "What if cement made in Uganda used less clinker, its most polluting ingredient, so that clinker was 65% of the cement by 2050 instead of about 72%?" | lever_x_profile → exploratory_modeling | must read lever 12 before running | exact: L12 = 0.583 (BAU 72% → 60%) *(v1)* |
| AG1 | Agriculture | "What if farmers stopped ploughing on 30% of the land where they grow cereals by 2050, and what would that do to emissions?" | lever_x_profile → exploratory_modeling | must report that agricultural emissions **rise** slightly · must not claim a cut | exact: L3 = 0.51 (BAU 0.1% → 59%). Surrogate: agriculture emissions **+2.3%** (+1.7 to +3.3) vs BAU — counter-intuitive, to report as found |
| LV1 | Livestock | "What if 40% of the manure from dairy cows were used to make biogas by 2050?" | lever_x_profile → (exploratory_modeling at the top of the range) | must say the model runs reach at most about 33% · must not test a level above 1 | exact: beyond the explored range (lever 20: BAU 0% → 32.7%). Offers the top of the range instead |
| BLD1 | Buildings | "What if homes and businesses used a quarter less energy for cooking and heating by 2050?" | lever_x_profile → exploratory_modeling | must read lever 27 before running | exact: L27 = 0.67 (heat demand ×1 → ×0.627) |
| WW1 | Wastewater | "What if half of rural households' wastewater went to septic tanks by 2050?" | lever_x_profile → exploratory_modeling | must read lever 46 before running | exact: L46 = 0.716 (BAU 18% → 63%) |
| B6 | Transport | "What if 45% of the distance driven by cars, vans and other light vehicles were electric by 2050?" | lever_x_profile → answer | must say BAU already has 50% · must not propose extra action | exact: below BAU, no lever needed *(v1)* |

## 2 · In-between quantities (T2) — 3 questions

The other half of RQ2: can the agent give a quantity the surrogate does not report? Wording: "as ambitiously as is realistically
possible" (the agent should read it as the top of the lever's range: the most ambitious level in the model runs).

| ID | Sector | Question | Tools | Must / must not | Answer key (runs) |
|---|---|---|---|---|---|
| S50 | Solid waste | "If Uganda captured methane from its landfills as ambitiously as is realistically possible, how much landfill gas would it capture in 2050?" | lever_x_profile → answer | must take the top of the lever's range and say it is the most ambitious level in the model runs · must give a number from the runs, with its source · must not present it as tested on the surrogate | 800,000 t (190,000–1.5 M) *(v1)*; tolerance to fix in advance |
| S3 | Agriculture | "If Uganda promoted soil-friendly farming (less ploughing, keeping crop residues on the field) as ambitiously as is realistically possible, how many hectares of farmland would use these methods in 2050?" | lever_x_profile → answer | same | 3.0 M ha (2.7–3.3) *(v1)* |
| S35 | Transport | "If Uganda moved cars and vans to electricity as ambitiously as is realistically possible, how many kilometres would electric cars and vans travel in 2050?" | lever_x_profile → answer | same | 24 billion vehicle-km (19–30) *(v1)* |

## 3 · Reach an emissions target (T3, controls) — 3 questions

| ID | Sector | Question | Tools | Must / must not | Answer key (surrogate) |
|---|---|---|---|---|---|
| LV2 | Livestock | "How far would we need to cut the methane cattle produce when digesting (what they burp out) to bring livestock emissions 10% below business as usual by 2050?" | exploratory_modeling (try several levels) → answer | must try several levels on the same futures | L23 ≈ 0.36 (median −9.6% at 0.35, −11.8% at 0.40) |
| AG2 | Agriculture + livestock | "Which policies could cut emissions from farming and livestock by a quarter compared with business as usual by 2050?" | output_levers → exploratory_modeling | must pick levers from agriculture, livestock or manure · must test the package | reachable: all 10 of those levers at the top of the range give −34% (−37 to −32); the answer is a smaller set |
| C4b | Waste + wastewater | "Can Uganda get total emissions 20% below business as usual by 2050 using only waste and wastewater policies?" | output_levers → exploratory_modeling → answer | must say it is not reachable, with the best case | infeasible: all waste and wastewater levers at the top give −8.4% (−10.1 to −6.9) |

## 4 · Robustness (RDM component 2) — 3 questions

Thresholds re-set so the policy fails in 20–60% of futures: scenario discovery now has something to find.

| ID | Sector | Question | Tools | Scripted reply (failure threshold) | Answer key (surrogate) |
|---|---|---|---|---|---|
| Q10b | Electricity + forests | "Is a policy with a strong push on renewable electricity and a moderate cut in deforestation robust?" | lever_x_profile → exploratory_modeling → vulnerability_analysis → scenario_discovery | "Count it as a failure if total emissions in 2050 are not at least 5% below business as usual in that same future." | with L7 = 0.8, L15 = 0.6: total −5.5% (−7.2 to −4.1); **fails in 34%** of futures. Must ask for the threshold, not invent it |
| D2b | Electricity + forests | "Does the policy we just tested still work if the economy grows fast?" (asked in the Q10b conversation) | exploratory_modeling (GDP growth restricted to its top third, the rest sampled) → vulnerability_analysis | same as Q10b | fast growth: −4.7% (−5.8 to −3.5); **fails in 66%**. Must restrict GDP to a range, never fix it or treat it as a lever |
| D3b | Diets / livestock | "Is having only 70% of Ugandans eat red meat by 2050 a robust way to cut livestock emissions?" | lever_x_profile → exploratory_modeling → vulnerability_analysis → scenario_discovery | "Count it as a failure if livestock emissions in 2050 are not at least 9% below business as usual in that same future." | exact L25 = 0.682 (BAU 100% → 56%); livestock −9.3% (−10.6 to −8.2); **fails in 39%**; scenario discovery should point to agricultural export volumes (18% / 45% / 55% fail from the low to the high third) |

## 5 · Trade-offs and improving a strategy (RDM component 3) — 2 questions

| ID | Sector | Question | Tools | Must / must not | Answer key |
|---|---|---|---|---|---|
| Q14b | Buildings vs forests | "Is moving homes and businesses to cleaner cooking and heating fuels better than cutting deforestation?" | exploratory_modeling (both, same futures) → trade_off_analysis | must compare on the same futures · must not name a winner | at the top of each range: cooking fuels −3.6% total (−4.5 to −2.8), deforestation −6.6% (−8.2 to −5.4); costs to read from trade_off_analysis |
| N1 | Electricity + forests (new) | Asked after Q10b in the same conversation: "It fails when the economy grows fast. What could we change so it holds up, and does it?" | exploratory_modeling (revised policy, fast growth) → vulnerability_analysis | must re-test the revised policy with the same threshold · must not claim it holds without testing | examples under fast growth: renewables and deforestation both at the top → fails 0%; both at 0.8 → 35%; adding a cut in cattle methane (L23 = 0.5) → 0% |

## 6 · Outside the model (T4) — 3 questions

| ID | Question | Tools | Expected behaviour |
|---|---|---|---|
| B8b | "What if Uganda built three new large hydropower dams by 2040?" | lever_x_profile / output_levers → ask or propose a proxy | says the model has no dams or plant counts; offers the renewable electricity lever as a proxy; no run until the user agrees |
| F2 | "Make Uganda greener." | none until clarified | asks what "greener" means. Scripted reply: "I mean less deforestation and cleaner cooking in homes." Then it is a T0 evaluation |
| F3b | "Slow down economic growth so that emissions fall." | none, or exploratory_modeling with GDP restricted (no lever) | explains GDP growth is an uncertainty, not a policy; may show how emissions differ under slow growth, never as a choice |

---

## Dropped from v1, and why

A1–A4 (look-ups, low value); B1 (asks in 0–1 values), P35i (already settled in pilots; lever 35 over-used),
P50o, P12o, P35o (pilots showed the same null for emission targets; LV2 keeps one), C1, C2 (replaced by AG2), C3
("renewable" ambiguous in a hydro-based system), B5 and E2 (the diet lever moved to D3b), B7 (inconsistent key), D4
(no key), E3 (cost sign still open), F1 ("HBLE" is jargon the agent is never told), B8, F3, Q10, D2, D3, Q14 (reworded
into other sectors: B8b, F3b, Q10b, D2b, D3b, Q14b).

## Still to do after your revision

1. Freeze the wording and the thresholds.
2. Put the questions, scripted replies and must / must-not rules in `backend/rdm/eval/questions.py` and compute
   every key with `bank_reference.py` (the *(v1)* keys included).
3. Fix the numeric tolerance for each key before the run.
