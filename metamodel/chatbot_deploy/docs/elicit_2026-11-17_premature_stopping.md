# Why retrieval agents stop early: evidence on stopping, answer substitution and information design

## What the evidence establishes

**Premature evidential closure is well documented; the specific claim that an answer-like intermediate number causes it is much less directly tested.** Search agents can declare completion while requirements remain unverified, and selectively forcing further retrieval on under-covered trajectories can improve answers. These findings support a distinction between *having encountered relevant information* and *having enough evidence to answer the actual question*. They do not, by themselves, establish that a percentage, proxy or partial numerical value triggers termination. [^1][^2]

The closest evidence suggests several separable failures: misjudging sufficiency; favoring evidence that resembles the original question; losing the connection to an unanswered subquestion; answering from the wrong source after the correct computation; and persisting with a preferred tool instead of switching. Interventions exist for each, but improvements in aggregate QA accuracy should not be relabeled as reductions in premature stopping unless stopping was actually measured. [^3][^4][^5][^6][^7]

**For the proposed DMDU mechanism, the defensible conclusion is “consistent with related evidence, but not yet directly established.”** Within the examined studies, no controlled experiment isolated the full chain: an intermediate numerical quantity is shown; it resembles the requested target but differs in meaning or units; the agent stops because of that quantity; and the correct target remains reachable through further graph navigation. Evidence-source substitution, source preferences and incomplete verification are relevant comparators, not substitutes for that experiment. [^6][^8][^1]

The accompanying evidence map distinguishes direct stopping studies from adjacent studies of evidence selection, graph navigation, numerical verification and tool trust. It also marks abstract-only assessments explicitly.

## 1. What makes an agent stop before sufficient evidence?

### The most direct evidence concerns sufficiency judgments, not numeric proxies

*When Is Enough Not Enough? Illusory Completion in Search Agents* identifies bare assertion, overlooked refutation, redundant searching ending unresolved, and premature exit with an unaddressed constraint. Its LIVELEDGER intervention exposes current verification states during execution. Accuracy increased by **2.2–11.6 percentage points** across the tested configurations. This is direct support for making unresolved requirements visible, although the state tracker is itself fallible. [^1]

SeekBench independently annotates whether search-agent steps are grounded, recover from poor evidence and assess sufficiency correctly. It reports overconfident answering before sufficient evidence in **76.5% of RL-agent trajectories**. That is a benchmark-specific rate from an expert-annotated trace sample, not a population estimate for all agents. The study diagnoses behavior; it does not randomize exposure to answer-like intermediate values. [^3]

*HALT: Verification-Aware Stopping for Retrieval-Augmented Search Agents* provides a more intervention-oriented test: keep the search agent frozen and use per-hop claim–evidence coverage to change the halt/continue decision. Selectively continuing trajectories that stopped before coverage improved exact match. The study distinguishes deployable question-generated claims from gold-claim diagnostics; neither the verifier nor the planned claim set should be treated as a guarantee of complete, correct evidence. [^2]

A different failure is premature *unavailability*. The WebDetective study reports agents concluding that an answer was unavailable after limited unsuccessful search, despite viable paths remaining. Its qualitative analysis says an explicit “please continue searching” instruction did not restart those searches. This is particularly close to a false “the tools do not contain that information” response, but it is not a controlled estimate of continuation-prompt effectiveness. [^9]

### More search is not a general solution

The converse failure also occurs. A diagnostic study separates missing evidence from evidence that was retrieved but not successfully used, and observes long, low-yield searches in some unsuccessful trajectories. Stop-RAG likewise finds benefits from a learned stop/continue controller in its own pipeline but not uniformly when transferred to another pipeline. The goal should therefore be evidence-sensitive termination, not a minimum number of calls. [^10][^11]

A particularly useful counterexample is *Beyond Retrieval Failure*. With the retriever, corpus and generator fixed, an open-subquestion register recovered more required evidence, but premature resolutions and abstentions increased as missing-evidence failures declined. Better retrieval guidance did not automatically repair the decision to answer. This paper was assessed from its abstract only. [^5]

## 2. Do agents substitute related quantities, and does question wording change this?

### Related evidence exists, but the exact percentage-for-amount mechanism remains a gap

