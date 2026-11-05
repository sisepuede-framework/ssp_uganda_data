"""One-row-per-slide table of what changed from the 1104 deck to _v2.

    python deck_1104_v2_changes.py docs/deck_1104_v2_changes.docx
"""
import os
import sys

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches, Pt

OUT = sys.argv[1]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")

ROWS = [
    ("3", "3", "Direct interaction between users and models now requires no technical expertise", "Using a model now requires no technical expertise. 3 short bullets.", "James: screenshot or gif plus a few bullets on why"),
    ("4", "4", "Long title, no content", "A lot of potential, but significant risks / Is the tool engaging as expected? Used as a quick transition.", "You: unsure how to use this phrase"),
    ("5", "5", "4 fact cards", "SISEPUEDE → 100,000 runs → XGBoost. The details moved to notes.", "James: surrogate only quickly. You: slides 5 and 6 must be clear"),
    ("6", "new", "(none)", "Every lever speaks its own units, so we use one scale.", "You: why translate raw ranges to 0–1, in simple words"),
    ("7", "new", "(none)", "Latin hypercube tests every part of every dial. Picture is a schematic.", "You: explain LHS in simple words"),
    ("8", "6", "The surrogate translates LHC trials… (Yada yada)", "To answer a real question, we translate back: three levers at dial 0, 0.5 and 1.", "James: translation between specifications, samples and final values"),
    ("9", "new", "(none)", "The same dial move means a different real change: +24, +22, +11 points. Implications for the AI agent. “Half” is not used here.", "You: translation matters for magnitudes; do not give away “half”"),
    ("10", "8", "Long question at a smaller size", "How can AI make computational experiments interactive? Your boxes and clicks unchanged.", "James: his title, shortened"),
    ("11", "9", "No title; RQ2 label misaligned", "Title added, RQ wording unchanged, key phrases in bold.", "Consistency"),
    ("13", "11", "Pipeline", "Your layout and clicks unchanged; shorter harness text. Your story moved to notes.", "You: the flow on slide 11 is the right one"),
    ("14", "12", "Six rules", "Adds: No script of steps: the agent chooses the tools and their order.", "You: check if the slide communicates this"),
    ("15", "13", "4 columns of detail", "Each tool has one job: tool, question, what it does. Read tools, then Run tools. Full table stays in the appendix.", "You: keep it, much simpler"),
    ("16", "new", "(none)", "The tools alone didn't let the agent understand the system.", "You: the real process"),
    ("17", "new", "(none)", "What data, and how? Not too little, not all of it.", "You: how and what data, without giving it all"),
    ("18", "14", "4 numbered points, 93.9%", "The AI built Map from the model's code: the five levels, with the two ends matching the XGBoost. 93.9% moved to notes.", "James: remove 3 and 4, expand. You: what the network includes"),
    ("19", "15", "Same 4 points", "Map+ adds the density of each variable from the runs: a summary, not the whole dataset.", "James: what is Map+? Clear, concise. You: densities"),
    ("20", "16", "Long title; section said Experiment", "Same walk and clicks. Codes removed. Closes on “one node at a time”.", "James: this shows the path from the previous slides"),
    ("22", "18", "Duplicate of the walk", "Only one thing changes: kept the same vs what changes.", "You: everything constant except the network version"),
    ("23", "19", "6 cards, name and quote", "Each card adds its purpose. Parts appear by row.", "You: each type has a specific purpose"),
    ("24", "20", "No title or footer; generic checks", "Four criteria, each with its own objective, then what we check.", "James: clearer criteria. You: add the objective of each evaluation"),
    ("25", "21", "Boxes out of line, small title", "Each conversation is scored against a human answer key: aligned flow.", "You: predetermined answers vs observed"),
    ("27", "23", "Two-line title; WW1 and P50i", "With no values, the agent can only guess what words mean. Codes removed; walks through on clicks.", "James: walk through the elements. You: no codes"),
    ("28", "24", "Static", "Same content, rows on click, criterion in the label.", "Consistency"),
    ("29", "25", "Half of a two-part slide", "With values, the agent also calculates for itself.", "James: colors. You: more slides, less content"),
    ("30", "25", "Other half; right side unclear", "With values, the agent can stop before the answer. Clearer labels, matching colors.", "You: the right part is not clear"),
    ("31", "26", "4 columns, jargon", "Objective first, then user asked → agent ran → it found, one row per click.", "You: needs better explanation; connect to the evaluation"),
    ("32", "26", "Bottom strip", "Across all 290 conversations, the process held. Labeled Tool use.", "You: is this connected to the evaluations?"),
    ("33", "27", "Design what the agent sees, and test it", "What data the agent gets, and how, shapes how it behaves. Point 2 no longer cites the removed slide. “Scope of these results”.", "James: clearer title, scientific; clearer subheaders"),
    ("(gone)", "7", "Duplicate of 8 + 9", "Removed.", "You split it into 8 and 9"),
]

d = Document()
sec = d.sections[0]
sec.orientation = WD_ORIENT.LANDSCAPE
sec.page_width, sec.page_height = sec.page_height, sec.page_width
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Inches(0.6))
d.styles["Normal"].font.name = "Arial"
d.styles["Normal"].font.size = Pt(9.5)
d.add_heading("DMDU talk: what changed from 1104 to _v2", 1)
d.add_paragraph("Talk slides only. The appendix is unchanged. Slide numbers: _v2 and 1104. Your comments are still in the file.")
widths = (0.5, 0.5, 2.6, 3.9, 2.3)
t = d.add_table(rows=1, cols=5)
t.style = "Table Grid"
for c, name in zip(t.rows[0].cells, ("_v2", "1104", "Before", "After", "Which comment it answers")):
    c.text = ""
    c.paragraphs[0].add_run(name).bold = True
for row in ROWS:
    for c, v in zip(t.add_row().cells, row):
        c.text = v
for r in t.rows:
    for c, w in zip(r.cells, widths):
        c.width = Inches(w)
d.save(OUT)
print("saved", OUT, len(ROWS))
