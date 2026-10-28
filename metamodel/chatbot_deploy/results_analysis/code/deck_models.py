"""Add the model settings to the DMDU deck (copy): slides 8 and 15, plus an appendix slide after slide 36."""
import copy
import sys
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
p = Presentation(SRC)
INK, BLUE, GREY, BOX = RGBColor(0x16, 0x18, 0x1D), RGBColor(0x1F, 0x4E, 0x9C), RGBColor(0x5B, 0x60, 0x6B), RGBColor(0xF4, 0xF5, 0xF7)


def shape(slide, sid):
    return next(s for s in slide.shapes if s.shape_id == sid)


def set_text(sh, text):
    """Replace the text of the first run, keep its format, drop the other runs."""
    para = sh.text_frame.paragraphs[0]
    para.runs[0].text = text
    for r in para.runs[1:]:
        r._r.getparent().remove(r._r)


def text(slide, x, y, w, h, s, size, font="IBM Plex Sans", color=INK, bold=False):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(s if isinstance(s, list) else [s]):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = para.add_run()
        r.text = line
        r.font.size, r.font.name, r.font.color.rgb, r.font.bold = Pt(size), font, color, bold
        if i:
            para.space_before = Pt(8)
    return tb


# slide 8: the agent model, and the thinking summary in the log
s8 = p.slides[7]
set_text(shape(s8, 9), "Agent")
set_text(shape(s8, 10), "Claude Sonnet 5.5 · chooses the tools and their arguments")
set_text(shape(s8, 26), "Tool calls, arguments, replies, the agent's thinking summary and the final answer, every turn")

# slide 15: what a log holds, who the reader is, and a models box in the free space right of "290"
s15 = p.slides[14]
set_text(shape(s15, 14), "logs: calls, arguments, replies, thinking summary, answer")
set_text(shape(s15, 20), "numbers no tool gave · no numeric range where futures were run")
set_text(shape(s15, 26), "forecast language · names a winner · direction, source, required statements · Claude "
         "Haiku 5.5 reads the whole conversation")
box = s15.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(12.4), Inches(2.66), Inches(6.46), Inches(2.0))
box.fill.solid()
box.fill.fore_color.rgb = BOX
box.line.fill.background()
text(s15, 12.7, 2.86, 6.0, 0.36, "MODELS · SAME IN EVERY ARM", 18, "IBM Plex Mono", BLUE)
text(s15, 12.7, 3.36, 6.0, 1.2, [
    "Agent: Claude Sonnet 5.5 · effort medium · thinking kept as a summary in each log · ≤ 20 requests",
    "Reader: Claude Haiku 5.5 · effort low · checks 13, 14, 17, 18, 22",
], 16.5, color=INK)

def appendix_slide(label, title, position):
    """A white appendix slide with the section label and footer of slide 36, moved to `position` (0-based)."""
    ref = p.slides[35]
    new = p.slides.add_slide(ref.slide_layout)
    for ph in list(new.placeholders):
        ph._element.getparent().remove(ph._element)
    new.background.fill.solid()
    new.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for sid in (2, 4, 5):
        new.shapes._spTree.append(copy.deepcopy(shape(ref, sid)._element))
    set_text(new.shapes[0], label)
    text(new, 1.15, 1.39, 18.33, 0.73, title, 36, bold=True)
    ids = p.slides._sldIdLst
    el = ids[-1]
    ids.remove(el)
    ids.insert(position, el)
    return new


def table(slide, rows, x, y, w, h, widths, size=17, header_col=True):
    tbl = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h)).table
    for j, cw in enumerate(widths):
        tbl.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = tbl.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = BOX if i == 0 or (header_col and j == 0) else RGBColor(0xFF, 0xFF, 0xFF)
            tf = c.text_frame
            for k, line in enumerate(str(v).split("\n")):
                para = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
                r = para.add_run()
                r.text = line
                r.font.name, r.font.color.rgb = "IBM Plex Sans", BLUE if i == 0 else (GREY if k else INK)
                r.font.size = Pt(size if k == 0 else size - 3)
                r.font.bold = k == 0 and (i == 0 or (header_col and j == 0))
    return tbl


