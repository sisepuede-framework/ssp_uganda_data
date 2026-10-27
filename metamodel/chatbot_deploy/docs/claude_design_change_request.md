# Changes for the DMDU 2026 Talk deck (paste into Claude Design)

Please apply these changes to `DMDU 2026 Talk.dc.html`. Keep the current visual style. All numbers below are final;
do not round or change them. Slide numbers refer to the current deck (26 slides).

## Remove or move

1. Delete slide 7 ("A surrogate stands in for the slow model", the empty placeholder). Slide 8 covers the surrogate.
2. Move these slides to an appendix at the end, after a new divider slide titled "Appendix: details for questions":
   9 (Six rules), 11 (Six tools), 13 (The type of question sets which tools to use), 15 (Tools read the network…),
   20 (The treatment: v0 sees relations…).
3. Delete slide 26 (RQ1: "The system kept its rules…"). It is replaced by the new RQ1 slide below.

## New order

Context: 1, 2, 3, 4, 5 · Method: 6, 8, 10, 12, 16 · Experiment: 17, 14, 18, 19, 21 · Findings: 22, NEW A, 25,
NEW B, NEW C, 23, 24, NEW W, NEW D · Appendix divider, 9, 11, 13, 15, 20.

## Edits to existing slides

- **Slide 3:** the fifth box "Architecture + data" → "What the agent sees".
- **Slide 14:** move it into the Experiment section. Label "EXPERIMENT · THE TREATMENT", title "The treatment: v0
  sees relations, v1 also sees values", footer "Experiment".
- **Slide 18:** replace the line under the six boxes with: "+ five hypothesis questions (HA1–HE1), each testing one
  prediction about v0 vs v1 · corner number = RDM component · answer key example: 'half of rural wastewater to
  septic tanks' = lever level 0.716, not 0.5".
- **Slide 23:** label "DESIGN LESSON 1 · PILOT" (instead of "PILOT FINDINGS").
- **Slide 24:** label "DESIGN LESSON 2 · PILOT". Under "0 / 4" write "pilot, before"; under "1 / 4" write "pilot,
  after rewording the two descriptions". Footnote: "Pilot runs, one conversation per arm and question · full run,
  v0 vs v1 after rewording: 0 of 10 vs 4 of 10".
- **Slide 25 (RQ2):** pooled numbers instead of ranges, and only four rows:

  | Pooled over all questions | v0 · links | v1 · values |
  |---|---|---|
  | Policy level off the answer key | 79% | 1% |
  | model_network calls per conversation | 2.3 | 1.3 |
  | Words taken literally ("40%" → 0.4) | 50% | 0% |
  | Comparison sent to trade_off_analysis | 0 of 10 | 4 of 10 |

  Remove the rows "Numbers no tool gave" and "Uncertainty range on the wrong side". Replace the range chart with one
  grey bar (v0) and one blue bar (v1) per row (row 2 on a 0–4 scale). Text below: "With values, the agent turned the
  user's words into the right setting, and it searched the model less." Footnote: "290 conversations · 5
  repetitions per arm · rows 1–3: p < 0.01 in every group tested · uncertainty ranges: no failures in either arm".

## New slides

