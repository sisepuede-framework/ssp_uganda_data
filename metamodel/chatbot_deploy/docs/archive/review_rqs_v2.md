# Review: research questions, version 2

*Independent review, 2026-10-19. Read: `docs/review_questions_vs_rqs.md`, `docs/question_bank_v2.md`,
`docs/rdm_information_layer_plan.md` (Pilot 3, Pilot 4, Update 2026-10-19), `backend/rdm/harness/prompt.py`,
`backend/rdm/harness/registry.py`. No other file was changed.*

> **RQ1:** "How do we integrate a surrogate model of SISEPUEDE and an AI agent into a system that carries questions
> asked by a non-technical person through the three components of RDM (exploratory modeling, vulnerability analysis
> and trade-off analysis)?"
>
> **RQ2:** "What is the impact of the type of information we give the agent about the model on its use of the
> available tools, on the parameters it sets, and on its responses to the user?"

## Short version

- **Both RQs are better than the originals.** "Type of information" fixes the "quality" problem. "Integrate … into a
  system" makes RQ1 an honest design question.
- **RQ1 still has three problems, all fixable with a few words:**
  1. "Questions asked by a non-technical person" still says that a real person asked. No one did: the researcher wrote
     the questions and a script plays the user.
  2. The intent to *test* such systems, which is half of the stated contribution, is not in either RQ.
  3. The parenthetical leaves out scenario discovery and strategy improvement, which the system does and which
     the question bank tests (D3b and Q10b for scenario discovery, N1 for strategy improvement).
- **RQ2 is answerable and partly answered already** (pilots 3 and 4). "Impact" is justified, because the arms are
  a controlled manipulation. Two of its three outcomes have scoring rules. The third, "responses to the user", has
  per-question rules but no general rubric yet.
- **They fit together** if RQ2 is presented as the experiment *inside* RQ1: one part of the design, varied on purpose.
- **Recommendation:** keep both, with minimal edits (section 5).

---

## 1. Does each RQ ask something clear and answerable?

| | What is asked | Answerable with this study? | What counts as an answer |
|---|---|---|---|
| RQ1 | A design: how to combine a surrogate and an agent so that a question moves through RDM | **Yes, as a design question.** The answer is the architecture and the evidence of where it works and where it breaks | (a) The architecture: 7 tools, information versus technical tools, rules enforced in code (no fixed uncertainty, threshold belongs to the user, levels within the explored range), the prompt and its rules, the translation step. (b) Per RDM component: the share of bank questions where the "must" actions happen and the "must not" actions are avoided. (c) A list of the failures seen and what fixed them (decision log D1–D19, pilot fixes, the D18 paragraph) |
| RQ2 | The effect of one design choice (what the agent can read about the model) on three behaviours | **Yes.** The 2 × 2 arms, an identical prompt and identical tool schemas make it a controlled comparison | For each outcome, the difference between arms on the questions where a difference is predicted (T1, T2), and no difference on the controls (T0, T3, T4) |

The main risk for RQ1 is that "how do we integrate" can be answered with "like this" and nothing else. The design
needs evaluation criteria next to it: a success rate per component and a list of failure types. Without them,
a DMDU reviewer will read RQ1 as a system description, not a research question.

## 2. RQ1 in detail

**"How do we integrate" is a design question.** That is legitimate (design-science research), and the DMDU
community is used to "how do we build a decision support process" contributions. A clear answer has two parts:
the artefact, and evidence of how well it does what it should. The study has both. The second part is thin for
components 2 and 3 (3 and 2 questions out of 21), so state the evidence for those as illustrative, not as rates.

**"Carries questions … through the three components" is measurable, but only per question and per component.**
A question is never carried through all three components: Q10b → D2b → N1 is the only chain that crosses
components 1, 2 and 3, and it does so across several turns. Operationalise it as: *for each component, does the
agent take the required step on the questions that call for it?* That is what the must / must-not scoring already does.
Say so in the methods, or readers will expect end-to-end runs through all three components.

