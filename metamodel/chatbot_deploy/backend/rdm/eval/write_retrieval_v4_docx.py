# Requires python-docx (system python3). Run from metamodel/chatbot_deploy:
#     python3 backend/rdm/eval/write_retrieval_v4_docx.py
"""The eight draft retrieval questions (retrieval_v4_reference.json) as a Word table for Alexa's approval:
docs/new_retrieval_questions_2026-11-16.docx. Nothing runs until she approves; then the questions are frozen."""
import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

REF = Path("backend/rdm/eval/retrieval_v4_reference.json")
OUT = Path("docs/new_retrieval_questions_2026-11-16.docx")
FONT = "Times New Roman"

# what the lever does, BAU → range maximum, in words (from model_network's input_values, 2050)
MOVES = {
    "R1": "Biogas recovery factor at treatment plants: 0 → 0.49",
    "R2": "Dairy manure to anaerobic digesters: 0% → 33% (and other management shares)",
    "R3": "Electricity lost in transmission: 11.7% → 5.5%",
    "R4": "Electricity share of industrial energy (e.g. agriculture and livestock industry): 16% → 56%",
    "R5": "Appliance energy demand: × 1.00 → × 0.54",
    "R6": "Food lost before consumption: 2.9% → 2.1% of production",
    "R7": "Passenger and freight transport demand: × 1.00 → × 0.79",
    "R8": "Incinerated waste recovered for energy: 4% → 56%",
}
NOTES = {
    "R1": "The value is larger than the landfill biogas of question S50 (about 0.7 million t). It is the model's "
          "value; worth a check with the modeling team.",
    "R5": "256 PJ is about 71 TWh, many times Uganda's electricity use today. It is the model's value in 2050; worth "
          "a check with the modeling team.",
    "R6": "The lever moves a small share (2.9% → 2.1%), so the value changes by about 19% between the lever's thirds.",
    "R7": "Three steps from the lever (the others are two), so it tests a longer search.",
    "R8": "A small quantity (about 12,000 t).",
}


def fmt(x: float, unit: str) -> str:
    if unit == "tonne":
        return f"{x / 1e6:.2f} million t" if x >= 1e6 else f"{x:,.0f} t"
    return f"{x:.1f} {unit}"


def shade(cell, hex_fill):
    tc = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"), sh.set(qn("w:color"), "auto"), sh.set(qn("w:fill"), hex_fill)
    tc.append(sh)


def para(doc, text, size=11, bold=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name, r.font.size, r.bold = FONT, Pt(size), bold
    return p


def main():
    ref = json.loads(REF.read_text())
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(10)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.6))

    para(doc, "Eight new retrieval questions — for your approval", 14, True)
    para(doc, "Draft, 16 November 2026. Nothing has been run on these questions. Once you approve (or edit) them, "
              "they are frozen in git with the run design before the first conversation, and run in all three arms "
              "(Map, Map+, Map+lever), five times each.")
    para(doc, "Each answer is an in-between quantity the surrogate does not predict: the agent has to find it in the "
              "model network. The answer key is what the network shows for the lever's top third in 2050 (median, "
              "and the p10–p90 range across the runs), the same rule as the landfill-gas, farmland and electric-car "
              "questions. A valid answer gives a value inside the range and says it comes from the model runs.")

    cols = ["", "Question (what the agent reads)", "The lever and what it moves (BAU → range maximum)",
            "Where the answer is", "Answer key, 2050 (median; p10–p90)", "Note", "OK? (y / n)", "Your edits"]
    widths = [0.8, 6.0, 4.2, 3.6, 3.4, 4.2, 1.3, 3.0]
    t = doc.add_table(rows=1, cols=len(cols))
    t.style = "Table Grid"
    for i, c in enumerate(cols):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(c)
        r.bold, r.font.name, r.font.size = True, FONT, Pt(9.5)
        shade(cell, "D9E2F3")
    for qid, q in ref.items():
        cells = t.add_row().cells
        u = q["unit"]
        vals = [qid, q["question"], f"L{q['lever']} {q['lever_name']}. {MOVES[qid]}",
                f"{q['node']} ({q['steps_from_lever']} steps from the lever)",
                f"{fmt(q['key_median'], u)}; {fmt(q['key_p10'], u)} to {fmt(q['key_p90'], u)}. "
                f"Bottom third: {fmt(q['low_third_median'], u)}",
                NOTES.get(qid, ""), "", ""]
        for c, v in zip(cells, vals):
            c.text = ""
            r = c.paragraphs[0].add_run(v)
            r.font.name, r.font.size = FONT, Pt(9.5)
    for row in t.rows:
        for c, w in zip(row.cells, widths):
            c.width = Cm(w)

    para(doc, "")
    para(doc, "How they were chosen", 11, True)
    para(doc, "From the network, not from any agent run: for every lever, the in-between variables two or three "
              "steps away with one field and values in the runs, kept when the lever moves them by at least 10% "
              "between its bottom and top third (58 candidates). One per sector, none used by an existing question.")
    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
