# Requires python-docx (system python3). Run from metamodel/chatbot_deploy:
#     python3 backend/rdm/eval/write_e3_questions_docx.py
"""E3 question table for Alexa's approval: docs/E3_questions_2026-11-17.docx (never overwritten).
Reads backend/rdm/eval/e3_reference.json (written by e3_questions.py) and the bank's 15 T1 questions."""
import ast
import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

REF = Path("backend/rdm/eval/e3_reference.json")
OUT = Path("docs/E3_questions_2026-11-17.docx")
FONT = "Times New Roman"
# what the agent sees at the lever: the relevant input, BAU → range maximum, 2050 (model_network input_values)
SETS = {
    "S50": "fraction of landfill gas recovered: 7% → 55%",
    "S3": "no-till share of each crop (e.g. cereals): 0.1% → 59%; residues removed / burned",
    "R1": "biogas recovery factor at treatment plants: 0 → 0.49",
    "R3": "share of electricity lost in transmission: 11.7% → 5.5%",
    "R6": "share of food produced that is lost: 2.9% → 2.1%",
    "R8": "share of incinerated municipal waste recovered for energy: 4% → 56%",
    "N1": "share of incinerated industrial waste recovered for energy: 4% → 56%",
    "N2": "biogas recovery factor at manure digesters: 0.50 → 0.74",
    "N3": "share of cattle manure incinerated (dairy 6% → 2.7%; others), among 22 manure-management shares",
    "N4": "share of glass recycled: 6% → 55% (and 6 other materials)",
    "N5": "share of food waste composted: 5% → 28%",
    "N6": "share of food waste treated anaerobically: 12% → 31%",
    "R4": "electricity share of each industry's energy (e.g. agriculture industry 16% → 56%; 162 inputs)",
    "R5": "appliance energy demand: × 1.00 → × 0.54",
    "R7": "passenger and freight transport demand: × 1.00 → × 0.79",
    "S35": "fuel mix of cars and vans (electric 50% → 72%)",
    "HD1": "fuel mix of cars and vans (electric 50% → 72%)",
    "O1": "heat energy demand of buildings: × 1.00 → × 0.63",
    "O2": "shares of urban wastewater by treatment type (e.g. advanced anaerobic 6% → 41%)",
    "O3": "fuel efficiency of industrial energy use: 0.67 → 0.89",
}
NOTES = {
    "S3": "E1 asked 'how many hectares' (now the explicit wording); the general wording is new.",
    "R1": "Large value (more than landfill gas); it is the model's value.",
    "R8": "Same lever as N1 (L52).",
    "N1": "Same lever as R8 (L52).",
    "N2": "R2 (E2) asked about the same biogas through another lever (L20, manure management); the agent could pick "
          "either lever. The key is L19's.",
    "N3": "The amount falls (0.92 → 0.55 million t from the lever's bottom to top third).",
    "N5": "Same lever as N6 (L49).",
    "N6": "Same lever as N5 (L49).",
    "R5": "256 PJ is about 71 TWh, many times today's use; it is the model's value in 2050.",
    "S35": "E1 asked 'how many kilometres'; this general wording is new.",
    "HD1": "Asks for a change: key = increase of about 3–5 PJ (56.0 → 59.9 PJ), as in E1.",
}


def fmt(x, unit):
    if unit == "tonne":
        return f"{x / 1e6:.2f} million t" if x >= 1e6 else f"{x:,.0f} t"
    if unit == "ha":
        return f"{x / 1e6:.2f} million ha"
    if unit == "vehicle-km":
        return f"{x / 1e9:.1f} billion vehicle-km"
    return f"{x:.1f} {unit}"


def shade(cell, fill):
    tc = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"), sh.set(qn("w:color"), "auto"), sh.set(qn("w:fill"), fill)
    tc.append(sh)


