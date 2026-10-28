"""Process and status document for Alexa (docs/process_and_status_2026-10-28.docx)."""
import sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

OUT = sys.argv[1]
FONT = "Times New Roman"
doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.2)
    s.top_margin = s.bottom_margin = Cm(2)
st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
for name, size in (("Title", 22), ("Heading 1", 15), ("Heading 2", 12.5)):
    h = doc.styles[name]
    h.font.name = FONT
    h.font.size = Pt(size)
    h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    rpr = h.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    rf = rf if rf is not None else OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FONT)
    if rf.getparent() is None:
        rpr.append(rf)
for name in ("List Bullet", "List Bullet 2"):
    doc.styles[name].font.name = FONT


def H(text, level=1):
    doc.add_heading(text, level)


def P(text, bold_lead=None, italic=False):
    p = doc.add_paragraph()
    if bold_lead:
        p.add_run(bold_lead).bold = True
    r = p.add_run(text)
    r.italic = italic
    return p


def B(text, lead=None, level=1):
    p = doc.add_paragraph(style="List Bullet" if level == 1 else "List Bullet 2")
    if lead:
        p.add_run(lead).bold = True
    p.add_run(text)
    p.paragraph_format.space_after = Pt(2)
    return p


def shade(cell, hex_):
    tc = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_)
    tc.append(sh)


def T(header, rows, widths, fills=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(h).bold = True
        shade(c, "D9E2F3")
    for k, r in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
            if fills and fills[k]:
                shade(cells[i], fills[k])
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9.5)
                    r.font.name = FONT
    doc.add_paragraph()
    return t


BLUE, GREEN, ORANGE = "DDEBF7", "E2EFDA", "FCE4D6"

doc.add_heading("RDM agent experiment: process and where we are", 0)
P("28 October 2026 · for Alexa · branch dmdu-agent", italic=True)

H("1. In short")
B("We built a system where an AI agent (Claude) helps a non-technical user carry out three components of Robust "
  "Decision Making (RDM) on a fast surrogate of SISEPUEDE for Uganda.")
B("We ran an experiment: the same agent, the same 6 tools and the same prompt, in two arms that differ only in what "
  "the model_network tool shows: v0 = how variables are related; v1 = relations plus values from the model runs.")
B("The full run is done: 290 conversations (29 conversations × 2 arms × 5 repetitions), US$20.05, no infrastructure faults.")
B("Every conversation is saved as a log (JSON). A script scores it with 25 automatic checks: 20 are code rules on the "
  "log; 5 (13, 14, 17, 18, 22) come from a second, smaller model (Claude Haiku 5.5) that reads the whole conversation.")
B("Main result (RQ2): with values (v1), the agent sets the policy lever right far more often (off the answer key 79% → 1%) "
  "and calls the network less (2.3 → 1.3 calls per conversation).")
B("Still open: your hand check of 20 Haiku judgments (decides whether checks 13, 14, 17, 18, 22 can be trusted), the results "
  "document, and the deck items listed in section 11.")

H("2. Research questions")
B("How do we integrate a surrogate model of SISEPUEDE with an AI agent to develop a system that enables non-technical "
  "users to explore policy questions through the three components of RDM (exploratory modeling, vulnerability "
  "analysis, and trade-off analysis), and how do we evaluate such a system?", "RQ1 (system and its evaluation): ")
B("What is the impact of the type of information we give the agent about the model (how its variables are related, "
  "or also their values) on its use of the available tools and on the policy levels and uncertainty ranges it sets?",
  "RQ2 (the experiment): ")

H("3. The system")
H("3.1 Data and the surrogate", 2)
B("100,000 SISEPUEDE runs: a Latin hypercube over 54 levers (policies) and 13 uncertainties, each scaled 0–1.")
B("What a lever level means: each lever goes from 0 to 1, the range designed for this experiment. L = 0 is BAU "
  "(no action); L = 1 is the range maximum, the most ambitious level the experiment explored. In between, every input "
  "field a lever sets moves on a straight line: value = BAU + L × (range maximum − BAU).", level=2)
B("Checked on all 527 lever input fields in 2050 and 2070 (worst error 0.4% of the range; tests/rdm/test_inputs.py, "
  "passing 2026-10-28). The two ends are read from the run's own files, not set by hand.", level=2)
B("The range maximum is a design choice of the experiment, not a strategy and not a proven technical maximum: we do "
  "not give it a strategy name. (Its inputs match the fixed pathway run the experiment was scaled from; that run is "
  "used only as a cross-check.)", level=2)
B("Not checked yet: whether the two transformations of that fixed pathway that are not levers (DEC_HFCS, "
  "DEC_OTHER_FCS, F-gases) are held fixed in every run. If so, a run with all levers at 0 equals BAU except for "
  "F-gases (team question).", level=2)