The closest scientific-model comparator is *Same Simulation, Different Evidence*. Agents used the deterministic PHREEQC simulator; replayed calls indicated that keyed values were computed about as often across conditions, while agents changed which output they used for their final answer. Under report retrieval, they sometimes skipped the report, used higher-precision output files and rounded to a neighboring multiple-choice option. The authors call this **evidence substitution**. It concerns the same target quantity represented through different outputs and precision, not substitution of a share for an absolute amount. Only the abstract was available for this assessment. [^6]

That distinction matters. “The answer was computed but the agent reported from another source,” “the agent selected the wrong metric,” and “an intermediate metric caused early termination” require different evidence. VeriFin addresses the second problem by independently grounding financial facts, periods, units and formulae before numerical verification. It shows the value of checking those semantics, but does not demonstrate that encountering a related quantity caused search to stop. [^12]

Question formulation clearly affects the evidence a system treats as relevant. The strongest directly relevant study finds that original-question scoring favors a named bridge entity over the unnamed answer-bearing entity, while decomposition changes later-hop evidence identification. However, it does **not** measure whether alternative wording changes the rate of percentage-for-amount substitution. WebDetective also shows why explicit path or entity hints change the nature of a search task, but comparisons between benchmark styles are not a matched rephrasing experiment on identical questions. [^4][^9]

**Answer to subquestion 1:** there is evidence for wrong-source use, metric/unit-sensitive answer errors and wording-sensitive evidence selection. The examined studies do not establish a causal estimate for the specific sequence “proxy quantity encountered → target substituted → navigation terminated,” nor how rephrasing changes that rate. [^6][^12][^4]

## 3. How does lexical overlap affect multi-hop retrieval and navigation?

### Overlap helps anchor a search but can favor the wrong hop

*Verification Without Sufficiency* supplies the clearest multi-hop result. In bridge questions, the original wording names an initial entity or work, while the answer lies in a later passage about another entity. Similarity and verification signals favor the question-named bridge passage; the deficit disappears on comparison questions naming both entities. Filtering evidence using original-query relevance can therefore remove material needed to complete the chain. This is a retrieval/selection failure, not necessarily an agent choosing to terminate. [^4]

Conditioning verification on a gold decomposed subquestion raises reported later-hop identification AUC from **0.546 to 0.840**. A deployable decomposer using the question plus an initial retrieved passage reaches **0.637**, illustrating the gap between knowing the intended hop and generating it reliably. These values measure evidence identification, not final-answer accuracy or stopping rates. The paper reports endpoint/lift figures that should not be combined into a new arithmetic effect estimate without further checking; only the stated endpoints are used here. [^4]

There is also evidence that answer construction favors question-like material after retrieval. *Blinded by Generated Contexts* finds that models can prefer incorrect generated passages over correct retrieved passages. Greater question–context similarity is associated with stronger preference, and controlled context-completeness comparisons show that semantic completeness also contributes. Similarity here is partly an observed association, not an independently randomized renaming intervention. [^13]

At tool selection, BiasBusters finds that query–description similarity and ordering influence selection among equivalent APIs; changing descriptions or prompt wording shifts preferences. That is useful evidence that naming and wording shape an agent's available path, but it does not quantify how renaming a target variable affects eventual arrival at that node in a model graph. [^14]

**Answer to subquestion 2:** lexical and semantic overlap can help identify a starting point while biasing retrieval toward named, intermediate evidence. There is no justified universal monotonic rule that more overlap with the original question produces better multi-hop completion. Evidence on exact variable-name interventions and stopping should be distinguished from evidence on passage relevance or tool choice. [^4][^13]

## 4. What instruction and information-design interventions have been tested?

### Explicit evidence states and coverage requirements: the closest stopping evidence

LIVELEDGER compares visible constraint states with baseline agents and also includes a test-time continuation comparator. The ledger configuration retained an accuracy advantage over continuation prompting; simply extending reasoning added many turns for a smaller gain. This is not an equal-information, equal-compute comparison, so it does not prove that changing information is intrinsically superior to changing instructions. HALT supplies complementary evidence that an explicit coverage predicate can improve the decision to continue. [^1][^2]