# appendix slide: the two models, after slide 36 (the loop and the scripted user)
new = appendix_slide("APPENDIX · THE MODELS", "The two models: the agent answers, the reader scores", 36)
table(new, [
    ("", "Agent", "Reader"),
    ("Model", "Claude Sonnet 5.5 (claude-sonnet-5-5)", "Claude Haiku 5.5 (claude-haiku-5-5)"),
    ("Effort", "medium", "low"),
    ("Thinking", "adaptive; kept as a summary in each log (same cost); never scored", "not kept"),
    ("Limits", "16,000 output tokens per request · 20 requests per conversation", "4,000 tokens · one call per answer"),
    ("Tools", "the 6 tools", "none"),
    ("Sees", "system prompt, tool descriptions, user messages, tool replies",
     "the question, the whole conversation (every answer), and what the question expects"),
    ("Does", "chooses tools and arguments; answers the user",
     "checks 13 forecast · 14 winner · 17 wrong direction · 18 wrong source · 22 required statement missing"),
    ("Checked", "20 checks are code rules on its log", "20 judgments checked by hand (pending)"),
], 1.15, 2.6, 17.7, 6.6, [2.6, 7.55, 7.55])
text(new, 1.15, 9.81, 17.79, 0.36, "From backend/rdm/harness/agent.py and backend/rdm/eval/failure_modes.py. Not part of the talk.",
     15, color=GREY)

# appendix slide: what the v1 values look like, after slide 30 (the treatment). Numbers from
# backend/rdm/network/out/run_2026_05_30_ranges.parquet (lever 35, 2050, emissions_transportation), checked 2026-10-28.
new = appendix_slide("APPENDIX · THE TOOLS", "What v1 values look like: lever thirds, and optionally an uncertainty third", 30)
text(new, 1.15, 2.45, 17.7, 0.5, "Transport emissions in 2050 (Mt CO₂e) for lever 35, light-duty vehicles to electricity · "
     "median, and p10–p90 below · 4,989 sampled runs; every other lever and uncertainty varies", 17, color=GREY)
text(new, 1.15, 3.2, 6.6, 0.4, "WHAT THE AGENT GOT · DEFAULT", 16, "IBM Plex Mono", BLUE)
text(new, 1.15, 3.65, 6.6, 0.4, 'model_network(node="L35", year=2050)  · as in HA1, v1', 14, "IBM Plex Mono", INK)
table(new, [
    ("L35 third", "Median", "p10 – p90"),
    ("low (0–⅓)", "9.89", "7.59 – 12.99"),
    ("mid (⅓–⅔)", "9.45", "7.20 – 12.57"),
    ("high (⅔–1)", "9.10", "6.93 – 11.99"),
], 1.15, 4.25, 6.6, 2.6, [2.2, 1.8, 2.6])
text(new, 1.15, 7.15, 6.6, 1.9, ["One row per lever third: all GDP futures mixed.",
     "In the full run (v1) the agent always looked at these; it never used the uncertainty filter successfully."],
     15.5, color=INK)
text(new, 8.6, 3.2, 10.3, 0.4, "WITH THE GDP FILTER · ONE CALL PER GDP THIRD", 16, "IBM Plex Mono", BLUE)
text(new, 8.6, 3.65, 10.3, 0.4, '… uncertainty=57, third="low" | "mid" | "high"', 14, "IBM Plex Mono", INK)
table(new, [
    ("GDP (X57) ↓ · L35 →", "low", "mid", "high"),
    ("GDP low", "8.51\n6.89 – 10.64", "8.23\n6.48 – 10.37", "7.83\n6.17 – 9.89"),
    ("GDP mid", "10.01\n7.97 – 12.43", "9.45\n7.59 – 11.92", "9.11\n7.32 – 11.65"),
    ("GDP high", "11.49\n9.12 – 14.41", "11.09\n8.73 – 13.74", "10.44\n8.35 – 12.96"),
], 8.6, 4.25, 10.3, 3.6, [3.1, 2.4, 2.4, 2.4])
text(new, 8.6, 8.1, 10.3, 1.2, ["Down a column (GDP up): about +3 Mt. Across a row (lever up): less than −1 Mt.",
     "Only uncertainties with a path to the node can filter it (here X57, X60, X66, X67). 532–593 runs per cell."],
     15.5, color=INK)