B("Surrogate: one XGBoost model per output (67 inputs → 258 outputs, 6 years 2025–2070), 80/20 split, "
  "median R² 0.994 on held-out runs. The technical tools run on it, so a 500-future ensemble takes seconds.")
B("The SISEPUEDE network: 804 nodes and 4,379 links read from the model code (a link = 'used to compute'). Tested on "
  "the runs: 93.9% of observed links have a path in the network. v1 values come from 4,989 sampled runs "
  "(median and p10–p90 by lever third × uncertainty third, every year).")
H("3.2 The six tools", 2)
T(["Tool", "Question it answers", "Reads"], [
    ("model_network", "What does this lever do? What moves this result? (the treatment)", "network; v1 also run values"),
    ("country_context", "What is Uganda like in the model's baseline?", "country baseline (BAU)"),
    ("exploratory_modeling", "RDM 1: how does a policy perform across 500 futures?", "surrogate"),
    ("vulnerability_analysis", "RDM 2: how often does it fail? (asks the user for the threshold)", "stored ensemble"),
    ("scenario_discovery", "RDM 2: under which conditions does it fail?", "stored ensemble"),
    ("trade_off_analysis", "RDM 3: emissions vs costs vs benefits of alternatives", "stored ensemble"),
], [4, 8.5, 4.5])
H("3.3 The harness (the code around the agent)", 2)
B("Runs the tools the agent asks for; never chooses for it.")
B("Keeps ensembles and pass/fail labels by id so tools can chain.")
B("Enforces rules: levers only within the range that was run; no uncertainty fixed at one value; a threshold before "
  "a vulnerability analysis. A broken rule returns an error message and the agent can try again.")
B("Plays a scripted user: sends the question, then the question's fixed replies in order (e.g. the failure "
  "threshold) when the agent stops and asks; otherwise 'Please go ahead with what you think is reasonable…'.")
B("Writes the log (section 7).")
H("3.4 Order and independence of the conversations", 2)
B("Every conversation starts from zero: a new message list with only the question, and a new harness (no ensembles "
  "or labels from earlier conversations). The agent never sees another question, another repetition or another arm.")
B("The system prompt is cached by the API between conversations (cache_read tokens in the log). This only saves cost "
  "on identical text; it carries no information from one conversation to the next.")
B("Order of the full run (run_bank.py): repetition 0 of every question, in bank order, each in v0 then v1; then "
  "repetition 1, and so on. Five conversations ran at the same time. 290 conversations took 23 minutes "
  "(2026-10-27, 00:38–01:01 UTC). Order cannot leak information, because conversations share nothing.")

H("4. The agent and the reader: model settings")
P("These settings are the same in every arm and every repetition. They are in harness/agent.py and "
  "eval/failure_modes.py; each log records the model, effort and the git commit it ran on.")
T(["Setting", "Agent (answers the user)", "Reader (scores the answer)"], [
    ("Model", "Claude Sonnet 5.5 (claude-sonnet-5-5)", "Claude Haiku 5.5 (claude-haiku-5-5)"),
    ("Effort", "medium", "low"),
    ("Thinking", "adaptive; shown as a summary, which we keep in the log", "default; not kept"),
    ("Limits", "16,000 output tokens per request; 20 requests per conversation", "4,000 tokens; one call per answer"),
    ("Tools", "the 6 tools above", "none"),
    ("Sees", "system prompt, tool descriptions, the user's messages, tool replies",
     "only the question, the conversation (user turns and every answer) and what the question expects"),
    ("Role", "chooses tools and arguments, answers the user", "judges checks 17, 18 and 22"),
], [3, 7, 7])
B("Why we keep the thinking summary: the API returns the agent's reasoning only as a summary (display 'summarized'); "
  "the cost is the same as without it. It lets us see why the agent chose a level or a tool (e.g. HD1: it estimated "
  "4–5 PJ from the network but called it 'unverified').")
B("The thinking summary is never scored: no check reads it. It is for reading and for explaining results.")

H("5. The experiment")
B("Arms: v0 (relations only) and v1 (relations + values). Only what model_network returns differs; prompt, tool names "
  "and descriptions are identical.")
B("Question bank v3: 31 questions in 29 conversations (Q10b → D2b → N1 is one conversation). Seven types: evaluate a "
  "policy in real-world units (11), in-between quantities (3), reach an emissions target (3), robustness (2), "
  "trade-offs (2), outside the model (3), hypothesis questions HA1–HE1 (5).")
B("Each question has a spec fixed in advance: the answer key (e.g. the lever level that matches the user's words, "
  "computed from the runs), required tools, required mentions/statements, expected direction or source.")
