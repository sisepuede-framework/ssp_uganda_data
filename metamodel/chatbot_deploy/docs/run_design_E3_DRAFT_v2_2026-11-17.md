# E3 (DRAFT v2): three focused experiments on navigating the network

**Status: DRAFT v2, 2026-11-17, for Alexa's review. Nothing implemented or run.** Supersedes
`run_design_E3_DRAFT_2026-11-17.md` (one combined design). Registry IDs **E3a, E3b, E3c**. Each becomes pre-registered
when approved, committed and tagged `exp/E3-frozen` before the first conversation.

Changes from draft v1, at Alexa's request: each experiment has **its own question set**, designed for its hypothesis
and phrased as a policy maker would ask; and the number of questions is set by a **power analysis**.

## 1. What changes in each experiment

Every experiment changes **one thing** relative to its control; everything not listed stays as in E2 (same agent
model and effort, system prompt, six tools, surrogate, 500 futures, scoring).

| Experiment | Question it answers | Lever: calibration (its inputs at BAU / middle / maximum) | Lever: emission values | Lever: role sentence | Values at in-between variables | Tool description (instructions) | Question wording | Arms compared |
|---|---|---|---|---|---|---|---|---|
| **E1** (Oct, done) | Does showing values change what the agent does? | no → **yes** | no → **yes** | — | no → **yes** | same | general | Map vs Map+ |
| **E2** (Nov 16, done) | Which part of Map+ does translation? Does retrieval hold on new questions? | **yes** | no | — | no | same | general | Map, Map+, **Map+lever** |
| **E3a** cause | Does a number at the lever that looks like the answer make the agent stop? | **yes → hidden** | yes | — | yes | same | general | **P** Map+ vs **H** calibration hidden |
| **E3b** fix | Can one sentence about the lever's role keep it searching, and does it work better as information or as an instruction? | yes | yes | **none → in the reply / in the description** | yes | **same / + the sentence** | general | **P** vs **L** (sentence in the lever's reply) vs **T** (same sentence in the tool description) |
| **E3c** wording | Does naming the unit of the amount ("how many tonnes") stop the agent answering with a share? | yes | yes | — | yes | same | **general → explicit** | **P** with general vs explicit wording |

**The role sentence** (identical, word for word, in L and T):

> A lever's input values are its settings: what each lever level means. They are not results. Quantities the lever
> changes, such as amounts of energy, food, waste or biogas, are further along the network.

P (Map+, general wording) is run **once** and serves as the control of E3a, E3b and E3c (same run, interleaved).

## 2. Question sets: one per purpose

All questions are what a policy maker could ask: a policy in plain words, "as ambitiously as is realistically
possible" (the range maximum), and a quantity in 2050. The answer is an in-between variable 2–3 steps from the lever,
which the surrogate does not predict, so only the network can answer it. Key: the variable's value for the lever's
top third in 2050 (median, p10–p90), as in E2.

**Share-type** means the lever's own input is a share of the quantity asked (the lever sets "fraction of food
lost"; the question asks how much food is lost). This is where E1/E2 found the agent stopping (Map+ reached the
answer in 2 of 30). Labels are a judgement, fixed before the run, for Alexa to check.

| Set | Used in | Targets | Wording | Why this set |
|---|---|---|---|---|
| **S** share-type | E3a, E3b, E3c | 12 (below) | general ("how much food would still be lost …") | Where the problem happens; every contrast is tested here |
| **S-explicit** | E3c | the same 12 | names the unit ("how many tonnes of food would still be lost …"); no mention of shares or levers | Same targets, only the wording differs |
| **O** other-type | E3a only | 8 (below) | general | Check: hiding the calibration should change little where the lever's input is not answer-like |
| **G** translation guard | E3b only | the 15 translation (T1) questions of the bank | as in E1 | The role sentence must not harm translation (off-key 1/75 in Map+) |

**S, share-type (12):** 6 from E1/E2 and 6 new.

| ID | Policy (lever) | The lever's input (what the agent sees at the lever) | Asked quantity (answer variable) | Key, 2050 |
|---|---|---|---|---|
| S50 | Capture landfill methane (L50) | fraction of landfill gas recovered | landfill gas recovered (t) | 0.12–1.40 Mt |
| S3 | Soil-friendly farming (L3) | no-till crop fraction | cropland under improved practices (ha) | 2.2–3.1 Mha |
| R1 | Capture biogas at wastewater plants (L43) | biogas recovery factor | biogas recovered at plants (t) | 1.87–3.54 Mt |
| R3 | Cut electricity grid losses (L5) | transmission loss fraction | electricity lost in transmission (PJ) | 19.7–44.9 PJ |
| R6 | Reduce supply-chain food losses (L2) | fraction of food lost | food lost before consumption (t) | 1.88–2.20 Mt |
| R8 | Recover energy from burned municipal waste (L52) | fraction of incinerated MSW recovered | municipal waste recovered for energy (t) | 9,064–14,680 t |
| **N1** | Recover energy from burned industrial waste (L52) | fraction of incinerated ISW recovered | industrial waste recovered for energy (t) | 10,230–16,950 t |
| **N2** | Capture biogas from manure digesters (L19) | biogas recovery factor at digesters | biogas recovered from manure (t) | 0.34–1.17 Mt |
| **N3** | Manage cattle and pig manure better (L20) | manure management fractions, incl. share incinerated | manure (dung) incinerated (t) | 0.46–0.67 Mt |
| **N4** | Recycle more waste (L54) | fraction of glass recycled | glass recycled (t) | 63,000–85,000 t |
| **N5** | Compost and digest more organic waste (L49) | fraction of food waste composted | food waste composted (t) | 2.66–3.56 Mt |
| **N6** | Compost and digest more organic waste (L49) | fraction of food waste treated anaerobically | food waste to anaerobic digestion (t) | 3.13–4.00 Mt |

