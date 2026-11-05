"""Clean the 1104 talk deck: new narrative, one idea per slide, parts appearing on click.

    python deck_1104_v2.py docs/DMDU_2026_Talk_draft_models_1104_video.pptx \
                           docs/DMDU_2026_Talk_draft_models_1104_video_v2.pptx

The source deck has Alexa's hand edits and is never overwritten. Slides that already exist stay the same slide
part, so comments and speaker notes stay attached. Lever numbers come from
backend/rdm/data/tables/run_2026_05_30_lever_inputs.csv (year 2050).
"""
import copy
import os
import random
import re
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")

INK, BLUE, GREY, MUTE = "16181D", "1F4E9C", "5B606B", "6B707B"
LINE, PALE, TINT, MAP = "E3E5E9", "F4F5F7", "E8EEF8", "A3A9B4"
SANS, MONO = "IBM Plex Sans", "IBM Plex Mono"
FOOTER = "DMDU Society Annual Meeting 2026"
SECTIONS = {"Context", "Method", "Experiment", "Findings"}

p = Presentation(SRC)
orig = {i: s for i, s in enumerate(p.slides, 1)}
assert len(orig) == 50, "the source deck changed: check the slide numbers in this script"


# ---------------------------------------------------------------- helpers
def rgb(hex_):
    return RGBColor.from_string(hex_)


def text(s, x, y, w, h, content, size=24, bold=False, color=INK, font=SANS, align=None, anchor=None, italic=False):
    """Text box with no padding. content: a string, or a list of paragraphs, each a string or a list of
    (text, {bold, color, font, size}) runs."""
    b = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if anchor:
        tf.vertical_anchor = anchor
    paras = content if isinstance(content, list) else [content]
    for k, para in enumerate(paras):
        pg = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        if align:
            pg.alignment = align
        if k:
            pg.space_before = Pt(6)
        for run_text, o in ([(para, {})] if isinstance(para, str) else para):
            r = pg.add_run()
            r.text = run_text
            r.font.name = o.get("font", font)
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.italic = italic
            r.font.color.rgb = rgb(o.get("color", color))
    return b


def rect(s, x, y, w, h, fill=None, line=None, dash=False, weight=1.25):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    r.shadow.inherit = False
    if fill:
        r.fill.solid()
        r.fill.fore_color.rgb = rgb(fill)
    else:
        r.fill.background()
    if line:
        r.line.color.rgb = rgb(line)
        r.line.width = Pt(weight)
        if dash:
            from pptx.enum.dml import MSO_LINE
            r.line.dash_style = MSO_LINE.DASH
    else:
        r.line.fill.background()
    return r


def box(s, x, y, w, h, head, body, fill=None, line=INK, head_size=30, body_size=26, dash=False):
    """A box and its two lines of text: returns the shapes so they can appear together."""
    dark = fill == BLUE
    r = rect(s, x, y, w, h, fill=fill, line=None if fill else line, dash=dash)
    a = text(s, x + 0.3, y + 0.3, w - 0.6, 0.6, head, head_size, True, "FFFFFF" if dark else INK)
    b = text(s, x + 0.3, y + 1.0, w - 0.6, h - 1.2, body, body_size, False, "FFFFFF" if dark else GREY)
    return [r, a, b]


def set_text(shape, new, size=None):
    """Replace a shape's text, keeping the format of its first run."""
    tf = shape.text_frame
    paras = tf.paragraphs
    for extra in paras[1:]:
        extra._p.getparent().remove(extra._p)
    runs = paras[0].runs
    for extra in runs[1:]:
        extra._r.getparent().remove(extra._r)
    runs[0].text = new
    if size:
        runs[0].font.size = Pt(size)


def no_autofit(shape):
    """Some titles were shrunk by PowerPoint's autofit: a shrunken title is smaller than the others."""
    body = shape.text_frame._txBody.find("{http://schemas.openxmlformats.org/drawingml/2006/main}bodyPr")
    for child in list(body):
        if child.tag.endswith("Autofit"):
            body.remove(child)
    for pg in shape.text_frame.paragraphs:
        for sp in pg._p.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}lnSpc"):
            sp.getparent().remove(sp)


def find(s, start):
    hits = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip().startswith(start)]
    assert hits, f"no shape starting with {start!r}"
    return hits[0]


def by_id(s, i):
    hits = [x for x in s.shapes if x.shape_id == i]
    assert hits, f"no shape id {i}"
    return hits[0]


def clear(s, keep=()):
    for x in list(s.shapes):
        if x.shape_id not in keep:
            x._element.getparent().remove(x._element)
    drop_timing(s)


def drop_timing(s):
    for t in s._element.findall("{http://schemas.openxmlformats.org/presentationml/2006/main}timing"):
        s._element.remove(t)


def frame(s, kicker, title, section):
    """Label, title and footers, at the same place on every slide. Reuses what is there, adds what is not."""
    labels = [x for x in s.shapes if x.has_text_frame and abs(x.top - Inches(0.92)) < Inches(0.05)]
    if labels:
        set_text(labels[0], kicker)
    else:
        labels = [text(s, 1.15, 0.92, 18.3, 0.36, kicker, 18, color=BLUE, font=MONO)]
    titles = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip()
              and x.top < Inches(1.6) and x.top > Inches(0.5) and x not in labels]
    if titles:
        t = titles[0]
        set_text(t, title, 45)
        t.left, t.top, t.width, t.height = Inches(1.15), Inches(1.39), Inches(18.33), Inches(0.73)
        no_autofit(t)
    else:
        text(s, 1.15, 1.39, 18.33, 0.73, title, 45, True)
    foot = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() == FOOTER]
    if not foot:
        text(s, 1.15, 10.26, 4.46, 0.36, FOOTER, 18, color=MUTE)
    right = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() in SECTIONS]
    if right:
        set_text(right[0], section)
    else:
        text(s, 15.0, 10.26, 3.94, 0.36, section, 18, color=MUTE, align=PP_ALIGN.RIGHT)