B("Tags: dev (used while building), designed (written for the test), blind (not seen while building), "
  "hypothesis (pre-registered predictions about v0 vs v1).")
B("Five repetitions per question and arm, because the same question can get different answers (seen in HC1).")
B("Questions, keys, checks and the analysis were committed to git before the first conversation (pre-registration).")

H("6. What we ran, in order")
T(["Date", "Run", "Size", "What it was for"], [
    ("10-21", "Network smoke test", "a few conversations", "first real agent on the new model_network tool"),
    ("10-26", "Hypothesis smoke tests (3 runs)", "10 conversations each",
     "check HA1–HE1 read as intended; third run with thinking summary and the reader"),
    ("10-26", "Source-label test (before / after)", "40 conversations",
     "HC1: unlabeled baseline GDP misled the agent; a label fixed it (results_source_labels.md)"),
    ("10-26", "Dry run", "58 conversations, US$3.56", "find scoring bugs and tool usability issues; not counted"),
    ("10-26/27", "Full run (bank v3)", "290 conversations, US$20.05", "the experiment; scored with rules + reader"),
], [2, 4.5, 4, 6.5])
P("All runs are in metamodel/chatbot_deploy/backend/rdm/eval/pilot_runs/; the full run is bank_v3_full/.")

H("7. What each log stores")
P("One JSON file per conversation, e.g. AG1_v1_r0.json (question AG1, arm v1, repetition 0). Everything below is "
  "recorded as it happened; nothing is judged here.")
T(["Field", "What it holds"], [
    ("question, question_id, arm, rep", "what was asked, in which arm and repetition"),
    ("model, effort", "the agent model and effort used"),
    ("versions", "git commit, and fingerprints (hashes) of the system prompt, tools, data tables and surrogate"),
    ("user_messages", "every user turn: the question and each scripted reply, and whether the agent had asked"),
    ("messages", "the full conversation: agent text, thinking summaries, tool calls, tool replies"),
    ("tool_log", "one entry per tool call: tool, arguments, ok/error and error code, full reply, size, user turn"),
    ("requests", "one entry per API request: tokens in/out, cache, why the model stopped"),
    ("answers", "every answer the agent gave, one per user turn (95 of 290 conversations have more than one: "
                "the agent asked something, the scripted user replied, the agent answered again)"),
    ("final_answer", "the last of those answers"),
    ("steps, seconds, hit_step_limit, final_stop_reason", "length of the conversation and how it ended"),
], [5, 12])

H("8. How we evaluate")
P("eval/failure_modes.py reads each log and writes one row per conversation with one column per check "
  "(True = the failure happened; empty = the check does not apply to that question). Two kinds of evaluation, kept apart:")
T(["Source", "Checks", "How"], [
    ("Code rules on the log (exact, repeatable)",
     "1–12, 15, 16, 19–21, 23–25: e.g. level off the key, literal translation, uncertainty fixed, required step "
     "skipped, numbers no tool gave, no numeric range, required mentions",
     "Python reads the tool calls, arguments and the final answer text (regular expressions)"),
    ("Haiku reader (a model's judgment)",
     "13 forecast language · 14 names a winner · 17 wrong direction of an effect · 18 wrong source for a number · "
     "22 a required statement missing",
     "Haiku reads the question + the whole conversation + what is expected and replies true/false with one sentence why"),
], [4, 7.5, 5.5], [GREEN, ORANGE])
B("What Haiku does NOT see: the tool calls, the tool replies, the agent's thinking, the system prompt. So it can say "
  "whether the answer states the right thing, not whether the agent did the right thing.")
B("Haiku runs only on questions whose spec has an expected direction, an expected source or required statements.")
B("Which answer is scored: every answer of the agent, for the rules (15, 16, 19) and for Haiku, since the review "
  "of 2026-10-28; check 24 reads the answer before the scripted reply. Details of every rule: "
  "docs/evaluation_rules_2026-10-28_v2.docx.")
B("Fix of 2026-10-28: until then Haiku read only the final answer. F2 ('Make Uganda greener') requires 'asks what "
  "greener means before running anything'; the agent asks in its first answer, so Haiku marked it missing in 10 of 10 "
  "while check 9 (from the tool calls) showed the agent did ask first. Haiku now reads every answer; all 290 "
  "conversations were re-scored (no conversation re-run, rule checks unchanged).")
B("Effect: check 22 failures 81 → 62 (18 changed from missing to present: F2 10, HA1 4, S35 2, C4b 1, TO1 1; none the "
  "other way); check 18 failures 9 → 4; check 17 still 0. The old scores are kept as failure_modes_before_reader_fix.csv.")
