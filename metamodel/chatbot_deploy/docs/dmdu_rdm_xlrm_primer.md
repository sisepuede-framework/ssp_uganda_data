# Deciding without a forecast: DMDU, RDM and XLRM behind the Explorer

**Uganda Climate Pathways Explorer — methodology primer for the team and reviewers**
Status: draft for expert review · 7 August 2026

## Why this document exists

The Explorer is not a general-purpose climate calculator that happens to have a chat box. It is one
instrument inside a **Decision Making under Deep Uncertainty (DMDU)** process, and specifically inside
a **Robust Decision Making (RDM)** analysis. Almost every design decision in the tool — why there are
levers and conditions rather than one settings panel, why the six official pathways are the ones they
are, why nothing on screen is called a forecast — follows from that.

This document states the method, so that everything the tool says can be checked against it. Its
companion, [`rdm_levers_and_uncertainties.md`](rdm_levers_and_uncertainties.md), is the **catalogue**:
what the 54 levers and 13 uncertainties actually are. This one is the **method**: why they are split
that way, what the numbers on them mean, and what the tool is and is not entitled to claim.

[§12 House style](#12-house-style--how-to-write-about-this-tool) is operational. It governs every word
in the interface and in the assistant's own instructions, and it extends the vocabulary rule already
agreed in [`change_proposal.md`](change_proposal.md) §3.

---

## 1. Deep uncertainty — the condition the method is for

Ordinary risk analysis needs a probability distribution. You can buy insurance against a flood because
somebody can say, defensibly, how often floods of each size occur.

**Deep uncertainty** is the condition where you cannot get that far. The standard definition is that
the parties to a decision do not know, or cannot agree on, (i) the probability distributions over key
uncertain factors, (ii) the model relating actions to consequences, or (iii) how to value the
outcomes. It is not "a lot of risk". It is the absence of the agreement that risk analysis assumes.

Uganda's 2070 is a textbook case. Nobody can hand you a defensible probability distribution over the
country's GDP in 2070, its population, the world price of fossil fuels, or the capital cost of battery
storage. Reasonable, informed people disagree — not about the arithmetic, but about the premises. And
because emissions, costs and development benefits all depend on those premises, so does every number
this tool can produce.

The honest response to that condition is not a better forecast. It is a different way of deciding.

## 2. DMDU — the family of methods

DMDU is the umbrella for approaches built for exactly this condition. The main members:

| Method | Core idea |
|---|---|
| **Robust Decision Making (RDM)** | Stress-test candidate strategies across a very large ensemble of plausible futures; find where they fail; look for strategies that hold up broadly. **This is the method behind this tool.** |
| **Dynamic Adaptive Policy Pathways (DAPP)** | Design a plan as a sequence of actions with pre-agreed trigger points, so it adapts as the future reveals itself. |
| **Info-Gap Decision Theory** | Ask how wrong your best estimate can be before a decision stops being acceptable. |
| **Assumption-Based Planning** | Surface the load-bearing assumptions in an existing plan, and hedge the ones that could break. |
| **Engineering Options Analysis** | Value the flexibility built into physical infrastructure. |

They differ in machinery but share four commitments, and all four are visible in the Explorer:

1. **Many plausible futures instead of one forecast.**
2. **Robustness rather than optimality** — a strategy that does acceptably across many futures beats
   one that is optimal for the single future you happened to assume.
3. **Adaptivity** — plans that can be revised as conditions become clearer.
4. **Deliberation with analysis** — the analysis is embedded in a structured conversation with the
   people who actually decide, not delivered to them at the end.

## 3. The inversion: agree-on-decisions, not agree-on-assumptions

This is the single most important idea in RDM, and the one the interface most needs to carry.

**Predict-then-act** — the conventional order — first seeks agreement on what the future will look
like, then uses that agreement to rank the options. It is sometimes called an *agree-on-assumptions*
approach, because it cannot start until the parties agree on premises. Under deep uncertainty that
agreement never arrives, and the analysis stalls in an argument about assumptions that no evidence can
settle.

RDM inverts it. It is an *agree-on-decisions* approach: begin with the strategies actually on the
table, use models and data to stress-test them over a wide range of plausible paths into the future,
and then use the resulting database of runs to characterise where each strategy is vulnerable and what
could be done about it.

Lempert's formulation of the point is worth keeping close, because it is the sentence this whole tool
is trying to embody:

> RDM is a set of concepts, processes, and enabling tools that use computation, **not to make better
> predictions, but to yield better decisions** under conditions of deep uncertainty.
> — Lempert (2019)

Parties who cannot agree on what 2050 holds can still agree that a particular transition is worth
starting, because they can see that it holds up across the futures each of them believes in. That is
the practical payoff, and it is why RDM works in rooms with genuine disagreement in them.

## 4. Exploratory models, not consolidative ones

Bankes (1993) drew the distinction the rest of this rests on:

- A **consolidative** model gathers what is known into a single package and is then used as a
  surrogate for the real system — it *predicts*. Validating it is meaningful, and its output is an
  answer.
- An **exploratory** model maps a wide range of assumptions onto their consequences without
  privileging any one set. No single run is a prediction. The output is a *landscape*, and the
  reasoning it supports is inductive: what happens if…, and under what conditions does that change?

Exploratory modelling is what you do when no single model can be validated — because data are missing,
theories compete, or the future is irreducibly uncertain. All three apply here.

The Country Development Pathway Model is used **exploratorily**. This is why "what does the model
predict for 2050?" is the wrong question to ask it, and why the tool should never answer as though it
were the right one. The right questions are comparative and conditional: *what changes if…*, *how much
of the difference comes from…*, *does this still hold if growth is faster?*

## 5. The RDM cycle, and where the Explorer sits in it

A full RDM analysis iterates through roughly these steps:

1. **Decision framing** — a structured workshop with stakeholders that produces the **XLRM matrix**
   (§6). This is a deliberation step, not a technical one: participants build a shared understanding of
   the problem, what they can do about it, and what would count as success.
2. **Case generation** — run the model over a large designed ensemble, varying uncertainties and lever
   settings together. Latin Hypercube Sampling is the usual design (§8).
3. **Scenario discovery / vulnerability analysis** — mine the resulting database with algorithms such
   as PRIM or CART to find the *combinations of conditions* under which a strategy fails. This is the
   output policymakers usually find most useful, because it tells them what to hedge against.
4. **Trade-off analysis** — compare candidate strategies on the metrics that matter, including the
   robustness of each.
5. **Iterate** — the findings send everyone back to step 1 with better questions.

**The Explorer occupies steps 2 and 4, and makes them conversational.** Its ~99,000-run training
ensemble is a case-generation exercise already performed; the metamodel lets a user generate and
compare further cases in seconds rather than hours, and read the trade-offs directly.

It does *not* do step 3. Scenario discovery — the formal search for the conditions under which a
strategy breaks — remains the analysis team's own work, and it needs the full run database, not a
conversation. Worth being clear-eyed about: the tool supports the exploration, and a user can find a
vulnerability by hand with a well-chosen question, but it does not systematically map the failure
regions for you.

Nor does it do step 1. Step 1 already happened, and its results are baked into what the tool offers —
which is the subject of §6 and §7.

## 6. XLRM — the framework, and the fact that it is a conversation

RDM organises a problem into four elements, conventionally laid out on a 2×2 matrix and **co-created
with stakeholders in a workshop** (Lempert, Groves, Popper & Bankes, 2006):

| | Element | Definition |
|---|---|---|
| **X** | Exogenous uncertainties | External factors beyond the decision-maker's control that can nonetheless determine whether a strategy succeeds. |
| **L** | Policy levers | The near-term actions or decisions the decision-makers can actually take to influence events. |
| **R** | Relationships | The models linking levers and uncertainties to consequences — how the system evolves. |
| **M** | Metrics / measures | The performance standards used to judge whether an outcome is desirable. |

Two things about this deserve more emphasis than they usually get.

**The matrix is elicited, not derived.** In the LAC practice this project descends from — Costa Rica,
Peru, Chile, Colombia, the Dominican Republic, Ecuador, Guatemala — the XLRM matrix is built in a
plenary-plus-working-tables workshop, with ministries, agencies, academia, business and civil society
at the tables, working through guided questions sector by sector. What ends up in the **L** column is
what the people in the room said they can do and want to do. What ends up in **X** is what they said
they are exposed to and cannot control.

**So the L/X split is a political fact as much as a modelling one.** It records who has agency over
what. When the Explorer shows "what Uganda decides" on one side and "what the world decides" on the
other, it is not a UI metaphor — it is the structure of the decision, as the people making it
described it.

**And the boundary is negotiable, which is itself informative.** Fossil fuel prices are an X for
Uganda; for a large exporter they might be closer to an L. Where a country draws that line says
something real about its room for manoeuvre.

## 7. Where the six official pathways come from

This follows directly from §6, and the interface should say so.

The six official pathways are **curated, not generated**. They are not six points sampled from the
space; they are positions that came out of conversations with policy actors about which transitions
are achievable, which are wanted, and what has already been committed to — the NDC ambitions, the
unconditional portion Uganda can deliver without external support, and the High Benefits, Low Emission
frontier that provides the analytical basis for NDC 3.0. Each was then run through the CDPM in full.

That is why they are the reference points and why "official pathway result" means something. They
carry institutional weight the metamodel cannot manufacture.

**And it is why the metamodel exists.** Deliberation does not stop at the six. Somebody asks what
happens *between* two of them, or *beyond* the frontier in one sector only, or what any of them looks
like if growth is faster than the central case assumed. Under predict-then-act those questions wait
for the next modelling round. Here they are answerable immediately, clearly labelled as estimates.
That pairing — authoritative curated runs, plus a fast surface for the questions deliberation actually
throws up — is what the tool is for.

## 8. What a lever is: an effect, not an instrument

**A lever is the modelled effect a policy is meant to produce, not the policy.**

Setting `Reduce DEFORESTATION` to 0.9 does not name a law, a budget line, or a programme. It describes
a state the land-use system arrives at by 2070, reached by a ramp over roughly 20–30 years rather than
a switch thrown today. How Uganda would get there is a separate question, and the model does not
answer it.

Two consequences, both of which matter to a policymaker reading a result:

- **One lever, many possible policies.** A given lever setting could be delivered by a tax, a
  performance standard, a subsidy, a procurement rule, a tenure reform, an enforcement budget, an
  information campaign, or several of these together. They differ enormously in cost, political
  feasibility, administrative burden, speed, and who bears the burden — **none of which this model
  represents**. Two routes to the same lever setting look identical here and are not identical in
  Uganda.
- **One policy, many levers.** The reverse is just as true. A serious clean-cooking programme moves
  cooking fuel demand, forest-land removals, household energy spending and indoor air quality at once.
  Real policies rarely map one-to-one onto the catalogue.

So the model tells you **what a transition would be worth if it happened**. It cannot tell you how to
make it happen, what it would take politically, or which instrument to reach for. That handoff — from
"this transition is worth achieving" to "here is the policy that achieves it" — is the reader's work,
and it is where the model's usefulness ends and a policymaker's judgement begins.

## 9. What 0 to 1 means: a sampling coordinate, and a relative one

Every lever and every uncertainty in this tool runs 0 to 1. That scale is **an artefact of how the
experiment was designed**, and reading it as a physical quantity is the most inviting mistake the tool
offers.

**Where the numbers come from.** SISEPUEDE explores its input space by Latin Hypercube Sampling — a
design that spreads sample points evenly across many dimensions at once, so a manageable number of
runs still covers the space. The values the metamodel was trained on are those sample coordinates,
read directly from the run's own design tables (`ATTRIBUTE_LHC_SAMPLES_LEVER_EFFECTS.csv` and
`ATTRIBUTE_LHC_SAMPLES_EXOGENOUS_UNCERTAINTIES.csv`; see `metamodel/README.md`, "Build predictor
features from LHS samples"), normalised to `[0,1]`. A lever's coordinate is then converted to a
transformation magnitude by

```
T = 0.9 × x + 0.1
```

and applied as a 2070 target that SISEPUEDE ramps toward over roughly 20–30 years.

**What that means when you read a result.** A lever at 0.9 is **a position near the ambitious end of
the range this study explored**. It is not 90% of anything. It does not name a number of stoves, a
share of the vehicle fleet, a budget, or a coverage percentage. There is no "100%" in the world for it
to be 90% of — the upper end of the range is a modelling judgement about what is technically feasible
by 2070, made when the experiment was designed.

**What it is genuinely good for.** This is a real capability, not a consolation prize. You can ask
what an *effective* intervention does in this system, and what a *very* effective one does, and see
how the answer propagates: which sectors move, what it costs, what comes back as development benefits,
how much of the gap to the frontier it closes. Comparisons across settings, across sectors and against
BAU and HBLE are all meaningful. It is the absolute reading — "0.9 means 90%" — that is not.

**This applies to the levers and the conditions alike.** The tool has always said it about the X's:
GDP growth at 0.8 means "toward the high end of the range the model explores", not "GDP is 80%
higher". The same caution applies to every L, for the same reason.

**Where to go when someone needs the physical answer.** They should. `get_scenario_variables` returns
the actual SISEPUEDE input-variable trajectories a lever moves, 2015→2070 — the concrete "what
changes, by how much, by when" behind a coordinate. That is the honest bridge from a sampled position
to a physical magnitude, and the tool should offer it rather than inventing a percentage.

## 10. Decision support means the decision stays with the reader

The Explorer is a decision-support tool. Everything about how it should speak follows from taking that
literally.

**What it can do.** Show what follows, in emissions, costs and development benefits, from a set of
choices under a set of conditions. Make comparison cheap. Make the difference between an official
result and an estimate visible on every answer. Let someone test whether a conclusion survives a
different future — which is the RDM question.

**What it cannot do, and must not appear to do.** It has no representation of political feasibility,
of financing or fiscal space, of institutional and administrative capacity, of who wins and who loses
within Uganda, of sequencing and timing beyond the 2070 target, or of the policy instruments in §8. A
pathway that looks excellent here can be undeliverable for reasons entirely outside the model.

**On robustness.** Robustness is a property to look for, not a score this tool computes. The tool can
show that a transition holds up across the conditions you tried; it cannot certify that a strategy is
robust, because that depends on the futures you chose to test and on what you decided counted as
acceptable — both of which are the reader's judgements, not the model's.

**So it does not rank and it does not recommend.** Not because of caution for its own sake, but
because the criteria that would decide the ranking — what Uganda values, what it can finance, what it
can administer, what it can get through a cabinet — are outside the model. Presenting outcomes and
trade-offs clearly, and leaving the choice where it belongs, is the more useful thing to do as well as
the more honest one.

## 11. How this maps onto the Explorer

| | In RDM | In this tool |
|---|---|---|
| **X** | Exogenous uncertainties | **13 country conditions** — GDP growth, population growth, fossil fuel prices, agricultural export volumes, four technology capital costs, five demand elasticities. 0 = low end, 0.5 = median (the default), 1 = high end. |
| **L** | Policy levers | **54 sectoral transitions across 16 sectors**, each a SISEPUEDE transformation. 0 = no action, 1 = maximum technically feasible deployment by 2070, via a ramp. |
| **R** | Relationships | **Two layers.** The **CDPM** itself, built with SISEPUEDE — six official pathways have been run through it and stored; those are **official pathway results**. And the **metamodel** (XGBoost, trained on ~99,000 CDPM runs), which answers combinations never officially run; those are **metamodel estimates**. Every answer says which it is. |
| **M** | Metrics | Emissions across the **23 official inventory categories**; **3 cost types**; **16 development-benefit types**; cost and benefit as a share of GDP. Reported at 2025, 2035, 2040, 2050 and 2070, always against the official BAU pathway with the official HBLE pathway as the frontier. |

The catalogue itself — every lever and every condition, with its SISEPUEDE transformation code — is in
[`rdm_levers_and_uncertainties.md`](rdm_levers_and_uncertainties.md) §5. It is generated from
`backend/feature_registry.json`, the same file the assistant reads when it builds its own
instructions, so the two cannot drift apart.

## 12. House style — how to write about this tool

Operational. This governs the interface, the assistant's system prompt, and these documents. It
**extends** the vocabulary rule in [`change_proposal.md`](change_proposal.md) §3, which stays in force
unchanged.

### 12.1 The added rules

| Never write | Write instead | Why |
|---|---|---|
| "predicts", "will be", "forecast", "projection" | **estimates**, "under these settings", "in this future" | §4 — the model is exploratory. A run is a conditional consequence, not a prediction. |
| "recommends", "the best pathway", "you should", "the optimal…" | describe the outcomes and the trade-offs; leave the choice with the reader | §10 — the criteria that would decide it are outside the model. |
| a lever *is* a policy; "the deforestation policy" | a lever is the **modelled effect** a policy is meant to produce | §8 — many instruments could deliver one lever; one policy usually moves several. |
| "0.9 = 90% of X"; any percentage gloss on a lever value | **a position in the sampled range** — near the ambitious end of what this study explored | §9 — the scale is an LHS coordinate, not a quantity. Offer `get_scenario_variables` for physical trajectories. |

### 12.2 Register

- **Provenance before magnitude.** Say what kind of answer this is before you say what it contains.
- **State the settings.** If the assistant interpreted "ambitious transport" as particular lever
  values, it says which — so the reader can disagree. An interpretation presented as a fact is not
  decision support.
- **Conditional, not declarative.** "Under this combination, emissions reach…" rather than "emissions
  will reach…".
- **No product voice.** No promissory framing, no speed or convenience claims, no "powered by". The
  tool is an instrument in a policy process; it should sound like one.
- **Robustness language is encouraged** — "holds up across these conditions", "this is where it breaks
  down". It is the DMDU frame, and the model can genuinely support it. What it must not do is score
  robustness on the reader's behalf (§10).
- **Plain over technical where both are true.** "What Uganda decides" and "what the world decides"
  carry XLRM correctly to a reader who has never heard of XLRM. Prefer that.

## 13. References

1. Lempert, R. J. (2019). "Robust Decision Making (RDM)", ch. 2 in Marchau, Walker, Bloemen & Popper
   (eds.), *Decision Making under Deep Uncertainty: From Theory to Practice*, Springer (open access).
   <https://link.springer.com/chapter/10.1007/978-3-030-05252-2_2> — the source of the
   agree-on-assumptions / agree-on-decisions framing and the "not better predictions, but better
   decisions" formulation in §3.
2. Lempert, R. J., Groves, D. G., Popper, S. W., & Bankes, S. C. (2006). "A General, Analytic Method
   for Generating Robust Strategies and Narrative Scenarios." *Management Science*, 52(4), 514–528.
   <https://doi.org/10.1287/mnsc.1050.0472> — the source of the XLRM framework. Note for the client:
   David Groves, who reviewed this tool, is a co-author.
3. Bankes, S. (1993). "Exploratory Modeling for Policy Analysis." *Operations Research*, 41(3),
   435–449. <https://doi.org/10.1287/opre.41.3.435> — the consolidative / exploratory distinction
   in §4.
4. Quirós-Tortós, J., Víctor-Gallardo, L., Rodríguez-Arce, M., & Soto-Rodríguez, A. (2024). *Using
   Robust Decision-Making to Develop Long-Term Strategies: A Practical Guide.* 2050 Pathways Platform
   / Climate Lead Group. <https://2050pathways.org/> — the closest published account of the process
   this project descends from: the XLRM workshop format, the LAC case studies (Costa Rica, Peru,
   Chile, Colombia, Dominican Republic, Ecuador, Guatemala), and SISEPUEDE named among the tools.
   Source for §5 and §6.
5. RAND Corporation, *Robust Decision Making*, in **Tools for Decision Making under Deep Uncertainty**
   (TL-320). <https://www.rand.org/pubs/tools/TL320/tool/robust-decision-making.html>
6. weADAPT, *Robust Decision Making: XLRM framework* — short practitioner explainer.
   <https://weadapt.org/knowledge-base/adaptation-decision-making/xlrm-framework/>
7. SISEPUEDE documentation. <https://sisepuede.readthedocs.io/> — the modelling framework underlying
   Uganda's Country Development Pathway Model.

## 14. Reviewer notes

Space for the team. Please note who you are and the date.

-
