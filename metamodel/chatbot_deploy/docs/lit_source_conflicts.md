# Literature: source conflicts and source trust in tool-using LLM agents

Prepared 2026-10-26 for the DMDU Society 2026 paper (draft due 9 Nov 2026).

## The two observations

- **Obs. 1 (inconsistent sources):** `country_context` gives a 2050 baseline GDP of 679 bn. The model runs give 444, 540 and 632 bn (one value per uncertainty third). In one run the agent navigated the network and worked out the correct mapping. In another run it used the ready-made `country_context` number and reached a wrong conclusion. Hypothesis: agents prefer the cheapest, most readily available information over navigating and testing. When sources disagree, that preference produces wrong answers, so system designers are responsible for checking that sources agree.
- **Obs. 2 (source trust hierarchy):** The agent got a quantity from the network tool (values from the model runs). It then told the user it could not report that quantity because the surrogate tool had not produced it. In other words, it treated only one tool's output as valid evidence.

## How to read this list

- I confirmed every entry's title, authors, year and venue on the linked page (arXiv abstract page, ACL Anthology, NeurIPS/ICLR/AAAI proceedings, or the venue's listing).
- Entries marked **[arXiv preprint]** have not been peer reviewed.
- Entries are ranked by relevance to our two observations.
- **[PARTIAL CONTRADICTION]** marks findings that cut against our hypothesis.

---

## Ranked works

### 1. Agents' overreliance on unreliable tools (2026)
Yang, H., Song, W., Kim, T., Song, J., Park, S., & Jo, Y. (2026). *Agents' Overreliance on Unreliable Tools.* arXiv:2609.05587 (v2, 26 Sep 2026). **[arXiv preprint]**
URL: https://arxiv.org/abs/2609.05587

- **Finding:** The authors tested 14 models. Agents adopted corrupted tool returns (web search, a sub-agent, a code executor) at high rates: on average more than a third for every tool, and 68% for web search. These returns often overrode answers the agents had got right without tools. Agents sometimes noticed the problem in their own reasoning but still passed the content on to users without warning them. Verification prompts reduced adoption.
- **Relevance:**
  - **Obs. 1:** An agent takes whatever a tool hands it without cross-checking.
  - **Obs. 2:** Trust follows the tool, not the evidence.
  - It also supports designer responsibility: the fixes are design-side (verification prompts, reliability labels).

### 2. KC-Bench: knowledge conflicts in LLM agents (2026)
Lyu, Y., Zhou, S., Toh, B., Zhu, P., & Li, L. (2026). *KC-Bench: A Dynamic Interactive Benchmark for Evaluating Knowledge Conflicts in LLM Agents.* arXiv:2609.03588. **[arXiv preprint]**
URL: https://arxiv.org/abs/2609.03588

- **Finding:** This is a multi-turn benchmark with stateful tools (238 tasks). It covers world-knowledge conflicts, input inconsistencies, and temporal conflicts across multiple sources. None of the 9 models tested handled all three conflict types reliably. Conflicts that went unnoticed carried through into later tool calls.
- **Relevance:** **Obs. 1.** This is the closest benchmark analogue to "two tools give different baseline numbers," and it shows the conflict spreading into later actions.

### 3. Knowledge conflicts survey (2024)
Xu, R., Qi, Z., Guo, Z., Wang, C., Wang, H., Zhang, Y., & Xu, W. (2024). *Knowledge Conflicts for LLMs: A Survey.* Proceedings of EMNLP 2024, pp. 8541–8565. doi:10.18653/v1/2024.emnlp-main.486
URL: https://aclanthology.org/2024.emnlp-main.486/ (arXiv: https://arxiv.org/abs/2403.08319)

- **Finding:** Sets out the standard taxonomy of conflict types:
  - context-memory conflicts
  - **inter-context** conflicts
  - intra-memory conflicts

  It reviews causes, model behaviour and mitigations, and argues that conflicts undermine trust and performance.
- **Relevance:**
  - **Obs. 1** is an *inter-context conflict* (country_context vs. model runs). Use this vocabulary in the paper.
  - **Obs. 2** is related, but it is a refusal to use one context, not a choice between two contexts.

### 4. Conflicting Needles in a Haystack (2025)
Kurfali, M., & Östling, R. (2025). *Conflicting Needles in a Haystack: How LLMs behave when faced with contradictory information.* Proceedings of EMNLP 2025, pp. 34361–34376. doi:10.18653/v1/2025.emnlp-main.1742
URL: https://aclanthology.org/2025.emnlp-main.1742/

- **Finding:** When long documents contained mutually exclusive facts, models "almost always fail to signal uncertainty and instead confidently select a single answer." Their choices were biased towards repeated content, recent content, and particular surface forms.
- **Relevance:** **Obs. 1.** The agent did not flag that 679 bn and 444/540/632 bn disagree. It picked one number and went ahead. The paper gives direct support for silent, confident selection.

