# E3 (DRAFT): Does an answer-like number at the lever make the agent stop? Instructions or information?

**Status: SUPERSEDED (2026-11-17) by `run_design_E3_DRAFT_v2_2026-11-17.md`. Never approved or run.** Alexa asked for a question set per experiment and a power analysis.

_Original status:_ DRAFT, for Alexa's review. Registry ID **E3**
(`docs/experiment_registry.md`). It becomes the pre-registration when approved, committed and tagged
`exp/E3-frozen` before the first conversation. Replaces the superseded v5 draft.

## Why this test

- **Our data (E1, E2, A4, exploratory).** Map+ answers correctly whenever it reaches the variable holding the answer,
  but it often stops at the lever. Question by question, it stops when the lever's own input is a share of the
  quantity asked ("fraction of food lost" for "how much food would be lost": reached 2 of 30) and walks on otherwise
  (17 of 30). How explicit the question is does not explain it.
- **The literature (Elicit, 2026-11-17).** Premature stopping and "answering from the wrong evidence" are documented
  (Ko et al. 2026; Roh & Han 2026; Zhang et al. 2026), but no controlled study has isolated our chain: an answer-like
  intermediate number is shown, the agent treats it as the answer and stops, while the real answer is still
  reachable. Elicit's proposed test: hold task, graph and tools fixed and vary independently (1) whether the
  answer-like number appears, (2) whether its role is labelled, (3) whether the question names the requested quantity;
  compare a reminder in the instructions with the same content in the returned information, with matched content.
  No general winner between instructions and information design is established.

## Arms (all are Map+, the only version that can answer; one change each)

| Arm | The lever's calibration (BAU / middle / maximum of its inputs) | The role sentence | Everything else |
|---|---|---|---|
| **P** Map+ | shown | none | as in E2 |
| **H** calibration hidden | **not shown** (the lever still lists the inputs it sets, without values) | none | as in E2 |
| **L** label in the reply (information) | shown | **in the lever's reply**, next to the calibration | as in E2 |
| **T** label in the tool description (instruction) | shown | **in the `model_network` description** | as in E2 |

**The role sentence (identical, word for word, in L and T):**

> A lever's input values are its settings: what each lever level means. They are not results. Quantities the lever
> changes, such as amounts of energy, food, waste or biogas, are further along the network.

- **H vs P** tests the cause: remove the answer-like number and see whether the agent walks on.
- **L vs P** and **T vs P** test two fixes with the same words; **L vs T** answers "information or instruction?".
- Values at every other variable, the emission values at the lever, the system prompt and the other five tools are
  the same in every arm.

## Questions: 16 targets × 2 wordings

**Targets.** The variable holding the answer, 2–3 steps from its lever; key = its value for the lever's top third,
2050, p10–p90 (as in E2). Classified **before the run** by a fixed rule: *share-type* if the lever's input is a share
or factor of the same quantity the question asks an amount of.

| Share-type (8) | Other (8) |
|---|---|
| S50 landfill gas (L50), S3 cropland under soil-friendly farming (L3), R1 wastewater biogas (L43), R3 transmission loss (L5), R6 food lost (L2), R8 municipal waste recovered for energy (L52), **N1 industrial waste recovered for energy (L52)**, **N2 manure incinerated (L20)** | S35 electric vehicle-km (L35), HD1 transport electricity (L35), R2 manure biogas (L20), R4 industry electricity (L11), R5 building electricity (L28), R7 transport energy (L31), **N3 building energy for heat (L27)**, **N4 nitrogen removed in wastewater treatment (L47)** |

N1–N4 are new (never run); they test the share-type pattern outside the 12 questions it was found on. N1 shares a
lever with R8 (few share-type targets exist in the network).

**Wordings.** Each target in two wordings, both run in every arm:
- *General*: "how much X would …" (the E1/E2 wording; for S3 and S35, which named a unit, a general version is
  written: "how much farmland", "how far would electric cars and vans travel").
- *Explicit*: names the unit of the amount: "how many tonnes of X", "how many petajoules (PJ) of …", "how many
  hectares …". No mention of shares or of the lever.

The 32 wordings and 4 new keys go to Alexa in a Word table for approval before anything runs.

**Translation guard.** The 15 translation (T1) bank questions in P, L and T, 1 repetition each: the role sentence
must not harm translation. (H hides the calibration translation needs; it is not run on T1.)

**Size.** 16 targets × 2 wordings × 4 arms × 3 repetitions = 384; guard 45. **Total 429 conversations ≈ 1.5 × the
October run.** Three repetitions rather than five: distinct targets matter more than repeats (Elicit's first report).
Order: repetition by repetition, arms and wordings interleaved.

## Outcomes, scored separately (as Elicit recommends)

1. **Reached the evidence**: the agent opened the variable holding the answer (check 25).
2. **Valid answer**: a value inside the key, in the asked unit (strict, as in E2).
3. **Where and why it stopped** (from the trace, coded before analysis with the A4 rules): last node opened (lever /
   in between / answer variable), and the final claim (gave the amount / gave the lever's share / said unavailable /
   other). "Said unavailable" is a *false* unavailability whenever the answer variable was reachable (always, here).
4. Guard: lever level off the key on T1, in P, L and T.

**Primary contrasts** (permutation within target × wording, two-sided, 10,000 permutations):
H vs P, L vs P, T vs P, L vs T on outcomes 1 and 2; general vs explicit wording within P.
**Secondary:** each contrast within share-type and other targets (the A4 pattern, tested prospectively); stop codes;
network calls; every other check.

**Expectations stated before the run** (any result is reported):
- If the answer-like number causes the stop, H reaches the answer more often than P, mainly on share-type targets.
- If the agent stops because it takes the share for the answer, the explicit wording reduces "gave the share".
- If the role is what the agent misreads, L and T both help; L vs T says whether placement matters.
- If "said unavailable" comes from trusting only the surrogate, none of these arms fixes it.

## Assumptions (stated so they can be questioned)

1. **Hiding the calibration does not hurt these questions.** All 16 ask about the most ambitious level, which the
   agent can set without knowing what the level means (lever = 1 or "top third"). It would hurt translation, so H is
   not run on T1.
2. **The role sentence is the same content in L and T**; only its place differs. In T it is part of the tool
   description, which the agent reads before every call; in L it appears only when the agent opens a lever. This
   difference in exposure is part of what "instruction vs information" means here, not a confound to remove.
3. **The share-type rule is a judgement**, fixed before the run and listed per target; Alexa checks it.
4. **The explicit wording only names the unit.** It does not mention shares, levers or the network, so it tests
   naming the requested quantity, not a hint.
5. **Emission values at the lever stay in every arm** (as in Map+), so the comparison isolates the calibration and the
   role sentence. Whether those emission values push the agent toward the surrogate (the R1 lead from E2) is not
   tested here.
6. **Strict scoring.** A share is not an answer to "how many tonnes". Stop codes report it separately.
7. **Same agent and day.** All arms run together; P is the control rerun, so drift since E2 does not matter.

## Before the first conversation

1. Alexa approves this design, the 32 wordings, the 4 new keys and the share-type labels.
2. Code: arms H, L, T in `tools/network.py` and the per-arm description in `harness/registry.py`; question set
   `framing_e3`; specs; smoke test of each new arm on a T1 question (not a target).
3. Analysis script committed before the run (as `analyze_v4.py`), stop coding included.
4. Commit, tag `exp/E3-frozen`, run, manifest, `--check`, analyse; registry updated the same day.
