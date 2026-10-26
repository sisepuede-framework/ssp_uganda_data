# Review: is question bank v3 still biased, and is it ready to freeze?

*Independent re-audit, 2026-10-19. Reviewed: `docs/question_bank_v3.md`, `docs/review_bank_bias.md` (previous audit),
`docs/question_bank_v2.md`, `backend/rdm/harness/prompt.py`, `backend/rdm/harness/registry.py`,
`backend/rdm/tools/information.py`, `backend/rdm/tools/technical.py`, `backend/rdm/harness/agent.py`,
`backend/rdm/eval/failure_modes.py`, `backend/rdm/eval/questions.py`,
`backend/rdm/data/tables/run_2026_05_30_lever_inputs.csv`. No existing file was changed.*

---

## Short version

1. **The previous must-do fixes were applied, and applied correctly in the bank text.** The leaked examples are
   gone from the prompt and the tool descriptions. Tags, a dated pre-registration, 5 new questions, LV2 dropped,
   Q10b and D2b scored on process only, C4b reworded. The keys of H1, H2, H3 and X1 match the lever input table.
2. **Two small leaks remain.** (a) The `x_ranges` example "e.g. [0.5, 1]" is exactly the lowest range that passes
   D2b. (b) In the three v1 arms only, `lever_x_profile` says "uncertainty low/high = bottom/top third of its
   range". This is a cue on uncertainty ranges, which RQ2 measures, and only some arms see it.
3. **The "blind" tag is only partly honest.** X2 is truly blind. H1–H3 are a random draw, which is good. X1 is not
   blind: its key (0.5) was worked out when it was written. Its key also equals the literal reading ("halve" →
   0.5), so it cannot tell translation from guessing. In practice only **H1** is a blind T1 question with a key
   that tells the two apart.
4. **The main remaining problem is scoring, not bias.** The bank says "Must / must not: what `failure_modes.py`
   checks". For about half of the rules this is not true yet. There are no v3 `SPECS`. TO1 needs two levers. The
   chain Q10b → D2b → N1 is one conversation, but it has three IDs. F3b's expected path cannot run (an empty policy
   is rejected) and would be flagged by check 9.
5. **Verdict: not ready to freeze yet. It can be ready after about 3 hours of low-effort work** (section 6).

---

## 1 · Were the previous audit's must-do fixes applied?

| Fix | Status | Notes |
|---|---|---|
| F1 Leaked examples out of the prompt | **Done** | "vehicle-km, hectares or tonnes of gas recovered" and "top third for fast growth" are gone from `prompt.py`. No bank answer found in the prompt text |
| F1 Leaked examples out of the tool descriptions | **Done, one remnant** | "boom … [0.67, 1]" is gone. "e.g. [0.5, 1]" stays. It equals D2b's pass boundary (low end ≥ 0.5), so an agent that copies the example passes D2b. The previous audit suggested keeping it; I would now change it (section 2) |
| F2 Tags | **Done in the doc, not in code** | Tags are in the bank. `questions.py` has no v3 entries and no `tag` field yet (bank "Still to do" 2) |
| F3 Five held-out questions | **Done** | H1–H3 and X1–X2 are in the bank, with the wording given in the previous audit |
| F4 Pre-registration | **Done, with gaps** | Dated paragraph, threshold rule, T1 pool, both draws, seed, tolerances, prompt change log. Missing: (a) the second-threshold sensitivity check; (b) several rule-compliance items (section 3); (c) a way to prove the date: `question_bank_v3.md` and the prompt change are **untracked in git**. Commit them before the first run |
| F5 Q10b process only | **Done** | D2b too. "Record the agent's own failure rate" is stated, but `failure_modes.py` does not record it yet |
| F6 Drop LV2 | **Done** | |
| N3 C4b reworded | **Done** | Must state its baseline |

**Search for other leaks** (prompt, tool descriptions and the fixed text that tools return). I searched for the bank's
quantities, sectors and wordings: vehicle-km, hectares, landfill, clinker, septic, chickens, deforestation, 2030,
NDC, dams, "fast growth", "top third", 0.67.

