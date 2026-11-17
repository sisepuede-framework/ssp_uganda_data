# Experiment registry: every test of the RDM agent

One row per test, kept up to date. **Start here** to find a test's design, the code it ran, its data, its analysis,
its status and its deviations. Created 2026-11-16 (Alexa: "keep a very good version control of all the tests").
Paths are relative to `metamodel/chatbot_deploy/`. Arms: v0 **Map** (relations), v1 **Map+** (lever calibration +
values of every variable), v2 **Map+lever** (lever calibration only); E3: v3 **H**, v4 **L**, v5 **T**; E4: v6 **C** (calibration on request + `looking_for`), v7 **R** (on request), v8 **F** (`looking_for`).

## Rules (how every test is version-controlled)

1. **An ID before anything runs.** E = pre-registered experiment, P = pilot or smoke test, A = analysis of existing
   data (C = confirmatory, as fixed before the run; X = exploratory, defined after seeing results).
2. **Design frozen in git before the first conversation.** A `docs/*.md` design file, committed; the commit is the
   proof. A git tag `exp/<ID>-frozen` marks it.
3. **Run code committed.** `run_bank.py` refuses to start with uncommitted code. **No commits while a run is going**
   (lesson from E1 and E2, see deviations).
4. **Data.** Conversation logs stay out of git (`backend/rdm/eval/pilot_runs/<folder>/`, 47 MB), but every folder
   has a committed **manifest** (`backend/rdm/eval/run_manifests/<folder>.csv`): each file's SHA-256 and the model,
   code commit and prompt/tool fingerprints the log records. Write after each run:
   `python -m backend.rdm.eval.run_manifest`; verify before any analysis: `... run_manifest --check`.
5. **Analysis script committed before results are read.** Outputs (`results_analysis/*.xlsx`) are never overwritten:
   scripts refuse; a hand-checked workbook is saved under a new name (`*_checked_<date>.xlsx`) and committed.
6. **Deviations are written here**, with the date, and carried into the paper.
7. **Paper numbers** are traced to the data by `results_analysis/code/working_paper_v2.py`.

## Tests