### 5. ClashEval (2024)
Wu, K., Wu, E., & Zou, J. (2024). *ClashEval: Quantifying the tug-of-war between an LLM's internal prior and external evidence.* Advances in Neural Information Processing Systems 37 (NeurIPS 2024), Datasets and Benchmarks Track.
URL: https://proceedings.neurips.cc/paper_files/paper/2024/hash/3aa291abc426d7a29fb08418c1244177-Abstract-Datasets_and_Benchmarks_Track.html

- **Finding:** Six top models (including GPT-4o) adopted incorrect retrieved content over their own correct prior answer more than 60% of the time. Blatantly wrong content was adopted less often, and low model confidence predicted deference to the retrieved content.
- **Relevance:** **Obs. 1.** Content placed in context is taken up readily, even when it is wrong. A plausible but inconsistent number like 679 bn is exactly the case where this happens.

### 6. Adaptive Chameleon or Stubborn Sloth (2024)
Xie, J., Zhang, K., Chen, J., Lou, R., & Su, Y. (2024). *Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of Large Language Models in Knowledge Conflicts.* ICLR 2024.
URL: https://proceedings.iclr.cc/paper_files/paper/2024/hash/99261adc8a6356b38bcf999bba9a26dc-Abstract-Conference.html

- **Finding:** LLMs readily accept coherent external evidence even when it contradicts their memory. When the evidence is mixed, they show strong confirmation bias towards the evidence that matches what they already believe. The authors flag the risk for tool-augmented LLMs.
- **Relevance:**
  - **Obs. 1:** Coherent context wins.
  - **[PARTIAL CONTRADICTION]:** The confirmation-bias result means the choice is not purely "cheapest source". Agreement with prior beliefs also matters. If the 679 bn figure happened to match the model's prior idea of Uganda's GDP, that may explain the choice as well as (or instead of) its availability.

### 7. Tool preferences are unreliable (2025)
Faghih, K., Wang, W., Cheng, Y., Bharti, S., Sriramanan, G., Balasubramanian, S., Hosseini, P., & Feizi, S. (2025). *Tool Preferences in Agentic LLMs are Unreliable.* EMNLP 2025 (main conference). arXiv:2505.18135.
URL: https://arxiv.org/abs/2505.18135

- **Finding:** Rewording only a tool's description, without changing what the tool does, made GPT-4.1 and Qwen2.5-7B use it more than 10× as often as competing tools. The trends held across 17 models.
- **Relevance:**
  - **Obs. 1 and Obs. 2.** Which tool the agent reaches for, and which tool it treats as the authority, depends heavily on the description text the designer writes.
  - This directly supports designer responsibility. Our tool docstrings (e.g. "surrogate = the model") may be creating the trust hierarchy seen in Obs. 2.

### 8. BiasBusters: tool selection bias (2026)
Blankenstein, T., Yu, J., Li, Z., Plachouras, V., Sengupta, S., Torr, P., Gal, Y., Paren, A., & Bibi, A. (2026). *BiasBusters: Uncovering and Mitigating Tool Selection Bias in Large Language Models.* ICLR 2026 (camera ready; arXiv:2510.00307).
URL: https://arxiv.org/abs/2510.00307

- **Finding:** Across 7 LLMs, tool choice among functionally equivalent tools was biased. Models fixated on one provider or favoured tools listed earlier in the context. The strongest driver was semantic overlap between the query and the tool's metadata.
- **Relevance:** **Obs. 1 and Obs. 2.** Tool choice is driven by surface cues (position, wording overlap), not by evidential quality. A tool whose description sounds like "baseline numbers" will be chosen for baseline questions even when another tool gives the model-consistent answer.

### 9. Control Illusion: instruction hierarchies fail (2026)
Geng, Y., Li, H., Mu, H., Han, X., Baldwin, T., Abend, O., Hovy, E., & Frermann, L. (2026). *Control Illusion: The Failure of Instruction Hierarchies in Large Language Models.* Proceedings of the AAAI Conference on Artificial Intelligence, 40(36), 30816–30824. doi:10.1609/aaai.v40i36.40339
URL: https://ojs.aaai.org/index.php/AAAI/article/view/40339

- **Finding:**
  - Models do not consistently follow the priorities that designers set through system/user prompt separation.
  - They have built-in biases towards certain constraint types.
  - Framings of authority, expertise or consensus sway them more than system/user roles do.
- **Relevance:** **Obs. 2.** The agent seems to have built its own authority ranking ("only the surrogate counts"), possibly from authority-like cues (e.g. "the model" or "simulation"), rather than from the evidence itself. This also supports the point that designers cannot simply *declare* a source hierarchy in the prompt and expect it to hold.