| Where | Text | Verdict |
|---|---|---|
| `registry.py`, `x_ranges` | "e.g. [0.5, 1]" | **Small leak for D2b** (see above) |
| `information.py:231`, `lever_x_profile` note, v1 arms only | "uncertainty low/high = bottom/top third of its range" | **New, depends on the arm.** v0 gets "Relations only.". In the v1 arms, "fast growth" is likely to become [0.67, 1]. In v0, it is likely to become [0.5, 1] (from the example). Both pass D2b, but the difference shows up in RQ2's "uncertainty ranges it sets" and comes from tool text, not from model information. Disclose it, or put the same sentence in every arm |
| `prompt.py` | "Levels beyond that were never run and cannot be tested"; "say where a number comes from"; results "for 2025, 2035, 2040, 2050…"; "(for example jobs or specific projects)"; costs "as changes against BAU" | These are rules, not examples. But they are the must rules of LV1, H2, H3, S50, S3, S35, X2, B8b and TO1. Report them as rule compliance (section 3) |
| `technical.py` `MONEY_NOTE`; `information.py` unit labels | "fewer vehicle-km" | Harmless: it is a unit, not a bank number |
| `values.py` `lever_channel` | Docstring names lever 35 and lever 50 as the motivating cases | The docstring is not shown to the agent. But the *feature* (the "moves most with this lever" variables) was designed around dev items P50i, S50 and S35. That is one more reason to keep them in dev. No change needed |

---

## 2 · Remaining bias, question by question

Types: **a** selection · **b** tuning · **c** leakage · **d** reuse · **e** framing · **f** coverage.
"Rule" = the must rule repeats a prompt rule, so the item measures rule compliance, not capability.

| ID | Tag | Remaining types | Severity now | Comment |
|---|---|---|---|---|
| P50i | dev | a, d | High (as dev: fine) | Correctly in dev |
| P12i | dev | a, d, e | High (as dev: fine) | Still gives BAU in the wording ("instead of about 72%"). Acceptable in dev |
| B6 | dev | a, b, d | Medium | Still the share of distance, not the share of the fleet (the wrong-denominator case is still missing) |
| AG1 | designed | a, b, e | Medium | The sign was known beforehand. Declare it a known-answer trap |
| LV1 | designed | a, b, rule | Medium | Built to exceed the range. "must not test above the range" cannot really fail: the tool rejects any level above 1 (see section 4) |
| BLD1 | designed | a | Low | Also reused inside TO1 |
| WW1 | designed | a, e | Low–medium | The wording names the septic path |
| **H1** | blind | — | **Low** | Clean. Random target. Key 0.573 is far from the literal 0.25. **The only blind T1 item whose key tells translation from guessing.** "About a quarter" is the rounded draw (24.0% → 25%); the key uses 25%. Fine |
| **H2** | blind | rule | Low | Beyond the range. The realistic failure is not "testing above the range". It is a *literal* 0.5, which is inside 0–1 and runs without error. Score it with check 2 (user_number 0.5) |
| **H3** | blind | rule | Low | Same as H2 (literal 0.2, or 0.8 read as a level) |
| **X1** | blind | b, e | **Medium: wrong tag** | The key was worked out when the question was written. It also equals the literal reading: all forest-to-other transitions fall linearly to 0, so "halve" → L = 0.5 exactly at the input level. Checks 2 and 3 cannot separate translating from guessing. Re-tag it "designed (key provisional)", or keep the tag and score only check 1 plus a stated translation |
| S50, S3, S35 | dev | c (rule), d, e | High (as dev: fine) | The direct leak is fixed. "As ambitiously as is realistically possible" still points to the top of the range. Fine in dev |
| AG2 | designed | b, e | Low | Still says "compared with business as usual". Acceptable: it is the reachable case |
| C4b | designed | b | Low | Reworded. Good |
| **X2** | blind | rule | Low | Truly blind (key after freezing). "2030 is not a model year" can be read off the prompt's year list. Calling costs changes vs BAU is a prompt rule. So most of its must rules are rule compliance. The 24.7% figure is consistent with Uganda's 2022 updated NDC as I recall it (conditional + unconditional, vs BAU, 2030). Still check it |
| Q10b | dev | b, d | Low (process only) | OK |
| D2b | dev | **c**, d | **Medium** | The "[0.5, 1]" example is the pass boundary. The v1-only "top third" note is a cue that differs by arm |
| D3b | designed | a, b | Medium | Single-field lever. The threshold sits at the median. The sensitivity check is still not pre-registered |
| Q14b | dev | d | Low | |
| **TO1** | designed | d, e | Medium | Both halves reuse P50i (dev, tuned) and BLD1 word for word, so its translation result is not independent of theirs. The question asks "which cuts more", but the must-not rule says "do not name a winner". An honest answer *does* say which has the lower median and how often (the tool returns this). Reword the rule (section 4) |
| N1 | dev | b, d | Medium | The example fixes came from the designers' runs. Score only "re-tested with the same threshold" |
| B8b, F2 | designed | c (rule) | Low | Rule compliance |
| F3b | designed | rule | Low | Its expected path cannot run as written (section 4) |