text(new, 1.15, 9.81, 17.79, 0.36, "From backend/rdm/tools/network.py and network/out/run_2026_05_30_ranges.parquet. Not part of the talk.",
     15, color=GREY)

# findings slide: with values the agent stops walking early (results_analysis/walk_depth.xlsx), after slide 19
ref = p.slides[18]
new = p.slides.add_slide(ref.slide_layout)
for ph in list(new.placeholders):
    ph._element.getparent().remove(ph._element)
new.background.fill.solid()
new.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
for sid in (2, 4, 5):
    new.shapes._spTree.append(copy.deepcopy(shape(ref, sid)._element))
text(new, 1.15, 1.39, 18.33, 0.73, "With values at the first step, the agent often stopped before the answer", 40, bold=True)
text(new, 1.15, 2.5, 17.7, 0.5, "Questions whose answer is an in-between quantity, two or three steps from the lever on the "
     "network · 5 repetitions per arm", 18, color=GREY)
table(new, [
    ("Question asks for", "v0 reached the node", "v1 reached the node", "v1 gave the run value"),
    ("S35 · electric vehicle-km", "5 / 5", "5 / 5", "5 / 5"),
    ("HD1 · transport electricity (PJ)", "5 / 5", "2 / 5", "2 / 5"),
    ("S50 · landfill gas recovered (t)", "5 / 5", "0 / 5", "0 / 5"),
    ("S3 · cropland under better practice (ha)", "1 / 5", "0 / 5", "0 / 5"),
], 1.15, 3.2, 10.2, 3.5, [4.5, 1.9, 1.9, 1.9], size=16)
text(new, 1.15, 6.95, 10.2, 0.9, ["v0 walks to the node but sees no values, so it cannot answer.",
     "v1 sees values from the first step; when it walked on, it answered."], 15.5, color=INK)
box = new.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(11.9), Inches(3.2), Inches(7.0), Inches(4.6))
box.fill.solid()
box.fill.fore_color.rgb = BOX
box.line.fill.background()
text(new, 12.2, 3.4, 6.4, 0.4, "HD1 · V1 · STOPPED AFTER THE FUEL SHARE", 15, "IBM Plex Mono", BLUE)
text(new, 12.2, 3.9, 6.4, 1.5, ["Its reasoning: “This is a share of fuel mix, not an absolute energy demand figure, so I "
     "can't directly translate it.”", "To the user: “The tools don't report transport electricity demand.”"], 16, color=INK)
text(new, 12.2, 5.65, 6.4, 0.5, "model_network had it, two steps on: 56.0 → 59.9 PJ.", 16, color=BLUE)
text(new, 12.2, 6.3, 6.4, 1.3, "S3 · v1 stopped at the lever and computed 3.7 M ha itself from the baseline crop areas "
     "(the runs give 2.2–3.1 M ha).", 15, color=GREY)
box = new.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.15), Inches(8.3), Inches(17.75), Inches(1.25))
box.fill.solid()
box.fill.fore_color.rgb = BOX
box.line.fill.background()
text(new, 1.45, 8.5, 17.2, 0.9, "v1, all four questions: reached the node 7 times, gave the run value 7 of 7; stopped "
     "early 13 times, 0 of 13. Values answer the first question so well that the agent stops looking.", 18, color=INK)
ids = p.slides._sldIdLst
el = ids[-1]
ids.remove(el)
ids.insert(19, el)          # right after slide 19 (own arithmetic)

# conclusion, point 1: walking less is not always good
set_text(shape(p.slides[24], 9), "With the model’s values the agent turns words into the right setting (79% → 1% off "
         "the key) and searches less, sometimes too little: it stopped before the answer in 13 of 20.")

p.save(OUT)
print(OUT, len(p.slides), "slides")