| ID | Date | What it asked | Design (frozen at) | Data folder (manifest) | Conversations | Analysis | Status |
|---|---|---|---|---|---|---|---|
| P1 | 2026-10-13/14 | Early pilots of the information arms (incl. v1_inputs, v1_outputs) | not pre-registered | `_archive` | 144 | — | done; arms v1_inputs/v1_outputs dropped 10-26 (`9a75792`) |
| P2 | 2026-10-21 | Smoke test of `model_network` | — | `smoke_network_2026_10_21` | 4 | — | done |
| P3 | 2026-10-26 | Smoke test of the 5 hypothesis questions (plus rerun, plus thinking on) | HA1–HE1 pre-registered `66a813e` | `smoke_hypotheses_2026_10_26{,_rerun,_thinking}` | 30 | — | done; HD1 key spec added after it |
| E0 | 2026-10-26 | Does a source label on `country_context` stop the agent reading the base future as typical? | `d0d32e4` (before `b7bfccd`, after `c3bcf15`) | `source_labels_before`, `source_labels_after` | 40 | `analyze_source_labels.py`, results `d8859f5` | done: X1 10/20 → 0/20 |
| P4 | 2026-10-26 | Dry run of the bank (harness and scoring check, not counted) | `9a75792` | `bank_dryrun_2026_10_26{,_tradeoff}` | 62 | — | done; fixes `d66e957`, `3497d44` |
| E1 | 2026-10-26/27 | Bank v3: Map vs Map+ (RQ1, RQ2) | `docs/question_bank_v3.md` "Run design", `7bedda2` (bank frozen `0f464b9`) | `bank_v3_full` | 290 | AC: `analyze_bank.py` (`b7b990b`) | done |
| A1 | 2026-10-27/30 | Scoring revisions after E1 (deviations, logged in `question_bank_v3.md`) | — | (re-scores `bank_v3_full`) | — | `c03ea33`, `4ae3d46`, `576335b` | done; reader hand check (20 judgments) **pending** |
| A2 | 2026-11-16 | Re-analysis for paper v2: pre-registered tables, process vs answer, provenance codes | — | `bank_v3_full` | — | AX: `results_analysis/code/reanalysis_v2.py` → `reanalysis_v2.xlsx` | done; **hand check pending** (Alexa) |
| A3 | 2026-11-16 | Is the surrogate fit for RDM? (held-out runs) | — | surrogate split | — | `surrogate_model_sector/rdm_fitness.py` | done |
| P5 | 2026-11-16 | Smoke test of Map+lever (WW1) | — | `smoke_v2_2026_11_16` | 1 | — | done (code uncommitted at the time; not analysed) |
| E2 | 2026-11-16 | Run v4: A Map+lever on the bank; B 8 held-out retrieval questions × 3 arms; C drift check | `docs/run_design_v4_2026-11-16.md`, `498c254`; analysis `5ba8aa7` | `bank_v4`, `retrieval_v4`, `bank_v4_drift` | 323 | AC: `backend/rdm/eval/analyze_v4.py` → `run_v4_analysis.xlsx` | done; **hand check of 12 matched values pending** |
| A4 | 2026-11-16 | Why did the agent not reach the answer? Is it the question wording? | — | `retrieval_v4` (+ `bank_v3_full`) | — | AX: `stop_coding_v4.py` → `run_v4_stop_coding.xlsx`; `question_pattern_v4.py` → `question_pattern_v4.xlsx` | done; **hand check pending** |
| P6 | 2026-11-17 | Smoke test of arms H, L, T (WW1) | — | `smoke_e3_2026_11_17` | 3 | — | done (code uncommitted at the time; not analysed): H shows no calibration and ran no policy; L and T set L46 = 0.72 |
| E3a | planned | Does an answer-like number at the lever make the agent stop? P (Map+) vs H (calibration hidden), 12 share-type questions × 5; check on 8 other-type × 3 | `docs/run_design_E3_2026-11-17.md` (draft v2; v1 superseded); power `results_analysis/code/power_e3.py` | `e3_S`, `e3_O` | 168 (P shared) | — | **done 2026-11-17** (393/393; results `docs/results_E3_2026-11-17.md`, `results_analysis/e3_analysis.xlsx`; **hand check pending**) |
| E3b | planned | Does one role sentence keep it searching, as information (L, in the lever's reply) or instruction (T, in the tool description)? 12 share-type × 5; translation guard 15 × 1 | same | `e3_S`, `e3_G` | 165 | `analyze_e3.py` | **done 2026-11-17; hand check pending** |
| E3c | planned | Does naming the unit ("how many tonnes") stop it answering with a share? P, general vs explicit wording, 12 share-type × 5 | same | `e3_SX` | 60 | `analyze_e3.py` | **done 2026-11-17; hand check pending** |
| P7 | 2026-11-17 | Smoke test of arms C, R, F: S50, R6, P50i | — | `smoke_e4_2026_11_17` | 7 | — | done (code uncommitted at the time; not analysed): translation right in every arm (L50 = 0.69); C R6 reached and answered; R R6 answered with the share |
| E4a | 2026-11-17 | 2×2 + H: calibration on request (R), stated target `looking_for` (F), both (C) vs Map+ (P) and hidden (H). Which change keeps the agent searching? 12 share-type × 10; other-type 8 × 3 | `docs/run_design_E4_2026-11-17.md`; power `results_analysis/code/power_e4.py` | `e4_S`, `e4_O` | 720 | AC: `analyze_e4.py` (6 contrasts, Holm) | frozen |
| E4b | 2026-11-17 | Do R, F, C still translate the user's words into the right lever level (and does H fail)? 15 T1 × 3, all five arms | same | `e4_G` | 225 | `analyze_e4.py` | frozen |

## Headline results (details in each analysis)

- **E1:** lever level off the key Map 59/75, Map+ 1/75 (every group p ≤ 0.008, permutation within question);
  `model_network` calls 2.36 vs 1.28 per question.
- **A2 (exploratory):** on 4 retrieval questions, reached the answer Map 16/20, Map+ 7/20; value inside the key Map
  0/20, Map+ 7/20. 28 untraced-number answers: 7 artefacts, 20 correct derivations, 1 wrong (proposed codes).
- **A3:** pass/fail agreement 96.9–99.3%; failure shares within 0.7 pp; scenario discovery same pair 4/4; ordering
  97%, but costs within 2% ordered at chance (52.5%); "vs BAU" thresholds not checkable.
- **E2:** lever level off the key Map 59/75, Map+ 1/75, **Map+lever 6/75** (lever calibration does the
  translation). Held-out retrieval: reached Map 37/40, Map+ 12/40, Map+lever 22/40; valid Map 0/40, Map+ 12/40,
  Map+lever 0/40. Drift: lever levels inside October's spread; network calls slightly outside (compared with C).
- **A4 (exploratory):** reaching the answer is not explained by how explicit the question is. With Map+, the agent
  stops when the lever's own input is a share of the quantity asked (reached 2/30) and walks on otherwise (17/30).
  Two forms of stopping: "nearby quantity" (answers with the lever's share; R3, R6, R8) and "said unavailable"
  (R1, R2, R7).

- **E3 (2026-11-17; `docs/results_E3_2026-11-17.md`; before the hand check):** hiding the lever's calibration (H) raised reaching the answer from 9 to 44 of 60 and valid answers from 8 to 44 (p < 0.001), also on the 6 new targets (6 → 19 of 30) and on other-type questions (8 → 18 of 24). The role sentence helped less: valid 8 → 18 of 60 both in the reply (L) and in the instructions (T); placement made no difference (18 vs 18). Naming the unit: valid 8 → 17, answering with the lever's share 20 → 4, but "said unavailable" 20 → 30. Translation unharmed (1–2 of 15 off key).

## Deviations and version notes

| Date | Test | What happened | Effect |
|---|---|---|---|
| 2026-10-27 | E1 | Check 15 re-scored after the run (A1) | before/after tables kept; reported |
| 2026-10-28 | E1 | Reader reads the whole conversation; text rules revised after Alexa's review (A1) | before/after kept; reported |
| 2026-10-30 | E1 | Reader hand-check sample redrawn by question, before any mark | reported |
| 2026-10-26 | E1 | 28 of 290 conversations (00:40–00:43 UTC) ran while two deck files (`backend/rdm/deck/`) had uncommitted edits, committed 5 min later as `36c8dcf`; logs record `7bedda2` or `36c8dcf` | none on the agent: system prompt and tools fingerprints identical in all 290 logs (`7370289f…`, `8a39a215…`). Found by the manifest, 2026-11-16 |
| 2026-11-16 | E1 | Paper v1 pooled the arms with Fisher tests; the pre-registration says per group, permutation within question | paper v2 reports the pre-registered tables; pooled counts descriptive only |
| 2026-11-16 | A2 | The walk-to-answer measure (16 vs 7 of 20) was defined on 10-28, after E1's results | labelled exploratory; tested prospectively in E2 part B |
| 2026-11-16 | E2 | `analyze_v4.py` committed during part A (needed by the preflight of parts B and C): part A logs record `498c254`, B and C `5ba8aa7` | none: the commits differ only by the analysis file |
| 2026-11-16 | E2 | Network calls in the drift check fell slightly outside October's spread | per design, calls compared with part C, not October; same conclusions |
| 2026-11-17 | E3 | The first freeze commit `4cd5de4` held only the rename of the design file (a failed `git add`); completed in `3a66a2d` and the tag `exp/E3-frozen` moved there | none: before the first conversation; every E3 log records `3a66a2d` |
| 2026-11-17 | E3 | Control P on other-type questions reached the answer less often than Map+ did in E1/E2 on similar targets (8/24 vs 17/25) | within-E3 comparisons use the concurrent control; reported as a caveat |
| 2026-11-17 | E3 | The stop-code table for the explicit wording (SX) was added after the results (`e3_stop_table.py`); `analyze_e3.py` listed stop codes for S and O only | descriptive; same coding rules |
| 2026-11-16 | A4 | `question_pattern_v4.xlsx` first built with hand-typed counts (one miscount found and fixed); replaced by `question_pattern_v4.py`, computed from the data | same numbers |

## Where things are

- Results: `docs/results_E3_2026-11-17.md`
- Designs: `docs/question_bank_v3.md`, `docs/run_design_v4_2026-11-16.md`, `docs/run_design_v5_DRAFT_2026-11-16.md` (superseded), `docs/run_design_E3_DRAFT_2026-11-17.md` (superseded), `docs/run_design_E3_2026-11-17.md`
- Literature: Elicit reports in `~/Downloads/` (innovation assessment 2026-11-16; premature stopping 2026-11-17)
- Questions and keys: `backend/rdm/eval/questions.py`, `bank_reference.json`, `retrieval_v4_reference.json`
- Runner and scoring: `backend/rdm/eval/run_bank.py`, `failure_modes.py`
- Data manifests: `backend/rdm/eval/run_manifests/` (`index.csv` lists every folder)
- Analyses: `backend/rdm/eval/analyze_bank.py`, `analyze_v4.py`; `results_analysis/code/*.py`; outputs `results_analysis/*.xlsx`
- Paper: `docs/DMDU_2026_working_paper_v2/` (local, git-ignored; the zip goes to Overleaf); builder and number trace
  `results_analysis/code/working_paper_v2.py`. On hold until E3 is done (Alexa, 2026-11-16).
