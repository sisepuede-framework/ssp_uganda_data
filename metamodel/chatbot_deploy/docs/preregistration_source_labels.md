# Pre-registration — two sources, one quantity (GDP 2050)

Written 2026-10-26, before any run of this test. It is committed to git before the first "before" conversation;
the commit date is the proof. Any run not described here is reported as exploratory.

## Why this test

Smoke tests of HC1 on 2026-10-26 (`backend/rdm/eval/pilot_runs/smoke_hypotheses_2026_10_26_rerun/` and
`…_thinking/`), question: *"Would moving homes and businesses to cleaner cooking and heating fuels still cut emissions
in 2050 if Uganda's economy were larger than about 580 billion dollars by then?"*

- In one v1 run the agent read GDP by X57 third from `model_network` (444 / 540 / 632 bn) and placed 580 bn in the
  top third (correct).
- In the other v1 run it read `country_context` (GDP 2050 = 679 bn), reasoned "580 is below the baseline, so most
  futures qualify", and said it could not place 580 bn on the uncertainty (wrong).

**What the two numbers are.** Both come from the same column (`gdp_mmm_usd`, billion international $, PPP) and agree
in 2025 (128.35). `country_context` reports **future 0**, SISEPUEDE's unperturbed base future, which is **not one of
the experiment's runs**. The experiment samples the GDP growth uncertainty (X57), and the base future sits above
almost all of its runs:

| Year | Base future (`country_context`) | Experiment runs, all: median (p10–p90) | X57 top third: median (p10–p90) |
|---|---|---|---|
| 2040 | 434.6 | 353.6 (286.7–418.9) | 407.2 (384.9–429.6) |
| 2050 | 679.2 | 540.3 (425.6–652.2) | 632.2 (593.9–670.6) |

Source: `backend/rdm/network/out/run_2026_05_30_ranges.parquet` (field `gdp_mmm_usd`, lever 0, 4,980 runs) and
`backend/services/context.py` (primary_id 0). Neither number is wrong; nothing tells the agent that they describe
different futures.

## Hypotheses

- **S1.** When two tools give an unlabelled number for the same quantity, and the numbers describe different futures,
  the agent often builds its answer on the one that looks sufficient (`country_context`, one call, one number)
  instead of the one that matches the experiment (`model_network` by X57 third).
- **S2.** Saying what the `country_context` number describes (the base future, not one of the runs, above almost all
  of them) lowers how often the agent builds on it and raises how often it places 580 bn in X57's top third.
- **S3.** In both conditions v1 places 580 bn correctly more often than v0 (v0's `model_network` has no values).

Direction only; no effect size is claimed in advance. The literature behind S1 is in `docs/lit_source_conflicts.md`.

## Design

| | |
|---|---|
| Question | HC1, wording above, unchanged; no scripted replies |
| Conditions | **before**: `country_context` as it is at the pre-registration commit · **after**: the same, plus the label below |
| Arms | v0 and v1 |
| Repetitions | 10 per condition × arm → **40 conversations** (~US$2.5) |
| Fixed | model `claude-sonnet-5-5`, effort `medium`, thinking adaptive with summarized display, system prompt, tools, tables, surrogate; recorded in each log's `versions` |
| Order | all 20 "before" conversations first; then the label is added and committed; then the 20 "after" |
| Output | `backend/rdm/eval/pilot_runs/source_labels_before/` and `…/source_labels_after/`, files `HC1_<arm>_r<rep>.json` |

**The only change in "after"** is in the RDM wrapper `backend/rdm/tools/context.py` (the deployed chatbot's
`backend/services/context.py` is not touched). For topic `gdp`, the reply gets this note, word for word:

> "These values are SISEPUEDE's base future (future 0). It is not one of the experiment's runs, and its GDP is above
> the 90th percentile of the runs in 2040 and 2050. Do not read it as the middle of the futures explored."

The note carries no run values, so v0 still receives no values from the runs (the v0/v1 difference is kept).

**"Before", pinned (added 2026-10-26, before the first run).** `country_context` wraps the deployed chatbot's
`backend/services/context.py`, which has local changes kept out of git on purpose (SHA-256 of the file used:
`08c40eac97668aad…`). The `gdp` reply in "before" is therefore pinned here as text, word for word:

```
{"topic": "gdp", "text": "Uganda Baseline — GDP Trajectory (billion international $, PPP, constant prices):\nYear      GDP (B intl $)\n------------------------\n2025               128.4\n2030               200.5\n2040               434.6\n2050               679.2\n\nNote: Values reflect the SSP-based baseline projection used in SISEPUEDE. GDP is in purchasing-power parity, constant prices (international dollars; growth matches the World Bank constant-price series), not market exchange rates.", "note": "Modelled baseline assumptions (2025–2050), not observed present-day statistics."}
```

"After" is this reply plus the note above. The runner checks every `gdp` reply against this text (plus the note in
"after") and stops if it differs.

## Measures (per conversation)

| ID | Measure | How it is read |
|---|---|---|
| **P1 (primary for S1/S2)** | The answer builds on the base value | Regex `\b679(\.\d)?\b` in the final answer (exact) |
| **P2 (primary for S2/S3)** | The answer places ~580 bn in the upper part / top third of the GDP uncertainty | Reader statement 1 of HC1's `must_say` (Haiku 5.5, `--reader`); Alexa checks 10 answers at random against the reader, chosen by seed 20261026 |
| P3 | Called `model_network` on the GDP node or X57 | Tool log (exact) |
| P4 | Called `country_context` with topic `gdp` | Tool log (exact) |
| P5 | Set an X57 range with lower bound ≥ 0.6 | Tool log, `x_ranges_set` (exact) |
| — | Which source the reasoning cites | Thinking summaries; read by hand, descriptive only |

## Analysis

- Counts and shares per cell (condition × arm) for P1–P5.
- S2: before vs after on P1 and P2, both arms pooled (20 vs 20) and per arm, Fisher's exact test, two-sided. With 20
  per condition only large differences can show; the result is reported as descriptive evidence, not as a general
  rate.
- S3: v1 vs v0 on P2 within each condition, same test.
- Every conversation is reported. A conversation is re-run only if a tool failed for an infrastructure reason (e.g.
  expired AWS login); re-runs are listed.

## After the test

Which `country_context` version goes into the full bank run is decided after this test and recorded in the plan log.
Open question for the team, independent of this test: was X57 meant to span only growth at or below the base path?
