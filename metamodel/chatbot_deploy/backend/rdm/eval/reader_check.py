"""
Reader check for the full run (docs/question_bank_v3.md, "Run design"): 20 reader judgments written to a Word file
for Alexa to mark agree / disagree against the agent's answer. Since 2026-10-30 the draw is by question (Alexa's
call, before any mark): 10 questions at random (seed 20261026), and for each one repetition at random with both its
v0 and its v1 conversation, shown side by side.

    /opt/miniconda3/bin/python -m backend.rdm.eval.reader_check      (an environment with python-docx)
        → docs/reader_check_2026-10-30.docx, backend/rdm/eval/pilot_runs/bank_v3_full/reader_check_sample_paired.csv

A judgment is one conversation (or one part of the Q10b → D2b → N1 conversation) that the reader scored: the
required statements it says are present or missing, and, where the question expects one, the direction of an
effect and the source of a number.
"""

import ast
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from backend.rdm.eval.failure_modes import _next_part, transcript
from backend.rdm.eval.questions import BANK_SPECS
D = Path(__file__).parent / "pilot_runs" / "bank_v3_full"     # (no harness import: runs where python-docx is)
OUT = Path(__file__).parents[3] / "docs" / "reader_check_2026-10-30.docx"
N_QUESTIONS, SEED = 10, 20261026
BOX = "☐ agree    ☐ disagree"
# A clickable Word checkbox (content control); "☐" in any text written by _runs becomes one.
CHECKBOX = ('<w:sdt xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"><w:sdtPr><w14:checkbox>'
            '<w14:checked w14:val="0"/><w14:checkedState w14:val="2612" w14:font="MS Gothic"/>'
            '<w14:uncheckedState w14:val="2610" w14:font="MS Gothic"/></w14:checkbox></w:sdtPr><w:sdtContent><w:r>'
            '<w:rPr><w:rFonts w:ascii="MS Gothic" w:eastAsia="MS Gothic" w:hAnsi="MS Gothic"/></w:rPr>'
            '<w:t>\u2610</w:t></w:r></w:sdtContent></w:sdt>')


def judgments() -> list:
    t = pd.read_csv(D / "failure_modes.csv")
    out = []
    for _, r in t.iterrows():
        for pre in ["", "N1:"]:
            note = r.get(f"{pre}reader_note")
            if not isinstance(note, str):
                continue
            spec = BANK_SPECS[r["question_id"]]
            part = None
            if pre:
                part = next(p for p in spec["parts"] if p["id"] == pre[:-1])
            s = part or spec
            if not (s.get("must_say") or s.get("expected_direction") or s.get("expected_source")):
                continue           # nothing for the reader to judge
            out.append({"file": r["file"], "question_id": pre[:-1] or r["question_id"], "arm": r["arm"],
                        "rep": int(r["rep"]), "part": pre[:-1] or None,
                        "wrong_direction": r.get(f"{pre}17_wrong_direction"),
                        "wrong_source": r.get(f"{pre}18_wrong_source"),
                        "missing": r.get(f"{pre}missing_statements"), "note": note,
                        "forecast": r.get(f"{pre}13_forecast_language"), "winner": r.get(f"{pre}14_names_a_winner")})
    return out


def answer_and_question(j: dict) -> tuple:
    """The question and what the reader read: the whole conversation (every answer, with the user's turns)."""
    run = json.loads((D / j["file"]).read_text())
    if not j["part"]:
        return run["question"], transcript(run)
    spec = BANK_SPECS[run["question_id"]]
    part = next(p for p in spec["parts"] if p["id"] == j["part"])
    return part.get("question", run["question"]), transcript(run, part["from_user_turn"], _next_part(spec, part))


def _font(doc):
    for name in ["Normal", "Heading 1", "Heading 2", "Heading 3", "List Bullet"]:
        st = doc.styles[name]
        st.font.name = "Times New Roman"
        f = st.element.get_or_add_rPr().get_or_add_rFonts()
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            f.set(qn(a), "Times New Roman")
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            f.attrib.pop(qn(a), None)
        if name.startswith("Heading"):
            st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    doc.styles["Normal"].font.size = Pt(11)


def _runs(par, text, size=None):
    for i, seg in enumerate(re.split(r"\*\*", text)):
        for k, piece in enumerate(seg.split("☐")):
            if k:
                par._p.append(parse_xml(CHECKBOX))
            if piece:
                r = par.add_run(piece)
                r.bold = i % 2 == 1
                if size:
                    r.font.size = Pt(size)


def _table(doc, rows, size=9.5):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows
             if not re.fullmatch(r"[\s|:\-]+", r)]
    if not cells:
        return
    t = doc.add_table(rows=len(cells), cols=max(len(r) for r in cells))
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement("w:" + e)
        x.set(qn("w:val"), "single"), x.set(qn("w:sz"), "4"), x.set(qn("w:color"), "999999")
        b.append(x)
    t._tbl.tblPr.append(b)
    for i, row in enumerate(cells):
        for k, c in enumerate(row):
            _runs(t.rows[i].cells[k].paragraphs[0], c, size)


def _markdown(doc, text):
    """The agent's answer: paragraphs, bullets, bold and tables."""
    lines, i = text.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            _table(doc, block)
            continue
        if ln.strip():
            m = re.match(r"\s*(?:[-*]|\d+\.)\s+(.*)", ln)
            h = re.match(r"#+\s+(.*)", ln)
            p = doc.add_paragraph(style="List Bullet") if m else doc.add_paragraph()
            _runs(p, (m or h).group(1) if (m or h) else ln.strip(), 10.5)
            if h:
                for r in p.runs:
                    r.bold = True
        i += 1


