# Run from metamodel/chatbot_deploy:  python3 results_analysis/code/elicit_prompts_doc.py docs/elicit_prompts_2026-10-28.docx
"""Elicit prompts for the literature review: one research question per finding we want to place in the literature,
with the columns to add in Elicit and backup keywords. Seed papers from docs/lit_source_conflicts.md."""
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(sys.argv[1])
if OUT.exists():
    raise SystemExit(f"{OUT} exists: write a new version (e.g. _v2) instead of overwriting a file handed over")
FONT = "Times New Roman"

doc = Document()
sec = doc.sections[0]
sec.orientation = WD_ORIENT.LANDSCAPE
sec.page_width, sec.page_height = sec.page_height, sec.page_width
for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, m, Cm(1.6))
for name in ("Normal", "Title", "Heading 1", "Heading 2", "List Bullet"):
    st = doc.styles[name]
    st.font.name = FONT
    rf = st.element.get_or_add_rPr().get_or_add_rFonts()
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rf.attrib.pop(qn(a), None)
    if name not in ("Normal", "List Bullet"):
        st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
doc.styles["Normal"].font.size = Pt(10.5)


def B(text, lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if lead:
        p.add_run(lead).bold = True
    p.add_run(text)


def shade(cell, fill):
    pr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", fill)):
        sh.set(qn(k), v)
    pr.append(sh)


def T(header, rows, widths, size=9.5):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.autofit = False
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(h).bold = True
        shade(c, "FFF2CC" if h.startswith("Your") else "D9E2F3")
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
            if header[i].startswith("Your"):
                shade(cells[i], "FFF2CC")
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                for run in p.runs:
                    run.font.size, run.font.name = Pt(size), FONT
    doc.add_paragraph()


doc.add_heading("Literature review with Elicit: prompts", 0)
doc.add_paragraph().add_run("28 October 2026 · one research question per finding we want to place in the "
                            "literature").italic = True

doc.add_heading("How to use these prompts", 1)
B("Paste the question in the 'Elicit prompt' column as it is: Elicit works best with a full research question, "
  "not keywords.", "Search. ")
B("Add the columns listed for each question (Elicit: 'Add column'). The last one always asks whether the paper "
  "supports or contradicts our finding, so the table answers 'does it fit?' directly.", "Columns. ")
B("LLM topics: 2023–2026 (older work predates tool-using agents). DMDU, surrogates and decision support: no year "
  "filter.", "Years. ")
B("Read the abstracts of the top 20–30 per question; keep a paper if it tests something (an experiment, a benchmark, "
  "a case study), not only an opinion. Mark contradicting papers: they are as useful as supporting ones.", "Screening. ")
B("Export each table to CSV and send them to me: I merge them into one Excel (finding × paper) for the review.",
  "Export. ")
B("Already found (docs/lit_source_conflicts.md): Agents' overreliance on unreliable tools (2026); KC-Bench (2026); "
  "Knowledge conflicts survey (2024); Conflicting Needles in a Haystack (2025); ClashEval (2024); Adaptive Chameleon "
  "or Stubborn Sloth (2024); Tool preferences are unreliable (2025); BiasBusters (2026); Control Illusion (2026); "
  "Illusory completion in search agents (2026); Tool-memory conflicts (2025/26). Use them in Elicit's 'find similar "
  "papers' to widen questions 9–11.", "Seed papers. ")

STD = "Agent / model used; Task and domain; What was varied; Main finding"
SUP = "Supports or contradicts: "

doc.add_heading("A. Context: AI, simulation models and decision making under deep uncertainty (RQ1)", 1)
T(["#", "What we want to place", "Elicit prompt", "Columns to add", "Backup keywords", "Your notes"], [
    ("1", "Our system: an LLM agent that runs a model of the economy and emissions for policy users",
     "How have large language model agents been used to run, query or interpret simulation models, integrated "
     "assessment models or energy-system models for policy analysis?",
     f"{STD}; {SUP}an agent can stand in for the technical expertise needed to run a policy model",
     "LLM agent; integrated assessment model; energy system model; simulation; tool use; climate policy", ""),
    ("2", "AI as an intermediary for the three components of RDM",
     "Can large language models support decision making under deep uncertainty methods such as robust decision "
     "making, exploratory modeling, vulnerability analysis or scenario discovery?",
     f"{STD}; which DMDU step; {SUP}an AI agent can carry out RDM steps for non-technical users",
     "robust decision making; DMDU; exploratory modeling; scenario discovery; large language model", ""),
    ("3", "The surrogate: fast emulation of a slow model to explore many futures",
     "How accurate are machine-learning surrogate or emulator models of integrated assessment, energy-economy or "
     "climate policy models, and how are they used to explore many scenarios quickly?",
     "Model emulated; ML method; Accuracy reported; How it was validated; Use for exploration",
     "surrogate model; emulator; metamodel; XGBoost; integrated assessment; scenario ensemble", ""),
    ("4", "Non-technical users and model-based decision support",
     "Do conversational AI or natural-language interfaces help non-expert policy makers use quantitative climate, "
     "energy or economic models?",
     f"Users studied; Interface; Outcome measured; {SUP}a conversational agent makes model results usable by non-experts",
     "decision support; policy makers; natural language interface; climate model; usability", ""),
], [0.8, 4.2, 7, 5.5, 4.2, 4.6])

doc.add_heading("B. What the information given to the agent changes (RQ2 and the design lessons)", 1)
T(["#", "Our finding", "Elicit prompt", "Columns to add", "Backup keywords", "Your notes"], [
    ("5", "Showing values, not only links, made the agent set levels right (79% → 1% off the key) with fewer calls",
     "How does the content and format of tool outputs, such as numeric values versus structural or relational "
     "descriptions, affect how LLM agents choose tools, set parameters and answer?",
     f"{STD}; {SUP}richer tool output improves parameter choice and reduces tool calls",
     "tool output format; tool response; structured information; knowledge graph; agent performance", ""),
    ("6", "Without values the agent took words literally ('40%' → 0.40) or used 0.5 as a default",
     "How accurately do large language models translate natural-language quantities or policy descriptions into "
     "model parameters or numeric settings, and what errors do they make?",
     f"{STD}; type of error (literal, default, scale); {SUP}LLMs map words to parameters literally without grounding data",
     "natural language to parameters; numeric grounding; quantity understanding; text-to-model; parameter estimation", ""),
    ("7", "With values the agent did its own arithmetic and reported numbers no tool gave",
     "How often do LLM agents report numbers they computed or inferred themselves instead of numbers returned by "
     "tools, and how can such unsupported numbers be detected?",
     f"{STD}; detection method; {SUP}tool values invite unverified calculations",
     "numerical hallucination; attribution; unsupported claims; faithfulness; tool-grounded answers", ""),
    ("8", "With values at the first step the agent stopped before the node with the answer (0 of 13 vs 7 of 7)",
     "Do tool-using LLM agents stop searching or exploring too early when partial information is available, and "
     "what makes them continue to the information they need?",
     f"{STD}; stopping cause; remedy tested; {SUP}partial information makes agents stop early",
     "premature termination; under-verification; illusory completion; satisficing; information foraging; agent search depth", ""),
    ("9", "One sentence in a tool description decided whether the agent used trade_off_analysis",
     "How does the wording of tool descriptions affect which tools LLM agents select and when they use them?",
     f"{STD}; {SUP}tool descriptions steer which analysis step the agent takes",
     "tool description; tool selection; tool documentation; function calling; prompt sensitivity", ""),
    ("10", "An unlabeled baseline number conflicted with the runs and misled the agent; a label fixed it",
     "How do LLM agents handle conflicting numbers from multiple tools or sources, and does labelling the source "
     "or context of each number reduce errors?",
     f"{STD}; conflict type; {SUP}source labels reduce wrong inferences from conflicting tools",
     "knowledge conflict; source conflict; inter-context conflict; provenance; source labels; RAG", ""),
    ("11", "The agent trusted the surrogate over the network and called valid network values 'unverified'",
     "Do LLM agents treat some tools or sources as more authoritative than others, and ignore valid evidence that "
     "comes from a less trusted tool?",
     f"{STD}; {SUP}agents build their own source hierarchy",
     "source credibility; tool trust; authority bias; instruction hierarchy; evidence weighting", ""),
], [0.8, 4.2, 7, 5.5, 4.2, 4.6])

doc.add_heading("C. How we evaluate (second half of RQ1)", 1)
T(["#", "Our choice", "Elicit prompt", "Columns to add", "Backup keywords", "Your notes"], [
    ("12", "A small model (Haiku) judges 5 checks; validated on 20 hand-marked judgments; reads the whole conversation",
     "How reliable are LLM-as-a-judge evaluations compared with human judgments, and how does the context given to "
     "the judge (final answer versus full conversation) change agreement?",
     "Judge model; Task; Agreement with humans; Biases found; How many human labels used",
     "LLM-as-a-judge; evaluator reliability; human agreement; judge bias; conversation-level evaluation", ""),
    ("13", "20 code rules on the tool calls and answers, plus a judge model",
     "How should tool-using LLM agents be evaluated: rule-based checks of tool-call trajectories, final-answer "
     "judgments, or both?",
     "Evaluation method; What it catches; What it misses; Benchmark",
     "agent evaluation; trajectory evaluation; tool call accuracy; process versus outcome evaluation", ""),
    ("14", "5 repetitions per question and arm; answers varied between runs (HC1)",
     "How much do LLM agent outputs vary across repeated runs with the same input, and how many repetitions are "
     "needed for reliable evaluation?",
     "Models; Source of variance; Repetitions used; Recommendation",
     "run-to-run variance; non-determinism; reproducibility; repeated sampling; LLM evaluation", ""),
    ("15", "Questions, keys, checks and analysis fixed in git before the run; deviations logged",
     "What practices make experiments with LLM agents reproducible, such as pre-registration, fixed evaluation "
     "criteria and versioning of prompts and tools?",
     "Practice; Field; Evidence of effect",
     "pre-registration; reproducibility; LLM experiments; evaluation protocol; research software", ""),
    ("16", "The agent must explore futures, not forecast or name a winner",
     "How do LLM-based decision support systems communicate uncertainty, and how do they avoid presenting scenario "
     "results as predictions or recommending a single option?",
     f"Domain; Communication approach; Effect on users; {SUP}scenario framing needs explicit design",
     "uncertainty communication; scenario framing; decision support; overconfidence; recommendation", ""),
], [0.8, 4.2, 7, 5.5, 4.2, 4.6])

doc.add_heading("Gaps to look for explicitly", 1)
B("Nothing yet found on an LLM agent querying a surrogate of an integrated assessment model, or running exploratory "
  "modeling over an ensemble for users (questions 1–3). If Elicit also finds nothing, that is a contribution to say.")
B("No study yet of 'least effort' or satisficing in LLM agents as such (question 8); the nearest terms are "
  "under-verification and illusory completion. Our walk-depth result (stops early with values) is a candidate "
  "contribution.")
B("No study yet of agents dismissing valid tool output because another tool was expected to produce it "
  "(question 11).")

doc.save(OUT)
print(OUT)
