# Review: does the question bank answer the research questions?

*Independent review, 2026-10-19. Reviewed: `docs/question_bank_v1.md`, `docs/rdm_information_layer_plan.md`
(incl. pilots 1–4 and the 10-16 / 10-19 updates), `backend/rdm/harness/prompt.py`, `backend/rdm/harness/registry.py`,
`docs/rdm_tools_design.md`, `paper1/md_to_claude/study_plan.md` §2–3. No other file was changed.*

## Short version

- **RQ2 is well served on its core and already half-answered by the pilots.** The questions that translate a
  quantity a lever sets ("60% electric") or an in-between quantity ("how much landfill gas") show a large, clean
  effect of the information arms. What is still unknown is whether the effect carries into the later RDM steps,
  whether the extra numbers cause harm, and how the agent's answers to the user change. The bank needs explicit
  scoring rules for "responses to the user" before the run.
- **RQ1 cannot be answered by a question bank alone**, and the current bank under-covers RDM component 2
  (vulnerability analysis and scenario discovery). The two questions meant to reach scenario discovery are
  both set up so that it has nothing to find: one fails in 100% of futures, the other in 0.2%.
- **Must fix before the run:** recompute the stale answer keys, re-set the robustness thresholds, fix B7's
  internally inconsistent key, write a scoring rule for each of the three parts of RQ2, and decide what
  "routing correct" means when several flows are valid.
- A frozen set of about **20 questions** (listed in section 6) answers both RQs at a modest cost.

### Words used in this report

| Term | Meaning |
|---|---|
| Lever | A policy Uganda decides (54 of them), set between 0 = business as usual (BAU) and 1 = the maximum in the model's high-ambition strategy (HBLE) |
| Uncertainty | A condition Uganda cannot decide (13: GDP, population, fuel prices, …), sampled over many futures |
| Surrogate | The fast XGBoost copy of SISEPUEDE; it only reports emissions by category, costs, benefits and GDP |
| In-between variable | A physical quantity inside the model (vehicle-km, hectares, tonnes of gas) — not reported by the surrogate |
| Arms | v0 = relations only (which lever moves what); v1_inputs = + the values a lever sets; v1_outputs = + values of in-between variables and emissions from the runs; v1 = both |
| T0–T4 | The bank's "translation" label: T0 nothing to translate; T1 a quantity a lever sets; T2 an in-between quantity; T3 an emission or cost target; T4 outside the model |
| Routing | Which tools the agent calls, in which order |

---

## 1. Can the bank answer RQ1?

> RQ1: "How do we build an ecosystem in which an agent is the intermediary, so that a non-technical person can
> carry out these three RDM components with SISEPUEDE?"

**A test bank cannot answer a "how do we build" question by itself.** "How do we build" is answered by the
design (the seven tools, the information layer, the rules enforced in code, the prompt) and by the evidence that
the design works and where it breaks. The decision log (D1–D19) and the pilot fixes (threshold bug, metric-name
bug, reply sizes, the D18 prompt paragraph) are in fact the best RQ1 evidence the project has — they document what
was needed and why. The bank can supply the second half: *does the built system let the user complete each
component, and how does it fail?*

What RQ1 would need, and what exists:

| Evidence RQ1 needs | Provided now? | Comment |
|---|---|---|
| A **non-technical person** completes the task | **No** | The user is scripted ("go ahead", plus a threshold in 3 questions). The study plan says accessibility is not measured. RQ1's wording promises something the study does not test |
| Each RDM component is **completed correctly** | Partly | Components 1 and 3 yes; component 2 effectively no (see below) |
| **Failure modes** listed and counted | Not planned | Pilots found real ones (info tools skipped for comparisons, target number taken as lever level, stopping after vulnerability analysis). No coding scheme exists to count them in the full run |
| **Design elements** shown to matter | Partly | Only the information layer is varied. Other parts (rules in code, the D18 prompt paragraph, the threshold-asking tool) are not tested; they can be argued from the log, not shown |
| Translation **policy-maker words → levers** works | Yes | T1/T2/T4 questions do this directly |

### Coverage of the three RDM components

Mapping each question to the component its expected flow ends in (categories A and F are not RDM components; they
are support: information lookup and staying inside the model):

