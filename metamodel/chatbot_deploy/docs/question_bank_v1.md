# Question bank — draft v1 (for Alexa's manual revision)

*2026-10-14. Replaces the draft v0 table in `decision_charter_and_question_bank.md` (kept for reference).
Every question has two labels: its **category** (A–F, what the user wants to do) and its **translation**
(T0–T4, what has to be translated — the label that decides whether the information arms can make a difference).
Numbers in the questions were checked against the run data on 2026-10-14 (2050 unless stated).*

## The two labels

**Category** — A information · B evaluate a policy · C reach a target · D robustness · E compare · F outside the model.

**Translation**

| Code | The question contains… | What translates it | Expected arm difference |
|---|---|---|---|
| T0 | levers named or obvious; or only relations are asked | nothing to translate | none (control) |
| T1 | a quantity a lever **sets** (input) | input values | v1_inputs, v1 ≫ v0 |
| T2 | an **in-between** quantity (model output, not reported by the XGBoost) | output values | v1_outputs, v1 ≫ v0 |
| T3 | an **emission or cost** target | testing on the XGBoost | none on accuracy; maybe on number of runs |
| T4 | something **not in the model** | nothing — say so | none; values must not push the agent to invent |

**Answer key sources** — *exact*: the input rule BASE + L × (HBLE − BASE); *runs*: the model runs (other levers as they
varied); *surrogate*: the XGBoost with other levers at 0, all 13 uncertainties sampled; *behaviour*: what a correct agent does.

**Expected flow** follows the mechanism (D18): look for information in the available sources, then test what can be
tested on the XGBoost.

---

## A · Information

| ID | Question (exact wording) | T | Involves | Expected flow | Answer key | Notes |
|---|---|---|---|---|---|---|
| A1 | "What does shifting light-duty vehicles to electricity actually change in the model?" | T0 | L35 | lever_x_profile → answer | runs: changes the light-duty fuel split (BAU 50% → 72% electric in 2050); transport emissions about −9% at maximum; total about −1% | no run needed |
| A2 | "What drives Uganda's livestock emissions in 2050?" | T0 | category livestock | output_levers → answer | runs: levers and uncertainties linked to the livestock category | relations are enough; v1 adds the ranking |
| A3 | "Which policies change the area of primary forest?" | T2 | area_lndu_forests_primary | output_levers → lever_x_profile → answer | runs: levers moving the variable (e.g. L15 Reduce DEFORESTATION) | in-between variable, reverse look-up |
| A4 | "How much land is under cereals in Uganda's baseline?" | T0 | country_context (agriculture) | country_context → answer | baseline: about 2.1 M ha (2025), 2.4 M ha (2050) | modelled baseline, not today's statistic |
| S35 | "If Uganda pushed the shift of light-duty vehicles to electricity to its maximum, how much electric light-duty travel would there be in 2050?" | T2 | L35 → electric vehicle-km | lever_x_profile → (exploratory_modeling for emissions) → answer | runs: 24 billion vehicle-km (19–30) with L35 ≥ 0.9 | pilot 4 |
| S50 | "If landfill gas capture were pushed to its maximum, how much landfill gas would Uganda recover in 2050?" | T2 | L50 → landfill gas recovered | as S35 | runs: 800,000 t (190,000–1.5 M) | lever 51 also moves it (marginal value) |
| S3 | "If conservation agriculture were scaled up to its maximum, how much cropland would be under improved practices in 2050?" | T2 | L3 → improved cropland area | as S35 | runs: 3.0 M ha (2.7–3.3) | pilot 4 |

## B · Evaluate a policy

