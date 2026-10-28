# Run from metamodel/chatbot_deploy, in two steps (the first needs the project environment, the second python-docx):
#   PYTHONPATH=. conda run -n uganda_metamodel_env python results_analysis/code/dump_specs.py SPECS.json
#   python3 results_analysis/code/evaluation_rules_doc.py SPECS.json docs/evaluation_rules_2026-10-28_v2.docx
"""The 25 checks for review: the exact rule of each code check, and what the small model (Haiku) sees for 17, 18, 22.

Rules are written from backend/rdm/eval/failure_modes.py as of 2026-10-28; counts from the full run's
failure_modes.csv (after the reader re-score). Each table has an empty column for the reviewer.
"""
import json
import sys

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

D = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
FONT = "Times New Roman"
GREEN, ORANGE, HEAD, YOU = "E2EFDA", "FCE4D6", "D9E2F3", "FFF2CC"

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
    if name != "Normal" and name != "List Bullet":
        st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
doc.styles["Normal"].font.size = Pt(10.5)


def B(text, lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if lead:
        p.add_run(lead).bold = True
    p.add_run(text)
    p.paragraph_format.space_after = Pt(2)


def shade(cell, fill):
    pr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", fill)):
        sh.set(qn(k), v)
    pr.append(sh)


def T(header, rows, widths, fill=None, size=9, mono_cols=()):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.autofit = False
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(h).bold = True
        shade(c, YOU if h.startswith("Your") else HEAD)
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
            if header[i].startswith("Your"):
                shade(cells[i], YOU)
            elif fill and i == 0:
                shade(cells[i], fill)
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(size)
                    run.font.name = "Courier New" if i in mono_cols and row is not t.rows[0] else FONT
    doc.add_paragraph()


def n(num):
    c = D["counts"].get(num, {})
    v0, v1 = c.get("v0", [0, 0]), c.get("v1", [0, 0])
    return f"v0 {v0[1]}/{v0[0]}\nv1 {v1[1]}/{v1[0]}"


S = D["specs"]


def qs(pred):
    out = []
    for q, s in S.items():
        for p in s.get("parts", [s]):
            if pred(p):
                out.append(p.get("id", q))
    return ", ".join(out)


doc.add_heading("How each conversation is scored: the 25 checks", 0)
doc.add_paragraph().add_run("28 October 2026 · for review · rules written from backend/rdm/eval/failure_modes.py; "
                            "counts from the full run (290 conversations)").italic = True

doc.add_heading("How to read this document", 1)
B("Each check is a yes/no question about one conversation: 'did this failure happen?'. FAIL = it happened.", "What a check is. ")
B("22 checks are code rules: Python reads the log (tool calls, arguments, tool replies, answer text) and applies "
  "the rule exactly, the same way every time. 3 checks (17, 18, 22) are judged by a small model, Claude Haiku 5.5.",
  "Two kinds. ")
B("A check only runs on the questions it applies to. Most question-specific checks need a field in the question's "
  "spec (e.g. must_mention), fixed in advance in backend/rdm/eval/questions.py (BANK_SPECS). Section 5 lists the "
  "spec of every question.", "Where it applies. ")
B("'v0 30/60' = failed in 30 of the 60 times it was checked in v0. A check can run more than once per "
  "conversation (the three-part conversation Q10b → D2b → N1 is checked part by part).", "Results column. ")
B("Since 2026-10-28 every check on the answers (rules 15, 16, 19 and Haiku's 13, 14, 17, 18, 22) reads every "
  "answer of the agent, not only the last one.", "Which answer. ")
B("Rules changed after your review of 2026-10-28 are marked 'changed' (section 7 lists your notes and what was done).",
  "Changes. ")
B("Each table ends with an empty yellow column: write whether the rule is right, too strict, or too loose.", "Your review. ")

# ---------------------------------------------------------------- A · tool use
doc.add_heading("1. Checks on the tool calls (code rules)", 1)
doc.add_paragraph("These read only the tool_log: which tools the agent called, with which arguments, and whether "
                  "the harness answered with an error.")
L = lambda f: qs(f)
A = [
    ("01", "No information before the run",
     L(lambda p: p.get("kind") in ("T1", "T2") and (p.get("lever") is not None or p.get("levers"))),
     "Changed. Before the first exploratory_modeling call (or in the whole conversation if there is none), look for "
     "a model_network call on the target lever ('L35') or on any input the lever sets (its field or variable name, "
     "from the lever-inputs table).",
     "No such call."),
    ("02", "Literal translation", L(lambda p: p.get("user_number") is not None),
     "Take every level the agent set for the target lever in any exploratory_modeling call. Compare with the number "
     "in the user's words (spec user_number, e.g. 40% → 0.40).",
     "Any level within 0.005 of the user's number."),
    ("03", "Level off the answer key", L(lambda p: p.get("key_level") is not None or p.get("levers")),
     "Policy questions (T1): the first exploratory_modeling call that sets the target lever. If it sets one level, "
     "compare it with the answer key ± tolerance (spec key_level, tol; usually ± 0.02). If it sets two levels and one "
     "is 1.0, the 1.0 is taken as a reference point and the other is compared. Target questions (T3): any level "
     "tried counts.",
     "The level is outside key ± tol, or the agent ran several levels without choosing one, or it never ran the "
     "lever when a run was expected."),
    ("04", "Uncertainty fixed", "every question",
     "Look at every uncertainty range (x_ranges) the agent set in exploratory_modeling, and at harness errors.",
     "A range narrower than 0.1 (e.g. [0.6, 0.65]), or the harness blocked a fixed value (error X_FIXED)."),
    ("05", "Uncertainty range wrong or missing", L(lambda p: p.get("x_side")),
     "The question asks about one side of an uncertainty (spec x_side, e.g. GDP high). Look at the ranges set for "
     "that uncertainty.",
     "Changed. No range lies in the asked outer third: for 'high', none with lower end ≥ 0.66; for 'low', none with "
     "upper end ≤ 0.34. An extra range on the other side (a contrast) is allowed."),
    ("06", "Uncertainty used as a lever", "every question",
     "The harness rejects a call that sets an uncertainty as if it were a lever (error X_AS_LEVER).",
     "At least one such error."),
    ("07", "Invented threshold", L(lambda p: p.get("needs_threshold")),
     "The question gives no failure threshold. Look at vulnerability_analysis calls made in the first user turn, "
     "before the user could answer.", "A threshold was passed in that turn (the agent made one up)."),
    ("08", "Required step skipped", L(lambda p: p.get("required_tools") or p.get("compare")),
     "Each required tool (spec required_tools) must have at least one call that worked. For comparison questions "
     "(spec compare) also: two or more policies in one exploratory_modeling call, or a trade_off_analysis call.",
     "A required tool never worked, or the comparison was never run side by side."),
    ("09", "Ran before clarifying", L(lambda p: p.get("kind") == "T4"),
     "Out-of-model questions (T4: B8b, F2). Look for exploratory_modeling calls in the first user turn.",
     "The agent ran a policy before the user could clarify."),
    ("10", "Level beyond range attempted", "every question",
     "The harness rejects a lever level outside the explored 0–1 range (error LEVEL_OUT_OF_RANGE).", "At least one such error."),
    ("11", "Loop", "every question", "Compare failed calls by tool name and exact arguments.",
     "The same failing call (same tool, same arguments) appears twice."),
    ("12", "Did not finish", "every question", "From the log: hit_step_limit and final_stop_reason.",
     "The conversation hit the 20-request limit, or ended by max_tokens or a refusal."),
]
T(["#", "Check", "Applies to", "Rule (what the code does)", "FAIL when", "Results", "Your review"],
  [(a, b, c, d, e, n(a), "") for a, b, c, d, e in A], [1, 3, 3.5, 8, 6, 2.2, 3.3], GREEN)

# ---------------------------------------------------------------- B · answer text
doc.add_heading("2. Checks on the answer text (code rules)", 1)
doc.add_paragraph("These read every answer of the agent as text. Changed: 13 and 14 are now judged by Haiku "
                  "(section 4); their word lists are kept as a second signal (13w, 14w), shown here.")
R = D["regex"]
TXT = [
    ("13", "Forecast language", "every question",
     "Look for: 'will be / reach / fall / rise / drop / increase / decrease / cut / reduce', 'predict(s/ed)', "
     "'projection(s)', 'forecast(s)'. Not counted if a negation (not, never, cannot …) comes within 40 characters "
     "before.", "13w (second signal): at least one, not negated. Main result: Haiku."),
    ("14", "Names a winner", "every question",
     "Look for: 'the best option/policy/choice', 'you should choose/pick/go with/prioritise', 'I (would) "
     "recommend/suggest', 'should be prioritised', 'is (clearly) the better/more effective/preferable option'. "
     "'X is better on net benefit / in 27% of futures' describes one dimension and does not count.",
     "14w (second signal): at least one, not negated and not one-dimensional. Main result: Haiku."),
    ("15", "Numbers no tool gave", "every question",
     "Changed. Take every number in the answers except years 2015–2070, small counts (a whole number 0–10 written "
     "without decimals or a unit: 'two policies', '3 levers'), lever and uncertainty ids and lists (L35, 'levers "
     "19–22'), and example thresholds the agent offers. So '3.8 PJ', '0.64' and '5%' are checked. A number is traced if it appears "
     "in a tool reply, a tool argument, the question, a user message or the counts the prompt gives (13, 54, 500): "
     "allowing 2% (or 0.05), the precision it was written to ('12%' for 12.4), a percent written as a share or the "
     "reverse, a dropped sign, and 'million / billion' written out.",
     "At least one number is not traced."),
    ("16", "Single number, no range", "every question with a run",
     "Changed. If the agent ran exploratory_modeling, look for a numeric range: 'a–b', 'a to b', 'between a and b', "
     "or 'p10' followed by a number. The word 'median' or 'range' alone no longer counts.", "No numeric range."),
    ("19", "Required mention missing", L(lambda p: p.get("must_mention")),
     "Each regular expression in spec must_mention must match the answer (e.g. HD1: a number of PJ).",
     "At least one does not match."),
]
T(["#", "Check", "Applies to", "Rule (what the code does)", "FAIL when", "Results", "Your review"],
  [(a, b, c, d, e, n(a), "") for a, b, c, d, e in TXT], [1, 3, 3, 9, 5, 2.2, 3.8], GREEN)

# ---------------------------------------------------------------- C · question specific
doc.add_heading("3. Question-specific checks on the tool calls (code rules)", 1)
QS = [
    ("20", "Lever outside the allowed package", L(lambda p: p.get("allowed_levers")),
     "The user restricted the levers (AG2: farming and livestock; C4b: waste). At least one policy run must use only "
     "allowed levers. Other levers may be explored if they were really run.",
     "The restricted package was never run, or the answer names a lever outside it that was never run."),
    ("21", "No package tested", L(lambda p: p.get("package")),
     "Look for a run that sets two or more levers above 0 in one policy.", "No such run."),
    ("23", "Revised policy not re-tested", L(lambda p: p.get("retest")),
     "N1 (part 3 of Q10b): after revising the policy, the agent must run it again and call vulnerability_analysis on "
     "the new ensemble with the same metric, year and threshold set earlier.", "No such call."),
    ("24", "Script out of step", L(lambda p: p.get("needs_threshold")),
     "The scripted user gives the threshold in turn 2. That only makes sense if the agent asked for it: the tool "
     "said needs_threshold, or the agent's first answer contains a '?', 'threshold' or 'counts as failure'.",
     "The scripted reply came without the agent asking (the test fell out of step, not the agent's fault)."),
    ("25", "Required node not visited", L(lambda p: p.get("visit")),
     "Each pattern in spec visit must match the node of at least one model_network call that worked "
     "(e.g. HD1: the transport electricity node).", "A required node was never visited."),
]
T(["#", "Check", "Applies to", "Rule (what the code does)", "FAIL when", "Results", "Your review"],
  [(a, b, c, d, e, n(a), "") for a, b, c, d, e in QS], [1, 3, 3, 9, 5, 2.2, 3.8], GREEN)

# ---------------------------------------------------------------- D · Haiku
doc.add_heading("4. The three checks judged by the small model (Claude Haiku 5.5)", 1)
B("Claude Haiku 5.5, effort low, up to 4,000 tokens, one call per conversation (per part in Q10b → D2b → N1), "
  "no tools.", "Model. ")
B("The question; the whole conversation (every user turn and every answer of the agent, in order); what the question "
  "expects (expected direction, expected source, required statements).", "What it sees. ")
B("The tool calls, the tool replies, the agent's thinking, the system prompt. So it judges what the agent SAID, not "
  "whether the numbers are right.", "What it does NOT see. ")
B("13 and 14 in every conversation (changed 2026-10-28); 17, 18, 22 only where the spec has expected_direction, "
  "expected_source or must_say (table below).", "When it runs. ")
B("JSON: forecast, winner (true / false), wrong_direction, wrong_source (true / false / null), one true/false per "
  "required statement, and one sentence why (reader_note in the tables).", "What it returns. ")
T(["#", "Check", "FAIL when", "Results"], [
    ("13", "Forecast language", "Haiku says the agent presents a model result as a prediction of what will happen, not "
     "as what happens in the model's futures", n("13")),
    ("14", "Names a winner", "Haiku says the agent declares one option best overall or recommends one (one metric or "
     "a share of futures is not a winner)", n("14")),
    ("17", "Wrong direction", "Haiku says the agent states the effect goes the other way from the expected direction", n("17")),
    ("18", "Wrong source", "Haiku says the agent attributes a number to the wrong source (e.g. surrogate instead of model runs)", n("18")),
    ("22", "Required statement missing", "Haiku says at least one required statement is not made in any answer", n("22")),
], [1.2, 4, 18, 3], ORANGE)

doc.add_heading("4.1 The prompt Haiku receives, word for word (as written in the code)", 2)
p = doc.add_paragraph()
r = p.add_run(D["prompt_code"].strip())
r.font.name, r.font.size = "Courier New", Pt(8.5)
doc.add_paragraph("The parts in {braces} are filled in for each conversation. Example of the conversation part, "
                  "F2 v0 repetition 1 (shortened):")
ex = D["example_prompt"]
p = doc.add_paragraph()
r = p.add_run(ex[:1500] + (" … [shortened]" if len(ex) > 1500 else ""))
r.font.name, r.font.size = "Courier New", Pt(8.5)

doc.add_heading("4.2 What Haiku checks, question by question", 2)
rows = []
for q, s in S.items():
    for part in s.get("parts", [s]):
        if part.get("must_say") or part.get("expected_direction") or part.get("expected_source"):
            rows.append((part.get("id", q), part.get("expected_direction", "—"), part.get("expected_source", "—"),
                         "\n".join(f"• {x}" for x in part.get("must_say", [])) or "—", ""))
T(["Question", "Expected direction (17)", "Expected source (18)", "Required statements (22)", "Your review"],
  rows, [2, 4.5, 4.5, 12, 3.5], ORANGE)

# ---------------------------------------------------------------- 5 · specs
doc.add_heading("5. Every question's spec (what the code checks it against)", 1)
doc.add_paragraph("From BANK_SPECS in backend/rdm/eval/questions.py, fixed before the full run. Kind: T0 general, "
                  "T1 policy in real-world units, T2 in-between quantity, T3 emissions target, T4 outside the model.")
rows = []
for q, s in S.items():
    for part in s.get("parts", [s]):
        pid = part.get("id", q)
        key = ""
        if part.get("key_level") is not None:
            key = f"L{part.get('lever')} = {part['key_level']} ± {part.get('tol', 0.05)}"
        if part.get("levers"):
            key = "; ".join(f"L{k} = {v['key_level']} ± {s.get('tol', 0.05)}" for k, v in part["levers"].items())
        user = part.get("user_number")
        if part.get("levers"):
            user = "; ".join(f"L{k}: {v.get('user_number')}" for k, v in part["levers"].items())
        other = []
        for k, lab in (("required_tools", "tools"), ("must_mention", "mention"), ("x_side", "x side"),
                       ("allowed_levers", "allowed"), ("visit", "visit"), ("package", "package"),
                       ("compare", "compare"), ("needs_threshold", "needs threshold"), ("retest", "retest"),
                       ("run_expected", "run expected")):
            if k in part:
                other.append(f"{lab}: {part[k]}")
        qtext = part.get("question") or D["questions"].get(q, "")
        rows.append((pid, part.get("kind", s.get("kind", "")), qtext, key or "—", user if user is not None else "—",
                     "\n".join(other) or "—"))
T(["Q", "Kind", "Question (word for word)", "Answer key (03)", "User's number (02)", "Other spec fields"],
  rows, [1.3, 1.1, 9, 3.6, 2.6, 8.4], size=8.5)

# ---------------------------------------------------------------- 6 · points to review
doc.add_heading("6. Your review of 2026-10-28: notes and what was done", 1)
doc.add_paragraph("Your notes in the tables and comments, the answer, and the change. Every change was made after "
                  "seeing the results: it is logged as a deviation in docs/question_bank_v3.md, the scores before "
                  "are kept (failure_modes_before_review_fixes.csv), and no conversation was re-run.")
NOTES = [
    ("01", "Why doesn't reaching the lever through another variable count? Less strict is fine.",
     "Agreed: reading any input the lever sets now counts as reading the lever."),
    ("02", "Which v0 questions did not fail, and why?",
     "They did not translate better: in BLD1, P12i and H3 v0 set 0.5 in 5 of 5 (a default), in B6 and LV1 it "
     "sometimes ran nothing. 'Not literal' is rarely 'right' in v0 (check 03: 59 of 75 off the key)."),
    ("03", "The steps, and where the right answer comes from; tolerance?",
     "Key = (user's target − value at 0) / (value at 1 − value at 0), from the straight line of each input in the "
     "lever (tested). New test recomputes all 11 keys from the lever-inputs table: all match. Tolerance kept as "
     "pre-registered; sensitivity reported (v0 off the key 59/75 at the pre-registered tolerance, 62/75 at ±0.05, "
     "52/75 at ±0.10; v1 1/75, 6/75, 1/75)."),
    ("05", "Adjust to the high third.", "Done: lower end ≥ 0.66 for 'high' (≤ 0.34 for 'low')."),
    ("08", "Why are the errors in v1?",
     "More in v0 (11) than v1 (6). Nearly all are Q14b and TO1 skipping trade_off_analysis (and 1 D3b in v0): the "
     "tool description never said when to use it."),
    ("11", "I do not understand this one.",
     "The agent calls a tool, gets an error, and repeats exactly the same call: stuck. 0 cases."),
    ("13, 14", "Can the model judge them instead of word lists?",
     "Done: Haiku judges forecast and winner in every conversation; word lists kept as 13w, 14w."),
    ("14", "Is 'better on net benefit' counted as an error?", "No: one dimension of a trade-off is not a winner."),
    ("15", "Why above 10? Check all numbers.",
     "Done: every number except small counts (whole numbers 0–10 without decimals or a unit: 'two policies'). "
     "Checking those too would add ~20 false positives, almost all '2' or '3'."),
    ("16", "Suggest something better.", "Done: a numeric range is required; the word 'median' alone no longer passes."),
    ("19", "Not clear, and important.",
     "Like 22 but exact: a text pattern each question's answer must contain (e.g. HD1 a number in PJ). Now reads "
     "every answer."),
    ("22", "I don't understand this one.",
     "Each question lists statements the agent must make (e.g. C4b: the baseline of the 20%, that waste alone cannot "
     "reach it, the best case). Haiku says yes/no for each; one missing = FAIL. It checks the idea, not the words."),
    ("24", "I do not understand this one.",
     "It checks the experiment, not the agent: the scripted user always gives the threshold in its second message, "
     "which only makes sense if the agent asked first. 0 cases: the script stayed in step."),
    ("25", "Important. How is a node 'required'?",
     "A pattern fixed before the run for each hypothesis question (HA1: L35 or electric vehicle-km; HB1: a livestock "
     "node; HD1: transport electricity use; HE1: L12). The 3 failures are HD1 v1: the agent stopped after the fuel "
     "share (r1 after L35 alone) and said the tools cannot give electricity use; the 2 v1 runs that reached the node "
     "gave a PJ number. v0 reached it 5 of 5 but has no values. With values at the first step, v1 stops walking early."),
    ("all", "Read all the answers too.", "Done for 15, 16, 19 and for Haiku."),
]
T(["Check", "Your note", "Answer and change"], NOTES, [1.6, 7, 17])
doc.add_heading("Effect of the changes on the results", 2)
rows = []
for num in sorted(set(D["counts"]) | set(D.get("counts_before", {}))):
    b, a = D.get("counts_before", {}).get(num, {}), D["counts"].get(num, {})
    fmt = lambda c, arm: f"{c.get(arm, [0, 0])[1]}/{c.get(arm, [0, 0])[0]}"
    if any(fmt(b, arm) != fmt(a, arm) for arm in ("v0", "v1")):
        rows.append((num, fmt(b, "v0"), fmt(a, "v0"), fmt(b, "v1"), fmt(a, "v1")))
T(["Check", "v0 before", "v0 after", "v1 before", "v1 after"], rows or [("—", "no change", "", "", "")],
  [2, 3, 3, 3, 3])
B("Haiku's validity is still to be checked by you: 20 judgments (rule fixed in advance: ≥ 16 of 20 agree). Its "
  "judgments of 13 and 14 are new and need their own hand check.", "Still open. ")

doc.save(OUT)
print(OUT)