**The non-technical framing still over-promises.** The questions are *written to sound like* a policy maker. Real
policy makers did not ask them, and the user's replies are scripted ("go ahead", a threshold). The bank also uses
expert words: "clinker share", "light-duty vehicle-km", "no-till", "conservation agriculture". The assumed user is closer to
a ministry technical officer than to a non-technical person. "Questions phrased as a policy maker would ask
them" is accurate. "Asked by a non-technical person" is not. The prompt itself says "policy makers", which also
matches the project's "policy maker first" principle.

**The "testing" part of her intent is missing.** She wants to propose a way "to design *and test*" such systems.
The test method is a real contribution:
- a simulated user;
- a question bank labelled by what has to be translated (T0–T4) and spread across sectors and RDM components;
- answer keys computed from the surrogate and the input table;
- must / must-not scoring;
- arms that switch one part of the design on and off.

Neither RQ names it. RQ2 *uses* the test method but asks about the information layer, not about the method.
The cheapest fix is to add "and how do we test it" to RQ1. The alternative is to state it as a contribution, not an RQ.

**Strategy improvement and scenario discovery are dropped from the parenthetical.** The system prompt lists the
three components as "exploratory modeling and stress testing", "vulnerability analysis and scenario discovery",
and "trade-off analysis and strategy improvement". The RQ keeps only the first half of each. The bank has a
strategy-improvement question (N1) and three questions that end in scenario discovery. The RQ therefore
understates the work. Scenario discovery is also the step DMDU people most associate with RDM.

**A DMDU-specific risk: RDM usually has a framing step.** Most accounts of RDM start with decision framing (XLRM).
Here XLRM is fixed by the model: 54 levers, 13 uncertainties, the emission and cost metrics. Part of what the agent
does, translating the user's words into levers, levels and uncertainty ranges, *is* a per-question framing step
inside that fixed XLRM. Someone in the audience will ask "what about framing?" Prepare one sentence for it
("the frame is fixed by the model; the agent maps each question into it"). It is a strength, not a gap.

**Wording and grammar:**
- "A surrogate model of SISEPUEDE": SISEPUEDE is a framework, and the surrogate copies the Uganda model built with it
  (the prompt calls it the Country Development Pathway Model). For this audience, "a surrogate of SISEPUEDE" is
  acceptable shorthand. Add "for Uganda" if you want precision.
- RQ1 names two parts, the surrogate and the agent. RQ2 then refers to "information we give the agent about the model",
  which RQ1 never introduced. The information tools are a third part of the system, and RQ2 is about them. This is a
  small gap in the logic, not an error. See alternative 1b.
- The parenthetical works grammatically. It just lists the wrong (shortened) names.

## 3. RQ2 in detail

**"Type of information … about the model"** is clearer than "quality", but a DMDU reader will not guess what the
types are. It could mean documentation, equations or data. One parenthetical solves it: relations between
variables only, or also their values. "Type" also hides that the design is 2 × 2 (input values × output values).
Show the four arms on a slide, not in the RQ.

**Are the three outcomes measured?**

| Outcome | Measured by | Status |
|---|---|---|
| Use of tools | must / must-not actions (e.g. "must read lever 50 before running"); P(calls an information tool) | **Measurable.** Pilots show it matters: information tools were skipped in 0 of 6 v1 runs for Q10 and Q14, so effect = P(call) × effect given the call. Report both parts |
| Parameters it sets | exact lever-level keys for 7 T1 questions; LV2 level; GDP range restricted, not fixed (D2b); threshold asked, not invented | **Measurable.** Numeric tolerances still to fix before the run. Note "parameters" is ambiguous for modellers: in SISEPUEDE usage parameters are often the uncertain inputs. Here it means lever levels, uncertainty ranges and thresholds |
| Responses to the user | number keys for T2 (S50, S3, S35) and AG1 (sign of the effect); must-say items (LV1 range limit, B6 already above BAU, C4b infeasible) | **Partly.** No general rubric yet (states its translation, gives a range rather than one number, no forecast language, gives the source of each number, no unsupported numbers, names no winner). Write it before the run, or this third outcome will be the weakest |

