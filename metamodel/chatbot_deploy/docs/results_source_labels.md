# Results — two sources, one quantity (GDP 2050)

Pre-registration: `docs/preregistration_source_labels.md` (commits d0d32e4, b7bfccd; label and analysis c3bcf15).
Runs: `backend/rdm/eval/pilot_runs/source_labels_before/` and `…_after/` (20 each), measures in
`backend/rdm/eval/pilot_runs/source_labels_measures.csv` (`python -m backend.rdm.eval.analyze_source_labels`).
Run 2026-10-26. The "after" run stopped at 15/20 when the API credit ran out; the 5 missing conversations were run
after the credit was topped up (infrastructure re-run, allowed by the pre-registration). No conversation was excluded.
Every `country_context` gdp reply matched the pinned text of its condition.

## Pre-registered measures

| Measure | before v0 | before v1 | after v0 | after v1 | before vs after, pooled (Fisher) |
|---|---|---|---|---|---|
| P1 answer cites 679 | 10/10 | 8/10 | 9/10 | 8/10 | p = 1.00 |
| P2 places 580 bn in the upper part (reader) | 5/10 | 5/10 | 8/10 | 9/10 | p = 0.041 (per arm v0 0.35, v1 0.14) |
| P3 `model_network` on GDP or X57 | 1/10 | 2/10 | 3/10 | 3/10 | — |
| P4 `country_context` gdp | 10/10 | 10/10 | 10/10 | 10/10 | — |
| P5 X57 lower bound ≥ 0.6 | 8/10 | 9/10 | 10/10 | 10/10 | — |

v1 vs v0 on P2: p = 1.00 in both conditions (S3 not supported).

## Exploratory measures (defined after seeing data)

| Measure | before | after |
|---|---|---|
| E1 placement justified by GDP values from the runs (addendum, defined before the "after" run) | v0 0/10, v1 2/10 | v0 0/10, v1 2/10 |
| X1 answer says 580 bn is below the base / "covers most futures" (regex, defined after both runs) | **10/20** | **0/20** |

X1 regex: `580 … below … (baseline|base|679)`, `(baseline|base) … 679 … above 580`, `covers most`, `most futures`.
It should be checked by hand before it is cited.

## Reading

- **S1 supported.** Before the label, the agent built on the base value in 18/20 answers and, in half of all
  answers, concluded that "larger than 580 bn" covers most futures because 580 < 679 — wrong for the experiment's
  runs (median 540). It looked up GDP in the network in 3/20, although v1's network has GDP by X57 third.
- **S2 partly supported.** With the label the wrong inference disappeared (X1 10/20 → 0/20) and more answers placed
  580 bn in the upper part (P2 10/20 → 17/20). But the agent reached that by reasoning from the label ("the base is
  above the 90th percentile, so 580 is probably in the upper part"), still without the numbers: it did not go to the
  network more often (P3 3 → 6 of 20, E1 unchanged at 2/20). P1 did not change because the agent still quotes 679 —
  now with the right reading; P1 as defined cannot tell a right use from a wrong one.
- **S3 not supported.** v1 has the GDP values by third and still guessed like v0 in 16/20 conversations. In its
  reasoning it says "I don't have GDP values to map 580" — it does not know, or does not think to look, where the
  number is. The one-step source (`country_context`) is consulted in every conversation; the network walk rarely.
- **For the design argument.** Labelling what a number describes fixed the wrong conclusion at no cost, but did not
  make the agent fetch the right number. Consistent, labelled sources prevent errors; getting the agent to the
  information it needs is a separate design problem (discoverability: prompt, tool descriptions).

## Limits

10 conversations per cell; only large differences can show. P2 rewards guesses ("top third as a stand-in"). X1 is
post hoc. One question (HC1), one model (Sonnet 5.5, effort medium).
