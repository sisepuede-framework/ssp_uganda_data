# E4: keep the calibration, but on request; and state the target. Which part does what?

**Status: FROZEN 2026-11-17, committed and tagged `exp/E4-frozen` before the first conversation (the commit is the
proof).** Alexa approved this design: "let's separate them and run the design that allows us to get the most
information". Questions are E3's, approved before E3, unchanged. It supersedes the one-arm draft (`66a8c9b`, C + P
only, 258 conversations). Registry IDs **E4a** (retrieval) and **E4b** (translation guard).

## Why

E3 showed that the lever's calibration numbers make the agent stop before the answer:
- hiding them (H) raised valid answers on 12 share-type questions from 8 to 44 of 60;
- naming the unit ("how many tonnes") stopped the share answer (20 → 4) but not "said unavailable";
- the calibration is what translation needs.

The design these results point to: keep the calibration one call away instead of in every lever reply, and make the
agent state what it is looking for, with its unit. E4 tests **each change separately and together**. H runs
alongside, to see what having the calibration on request costs compared with not having it at all.

## Arms: a 2×2 plus H, all run together

| | Calibration in the lever's reply | Calibration on request | Not available |
|---|---|---|---|
| **No stated target** | **P** v1 (Map+, control) | **R** v7 | **H** v3 (as E3) |
| **`looking_for` in every call** | **F** v8 | **C** v6 | — |

- **Calibration on request (R, C):**
  - the lever reply has no input values, as in H;
  - `model_network(lever, meaning=true)` returns only what the lever's levels mean (input settings at BAU, the
    middle and the range maximum);
  - the tool description gains one sentence: "A lever's reply does not show what its levels mean. To translate the
    user's words into a lever level, call it with meaning=true: you get the lever's input settings at BAU, the middle
    and the range maximum."