| RDM component | Questions | n | Assessment |
|---|---|---|---|
| 1 · Exploratory modeling / stress testing | B1, P35i, P50i, P12i, B5, B6, B7, P35o, P50o, P12o, C3, C4 (+ D2, D4 stress under an uncertainty) | 12 (+2) | Well covered; arguably over-covered |
| 2 · Vulnerability analysis & scenario discovery | Q10, D2, D3 (+ C1, C2 end with vulnerability analysis) | 3 (+2) | **Under-covered and broken.** Q10 and D2 fail in 100% of futures; D3 fails in 0.2% (≈1 of 500). In all three, scenario discovery has nothing to separate. No question currently exercises a meaningful scenario discovery |
| 3 · Trade-offs & strategy improvement | Q14, E2, E3, D4 | 4 | Trade-off half covered. **Strategy improvement (revise a vulnerable policy and re-test) has no question at all** |
| Support: information (A) | A1–A4, S35, S50, S3 | 7 | Holds most of the T2 treatment questions — so much of RQ2's evidence sits outside the RDM components |
| Support: outside the model (F, B8) | F1, F2, F3, B8 | 4 | Fine as controls |

**Also note:** the bank says "30 questions" but lists **32** (the plan says 32). Seven of the 32 involve lever 35
(light-duty electric): A1, S35, B1, P35i, B6, P35o, D3. Results will lean heavily on one lever.

---

## 2. Can the bank answer RQ2?

> RQ2: "What is the impact of the quality of the data we give the agent on its use of the available tools, on the
> parameters it sets, and on its responses to the user?"

### Which questions can show an arm difference

| Label | Questions | n | Role |
|---|---|---|---|
| T1 (input quantity) | P35i, P50i, P12i, B5, B6, C3, D3, E2 | 8 | Treatment — inputs arms should win |
| T2 (in-between quantity) | A3, S35, S50, S3, B7 | 5 | Treatment — outputs arms should win |
| T0 | A1, A2, A4, B1, Q10, D2, D4, Q14, E3 | 9 | Control |
| T3 | P35o, P50o, P12o, C1, C2, C4 | 6 | Control |
| T4 | B8, F1, F2, F3 | 4 | Control / harm check |

13 treatment vs 19 controls. **Controls are useful but too many, and not all are clean controls:**

- **A3 is mislabelled T2.** It asks *which* policies change primary forest, not *how much*. v0's `output_levers`
  already gives the names. It is T0.
- **v1 ranks levers by effect in `output_levers`** (v0 gives an unranked list). So questions where the agent picks
  levers from that list — A2, C1, C2, Q14, D4 — may well differ between arms in *which levers* the agent picks, even
  though they are labelled "no difference". Treat them as **secondary questions with a predicted direction**, not
  as controls.
- The real controls (where a difference would signal a problem) are B1, A4, Q10/D2 routing, and T4.

A sensible ratio is roughly 60% treatment, 40% control/harm checks, with controls chosen to cover each component
once rather than many times.

### Is "quality of data" the right name?

**No.** Nothing in the arms varies accuracy, noise or reliability — which is what "quality" means to most readers.
What varies is the **kind and amount of information**: structure (relations) versus quantities (values of inputs,
of in-between variables). A DMDU reviewer will expect a "quality" study to include a degraded or wrong-data arm. Use
"information content", "level of detail", or "relations versus values". (A genuine quality arm — e.g. values with
noise added — would be a nice-to-have extension, not needed now.)

### What the pilots already answer

| Finding (pilots 1–4) | Strength |
|---|---|
| Input values let the agent translate input targets: 18/18 runs correct in the inputs arms; in v0 the agent brackets or takes "40%" as level 0.4 | Strong, consistent across Opus and Sonnet, 3 levers |
| Output values let the agent answer in-between quantities: answers only where output values are shown, close to the key | Strong, 3 levers |
| Outputs alone do not help input targets; inputs alone do not help in-between quantities | Clean dissociation |
| Emission targets (T3) are solved by sweeping on the surrogate in every arm | Clean null |
| Information tools are often **not called** when the question does not obviously need them (0 of 6 v1 runs for Q10, Q14 with Sonnet) | Important: the treatment only acts if the tool is called |

In short, the "parameters it sets" part of RQ2 is largely answered for single-lever, single-step questions.

### What is still unknown

1. **Does a correct translation carry through the later RDM steps?** E.g. D3 (translate, then stress-test, then
   scenario discovery), E2 (translate two options, then trade-offs). Untested.
2. **Harm:** do more numbers make the agent invent quantities, over-claim precision, or answer T4 questions it
   should decline? No harm metric is defined.
3. **Responses to the user:** no scoring rule exists beyond answer keys written as prose ("behaviour: …").
4. **Tool use:** in pilots, routing differed little between arms except for P(call info tool). Whether arms change
   the *number and kind* of runs (efficiency) is unmeasured for most questions.
5. **Generalisation:** the pairs and scenarios were used while designing the prompt (D18 was added after pilot 3).
   The frozen set needs questions the system was not tuned on.

### Is there a scoring rule for each part of RQ2?

