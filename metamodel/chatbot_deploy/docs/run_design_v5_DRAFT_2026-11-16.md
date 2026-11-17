# Run design v5 (DRAFT): instructions or data? How to make the agent find intermediate quantities

**Status: SUPERSEDED DRAFT (2026-11-16). Never approved, implemented or run.** Kept for the record. The question-by-question analysis (A4, `results_analysis/question_pattern_v4.xlsx`) showed that whether the lever's own input is a share of the asked quantity explains reaching the answer better than instructions or signposts would address; Alexa was also unsure about signposts. E3 will be redesigned after the Elicit search (see `docs/experiment_registry.md`).

_Original status:_ DRAFT, for Alexa's review. It becomes a pre-registration only
when approved and committed before the first conversation.

## The question

Run v4 confirmed that the lever's calibration (its inputs at BAU, middle and range maximum) is what translation needs:
lever level off the key 59/75 (Map), 6/75 (Map+lever), 1/75 (Map+). That result stands on its own and matters for
models without SISEPUEDE's rich in-between variables: any model can expose a lever's calibration.

What remains open is retrieval. With Map+, the agent answered correctly whenever it reached the variable holding the
answer (12/12), but it reached it in only 12 of 40 conversations. Reading the 28 that did not reach it
(`results_analysis/run_v4_stop_coding.xlsx`, proposed codes awaiting the hand check):

| Why it did not reach the answer | Map+ | Map+lever | Questions |
|---|---|---|---|
| **Nearby quantity**: answered with the lever's own input ("about 5.5% of electricity would still be lost") | 11 | 9 | R3, R6, R8 |
| **Said unavailable**: "the surrogate doesn't report it" | 16 | 8 | R1, R2, R7 |

**Is the fix to tell the agent how to navigate (instructions), or to change what the network shows (data)?** This
run tests both, alone and together, so their effects can be separated.

## Arms (all start from Map+, the only arm that can answer)

| Arm | Instructions | Data at the lever node | Everything else |
|---|---|---|---|
| **P** Map+ (control, rerun now) | as in v4 | as in v4 | as in v4 |
| **I** Map+ & instructions | + navigation text (below) | as in v4 | as in v4 |
| **D** Map+ & signposts | as in v4 | + calibration labelled "settings, not results" + "quantities this lever changes" (below) | as in v4 |
| **ID** both | + navigation text | + labels and signposts | as in v4 |

**Instructions (I, ID)**: added to the `model_network` tool description (the only text that differs between arms):

> The network also holds quantities the surrogate does not report, such as amounts of energy, biogas, land, food or
> waste; each variable states its unit. When the user asks for such a quantity, walk forward from the lever until you
> reach the variable measured in what the user asked for, and report its values. A lever's input values are its
> settings (what each lever level means), not results. Do not tell the user a quantity is unavailable before you have
> looked for it in the network.

**Signposts (D, ID)**: two changes to the lever node's reply, no new values:
1. The calibration block is labelled: "settings: what each lever level means; these are not results".
2. A new list, "quantities this lever changes": up to 8 in-between variables within 3 steps, with unit and steps,
   ranked by how much the lever moves them in the runs, without values. Example, L2 (supply-chain losses):
   *Total Food Produced Lost Before Consumption (tonne), 2 steps; Total Food Loss Sent to Municipal Solid Waste
   (tonne), 2 steps; Biogas Recovered from Landfills (tonne), 3 steps; …*

## Questions

| Set | Questions | Why |
|---|---|---|
| R1–R8 (v4, unchanged) | 8 | Direct comparison with v4; 3 of them (R3, R6, R8) can be read as asking for a share |
| R9–R16 (new, held out) | 8, **unit named** ("in tonnes", "in PJ") | Removes the share reading. **4 with the answer on the signpost list, 4 not** (more than 8 variables down the list, or 4 steps away) so that signposts are not simply pointing at the answer |
| T1 translation guard | the 15 T1 bank questions | Checks that the new text or labels do not harm translation |

Runs: R1–R16 × 4 arms × 5 = 320; T1 × 4 arms × 2 = 120. **Total 440 conversations ≈ 1.5 × the October run.**
Order as in v4: repetition by repetition, arms interleaved.

## Outcomes (primary)

1. Value inside the answer key, in the asked unit (strict score, as pre-registered in v4).
2. Reached the variable holding the answer (process).
3. Lever level off the key on T1 (guard: no arm should be worse than P).

Secondary: why it did not reach the answer (nearby quantity / said unavailable / other, the v4 coding), network calls,
every other check. Analysis as in v4: per question set, permutation within question, pairwise against P, plus the
2 × 2 contrasts (effect of I, effect of D, and whether they add up).

## Assumptions (stated so they can be questioned)

1. **Map+ is the right base.** Only Map+ shows values at the answer variable, so only it can answer. The test asks how
   to make Map+ reach the answer, not whether values are needed (v4 showed they are).
2. **The two forms of stopping have different fixes.** "Nearby quantity" should respond to the settings label and to
   naming the unit; "said unavailable" should respond to the instruction and to the signposts. If one fix solves
   both, the 2 × 2 will show it.
3. **Signposts are a data change, not an instruction.** They add no values and no advice, only the names and units of
   what the lever changes. They are model-agnostic: any model with inputs and outputs can list them.
4. **The signpost ranking uses the runs** (how much the lever moves each variable). This is information about the
   model, not about the questions. Because R1–R8 were chosen as variables the lever moves strongly, signposts favour
   them; R9–R16 balance this with 4 questions off the list.
5. **The instruction changes only the `model_network` description.** The system prompt and the other tools stay as
   in v4, so the comparison isolates the navigation text. (This departs from v4, where every description was the same
   in every arm: here the description is the treatment.)
6. **Scoring stays strict.** A share is not counted as the answer when an amount was asked. For R1–R8 the nearby
   quantity is reported beside it, as in v4.
7. **Drift.** P is rerun now, so every comparison is between arms run at the same time.

## What it would tell us

- I works, D does not: the agent knew the data was there but needed to be told how to look. The fix is text.
- D works, I does not: the agent needs to see what exists. The fix is structure in the model-information layer.
- Both work and add up: they act on different forms of stopping.
- Neither works: the stopping is a property of the agent model; the next step is a different design (for example, a
  tool that answers "what quantity does this lever change, in this unit?").
