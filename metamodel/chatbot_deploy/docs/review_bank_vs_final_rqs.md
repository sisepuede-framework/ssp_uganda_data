# Review: question bank v2 against the final research questions

*Independent review, 2026-10-19. Reviewed: `docs/question_bank_v2.md`, the two earlier reviews
(`review_questions_vs_rqs.md`, `review_rqs_v2.md`), `docs/rdm_information_layer_plan.md` (pilots 1–4, Update
2026-10-19), `backend/rdm/harness/prompt.py`, `backend/rdm/harness/registry.py`, `backend/rdm/tools/information.py`,
`backend/rdm/eval/bank_reference.py`. New numbers were computed with the retrained surrogate (2050, other levers
at 0, 1,000 futures, the same futures as `bank_reference.py`). No existing file was changed.*

The research questions are taken as final and are not reworded here.

- **RQ1:** How do we integrate a surrogate model of SISEPUEDE with an AI agent so that non-technical users can
  explore policy questions through the three components of RDM (exploratory modeling, vulnerability analysis,
  trade-off analysis), and how do we evaluate such a system?
- **RQ2:** What is the impact of the type of information we give the agent about the model (how its variables
  are related, or also their values) on (a) its use of the available tools and (b) the policy levels and
  uncertainty ranges it sets?

---

## Short version

1. **The D3b "+10%" result is a computation error, not a model result.** It is reproduced exactly when business
   as usual and the policy are swapped in the percentage formula. The correct numbers are in section 0.
   `bank_reference.py` itself is correct. Population growth barely changes D3b. The uncertainty that drives its
   failures is **agricultural export volumes**.
2. **RQ1 coverage is lopsided.** 16 of 21 questions are exploratory modeling, 3 are vulnerability analysis and
   2 are trade-off analysis. Trade-off analysis (component 3) is under-covered. Its cost side cannot be scored
   yet, because the cost signs are still open (P8) and the cost intervals cross zero.
3. **"Non-technical users":** about six questions use specialist words. Most can be made plainer without
   changing the answer key. The rule is to keep the number and its unit. A rewording that drops the number
   turns a T1 question into a T0 question, and then it no longer tests RQ2.
4. **"How do we evaluate":** the must / must-not scoring is the right core, but it is not yet a method. It
   still needs fixed tolerances, a general rubric, a list of failure modes, a second labeller with an agreement
   figure, and a fixed key for Q10b and Q14b, whose policy levels are left vague.
5. **RQ2 after "responses" was removed:**
   - T2 questions (S50, S3, S35) no longer measure an RQ2 outcome through the number they report. They still
     measure **tool use**: without output values, the agent ran the surrogate as a substitute. Keep them, and
     move the reported number to the RQ1 evaluation.
   - **Uncertainty ranges cannot differ between arms as the bank stands.** Every X question (D2b, N1, F3b) is
     qualitative ("fast growth"), and the system prompt translates that ("top third") in every arm. No arm
     gives X in real units. Declare this an expected null, or add a minimal X-units block to the value arms
     (data for population and GDP already exist).
6. **Changes:** 2 additions, 1 relocation, about 7 rewordings and a scoring sheet. The bank goes from 21 to 23
   questions with the sector balance kept (section 5).

---

## 0 · The D3b population check (done first, as asked)

**Verdict: computation error.** The computation that produced the reported numbers swapped business as usual
(BAU) and the policy. It computed (BAU − policy) / policy instead of (policy − BAU) / |BAU|. Recomputing it the
wrong way gives **+10.04% (+8.85 to +11.60)**, the reported figure to the decimal. Because every value then
comes out positive, the test "not at least 9% below BAU" fails in 100% of futures. That explains both odd
results. `run_policy` and `_futures` in `bank_reference.py` restrict the range correctly.

Correct numbers for D3b (healthier diets, L25 = 0.682; livestock emissions in 2050; failure = not at least 9%
below BAU):

| Futures | Change vs BAU, median (p10 to p90) | Fails |
|---|---|---|
| All 13 uncertainties sampled | −9.3% (−10.6 to −8.2) | 39% |
| Population growth, bottom third | −9.2% (−10.6 to −7.7) | 44% |
| Population growth, middle third | −9.6% (−10.9 to −8.7) | 25% |
| Population growth, top third | −9.1% (−10.4 to −8.1) | 46% |
| **Agricultural export volumes, bottom / middle / top third** | — | **18% / 45% / 55%** |

- Population barely matters for D3b. The U-shape is small and probably surrogate noise (the BAU value jumps at
  the very low end of population).