Two levers give two targets each (L52: R8, N1; L49: N5, N6), because share-type targets are rare in the network. The
analysis reports results with and without the second target of each lever. N1–N6 have never been run.

**O, other-type (8):** the lever sets something else (a fuel mix, a demand multiplier, an efficiency factor).

| ID | Policy (lever) | The lever's input | Asked quantity | From |
|---|---|---|---|---|
| R4 | Industry switches to electricity (L11) | industrial fuel fractions | electricity used by industry (PJ) | E2 |
| R5 | Efficient appliances (L28) | appliance demand multiplier | electricity used by buildings (PJ) | E2 |
| R7 | Less transport demand (L31) | transport demand multiplier | energy used by transport (PJ) | E2 |
| S35 | Electric cars and vans (L35) | light-duty fuel fractions | km driven on electricity | E1 |
| HD1 | Electric cars and vans (L35) | light-duty fuel fractions | extra electricity used by transport (PJ) | E1 |
| **O1** | Less heat demand in buildings (L27) | heat demand multiplier | energy used by buildings (PJ) | new |
| **O2** | More urban wastewater treatment (L47) | treatment-type fractions | nitrogen removed in treatment (t) | new |
| **O3** | More efficient industrial energy use (L10) | fuel efficiency factor | energy used by industry (PJ) | new |

All 20 targets × 2 wordings go to Alexa as a Word table (question text, lever, answer variable, key, share label) for
approval before anything runs.

## 3. How many questions: power analysis

The sample is the questions, not the repetitions: the five repetitions of a question are not independent. The power
of the pre-registered test (arm labels permuted within question, two-sided, α = 0.05) was simulated with questions
that differ in their baseline and in their response, with spreads taken from E1/E2
(`results_analysis/code/power_e3.py` → `power_e3.csv`). Baseline: Map+ reached the answer on 7% of share-type
questions.

| Contrast | Effect it should detect | 8 questions × 5 | **12 × 5 (chosen)** | 16 × 5 |
|---|---|---|---|---|
| E3a cause: P vs H | 7% → 40% reached | 0.90 | **0.98** | 1.00 |
| E3b fix: P vs L, P vs T | 7% → 30% | 0.70 | **0.86** | 0.96 |
| E3c wording: general vs explicit | 7% → 30% | 0.71 | **0.86** | 0.95 |
| E3b placement: L vs T | 40% vs 70% | 0.56 | **0.75** | 0.88 |
| E3b placement: L vs T | 30% vs 50% | 0.28 | **0.43** | 0.60 |

**What this means.** With 12 share-type questions × 5 repetitions, E3a, E3b (sentence vs none) and E3c have at
least 0.86 power for moderate effects. **L vs T** can only be told apart if the difference is large (about 30
points, power 0.75); a smaller difference will be reported as an estimate with its uncertainty, not as a test. 16
questions would raise it, but the network has few more share-type targets. Set O (8 × 3) is a descriptive check,
not a test (power is low by design for a small change).

## 4. Size

| Part | Set | Arms | Questions × repetitions | Conversations |
|---|---|---|---|---|
| E3a + shared control | S | P, H | 12 × 5 | 120 |
| E3a check | O | P, H | 8 × 3 | 48 |
| E3b | S | L, T (P shared) | 12 × 5 | 120 |
| E3c | S-explicit | P | 12 × 5 | 60 |
| E3b guard | G | P, L, T | 15 × 1 | 45 |
| **Total** | | | | **393 ≈ 1.35 × the October run** |

## 5. Outcomes (scored separately)

1. **Reached the evidence** (opened the answer variable): primary for E3a and E3b.
2. **Valid answer** (value inside the key, in the asked unit): primary for E3b and E3c.
3. **Where it stopped and what it claimed** (lever / in between / answer variable; gave the amount / gave the
   lever's share / said unavailable / other), coded from the trace with the A4 rules: primary for E3c ("gave the
   share"), secondary elsewhere.
4. Guard: lever level off the key on G (L and T must not be worse than P).

## 6. Assumptions

1. **Hiding the calibration does not hurt these questions**: all ask about the most ambitious level, which the agent
   can set without knowing what levels mean. It would hurt translation, so H is not run on G.
2. **L and T carry the same words**; the agent sees T before every call and L only when it opens a lever. That
   difference is what "information vs instruction" means here.
3. **Share-type labels are a judgement** fixed before the run.
4. **The explicit wording only names the unit** (no hint about shares, levers or the network).
5. **Emission values at the lever stay in every arm**, so E3 isolates the calibration and the role sentence.
6. **The effect sizes in the power analysis are assumptions** (7% baseline from E1/E2; 30–40% after a change). If
   real effects are smaller, the tests may miss them; estimates and intervals are reported either way.
7. **Strict scoring**: a share is not an answer to "how many tonnes".
8. **All arms run together**, so drift since E2 does not matter.

## 7. Before the first conversation

1. Alexa approves this plan, then the Word table of the 20 targets × wordings, keys and share labels.
2. Code: arms H, L, T (`tools/network.py`, per-arm description in `harness/registry.py`), question sets, specs;
   smoke test of each new arm on a G question.
3. Analysis script (with stop coding) committed before the run.
4. Commit, tag `exp/E3-frozen`, run, manifest, `--check`, analyse; registry updated the same day.