B("analyze_bank.py compares v0 vs v1 per check (permutation test, by question group) → analysis_primary.csv.")

H("9. Results so far (full run)")
T(["Result", "v0 (relations)", "v1 (+ values)"], [
    ("Policy level off the answer key (75 policy questions per arm)", "79%", "1%"),
    ("Words taken literally ('40%' → 0.4)", "50%", "0%"),
    ("model_network calls per conversation", "2.3", "1.3"),
    ("Comparisons sent to trade_off_analysis (Q14b + TO1, 5 repetitions each)", "0 of 10", "4 of 10"),
    ("Conversations with a number no tool gave", "6 of 145", "12 of 145"),
    ("Uncertainty range wrong or missing", "0", "0"),
], [9, 4, 4])
B("Rows 1–3: p < 0.01 in every question group tested.")
B("The 10 in the trade-off row: the two comparison questions (Q14b cooking fuels vs deforestation; TO1 landfill methane "
  "vs less cooking/heating energy) × 5 repetitions. v1 used trade_off_analysis in Q14b 1 of 5 and TO1 3 of 5.")
B("RQ1: 290/290 finished, no loops, no invented thresholds, no forecasts; a scripted user ran all three RDM components "
  "in one conversation (Q10b → D2b → N1).")
B("Design lessons from the pilots: unlabeled numbers mislead (HC1 GDP); tool wording decides which RDM step the agent "
  "takes (trade_off_analysis); the agent may trust the surrogate over the network (HD1).")
B("Not yet in these numbers: your reader check (affects checks 13, 14, 17, 18, 22).")

H("10. The review tables (new today)")
P("Folder metamodel/chatbot_deploy/results_analysis/, made by code/write_review_workbook.py from the logs (no API calls).")
B("full_run_review.xlsx, for reading. Header colours: blue = from the log, green = code rules, orange = Haiku, "
  "yellow = your marks. 'By question' shows the 5 answers and the tools of each question side by side.")
B("full_run_analysis.xlsx, for statistics in Python: Conversations (290 rows), Tool calls (1,082), Lever settings "
  "(3,389), joined on 'conversation'; a 'Columns' sheet explains each column.")

H("11. Where we are and what is next")
T(["#", "Item", "Who"], [
    ("1", "IMPORTANT: review Haiku's results — mark the 20 reader judgments in full_run_review.xlsx ('Your mark') or "
          "docs/reader_check_2026-10-28.docx (re-scored, same 20 conversations)", "Alexa"),
    ("1a", "Review the code-rule checks (docs/evaluation_rules_2026-10-28_v2.docx)", "Alexa"),
    ("1b", "Deck: make the harness more visible (it keeps the log, plays the user, enforces rules, starts each "
           "conversation from zero)", "Claude"),
    ("2", "Deck: model settings on slides 8 and 15 + appendix slide", "Claude"),
    ("3", "Elicit prompts for the literature review (Word)", "Claude"),
    ("4", "Commit the tables and code; push when you say", "Claude / Alexa"),
    ("5", "After 1: drop 'reader checks pending' from the RQ1 and RQ2 slides; write the full-run results document", "Claude"),
    ("6", "Presenter and co-author names; surrogate slide", "Alexa / team"),
    ("7", "Team questions: X57 GDP range below the base path? whether F-gas transformations (DEC_HFCS, DEC_OTHER_FCS) are fixed in every run", "team"),
    ("8", "Later: XGBoost overfitting review (k-fold), BAU extrapolation check, network gaps (L12, 9 outputs)", "Claude"),
], [1, 13, 3])

H("12. Where things are")
T(["What", "Path (from metamodel/chatbot_deploy/)"], [
    ("Agent loop and settings", "backend/rdm/harness/agent.py"),
    ("System prompt / tool descriptions", "backend/rdm/harness/prompt.py, registry.py"),
    ("Tools", "backend/rdm/tools/"),
    ("Questions, specs, scripted replies", "backend/rdm/eval/questions.py; docs/test_questions.docx"),
    ("Checks and Haiku reader", "backend/rdm/eval/failure_modes.py"),
    ("Statistics v0 vs v1", "backend/rdm/eval/analyze_bank.py"),
    ("Full-run logs and scores", "backend/rdm/eval/pilot_runs/bank_v3_full/ (failure_modes.csv, analysis_*.csv)"),
    ("Review tables", "results_analysis/"),
    ("Reader check (Word)", "docs/reader_check_2026-10-28.docx"),
    ("Deck (your latest)", "~/Downloads/DMDU_2026_Talk_draft.pptx"),
], [5.5, 11.5])

doc.save(OUT)
print(OUT)