- Scenario discovery on D3b should point to **agricultural export volumes**, and that should be the answer key.
- The same check on Q10b (renewables 0.8 + deforestation 0.6; failure = less than 5% below BAU) shows a clear
  driver: GDP growth fails 3% / 28% / 69% from the bottom to the top third, and population 9% / 39% / 55%. So
  population is a real driver for Q10b, not for D3b.

---

## 1 · RQ1: coverage of the three RDM components

Each question is counted once, under the deepest component it has to reach.

| Component | Questions | Count |
|---|---|---|
| 1 · Exploratory modeling / stress testing | P50i, P12i, AG1, LV1, BLD1, WW1, B6, S50, S3, S35, LV2, AG2, C4b, B8b, F2, F3b | 16 |
| 2 · Vulnerability analysis + scenario discovery | Q10b, D2b, D3b (scenario discovery expected in Q10b and D3b only) | 3 |
| 3 · Trade-off analysis + strategy improvement | Q14b (trade-off), N1 (strategy improvement) | 2 |

**Findings**

- **Component 1 is inflated.** Six of the 16 (B6, LV1, S50, S3, S35 and partly F2) can be answered without
  running the surrogate across futures. They test translation and look-up, not stress testing. That is fine
  for RQ2, but RQ1 should not count them as exploratory modeling.
- **Component 2 is thin but workable.** Q10b fails in 34% of futures, D2b in 66% and D3b in 39%, so every one
  can fail and scenario discovery has something to find. Q10b, D2b and N1 all use the same electricity +
  forests policy, so component 2/3 evidence rests mostly on one policy.
- **Component 3 is under-covered: 2 questions, one per sub-step.** With 3 repetitions that is 6 conversations
  per arm, which is illustrative only.
- **Do the cost signs (P8) block component 3?** Partly. Today's numbers (2050, change vs BAU, billion USD):

  | Policy | Cost change, median (p10 to p90) | Benefit change |
  |---|---|---|
  | 40% landfill gas recovered (L50 = 0.688) | +0.11 (−0.01 to +0.35) | +0.25 |
  | Heat demand a quarter lower (L27 = 0.67) | +0.21 (−0.03 to +0.28) | +0.02 |
  | Deforestation at the top of its range (L15 = 1) | −0.05 (−0.16 to +0.01) | **−2.64** |

  - Both cost intervals cross zero, so the sign is not settled.
  - Cutting deforestation shows a large *negative* benefit, and landfill gas capture shows a *higher* fuel
    cost. Both point the opposite way from what one would expect and should be checked by the team (P8).
  - **What still works:** comparing two policies on emissions in the same futures; the process (calls
    trade_off_analysis, uses the same futures, names no winner); and strategy improvement, which needs no
    costs.
  - **What is blocked:** any answer key or claim that involves a cost figure.
  - **Until P8 is closed:** score component 3 on emissions and process only. Have the agent say that cost
    figures are provisional; the same note in every arm keeps the arms comparable.

---

## 2 · RQ1: wording a non-technical user would not use

The rule is to keep the number **and what it is a share of**. If either changes, the key changes.

| ID | Current wording (problem words in bold) | Plainer wording, same key | Key or label at risk? |
|---|---|---|---|
| P12i | "What if the **clinker share** of cement fell to 65% by 2050?" | "What if cement made in Uganda used less clinker, its most polluting ingredient, so that clinker was 65% of the cement instead of about 72% today?" | Keep "65% of the cement". "Cement plants cut emissions" alone would become T0 and lose the RQ2 signal |
| AG1 | "30% of cereal farmland under **no-till**" | "What if farmers stopped ploughing on 30% of the land where they grow cereals by 2050, and what would that do to emissions?" | Same key (L3 = 0.51). Do not say "conservation agriculture on 30% of farms": share of farms ≠ share of cereal area |
| LV1 | "40% of dairy cattle manure went to **biogas digesters**" | "What if 40% of the manure from dairy cows were used to make biogas by 2050?" | Same key. Minor: biogas digesters are familiar in Uganda |
| B6 | "45% of **light-duty vehicle-km** were electric" | "What if 45% of the distance driven by cars, vans and other light vehicles were electric by 2050?" | Same key **only if "distance driven" stays**. "45% of cars electric" is a share of the fleet, a different quantity, and the key would change. Leave out motorbikes (a separate lever, 38) |
| S35 | "how much **electric light-duty travel**" | "… how many kilometres would electric cars and vans travel in Uganda in 2050?" | Same key (vehicle-km) |
| S3 | "If **conservation agriculture** went as far as the model allows, how much cropland would be under **improved practices**" | "If the push for soil-friendly farming (less ploughing, cover crops) went as far as the model allows, how many hectares of farmland would use these methods in 2050?" | Same key (area of improved cropland) |
| WW1 | "half of rural households' wastewater went to **septic tanks**" | Keep as is. "Septic tanks" is everyday language | — |
| P50i, S50 | "**landfill gas**" | "methane captured from rubbish dumps (landfill gas)" | Same key |
| LV2 | "methane from **cattle digestion**" | "methane that cattle burp out" (optional) | Same key |
| Q10b | "a **strong push** … and a **moderate cut**" | Plain already, **but vague**: see section 3 | The key assumes L7 = 0.8 and L15 = 0.6, which the user never says |
| D2b | "**that same kind of policy**" | "Does the policy we just tested still work if the economy grows fast?" (asked in the same conversation as Q10b) | Must run in the Q10b conversation, otherwise "that" has nothing to refer to |