FAIR-RAG uses required-finding checklists and gap-targeted refinement, and its error analysis still identifies premature sufficiency judgments. It is relevant as an operational recipe, but its sufficiency and query-refinement components were not separately removed, so its end-to-end QA gains cannot be attributed specifically to the checklist or to reduced premature stopping. [^15]

### Navigation guidance and visible structure: relevant, but usually measured through QA

GraphReader ablates its rational plan and compares reasoned with random node selection; the ablations reduce QA performance. Guidance Graph exploration separately tests richer semantic target descriptions and removes structural/pruning components. These are useful precedents for explicit navigation targets and structural guidance, but neither isolates an intermediate value's ability to look like a final answer. [^16][^17]

A cleaner visibility comparison varies how many prior hops the relation-selection prompt sees while the controller retains the complete path. Bounded Path Context finds that shorter histories can match or exceed full-history prompting, including fewer “no relevant path” returns in a WebQSP comparison. The authors disclose a serving-configuration confound in their separate CWQ comparison. This cautions against assuming that exposing more history always improves navigation. [^18]

Two abstract-only studies are especially relevant to signposting. CorpusMap adds entity pages linking otherwise disconnected documents and reports better evidence discovery and answers than raw-corpus search. Connection-aware pruning preserves evidence chains rather than retaining only highly question-similar snippets, with comparisons under identical token budgets. These test navigation structure and evidence visibility, not isolated labels such as “input,” “intermediate result” or “final quantity.” [^19][^20]

### Returned feedback: actionable content matters more than formatting alone in a close comparator

*Structured Feedback Improves Repair in an LLM Agent Loop* compares raw diagnostics with location, observed value and admissible alternatives. Ablations locate most of the benefit in the alternatives; prose containing the same repair values reaches similar success to keyed records. The keyed condition also changes framing and adds a failure label, so even this relatively careful comparison is not a pure serialization experiment. This is evidence from sequential action repair, not directly from graph-QA stopping. [^21]

QueryAgent likewise combines intermediate execution feedback with error-specific guidance rather than relying only on a generic instruction to self-correct. Its results support targeted recovery feedback, but do not isolate instructions from observations. Butterfly Effects in Toolchains shows that perturbing documentation, queries and tool returns changes parameter-filling failures; it is a robustness study, not evidence that a particular beneficial labeling scheme prevents early stopping. [^22][^23]

### Provenance and scope labels: promising, but outcome- and model-dependent

In the PHREEQC study's abstract, naming the authoritative output improved accuracy by **6.3–7.9 percentage points** over plain retrieval for the tested GPT models; a request for correct rounding did not. This is unusually close to the distinction between telling an agent to be careful and telling it which evidence answers the question. But without full text, matched content, context budget and precise intervention placement cannot be fully assessed. [^6]

Other comparisons show why there is no universal winner. A retrieval-refusal study finds some agents respond strongly to refusal information inside a tool observation, while other models respond more to system instructions or answer from memory. Its gold passages are deliberately absent: it tests appropriate abstention, **not** false refusal when an answer remains reachable. A tool-registry study also compares warnings/disclosures and structured capability fields, but those experiments use different outcomes and cannot establish a clean ranking of instruction versus information design for stopping. [^24][^25]

### Information foraging is an empirical LLM research direction, not yet a validated label recipe

InForage explicitly applies information-foraging theory through outcome rewards, intermediate evidence-acquisition rewards and an efficiency penalty. Reward ablations contribute evidence that intermediate acquisition deserves supervision rather than judging only the final answer. It does not test whether an “answer lies two hops ahead” label, input/result labels, or numerical concealment prevents premature stopping. Its efficiency penalty also reinforces that the goal is useful evidence acquisition, not indiscriminate persistence. [^26]

**Answer to subquestion 3:** both instructions and information design have been tested, with some informative near-head-to-head comparisons. A general superiority claim is not supported. The most direct stopping interventions expose unresolved requirements or enforce evidence coverage; evidence specifically comparing intermediate-value labels with prompt-only reminders remains limited. [^1][^2][^21][^24]

## 5. Do agents treat one tool as the only authority and overlook another?