### 10. Illusory completion in search agents (2026)
Ko, D., Kim, J., Kim, S., Park, H., Lee, D., Kim, G., Lee, M., & Lee, K. (2026). *When Is Enough Not Enough? Illusory Completion in Search Agents.* arXiv:2602.07549 (v3, 13 Oct 2026). **[arXiv preprint]**
URL: https://arxiv.org/abs/2602.07549

- **Finding:**
  - Search agents often declare a task finished with constraints still unverified. This happened in up to 48% of *correct* answers on multi-constraint questions.
  - Scale and training changed the form of the verification failures but did not remove them.
  - Showing agents an external per-constraint tracker improved accuracy by 4.4–16.1 points.
- **Relevance:** **Obs. 1.** This is the closest evidence for the "stop at the first available answer, skip the checking" part of our hypothesis. The paper frames it as under-verification rather than least effort. The fix it reports is designer-side scaffolding.

### 11. Tool-memory conflicts (2025/2026)
Cheng, J., Pan, R., & Amiri, H. (2026). *Investigating Tool-Memory Conflicts in Tool-Augmented LLMs.* arXiv:2601.09760; presented at the R2-FM Workshop @ ICML 2025. **[workshop paper / arXiv]**
URL: https://arxiv.org/abs/2601.09760

- **Finding:**
  - The paper defines tool-memory conflict: the model's internal knowledge disagrees with what a tool returns.
  - Conflicts were common, especially on STEM tasks.
  - Models favoured tool output or memory depending on the condition.
  - Prompting and RAG mitigations did not solve the problem.
- **Relevance:**
  - **Obs. 1 and Obs. 2.**
  - **[PARTIAL CONTRADICTION]:** Source preference depends on the condition. There is no stable rule such as "always the cheapest" or "always the tool". This argues for presenting our finding as condition-dependent.

### 12. What evidence do LMs find convincing? (2024)
Wan, A., Wallace, E., & Klein, D. (2024). *What Evidence Do Language Models Find Convincing?* Proceedings of ACL 2024 (Volume 1: Long Papers), pp. 7468–7484.
URL: https://aclanthology.org/2024.acl-long.403/

- **Finding:** On questions with conflicting evidence documents (ConflictingQA), models relied mainly on how *relevant* a source looked to the query. They largely ignored the features humans use to judge credibility, such as references or neutral tone.
- **Relevance:** **Obs. 1.** A tool named and described as "country context / baseline" looks maximally relevant to a baseline-GDP question, whatever its consistency with the model.

### 13. SMART: tool overuse (2025)
Qian, C., Acikgoz, E. C., Wang, H., Chen, X., Sil, A., Hakkani-Tür, D., Tur, G., & Ji, H. (2025). *SMART: Self-Aware Agent for Tool Overuse Mitigation.* Findings of ACL 2025. arXiv:2502.11435.
URL: https://arxiv.org/abs/2502.11435

- **Finding:** LLM agents call tools unnecessarily, in more than 30% of cases in the authors' preliminary study, even when their own knowledge would be enough. Unneeded calls sometimes produced wrong answers.
- **Relevance:**
  - **[PARTIAL CONTRADICTION] to Obs. 1:** Agents do not always minimise effort. They often do *more* tool work than needed.
  - Our hypothesis should be narrowed: agents prefer the information that *looks* sufficient and directly relevant, not simply the cheapest action. In our setup, the cheap option happened to be a tool call (`country_context`).

### 14. AI Agents That Matter (2025)
Kapoor, S., Stroebl, B., Siegel, Z., Nadgir, N., & Narayanan, A. (2025). *AI Agents That Matter.* Transactions on Machine Learning Research (TMLR). arXiv:2407.01502.
URL: https://arxiv.org/abs/2407.01502 (TMLR listing: https://mlanthology.org/tmlr/2025/kapoor2025tmlr-ai/)

- **Finding:** Agent benchmarks focus too narrowly on accuracy. They lack proper holdouts, so agents can take shortcuts, and they are poorly standardised, which hurts reproducibility. The authors call for evaluation that accounts for cost and for the downstream use.
- **Relevance:** Designer responsibility (**both**). This is the general argument that the people who build and evaluate agents must test them under realistic conditions. For us, that means checking that sources agree and that the agent's trust in each source is justified.

### 15. ToolEmu: risks of LM agents (2024)
Ruan, Y., Dong, H., Wang, A., Pitis, S., Zhou, Y., Ba, J., Dubois, Y., Maddison, C. J., & Hashimoto, T. (2024). *Identifying the Risks of LM Agents with an LM-Emulated Sandbox.* ICLR 2024. arXiv:2309.15817.
URL: https://arxiv.org/abs/2309.15817 (ICLR page: https://iclr.cc/virtual/2024/poster/19037)
*(Note: I confirmed the title, first author, venue and year on the ICLR and arXiv pages. Check the full author list against the PDF before citing.)*