### Is the 3-tag split honest and useful?

- **Useful: yes.** Separating dev (prompt tuned on them) from designed (written after exploring the model) is
  more honest than the previous audit's dev / held-out split. "Designed" items are not held out in any real sense.
- **Honest: mostly.** Two corrections:
  - X1 should not be "blind" (see above).
  - H1–H3 are better called "drawn". Their *targets* are random, but whoever wrote the wording knew the keys.
    That is acceptable; just name it accurately.
- **Do not pool.** The tags differ in kind, not only in "how biased". The arm effect within each tag is the right
  unit, as the pre-registration says.

### What can n = 5 blind items support?

| Can support | Cannot support |
|---|---|
| An existence check: does the system break on unseen items in ways not seen in dev? | Any rate or percentage of success "on unseen questions" |
| A descriptive side-by-side with dev ("the same failure modes appear / new ones appear") | Any arm effect (RQ2) on held-out items. With 5 items × 4 arms, one item flipping changes a rate by 20 points |
| Examples to show in the talk | A claim that results generalise. Even 5/5 passes gives a 95% interval of about 48–100% for the item pass rate; 4/5 gives about 28–99% |

- Repetitions (3 per arm) measure the agent's randomness on the *same* item. They do not add items.
- The 5 items are also different kinds: H1 is an in-range T1; X1 is a T1 that cannot discriminate; H2 and H3 are
  beyond the range; X2 is a target with the wrong year and costs. So "blind" is really **one test of in-range
  translation, two of boundary handling, and one of year and cost handling**.
- Say this plainly in the paper: *"Five held-out items were used as a check for overfitting, not to estimate
  performance."*

---

## 3 · Keys verified (lever input table, 2050; rule = BAU + L × (top − BAU))

| ID | Field | BAU → top of range (2050) | Target | Key in bank | Verified |
|---|---|---|---|---|---|
| H1 | `frac_lvst_mm_chickens_anaerobic_digester` (lever 22, 5 fields) | 0 → 0.4364 | 0.25 | L22 = 0.573 | **Yes** (0.25 / 0.4364 = 0.573) |
| H2 | `frac_ippu_production_with_co2_capture_chemicals` (lever 26; cement, metals and plastic are identical) | 0 → 0.4190 | 0.50 | beyond the range, max about 42% | **Yes**. The lever does set the same share for cement, metals and plastic |
| H3 | `factor_waso_waste_per_capita_scalar_food` (lever 48, 1 field) | 1 → 0.8364 | 0.80 | beyond the range, max about 16% less | **Yes** (16.4% less) |
| X1 | 30 forest/mangrove → non-forest transition probabilities (lever 15, 79 fields) | each p → 0 (exactly linear; at L = 0.5 every ratio is 0.500, except two "to wetlands" fields at 0.50–0.52) | "halve" | L15 ≈ 0.5 ± 0.1 | **Yes at the input level.** In hectares it will differ slightly: forest area stays larger, and the lever also raises cropland → secondary forest. The key may move above 0.5. Confirm it as planned |
| TO1 | lever 50 (0.07 → 0.55); lever 27 (×1 → ×0.627) | | 0.40; ×0.75 | 0.69; 0.67 | **Yes** (0.6875; 0.670) |
| also checked | L25 = 0.682, L3 = 0.51, L46 = 0.715, L12 = 0.583, B6 BAU = 50% | | | | **Yes** (L46 is 0.715, not 0.716; within tolerance) |

**Year dependence (new finding).** The table has two years, and the ranges are much wider in 2070. Chicken
digesters reach 80%, industrial CCS 80%, food waste ×0.70 and landfill gas 95%. `lever_x_profile` shows both
years to the v1-input arms. Consequences:

- The keys are correct for "by 2050". An agent that reads the 2070 row will be off the key (for example H1 → 0.31).
  That is a real failure and should count.
- For H2, H3 and LV1, the right answer is "not by 2050 at the most ambitious level explored; it is reached later
  in the runs". A good answer may say that. Do not score it as wrong.

**TO1: are its must rules achievable from what the tools return?**