def new_slide():
    s = p.slides.add_slide(p.slide_layouts[0])
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    return s


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def animate(s, clicks):
    """Parts appear on click, with the same 'appear' effect used on Alexa's slides. clicks: list of lists of shapes."""
    drop_timing(s)
    n = [2]

    def nid():
        n[0] += 1
        return n[0]

    body = []
    used = []
    for group in clicks:
        flat = [x for x in group]
        assert flat
        outer, inner = nid(), nid()
        effects = []
        for k, sh in enumerate(flat):
            used.append(sh.shape_id)
            kind = "clickEffect" if k == 0 else "withEffect"
            effects.append(
                f'<p:par><p:cTn id="{nid()}" presetID="1" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" '
                f'nodeType="{kind}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst><p:set><p:cBhvr>'
                f'<p:cTn id="{nid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'<p:tgtEl><p:spTgt spid="{sh.shape_id}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility'
                f'</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set></p:childTnLst>'
                f'</p:cTn></p:par>')
        body.append(
            f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
            f'<p:childTnLst><p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
            f'<p:childTnLst>{"".join(effects)}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
    assert len(used) == len(set(used)), "a shape appears twice in one animation"
    bld = "".join(f'<p:bldP spid="{i}" grpId="0" animBg="1"/>' for i in used)
    xml = (f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" '
           f'nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" '
           f'nodeType="mainSeq"><p:childTnLst>{"".join(body)}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" '
           f'delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" '
           f'delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par>'
           f'</p:tnLst><p:bldLst>{bld}</p:bldLst></p:timing>')
    el = etree.fromstring(xml)
    ext = s._element.find(f"{{{P_NS}}}extLst")
    if ext is not None:
        ext.addprevious(el)
    else:
        s._element.append(el)


def clicks_of(s):
    """Read the click groups of a slide's existing animation, as lists of shapes."""
    t = s._element.find(f"{{{P_NS}}}timing")
    groups = []
    for c in t.iter(f"{{{P_NS}}}cTn"):
        kind = c.get("nodeType")
        if kind in ("clickEffect", "withEffect", "afterEffect"):
            tgt = c.find(f".//{{{P_NS}}}spTgt")
            sh = by_id(s, int(tgt.get("spid")))
            if kind == "clickEffect":
                groups.append([sh])
            else:
                groups[-1].append(sh)
    return groups


def notes(s, body):
    ns = s.notes_slide
    if ns.notes_text_frame is None:  # this deck's notes master has no body placeholder to clone
        ns.shapes._spTree.append(etree.fromstring(
            f'<p:sp xmlns:p="{P_NS}" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:nvSpPr>'
            f'<p:cNvPr id="{max([x.shape_id for x in ns.shapes] + [1]) + 1}" name="Notes"/><p:cNvSpPr>'
            f'<a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>'))
    ns.notes_text_frame.text = body


def row_line(s, x, y, w, color=LINE):
    return rect(s, x, y, w, 0.02, fill=color)


# ---------------------------------------------------------------- Context
# 3. The video
s = orig[3]
frame(s, "CONTEXT · THE TOOL", "Using a model now requires no technical expertise", "Context")
col = find(s, "This tool allows")
ps = col.text_frame.paragraphs
for pg, new in zip(ps[:3], ("Ask for scenarios beyond the official NDC pathways",
                            "Talk to the model directly, with no analyst in between",
                            "Fast answers with emissions, costs and benefits")):
    for extra in pg.runs[1:]:
        extra._r.getparent().remove(extra._r)
    pg.runs[0].text = new
for extra in ps[3:]:
    extra._p.getparent().remove(extra._p)
notes(s, "This is an earlier version of what we built. It works, it looks great, and it would be easy to put it in front "
         "of a decision maker. Before doing that, we took a step back to understand how the components we were putting "
         "together actually behave.\n\n"
         "[Video: real answer from the earlier app and agent; waiting time cut. Do not quote its numbers as results.]")

# 4. Alexa's phrase, as a transition
s = orig[4]
clear(s, keep=[x.shape_id for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() in SECTIONS | {FOOTER}])
text(s, 1.15, 0.92, 18.3, 0.36, "CONTEXT · THE TOOL", 18, color=BLUE, font=MONO)
text(s, 1.15, 3.7, 17.7, 1.2, "A lot of potential, but significant risks", 63, True)
q = text(s, 1.15, 5.3, 17.7, 0.9, "Is the tool engaging as expected?", 42, color=BLUE)
animate(s, [[q]])
notes(s, "Transition, a few seconds. There is a lot of potential, but there are significant risks. "
         "We want to understand that a tool is engaging as expected.")

# 5. Surrogate
s = orig[5]
clear(s, keep=[x.shape_id for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() in SECTIONS | {FOOTER}]
     + [2, 3, 37, 38])
frame(s, "CONTEXT · THE SURROGATE", "First, a surrogate model makes policy exploration fast", "Context")
y, h, w = 3.3, 3.2, 4.9
b1 = box(s, 1.15, y, w, h, "SISEPUEDE", "The full model: about 3 minutes per run")
a1 = text(s, 6.2, y, 0.8, h, "→", 40, color=MUTE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
b2 = box(s, 7.15, y, w, h, "100,000 runs", "Many policies and many futures, run in advance")
a2 = text(s, 12.2, y, 0.8, h, "→", 40, color=MUTE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
b3 = box(s, 13.15, y, 5.7, h, "XGBoost surrogate", "Learns from the runs, so we get answers without running the model each time", fill=BLUE)
by_id(s, 37).top, by_id(s, 38).top = Inches(7.3), Inches(7.5)
animate(s, [b1, [a1] + b2, [a2] + b3, [by_id(s, 37), by_id(s, 38)]])
notes(s, "James: we are not focused on the surrogate in this talk beyond the context it provides for the AI agent. "
         "Keep it quick.\n\n"
         "Details for Q&A: Latin hypercube over 54 levers and 13 uncertainties. 67 inputs, 258 outputs (emissions, "
         "benefits, costs and GDP), 6 years 2025-2070. One gradient-boosted tree model per output, default "
         "hyperparameters. 79,670 runs to train, 19,918 held out to test. R² 0.993 emissions, 0.996 benefits, 0.990 "
         "costs, 1.000 GDP; SMAPE 1.6%; 15 outputs with R² < 0.8.")

# B. One scale
sB = new_slide()
frame(sB, "CONTEXT · THE SURROGATE", "Every lever speaks its own units, so we use one scale", "Context")
rows = (("Landfill gas recovered", "7%", "55%"),
        ("Cereal yield", "4.4 t/ha", "6.1 t/ha"),
        ("Powered-bike efficiency", "50 km/kWh", "63 km/kWh"))
parts, ends = [], []
x0, x1 = 9.2, 15.9
for k, (name, lo, hi) in enumerate(rows):
    yy = 3.6 + k * 1.25
    parts += [text(sB, 1.15, yy, 5.6, 0.6, name, 28, True),
              text(sB, 6.9, yy, 2.1, 0.6, lo, 26, color=GREY, align=PP_ALIGN.RIGHT),
              rect(sB, x0, yy + 0.24, x1 - x0, 0.05, fill=MAP),
              text(sB, 16.1, yy, 2.8, 0.6, hi, 26, color=GREY)]
    ends += [rect(sB, x0 - 0.11, yy + 0.155, 0.22, 0.22, fill=BLUE), rect(sB, x1 - 0.11, yy + 0.155, 0.22, 0.22, fill=BLUE)]
head = [text(sB, x0 - 1.0, 2.75, 2.0, 0.5, "0 = BAU", 26, True, BLUE, align=PP_ALIGN.CENTER),
        text(sB, x1 - 1.6, 2.75, 3.6, 0.5, "1 = range maximum", 26, True, BLUE, align=PP_ALIGN.CENTER)]
line = text(sB, 1.15, 7.65, 17.7, 0.7, "One lever can move up to 186 inputs at once. One dial lets us treat every lever the same way.", 28)
animate(sB, [parts, head + ends, [line]])
notes(sB, "Each lever changes real things in the model, and each one has its own units and its own range: percentages, "
          "tonnes per hectare, kilometres per kilowatt-hour. Some levers change many inputs at once. To explore all of "
          "them the same way, we put each lever on one common scale, a dial from 0 to 1. 0 is business as usual and 1 "
          "is the most ambitious level explored in the experiment.\n\n"
          "Values for 2050. Levers 50, 4 and 32; lever 11 moves 186 inputs (run_2026_05_30_lever_inputs.csv).")

# C. Latin hypercube
sC = new_slide()
frame(sC, "CONTEXT · THE SURROGATE", "Latin hypercube tests every part of every dial", "Context")
n, gx, gy, cell = 8, 1.55, 2.85, 0.75
grid = []
for i in range(n + 1):
    grid.append(rect(sC, gx + i * cell, gy, 0.02, n * cell, fill=MAP))
    grid.append(rect(sC, gx, gy + i * cell, n * cell, 0.02, fill=MAP))
grid.append(text(sC, gx, gy + n * cell + 0.1, n * cell, 0.45, "Dial A, cut into equal slices", 22, color=GREY, align=PP_ALIGN.CENTER))
grid.append(text(sC, 1.15, gy - 0.5, 6.4, 0.45, "Dial B", 22, color=GREY))
order = list(range(n))
random.Random(7).shuffle(order)
dots = [rect(sC, gx + i * cell + cell / 2 - 0.14, gy + order[i] * cell + cell / 2 - 0.14, 0.28, 0.28, fill=BLUE) for i in range(n)]
for d in dots:
    d._element.spPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom").set("prst", "ellipse")
t1 = text(sC, 9.2, 3.0, 9.6, 1.1, [[("Cut each dial ", {"bold": True}), ("into equal slices", {})]], 32)
t2 = text(sC, 9.2, 4.3, 9.6, 1.1, [[("Try every slice ", {"bold": True}), ("of every dial, so no part of a range is left out", {})]], 32)
t3 = text(sC, 9.2, 5.9, 9.6, 1.1, [[("Mix the dials ", {"bold": True}), ("at random, so each run is a new combination", {})]], 32)
t4 = text(sC, 9.2, 7.6, 9.6, 1.0, "54 levers + 13 uncertainties, about 100,000 runs", 28, True, BLUE)
animate(sC, [grid + [t1], dots + [t2], [t3], [t4]])
notes(sC, "Why this matters: with this design we have seen every part of every lever's range, in many combinations, "
          "without trying every possible combination. That is what the surrogate learns from.\n\n"
          "Picture: schematic for two dials and 8 slices, not the real design.")

# 6. Translate back
s = orig[6]
clear(s, keep=[x.shape_id for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() in SECTIONS | {FOOTER}] + [2, 3])
frame(s, "CONTEXT · THE SURROGATE", "To answer a real question, we translate back", "Context")
x0, xm, x1 = 8.6, 12.65, 16.7
top = [text(s, 1.15, 2.95, 6.5, 0.5, "The dial at…", 26, True, BLUE),
       text(s, x0 - 1.3, 2.95, 2.6, 0.5, "0", 28, True, BLUE, align=PP_ALIGN.CENTER),
       text(s, xm - 1.3, 2.95, 2.6, 0.5, "0.5", 28, True, BLUE, align=PP_ALIGN.CENTER),
       text(s, x1 - 1.3, 2.95, 2.6, 0.5, "1", 28, True, BLUE, align=PP_ALIGN.CENTER)]
groups = [top]
for k, (name, a, b, c) in enumerate((("Landfill gas recovered", "7%", "31%", "55%"),
                                     ("Rural wastewater in septic tanks", "18%", "40%", "63%"),
                                     ("Electric share of cars and vans", "50%", "61%", "72%"))):
    yy = 3.85 + k * 1.45
    g = [text(s, 1.15, yy, 6.3, 1.0, name, 27, True),
         rect(s, x0, yy + 0.27, x1 - x0, 0.05, fill=MAP)]
    for xx, v in ((x0, a), (xm, b), (x1, c)):
        chip = rect(s, xx - 0.75, yy, 1.5, 0.62, fill=TINT)
        g += [chip, text(s, xx - 0.75, yy, 1.5, 0.62, v, 28, True, BLUE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)]
    groups.append(g)
close = text(s, 1.15, 8.45, 17.7, 0.7, "Between the two ends, the real value follows a straight line.", 28)
groups.append([close])
animate(s, groups)
notes(s, "The surrogate only understands the dial, but people ask in real terms. So we also have to go the other way, from "
         "the dial back to the real value. Each lever has its own line, read from the runs.\n\n"
         "Values for 2050: BAU, middle and top of the range run. Levers 50, 46 and 35 (lever_inputs table: input = value at 0 "
         "+ L x (value at 1 - value at 0)).\n\n"
         "James's comment here: the translation between strategic specifications, lever uncertainty samples and the final value "
         "might inform some of the issues we run into.")

# E. Why it matters
sE = new_slide()
frame(sE, "CONTEXT · THE SURROGATE", "The same dial move means a different real change", "Context")
text(sE, 1.15, 2.85, 17.7, 0.5, "Moving the dial from 0 to 0.5 adds…", 28, color=GREY)
groups = []
scale = 7.2 / 24
for k, (name, pts) in enumerate((("Landfill gas recovered", 24), ("Rural wastewater in septic tanks", 22), ("Electric share of cars and vans", 11))):
    yy = 3.65 + k * 1.0
    groups.append([text(sE, 1.15, yy, 6.9, 0.6, name, 27, True),
                   rect(sE, 8.2, yy + 0.08, pts * scale, 0.42, fill=BLUE),
                   text(sE, 8.2 + pts * scale + 0.25, yy, 3.0, 0.6, f"+{pts} points", 27, True, BLUE)])
msg = text(sE, 1.15, 6.75, 17.7, 0.7, "So the translation sets the size of the change we test.", 32, True)
rect_i = rect(sE, 1.15, 7.65, 17.7, 1.95, fill=TINT)
lab = text(sE, 1.5, 7.85, 17.0, 0.5, "IMPLICATIONS FOR THE AI AGENT", 20, color=BLUE, font=MONO)
imp = text(sE, 1.5, 8.35, 17.0, 1.1, "The surrogate only takes 0–1 and people speak in real units, so the agent has to translate both ways.", 30)
animate(sE, groups[:1] + [groups[1] + groups[2]] + [[msg], [rect_i, lab, imp]])
notes(sE, "This is why the translation is important. The same move on the dial is a different real change on each lever. "
          "If we want to approximate the magnitude of a change correctly, we need to go from the real value to the dial "
          "and back. The agent sits in the middle of this.\n\n"
          "Do not mention the 'half' example here: it comes in Findings.")

# 8. Problem and opportunity (Alexa's boxes and clicks stay)
s = orig[8]
t = by_id(s, 38)
set_text(t, "How can AI make computational experiments interactive?", 45)
t.left, t.top, t.width, t.height = Inches(1.15), Inches(1.39), Inches(18.33), Inches(0.73)
no_autofit(t)
notes(s, "James's question: how can we leverage AI to support faster, interactive analyses with computational experiments?")

# 9. Research questions (wording untouched, key phrases in bold, Alexa's clicks stay)
s = orig[9]
text(s, 1.15, 1.39, 18.33, 0.73, "Our questions: how to build it, what the agent must know", 45, True)


def bold_phrases(shape, phrases, size):
    pg = shape.text_frame.paragraphs[0]
    assert len(shape.text_frame.paragraphs) == 1
    full = "".join(r.text for r in pg.runs)
    template = pg.runs[0]._r
    pieces, rest = [], full
    for ph in phrases:
        a, b = rest.split(ph, 1)
        pieces += [(a, False), (ph, True)]
        rest = b
    pieces.append((rest, False))
    assert "".join(x for x, _ in pieces) == full
    for r in pg.runs[1:]:
        r._r.getparent().remove(r._r)
    last = template
    for k, (txt, is_bold) in enumerate(pieces):
        el = template if k == 0 else copy.deepcopy(template)
        if k:
            last.addnext(el)
        last = el
    for r, (txt, is_bold) in zip(pg.runs, pieces):
        r.text = txt
        r.font.bold = is_bold
        r.font.size = Pt(size)


bold_phrases(by_id(s, 34), ["integrate a surrogate model", "AI agent", "non-technical users", "three components of RDM",
                            "evaluate"], 25)
bold_phrases(by_id(s, 37), ["type of information", "use of the available tools", "policy levels and uncertainty ranges"], 25)
by_id(s, 36).top = by_id(s, 33).top
notes(s, "RQ1 is about building and evaluating the system. RQ2 is about the information we give the agent.")

# ---------------------------------------------------------------- Method
# 11. Pipeline (Alexa's layout and clicks stay; shorter text in the harness)
s = orig[11]
set_text(by_id(s, 10), "Claude Sonnet 5.5 · chooses tools and arguments")
set_text(by_id(s, 22), "Keeps ensembles and labels, so tools chain safely")
set_text(by_id(s, 24), "Levers in range · uncertainties never fixed · threshold before vulnerability")
set_text(by_id(s, 26), "Every call, reply and answer")
set_text(by_id(s, 28), "Same limits in every condition")
notes(s, "The story is: the policy maker asks a question. The agent is the brain, and that brain's capacities vary depending "
         "on the model we choose; this model balances capacity and tokens. With just the brain able to think and answer "
         "back it's not enough: we need to give it tools to execute processes. They run deterministic methods that have "
         "access to the surrogate we build and to the data we decide to provide. But the way the brain and the tools "
         "interact depends on the harness we build for it. In there we specify what each of the tools does, specify the "
         "rules for the agent and track its actions in the system.")

# 12. Rules
s = orig[12]
frame(s, "METHOD · THE ECOSYSTEM", "Six rules for the agent, its tool use and the tools", "Method")
groups = clicks_of(s)
extra = text(s, 1.15, 8.0, 17.7, 0.7, "No script of steps: the agent chooses the tools and their order.", 30, True, BLUE)
animate(s, groups + [[extra]])
notes(s, "Note: the rules don't script the agent's behavior step by step. They give it information about what each tool does "
         "and provides, and the agent decides.\n\n"
         "For Q&A: the harness does contain a few conditional instructions, for example 'If vulnerability_analysis asks for a "
         "threshold, ask the user' (appendix, system prompt).")

# 13. Tools, much simpler
s = orig[13]
clear(s, keep=[x.shape_id for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() in SECTIONS | {FOOTER}] + [2, 3])
frame(s, "METHOD · THE TOOLS", "Each tool has one job", "Method")
cols = (2.35, 7.5, 14.0)
heads = [text(s, cols[0], 2.65, 5, 0.45, "Tool", 21, True, GREY), text(s, cols[1], 2.65, 6, 0.45, "The question it answers", 21, True, GREY),
         text(s, cols[2], 2.65, 5, 0.45, "What it does", 21, True, GREY), rect(s, 1.15, 3.15, 17.7, 0.025, fill=INK)]
table = (("READ", "model_network", "What does this lever do? What moves this result?", "Shows the links; Map+ adds values"),
         ("READ", "country_context", "What is Uganda like in the model?", "Gives the modeled baseline"),
         ("RUN", "exploratory_modeling", "What happens if we apply this policy?", "Runs it across 500 futures"),
         ("RUN", "vulnerability_analysis", "How often does it fail?", "Asks the user what counts as failure"),
         ("RUN", "scenario_discovery", "Under which conditions does it fail?", "Names the conditions, not predictions"),
         ("RUN", "trade_off_analysis", "What does each policy cost for what it cuts?", "Compares, never names a winner"))
read, run = [], []
for k, (tag, tool, q, does) in enumerate(table):
    yy = 3.35 + k * 1.06
    fill = BLUE if tag == "READ" else GREY
    g = [rect(s, 1.15, yy + 0.03, 0.95, 0.42, fill=fill),
         text(s, 1.15, yy + 0.03, 0.95, 0.42, tag, 17, True, "FFFFFF", MONO, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE),
         text(s, cols[0], yy, 5.0, 0.9, tool, 20, True, BLUE if tag == "READ" else INK, MONO),
         text(s, cols[1], yy, 6.2, 0.95, q, 22),
         text(s, cols[2], yy, 4.85, 0.95, does, 22, color=GREY),
         row_line(s, 1.15, yy + 0.95, 17.7)]
    (read if tag == "READ" else run).extend(g)
animate(s, [read, run])
notes(s, "Here are the capabilities we are giving the agent to use in this system we have built for it. The first two "
         "provide information, the rest allow the execution of actions.\n\n"
         "The full table, with examples and what each tool does not do, is in the appendix.")

# P. The problem we hit
sP = new_slide()
frame(sP, "METHOD · THE DATA", "The tools alone didn't let the agent understand the system", "Method")
y, h = 3.4, 3.4
g1 = box(sP, 1.15, y, 4.4, h, "Levers", "What the agent can set, from 0 to 1", fill=PALE)
ar1 = text(sP, 5.6, y, 0.8, h, "→", 40, color=MUTE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
mid_r = rect(sP, 6.45, y, 7.1, h, line=BLUE, dash=True, weight=2)
mid_t = text(sP, 6.75, y, 6.5, h, ["What does a lever mean?", "What happens in between?"], 32, True, BLUE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
ar2 = text(sP, 13.6, y, 0.8, h, "→", 40, color=MUTE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
g2 = box(sP, 14.45, y, 4.4, h, "Results", "Sector emissions, costs, benefits, GDP", fill=PALE)
cap = text(sP, 1.15, 7.45, 17.7, 0.7, "The agent could run the surrogate, but it could not see inside it.", 32)
animate(sP, [g1 + g2 + [ar1, ar2], [mid_r, mid_t], [cap]])
notes(sP, "This is the real process. I noted from the beginning that the tools, as they were constructed, weren't giving "
          "the agent enough data to understand the system.")

# Q. The dilemma
sQ = new_slide()
frame(sQ, "METHOD · THE DATA", "What data, and how? Not too little, not all of it", "Method")
y, h, w = 3.3, 3.2, 5.6
c1 = box(sQ, 1.15, y, w, h, "Too little", "The agent guesses what the levers mean")
c3 = box(sQ, 13.25, y, w, h, "All 100,000 runs", "The agent becomes slow and costly")
c2 = box(sQ, 7.2, y, w, h, "Just enough", "What the agent needs, when it asks for it", fill=BLUE)
end = text(sQ, 1.15, 7.3, 17.7, 0.8, "How we give the data, and which data, became a design question.", 32, True)
animate(sQ, [c1, c3, c2, [end]])
notes(sQ, "We needed a way to give the information without giving the whole 100k dataset, and without losing the objective of "
          "evaluating how the agent behaves.\n\n"
          "Careful in Q&A: 'slow and costly' is our design reasoning. We did not test giving the agent all the data.")

# 14. Map
s = orig[14]
keep = [x.shape_id for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() in SECTIONS | {FOOTER}]
keep += [2, 3] + [x.shape_id for x in s.shapes if x.shape_type == 13 or x.top > Inches(9.2)]
clear(s, keep=keep)
frame(s, "METHOD · THE DATA", "The AI built Map, a knowledge graph, from the model's code", "Method")
set_text(find(s, "the L35 walk"), "one walk")
layers = (("Levers and uncertainties", "What we can set", True),
          ("Input variables", "What each lever changes", False),
          ("In-between variables", "What SISEPUEDE computes from them", False),
          ("Emissions", "In detail, by source", False),
          ("Sector emissions", "The categories the XGBoost predicts", True))
lay, ends_ = [], []
for k, (name, sub, end_) in enumerate(layers):
    yy = 2.55 + k * 1.02
    if end_:
        ends_.append(rect(s, 10.3, yy - 0.08, 8.55, 0.98, fill=TINT))
    lay += [text(s, 10.5, yy, 8.2, 0.45, name, 26, True), text(s, 10.5, yy + 0.43, 8.2, 0.4, sub, 20, color=GREY)]
for e in ends_:
    s.shapes._spTree.remove(e._element)
    s.shapes._spTree.insert(2, e._element)
msg = text(s, 10.3, 7.72, 8.55, 1.2, "The two ends match the XGBoost. Map shows the agent what happens in between.", 27, True, BLUE)
animate(s, [lay, ends_ + [msg]])
notes(s, "For the model_network tool we design a network that shows the relations of the variables in the original model, the "
         "one the 100,000 runs for the surrogate come from. We have two versions of the network. The first one we call Map "
         "and it only includes the relations of these variables: each of the levers, the ones that can be moved in the "
         "surrogate parameters, the input variables of the model, some in-between variables, the disaggregated emissions "
         "they are connected to, and the categories of emissions that are the variables predicted in the XGBoost.\n\n"
         "For Q&A, how do you know the network is right? 93.9% of the 4,568 links seen in the runs have a path in the network "
         "(levers to emissions 97.8%). 714 SISEPUEDE variables, 804 nodes, 4,379 links, traced from one run of the code with "
         "tagged arrays. A link means 'used to compute', not causality.")

# 15. Map+
s = orig[15]
keep = [x.shape_id for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() in SECTIONS | {FOOTER}]
keep += [2, 3] + [x.shape_id for x in s.shapes if x.shape_type == 13 or x.top > Inches(9.2)]
clear(s, keep=keep)
frame(s, "METHOD · THE DATA", "Map+ adds the density of each variable from the runs", "Method")
set_text(find(s, "the L35 walk"), "one walk")
a = text(s, 10.5, 2.75, 8.3, 0.6, "The same links, plus:", 32, True)
b1_ = text(s, 10.5, 3.65, 8.3, 0.95, [[("The density ", {"bold": True, "color": BLUE}), ("of each variable", {})]], 30)
b2_ = text(s, 10.5, 4.6, 8.3, 1.2, [[("From a sample ", {"bold": True, "color": BLUE}), ("of 4,989 of the 100,000 runs", {})]], 30)
b3_ = text(s, 10.5, 5.75, 8.3, 1.2, [[("By lever level ", {"bold": True, "color": BLUE}), ("and by uncertainty level", {})]], 30)
c_ = text(s, 10.5, 7.45, 8.35, 1.2, "A summary of the runs, not the whole dataset.", 30, True)
animate(s, [[a, b1_], [b2_], [b3_], [c_]])
notes(s, "The second version includes the same links, but each node now includes information on the densities of each variable, "
         "from a sample of runs out of the 100k.\n\n"
         "For Q&A: precisely, the agent sees the median and p10-p90 of each variable, by lever third and uncertainty third.")

# 16. The walk (Alexa's clicks stay)
s = orig[16]
frame(s, "METHOD · THE DATA", "Map and Map+ see different information on the same walk", "Method")
set_text(by_id(s, 18), "Car fuel shift")
set_text(by_id(s, 52), "12 transport levers reach it")
set_text(by_id(s, 75), "How we give it: one node at a time, so the agent takes only what it asks for.")
notes(s, "When speaking, note that this is showing the path from the previous two slides.\n\n"
         "When the agent gets a question it can call the model_network tool and navigate the network. When the Map version is "
         "in place, it will only look at the relations, while when the Map+ is in place it will also be able to see the "
         "densities of the values for each variable. Here is an example of the differences in what the agent will see on each "
         "version. That path across the network is for lever 35.\n\n"
         "2050 medians from 4,989 runs. Lever low (0-1/3) to high (2/3-1). Shares: BAU to top of range. Levers that reach "
         "Transportation: L31-L42.")

# ---------------------------------------------------------------- Experiment
# 18. Only one thing changes
s = orig[18]
clear(s, keep=[x.shape_id for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() in SECTIONS | {FOOTER}] + [2, 3])
frame(s, "EXPERIMENT · THE TREATMENT", "Only one thing changes: the version of the network", "Experiment")
left = [rect(s, 1.15, 3.0, 7.6, 0.025, fill=INK), text(s, 1.15, 3.2, 7.6, 0.6, "Kept the same", 30, True)]
left += [text(s, 1.15, 4.0 + k * 0.72, 7.6, 0.6, t_, 28, color=GREY) for k, t_ in
         enumerate(("Same prompt", "Same 6 tools", "Same agent model", "Same questions", "Same futures"))]
r_ = [rect(s, 9.6, 3.0, 9.25, 4.75, fill=TINT), text(s, 9.95, 3.2, 8.6, 0.6, "What changes", 30, True, BLUE),
      text(s, 9.95, 4.15, 8.6, 1.3, [[("Map: ", {"bold": True}), ("the relations", {})]], 34),
      text(s, 9.95, 5.45, 8.6, 1.3, [[("Map+: ", {"bold": True, "color": BLUE}), ("the relations and the densities", {})]], 34)]
goal = text(s, 1.15, 8.2, 17.7, 0.8, "So we can evaluate how the agent behaves with and without the values.", 32, True)
animate(s, [left, r_, [goal]])
notes(s, "The experiment consists of keeping everything constant except for the version of the network the agent can see: "
         "either Map or Map+.")

# 19. Six types of question
s = orig[19]
frame(s, "EXPERIMENT · QUESTIONS", "We asked six types of question across 290 conversations", "Experiment")
purpose = {"Evaluate a policy": "Translate words into a lever",
           "In-between quantities": "Find what the surrogate can't report",
           "Reach a target": "Find the levers that matter",
           "Robustness": "Complete the RDM steps",
           "Trade-offs": "Compare without naming a winner",
           "Outside the model": "Say the model can't answer"}
row1, row2 = [], []
for (bg, head_, quote), yy in zip(((6, 7, 8), (9, 10, 11), (12, 13, 14), (15, 16, 17), (18, 19, 20), (21, 22, 23)),
                                  (2.45, 2.45, 2.45, 4.8, 4.8, 4.8)):
    b_, h_, q_ = by_id(s, bg), by_id(s, head_), by_id(s, quote)
    b_.top, b_.height = Inches(yy), Inches(2.2)
    h_.top = Inches(yy + 0.14)
    pp = text(s, h_.left / 914400, yy + 0.66, 5.24, 0.42, purpose[h_.text_frame.text.strip()], 21, True, BLUE)
    q_.top = Inches(yy + 1.14)
    for r in q_.text_frame.paragraphs[0].runs:
        r.font.size = Pt(17)
    (row1 if yy < 3 else row2).extend([b_, h_, pp, q_])
strip = [by_id(s, i) for i in range(24, 35)]
for x in strip:
    x.top += Inches(0.1)
animate(s, [row1, row2, strip])
notes(s, "We evaluate 6 types of questions, each one with a specific purpose. In total there were 29 question scripts, evaluated "
         "with the two versions of the network, 5 times each. All of the conversations were logged for the results analysis.")

# 20. Criteria, each with its objective
s = orig[20]
clear(s)
frame(s, "EXPERIMENT · EVALUATION", "Four criteria, each with its own objective", "Experiment")
crit = (("Tool use", "Does the agent run the analysis correctly?",
         ["Level matches the key", "No required step skipped", "No invented threshold"]),
        ("Answer rules", "Can the user trace where its numbers come from?",
         ["Numbers come from a tool", "Gives a range"]),
        ("Per question", "Did it deliver what this question needed?",
         ["Says what was required", "Reaches the right variable"]),
        ("Reader model", "Does it respect the RDM framing?",
         ["A second model reads the conversation", "No forecast language", "Names no winner"]))
groups = []
w = 4.1
for k, (name, obj, checks) in enumerate(crit):
    x = 1.15 + k * (w + 0.43)
    groups.append([rect(s, x, 2.75, w, 0.03, fill=INK),
                   text(s, x, 2.95, w, 0.55, name, 25, True, BLUE),
                   text(s, x, 3.6, w, 2.1, obj, 29, True),
                   text(s, x, 5.85, w, 0.4, "WE CHECK", 17, color=MUTE, font=MONO),
                   text(s, x, 6.3, w, 2.9, checks, 23, color=GREY)])
animate(s, groups)
notes(s, "First explain the evaluation criteria clearly. Each one has its own objective, and we come back to them in the findings.\n\n"
         "Where they show up: Tool use in the 'half' example, the pooled results and the 290-conversation numbers. Answer rules in "
         "the arithmetic slide. Per question in the early-stop slide. Reader model: no talk slide reports a reader result.")

# 21. The scoring flow
s = orig[21]
clear(s)
frame(s, "EXPERIMENT · EVALUATION", "Each conversation is scored against a human answer key", "Experiment")
w = 4.9
q_ = box(s, 1.15, 4.35, w, 2.5, "Question", "Asked word for word")
aq1 = text(s, 6.15, 3.2, 1.3, 2.4, "→", 40, color=MUTE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
aq2 = text(s, 6.15, 5.6, 1.3, 2.4, "→", 40, color=MUTE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
e_ = box(s, 7.55, 3.0, w, 2.5, "Expected", "Answer key and tools")
o_ = box(s, 7.55, 5.7, w, 2.5, "Observed", "Tools, arguments and answer, from the log")
ac = text(s, 12.55, 4.35, 1.3, 2.5, "→", 40, color=MUTE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
c_ = box(s, 13.95, 4.35, w, 2.5, "Compare", "25 automatic checks", fill=BLUE)
animate(s, [q_, [aq1] + e_, [aq2] + o_, [ac] + c_])
notes(s, "Then we want to show that the predetermined answers were compared against the observed ones.")

# ---------------------------------------------------------------- Findings
# 23. "Half"
s = orig[23]
frame(s, "FINDINGS · RQ2 · CRITERION: TOOL USE", "With no values, the agent can only guess what words mean", "Findings")
for sid in (7, 18):
    tf = by_id(s, sid).text_frame
    first = tf.paragraphs[0]
    assert first.text.strip() in ("WW1", "P50i")
    first._p.getparent().remove(first._p)
for sid in (13, 24, 15, 17, 28, 30):
    for r in by_id(s, sid).text_frame.paragraphs[0].runs:
        r.font.size = Pt(19)
set_text(by_id(s, 13), "answer key 0.716: half to septic tanks")
set_text(by_id(s, 31), "With values, it looks them up.", 34)
for r in by_id(s, 31).text_frame.paragraphs[0].runs:
    r.font.bold = True
G = lambda *ids: [by_id(s, i) for i in ids]
animate(s, [G(7, 8, 9, 10, 11), G(12, 13), G(14, 15), G(16, 17),
            G(18, 19, 20, 21, 22, 23, 24), G(25, 26, 27, 28), G(29, 30), G(31)])
notes(s, "James: remember to walk through the elements here. It's a simple graph, but there's a lot to detail for the listener.\n\n"
         "Each line is the lever's dial, from 0 to 1. First the question, then the answer key, then what the agent did in Map, "
         "then in Map+.\n\n"
         "Questions WW1 (lever 46, key 0.716) and P50i (lever 50, key 0.688). Lever levels set in the first run of each "
         "conversation; answer keys computed from the model runs, fixed before the run.")

# 24. Pooled results
s = orig[24]
frame(s, "FINDINGS · RQ2 · CRITERION: TOOL USE", "With values, the agent set levels right in fewer calls", "Findings")
rows_ = [[], [], [], []]
bands = ((3.5, 4.2), (4.25, 4.95), (5.0, 5.7), (5.75, 6.45))
for x in s.shapes:
    top = x.top / 914400
    for k, (a_, b_) in enumerate(bands):
        if a_ <= top < b_:
            rows_[k].append(x)
closing = find(s, "Uncertainty ranges")
animate(s, rows_ + [[closing]])
notes(s, "Rows one by one. 290 conversations; rows 1-3: p < 0.01. Bars show the share of answers (calls: 0-4 per conversation).")

# 25a. Own arithmetic
s = orig[25]
clear(s, keep=[x.shape_id for x in s.shapes if x.has_text_frame and (x.text_frame.text.strip() in SECTIONS | {FOOTER} or x.top < Inches(1.6))])
frame(s, "FINDINGS · RQ2 · CRITERION: ANSWER RULES", "With values, the agent also calculates for itself", "Findings")
text(s, 1.15, 2.85, 17.7, 0.5, "Answers with a number no tool gave", 28, color=GREY)
TRACK = 11.0


def meter(s, y, label, value, of, shown, color, label_w=4.6):
    x = 1.15 + label_w
    return [text(s, 1.15, y, label_w - 0.2, 0.6, label, 28, True, color if color == BLUE else GREY),
            rect(s, x, y + 0.08, TRACK, 0.42, fill=PALE),
            rect(s, x, y + 0.08, max(TRACK * value / of, 0.06), 0.42, fill=color),
            text(s, x + TRACK + 0.3, y, 18.85 - (x + TRACK + 0.3), 0.6, shown, 28, True, color if color == BLUE else GREY)]


m1 = meter(s, 3.6, "Map", 11, 155, "11 of 155", MAP)
m2 = meter(s, 4.5, "Map+", 17, 155, "17 of 155", BLUE)
c0 = rect(s, 1.15, 5.8, 17.7, 2.9, fill=TINT)
c1_ = text(s, 1.5, 6.05, 17, 0.45, "THE AGENT COMPUTED", 20, color=BLUE, font=MONO)
c2_ = text(s, 1.5, 6.6, 17, 0.8, "“21 ÷ 33 is about 0.64 electric.”", 36, True)
c3_ = text(s, 1.5, 7.55, 17, 0.7, "Reasonable, but no tool computed it.", 28, color=GREY)
animate(s, [m1 + m2, [c0, c1_, c2_, c3_]])
notes(s, "Values give the agent numbers to calculate with. Those numbers need tracing before they reach a decision maker.\n\n"
         "Question HA1, Map+. Hypothesis questions: 0% vs 20%.")

# 25b. Early stops
sR = new_slide()
frame(sR, "FINDINGS · RQ2 · CRITERION: PER QUESTION", "With values, the agent can stop before the answer", "Findings")
text(sR, 1.15, 2.85, 17.7, 0.5, "In-between questions, Map+: did it give the value from the runs?", 28, color=GREY)
TRACK = 8.2
m1 = meter(sR, 3.6, "When it reached the variable", 7, 7, "7 of 7", BLUE, label_w=7.4)
m2 = meter(sR, 4.5, "When it stopped early", 0, 13, "0 of 13", BLUE, label_w=7.4)
c0 = rect(sR, 1.15, 5.6, 17.7, 2.5, fill=TINT)
c1_ = text(sR, 1.5, 5.8, 17, 0.45, "THE AGENT TOLD THE USER", 20, color=BLUE, font=MONO)
c2_ = text(sR, 1.5, 6.3, 17, 0.8, "“The tools don't report transport electricity demand.”", 34, True)
c3_ = text(sR, 1.5, 7.2, 17, 0.7, "The network had it, two steps further on: 56.0 → 59.9 PJ.", 28, color=GREY)
end = text(sR, 1.15, 8.5, 17.7, 0.8, "Values answer the first question so well that the agent stops looking.", 32, True)
animate(sR, [m1, m2, [c0, c1_, c2_, c3_], [end]])
notes(sR, "Questions S50, S3, S35 and HD1. Map+ reached the node 7 times and gave the run value 7 of 7; it stopped early 13 "
          "times and gave it 0 of 13. The quote is from HD1. Full table in the appendix.")

# 26a. One robustness question
s = orig[26]
clear(s, keep=[x.shape_id for x in s.shapes if x.has_text_frame and (x.text_frame.text.strip() in SECTIONS | {FOOTER} or x.top < Inches(1.6))])
frame(s, "FINDINGS · RQ1", "A simulated user worked through RDM via the agent", "Findings")
text(s, 1.15, 2.6, 17.7, 0.6, "Can a non-technical user complete the three RDM components?", 30, True, BLUE)
cx = (1.15, 2.35, 10.2, 14.65)
hd = [text(s, cx[1], 3.45, 7.5, 0.4, "The user asked", 20, True, GREY),
      text(s, cx[2], 3.45, 4.2, 0.4, "The agent ran", 20, True, GREY),
      text(s, cx[3], 3.45, 4.2, 0.4, "It found", 20, True, GREY),
      rect(s, 1.15, 3.9, 17.7, 0.025, fill=INK)]
turns = (("1", "“Is a policy with a strong push on renewable electricity and a moderate cut in deforestation robust?”",
          ["exploratory_modeling"], "500 futures; asks what counts as failure"),
         ("2", "“Count it as a failure if 2050 emissions are not at least 5% below BAU.”",
          ["vulnerability_analysis", "scenario_discovery"], "Fails in 79%, mostly when GDP grows fast"),
         ("2", "“Does it still work if the economy grows fast?”",
          ["exploratory_modeling", "vulnerability_analysis"], "Fails in 99%"),
         ("3", "“What could we change so it holds up, and does it?”",
          ["model_network", "exploratory_modeling", "vulnerability_analysis"], "Adds a livestock lever: fails in 0%"))
groups = []
for k, (comp, ask, ran, found) in enumerate(turns):
    yy = 4.05 + k * 1.45
    g = [rect(s, 1.15, yy + 0.04, 0.95, 0.42, fill=TINT),
         text(s, 1.15, yy + 0.04, 0.95, 0.42, f"RDM {comp}", 15, True, BLUE, MONO, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE),
         text(s, cx[1], yy, 7.5, 1.3, ask, 22),
         text(s, cx[2], yy, 4.3, 1.3, ran, 15, color=GREY, font=MONO),
         text(s, cx[3], yy, 4.2, 1.3, found, 22, True, BLUE),
         row_line(s, 1.15, yy + 1.35, 17.7)]
    groups.append(g)
animate(s, [hd + groups[0]] + groups[1:])
notes(s, "RQ1: one question followed through the three RDM components. RDM 1 is exploratory modeling, RDM 2 is vulnerability "
         "analysis and scenario discovery, RDM 3 is trade-off analysis and strategy improvement. The user here is scripted, not a "
         "real policy maker.\n\nConversation Q10b. Connected to the Tool use criterion: the next slide gives the numbers for all "
         "290 conversations.")

# 26b. Across all conversations
sT = new_slide()
frame(sT, "FINDINGS · RQ1 · CRITERION: TOOL USE", "Across all 290 conversations, the process held", "Findings")
groups = []
for k, (big, small, color) in enumerate((("290 of 290", "conversations finished", INK), ("0", "invented thresholds", INK),
                                         ("22% → 12%", "required RDM step skipped, Map → Map+", BLUE))):
    x = 1.15 + k * 6.05
    groups.append([rect(sT, x, 3.5, 5.6, 0.03, fill=INK), text(sT, x, 3.85, 5.6, 1.2, big, 54, True, color),
                   text(sT, x, 5.2, 5.5, 1.3, small, 28, color=GREY)])
animate(sT, groups)
notes(sT, "These numbers come from the Tool use criterion.")

# 27. Conclusion
s = orig[27]
frame(s, "FINDINGS · CONCLUSION", "What data the agent gets, and how, shapes how it behaves", "Findings")
set_text(find(s, "Trace and label every number"), "Trace every number")
set_text(find(s, "Values invite the agent"), "Values invite the agent’s own arithmetic (11 → 17 of 155 answers).")
set_text(find(s, "Notes on what we"), "Scope of these results")
for start in ("The agent turns words", "Values invite the agent", "Tool instructions need"):
    for r in find(s, start).text_frame.paragraphs[0].runs:
        r.font.size = Pt(22)
cards = []
for start in ("1", "2", "3"):
    num = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() == start][0]
    cards.append(num)
tops = sorted({c.left for c in cards})
groups = []
for c in sorted(cards, key=lambda c: c.left):
    x0_, x1_ = c.left - Inches(0.5), c.left + Inches(5.6)
    groups.append([x for x in s.shapes if x0_ <= x.left < x1_ and Inches(2.3) < x.top < find(s, "Scope of these").top - Inches(0.05)])
low = [x for x in s.shapes if find(s, "Scope of these").top - Inches(0.05) <= x.top < Inches(10.0)]
assert not set(id(a) for g in groups for a in g) & set(id(b) for b in low)
animate(s, groups + [low])
notes(s, "With values the agent translates policies correctly and searches less, but it also calculates for itself and sometimes "
         "stops too early. More information doesn't simply mean better: it changes how the agent behaves, so what data we give "
         "and how we give it is a design decision we have to test.")

# ---------------------------------------------------------------- order
ids = p.slides._sldIdLst
el = {i: None for i in orig}
for sid in list(ids):
    rid = sid.rId
    for i, sl in orig.items():
        if p.part.related_part(rid) is sl.part:
            el[i] = sid
extra_el = {}
for sid in list(ids):
    part = p.part.related_part(sid.rId)
    for key, sl in (("B", sB), ("C", sC), ("E", sE), ("P", sP), ("Q", sQ), ("R", sR), ("T", sT)):
        if part is sl.part:
            extra_el[key] = sid
order_ = [1, 2, 3, 4, 5, "B", "C", 6, "E", 8, 9, 10, 11, 12, 13, "P", "Q", 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
          "R", 26, "T", 27] + list(range(28, 51))
dup = el[7]
p.part.drop_rel(dup.rId)
for sid in list(ids):
    ids.remove(sid)
for key in order_:
    ids.append(el[key] if isinstance(key, int) else extra_el[key])

p.save(OUT)
print("saved", OUT, "slides:", len(order_))
