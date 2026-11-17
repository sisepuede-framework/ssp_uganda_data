# E4 run design (DRAFT, for Alexa's approval): calibration on request

Status: **draft, nothing run** except the smoke test P7 (3 conversations, code uncommitted at the time, not analysed).
When approved it is renamed `run_design_E4_2026-11-17.md`, committed and tagged `exp/E4-frozen` before the first
conversation (registry rules 2–5).

## Why

E3 showed that the lever's calibration numbers make the agent stop before the answer:
- hiding them (H) raised valid answers on 12 share-type questions from 8 to 44 of 60;
- hiding them also removes what translation needs.

E3 also showed that the two ways of stopping have different fixes:
- naming the unit stops the share answer;
- only removing the number stops "said unavailable".

E4 tests the design these results point to. **Keep the calibration, but only on request, and make the agent state
what it is looking for, with its unit, before it walks.**

## The new arm C (v6), one row against Map+ (P, v1)

| | P (Map+) | C (calibration on request) |
|---|---|---|
| Lever reply | relations + calibration (input values at BAU, middle, range maximum) + emission values | relations + emission values; **no calibration** (as E3's H) |
| Calibration | in every lever reply | **one call away:** `model_network(lever, meaning=true)` returns only what the lever's levels mean |
| Target | not asked | **`looking_for` is required in every `model_network` call** (the quantity sought, with its unit, or what a lever level should mean), echoed at the top of the reply |
| Tool description | as in E1–E3 | + "A lever's reply does not show what its levels mean. To translate the user's words into a lever level, call it with meaning=true…" |
| Values of in-between variables, emissions, categories | yes | yes (unchanged) |

Code: `backend/rdm/tools/network.py` (`ON_REQUEST`), `backend/rdm/harness/registry.py` (`tools_for`). Arms v0–v5
are unchanged:
- all 805 `model_network` calls logged in E3 replay identically with the new code (`tools_sha` unchanged);
- the only variation is the order of tied rows in `lever_effects`, a pre-existing hash-order effect.

## Which arms and questions

**Only the new arm C, plus Map+ (P) run again alongside it.** L, T, H and SX are not run again, since their questions
are answered.

P is run again, not reused from E3, because:
- the test (arm labels permuted within question) assumes the arms ran together;
- E3 already showed a day-to-day difference: P on other-type questions reached 8 of 24 vs 17 of 25 in E1/E2;
- it costs about $5.

E3's H, L, T and SX are reported next to C as counts only, with no test, since they ran separately (hours earlier).

| Set | Questions (unchanged from E3) | Arms | Repetitions | Conversations |
|---|---|---|---|---|
| S (share-type, general wording) | 12 | P, C | 5 | 120 |
| O (other-type, general wording) | 8 | P, C | 3 | 48 |
| G (translation guard, T1 bank questions) | 15 | P, C | **3** (E3: 1) | 90 |
| | | | | **258** |

G has 3 repetitions because translation is where C can fail: the calibration is no longer shown unless the agent
asks for it. With 45 conversations per arm, a large harm can be seen (off the key from about 2% to 20%), but not a
small one.

Cost: about $11 (E3: $0.03–0.06 per conversation for the agent, Sonnet 5.5), plus the reader (Haiku).
Time: about 15 minutes.

## Outcomes and tests (analysis `backend/rdm/eval/analyze_e4.py`, committed before the run)

As E3: reached, valid (value with the asked unit inside the key; text rule, then hand check) and stop code.
Permutation test within question, two-sided, 10,000 permutations.

**Primary**
- **E4a retrieval (S):** C vs P on valid answers (and reached). Power: about 0.86 if C only matches the role sentence
  (18 vs 8 of 60); about 1 if C is close to H (44 vs 8).
- **E4b translation (G):** C vs P on lever level off the key.

**Secondary**
- O set, C vs P.
- Old vs new targets.
- Without N1 and N6.
- Stop codes by arm.
- Meaning use: how many C conversations asked for the meaning, and whether before walking.
- How many `looking_for`s name a unit.
- In G, off-key by whether the agent asked for the meaning.

**Historical, counts only:** C next to E3's H, L, T and SX, and E4's P next to E3's P (drift).

**What counts as success (stated before the run).** C is a usable design if:
- its valid answers on S are clearly above P's (E4a significant);
- its off-key rate on G is not clearly above P's.

A non-significant G difference is not proof of no harm: report the counts.

## Assumptions (decided, stated so they can be challenged)

1. **C bundles two changes**: calibration on request and `looking_for`. A positive result shows the design works,
   not which part did it. E3 suggests most of it is the calibration (H alone: 44/60) and that the unit fixes the
   share answer (SX: 20 → 4). Splitting them would need one more arm (+84 conversations); not proposed.
2. **On retrieval questions the agent still needs a translation** ("as ambitious as realistically possible" is the
   top of the range). So it may ask for the meaning first, and the smoke test shows it does (S50, R6). E4 therefore
   tests whether a number the agent **asked for on purpose** still stops it, which is the realistic use.
3. The meaning reply has **no role sentence**. The sentence helped little in E3, and adding it would be a third
   change.
4. `looking_for` is required but **not checked**: any text passes. The unit is suggested, not enforced.
5. Same model (Claude Sonnet 5.5, medium effort), questions, scripted replies, keys and reader as E3.

## Smoke test P7 (2026-11-17, `pilot_runs/smoke_e4_2026_11_17`, not analysed)

- **P50i (translation):** asked for L50's meaning, set the lever at 0.69 for "40% captured" (right: (0.40 − 0.07) /
  0.48).
- **R6:** asked for the meaning, walked on to the food-loss variable and answered "about 2.0 million tonnes (1.9–2.2)".
- **S50:** asked for the meaning, reached the landfill-gas node without the lever filter (got all-runs values), and
  answered with an emission change instead.

No tool errors; every call carried `looking_for`.