| Rule | Achievable? |
|---|---|
| Translate both (L50 ≈ 0.69, L27 ≈ 0.67) | **Only in v1_inputs and v1.** Input values (BAU, middle, top) appear only there. In v0 and v1_outputs the agent can only guess. That is the RQ2 contrast, so it is an *outcome* in those arms, not a must. The same holds for every T1 key. Say so once in the pre-registration |
| Compare on the same futures | Yes: one `exploratory_modeling` call with two policies, then `trade_off_analysis` |
| Report emissions and cost | Yes: `trade_off_analysis` returns the change vs BAU in emissions, cost and net benefit, and the cost per tonne. Costs come only as changes vs BAU |
| "Which cuts more" without naming a winner | Yes: `pairwise.share_a_lower_emissions` gives the share of futures. Reword the rule: "must report the overlap or the share of futures; must not call one better overall" |

---

## 4 · Can `failure_modes.py` detect each rule as written?

Key: **auto** = an existing check, given a correct spec · **reader** = needs `--reader` (checks 17–18) ·
**new** = no check yet. Smallest additions are listed under the table.

| ID | Rule | Detectable? | Spec / fix needed |
|---|---|---|---|
| All T1 | key ± 0.02 | auto (check 3) | The default `LEVEL_TOL` is **0.05**. Set `tol: 0.02` in every spec (X1: 0.1) |
| P50i, H1, BLD1, WW1, AG1, P12i, D3b | must not use the literal number | auto (check 2) | `user_number` in each spec (0.4, 0.25, 0.25 or 0.75, 0.5, 0.3, 0.65, 0.7) |
| P50i, P12i, BLD1, WW1, H1, X1 | read lever N before running | auto (check 1) | `kind: T1`, `lever` |
| X1 | state the translation | reader | **new A** (`must_say`) |
| B6 | do not run / propose action | auto | `run_expected: False`, `key_level: 0` |
| B6 | must say BAU is already 50% | no | **new B** (`must_mention: ["50"]`) |
| AG1 | emissions rise, not a cut | reader (check 17) | `expected_direction: "up"` |
| LV1, H2, H3 | must not test above the range | auto (check 10), but it can hardly fail: the tool rejects it | The real failures are a **literal** level (check 2: `user_number` 0.4 / 0.5 / 0.2) and **silently running at 1** as if it were the user's number (new B) |
| LV1, H2, H3 | must say the maximum (33% / 42% / 16%) | no | **new B** (`must_mention: ["3[23]", "4[12]", "16"]`) |
| H2 | notes cement, metals, plastic | no | new B (optional) |
| S50, S3, S35 | top of the range; number from the runs; source | partly: check 15 (number traced), check 18 reader (source) | Value inside p10–p90: **new B** with a numeric range (`answer_range`), or reader |
| AG2 | levers only from agriculture, livestock, manure | no | **new C** (`allowed_levers`) |
| AG2 | test the package | partly (check 8 needs the tool, not the package) | **new C**: one policy with ≥ 2 levers |
| C4b | only waste levers; baseline stated; "not reachable" with the best case | no | new C (`allowed_levers`) + new B (`must_mention: ["8\\.4", "not (be )?reach"]`) or reader |
| X2 | 2030 not a model year; no 2030 number as computed; costs vs BAU | no | new B (`2030` together with `2025\|2035`) + reader for "not presented as computed". An attempted `years: [2030]` shows up as `BAD_METRIC` in the log: count it |
| Q10b | ask for the threshold | auto (check 7 + check 8, `needs_threshold`) | Add the failure share for the agent's own levels as a column (**new D**, 3 lines from the `vulnerability_analysis` reply) |
| D2b | GDP restricted, low end ≥ 0.5; not fixed; not a lever | auto (checks 5, 4, 6) | `x_side: {gdp_id: "high"}`. But see the turn problem below |
| D3b | key; threshold asked; scenario discovery | auto (3, 7, 8) | "Points to agricultural exports" is tool output; check it in the answer with new B |
| Q14b | same futures; no winner | auto (check 8 `compare`; check 14) | The `WINNER` regex misses "is more effective", "should prioritise", "I'd suggest". Extend it or use the reader |
| TO1 | translate **both** levers | **no**: a spec takes one lever | **new E**: `levers: {50: 0.688, 27: 0.670}`, run checks 1–3 for each, OR the flags |
| TO1 | same futures; no "better overall" | auto (8, 14) | Reword the rule (section 3) |
| N1 | re-test the revised policy with the same threshold | **no** | **new F** |
| N1 | does not claim it holds without testing | reader | new A |
| B8b, F2 | no run before clarifying | auto (check 9, `kind: T4`) | Proxy offered: new A or new B (`renewab`) |
| **F3b** | GDP is not a policy; "may run with GDP restricted (no lever)" | check 6 auto; **check 9 contradicts the bank** | `exploratory_modeling` with no lever raises `EMPTY_POLICY`, so the "no lever" path cannot run as written (only with a dummy lever at 0). With `kind: T4`, any run at turn 1 is flagged. Fix the text, and do not give F3b `kind: T4` (or drop check 9 for it) |

