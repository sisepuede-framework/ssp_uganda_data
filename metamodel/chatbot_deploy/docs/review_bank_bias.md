# Review: is question bank v2 biased by what we already know about the model?

*Independent review, 2026-10-19. Reviewed: `docs/question_bank_v2.md`, `docs/review_bank_vs_final_rqs.md`,
`docs/rdm_information_layer_plan.md` (pilots 1–4), `backend/rdm/harness/prompt.py`, `backend/rdm/harness/registry.py`,
`backend/rdm/data/tables/run_2026_05_30_lever_inputs.csv`, `backend/rdm/eval/questions.py`. No existing file was
changed. New keys in section 5 come from the lever input table (the exact rule BASE + L × (HBLE − BASE)), 2050.*

---

## Short version

1. **The worry is justified, but most of the bias is fixable cheaply.** About half the bank (10 of 21) comes from
   the pilots, and the prompt was tuned on those pilots. Three prompt examples match bank questions word for word.
2. **Strongest problem: leakage.** The system prompt lists "vehicle-km, hectares or tonnes of gas recovered" as
   examples. These are exactly the quantities in S35, S3 and S50. The prompt and the `x_ranges` description also
   say "top third for fast growth" and "boom = high GDP growth, [0.67, 1]". That is exactly the D2b key.
3. **Second problem: selection.** All 8 T1 levers have a quantity a user can say as a plain share. 4 of the 8 set
   one field (or one value copied across fields). The other 4 are worded so the question names the one field the
   key uses ("land where they grow cereals", "distance driven", "rural households' wastewater"). None of the messy
   levers (renewable electricity: 13 fields; deforestation: 79; heat fuels: 186) is ever asked with a number.
   They appear only in vaguely worded questions, where translation is not scored.
4. **Third problem: tuning.** Every target number and threshold was set after the answer was known. Some of this
   is necessary: scenario discovery needs a policy that fails sometimes. The fix is to say so in the paper and
   add a sensitivity check, not to remove it.
5. **Coverage gaps.** The bank has no number that does not match the model's denominator, no counts or MW, no
   year other than 2050 with a number, no package described in numbers, no baseline ambiguity, no false premise
   and no question about the uncertainties themselves.
6. **Low-effort fix (about 4–5 h in total):** remove the leaked examples (20 min), split the bank into a
   *development* set (pilot-derived) and a *held-out* set, and add 5 held-out questions: 3 drawn at random, 2
   messy and realistic. Pre-register the thresholds and their origin. The bank goes from 21 to 26 (section 5).

---

## 1 · Where the bias comes from

| Source | What happened | Questions affected |
|---|---|---|
| **Reuse of pilot items** | Pilot 3 used the same lever and the same number as P50i (40% landfill gas) and P12i (65% clinker). Pilot 4 used the same scenario as S50, S3 and S35. The D18 prompt paragraph was written between pilots 3 and 4 and tested on S50, S3 and S35 | P50i, P12i, S50, S3, S35 (identical); B6 (lever 35, pilot Q04b); Q10b, D2b, Q14b (pilot Q10, D2 and Q14 moved to other sectors); LV2 (pilot 3 "output target" template) |
| **Leakage in the prompt and tool descriptions** | The examples in the text are the bank's own answers | S50, S3, S35, D2b (strong); B8b, F2, F3b, Q10b, Q14b (rule-level, see section 2) |
| **Selection of levers** | Only levers with a clean, user-sayable field | All 7 T1 questions + D3b |
| **Wording fitted to the field** | The previous review's rule ("keep the number *and what it is a share of*") makes the user speak in the model's denominator | AG1, B6, WW1, P12i, BLD1 |
| **Tuning of numbers and thresholds** | Targets and thresholds were placed after the outcome was computed | LV2 (10%), AG2 (a quarter, max −34%), C4b (20%, max −8.4%), Q10b (5%, re-set after 50% failed everywhere), D3b (9% vs median −9.3%), N1, N2 (proposed) |
| **Framing in model vocabulary** | "below business as usual" (the tool's `reduction_vs_bau_pct`); "as ambitiously as is realistically possible" (the prompt's "most ambitious level explored") | LV2, AG2, C4b, Q10b, D3b; S50, S3, S35 |

