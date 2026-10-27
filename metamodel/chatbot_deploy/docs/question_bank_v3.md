# Question bank — v3 (adjusted for designer bias)

*2026-10-19. Replaces `archive/question_bank_v2.md` (kept for reference). Built from the bias review
(`archive/review_bank_bias.md`): leaked examples removed from the prompt and the tool descriptions, LV2 dropped, five
questions added that were written without knowing their answer (three drawn at random, two realistic and messy),
TO1 added for trade-offs, and every question tagged by how it was made. 26 questions in 24 conversations
(Q10b → D2b → N1 is one conversation).*

*Updated 2026-10-19 after the second bias audit (`archive/review_bank_bias_v3.md`): X1 re-tagged designed, F3b's expected path
fixed, TO1's must-not reworded, the last leaked examples made neutral, the pre-registration completed, and every rule
wired to `failure_modes.py` (`BANK_SPECS` in `backend/rdm/eval/questions.py`).*

*Updated 2026-10-20: the two information tools `lever_x_profile` and `output_levers` were merged into one tool,
`model_network`, which starts from a lever (forward: inputs → variables → categories) or from an output (backward:
the levers and uncertainties that move it). The v1 arms add a weight to every link (Spearman ρ across the runs).
Expected paths below now read "model_network (lever)" or "model_network (output)". No question, key or must/must-not
rule changed; check 1 ("information before the run") now looks for a model_network call that starts from the lever.*

*Updated 2026-10-21: `model_network` was rebuilt on the SISEPUEDE network read from the model code
(`docs/rdm_network_plan.md`): one call gives a node, what it is computed from and what it is used to compute, and
the agent walks the network step by step. v0 gets nodes, attributes and links; v1 adds values from the runs (what
a lever sets at BAU, middle and top of the range; medians and p10–p90 of variables, emissions and categories, by a
lever's thirds and within an uncertainty's third). *(2026-10-26: the two half arms v1_inputs and v1_outputs were
dropped; the experiment compares v0 and v1 only.)* The link weights of
2026-10-20 are gone. **Change to the note on uncertainty ranges below:** the tool's parameters, identical in every
arm, now define an uncertainty's thirds (low 0–⅓, mid ⅓–⅔, high ⅔–1), so the definition is no longer v1-only;
the v1 arms still show values per third. An arm difference in the ranges the agent sets is reported with this
named. No question, key or must/must-not rule changed.*

*Updated 2026-10-21 (keys, before any run of this bank): S50, S3 and S35 are now keyed on the lever's top third
(⅔–1), the cell model_network reports, instead of the lever ≥ 0.9 (a correct answer read from the tool would have
been scored outside the old ranges); X1 accepts 0.50–0.65 (rates halved vs hectares halved); X2's key computed
at 2035; the 24.7% NDC figure confirmed.*

## Pre-registration (written 2026-10-19, before any run of this bank)

- **Where each question comes from (tag):**
  - **dev**: taken or reworded from the pilots, on which the prompt was tuned (10): P50i, P12i, S50, S3, S35, B6,
    Q10b, D2b, Q14b, N1.
  - **designed**: new, but written by the designers after exploring the model (12): AG1, LV1, BLD1, WW1, X1, AG2,
    C4b, D3b, TO1, B8b, F2, F3b. X1 was first tagged blind; its key (0.5) was worked out when it was written and equals
    the literal reading of "halve", so it cannot tell translating from guessing.
  - **blind** (4): H1, H2, H3, whose targets were drawn at random (the person who wrote the wording knew the keys),
    and X2, whose key is computed after the wording is frozen.
  - Results are reported for each tag separately, with the arm effect computed within each. Tags are not pooled.
  - **The four blind items are a check for overfitting, not an estimate of performance.** Even 4 of 4 passes gives
    a 95% interval of about 40–100%. They are one test of in-range translation (H1), two of handling a target beyond
    the range (H2, H3), and one of year and cost handling (X2). They are described next to the dev items (same failure
    modes, or new ones) and used as examples; no rate or arm effect is claimed on them.
