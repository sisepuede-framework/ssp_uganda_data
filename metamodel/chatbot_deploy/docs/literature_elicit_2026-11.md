# Papers found by Elicit (November 2026): index for the paper update

Saved 2026-11-17 at Alexa's request ("we will need that when we update the paper draft"). Full reports, copied word
for word from `~/Downloads/`:

- **[I]** `docs/elicit_2026-11-16_innovation_assessment.md`: is the study novel? (7 references)
- **[S]** `docs/elicit_2026-11-17_premature_stopping.md`: why retrieval agents stop early (29 references)

**Before citing any of these:** the paper's rule is that `references.bib` holds only verified entries (title,
authors, venue, year and DOI or arXiv id checked on the publisher or arXiv page). "In bib" below means already
verified. "Abstract only" means Elicit says it only read the abstract ("not flagged" means Elicit did not say; it is not a guarantee it read the full text), so its description of the design and numbers
must be checked against the full text before we lean on it.

## Already in `references.bib` (verified)

| Paper | Report | Bib key | Used for |
|---|---|---|---|
| Abubakar & Cepero Mejías 2026, natural-language interface for parameterised LCA (J. Industrial Ecology) | I | `abubakar2026lca` | Related work: language interfaces to existing models. DOI still to confirm (ResearchGate only) |
| Emami et al., SysCaps: language interfaces for simulation surrogates (ICLR 2025; Elicit says 2024 = arXiv) | I | `emami2025syscaps` | Related work |
| Wang et al. 2026, AI agent architectures for SWMM calibration (npj Clean Water) | I | `wang2026swmm` | Related work; controlled comparison of model-operating agents |
| Yang, Leitner & Burke 2025, feedback-induced performance decline (arXiv 2507.14906) | I | `yang2025feedback` | More information can hurt |
| Ray & Goyal 2026, structured feedback improves repair (arXiv 2607.14167) | I, S | `ray2026feedback` | Content vs presentation of returned information |
| Pei et al. 2026, GenAI-assisted participatory modeling under deep uncertainty (arXiv) | I | `pei2026participatory` | Closest DMDU work |
| Dong et al. 2026, resource recovery … generative AI-enabled decision support (Water Research 126563) | I | `dong2026drainage` | Related work (abstract only) |
| Ko et al. 2026, illusory completion in search agents (arXiv) | S | `ko2026illusory` | Premature stopping; LIVELEDGER (visible verification states) |
| Blankenstein et al., BiasBusters: tool selection bias (ICLR 2026; Elicit cites the 2025 arXiv) | S | `blankenstein2026biasbusters` | Wording and order shape tool choice |
| Faghih et al. 2025, tool preferences in agentic LLMs are unreliable (EMNLP) | S | `faghih2025tool` | Tool descriptions change tool use |
| Yang et al. 2026, agents' overreliance on unreliable tools | S | `yang2026overreliance` | Tool trust, source reliability |

## New, to verify before citing (from the premature-stopping report [S])

Grouped by the part of the paper they would support. ★ = most important for E3 and the discussion.

**Why agents stop before the evidence is sufficient**

| Paper | What Elicit says it shows | Read by Elicit |
|---|---|---|
| ★ Roh & Han 2026, HALT: verification-aware stopping for retrieval-augmented search agents (arXiv) | Coverage check per hop changes halt/continue; selectively continuing under-covered searches improves exact match | not flagged |
| Shao et al. 2025, SeekBench: grounding, recovery and sufficiency in information-seeking agents (arXiv) | Overconfident answering before sufficient evidence in 76.5% of RL-agent trajectories (benchmark-specific) | not flagged |
| ★ Song et al. 2025, WebDetective: hint-free multi-hop deep search (arXiv) | Agents conclude an answer is unavailable after limited search while paths remain; "please continue searching" did not restart them. Closest to our "said unavailable" | not flagged |
| Liu et al. 2026, diagnosing search behavior in long-horizon search agents (arXiv) | Separates missing evidence from retrieved-but-unused; long low-yield searches also fail | not flagged |
| Park et al. 2025, Stop-RAG: value-based retrieval control (arXiv) | Learned stop/continue helps in its own pipeline, not uniformly elsewhere: more search is not the goal | not flagged |
| Wei et al. 2026, Beyond Retrieval Failure: why LLMs miss evidence in multi-hop RAG | An open-subquestion register recovers evidence but premature resolutions and abstentions rise | **abstract only** |
| Asl et al. 2025, FAIR-RAG (arXiv) | Required-finding checklists; premature sufficiency judgments remain | not flagged |