**The Q10b → D2b → N1 chain.** It is one conversation with three IDs. `failure_modes.py` scores one spec per
conversation. The scripted replies are popped in order whenever the agent ends its turn. If the agent asks
something else first (for example "what do you mean by strong?"), the threshold reply goes to the wrong question
and the chain falls out of step.
**Smallest fix:** score the chain as one conversation with a merged spec. Add `from_user_turn` to the checks that
belong to D2b (≥ 3) and N1 (≥ 4): filter `calls` by `c["user_turn"]`. Add a flag for when a scripted reply was
used before the agent asked for it. That is about 10 lines.

**Smallest additions (all in `failure_modes.py` / `questions.py`):**

| # | Addition | Size |
|---|---|---|
| A | `must_say: [claims]` → extend the `reader_check` prompt to return one true/false per claim | ~10 lines |
| B | `must_mention: [regex]` (and optional `answer_range: [lo, hi]`) → a deterministic check on the final answer | ~8 lines |
| C | `allowed_levers: set` + `package: True` → every lever in every `exploratory_modeling` policy is in the set; some policy has ≥ 2 levers | ~6 lines |
| D | `fail_share`: read `share_fail` (or similar) from each `vulnerability_analysis` reply into the row | ~3 lines |
| E | `levers: {id: key}` → loop checks 1–3 per lever | ~8 lines |
| F | `retest: True` → ≥ 2 `vulnerability_analysis` calls with the same metric, year and threshold, on different policies, after `from_user_turn` | ~8 lines |

Then fix the bank's "How to read a row" sentence. Mark each rule auto / reader so it does not claim that every
rule is checked automatically.

---

## 5 · What did not change (accepted, disclosed)

- The T1 pool is restricted to levers with a quantity a user can state. This is disclosed.
- There is still no wrong-denominator item (B6′ fleet share), no unit-mismatch item (X3 boda bodas) and no
  messy lever with a discriminating number. X1 was meant to fill that gap but cannot (see above). Electricity
  (13 fields) is never asked with a number.
- Thresholds are tuned to 20–60% failure. This is disclosed and legitimate.

---

## 6 · Verdict

**Not ready to freeze today. Ready after about 3 hours**, almost all of it in scoring, not in the questions.

### Must fix before freezing

| # | Item | Effort |
|---|---|---|
| 1 | Write the v3 `SPECS` (with `tag`) in `questions.py`. Explicit `tol: 0.02`; `user_number` for every T1, including LV1 / H2 / H3; `key_level: 1` for the beyond-range items; B6 `run_expected: False`; D2b `x_side` | 1–1.5 h |
| 2 | Add checks B, C, E and F and the turn filter for the Q10b → D2b → N1 chain. Route the rest to the reader (A). Fix "How to read a row" | 1–1.5 h |
| 3 | F3b: rewrite the expected path (a run needs a lever) and keep it out of check 9 | 10 min |
| 4 | X1: re-tag as designed (key provisional), or score only "read lever 15 + stated translation". Note that its key equals the literal reading | 5 min |
| 5 | D2b: change the `x_ranges` example to a neutral one (e.g. "[0.2, 0.6]"). Disclose the v1-only "top third" note as an arm-specific cue on uncertainty ranges (or add the same sentence in v0). Rerun the smoke test | 15 min |
| 6 | Pre-registration: list the extra rule-compliance items (beyond the range, source of numbers, costs vs BAU, years, outside the model). State that T1 keys are achievable only in the arms that show input values. Add the 2050-vs-2070 note. Reword TO1's must-not. Then **commit the bank and the prompt change before any run** | 20 min |

### Nice to have (at most 3)

1. A threshold sensitivity check offline on the logged ensembles of Q10b and D3b, and pre-register it (30 min).
2. Swap X1 for B6′ ("45% of the cars and vans on Uganda's roads") or X3 (boda bodas). Either gives a held-out item
   that tells translation from guessing (30 min).
3. Widen the `WINNER` regex (or rely on the reader) so that "is more effective" and "should prioritise" count
   (10 min).