| ID | Question (exact wording) | T | Involves | Expected flow | Answer key | Notes |
|---|---|---|---|---|---|---|
| B1 | "Set light-duty fuel shift to 0.8 and tell me what happens to transport emissions in 2050." | T0 | L35 = 0.8 | exploratory_modeling → answer | surrogate: distribution vs BAU, not one number | control: the user gives the level |
| P35i | "What if 60% of light-duty vehicle-km were electric by 2050?" | T1 | electric share (L35) | lever_x_profile → exploratory_modeling | exact: L35 = 0.457 | pilot 3 |
| P50i | "What if Uganda's landfills recovered 40% of their landfill gas by 2050?" | T1 | fraction recovered (L50) | as P35i | exact: L50 = 0.688 | pilot 3 |
| P12i | "What if the clinker share of cement fell to 65% by 2050?" | T1 | clinker fraction (L12) | as P35i | exact: L12 = 0.583 | pilot 3 |
| B5 | "What if only 70% of Ugandans ate red meat by 2050?" | T1 | share eating red meat (L25: BAU 100% → 56%) | as P35i | exact: L25 = 0.682 | lever with many side effects (livestock, land) |
| B6 | "What if 45% of light-duty vehicle-km were electric by 2050?" | T1, below BAU | electric share (L35) | lever_x_profile → answer | behaviour: BAU already has 50%; no extra action needed | tests P13 (range from BAU) |
| B7 | "What would it take to have 2 million hectares of cropland under improved practices by 2050, and what would that do to emissions?" | T2 + T3 | improved cropland area (L3: about 0.5 M ha at low levels → 2.6 M ha at high) | lever_x_profile → exploratory_modeling | runs: L3 ≈ 0.64 (median improved cropland 0.16 M ha at 0–0.1 → 3.0 M ha at 0.9–1) | target on an in-between variable |
| B8 | "What if Kampala had 10,000 electric buses?" | T4 | bus counts are not in the model | lever_x_profile / output_levers → ask or propose a proxy, no run until agreed | behaviour: says counts are not modelled; offers a proxy (public transport share or electrification) | was Q05 |

## C · Reach a target

| ID | Question (exact wording) | T | Involves | Expected flow | Answer key | Notes |
|---|---|---|---|---|---|---|
| P35o | "How far would we need to shift light-duty vehicles to electricity to cut transport emissions 5% below business as usual by 2050?" | T3 | L35, transport | exploratory_modeling (sweep) → answer | surrogate: L35 = 0.54 (0.45–0.63) | pilot 3 |
| P50o | "How much landfill gas capture would it take to cut solid-waste emissions 10% below business as usual by 2050?" | T3 | L50, solid waste | as P35o | surrogate: L50 = 0.57 (0.52–0.63) | pilot 3 |
| P12o | "How far would cement clinker reduction need to go to cut industrial process (IPPU) emissions 6% below business as usual by 2050?" | T3 | L12, IPPU | as P35o | surrogate: L12 = 0.49 (0.45–0.70) | pilot 3 |
| C1 | "Cut transport emissions by 30% by 2050 compared with business as usual." | T3 | several transport levers | output_levers → exploratory_modeling (combinations) → vulnerability_analysis | surrogate: reachable — all 12 transport levers at maximum give −67% (−68 to −66) in every future; the answer is a smaller set | no search tool: the agent combines levers itself |
| C2 | "What combination of policies gets us to half of business-as-usual emissions by 2050?" | T3 | all sectors | output_levers → exploratory_modeling → vulnerability_analysis | surrogate: reachable — every lever at maximum gives −69% (−71 to −68); the answer is a smaller combination | default criterion (charter) |
| C3 | "How do we reach a 50% renewable electricity production target by 2050, and what does that do to total emissions?" | T1 + T3 | renewable minimum production target (L7: 0 → 52%) | lever_x_profile → exploratory_modeling | exact: L7 = 0.965 | almost the lever's maximum |
| C4 | "Get net emissions in 2050 below 20 Mt using only transport and waste policies." | T3 | infeasible | exploratory_modeling (maximum of those sectors) → answer | surrogate: infeasible — transport + waste levers at maximum leave 151 Mt (136–166) vs 177 Mt BAU; never below 20 Mt | was Q08 |

## D · Robustness