- **Robustness thresholds** (Q10b, D2b, D3b) were set by the designers after computing each policy's distribution,
  so that failure is between 20% and 60% of futures (scenario discovery needs failures to explain). They play the
  role of a user's answer and are not elicited policy targets. Q10b and D2b: total emissions at least 5% below BAU;
  D3b: livestock emissions at least 9% below BAU. **Q10b and D2b are scored on process only**, because the user never
  states the lever levels; the failure share is read for the levels the agent chose.
- **Case design:** targets were chosen to produce pre-specified cases: inside the range, beyond it (LV1, H2, H3),
  below BAU (B6), reachable (AG2), not reachable (C4b).
- **T1 lever pool:** T1 questions use levers whose inputs include a share or quantity a non-specialist could state.
  About a third of the levers have none (shown by the random draw); results do not cover them.
- **Random draw (H1–H3):** pool = levers not yet in the bank, outside electricity and transport, with a user-stateable
  field: 2, 8, 21, 22, 26, 44, 45, 47, 48, 49, 51, 52, 53, 54. Draw 3 levers, one field each, target =
  at_0 + u × (at_1 − at_0) with u ~ U(−0.25, 1.25), so a target can land below BAU or beyond the range; numpy
  `default_rng(20261019)`. A first draw from all 28 unused levers gave three fields no user would state; the pool
  was then restricted. Both draws are reported.
- **Tolerances:** exact lever keys ±0.02 (0–1 scale); X1 ±0.1; in-between quantities (S50, S3, S35): inside the
  p10–p90 range of the runs at the top of the lever's range; emission-target and robustness keys: process only.
  For D3b the literal reading (0.70) falls inside the tolerance of the key (0.682); only the literal-translation check
  separates them there.
- **T1 keys depend on the arm.** The input values that make a T1 key computable (business as usual, middle and top
  of the range) are shown only in v1. In v0 the agent can only guess, so a level on the
  key is an *outcome* in those arms (the RQ2 contrast), not a rule it can be expected to follow.
- **Year.** Keys are for 2050. The explored ranges are much wider in 2070 (for example chicken-manure digesters reach
  80%, industrial CO₂ capture 80%), and `model_network` (from a lever) shows both years in the v1 arms. A level read from the 2070
  row counts as off the key. For the targets beyond the range (LV1, H2, H3), "not by 2050; reached later in the runs"
  is a correct answer.
- **Uncertainty ranges and the arms.** In the v1 arms only, `model_network` (from a lever) says "uncertainty low/high =
  bottom/top third of its range" (it explains the values it shows). This is part of the v1 treatment: it may change
  how the agent sets uncertainty ranges (for example "fast growth" → [0.67, 1] rather than [0.5, 1]), so the
  "uncertainty ranges" part of RQ2 may not be null. Any arm difference in ranges is reported with this cause named.
- **Threshold sensitivity (offline).** For Q10b and D3b the failure share is recomputed on the logged ensembles with
  the threshold 2 points stricter and 2 points looser; reported, not scored.
- **Script out of step.** Scripted replies are given in order whenever the agent ends its turn. If the threshold
  reply arrives before the agent asked for one, the conversation is flagged (check 24) and reported, not dropped.
- **Prompt change after the pilots** (logged): examples that matched bank answers were removed from the system
  prompt ("vehicle-km, hectares or tonnes of gas recovered"; "top third for fast growth" → "the upper part of its
  range" → "its lower or its upper part") and from the x_ranges description ("a boom = high GDP growth, [0.67, 1]" →
  "e.g. [0.5, 1]" → "e.g. [0.2, 0.6]"; [0.5, 1] was exactly the lowest range that passes D2b).
- **Rule compliance (RQ1), not capability.** Items whose must rules repeat a prompt rule are reported as rule
  compliance: ask for the threshold (Q10b, D3b), never fix an uncertainty or use it as a lever (D2b, N1, F3b), do not
  name a winner (Q14b, TO1), ask when ambiguous or outside the model (B8b, F2), say the target is beyond the explored
  range (LV1, H2, H3), say where a number comes from (S50, S3, S35), use only the model's years (X2), and call costs
  changes against business as usual (X2, TO1).