### How clean are the T1 levers? (lever input table, 2050)

| Lever in the bank | Fields that change | What the question does |
|---|---|---|
| 50 landfill gas | 1 | clean by construction |
| 12 clinker | 1 | clean by construction |
| 25 red meat | 1 | clean by construction |
| 27 heat demand | 3, all the same scalar | "a quarter less" maps to ×0.75 directly |
| 3 conservation agriculture | 8 (no-till for 6 crop groups, residue burning, residue removal) | names **cereals** only, one of the three groups that reach 59% |
| 46 rural wastewater | 4 treatment paths | names the **septic** path |
| 35 light-duty fuel | 4 fuel shares | names **electric share of distance**, not of the fleet |
| 20 cattle and pig manure | 22 | names **dairy, digester** (chosen to exceed the range) |

- Across all 54 levers, 16 change exactly one field in 2050. About two thirds have a quantity a user could state
  as a share. The other third are emission factors, efficiency factors, land transition probabilities or
  "unknown" units.
- **Evidence from a random draw.** I drew 3 levers at random (seed 20261019) from the 28 not yet used, leaving out
  electricity and transport. All three had **no quantity a user would say**:
  - N₂O per unit of GDP in "other product manufacturing";
  - pasture sequestration per hectare (silvopasture);
  - biomass heating efficiency.
- **What this means:** RQ2's translation result generalises to *levers with a sayable quantity*, not to "the
  model". The paper must say so. This restriction is partly a property of the model, not only of the designers.
  Writing it down is the fix.

---

## 2 · Question by question

Bias types: **a** selection · **b** tuning · **c** leakage · **d** reuse · **e** framing · **f** coverage (section 3).
**Severity** means how much the item overstates the agent's ability on an unseen question of the same kind.