- **Stated target (F, C):**
  - `looking_for` is a required argument of every `model_network` call ("what you are looking for, with its unit, as
    the user asked it (e.g. "food lost, tonnes per year, 2050"), or what a lever level should mean…");
  - it is echoed at the top of the reply;
  - a call without it is refused with "State looking_for…".
- **Everything else is as Map+:** values of in-between variables, emissions and categories, other tools, the system
  prompt, the model (Claude Sonnet 5.5, medium effort), scripted replies, keys and the reader.

Code: `backend/rdm/tools/network.py` (`ON_REQUEST`, `LOOKING_FOR`), `backend/rdm/harness/registry.py` (`tools_for`).
Arms v0–v5 are unchanged: all 805 `model_network` calls logged in E3 replay identically with this code, and
`tools_sha` is unchanged. The only variation is the order of tied rows in `lever_effects`, a pre-existing hash-order
effect. `tools_sha`: P/H 8a39a215c5125f15, R 58ba993fa22967b2, F 335ce92d80d29cc5, C 367d63dd4fe55df1.

## Questions and size (runner `backend/rdm/eval/run_e4.py`)

| Set | Questions (as E3) | Arms | Repetitions | Conversations |
|---|---|---|---|---|
| S share-type, general wording | 12 | P, H, R, F, C | **10** | 600 |
| O other-type, general wording | 8 | P, H, R, F, C | 3 | 120 |
| G translation guard (T1 bank questions) | 15 | P, H, R, F, C | 3 | 225 |
| | | | | **945** |

Interleaved by repetition (as E3); 5 conversations at a time; preflight, resume and fault retries as E3. Cost is
about $38 for the agent (E3: $0.03–0.06 per conversation), plus the reader (Haiku). Time is about an hour.

**Why 10 repetitions on S.** Power is simulated by `results_analysis/code/power_e4.py` →
`results_analysis/power_e4.csv` (same model as E3: question random effect and random slope; the permutation test).
Rates are taken from E3.

| Contrast (scenario) | 5 repetitions | 10 repetitions |
|---|---|---|
| R vs P, on request helps as much as hiding (0.15 → 0.70) | 1.00 | 1.00 |
| R vs P, half as much (0.15 → 0.40) | 0.79 | 0.97 |
| F vs P, as the explicit unit in E3 (0.15 → 0.30) | 0.41 | 0.74 |
| C vs R, target adds a moderate amount (0.40 → 0.65) | 0.59 | 0.86 |
| C vs R, target adds a little near the ceiling (0.70 → 0.85) | 0.30 | 0.62 |
| R vs H, on request loses part of H's gain (0.73 → 0.50) | 0.52 | 0.79 |

All power figures are at alpha 0.05. The strictest Holm step (alpha ≈ 0.01) is in the csv.

## Outcomes and tests (analysis `backend/rdm/eval/analyze_e4.py`, committed before the run)

As E3: reached, valid (a value with the asked unit inside the key; text rule, then hand check), and stop code. Test:
arm labels permuted within question, two-sided, 10,000 permutations.

**Primary (E4a): set S, outcome valid** (reached reported alongside). Holm adjustment over the six contrasts;
conclusions use the adjusted p.

| # | Contrast | What it isolates |
|---|---|---|
| 1 | R vs P | calibration on request, no target |
| 2 | C vs F | calibration on request, with target |
| 3 | F vs P | target, calibration shown |
| 4 | C vs R | target, calibration on request |
| 5 | C vs P | the whole design |
| 6 | R vs H | on request vs not available at all |

Interaction (C − R) − (F − P): estimate only, since it is not powered.

**E4b translation guard: set G, lever level off the key.** As in E1–E3, a conversation that runs no policy counts as
off the key. Compared: H, R, F, C vs P, unadjusted p. Also reported: how many conversations ran no policy. H is
expected to fail here, which measures for the first time what the calibration is needed for (until now only the
one-conversation smoke test P6).

**Secondary:**
- Set O: the same contrasts, descriptive.
- S: old vs new targets; without N1 and N6.
- Stop codes by arm.
- Meaning use: how often R and C asked for it, and whether before walking.
- How many `looking_for`s name a unit.
- In G: off the key by whether the agent asked for the meaning.

**Historical, counts only:** E3's P, H, L, T and SX next to E4's arms.

## Expectations, stated before the run (from E3)

- **R vs P:** positive if the number only stops the agent when it is offered unasked. The smoke test suggests a
  number the agent asks for can still stop it (R6 under R: asked for the meaning, answered "2.1% lost").
- **F vs P:** positive, mainly by removing the share answer (as the explicit wording did).
- **C vs R, C vs F, R vs H:** open. These are the questions the design is built to answer.
- **G:** P, R, F, C low; H high (no calibration, so no way to translate).

**A usable design** has:
- valid answers on S clearly above P (Holm-adjusted p < 0.05);
- an off-key rate on G not clearly above P's.

A non-significant G difference is not proof of no harm, so the counts are reported.

## Assumptions (decided, stated so they can be challenged)

1. **On retrieval questions the agent still needs a translation** ("as ambitious as realistically possible" is the top
   of the range). So in R and C it may ask for the meaning first. E4 tests whether a number the agent **asked for on
   purpose** still stops it, which is the realistic use.
2. **The meaning reply has no role sentence.** The sentence helped little in E3, and adding it would be a third change.
3. **`looking_for` is required but not checked:** any text passes, and the unit is suggested, not enforced.
4. **O and G have 3 repetitions:** O is descriptive; G is powered for a large harm (about 2% → 20% off the key), not
   a small one.
5. **Six primary contrasts with Holm:** this is stricter than E3, which had no adjustment. Unadjusted p is reported
   too.

## Smoke test P7 (2026-11-17, `pilot_runs/smoke_e4_2026_11_17`, code uncommitted at the time, not analysed)

- **C:**
  - P50i: asked for L50's meaning, set 0.69 for "40% captured" (right).
  - R6: asked for the meaning, walked on, answered "about 2.0 million t" (in the key).
  - S50: asked for the meaning, reached the node without the lever filter, answered with an emissions change.
- **R:**
  - R6: asked for the meaning, answered with the share (2.1%).
  - P50i: 0.69 (right).
- **F:**
  - R6: stated the target, ran a policy, no walk.
  - P50i: 0.69 (right).

There were no tool errors.