## Dry run (2026-10-26) and what it changed

Every bank conversation once in v0 and v1 (58 conversations, US$3.56; `backend/rdm/eval/pilot_runs/bank_dryrun_2026_10_26/`),
to find faults before the full run. **Not part of the results.** Only faults in scoring and tool usability were fixed;
the prompt and the questions were not changed to make the agent pass.

- Check 24 (script out of step): the agent's request for a threshold counts when it is anywhere in the answer ("?" or
  a request naming the threshold / what counts as failure), not only when the answer ends with "?".
- Check 15 (untraced numbers): the counts the harness gives every agent (54 levers, 13 uncertainties, 500 futures by
  default) are traced; lever lists with ranges ("levers 31, 32, 34, 36–42") are references. The agent's own
  calculations stay flagged.
- `model_network`: `third` given with a lever and no uncertainty is no longer an error (the lever is shown for all
  three of its thirds; the reply says so); the parameter description says it.
- Lever and uncertainty ids written "L25" / "X57" are accepted by every tool.
- **Check 20 redefined (Alexa's decision, after the dry run):** exploring levers outside the user's restriction is
  allowed when it rests on real runs. Check 20 now fails when the restricted package (only `allowed_levers`) was never
  tested, or when the answer names levers outside it that were never run. Levers explored with runs are recorded
  (`levers_outside_run`), not scored. Applies to C4b and AG2.
- **Q14b and TO1 keep `trade_off_analysis` as required** (Alexa's decision).
- **Tool descriptions changed (Alexa's decision, after the dry run):** `exploratory_modeling` said "Use it to evaluate
  or compare policies" and nothing said when to use `trade_off_analysis`, so the agent compared alternatives without
  it in Q14b and TO1 (both arms). Now `exploratory_modeling`: "Use it to evaluate policies, and again after revising a
  policy. To compare alternatives, run them in one call, then use trade_off_analysis on its ensemble."
  `trade_off_analysis` starts: "Use it whenever the user compares two or more alternatives." A design fix (the two
  descriptions contradicted the RDM steps), identical in both arms; Q14b and TO1 were re-run once per arm to check.
  Re-run: `trade_off_analysis` used in 1 of 4 conversations (TO1 v1), 0 of 4 before. The system prompt is left as is
  (Alexa's decision): insisting further after seeing these questions would tune the agent to the test.
- Check 14 (names a winner): "X is better on net benefit / in 27% of futures" describes one dimension of a
  trade-off and no longer counts; "can't / cannot" negates. "X is the better option" and "X is better than Y" still
  count.

## Hypothesis questions (v3.1) — pre-registered 2026-10-21, before their keys were computed and before any run

Five questions added on Alexa's request, each to test one hypothesis about agents using these tools. Tag:
**designed** (written by the designers, who know the model); reported apart from the 26 questions above. IDs start
with H and the hypothesis letter.

| ID | Hypothesis | What we expect, v0 vs v1 | Read from the logs (auto) |
|---|---|---|---|
| HA1 | A target in real units of an **in-between variable** (not an emission) needs the network: the surrogate cannot report it. v1 can translate it to a lever level; v0 cannot. | v1: model_network on L35 or the variable, a level near the key, says the quantity is not testable on the surrogate. v0: no level it can justify; says so or guesses. | level set vs key (checks 2–3); model_network visited L35 or the vehicle-km variable (check 25) |
| HB1 | When the levers that matter are **outside the obvious sector**, the catalogue shortcut fails and a **backward walk** from the category finds them. | Both arms: model_network on emissions_livestock (backward). v1 can rank them by effect. | check 25 (visited emissions_livestock); levers named (check 19) |
| HC1 | A condition on the future in **real numbers** ("if GDP is above …") needs the uncertainty's values: v1 can turn it into a range of X57; v0 can only guess the side. | v1: x_ranges on X57 in its top third (lower bound ≥ 0.6). v0: often [0.5, 1] or no range. | x_ranges (check 5, x_side high); the lower bound set is recorded |
| HD1 | For a quantity **several steps** from the lever, the agent walks the whole chain. | Both: model_network from L35 down to transport's electricity use (3 steps). v1 gives the number; v0 says it cannot. | check 25 (visited the electricity-use variable); number of model_network calls |
| HE1 | Where the network has a **gap**, the agent says so and tests on the surrogate what can be tested. | Both: reads L12 (clinker 72% → 60% in v1), sees no chain, runs exploratory_modeling for industrial emissions. | model_network visited L12 (check 25); exploratory_modeling run (check 8) |

**Rules fixed before computing anything:**
- HA1's number: the median of the 2050 electric light-duty vehicle-km in the runs with L35 between 0.5 and 0.6,
  rounded to the nearest billion — a target inside the explored range.
- HC1's number: the median 2050 GDP of the runs with X57 between 0.6 and 0.7 (the start of its top third), rounded
  to the nearest 10 billion USD. The policy is homes and businesses moving to cleaner cooking and heating fuels
  (L30), at the top of its range.
- HD1's key: the change in total electricity used by transport, L35 top third minus bottom third, 2050, from the runs.
- HE1's key: clinker 72% → 60% (L12's inputs, 2050) and the surrogate's industrial-process emissions with L12 at the
  top vs BAU, 2050.
- HB1's key: the levers with a path to emissions_livestock in the network that belong to other sectors.
- New check 25 (`visit`): a model_network call on a node matching each given pattern. It reads the logs only.

**Keys (computed 2026-10-21 by the rules above, after commit 66a813e):**

| ID | Question | Key |
|---|---|---|
| HA1 | "How far would Uganda need to push the shift of cars and vans to electricity for them to drive 21 billion kilometres on electricity in 2050?" | target 21 bn (median of runs with L35 in 0.5–0.6); reached at L35 ≈ 0.62 (accept 0.52–0.72). Runs' median by L35 tenth: 16.7 … 23.9 bn |
| HB1 | "Which policies outside livestock farming itself could also reduce Uganda's livestock emissions?" | levers from other sectors with a path to livestock emissions: L25 healthier diets (−7.4 Mt, low → high third), L15 deforestation (−2.5), L4 crop productivity (+1.2, raises them), L2 supply-chain losses, L17, L18 (small). Must mention diets and deforestation |
| HC1 | "Would moving homes and businesses to cleaner cooking and heating fuels still cut emissions in 2050 if Uganda's economy were larger than about 580 billion dollars by then?" | 580 bn = median GDP 2050 of runs with X57 in 0.6–0.7; GDP by X57 third 444 / 540 / 632 bn → X57 top third. L30 at the top there: total −5.95 Mt (−7.18 to −4.84), −3.3%: yes |
| HD1 | "If cars and vans moved to electricity as far as the model allows, how much more electricity would transport use in 2050?" | 56.0 → 59.9 PJ (L35 bottom vs top third): about +3.8 PJ, +7%, from the runs |
| HE1 | "If cement made in Uganda used as little clinker as the model allows, how much clinker would it contain and how much would emissions from industrial processes fall by 2050?" | clinker 72% → 60%; surrogate, L12 at the top vs BAU: industrial processes −1.4 Mt (−1.75 to −1.0), −12.4% |

## How to read a row

- **Kind:** T1 a quantity a lever sets · T2 an in-between quantity the model computes · T3 an emissions target ·
  T0 nothing to translate · T4 not in the model.
- **Tools:** from the slide-11 guide, in order. **Must / must not:** what `failure_modes.py` scores (spec in
  `BANK_SPECS`). Rules about tool calls are checked exactly from the log; rules marked **(R)** are about what the
  answer says and are read by a small reader model (`--reader`); a number the answer must mention is checked with a
  pattern on the answer text.
- **Levels** go from 0 (business as usual, BAU) to 1 (the most ambitious level explored in the experiment's runs).

## Sectors covered

| Sector | Questions |
|---|---|
| Solid waste | P50i, S50, C4b, TO1, H3 |
| Wastewater | WW1, C4b |
| Industry | P12i, H2 |
| Agriculture | AG1, S3, AG2 |
| Livestock and diets | LV1, AG2, D3b, H1 |
| Buildings (cooking, heating) | BLD1, Q14b, TO1 |
| Transport | B6, S35 |
| Electricity | Q10b, D2b, N1, B8b |
| Forests and land use | Q10b, D2b, N1, Q14b, X1 |
| Whole economy | F3b, X2 |

---

## 1 · Evaluate a policy given in real-world units (T1) — 11 questions

| ID | Tag | Sector | Question (exact wording) | Tools | Must / must not | Answer key |
|---|---|---|---|---|---|---|
| P50i | dev | Solid waste | "What if Uganda's landfills captured 40% of the methane their rubbish gives off (landfill gas) by 2050?" | model_network (lever) → exploratory_modeling | must read lever 50 before running · must not use 0.4 as the level | exact: L50 = 0.688 (BAU 7% → 55%) |
| P12i | dev | Industry | "What if cement made in Uganda used less clinker, its most polluting ingredient, so that clinker was 65% of the cement by 2050 instead of about 72%?" | model_network (lever) → exploratory_modeling | must read lever 12 before running | exact: L12 = 0.583 (BAU 72% → 60%) |
| B6 | dev | Transport | "What if 45% of the distance driven by cars, vans and other light vehicles were electric by 2050?" | model_network (lever) → answer | must say BAU already has 50% · must not run lever 35 above BAU | exact: below BAU, no lever needed |
| AG1 | designed | Agriculture | "What if farmers stopped ploughing on 30% of the land where they grow cereals by 2050, and what would that do to emissions?" | model_network (lever) → exploratory_modeling | must report that agricultural emissions rise slightly · must not claim a cut (R) | exact: L3 = 0.51; agriculture emissions +2.3% (+1.7 to +3.3) |
| LV1 | designed | Livestock | "What if 40% of the manure from dairy cows were used to make biogas by 2050?" | model_network (lever) → (exploratory_modeling at the top of the range) | must say the runs reach at most about 33% · must say the target is beyond the range (R) · must not use 0.4 | beyond the range (lever 20: BAU 0% → 32.7%) |
| BLD1 | designed | Buildings | "What if homes and businesses used a quarter less energy for cooking and heating by 2050?" | model_network (lever) → exploratory_modeling | must read lever 27 before running · must not use 0.25 or 0.75 | exact: L27 = 0.67 (×1 → ×0.627) |
| WW1 | designed | Wastewater | "What if half of rural households' wastewater went to septic tanks by 2050?" | model_network (lever) → exploratory_modeling | must read lever 46 before running | exact: L46 = 0.716 (BAU 18% → 63%) |
| H1 | blind | Livestock | "What if about a quarter of the manure from chickens went into biogas digesters by 2050?" | model_network (lever) → exploratory_modeling | must read lever 22 before running · must not use 0.25 | exact: L22 = 0.573 (BAU 0% → 43.6%) |
| H2 | blind | Industry | "What if half of Uganda's chemical production captured its CO₂ by 2050?" | model_network (lever) → (exploratory_modeling at the top of the range) | must say the runs reach at most about 42% · must say the target is beyond the range (R) · must not use 0.5 · good answer: notes the lever also sets cement, metals and plastic | beyond the range (lever 26: BAU 0% → 41.9%) |
| H3 | blind | Solid waste | "What if each Ugandan threw away a fifth less food by 2050?" | model_network (lever) → (exploratory_modeling at the top of the range) | must say the runs reach at most about 16% less · must say the target is beyond the range (R) · must not use 0.2 or 0.8 | beyond the range (lever 48: ×1 → ×0.836) |
| X1 | designed | Forests | "What if Uganda halved deforestation by 2050?" | model_network (lever) → exploratory_modeling | must read lever 15 · must state its translation (R) | L15 = 0.50–0.65: 0.5 halves the deforestation rates the lever sets; forest loss in hectares halves at about 0.60 (2035) to 0.65 (2050) in the runs. Both readings accepted |

## 2 · In-between quantities (T2) — 3 questions

| ID | Tag | Sector | Question | Tools | Must / must not | Answer key (runs) |
|---|---|---|---|---|---|---|
| S50 | dev | Solid waste | "If Uganda captured methane from its landfills as ambitiously as is realistically possible, how much landfill gas would it capture in 2050?" | model_network (lever) → answer | must read the lever · must say it is the most ambitious level in the runs (R) · must give a number inside the runs' range (R) · must not present it as tested on the surrogate (R) | lever top third (⅔–1): 708,000 t (121,000–1.40 M); lever ≥ 0.9: 805,000 t |
| S3 | dev | Agriculture | "If Uganda promoted soil-friendly farming (less ploughing, keeping crop residues on the field) as ambitiously as is realistically possible, how many hectares of farmland would use these methods in 2050?" | model_network (lever) → answer | same | lever top third: 2.63 M ha (2.18–3.12); lever ≥ 0.9: 2.98 M ha |
| S35 | dev | Transport | "If Uganda moved cars and vans to electricity as ambitiously as is realistically possible, how many kilometres would electric cars and vans travel in 2050?" | model_network (lever) → answer | same | lever top third: 22.6 billion vehicle-km (17.9–28.4); lever ≥ 0.9: 23.9 billion |

## 3 · Reach an emissions target (T3) — 3 questions

| ID | Tag | Sector | Question | Tools | Must / must not | Answer key (surrogate) |
|---|---|---|---|---|---|---|
| AG2 | designed | Agriculture + livestock | "Which policies could cut emissions from farming and livestock by a quarter compared with business as usual by 2050?" | model_network (output) → exploratory_modeling | must pick levers from agriculture, livestock or manure (and diets, which act on livestock) · must test the package | reachable: all 10 such levers at the top give −34% (−37 to −32) |
| C4b | designed | Waste + wastewater | "Can Uganda cut its total emissions by 20% by 2050 using only waste and wastewater policies?" | model_network (output) → exploratory_modeling → answer | must use only waste and wastewater levers · must state the baseline it used (R) · must say it is not reachable, with the best case (R) | not reachable under either baseline: best case −8.4% vs BAU (−10.1 to −6.9); BAU 2050 (168 Mt) is above 2025 (126 Mt) |
| X2 | blind | Whole economy | "Uganda has pledged to cut its emissions 24.7% below business as usual by 2030. Which policies in the model could get us there, and roughly what would they cost?" | model_network (output) → exploratory_modeling | must say 2030 is not a model year (it reports 2025 and 2035) and state what it uses instead (R) · must not present a 2030 number as computed (R) · must call costs changes vs BAU (R) | reachable at 2035 (surrogate, other levers at BAU): every lever at the top −31.0% (−31.6 to −30.3), cost +2.84 bn USD (1.90–3.61); smallest package L30, L29, L9, L15, L23 at the top −26.1% (−26.8 to −25.4), 99% of futures, cost +1.37 bn (1.05–1.64). Model BAU 2035 139 Mt; the NDC's BAU for 2030 is about 143 Mt. 24.7% confirmed: Uganda's updated NDC (2022), 5.9% unconditional + 18.8% conditional |

## 4 · Robustness (RDM component 2) — 3 questions

| ID | Tag | Sector | Question | Tools | Scripted reply (failure threshold) | Answer key |
|---|---|---|---|---|---|---|
| Q10b | dev | Electricity + forests | "Is a policy with a strong push on renewable electricity and a moderate cut in deforestation robust?" | model_network (lever) → exploratory_modeling → vulnerability_analysis → scenario_discovery | "Count it as a failure if total emissions in 2050 are not at least 5% below business as usual in that same future." | process only: must ask for the threshold, not invent it; must run scenario discovery. The failure share for the agent's own levels is recorded. Reference: with L7 = 0.8, L15 = 0.6 it fails in 34% |
| D2b | dev | Electricity + forests | "Does the policy we just tested still work if the economy grows fast?" (in the Q10b conversation) | exploratory_modeling (GDP growth restricted to the upper part of its range, the rest sampled) → vulnerability_analysis | same as Q10b | process only: must restrict GDP growth to its upper part (low end ≥ 0.5), never fix it or treat it as a lever. Reference: fails in 66% |
| D3b | designed | Diets / livestock | "Is having only 70% of Ugandans eat red meat by 2050 a robust way to cut livestock emissions?" | model_network (lever) → exploratory_modeling → vulnerability_analysis → scenario_discovery | "Count it as a failure if livestock emissions in 2050 are not at least 9% below business as usual in that same future." | exact L25 = 0.682; livestock −9.3% (−10.6 to −8.2); fails in 39%; the answer must mention agricultural export volumes, where scenario discovery points |

## 5 · Trade-offs and improving a strategy (RDM component 3) — 3 questions

Costs are scored on caution (changes vs BAU, provisional) rather than on their value.

| ID | Tag | Sector | Question | Tools | Must / must not | Answer key |
|---|---|---|---|---|---|---|
| Q14b | dev | Buildings vs forests | "Is moving homes and businesses to cleaner cooking and heating fuels better than cutting deforestation?" | exploratory_modeling (both, same futures) → trade_off_analysis | must compare on the same futures · must not name a winner | at the top of each range: cooking fuels −3.6% total (−4.5 to −2.8), deforestation −6.6% (−8.2 to −5.4) |
| TO1 | designed | Solid waste vs buildings | "Which cuts more emissions by 2050, and at what cost: landfills capturing 40% of their methane, or homes and businesses using a quarter less energy for cooking and heating?" | model_network (both levers) → exploratory_modeling (both, same futures) → trade_off_analysis | must translate both (L50 ≈ 0.69, L27 ≈ 0.67) · must compare on the same futures · must report how often or by how much one cuts more (share of futures, or overlapping ranges) (R) · must not call one better overall · must call costs changes vs BAU (R) | emissions: −2.3 Mt (−2.9 to −1.6) vs −2.1 Mt (−3.3 to −0.6), close; cost change: +0.11 bn USD (−0.01 to +0.35) vs +0.21 (−0.03 to +0.28); net benefit +0.16 vs −0.08 |
| N1 | dev | Electricity + forests | Asked after D2b in the same conversation: "It fails when the economy grows fast. What could we change so it holds up, and does it?" | exploratory_modeling (revised policy, fast growth) → vulnerability_analysis | must re-test the revised policy (a new run, under fast growth) with the same threshold · must not claim it holds without testing (R) | examples under fast growth: renewables and deforestation both at the top → 0% fail; both at 0.8 → 35% |

## 6 · Outside the model (T4) — 3 questions

| ID | Tag | Question | Tools | Expected behaviour |
|---|---|---|---|---|
| B8b | designed | "What if Uganda built three new large hydropower dams by 2040?" | model_network → ask or propose a proxy | says the model has no dams or plant counts (R); offers the renewable electricity lever as a proxy (R); no run before the user replies |
| F2 | designed | "Make Uganda greener." | none until clarified | asks what "greener" means (R), no run before the user replies. Scripted reply: "I mean less deforestation and cleaner cooking in homes." Then it is a T0 evaluation |
| F3b | designed | "Slow down economic growth so that emissions fall." | none; or, to show the effect of slow growth, exploratory_modeling with a policy (it needs at least one lever) and GDP growth restricted to its lower part | says GDP growth is an uncertainty Uganda does not choose, not a policy (R); never sets GDP growth as a lever. Running is allowed (it is not scored as running before clarifying) |

---

## Changes from v2

- Dropped LV2 (a T3 control with a tuned target; pilot 3 already showed the null).
- Added H1, H2, H3 (random draw), X1, X2 (messy, keys after freezing), TO1 (trade-offs).
- C4b reworded without "below business as usual": the agent must state its baseline.
- Q10b and D2b scored on process only; D2b's must rule no longer assumes "top third".
- Prompt and tool descriptions: leaked examples removed (see pre-registration).

- After the second audit: X1 re-tagged designed; F3b's path fixed (a run needs a lever); TO1's must-not reworded;
  x_ranges example and prompt example made neutral; pre-registration completed; `BANK_SPECS` written.

## Still to do

1. ~~Confirm X1's key against forest loss in hectares; compute X2's key after freezing; check the 24.7% NDC figure.~~ Done 2026-10-21 (rows above).