Not jargon, but worth knowing: "as far as the model allows" (S50, S3, S35) is honest, though no user says it. It
stays, because the alternative ("maximum") was misleading.

---

## 3 · RQ1: is the bank + must/must-not a usable evaluation method?

**What it has:** a fixed question set; a translation label per question; expected tools; one or two
must / must-not rules; and keys computed from the model, not from opinion. Scoring actions rather than tool
order is the right choice. Together that is the skeleton of a method.

**What is missing before it can be called "a way to evaluate such a system":**

| Gap | Why it matters | Minimal fix |
|---|---|---|
| Tolerances not fixed (the bank itself lists this as to do) | Without them, "correct level" is decided after seeing results | Before the run: lever levels ±0.03; T2 numbers within the runs' p10 to p90; X ranges "top third" = lower bound 0.6–0.75, upper bound 1 |
| Q10b and Q14b have no fixed key: their levels are vague words | Different agents pick different levels, so pass/fail is not comparable | Score the process (threshold asked; same futures; vulnerability_analysis and scenario_discovery called; no winner named) and record the levels chosen as data. Or put numbers in the wording |
| No general rubric across questions | Must / must-not catches 1–2 behaviours per question, not the system's general rules | One checklist per answer: states its translation; gives a range, not one number; no forecast language; gives the source of each number; says when something was not tested; names no winner; asks before running when unclear |
| No failure-mode list | Results become anecdotes | Code each failure from a fixed list (below), named before the run |
| One labeller (reader model + hand check) | No agreement figure, so a reviewer cannot judge reliability | A second human labels a 20% random sample; report agreement (Cohen's κ) per rule |
| Pilot questions are reused (P50i, P12i, S50, S3, S35); the prompt was tuned on them (D18) | Optimistic bias on those items | Flag them in results, or report the 16 held-out questions separately |
| 3 repetitions | Wide intervals; component 3 has n = 2 questions | Report rates with intervals; present components 2–3 as illustrative |
| Surrogate accuracy is not part of the bank | "Evaluate the system" includes whether its numbers are right | One line in methods: test R² (median 0.994; 15 targets < 0.8) and which categories are weak |

**Failure modes, from the pilots and the rules:**

1. Took the user's number as the lever level ("40%" → 0.4).
2. Bracketed or guessed instead of translating.
3. Set a level outside the explored range.
4. Fixed an uncertainty to one value, or treated it as a lever.
5. Invented a failure threshold.
6. Reported a number with no source, or as tested when it was not.
7. Named a winner.
8. Used forecast language.
9. Ran before clarifying an ambiguous or out-of-model question.
10. Claimed a revised policy works without re-testing it.
11. Asserted a mechanism that was not checked (the saved idea "verify why-claims").

---

## 4 · RQ2: which outcome each question measures

(a) = tool use; (b) = lever levels / uncertainty ranges set. "Arms differ?" = whether the information arms are
expected to give different results.

| ID | Kind | (a) tool use | (b) levels / ranges | Arms differ? | Note |
|---|---|---|---|---|---|
| P50i, P12i, BLD1, WW1 | T1 | reads the lever before running | **lever level** (exact key) | **Yes** (input values) | Core of RQ2; pilots: 100% vs 38% committed, error 0.003 vs 0.15 |
| AG1 | T1 | reads lever 3 | level 0.51 | Yes | "Emissions rise" is a response → RQ1 |
| LV1 | T1 | reads lever 20; runs only at the top | level capped at the top of the range | Yes | Saying "beyond range" is a response → RQ1 |
| B6 | T1 | reads lever 35; **does not run** | level = 0 (none needed) | Yes | Not running is itself a tool-use outcome |
| D3b | T1 + comp. 2 | VA + SD | level 0.682 | Yes (level); SD driver no | The only question carrying a translation into component 2 |
| **S50, S3, S35** | T2 | **yes**: answers from the information tool vs runs the surrogate as a substitute | none | Yes, on (a) | See below |
| LV2 | T3 | sweeps several levels | level ≈ 0.36 | No (control) | Expected null, as in pilot 3 |
| AG2 | T3 | output_levers → package | lever choice + levels | Weak (v1 ranks levers) | |
| C4b | T3 | output_levers → package | lever choice | No | "Not reachable" is a response → RQ1 |
| Q10b | comp. 2 | VA + SD | levels from vague words; threshold asked | No | |
| **D2b** | comp. 2 | VA | **X range** (GDP top third) | **No: translated in the prompt** | |
| **N1** | comp. 3 | re-tests | revised levels; **X range** reused | No | |
| Q14b | comp. 3 | same futures + trade_off_analysis | levels from vague words | No | |
| B8b | T4 | no run until agreed | proxy lever | No | |
| F2 | T4 | no tool before clarifying | — | No | |
| **F3b** | T4 | — | **X range, never a lever** | No | |

**Arms are expected to differ on 11 of 21:** 8 on levels (7 T1 + D3b) and 3 on tool use (T2). The other 10 are
controls. That proportion is fine if the paper says so.

### T2 (S50, S3, S35) now that "responses" is out of RQ2

- What these questions show (pilot 4) is mostly a **reported number**, which is a response. That part now
  belongs to the **RQ1 evaluation**: is the answer correct, and is its source stated?
- They still measure **(a) tool use**. Without output values the agent "said the quantity is not available …
  then tested what they could" (pilot 4). It ran exploratory_modeling as a substitute. With output values it
  answered from lever_x_profile. That is a routing difference.
- **Recommendation:** keep all three, and change their scoring so that RQ2 reads the routing:
  - (a) did it run exploratory_modeling as a substitute?
  - (a) did it call lever_x_profile at the right year?
  - The number goes to the RQ1 scoresheet.
- S35 is one of only two transport questions, so dropping it would not help the sector balance anyway.

### Uncertainty ranges: testable or null by design?

**What each arm gives about uncertainties (from `information.py`):**

- **lever_x_profile:** in every arm, only the uncertainty's id and name, and a yes/no flag ("uncertainty also
  moves this"). In the arms that show outputs, it adds the **medians of the lever's outputs when X is in its
  low vs high third**. That is how X affects outputs, not what X *is* in real units.
- **output_levers:** in v0, the names of the uncertainties that move an output. In the value arms, the median
  output at the low end (0–0.2) vs the high end (0.8–1) of each uncertainty.
- **country_context:** baseline population and GDP text, the same in all arms.
- **System prompt and tool schema, identical in all arms:** "restricted … for example the top third for 'fast
  growth'" and "a boom = high GDP growth, [0.7, 1]". **The qualitative translation of X is handed out in every
  arm.**

**Consequence:** D2b, N1 and F3b use qualitative X words, so the arms **cannot** differ on the ranges set. This
part of RQ2 is a null by design. It is not a finding.

**An indirect route exists, but no agent will find it.** Calling output_levers on the variable
`population_gnrl_total` in a value arm returns population at the low vs high end of X60: **77.4 M vs 87.8 M in
2050**. The same call on `gdp_per_capita_usd` returns 5,139 vs 7,837 USD for X57. But:

- the unit shows as "unknown";
- the agent must already know the field name (the error message lists only the 23 categories);
- **nothing exists for fuel prices** (X56) or the 10 other uncertainties.

**Options:**

| Option | Effort | What RQ2 can then say |
|---|---|---|
| A · Accept as an expected null (minimum) | none | "Uncertainty ranges were translated identically in all arms because the prompt provides the qualitative mapping; arms could not differ by design." Score X ranges in the RQ1 evaluation (range, not a fixed value; not treated as a lever) |
| B · Add an X-units block to the value arms of lever_x_profile, for X57 and X60 only (population total and GDP per capita at the low / middle / high third; the data are already in the runs) + **one** real-unit question (below) | ~1–2 h + recompute | A real test on ranges for 2 of 13 uncertainties. Fuel prices and the rest remain future work (P8) |
| C · Real units for all 13 X (P8) | needs the team | Full test; not before this run |

**Recommendation: A as the default, with B only if it can be done before the freeze.** Write the null into the
methods now. If B is done, add one question that is otherwise identical to Q10b:

> "Is that policy still robust if Uganda's population reaches about 88 million by 2050?"

- Expected range: population around [0.8, 1] or the top third.
- Key: population top third → Q10b fails in 55% of futures (vs 34% overall).
- v0 should bracket or guess; the value arms should translate. That is the range analogue of the T1 questions.

---

## 5 · Recommended changes (21 → 23 questions)

### Must do before the run

| # | Change | Why |
|---|---|---|
| M1 | **Correct D3b's scenario-discovery key** to "agricultural export volumes" (18% / 45% / 55% failing from low to high). Discard the "+10% under fast population growth" numbers | Section 0 |
| M2 | **Add TO1 (component 3, T1 inside a trade-off):** "Which cuts more emissions by 2050, and at what cost: capturing 40% of the methane from rubbish dumps, or homes and businesses using a quarter less energy for cooking and heating?" Must translate both (L50 = 0.688, L27 = 0.67), compare on the same futures, call trade_off_analysis, name no winner, and call costs provisional. Key: total −2.27 Mt (−2.87 to −1.59) vs −2.05 Mt (−3.29 to −0.62); the intervals overlap, so neither clearly cuts more | Component 3 is under-covered, and this is the only question where an arm difference (translation) carries into component 3 |
| M3 | **Add N2 (component 3, strategy improvement, livestock)**, asked after D3b: "It fails when agricultural exports are high. What could we add so it holds up, and does it?" Key (exports in the top third): diets alone fail 52%; + less cattle methane (L23 = 0.3) → 0%; diets at the top of the range → 0%; + livestock productivity (L24 = 0.5) → **94% (worse)**. Must re-test, must not assume | A second strategy-improvement case outside electricity + forests; the productivity trap tests "must not claim without testing" |
| M4 | **Fix tolerances, the general rubric, the failure-mode list and the second-labeller plan** (section 3) before seeing any result | Turns the bank into an evaluation method (RQ1, second half) |
| M5 | **Q10b and Q14b:** score on process; record the levels chosen; no numeric pass/fail on levels | Their wording is vague by design |
| M6 | **Cost-free scoring for component 3** until P8 is closed; the same "costs provisional" note in all arms | Section 1 |
| M7 | **Write in the methods that X ranges are an expected null** (Option A), unless Option B is done | Section 4 |
| M8 | **Re-tag S50, S3, S35** as tool-use questions for RQ2; their number goes to RQ1 | Section 4 |
| M9 | **D2b and N1 run in the Q10b conversation; N2 in the D3b conversation**; make the scripted turns explicit | The follow-up questions refer back to the earlier one |

### Nice to have

| # | Change |
|---|---|
| N-a | Apply the plain rewordings in section 2. They are safe as long as the number and its unit stay |
| N-b | Option B (X units for population and GDP) + the population question. That would bring the bank to 24 |
| N-c | If livestock now feels heavy (LV1, LV2, AG2, D3b, N2), replace LV2 by an industry emission target ("How far would cement need to cut clinker to bring industrial-process emissions 6% below business as usual?"). The key exists from pilot 3 (P12o) but needs recomputing. Industry has only one question today |
| N-d | Check AG1's "+2.3%" against the raw runs before freezing. A counter-intuitive sign used as a must-rule should not rest on the surrogate alone |
| N-e | Report the 5 pilot-reused questions separately |

### Sector balance after M2 + M3 (23 questions)

| Sector | Before | After |
|---|---|---|
| Solid waste | 3 | 4 (+TO1) |
| Buildings | 2 | 3 (+TO1) |
| Livestock and diets | 4 | 5 (+N2); 4 with N-c |
| Electricity | 4 | 4 |
| Transport | 2 | 2 |
| Industry | 1 | 1; 2 with N-c |
| Others | unchanged | unchanged |

Electricity and transport are not increased. The two new questions sit in waste, buildings and livestock.

### Components after the changes

| Component | Before | After |
|---|---|---|
| 1 · Exploratory modeling | 16 | 16 |
| 2 · Vulnerability analysis | 3 | 3 |
| 3 · Trade-off analysis / strategy improvement | 2 | 4 (Q14b, TO1, N1, N2) |

---

*Numbers in this report: scripts in the session scratchpad, reproducible with `bank_reference.run_policy` and the
same futures (seed 0, N = 1,000).*