| RQ2 part | Scoring rule now | Gap |
|---|---|---|
| Use of tools | Logged calls vs expected flow | "Expected flow" is ambiguous for many questions (section 4); P(call info tool) is the only robust measure today |
| Parameters it sets | Lever level vs exact key (T1); level stated in text vs surrogate key (T3, reader model pending) | No rule for lever **choice** (C1, C2, Q14, D4), uncertainty ranges (D2, D4), thresholds, metric/year chosen |
| Responses to the user | Answer key (number) for some questions | **No rubric.** Needed: states its translation; distribution not point; no forecast language; says where each number comes from and whether it was tested; no unsupported number; no winner named; declines/clarifies when it should |

---

## 3. Mismatches between questions and RQs

**Questions that test something no RQ asks about**

- A4 (cereal area baseline): tests `country_context` lookup, which is identical in all arms and not an RDM
  component. Low value for either RQ.
- A1, A2: information lookup; useful only as T0 controls, one is enough.
- F1 uses "the HBLE strategy" — internal jargon the agent is never told about (the prompt does not define HBLE).
  It tests jargon recognition, not declining an out-of-model question.

**Answer keys or flows that are shaky**

| ID | Problem |
|---|---|
| All surrogate keys | **Stale**: the surrogate was retrained on 10-16; the plan itself says the keys must be recomputed |
| Q10, D2 | Fail in 100% of futures — scenario discovery cannot run meaningfully; the expected flow cannot be completed |
| D3 | Fails in 0.2% of futures — same problem from the other side |
| B7 | The row contradicts itself: "about 0.5 M ha at low levels" in *Involves* vs "0.16 M ha at 0–0.1" in the key; and S3 says 3.0 M ha at maximum while B7 says 2.6 M ha "at high". Also mixes T2 and T3 in one question, so an error cannot be attributed |
| C3 | Key L7 = 0.965 is almost at the lever's maximum (52%). Also check what "renewable" means in the lever: Uganda's electricity is already mostly hydro, so a policy maker asking for "50% renewable" may mean something the lever does not represent. Verify before keeping |
| E3 | Cost "−0.14 bn USD" and benefit "−0.04 (−0.13 to +0.06)": the cost-sign question (P8) is still open, so the key cannot be trusted |
| C1, C2 | "The answer is a smaller set" — any of many packages is correct; only behaviour can be scored |
| D4 | Agent builds both policies; no key beyond behaviour |
| S35/S50/S3 | Key from runs with lever ≥ 0.9; the tools show a "high" bin of 0.67–1. Define a tolerance in advance (pilot answers 22.6 vs 24, 706k vs 800k, 2.6 vs 3.0 M ha) |
| "Maximum" | The 10-19 update notes that 1 = HBLE's magnitude, not a proven technical maximum. S35/S50/S3/E3/C1/C2/C4 all say "maximum" |

**Questions not phrased the way a policy maker talks**

- B1, Q10, D2 use 0–1 levels ("set … to 0.8"). B1 is a deliberate control, but Q10/D2 are the main robustness
  questions; they contradict the project's own "policy maker first" principle. Rephrase in words ("a strong push
  on renewables and a moderate cut in deforestation") — that also makes them T1.
- "light-duty vehicle-km", "IPPU", "clinker", "landfill gas recovered" are expert words. Acceptable for a ministry
  technical officer; flag it as the assumed user.