**Where RQ2's evidence comes from.** Arms are predicted to differ on about 10 of 21 questions (7 T1, 3 T2), plus
AG2, where v1 ranks levers. The RDM-component questions (Q10b, D2b, N1, Q14b) are mostly controls. D3b is the only
question that carries a translation into vulnerability analysis and scenario discovery. In practice, then, RQ2 says
"information changes translation", and only one question tests whether that carries into robustness results. That is
fine, but say it.

**Is "impact" justified?** Yes, within the setup:
- Each arm switches one thing: the values the information tools return.
- The prompt and the tool schemas are identical in every arm (stated in `prompt.py` and `registry.py`).
- Each question is repeated.

That is a controlled experiment, and causal language about *this system* is fair. Limits to state:
- one or two LLMs (Sonnet, Opus);
- 3–5 repetitions per cell, so report rates with intervals;
- the prompt was tuned on pilot questions (D18 was added after pilot 3);
- effects are conditional on the agent calling the tool.

"Effect" is slightly more neutral than "impact". Either is fine.

## 4. Do RQ1 and RQ2 fit together and match the contribution?

They fit as **design (RQ1) → one controlled test of one design choice (RQ2)**. Present RQ2 as a sub-question:
"Within that system, what difference does the information layer make?" Two things weaken the fit now:
1. RQ1 does not name the information layer that RQ2 varies.
2. Neither RQ names the test method, which is the "test such systems" half of the contribution.

On "one of the first": the claim is plausible for *RDM specifically* (agent + surrogate + the full RDM cycle). Check
the recent literature on LLM agents with energy-system models, integrated assessment models and the EMA Workbench
before saying it aloud. "Among the first" is safer than "the first".

## 5. Recommendations (minimal edits only)

Keep the structure and her wording. Changes are shown as ~~removed~~ → **added**.

### RQ1, alternative 1a (recommended): honest user, adds testing

"How do we integrate a surrogate model of SISEPUEDE and an AI agent into a system that carries questions
~~asked by a non-technical person~~ → **phrased as a policy maker would ask them** through the three components of
RDM (exploratory modeling, vulnerability analysis and trade-off analysis)**, and how do we test such a system**?"

*Why:* this fixes the over-promise (no real person asks), puts "test" into the RQ to match her stated intent,
and keeps everything else word for word.

### RQ1, alternative 1b: full component names, information layer named

"How do we integrate a surrogate model of SISEPUEDE**, information about the model,** and an AI agent into a system
that carries questions ~~asked by a non-technical person~~ → **phrased as a policy maker would ask them** through the
three components of RDM (exploratory modeling**/stress testing**, vulnerability analysis**/scenario discovery** and
trade-off analysis**/strategy improvement**)?"

*Why:* it restores scenario discovery and strategy improvement, which the system and the bank actually cover, and
it introduces what RQ2 varies. It is longer. If 1a is used, put the full component names on the slide instead.

### RQ2, alternative 2a (recommended): say what "type" means

"What is the impact of the type of information we give the agent about the model **(how its variables are related,
or also their values)** on its use of the available tools, on the parameters it sets, and on its responses to the user?"

*Why:* it tells a non-AI audience what the arms vary, using only words they already know.

### RQ2, alternative 2b: plain words for "parameters"

"… on its use of the available tools, on the ~~parameters~~ → **policy levels and uncertainty ranges** it sets, and on its
responses to the user?"

*Why:* to modellers, "parameters" can mean the model's uncertain inputs. This names what is actually scored. Use it
only if the RQ stays short enough with 2a.

### Must do whatever wording is chosen

- In methods and in the talk, say that the user is simulated and that accessibility for real users is future work.
- Write the general response rubric (section 3) before the full run.
- Define "carries through" as per-component success on must / must-not, and present component-2/3 evidence as
  illustrative given n = 3 and n = 2.

### One sentence for the talk

> "We built an AI assistant that sits on top of a fast copy of SISEPUEDE and takes a question in a policy maker's
> own words through an RDM analysis — and, just as important, a way to test whether it does that correctly before
> anyone relies on it."