**A · after the Findings divider.** Label "RESULTS · RQ2 · ONE EXAMPLE". Title: "'Half' is not 0.5 on the lever".
Two rows, each a 0–1 lever axis with a vertical line at the answer key:
- WW1 · "What if half of rural households' wastewater went to septic tanks by 2050?" Key 0.716 ("half of rural
  wastewater to septic"). v0 (grey): 0.5 in 5 of 5, "half" read as half of the lever. v1 (blue): 0.72 in 5 of 5.
- P50i · "What if Uganda's landfills captured 40% of the methane their rubbish gives off by 2050?" Key 0.688 ("40%
  of landfill gas captured"). v0: 0.4 once; 4 times it ran 0.4, 0.7 and 1.0 without choosing. v1: 0.69 in 5 of 5.
Text: "Without values the agent can only guess how words map to settings. With values it looks them up. Over all 75
policy questions per arm: off the key 79% (v0) vs 1% (v1)." Footnote: "Lever levels set in the first run of each
conversation · answer keys computed from the model runs, fixed before the run".

**B · after slide 25.** Label "RESULTS · RQ2". Title: "Values also invite the agent's own arithmetic".
Question line: HA1 · "How far would Uganda need to push the shift of cars and vans to electricity for them to drive
21 billion kilometres on electricity in 2050?" Three boxes with arrows:
1. model_network gave (v1): electric light-duty travel 20.1 bn km, at an electric share of 0.61 (blue).
2. the agent computed: "That implies roughly 33 billion km of light-duty travel in total." (orange)
3. and answered: "21 ÷ 33 is about 0.64 electric." Reasonable, but no tool computed it. (orange)
Small table, "Conversations with a number no tool gave": All 290 · v0 6 of 145 · v1 12 of 145; Hypothesis
questions (HA1–HE1) · v0 0% · v1 20%. Side text: "Values improve the setting the agent chooses, and give it numbers
to calculate with. Those numbers need tracing before they reach a decision maker." Footnote: "Check 15 re-scored
after the run (rounding, lever lists, example thresholds were false positives; logged) · before the fix: hypothesis
0% vs 32%".

**C · RQ1, after B.** Label "RESULTS · RQ1". Title: "Through the agent, a user ran all three RDM steps". Four
columns with arrows between them; each has the RDM component, the user's words, the tools called, and the result:
1. Component 1 · "Is a policy with a strong push on renewable electricity and a moderate cut in deforestation
   robust?" · exploratory_modeling · 500 futures, asks the user what counts as failure.
2. Component 2 · "Count it as a failure if 2050 emissions are not at least 5% below BAU." · vulnerability_analysis,
   scenario_discovery · fails in 79%, mostly when GDP grows fast.
3. Component 2 · "Does it still work if the economy grows fast?" · exploratory_modeling (GDP top third),
   vulnerability_analysis · fails in 99%.
4. Component 3 · "What could we change so it holds up, and does it?" · model_network × 3, exploratory_modeling,
   vulnerability_analysis · adds a livestock lever: fails in 0%.
Bottom row, "Across all 290 conversations": 290 / 290 finished · 0 loops · 0 invented thresholds · 1 forecast
language · 3 named a winner · required RDM step skipped 22% → 12% (v0 → v1). Footnote: "Q10b → D2b → N1, v1,
repetition 1 · all 10 conversations (v0 and v1) took this path · reader checks pending the hand check".

**D · last slide before the appendix.** Label "CONCLUSION". Title: "Design what the agent sees, and test it". Three
boxes (the first one filled blue):
1. Show values, not only links: with the model's values the agent turns words into the right setting (79% → 1% off
   the key) and searches less.
2. Trace and label every number: values invite the agent's own arithmetic, and one unlabeled number misled it in
   half the conversations. Label each source; trace what the agent computes.
3. Tool wording chooses the RDM step: one sentence in a tool description decided whether the agent compared
   policies with trade_off_analysis. Test it like a model.
Below, small: "What we have not shown: one model and one country · one agent model · scripted users, not policy
makers · 5 repetitions per arm · the reader model is checked on 20 judgments". "Next: sessions with real users in
Uganda · checking the agent's explanations of why a policy works · tracing the agent's own numbers in the answer".

**W · after slide 24, before D.** Label "DESIGN LESSONS · THE WORDS". Title: "Two wording changes that changed what
the agent did". A table with four columns: Where · Before · After (added in bold, light blue) · What changed (blue).
1. Tool descriptions (exploratory_modeling and trade_off_analysis).
   Before: exploratory_modeling: "Use it to evaluate or compare policies, and again after revising a policy."
   trade_off_analysis: "RDM step 3 — trade-offs. Compares the policies of an ensemble …" (nothing on when to use it).
   After: exploratory_modeling: "Use it to evaluate policies, and again after revising a policy. **To compare
   alternatives, run them in one call, then use trade_off_analysis on its ensemble.**" trade_off_analysis: "RDM step
   3 — trade-offs. **Use it whenever the user compares two or more alternatives.**"
   What changed: **0 of 4 → 1 of 4** comparisons sent to trade_off_analysis (pilot). Full run: 4 of 10 with values,
   0 of 10 without.
2. A tool reply (country_context, GDP).
   Before: Uganda's GDP by year, nothing else: 679 bn in 2050.
   After: the same numbers, then: "**These values are SISEPUEDE's base future (future 0). It is not one of the
   experiment's runs, and its GDP is above the 90th percentile of the runs in 2040 and 2050. Do not read it as the
   middle of the futures explored.**"
   What changed: **10 of 20 → 0 of 20** conversations concluding "580 bn covers most futures" (pre-registered test).
Footnote: "Word for word from the code before and after (registry.py, commit 3497d44; tools/context.py) · the rest of
the prompt and the tools stayed the same".

## Appendix with the harness text

Do not build it in Claude Design. After exporting the .pptx, it is appended by
`python backend/rdm/deck/add_harness_appendix.py EXPORTED.pptx OUT.pptx` (9 slides: system prompt, catalogue, tool
descriptions, loop, rule messages, fixed text in the replies, word for word from the code).
