# Plan A5: rescoring E2–E4 after the independent review (for the next session)

Status: **plan saved 2026-11-17, nothing done yet.** Alexa asked to save it for the next session; she has not yet said
go. Source of the findings: `docs/review_E2-E4_2026-11-17.md`.

**What A5 is:** an exploratory analysis, because the reviewer's numbers have already been seen. It sits next to the
pre-registered results, which stay as they are. No new conversations are run and no API is called, so the cost is
$0; my work is about 200–400k tokens of a Claude Code session. Time is about 1–1.5 hours.

## Steps

0. **Fix the rules before computing.** Write the rules below into `backend/rdm/eval/rescore_a5.py` (docstring), add an
   A5 row to `docs/experiment_registry.md`, and commit. Only then run it.
1. **Read numbers correctly.**
   - Parse "Mt", "kt" and "Mha" (`analyze_e3.UNIT_RX` misses "0.7 Mt").
   - Take both ends of a range ("85,000–90,000").
   - Rounding: a stated number counts if its rounding interval overlaps the key ("3.6 million" means 3.55–3.65).
2. **Where each matched number came from**, compared with the tool replies in the same conversation:
   - **read:** the value for the lever's top third in 2050, at the answer variable;
   - **all-runs or wrong third:** on screen, but for the wrong setting;
   - **own calculation:** no tool showed it.

   "Valid" is reported three ways:
   - **pre-registered**, unchanged;
   - **corrected**: step 1 fixes, and all-runs matches removed;
   - **strict**: read from the right cell only.
3. **Keys.**
   - Recompute each key from the runs near the lever maximum, since the question asks for the maximum and the key
     used the top third (centred at about 0.83).
   - Flag the keys whose range contains the all-runs or low-third median (S50, N2, R3; 7 of 8 O questions; also R5,
     R7, HD1, O1, O3), and report results with and without them.
   - Check S3's construct: agents compute the no-till area (about 3.7 Mha), while the key variable is "Area of
     Improved Land" (2.2–3.1 Mha).
4. **Stop reasons from the whole final answer**, as two separate yes/no codes: "reports the lever's share" and "says
   the amount is unavailable". Add share values for the O questions, which are missing from `TOP`. This replaces the
   one-label, first-400-characters code.
5. **Two levels of "reached":**
   - "opened the answer variable" (check 25, as now);
   - "opened it with the lever filter at 2050" (the value was on screen).
6. **Tests with questions as the unit** (exact sign-flip test on per-question differences) for every E2, E3 and E4
   contrast, next to the conversation-level permutation tests. Holm within each experiment, E3 included.
7. **Outputs.**
   - Workbook: `results_analysis/a5_rescoring.xlsx`, with pre-registered vs corrected vs strict side by side, and a
     hand-check sheet with each number's source pre-filled, so Alexa only confirms.
   - Results documents: `docs/results_E3_2026-11-17_v2.md` and `docs/results_E4_2026-11-17_v2.md`, with the claims
     reworded (below); the originals are kept.
   - Records: registry rows and deviations, then a commit.
8. **Run the independent reviewer again** on A5 (about 350k tokens of agent work, no API cost).

## Claims to reword in the v2 results documents

| Where | Claim | Change |
|---|---|---|
| E3 #2 | "It is not only the share-type questions" | It did not replicate in E4: O, P 13 vs H 17 of 24, p = .21. Withdraw, or report E4 as the replication. |
| E3 #4 | "Naming the unit removes the share answer, 20→4" | It changes the order: the share is still given in 40/43 SX stops. |
| E3 #6, and the "two forms of stopping" story | "two forms of stopping, each with its own fix" | There is one stop: stay at the lever, report its setting, and say the amount is unavailable. |
| E3b, E3c | significant valid gains | Not significant under the corrected rule or with questions as the unit. |
| E4 #1 | "because it needs it to translate" | The tool description tells it to ask; H shows it is not needed. |
| E4 #1 | "having the number when it starts looking" | Contradicted by C. |
| E4 | "works only together" | The interaction is an estimate only; its CI includes 0 under strict scoring. |

Other corrections:
- "reached" → "opened the answer variable".
- Disclose the `looking_for` example, which is R6's target (`registry.py:128`).
- Disclose the key mismatch (top third vs L = 1).
- Fix the small numbers: S3 "0 of 10 per arm"; the 12 C reached-not-valid; true no-policy counts; and that
  "no run = off key" holds for only 10 of 15 G questions.
- Remove overclaims: "translation is safe", "as good as Map+", "placement made no difference".
- Small fixes: `power_e4.py` says five contrasts (there are six); the registry date column shows E3 as "planned";
  results_E4 is missing from "Where things are".

## What is safe already (reviewer)

- E3a: hiding the calibration → the agent opens the answer variable (p = .001 with questions as the unit).
- H cannot translate (31/45).
- E4: C > P, C > R, C > F, and R < H. C is 46–54 of 120 under the stricter rules, against 15 for P.

## After A5

1. Alexa's hand checks, which are simpler with the sources pre-filled.
2. Paper v2: E2, E3, E4, the framework and the Elicit references, each verified before it enters the bib.
3. Ask whether to push `dmdu-agent` and the tags. Nothing has been pushed since `576335b`, and pushing would give the
   freezes an outside timestamp.