**Answering from the wrong evidence; question wording and overlap**

| Paper | What Elicit says it shows | Read by Elicit |
|---|---|---|
| ★ Zhang et al. 2026, Same Simulation, Different Evidence (PHREEQC simulator agents) | Agents compute the right value but answer from another output ("evidence substitution"); naming the authoritative output +6.3 to +7.9 pp, a rounding reminder did not help. Closest scientific-model comparator | **abstract only** |
| ★ Kumar 2026, Verification Without Sufficiency: per-chunk filtering fails on multi-hop RAG (arXiv) | Question-similar (named bridge) evidence is favoured over the unnamed answer-bearing passage; decomposition repairs it (AUC 0.546 → 0.840 with gold subquestions). Relatedness ≠ sufficiency | not flagged |
| Tan et al. 2024, Blinded by Generated Contexts (arXiv) | Models prefer question-similar generated passages over correct retrieved ones | not flagged |
| Hall et al. 2026, VeriFin: verifying LLM financial claims (arXiv) | Grounding facts, periods, units and formulae before numerical verification (our "target ledger" idea) | not flagged |

**Navigation, structure and information design**

| Paper | What Elicit says it shows | Read by Elicit |
|---|---|---|
| Li et al. 2024, GraphReader (EMNLP) | Rational plan and node selection ablations reduce QA | not flagged |
| Tao et al. 2025, guidance graphs for knowledge-dense navigation (arXiv) | Richer target descriptions and structure help exploration | not flagged |
| Shan & Luo 2026, Bounded Path Context in KGQA (arXiv) | Showing more path history does not always help navigation | not flagged |
| Jeong et al. 2026, Follow the Entities: a corpus map for agentic search | Entity pages as signposts improve evidence discovery | **abstract only** |
| Wu et al. 2026, connection-aware graph pruning (IJCNN) | Keeping evidence chains beats keeping question-similar snippets | **abstract only** |
| Huang et al. 2024, QueryAgent (ACL) | Targeted environmental feedback for self-correction | not flagged |
| Xiong et al. 2025, Butterfly Effects in Toolchains (EMNLP) | Perturbing documentation, queries and returns changes failures | not flagged |
| ★ Wang 2026, agent-facing information design in tool registries (arXiv) | Warnings, disclosures and structured capability fields (instruction vs information) | not flagged |
| Qian & Liu 2025, Scent of Knowledge: information foraging for search reasoning (NeurIPS) | Information-foraging rewards for intermediate evidence acquisition | not flagged |

**Tool trust and "only one source counts"**

| Paper | What Elicit says it shows | Read by Elicit |
|---|---|---|
| ★ Ye 2026, set-shifting behavioral test for harnessed agents (arXiv) | Agents persist with a preferred tool after it fails; an "unavailable" message does not reliably make them switch | not flagged |
| ★ Chandradevan et al. 2026, Search Engines Never Say No: agents and a refusing retrieval tool | Some agents follow refusal information in tool output, others follow system instructions (instruction vs information depends on the model) | **abstract only** |
| Song et al. 2026, source preference in the wild | Agents favour items by source; mitigations | **abstract only** |
| Shi et al. 2026, tool-error signals and recovery routes, controlled factorial study (IEEE Access) | Route-relevant messages change retries and rerouting | **abstract only** |

## How these will be used in paper v2 (after E3)

- **Related work (§2.4):** add the stopping and evidence-substitution studies (Ko, Roh & Han, WebDetective, Zhang,
  Kumar) next to the language-interface papers already there.
- **Positioning sentence** proposed by Elicit, to adapt: "Prior studies document underverified completion,
  query-conditioned evidence-selection bias, tool-routing persistence and evidence substitution. The present
  mechanism of interest is narrower: whether numerical information at an intermediate model variable encourages an
  agent to treat a related quantity as sufficient, terminate navigation and fail to answer the user's actual question."
- **Discussion:** instruction vs information (Wang 2026; Chandradevan 2026; Ray & Goyal 2026); "said unavailable"
  (WebDetective; Ye 2026); the design implication of a target check (quantity, unit, year, baseline) before an answer
  counts (HALT; VeriFin).
- **Each new citation:** verify, add to `references.bib`, and read the full text of every "abstract only" paper we
  cite for a specific number or design detail.