def build(sample: list):
    doc = Document()
    sec = doc.sections[0]
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, m, Cm(2.0))
    _font(doc)
    doc.add_heading("Reader check — full bank run (re-scored 2026-10-28)", level=1)
    for s in [
        "The reader is a small model (Claude Haiku 5.5) that reads each conversation (the user's turns and every "
        "answer of the agent, in order; since 2026-10-28, before only the final answer) and judges it against "
        "what the question expects. Its judgments feed checks 13 (forecast language), 14 (names a winner), 17 (wrong "
        "direction), 18 (wrong source) and 22 (a required statement missing). The 20 judgments are 10 questions drawn at "
        "random (seed 20261026) from the questions the reader judges, and for each one repetition drawn at random with "
        "both its v0 and its v1 conversation, one after the other.",
        "**What to do:** for each judgment, read the conversation and mark whether you agree with each verdict of "
        "the reader. At the end, mark whether you agree with the judgment as a whole. **Rule fixed in advance:** if "
        "you agree with fewer than 16 of the 20, the reader's checks are reported as unreliable, or re-scored after "
        "the reader is fixed.",
        "You judge the reader, not the agent: a verdict is right if it describes the answer correctly, whether or not "
        "the agent did well."]:
        _runs(doc.add_paragraph(), s)
    for n, j in enumerate(sample, 1):
        q, ans = answer_and_question(j)
        spec = BANK_SPECS[j["file"].split("_")[0]]
        s = next((p for p in spec.get("parts", []) if p["id"] == j["part"]), None) if j["part"] else spec
        doc.add_page_break()
        if j["arm"] == "v0":
            doc.add_heading(f"Question {(n + 1) // 2} of {len(sample) // 2} · {j['question_id']} · "
                            f"repetition {j['rep'] + 1}", level=1)
        doc.add_heading(f"{n} of {len(sample)} · {j['question_id']} · {j['arm']} · repetition {j['rep'] + 1}", level=2)
        _runs(doc.add_paragraph(), f"**Question:** {q}")
        doc.add_heading("The reader's verdicts", level=3)
        missing = set(ast.literal_eval(j["missing"])) if isinstance(j["missing"], str) else set()
        for st in s.get("must_say", []):
            v = "MISSING from the conversation" if st in missing else "present in the conversation"
            _runs(doc.add_paragraph(style="List Bullet"), f"Required: \"{st}\" → reader: **{v}**    {BOX}")
        if s.get("expected_direction"):
            v = {True: "goes the WRONG way", False: "goes the expected way"}.get(j["wrong_direction"], "not stated")
            _runs(doc.add_paragraph(style="List Bullet"),
                  f"Expected direction: {s['expected_direction']} → reader: the effect **{v}**    {BOX}")
        if s.get("expected_source"):
            v = {True: "attributed to a WRONG source", False: "attributed to the right source"}.get(
                j["wrong_source"], "no source stated")
            _runs(doc.add_paragraph(style="List Bullet"),
                  f"Expected source: {s['expected_source']} → reader: the number is **{v}**    {BOX}")
        for key, label, yes, no in (("forecast", "Forecast language (13)", "presents a result as a forecast",
                                     "no forecast"), ("winner", "Names a winner (14)", "names a winner", "no winner")):
            v = {True: yes, False: no, "True": yes, "False": no}.get(j.get(key), "not judged")
            _runs(doc.add_paragraph(style="List Bullet"), f"{label} → reader: **{v}**    {BOX}")
        _runs(doc.add_paragraph(), f"**Reader's note:** {j['note']}")
        _runs(doc.add_paragraph(), f"**Overall, I agree with this judgment:**    ☐ yes    ☐ no")
        _runs(doc.add_paragraph(), "**Comment:** ______________________________________________")
        doc.add_heading("The conversation the reader read", level=3)
        _markdown(doc, ans)
    doc.add_page_break()
    doc.add_heading("Summary", level=2)
    t = doc.add_table(rows=len(sample) + 1, cols=4)
    for k, h in enumerate(["#", "Judgment", "I agree overall", "Comment"]):
        t.rows[0].cells[k].text = h
    for n, j in enumerate(sample, 1):
        t.rows[n].cells[0].text = str(n)
        t.rows[n].cells[1].text = f"{j['question_id']} · {j['arm']} · rep {j['rep'] + 1}"
        _runs(t.rows[n].cells[2].paragraphs[0], "☐ yes   ☐ no")
    t.style = "Table Grid"
    _runs(doc.add_paragraph(), "**Agreed with ___ of 20** (16 or more: the reader's checks are reported as reliable).")
    doc.save(OUT)


if __name__ == "__main__":
    js = judgments()
    by = {(j["question_id"], j["arm"], j["rep"]): j for j in js}
    units = sorted({j["question_id"] for j in js})
    rng = np.random.default_rng(SEED)
    sample = []
    for q in rng.choice(units, size=N_QUESTIONS, replace=False):
        reps = sorted(r for (qq, a, r) in by if qq == q and a == "v0" and (q, "v1", r) in by)
        r = int(rng.choice(reps))
        sample += [by[(q, "v0", r)], by[(q, "v1", r)]]
    pd.DataFrame(sample).to_csv(D / "reader_check_sample_paired.csv", index=False)
    build(sample)
    print(f"{len(js)} judgments; {N_QUESTIONS} questions × v0/v1 drawn → {OUT}")