The literature supports components of that explanation more strongly than the complete explanation. Tool Preferences and BiasBusters establish that descriptions and ordering can causally alter which tool is chosen despite equivalent functionality. This is **selection bias**, not proof that an agent rejects correct evidence after seeing it or claims that information does not exist elsewhere. [^27][^14]

Set-shifting experiments give a closer behavioral analogue: after a backend reliability change, some agents keep routing to a previously preferred tool group. A prompt to reuse successful tools and switch after failure substantially helps some tested models but barely changes others; even an explicit unavailable message does not reliably induce switching. The setting is simulated redundant tools, not a test of source-authority labels or a final false-unavailability statement. [^7]

A factorial error-signal study holds the task, tool catalog, source state and executable transitions fixed while varying signal detail and visibility. Route-relevant messages change retries, rerouting and escalation, but improved operational closure does not imply equally large recovery gains. That is direct evidence for making the available recovery route intelligible, assessed here from the abstract. [^28]

Post-retrieval evidence choice can also be biased. A live-search source-preference study changes source identity and missing information, while an unreliable-tools study corrupts returns and tests verification prompts and reliability metadata. Both find effects, but neither establishes a stable, exclusive hierarchy that causes the precise statement “unavailable” despite a correct answer in another accessible tool. The PHREEQC evidence-substitution result is a useful scientific counterpart, but again addresses evidence use rather than that complete chain. [^8][^29][^6]

**Answer to subquestion 4:** tool-choice persistence, source-sensitive selection and inappropriate deference are empirically supported. The exact cross-tool false-unavailability mechanism was not isolated in the examined studies. It should be tested by tracing what each tool made available, what the agent actually inspected, and what its final claim asserted—not inferred from tool-call frequency alone. [^7][^8][^29]

## Implications for the DMDU study

The literature supports separating three outcomes: **reaching sufficient evidence, selecting the right evidence, and constructing a valid answer**. Live evidence ledgers address unresolved requirements; multi-hop filtering studies address visibility of later-hop evidence; the simulator study addresses the final evidence source even after correct execution. Those are distinct failure locations and need distinct checks. [^1][^4][^6]

For the specific intermediate-value hypothesis, the next discriminating test would hold task, graph, paths and tool functionality constant while independently varying whether an answer-like intermediate number appears, whether its role is labeled, and whether the question names the requested quantity explicitly. A prompt-only reminder should be compared with returned-information changes under matched evidence and a stated budget. These are proposed tests, **not interventions already validated by the reviewed literature**.

The evidence-informed design direction is to make the unresolved target explicit and to verify that the final answer matches it. A target should specify quantity, unit, time, aggregation and baseline; a candidate value should be checked against those fields before it can count as completion. This proposal combines coverage-oriented stopping with candidate-independent numerical semantics, rather than assuming that either a graph visit or a plausible number is sufficient. [^2][^12]

A careful related-work statement would be:

> Prior studies document underverified completion, query-conditioned evidence-selection bias, tool-routing persistence and evidence substitution. The present mechanism of interest is narrower: whether numerical information at an intermediate model variable encourages an agent to treat a related quantity as sufficient, terminate navigation and fail to answer the user's actual question. [^1][^4][^7][^6]

## Scope and evidence limitations

This was a targeted synthesis of empirical literature in the requested publication window, using existing project collections as seeds and additional searches across stopping, graph navigation, lexical matching, information design and tool trust. It is not a completed systematic or scoping review and does not establish that no matching study exists. Generic single-step QA without retrieval, purely conceptual proposals and records without a reported empirical comparison were not used as core evidence.

Several especially close studies were assessable only from abstracts, notably the PHREEQC evidence-substitution paper, CorpusMap, retrieval refusal, source preference and error-signal routing. Their findings are reported as author claims, with no invented design details. Larger claims about prompt-versus-information superiority remain limited by bundled interventions, differing outcomes, learned verification errors and the distinction between gold diagnostic information and deployable generated information. [^6][^19][^24][^8][^28][^2]


[^1]: Ko et al., 2026. When Is Enough Not Enough? Illusory Completion in Search Agents. arXiv.org.

[^2]: Roh & Han, 2026. HALT: Verification-Aware Stopping for Retrieval-Augmented Search Agents. arXiv.org.

