# Run design v4: Map+lever arm and eight held-out retrieval questions

**Status: FROZEN 2026-11-16**, committed before the first conversation of parts A, B and C (the commit is the
proof). Alexa approved R1–R8 as written (in chat, 2026-11-16; no edits in `docs/new_retrieval_questions_2026-11-16.docx`).
Anything not described here is reported as exploratory. Earlier designs: `docs/question_bank_v3.md` ("Pre-registration",
"Run design"); this one adds to them and changes nothing in them.

## Why

Working paper v2 found, on the October run (290 conversations):

- Map+ fixes translation (lever level off the key 59/75 → 1/75), but it adds two things at once: the lever's
  calibration (its inputs at BAU, middle, range maximum) and the values of every variable. Which one does the work?
- On four retrieval questions, process and answer diverge: Map+ reaches the node holding the answer less often
  (16/20 → 7/20) but answers validly more often (0/20 → 7/20). This was defined after the results were seen, on four
  questions. Does it hold on new questions? Does the early stop come from the values shown at the lever?

## What runs

| Part | Questions | Arms | Repetitions | Conversations |
|---|---|---|---|---|
| A. Bank, new arm | the 29 bank conversations (as in October) | v2 (Map+lever) | 5 | 145 |
| B. Held-out retrieval | R1–R8 (`backend/rdm/eval/retrieval_v4.py`) | v0, v1, v2 | 5 | 120 |
| C. Drift check | the 29 bank conversations | v0, v1 | 1 | 58 |
| **Total** | | | | **323** |

- **Arms.** v0 Map (relations), v1 Map+ (lever calibration + values of variables), v2 Map+lever (lever calibration,
  no values of variables). `backend/rdm/tools/network.py` `ARMS`; the tool's name, schema and description are the
  same in every arm.
- **Fixed:** model `claude-sonnet-5-5`, effort `medium`, adaptive thinking with summarized display, system prompt,
  tools and harness at the launch commit (each log records commit and fingerprints), as in October.
- **Order:** repetition by repetition, every arm of a question inside each repetition (interleaved), 5 at a time.
  Infrastructure faults are set apart and run again; no conversation is dropped for what the agent did.
- **Why C.** Part A runs about four weeks after v0 and v1. One repetition of v0 and v1 on the same 29 scripts checks
  that the agent has not drifted (same model id, but the service can change). If the primary outcomes of C differ
  from October's repetition 0 by more than the October spread between repetitions, that is reported and part A is
  compared with C, not with October.
- **Cost:** about 20,000 input and 2,400 output tokens per conversation in October; 323 conversations ≈ 1.1 × the
  October run.

## Outcomes

- **RQ3 (which part of Map+ does what), primary:**
  1. Lever level off the key (check 3, T1 questions): v2 vs v0 and v2 vs v1, per group as in October.
  2. `model_network` calls per question: v2 vs v0 and v2 vs v1.
- **RQ2b–c on held-out questions, primary (part B):**
  3. Reached the node holding the answer (process): v0, v1, v2.
  4. Value inside the answer key, from the model runs (answer): v0, v1. In v2 the answer node shows no values, as in
     v0, so a valid answer is not expected; reported, not tested.
- **Expectations, stated before the run** (not hypotheses to confirm; any result is reported):
  - If the lever calibration is what translation needs, v2 is close to v1 on outcome 1.
  - If values shown at the lever make the agent stop early, v2 reaches the node more often than v1 (outcome 3).
    If v2 also stops early, the calibration alone is enough to give the impression of an answer.
  - On R1–R8, v1 gives more valid answers than v0 and reaches the node less often, as on the four October questions.
- **Secondary:** every other check of the bank, as in October; process × answer table for R1–R8; provenance codes
  (A–D, `results_analysis/code/reanalysis_v2.py`) for answers flagged by check 15.

## Scoring and analysis

- Scoring: `failure_modes` with the checks and specs at the launch commit (the October rules after the 2026-10-27/28
  revisions), plus the R1–R8 specs: `visit` = the answer node; `must_say` = "gives a value from the model runs between
  p10 and p90" and "says this is the most ambitious level explored in the model runs" (as `_t2`).
- Answer validity: the text rule of `reanalysis_v2.py` (value with the right unit inside p10–p90), every match read
  by hand before the analysis.
- Analysis: per group, never pooled across groups; R1–R8 are their own group ("held-out retrieval"). Arm differences
  by a permutation test that shuffles arm labels within each question (10,000 permutations, two-sided), pairwise
  (v2–v0, v2–v1, v1–v0). Primary outcomes are named above; secondary p-values are reported without a claim of
  significance.
- No extra repetitions after seeing results, except runs labelled exploratory.

## Before the first conversation (checklist)

1. Alexa approves or edits R1–R8 (Word file). Wording changes → rerun `retrieval_v4.py`, which recomputes the keys.
2. Done 2026-11-16: R1–R8 are the set `retrieval_v4` in `questions.py` (read from `retrieval_v4_reference.json`,
   specs `RETRIEVAL_V4_SPECS`, tag "heldout"); `failure_modes.table` picks specs by question set; `run_bank.py` has
   `--set` and `--out` (commands at the top of the file). Re-scoring the October logs with this code: 0 differences
   on the 46 rule-based checks.
3. Done 2026-11-16: smoke test WW1 × v2 (`pilot_runs/smoke_v2_2026_11_16/`, not part of the analysis). Both
   `model_network` replies had `input_values` and no variable or category values; the agent set L46 = 0.72 (key
   0.716); checks 01, 02, 03, 15 pass.
4. Commit this file (status → FROZEN, with the date), the questions, keys and code. Then launch A, B and C.