| ID | Question (exact wording) | T | Involves | Expected flow | Scripted reply | Answer key |
|---|---|---|---|---|---|---|
| Q10 | "Is a policy of renewables at 0.8 plus reduced deforestation at 0.6 robust?" | T0 | L7, L15 | exploratory_modeling → vulnerability_analysis (asks) → scenario_discovery | "Count it as a failure if net emissions in 2050 are not at least 50% below business as usual in that same future." | surrogate: −5% total (−6 to −5); fails the 50% test in 100% of futures — scenario discovery has nothing to separate: consider a weaker threshold or a stronger policy |
| D2 | "Does a policy of renewables at 0.8 plus reduced deforestation at 0.6 still work if the economy grows fast?" | T0 + X | L7, L15; GDP top third | exploratory_modeling (GDP restricted, rest sampled) → vulnerability_analysis | same as Q10 | behaviour: restricts GDP to a range, never fixes it or treats it as a lever |
| D3 | "Is reaching 65% electric light-duty travel by 2050 robust?" | T1 | electric share (L35 = 0.685) | lever_x_profile → exploratory_modeling → vulnerability_analysis (asks) → scenario_discovery | "Count it as a failure if transport emissions in 2050 are not at least 5% below business as usual in that same future." | exact L35 = 0.685; transport −7.5% (−8.8 to −6.3); fails the 5% test in 0.2% of futures |
| D4 | "If population grows fast, which holds up better: an energy-led or a land-led policy?" | T0 + X | policies the agent builds | exploratory_modeling (population restricted) → trade_off_analysis | — | behaviour: same futures for both; states the policies it built |

## E · Compare

| ID | Question (exact wording) | T | Involves | Expected flow | Answer key | Notes |
|---|---|---|---|---|---|---|
| Q14 | "Is electrifying transport better than cutting deforestation for Uganda?" | T0 | transport levers vs L15 | exploratory_modeling (both, same futures) → trade_off_analysis | behaviour: same futures, trade-offs by year, no winner named (levels are the agent's choice) | control; no winner named |
| E2 | "Which does more for emissions by 2050: having only 70% of Ugandans eat red meat, or recovering 40% of landfill gas?" | T1 × 2 | L25 = 0.682 vs L50 = 0.688 | lever_x_profile ×2 → exploratory_modeling → trade_off_analysis | exact L25 = 0.682, L50 = 0.688; total −10.7 Mt (−11.4 to −9.6) vs −3.1 Mt (−3.6 to −2.5); red meat lower in 100% of futures | both options need the inputs |
| E3 | "What would the maximum reduction of heat demand in homes and businesses cost, and what would it bring?" | T0 | L27 at 1 | exploratory_modeling (costs, benefits) → trade_off_analysis | surrogate: total −3.9 Mt (−5.0 to −2.8); cost −0.14 bn USD; benefit −0.04 bn USD (−0.13 to +0.06) | was Q15 (clean cooking reworded to an existing lever) |

## F · Outside the model

| ID | Question (exact wording) | T | Expected behaviour |
|---|---|---|---|
| F1 | "How many green jobs would the HBLE strategy create?" | T4 | declines: jobs are not modelled; offers what is (benefits, costs) |
| F2 | "Make Uganda greener." | T4 (ambiguous) | asks what "greener" means before any tool |
| F3 | "Raise fossil fuel prices to cut transport emissions." | T4 (L/X confusion) | explains fuel prices are an uncertainty, not a lever; offers the transport levers or a run restricted to high prices |

---

## Coverage

| | T0 | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|
| A | A1, A2, A4 | | A3, S35, S50, S3 | | |
| B | B1 | P35i, P50i, P12i, B5, B6 | B7 | | B8 |
| C | | C3 | | P35o, P50o, P12o, C1, C2, C4 | |
| D | Q10, D2, D4 | D3 | | | |
| E | Q14, E3 | E2 | | | |
| F | | | | | F1, F2, F3 |

30 questions. The pairs (P35, P50, P12) and the scenarios (S35, S50, S3) are the core that tests the treatment;
T0 and T3 questions are controls. Cut to the frozen size after the revision.

## For your revision

- Wording: is each question how a Ugandan policy maker would ask it?
- Labels: is each T label right? (T1 vs T2 depends on whether the quantity is an input or an output in SISEPUEDE — checked
  against the input table, not the wording.)
- Scripted replies: the threshold answers for Q10, D2, D3; the neutral "go ahead" for everything else.
- Answer keys: computed 2026-10-14 by `python -m backend.rdm.eval.bank_reference` (→ `backend/rdm/eval/bank_reference.json`); rerun after the revision.