| ID | Types | Severity | Why | Fix |
|---|---|---|---|---|
| P50i | a, d | **High** | Identical to pilot 3, where the input-value effect was first seen. Single-field lever | Move to the dev set |
| P12i | a, d | **High** | Identical to pilot 3. Single field. The wording gives the BAU value ("about 72%") | Dev set. Optional: drop "instead of about 72%" |
| AG1 | a, b, e | Medium | "land where they grow cereals" is the field name in plain words. Chosen partly because the sign is known to be surprising (+2.3%) | Keep. Declare it a known-answer trap. Check the sign in the raw runs |
| LV1 | a, b | Medium | Built to exceed the range (40% vs a max of 32.7%), using a known maximum | Keep. The random draw (H2, H3) adds unplanned out-of-range cases |
| BLD1 | a | Low–medium | "A quarter less" maps exactly onto one scalar | Keep |
| WW1 | a, e | Low–medium | The wording names the exact treatment path | Keep |
| B6 | a, b, d | Medium | Number placed just below a BAU value the designers knew. Lever 35 has been used since pilot 1 | Dev set. Optional: reword to a fleet share (section 5) |
| S50, S3, S35 | c, d, e | **High** | The prompt names their exact quantities. Identical to pilot 4. "as ambitiously as is realistically possible" points to the top of the range | Remove the prompt examples. Dev set |
| LV2 | b, d, e | Medium | Template from pilot 3. The 10% target was placed inside the reachable range. Pilot 3 already showed a null in every arm | **Drop** (AG2 and C4b keep T3) |
| AG2 | b, e | Low | "A quarter" chosen knowing the max is −34% (reachable) | Keep. Report it as the "reachable" case |
| C4b | b, e | Low | 20% chosen knowing the max is −8.4% (unreachable). "Below business as usual" is the tool's word | Reword without "below BAU" (section 5) |
| Q10b | b, d | **High** for the key, low for the process | The 5% threshold was re-tuned for L7 = 0.8, L15 = 0.6, levels the user never states. If the agent reads "strong" as 1.0, the 34% key no longer applies | Score the process only. Record the agent's own failure rate |
| D2b | c, d | **High** | The prompt and the tool give the exact translation ("fast growth" → top third, [0.67, 1]) | Remove or replace the example |
| D3b | a, b | Medium | Single-field lever. The 9% threshold sits at the policy's median, so it fails about 40% by construction | Keep. Add a threshold sensitivity check |
| Q14b | d | Low | Pilot Q14 structure. Vague levels | Keep, process scoring |
| N1 | b, d | Medium | The example fixes come from the designers' own runs | Keep. Score only "re-tested, same threshold" |
| B8b | c (rule) | Low | The prompt says "outside the model (for example … specific projects)" | Keep. Note it is rule compliance |
| F2 | c (rule) | Low | The prompt says "If it is ambiguous, ask before running" | Keep (it is the system's rule) |
| F3b | c (rule) | Low | The prompt says uncertainties are "never set to one value" | Keep |

**Clean or nearly clean:** BLD1, WW1, AG2, Q14b, F2, F3b, B8b. In the last three, the prompt states a rule rather
than an example.

---

## 3 · Coverage gaps: real questions the bank avoids

| Kind of question | In the bank? | Why it matters |
|---|---|---|
| Number in a unit the model does not use (counts of vehicles, MW, number of dams) | Only B8b, without a number | Most real asks are like this. It tests whether the agent says it cannot translate, instead of guessing |
| Share with the wrong denominator ("45% of cars" vs share of distance) | No (the rule avoided it) | This is the main real-world translation error |
| A messy lever with a number ("halve deforestation") | No | It tests RQ2 where translation is hard |
| A package in words with numbers (3 levers at once) | No | Real policies are packages |
| A year other than 2050 with a number (2030 NDC) | No (B8b says 2040, but has no number) | The model reports 2025, 2035, 2040, 2050…; 2030 is not a model year |
| Baseline ambiguity ("cut 20%": vs today or vs BAU?) | No, every target says "below BAU" | The wording does the translation for the agent |
| A false premise | No | It tests correction against the model's data |
| Costs first ("cheapest way to…") | No | Costs are provisional (P8), so score caution only |
| Questions about the uncertainties themselves | Only F3b | RQ2 mentions uncertainty ranges |
| A user who changes their mind, or conflicting goals | No | Multi-turn robustness. Nice to have |

---

## 4 · What tuning is legitimate, and how to report it

| Tuning | Necessary? | Honest wording for the paper |
|---|---|---|
| Robustness thresholds placed so the policy fails in 20–60% of futures (Q10b, D2b, D3b) | **Yes.** With 0% or 100% failure, scenario discovery has nothing to find | "Failure thresholds were set by the designers after computing each policy's distribution, so that failure was between 20% and 60% of futures. They play the role of a user's answer and are not elicited policy targets. Results at a second threshold are in the appendix." |
| One reachable and one unreachable target (AG2, C4b), one beyond-range and one below-BAU input (LV1, B6) | **Yes.** It is case design: each case tests a different behaviour | "Targets were chosen to produce pre-specified cases (inside the range, beyond it, below BAU, reachable, unreachable)." |
| Only levers with a user-sayable quantity in T1 | **Partly.** About a third of levers have none (shown by the random draw) | "T1 questions were drawn from the N levers whose inputs include a share or quantity a non-specialist could state; results do not cover the others." List the pool |
| Wording that names the field's denominator | **No.** It does the translation for the agent | Keep these in the dev set and add held-out items with mismatched denominators |
| Prompt examples that equal bank answers | **No** | Remove before the run. If they stay, report the affected items separately as "prompt-exemplified" |
| Prompt tuned on pilot questions | Normal in development, but it biases those items | "Questions used during development (pilots 1–4) are reported separately from held-out questions." |
| Prompt rules that equal must / must-not rules (do not invent a threshold, do not name a winner, never fix an X, ask when ambiguous) | **Yes.** The system *is* the prompt plus the agent | Call these items "rule compliance" in RQ1, not "capability" |

---

## 5 · Fixes, prioritised

### Must do before the run

| # | Fix | Effort |
|---|---|---|
| F1 | **Remove the leaked examples.** In `prompt.py`: (1) replace "in-between quantities such as vehicle-km, hectares or tonnes of gas recovered" with "in-between quantities (anything the model computes between the inputs a lever sets and the emissions)"; (2) replace "(for example the top third for "fast growth")" with a generic "(for example only the upper part of its range)". In `registry.py`, `x_ranges`: drop "(e.g. a boom = high GDP growth, its top third: [0.67, 1])" and keep "e.g. [0.5, 1]". Log it as a post-pilot prompt change; rerun tests and the smoke test | 20 min + smoke test |
| F2 | **Tag every item `dev` or `held_out`** in `questions.py`. Dev: P50i, P12i, S50, S3, S35, B6, Q10b, D2b, Q14b, N1. Report the two sets separately, with the arm effect computed in each | 15 min |
| F3 | **Add the 5 held-out questions H1–H3 and X1–X2 below.** For X1–X2, freeze the wording first, then compute the keys | 2 h (keys with `bank_reference.py`) |
| F4 | **Pre-register** (one dated paragraph in the bank, before any run): the threshold rule (20–60% failure) and the value chosen; the T1 lever pool; the tolerances; the dev / held-out split; the random-draw procedure and seed | 30 min |
| F5 | **Q10b:** score the process, and record the failure rate *for the levels the agent chose* (the tool returns it). Never score against the 34% | 0 (scoring rule) |
| F6 | **Drop LV2** (a T3 control with a tuned target; pilot 3 already showed the null; AG2 and C4b cover T3) | 1 min |

### Nice to have

| # | Fix | Effort |
|---|---|---|
| N1 | **Blind rewording.** A colleague who has not seen the results rewrites H1–H3, X1 and X2 in their own words, given only the lever name and the target. Recompute the keys from the rule afterwards. A model given only the same two facts is a cheaper substitute | 30 min of their time |
| N2 | **Threshold sensitivity, offline.** Rerun `vulnerability_analysis` on the logged ensembles of Q10b and D3b at a second threshold (e.g. 3% and 12%). Report whether the scenario-discovery driver stays the same. No new conversations are needed | 30 min |
| N3 | Reword C4b without "below BAU" (below). It tests whether the agent states its baseline. The key stays "not reachable" if BAU 2050 total ≥ 2025 total (check this with one line first) | 10 min |
| N4 | Swap-ins for any item you want to replace: X3 (unit confusion), X4 (the uncertainties themselves), or a B6 reworded to a fleet share | 30 min each |
| N5 | A change-of-mind turn in the Q14b conversation: "Actually, leave deforestation aside. Compare cleaner cooking fuels with using a quarter less energy for cooking and heating." | 20 min |
| N6 | Leave out the proposed N2 (livestock productivity "trap"). It is built from a result already known (+productivity → 94% fail). If you keep it, put it in the dev set | — |

---

## 6 · Recommended new and reworded questions (exact wording)

### Held-out, drawn at random (H1–H3)

**Procedure** (state it in the paper). Pool: levers not yet in the bank, outside electricity and transport, whose
inputs include a share or quantity a user can state (levers 2, 8, 21, 22, 26, 44, 45, 47, 48, 49, 51, 52, 53, 54).
Draw 3 levers; draw one of each lever's fields; draw the target as at_0 + u × (at_1 − at_0) with u ~ U(−0.25,
1.25), so the target can land below BAU or beyond the range. Seed 20261019 (numpy `default_rng`).