def para(doc, text, size=10.5, bold=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name, r.font.size, r.bold = FONT, Pt(size), bold
    return p


def table(doc, cols, widths, rows, header_fill="D9E2F3"):
    t = doc.add_table(rows=1, cols=len(cols))
    t.style = "Table Grid"
    for c, h in zip(t.rows[0].cells, cols):
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.name, r.font.size = True, FONT, Pt(8.5)
        shade(c, header_fill)
    for vals in rows:
        cells = t.add_row().cells
        for c, v in zip(cells, vals):
            c.text = ""
            r = c.paragraphs[0].add_run(str(v))
            r.font.name, r.font.size = FONT, Pt(8.5)
    for row in t.rows:
        for c, w in zip(row.cells, widths):
            c.width = Cm(w)
    return t


def t1_questions():
    src = Path("backend/rdm/eval/questions.py").read_text()
    bank = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "BANK" and isinstance(node.value, ast.Dict):
            bank = ast.literal_eval(node.value)
            break
    ids = ["P50i", "P12i", "B6", "AG1", "LV1", "BLD1", "WW1", "H1", "H2", "H3", "X1", "D3b", "HA1", "HE1", "TO1"]
    return [(q, bank[q]) for q in ids]


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists (it may hold Alexa's marks); write a new name")
    ref = json.loads(REF.read_text())
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.3))

    para(doc, "E3 questions — for your approval", 14, True)
    para(doc, "17 November 2026. Plan approved (docs/run_design_E3_DRAFT_v2_2026-11-17, 393 conversations). Nothing "
              "has been run on these questions. When you approve (or edit) them, they are frozen in git with the run "
              "design before the first conversation.")
    para(doc, "How to read the table", 11, True)
    for line in [
        "Every question is a policy in plain words, at the most ambitious level the model explores, for 2050. Its "
        "answer is a quantity the surrogate does not report: the agent has to find it in the model network, two or "
        "three steps after the lever.",
        "Answer key: the value the network shows for the lever's top third in 2050 (median, and the p10–p90 range "
        "across the runs), the same rule as E2. A valid answer gives a value inside the range, in the asked unit.",
        "Share-type: what the lever sets (column 'What the agent sees at the lever') is a share of the very quantity "
        "the question asks for, e.g. 'share of food lost' for 'how much food would be lost'. This is where the agent "
        "stopped in E1/E2. Please check each label.",
        "General vs explicit wording: identical except that the explicit one names the unit of the amount ('how many "
        "tonnes'). Explicit wordings are only for the share-type set (experiment E3c).",
        "Columns 'OK?' and 'Your edits': mark y / n and write any change. If you change a wording, I recompute nothing "
        "(keys do not depend on wording); if you change a target, I recompute its key.",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(line)
        r.font.name, r.font.size = FONT, Pt(10)

    cols = ["ID", "New?", "Question — general wording", "Question — explicit wording (E3c)",
            "What the agent sees at the lever (BAU → maximum, 2050)", "Where the answer is (steps from the lever)",
            "Answer key, 2050 (median; p10–p90)", "Share-type: why", "Note", "OK? (y/n)", "Your edits"]
    widths = [0.9, 0.9, 4.6, 4.6, 3.6, 3.0, 2.8, 2.6, 2.8, 0.9, 2.2]

    def rows(set_name):
        out = []
        for qid, r in ref.items():
            if r["set"] != set_name:
                continue
            u = r["unit"]
            key = (f"{fmt(r['key_median'], u)}; {fmt(r['key_p10'], u)} to {fmt(r['key_p90'], u)}"
                   if qid != "HD1" else "an increase of about 3–5 PJ (56.0 → 59.9 PJ)")
            out.append([qid, "new" if r["new"] else "E1/E2", r["question_general"], r["question_explicit"] or "—",
                        f"L{r['lever']} {r['lever_name']}: {SETS[qid]}",
                        f"{r['node']} ({r['steps_from_lever']} steps)", key, r["why_share_label"],
                        NOTES.get(qid, ""), "", ""])
        return out

    para(doc, "")
    para(doc, "Set S — 12 share-type questions (experiments E3a, E3b, E3c; 5 repetitions)", 11.5, True)
    table(doc, cols, widths, rows("S"))
    para(doc, "")
    para(doc, "Set O — 8 other-type questions (E3a check only; general wording; 3 repetitions)", 11.5, True)
    para(doc, "Here the lever sets something that is not a share of the asked quantity (a fuel mix, a demand "
              "multiplier, an efficiency factor). E1/E2: the agent walked on to the answer more often (17 of 25).", 10)
    table(doc, cols, widths, rows("O"))
    para(doc, "")
    para(doc, "Set G — 15 translation questions (E3b guard; unchanged from the October bank; 1 repetition)", 11.5, True)
    para(doc, "Checks that the role sentence does not harm translating the user's words into a lever level "
              "(Map+ was off the key in 1 of 75). Shown for completeness; no change proposed.", 10)
    table(doc, ["ID", "Question (as in the October bank)"], [1.5, 26.0],
          [[q, x if isinstance(x, str) else x["question"]] for q, x in t1_questions()], header_fill="EDEDED")
    para(doc, "")
    para(doc, "Your decision", 11.5, True)
    para(doc, "Approve or edit each question (columns 'OK?' and 'Your edits'), and check each share-type label. Then "
              "I build the three new arms, run a smoke test on a G question, commit and tag the frozen design, and "
              "launch.")
    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