- **Finding:** The paper builds a framework that tests tool-using agents across 36 toolkits and 144 test cases. Even the safest agent tested failed in 23.9% of cases.
- **Relevance:** Designer responsibility (**both**). It is a precedent for systematically testing agents before deployment, which matches our smoke-test approach.

---

## Context only (verified; cite where useful)

- **Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2024).** *Lost in the Middle: How Language Models Use Long Contexts.* TACL 12, 157–173. https://aclanthology.org/2024.tacl-1.9/
  - Models use information best when it sits at the start or end of the context. Where information sits in the context shapes how well it is used.
  - Supports a "salience/availability" reading of **Obs. 1**.
- **Naphade, A. (2026).** *Rational Synthesizers or Heuristic Followers? Analyzing LLMs in RAG-based Question-Answering.* arXiv:2601.06189. **[arXiv preprint, ACL ARR submission]** https://arxiv.org/abs/2601.06189
  - Models favour evidence presented first, and rephrasing an argument persuades them more than independent support does.
  - The explanations models give for their answers are unfaithful. This matters for our saved "verify why claims" idea.
- **Vasconcelos, H., Jörke, M., Grunde-McLaughlin, M., Gerstenberg, T., Bernstein, M. S., & Krishna, R. (2023).** *Explanations Can Reduce Overreliance on AI Systems During Decision-Making.* Proc. ACM HCI 7 (CSCW1), Article 129. https://arxiv.org/abs/2212.06823
  - Human overreliance follows a cost-benefit logic: people check AI output when checking is cheap relative to the task.
  - This is a *human* analogue of our least-effort hypothesis, and relevant to the end users (policy makers) of our tool.
- **Pei, Z., Lipovetzky, N., Rojas-Arevalo, A. M., de Haan, F. J., & Moallemi, E. A. (2026).** *Generative AI-assisted Participatory Modeling in Socio-Environmental Planning under Deep Uncertainty.* arXiv:2603.17021. **[arXiv preprint]** https://arxiv.org/abs/2603.17021
  - LLMs helped turn stakeholder descriptions into a Python model (lake problem, electricity market). Acceptable output needed several rounds of human checking.
  - An earlier version is the MODSIM 2025 paper "LLM-assisted initial problem conceptualization in decision-making under deep uncertainty" (https://mssanz.org.au/modsim2025/files/F10.pei.pdf). I confirmed that paper's title and authors only through search-index text; I could not read the PDF.
  - This is the closest DMDU + LLM work I found. It covers problem conceptualization, not agents querying an existing model.

---

## Search directions with nothing solid

1. **LLM agents + surrogate/emulator of an IAM + exploratory modeling or RDM.** I found no peer-reviewed or preprint work where an LLM agent queries a surrogate of an integrated assessment model, or runs exploratory modeling over a large ensemble for users. Closest neighbours:
   - LLMs used for problem conceptualization in DMDU (Pei et al., above).
   - LLM agents used *as* simulated actors in agent-based models.

   This gap is a contribution claim for our paper.
2. **"Least effort", "satisficing" or "cognitive miser" framing for LLM agents.** I found no paper that tests a least-effort preference for stored or cheap information over navigating and testing. The nearest work uses other terms: under-verification or illusory completion (Ko et al.) and tool overuse (Qian et al., which partly contradicts our hypothesis). Our framing would be new and should be stated as a hypothesis, not as an established effect.
3. **Agents refusing to use valid evidence because it came from a "non-authoritative" tool (Obs. 2).** I found no study of this exact failure: valid tool output dismissed because a different tool was expected to produce it. Related work covers instruction hierarchies (Geng et al.) and tool-selection bias (Faghih et al.; Blankenstein et al.), but not *source-legitimacy* refusals. This is another possible contribution.

## Suggested framing for the paper (one paragraph)

Obs. 1 is an **inter-context knowledge conflict** (Xu et al., 2024) in a tool-using agent. Several findings fit what we saw:

- Agents tend to pick one source confidently without flagging the conflict (Kurfali & Östling, 2025).
- They readily adopt plausible tool or context content (Wu et al., 2024; Yang et al., 2026).
- They stop before verifying (Ko et al., 2026).

Obs. 2 fits evidence that tool choice and trust follow tool descriptions and authority cues rather than the evidence (Faghih et al., 2025; Blankenstein et al., 2026; Geng et al., 2026).

Two caveats go with this:

- Preferences are condition-dependent (Cheng et al., 2025/26).
- Agents also *over*-use tools (Qian et al., 2025).

So "least effort" should be narrowed to "the source that *looks* sufficient and relevant". Most mitigations reported in this literature are on the designer side (verification prompts, reliability labels, tool-description design, state tracking), which supports our claim about designer responsibility.