**Disclosure:** I wrote this pool after a first draw from all 28 unused levers gave three fields no user would
state (see section 1). Report both draws.

| ID | Sector | Question | Drawn | Key (exact rule, 2050) |
|---|---|---|---|---|
| H1 | Livestock | "What if about a quarter of the manure from chickens went into biogas digesters by 2050?" | L22, `frac_lvst_mm_chickens_anaerobic_digester`, u = 0.55 | **L22 = 0.573** (BAU 0% → 43.6%). Must read lever 22 before running; must not use 0.25 |
| H2 | Industry | "What if half of Uganda's chemical production captured its CO₂ by 2050?" | L26, `frac_ippu_production_with_co2_capture_chemicals`, u = 1.19 | **Beyond the range** (BAU 0% → 41.9%). Must say so and offer the top of the range. Must not test above it. Note: the lever sets the same share for cement, metals and plastic too. A good answer says so |
| H3 | Solid waste | "What if each Ugandan threw away a fifth less food by 2050?" | L48, food waste per person (×1 → ×0.836), u = 1.16 | **Beyond the range** (the most explored is 16.4% less). Same must rules as H2 |

- The draw gives 2 of 3 out-of-range targets. The designed bank has 1 of 7.
- **Finding:** the designed set under-tests boundary handling.