[^3]: Shao et al., 2025. Do LLM Agents Know How to Ground, Recover, and Assess? A Benchmark for Epistemic Competence in Information-Seeking Agents. arXiv.org.

[^4]: Kumar, 2026. Verification Without Sufficiency: Per-Chunk Filtering Fails on Multi-Hop RAG, and Decomposition Repairs It. arXiv.org.

[^5]: Wei et al., 2026. Beyond Retrieval Failure: Understanding Why LLMs Miss Evidence in Multi-Hop RAG.

[^6]: Zhang et al., 2026. Same Simulation, Different Evidence: Where Retrieved Tool Output Costs LLM Agents Accuracy.

[^7]: Ye, 2026. Set-shifting Behavioral Test for Harnessed Agents. arXiv.org.

[^8]: Song et al., 2026. Source Preference in the Wild: How LLM Agents Favor Items by Source, and How to Reduce It.

[^9]: Song et al., 2025. Demystifying deep search: a holistic evaluation with hint-free multi-hop questions and factorised metrics. arXiv.org.

[^10]: Liu et al., 2026. Diagnosing Search Behavior and Failure Modes in Long-Horizon Search Agents. arXiv.org.

[^11]: Park et al., 2025. Stop-RAG: Value-Based Retrieval Control for Iterative RAG. arXiv.org.

[^12]: Hall et al., 2026. VeriFin: A Neurosymbolic Framework for Verifying LLM-Generated Financial Claims. arXiv.org.

[^13]: Tan et al., 2024. Blinded by Generated Contexts: How Language Models Merge Generated and Retrieved Contexts for Open-Domain QA?. arXiv.org.

[^14]: Blankenstein et al., 2025. BiasBusters: Uncovering and Mitigating Tool Selection Bias in Large Language Models. arXiv.org.

[^15]: Asl et al., 2025. FAIR-RAG: Faithful Adaptive Iterative Refinement for Retrieval-Augmented Generation. arXiv.org.

[^16]: Li et al., 2024. GraphReader: Building Graph-based Agent to Enhance Long-Context Abilities of Large Language Models. Conference on Empirical Methods in Natural Language Processing.

[^17]: Tao et al., 2025. Guided Navigation in Knowledge-Dense Environments: Structured Semantic Exploration with Guidance Graphs. arXiv.org.

[^18]: Shan & Luo, 2026. Bounded Path Context: A Controlled Study of Visible Path History in LLM-Based Knowledge Graph Question Answering. arXiv.org.

[^19]: Jeong et al., 2026. Follow the Entities: A Corpus Map for Agentic Search.

[^20]: Wu et al., 2026. Connection-Aware Graph Pruning in RAG for Multi-Hop Question Answering. IEEE International Joint Conference on Neural Network.

[^21]: Ray & Goyal, 2026. Structured Feedback Improves Repair in an LLM Agent Loop. arXiv.org.

[^22]: Huang et al., 2024. QueryAgent: A Reliable and Efficient Reasoning Framework with Environmental Feedback based Self-Correction. Annual Meeting of the Association for Computational Linguistics.

[^23]: Xiong et al., 2025. Butterfly Effects in Toolchains: A Comprehensive Analysis of Failed Parameter Filling in LLM Tool-Agent Systems. Conference on Empirical Methods in Natural Language Processing.

[^24]: Chandradevan et al., 2026. Search Engines Never Say No: How Frozen Agents React When the Retrieval Tool Refuses.

[^25]: Wang, 2026. Agent-Facing Information Design in LLM Tool Registries. arXiv.org.

[^26]: Qian & Liu, 2025. Scent of Knowledge: Optimizing Search-Enhanced Reasoning with Information Foraging. Neural Information Processing Systems.

[^27]: Faghih et al., 2025. Tool Preferences in Agentic LLMs are Unreliable. Conference on Empirical Methods in Natural Language Processing.

[^28]: Shi et al., 2026. How Tool-Error Signals Shape Recovery Route Selection in Information-Gathering LLM Agents: A Controlled Factorial Study. IEEE Access.

[^29]: Yang et al., 2026. Agents'Overreliance on Unreliable Tools.