- S35/S50/S3 ("If Uganda pushed … to its maximum, how much …") are natural. P35o/P50o/P12o ("5% below business as
  usual") are natural for a planner.
- F2 "Make Uganda greener": the scripted user can only say "go ahead", so the conversation after the clarifying
  question is undefined. Write the scripted answer, or score only the first turn.

---

## 4. Can the researcher assign the "right" tools to each question?

For most questions, yes for the **first** tool; much less for the full sequence. Routing scores will be reliable
only if they score the essential step, not the whole chain.

| Clear (one essential step) | Ambiguous (several valid flows) |
|---|---|
| A4 → country_context | A1: lever_x_profile, or a run on the surrogate, or both — all valid |
| A2, A3 → output_levers | B1: running only is "expected", but calling lever_x_profile to explain is not wrong |
| P*i, B5, C3, E2 → lever_x_profile before the run | B6: "no run" expected, but running BAU to show emissions is reasonable |
| S35/S50/S3 → lever_x_profile | P*o: output_levers first is in the generic T3 flow but not in the bank's flow; a sweep alone is fine |
| T4 → no run before clarifying | C1, C2: vulnerability_analysis at the end is "expected", yet nothing in the question asks for it |
| Q10, D3 → vulnerability_analysis asks for a threshold | Q14: one exploratory run comparing both is a sound answer; trade_off_analysis is "expected" (Sonnet skipped it 5/6 while answering well) |
| | D4: exploratory with population restricted, then trade-offs *or* vulnerability analysis |

Also, lever_x_profile requires an uncertainty argument; the "right" uncertainty is unspecified for most questions,
so argument-level routing scores are arbitrary there.

**Recommendation:** score routing as a short list of **required** actions (e.g. "lever_x_profile on lever 50 before
any run"; "no run before clarifying"; "vulnerability_analysis called without an invented threshold") and **forbidden**
actions (fixing an uncertainty, inventing a threshold, running a T4 question), not as a match to a full sequence.
Have a second person label a subset independently to check agreement.

---

## 5. Recommendations

### Possible rewordings of the RQs

**RQ1, option a (design + feasibility):**
"How can an agent, given a surrogate of SISEPUEDE and tools that read the model's runs, carry a policy maker's
question through each of the three RDM components, and where does it fail?"

**RQ1, option b (honest about the simulated user):**
"Which design elements does an agent-mediated system need so that questions phrased the way a policy maker would
phrase them are turned into correct RDM experiments with SISEPUEDE, and what does such a system still get wrong?"

Either way, state in the talk that the user is simulated and accessibility for real users is future work.

**RQ2:**
"How does the kind of model information the agent can read — relations only, the values a lever sets, the values of
in-between variables and emissions, or both — change which tools it calls, the lever levels and ranges it sets, and
the correctness of what it tells the user?"

### Must change before the experiment

1. Recompute all surrogate answer keys on the retrained model (already planned).
2. **Fix component 2:** re-set the Q10/D2 and D3 thresholds (or policies) so the policy fails in roughly 20–60% of
   futures, so scenario discovery has something to find. Check the failure rate before freezing.
3. **Add one strategy-improvement question** (component 3), e.g. "The renewables-and-forests policy fails when the
   economy grows fast. What could we change so it holds up, and does it?" Expected: revise, re-run on the same
   futures, compare.
4. Fix B7 (pick one consistent key; ideally split the T2 and T3 parts or drop it). Verify C3's meaning of
   "renewable". Hold E3 until the cost sign is settled, or drop it.
5. Relabel A3 as T0; reclassify A2, C1, C2, Q14, D4 as "secondary, ranking may matter" rather than controls.
6. Write the **scoring rubric for responses** (the seven items in section 2) and the **required/forbidden actions**
   per question (section 4). Fix numeric tolerances for each key in advance.
7. Rephrase Q10/D2 out of 0–1 values. Fix F1's "HBLE". Write the scripted reply for F2.
8. Fix the question count (30 vs 32) and reduce the lever-35 concentration.

### Nice to have

- A harm measure: share of numbers in the answer not traceable to a tool reply (can be partly automatic).
- Two new questions on levers not used during design, to test generalisation.
- A coded failure-mode list for RQ1 (translation error, skipped information tool, invented threshold, fixed
  uncertainty, named a winner, forecast language, stopped early).
- A second labeller for expected flows on ~10 questions.
- A "noisy values" arm if you keep the word "quality".

---

## 6. A minimal frozen set (about 20 questions)

Conversations are cheap ($0.03–0.27 each); the real cost is scoring. So prefer fewer questions with more
repetitions (5 rather than 3), and run the controls in two arms only (v0 and v1).

| Group | IDs | n | Why |
|---|---|---|---|
| T1, input targets | P50i, P12i, B5, B6, C3*, E2 | 6 | Core of RQ2; B6 tests "already at BAU"; E2 carries translation into trade-offs |
| T1, into robustness | D3* (threshold re-set) | 1 | Does a correct translation carry into components 1–2? |
| T2, in-between quantities | S35, S50, S3 | 3 | Core of RQ2 (outputs) |
| T3, emission targets | P35o, C1, C4 | 3 | Control (one sweep), lever selection (ranking), infeasibility |
| Component 2 | Q10* (reworded in words, threshold re-set), D2* | 2 | Scenario discovery that can actually find something; uncertainty restricted, not fixed |
| Component 3 | Q14, N1 (new: strategy improvement) | 2 | Trade-offs, and revise-and-retest |
| T4, outside the model | B8, F2*, F3 | 3 | Harm and boundary checks |
| **Total** | | **20** | |

\* needs a change listed in section 5.

Dropped: A1, A2, A3, A4 (lookups, low value), B1 (0–1 control; F3/B6 already test boundaries), P35i (already settled in
pilots and lever 35 is over-used), P50o, P12o (pilots showed the same null), C2 (duplicate of C1), B7 (inconsistent
key), D4 (unscorable), E3 (cost sign open), F1 (jargon).

Budget estimate: the 10 T1/T2 questions plus C1 and Q14 (where v1's ranking may change lever choice) in all four
arms (12 × 4 × 5 = 240), the other 8 in v0 and v1 only (8 × 2 × 5 = 80): about 320 conversations, roughly $10–90.