### Held-out, messy and realistic (X1–X2), keys computed after the wording is frozen

| ID | Sector | Question | What it tests | Expected behaviour / provisional key |
|---|---|---|---|---|
| X1 | Forests | "What if Uganda halved deforestation by 2050?" | T1 on a messy lever (79 land-transition fields) | Must read lever 15 and state the translation. Provisional key: **L15 ≈ 0.5**, because the forest-to-other transitions fall linearly to about 0 at L = 1. Confirm against forest loss in hectares in the runs before freezing; tolerance ±0.1 |
| X2 | Cross-sector | "Uganda has pledged to cut its emissions 24.7% below business as usual by 2030. Which policies in the model could get us there, and roughly what would they cost?" | A year that is not a model year; a whole-economy target; costs first | Must say 2030 is not a model year (it reports 2025 and 2035) and state what it uses instead. Must not present a 2030 number as computed. Uses output_levers → exploratory_modeling. Calls costs provisional. Key: feasibility at 2035, computed after freezing. (Check the 24.7% figure against Uganda's 2022 NDC) |

### Optional swap-ins

| ID | Sector | Question | Expected behaviour |
|---|---|---|---|
| X3 | Transport | "What if Uganda had 200,000 electric boda bodas on the road by 2035?" | Must say the model works with the electric share of motorcycle travel, not with numbers of bikes. Must ask, or state an assumption, before running. Must not convert silently |
| X4 | Uncertainty | "What could happen outside our control that would push Uganda's emissions much higher by 2050?" | Must treat these as uncertainties (output_levers on total emissions, or a BAU ensemble), report ranges and use no forecast language |
| B6′ | Transport | "What if 45% of the cars and vans on Uganda's roads were electric by 2050?" | Must say the model uses the share of distance driven, not of the fleet, and state the assumption. Key under that assumption is unchanged (below BAU) |

### Rewording (no change in count)

| ID | Now | Proposed |
|---|---|---|
| C4b | "Can Uganda get total emissions 20% below business as usual by 2050 using only waste and wastewater policies?" | "Can Uganda cut its total emissions by 20% by 2050 using only waste and wastewater policies?" Must state the baseline it used. Key: not reachable under either baseline (check that BAU 2050 total ≥ 2025 total) |

### Resulting bank: 26 questions

21 − LV2 + TO1 (proposed in the previous review) + H1, H2, H3 + X1, X2 = **26**.

| Sector | v2 | After |
|---|---|---|
| Solid waste | 3 | 5 (+TO1, +H3) |
| Wastewater | 2 | 2 |
| Industry | 1 | 2 (+H2) |
| Agriculture | 3 | 3 |
| Livestock and diets | 4 | 4 (−LV2, +H1) |
| Buildings | 2 | 3 (+TO1) |
| Transport | 2 | 2 |
| Electricity | 4 | 4 |
| Forests and land use | 4 | 5 (+X1) |
| Economy / cross-sector | 1 | 2 (+X2) |

- Electricity and transport are not increased.
- Solid waste rises to 5 because the random draw picked food waste.
- Do not swap H3 for another sector after seeing it. That would undo the point of the draw.
- If 26 is too many, drop TO1 rather than a held-out item.
- **Dev / held-out split:** 10 dev items, 16 held-out. Among the held-out items, 5 were written without prior
  knowledge of the outcome: H1–H3 by procedure, X1–X2 by design with keys computed afterwards.
