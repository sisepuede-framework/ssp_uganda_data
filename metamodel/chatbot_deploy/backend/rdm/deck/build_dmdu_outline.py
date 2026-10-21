# Requires python-pptx. Usage: python backend/rdm/deck/build_dmdu_outline.py docs/dmdu_2026_talk_outline.pptx
"""Preliminary outline deck for the DMDU 2026 annual meeting talk (python-pptx).
White background, sober type, boxes and arrows."""
import json
import math
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

OUT = sys.argv[1]
# Harness text for the appendix; refresh with: python -m backend.rdm.deck.dump_harness_text
HARNESS = json.loads((Path(__file__).parent / "harness_text.json").read_text())

WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TXT = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x6B, 0x72, 0x80)
BORDER = RGBColor(0xC9, 0xCE, 0xD6)
FILL = RGBColor(0xF3, 0xF4, 0xF6)
ACC = RGBColor(0x1F, 0x4E, 0x79)
ACC_LT = RGBColor(0xE6, 0xEE, 0xF6)
HEAD = "Montserrat"          # titles, labels, box headings
BODY = "Times New Roman"     # running text, box sub-lines, tool names

W, H = 13.333, 7.5
LM = 0.6
CW = W - 2 * LM
TOP = 1.55

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, s, pt, color=TXT, bold=False, italic=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, space_after=0, font=BODY):
    """'\n' = new paragraph; '**x**' = bold run."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, para in enumerate(s.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = 1.05
        if space_after:
            p.space_after = Pt(space_after)
        for j, seg in enumerate(para.split("**")):
            if not seg:
                continue
            r = p.add_run()
            r.text = seg
            f = r.font
            f.name, f.size, f.color.rgb = font, Pt(pt), color
            f.bold = bold or (j % 2 == 1)
            f.italic = italic
    return tb


def rect(slide, x, y, w, h, fill=WHITE, line=BORDER, dash=False, line_w=1.0):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = min(0.15, 0.08 / max(h, 0.1))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
        if dash:
            shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    shp.shadow.inherit = False
    return shp


def node(slide, x, y, w, h, head, sub=None, fill=WHITE, line=BORDER, head_pt=15, sub_pt=12,
         head_color=TXT, sub_color=MUTED, align=PP_ALIGN.CENTER, dash=False, italic=False,
         head_font=HEAD):
    """A box with a bold heading and an optional line below, centred vertically."""
    rect(slide, x, y, w, h, fill, line, dash=dash)
    s = f"**{head}**" if head else ""
    tb = text(slide, x + 0.12, y + 0.06, w - 0.24, h - 0.12, s, head_pt, color=head_color,
              align=align, anchor=MSO_ANCHOR.MIDDLE, italic=italic, font=head_font)
    if sub:
        p = tb.text_frame.add_paragraph()
        p.alignment = align
        p.space_before = Pt(3)
        r = p.add_run()
        r.text = sub
        r.font.name, r.font.size, r.font.color.rgb = BODY, Pt(sub_pt + 1), sub_color
        r.font.italic = italic
    return tb


def arrow(slide, x1, y1, x2, y2, color=MUTED, width=1.5, dash=False, head=True):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    if dash:
        c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    if not head:
        return c
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


def new_slide(title, section, notes=None):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = WHITE
    text(s, LM, 0.42, CW, 0.3, section.upper(), 11, color=MUTED, bold=True, font=HEAD)
    text(s, LM, 0.7, CW, 0.6, title, 24, color=TXT, bold=True, anchor=MSO_ANCHOR.BOTTOM, font=HEAD)
    text(s, LM, 7.02, CW - 0.6, 0.25, "DMDU 2026 · preliminary outline", 10, color=MUTED, font=HEAD)
    text(s, W - LM - 0.5, 7.02, 0.5, 0.25, str(len(prs.slides)), 10, color=MUTED, align=PP_ALIGN.RIGHT, font=HEAD)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def placeholder(slide, x, y, w, h, s, pt=14):
    rect(slide, x, y, w, h, fill=None, line=BORDER, dash=True)
    text(slide, x + 0.3, y, w - 0.6, h, s, pt, color=MUTED, italic=True, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)


# ═════════════════════════════════════════════════════════════════════════════
# 1 · Cover
s = prs.slides.add_slide(BLANK)
s.background.fill.solid()
s.background.fill.fore_color.rgb = WHITE
text(s, LM, 2.0, CW, 0.3, "DMDU Society Annual Meeting 2026  ·  Preliminary outline", 14, color=MUTED, font=HEAD)
text(s, LM, 2.45, 11.5, 1.6, "AI as an intermediary for three\ncomponents of Robust Decision Making", 36, color=TXT, bold=True, font=HEAD)
text(s, LM, 4.25, 10.5, 0.8, "An agent ecosystem on a SISEPUEDE surrogate for Uganda, and what the information "
     "we give the agent about the model changes", 20, color=MUTED)
text(s, LM, 6.3, CW, 0.3, "[Presenter] · [Co-authors] · [Affiliation]", 14, color=MUTED)
s.notes_slide.notes_text_frame.text = (
    "Preliminary structure for the DMDU annual meeting talk, to review with my lead. Working title. "
    "Items in [brackets] are still to be filled.")

# 2 · Context
s = new_slide("Slow, technical models keep policy makers out of RDM", "Context",
              "1. Running the model takes about 3 minutes per run. 2. It requires technical expertise: to run the "
              "model and to carry out the analytical steps of RDM. 3. Surrogate models make faster runs possible. 4. AI can act as "
              "an intermediary that covers the need for technical expertise. 5. The AI relies on the architecture we "
              "build for the agent to move in, and on the information we give it about the model. The literature review "
              "still has to be done to support this part.")
steps = [
    ("~3 min per run", "Running SISEPUEDE is slow; RDM needs many runs"),
    ("Technical expertise", "To run the model and to carry out the analytical steps of RDM"),
    ("Surrogate models", "Make runs fast enough to explore many futures"),
    ("AI as intermediary", "An agent can stand in for the technical expertise"),
    ("Architecture + data", "The agent depends on the system we build and the data we give it"),
]
gap = 0.4
bw = (CW - 4 * gap) / 5
by, bh = TOP + 0.5, 1.9
for i, (head, sub) in enumerate(steps):
    x = LM + i * (bw + gap)
    hl = i == 4
    text(s, x, by - 0.42, bw, 0.3, str(i + 1), 14, color=ACC if hl else MUTED, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
    node(s, x, by, bw, bh, head, sub, fill=ACC_LT if hl else FILL, line=ACC if hl else BORDER,
         head_pt=16, sub_pt=13)
    if i < 4:
        arrow(s, x + bw + 0.05, by + bh / 2, x + bw + gap - 0.05, by + bh / 2)
for label, a, b in [("Problem", 0, 2), ("Opportunity", 2, 4), ("Our focus", 4, 5)]:
    x = LM + a * (bw + gap)
    w = (b - a) * bw + (b - a - 1) * gap
    text(s, x, by + bh + 0.15, w, 0.3, label, 13, color=MUTED, align=PP_ALIGN.CENTER)
placeholder(s, LM, by + bh + 0.75, CW, 1.6,
            "[Literature review to add: RDM practice and its barriers · surrogate models in DMDU · "
            "LLM agents as interfaces to models]")

# 3 · Research questions
s = new_slide("We build the system, then vary what the agent knows", "Context",
              "From here come our research questions. Shorter variant of RQ1 in my notes: 'How can we build an "
              "ecosystem that integrates AI and surrogate models?' Changed 2026-10-19 after the critical review: RQ1 "
              "speaks of questions asked by a non-technical person, because the user in the experiment is simulated "
              "(testing with real decision makers is future work); RQ2 says 'type of information' instead of "
              "'quality of the data', because the arms change what the agent sees of the model, not how accurate it is.")
rqs = [("RQ1", "How do we integrate a surrogate model of SISEPUEDE with an AI agent to develop a system "
               "that enables non-technical users to explore policy questions through the three components of RDM "
               "(exploratory modeling, vulnerability analysis, and trade-off analysis), and how do we evaluate "
               "such a system?",
        "→ Method: the surrogate and the ecosystem"),
       ("RQ2", "What is the impact of the type of information we give the agent about the model (how its variables "
               "are related, or also their values) on its use of the available tools and on the policy levels and "
               "uncertainty ranges it sets?",
        "→ Experiment: data, questions and surrogate interaction")]
y = TOP + 0.2
for tag, q, where in rqs:
    rect(s, LM, y, CW, 2.3, fill=WHITE, line=BORDER)
    text(s, LM + 0.35, y + 0.3, 1.2, 0.5, tag, 24, color=ACC, bold=True, font=HEAD)
    text(s, LM + 1.7, y + 0.3, CW - 2.1, 1.4, q, 21, color=TXT)
    text(s, LM + 1.7, y + 1.85, CW - 2.1, 0.35, where, 14, color=MUTED)
    y += 2.6

# 4 · Three components of RDM
s = new_slide("Through the agent, users do three components of RDM", "Context",
              "We do not present the tool as an RDM analysis in itself. It facilitates three components of the RDM "
              "methodology. 1. Exploratory modeling and stress testing: run a model across many combinations of "
              "uncertain assumptions to see how each strategy performs in different plausible futures. "
              "2. Vulnerability analysis and scenario discovery: use statistical analysis and visualization to identify "
              "combinations of conditions associated with poor performance; these become decision-relevant scenarios, "
              "not necessarily predictions. 3. Trade-off analysis and strategy improvement: compare the benefits and "
              "disadvantages of alternative responses, revise vulnerable plans, and test them again. The loop back "
              "from 3 to 1 is what makes it iterative. The numbers 1-3 reappear on the tools and questions slides.")
comps = [("Exploratory modeling and stress testing",
          "Run the model across many combinations of uncertain assumptions to see how each strategy performs "
          "in different plausible futures."),
         ("Vulnerability analysis and scenario discovery",
          "Use statistical analysis and visualization to identify combinations of conditions associated with "
          "poor performance. These become decision-relevant scenarios, not necessarily predictions."),
         ("Trade-off analysis and strategy improvement",
          "Compare the benefits and disadvantages of alternative responses, revise vulnerable plans, and test "
          "them again.")]
gap = 0.6
cw3 = (CW - 2 * gap) / 3
hy, hh = TOP + 0.45, 0.95
for i, (head, body) in enumerate(comps):
    x = LM + i * (cw3 + gap)
    text(s, x, TOP, cw3, 0.35, str(i + 1), 18, color=ACC, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
    node(s, x, hy, cw3, hh, head, fill=ACC_LT, line=ACC, head_pt=15)
    text(s, x + 0.1, hy + hh + 0.3, cw3 - 0.2, 2.0, body, 16, color=TXT)
    if i < 2:
        arrow(s, x + cw3 + 0.06, hy + hh / 2, x + cw3 + gap - 0.06, hy + hh / 2)
# loop: 3 back to 1
ly0, ly1 = TOP + 3.55, TOP + 3.95
x1c, x3c = LM + cw3 / 2, LM + 2 * (cw3 + gap) + cw3 / 2
arrow(s, x3c, ly0, x3c, ly1, color=ACC, head=False)
arrow(s, x3c, ly1, x1c, ly1, color=ACC, head=False)
arrow(s, x1c, ly1, x1c, ly0, color=ACC)
text(s, LM, TOP + 4.75, CW, 0.4, "The tool is not an RDM analysis in itself: it lets a non-technical user carry out "
     "these three components through an agent.", 15, color=MUTED, align=PP_ALIGN.CENTER)

# 5 · Surrogate (left blank on purpose)
s = new_slide("A surrogate stands in for the slow model", "Method · the surrogate",
              "This slide will be prepared by a teammate. Left blank on purpose.")
placeholder(s, LM, TOP + 0.2, CW, 5.0, "[To be prepared by the surrogate team]", 16)

# 6 · Surrogate training details
s = new_slide("The surrogate matches SISEPUEDE: median R² 0.99", "Method · the surrogate",
              "Brief training facts of the XGBoost surrogate the technical tools run. Sources: "
              "metamodel/surrogate_model_sector/retrain_sector.py, utils/ml_utils_v2.py (XGBMultiOutputPipeline), "
              "athena/README.md (rows dropped), trained_models/metrics_<run>_summary.md (scores), "
              "trained_models/split_<run>.csv (which run is in which half). Retrained 2026-10-16.")
bw4 = (CW - 3 * 0.45) / 4
steps = [("100,000 SISEPUEDE runs", "Latin hypercube over 54 levers and 13 uncertainties, each 0–1."),
         ("67 inputs → 258 outputs", "23 emission categories, 16 benefits, 3 cost types and GDP, "
                                     "each for 2025, 2035, 2040, 2050, 2060, 2070"),
         ("XGBoost", "one gradient-boosted tree model per output (scikit-learn MultiOutputRegressor); "
                     "default hyperparameters, no tuning"),
         ("80 / 20 random split", "79,670 runs to train, 19,918 held out to test (seed 42); "
                                  "the split is saved per run id")]
for i, (head, sub) in enumerate(steps):
    x = LM + i * (bw4 + 0.45)
    node(s, x, TOP + 0.15, bw4, 2.0, head, sub, fill=FILL if i == 0 else WHITE, head_pt=14, sub_pt=11,
         align=PP_ALIGN.LEFT)
    if i < 3:
        arrow(s, x + bw4 + 0.05, TOP + 1.15, x + bw4 + 0.4, TOP + 1.15)
text(s, LM, TOP + 2.5, CW, 0.3, "Accuracy on the held-out runs · median R², 2035–2070 (215 outputs)", 15,
     color=TXT, bold=True, font=HEAD)
bw5 = (CW - 4 * 0.3) / 5
for i, (fam, r2) in enumerate([("All outputs", "0.994"), ("Emissions", "0.993"), ("Benefits", "0.996"),
                               ("Costs", "0.990"), ("GDP", "1.000")]):
    node(s, LM + i * (bw5 + 0.3), TOP + 2.95, bw5, 0.95, r2, fam, fill=ACC_LT if i == 0 else WHITE,
         line=ACC if i == 0 else BORDER, head_pt=20, sub_pt=11)
text(s, LM, TOP + 4.15, CW, 1.2,
     "Median error (SMAPE) 1.6%. **15 outputs with R² < 0.8:** fuel production (every year), wetland ecosystem "
     "services, other and not-estimated land conversion (2070).\n"
     "**2025 is left out of the scores:** six years after the 2019 base the outputs barely vary across runs, so R² "
     "is unstable there while the absolute errors stay tiny.", 13, color=MUTED, space_after=6)

# 6 · Ecosystem principles
s = new_slide("Six rules for the agent, its tool use and the tools", "Method · the ecosystem",
              "What were the intentions and rules: the ecosystem should support the three RDM components. Three kinds of rules: "
              "the rules we give the agent, how it can interact with the tools, and the rules for designing the tools "
              "(only one data source per tool).")
cols = [
    ("Rules for the agent", ["Speak the policy maker's language; never ask for 0–1 values",
                             "Ask the user for the failure threshold; never invent it"]),
    ("Rules for its interaction with the tools", ["Every evaluation is an ensemble of futures, never one run",
                                                  "Levers are decided; uncertainties are sampled"]),
    ("Rules for designing the tools", ["One tool answers one question",
                                       "Only one data source per tool"]),
]
cw3 = (CW - 2 * 0.35) / 3
text(s, LM, TOP + 0.05, CW, 0.3, "Intention: support the three RDM components: explore · find vulnerabilities · weigh trade-offs", 15, color=ACC, bold=True,
     align=PP_ALIGN.CENTER, font=HEAD)
for i, (head, rules) in enumerate(cols):
    x = LM + i * (cw3 + 0.35)
    arrow(s, LM + CW / 2, TOP + 0.4, x + cw3 / 2, TOP + 0.9)
    node(s, x, TOP + 0.95, cw3, 0.75, head, fill=ACC_LT, line=ACC, head_pt=16)
    yy = TOP + 2.05
    for r in rules:
        arrow(s, x + cw3 / 2, yy - 0.33, x + cw3 / 2, yy - 0.03)
        node(s, x, yy, cw3, 1.15, None, r, fill=WHITE, sub_pt=15, sub_color=TXT)
        yy += 1.5

# 7 · Architecture
s = new_slide("The agent picks tools; the harness enforces the rules", "Method · the ecosystem",
              "We include the harness, list the tools and talk about the design. The agent decides which tool to use; "
              "the harness never does. A fixed sequence would remove what the experiment measures. There is no "
              "plan step: we measure only the actions the agent takes, from the log.")
cx, colw = LM + 0.3, 4.6
rows6 = [("Policy maker", "Asks in plain language", FILL, BORDER),
         ("Agent (Claude)", "Chooses the tools and their arguments", ACC_LT, ACC),
         ("6 tools", "Deterministic methods, one data source each", WHITE, BORDER),
         ("Data", "Surrogate · SISEPUEDE network · model runs", FILL, BORDER)]
yy = TOP + 0.1
for i, (head, sub, fill, line) in enumerate(rows6):
    node(s, cx, yy, colw, 0.85, head, sub, fill=fill, line=line, head_pt=16, sub_pt=13)
    if i < 3:
        arrow(s, cx + colw / 2 - 0.4, yy + 0.87, cx + colw / 2 - 0.4, yy + 1.23)
        arrow(s, cx + colw / 2 + 0.4, yy + 1.23, cx + colw / 2 + 0.4, yy + 0.87)
    yy += 1.25
# harness frame around agent + tools
rect(s, cx - 0.25, TOP + 1.15, colw + 0.5, 2.25, fill=None, line=ACC, dash=True, line_w=1.25)
text(s, cx - 0.2, TOP + 3.43, 2.5, 0.3, "HARNESS", 11, color=ACC, bold=True, font=HEAD)
# harness functions on the right
rx = LM + 6.2
rw = LM + CW - rx
text(s, rx, TOP + 0.1, rw, 0.35, "What the harness does", 16, color=TXT, bold=True, font=HEAD)
fns = [("State", "Keeps ensembles and pass / fail labels by id, so tools chain safely"),
       ("Rules", "Levers within the range run · no X fixed at one value · a threshold before vulnerability"),
       ("Log", "Tool calls, arguments, replies and the final answer, every turn"),
       ("Limits", "Same iterations and timeouts in every condition")]
yy = TOP + 0.6
for head, sub in fns:
    rect(s, rx, yy, rw, 0.95, fill=WHITE, line=BORDER)
    text(s, rx + 0.25, yy, 1.3, 0.95, head, 16, color=ACC, bold=True, anchor=MSO_ANCHOR.MIDDLE, font=HEAD)
    text(s, rx + 1.6, yy, rw - 1.85, 0.95, sub, 14, color=TXT, anchor=MSO_ANCHOR.MIDDLE)
    yy += 1.1
arrow(s, cx + colw + 0.3, TOP + 2.3, rx - 0.1, TOP + 2.3, color=ACC, dash=True)

# 8 · Tools map
s = new_slide("Six tools: one question and one data source each", "Method · the tools",
              "Six tools in three groups. The information tool, model_network, reads the model runs as a network and "
              "tells the agent what a lever moves and what moves an output; it is the treatment. Technical tools run on the surrogate, one per "
              "step of the three RDM components (the small numbers). Context is the country baseline. The crosswalk "
              "(505 emission fields to 23 categories) links the runs to the surrogate.")
groups = [
    ("Information", [("model_network", "What does a lever move? What moves an output?")],
     "SISEPUEDE network (from the code) · values from the runs", True),
    ("Technical", [("exploratory_modeling", "How does it perform across futures?"),
                   ("vulnerability_analysis", "How often does it fail?"),
                   ("scenario_discovery", "Under which conditions does it fail?"),
                   ("trade_off_analysis", "Emissions vs costs?")],
     "Surrogate (XGBoost) · stored ensembles", False),
    ("Context", [("country_context", "What is the country like in the baseline?")],
     "Country baseline", False),
]
tool_comp = {"exploratory_modeling": "1", "vulnerability_analysis": "2", "scenario_discovery": "2",
             "trade_off_analysis": "3"}
gap = 0.5
gw = (CW - 2 * gap) / 3
th, tg = 0.72, 0.12
data_y = TOP + 0.55 + 4 * (th + tg) + 0.4
for i, (head, tools, data, hl) in enumerate(groups):
    x = LM + i * (gw + gap)
    text(s, x, TOP, gw, 0.4, head, 14, color=ACC if hl else TXT, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
    yy = TOP + 0.5
    for name, q in tools:
        node(s, x, yy, gw, th, name, q, fill=ACC_LT if hl else WHITE, line=ACC if hl else BORDER,
             head_pt=15, sub_pt=11, head_font=BODY)
        if name in tool_comp:
            text(s, x + 0.08, yy + 0.04, 0.3, 0.25, tool_comp[name], 11, color=ACC, bold=True, font=HEAD)
        yy += th + tg
    arrow(s, x + gw / 2, data_y - 0.02, x + gw / 2, yy + 0.02)
    node(s, x, data_y, gw, 0.6, data, fill=FILL, line=BORDER, head_pt=13)
    if i == 0:
        arrow(s, x + gw + 0.06, TOP + 0.2, x + gw + gap - 0.06, TOP + 0.2)
text(s, LM, data_y + 0.7, CW, 0.3, "Highlighted: the information tool, where the experiment changes what the agent "
     "receives  ·  1 · 2 · 3 = the RDM component a tool serves", 12, color=MUTED, align=PP_ALIGN.CENTER)

# 8b · What each tool does and does not do
s = new_slide("Each tool has one job, and things it will not do", "Method · the tools",
              "Two families. READ tools describe the 100,000 model runs that already exist; they never compute "
              "anything new. RUN tools compute new results on the surrogate: only exploratory_modeling creates "
              "results, the other three analyse the ensemble it returns. Examples are from the question bank.")
cols = [("Tool", 1.85), ("The question it answers", 2.15), ("You give it", 2.2),
        ("You get back (example)", 3.6), ("It does NOT", 2.33)]
rows = [
    ("model_network", "What does this lever do? What moves this result?", "a node: a lever, an uncertainty, a "
     "variable or a category; a year (optionally a lever, an uncertainty third)",
     "the node, what it is computed from and what it computes, to walk on step by step · v1: values in real "
     "units, e.g. lever 35 takes electric light-duty travel from 50% (BAU) to 72%",
     "run a policy, test across futures, or say how far to push a lever"),
    ("country_context", "What is Uganda like in the model?", "a topic (e.g. agriculture)",
     "the modelled baseline: about 2.4 M ha of cereals in 2050", "give today's statistics or policy effects"),
    ("exploratory_modeling", "What happens if we apply this policy?", "one or more policies as lever levels; "
     "optionally a range for an uncertainty", "emissions and costs in 500 futures: median, range, change vs BAU",
     "report in-between quantities (vehicle-km, hectares) or choose the levels"),
    ("vulnerability_analysis", "How often does it fail?", "a result of exploratory_modeling + the user's "
     "failure threshold", "the share of futures that fail; if no threshold, it asks the user",
     "invent the threshold or say why it fails"),
    ("scenario_discovery", "Under which conditions does it fail?", "a result already labelled pass / fail",
     "the two uncertainties that best explain failure, e.g. \"fails when GDP grows fast\"",
     "predict which future will happen"),
    ("trade_off_analysis", "What does each policy cost for what it cuts?", "a result with two or more policies",
     "emissions vs cost per policy, cost per tonne, which one is dominated", "name a winner"),
]
hy = TOP - 0.05
x = LM
for name, w in cols:
    text(s, x + 0.06, hy, w - 0.12, 0.3, name, 12, color=MUTED, bold=True, font=HEAD)
    x += w
y = hy + 0.38
for i, row in enumerate(rows):
    rh = 1.0 if i == 0 else 0.6
    read = i < 2
    rect(s, LM, y, CW, rh, fill=ACC_LT if read else FILL, line=None)
    x = LM
    for j, ((_, w), cell) in enumerate(zip(cols, row)):
        text(s, x + 0.08, y + 0.05, w - 0.16, rh - 0.1, f"**{cell}**" if j < 2 else cell, 11.5 if j < 2 else 10.5,
             color=TXT if j < 4 else MUTED, anchor=MSO_ANCHOR.MIDDLE, font=BODY)
        x += w
    y += rh + 0.05 + (0.18 if i == 1 else 0)
text(s, LM, 6.68, CW, 0.3,
     "Blue = READ tools: describe the model runs (the experiment changes what model_network shows)   ·   "
     "Grey = RUN tools: new results on the surrogate", 12, color=MUTED, align=PP_ALIGN.CENTER)

# 8c · Which tool for which question
s = new_slide("The type of question sets which tools to use", "Method · the tools",
              "A guide to assign tools to any question, used to set the expected flow of each question in the bank. "
              "Read the question, find the first row that fits, use those tools in that order.")
guide = [
    ("asks what a lever does", ["model_network (lever)"], "e.g. \"What does reducing deforestation change in the model?\""),
    ("asks what moves a result", ["model_network (output)"], "e.g. \"What drives livestock emissions in 2050?\""),
    ("asks about Uganda's baseline", ["country_context"], "e.g. \"How much land is under cereals?\""),
    ("gives a policy as lever levels", ["exploratory_modeling"], "e.g. \"Set reduced deforestation to 0.6 …\""),
    ("gives a policy in real-world units", ["model_network (lever)", "exploratory_modeling"],
     "P50i · \"What if landfills recovered 40% of their gas?\""),
    ("asks for an emissions target", ["model_network (output)", "exploratory_modeling"],
     "AG2 · \"Cut farming and livestock emissions by a quarter\""),
    ("asks whether it holds up / when it fails", ["exploratory_modeling", "vulnerability_analysis",
                                                    "scenario_discovery"], "Q10b · \"Is this policy robust?\""),
    ("compares options", ["exploratory_modeling", "trade_off_analysis"],
     "Q14b · \"Are cleaner cooking fuels better than cutting deforestation?\""),
    ("asks something not in the model", ["no tool: say so"], "B8b · \"What if Uganda built three new dams?\""),
]
qw, tw, tg2 = 3.0, 1.95, 0.22
ex_x = LM + qw + 0.2 + 3 * tw + 2 * tg2 + 0.25
text(s, LM, TOP - 0.05, qw, 0.3, "If the question…", 12, color=MUTED, bold=True, font=HEAD)
text(s, LM + qw + 0.2, TOP - 0.05, 3 * tw, 0.3, "use, in this order", 12, color=MUTED, bold=True, font=HEAD)
text(s, ex_x, TOP - 0.05, LM + CW - ex_x, 0.3, "Example from the bank", 12, color=MUTED, bold=True, font=HEAD)
gh = 0.5
for i, (cond, tools, ex) in enumerate(guide):
    y = TOP + 0.35 + i * (gh + 0.07)
    text(s, LM, y, qw, gh, cond, 13, color=TXT, bold=True, anchor=MSO_ANCHOR.MIDDLE, font=BODY)
    for j, t in enumerate(tools):
        tx = LM + qw + 0.2 + j * (tw + tg2)
        read = t.startswith("model_network") or t == "country_context"
        if t.startswith("no tool"):
            node(s, tx, y, tw, gh, t, fill=WHITE, line=MUTED, head_pt=11, head_color=MUTED, dash=True,
                 italic=True, head_font=BODY)
        else:
            node(s, tx, y, tw, gh, t, fill=ACC_LT if read else FILL, line=ACC if read else BORDER, head_pt=11,
                 head_font=BODY)
        if j < len(tools) - 1:
            arrow(s, tx + tw + 0.02, y + gh / 2, tx + tw + tg2 - 0.02, y + gh / 2)
    text(s, ex_x, y, LM + CW - ex_x, gh, ex, 11, color=MUTED, italic=True, anchor=MSO_ANCHOR.MIDDLE)

# 8a · The SISEPUEDE network and what each tool shows of it
s = new_slide("model_network walks the network one step at a time", "Method · the tools",
              "Top row: the SISEPUEDE pipeline, left to right. A lever (or uncertainty) is a 0-1 value; it sets "
              "input trajectories (model_input). SISEPUEDE computes the in-between variables (vehicle-km, crop area, "
              "fuel demand) and the emissions (505 emission fields); our crosswalk sums them into the 23 inventory "
              "categories the XGBoost predicts.\n"
              "\n"
              "The network behind model_network was read from the SISEPUEDE code (version 1.4.0): one run of the model "
              "with tagged arrays, so every variable written knows which variables it was computed from. A link means "
              "'used to compute'. NemoMod, the electricity optimisation, is one box: its inputs and outputs are known, "
              "not the steps inside.\n"
              "\n"
              "Rows: what each tool shows the agent at each step. Dark = names and, in the v1 arms, values; light = "
              "names only; empty = not read.\n"
              "- Forward, from a lever: what it sets (v1: the input at BAU, middle and top of the range run), then one "
              "step at a time what each variable is used to compute, down to the categories (v1: median and p10-p90 "
              "by the lever's thirds, optionally within an uncertainty's third).\n"
              "- Back, from a category or a variable: what it is computed from, and the levers and uncertainties that "
              "reach it (v1 adds, for a category, each lever's change from its low to its high third). Used in A (what "
              "drives X?) and as the first step of C (which lever can reach this target?).\n"
              "- The technical tools never walk the chain: the XGBoost goes straight from the 0-1 levers and "
              "uncertainties to the 23 categories (plus costs, benefits and GDP).\n"
              "- country_context reads one run, the BAU baseline.\n"
              "\n"
              "Plan, rules and test: metamodel/chatbot_deploy/docs/rdm_network_plan.md. Code: backend/rdm/network/ "
              "(building it) and backend/rdm/tools/network.py (the tool).")
stages = [("Levers & uncertainties", "0–1 values"),
          ("Inputs", "model_input"),
          ("In-between", "model_output"),
          ("Emissions", "505 emission fields"),
          ("Categories", "crosswalk · 23")]
lab_w = 2.0
sg = 0.22
sw = (CW - lab_w - 4 * sg) / 5
sx = [LM + lab_w + i * (sw + sg) for i in range(5)]
hy, hh = TOP + 0.55, 0.8
# SISEPUEDE bracket: from the inputs' outgoing arrow to the end of the emissions
bx0, bx1 = sx[1] + sw + sg / 2, sx[3] + sw
rect(s, bx0, TOP - 0.05, bx1 - bx0, 0.42, fill=WHITE, line=TXT, line_w=1.25)
text(s, bx0, TOP - 0.05, bx1 - bx0, 0.42, "**SISEPUEDE** computes: in-between + emissions", 12, color=TXT,
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, font=HEAD)
for x0 in (bx0, bx1 - 0.001):
    arrow(s, x0, TOP + 0.37, x0, hy - 0.04, color=TXT, head=False)
text(s, sx[4], TOP - 0.05, sw, 0.42, "ours", 12, color=MUTED, italic=True, align=PP_ALIGN.CENTER,
     anchor=MSO_ANCHOR.MIDDLE)
for i, (head, sub) in enumerate(stages):
    node(s, sx[i], hy, sw, hh, head, sub, fill=FILL, line=BORDER, head_pt=13, sub_pt=10)
    if i < 4:
        arrow(s, sx[i] + sw + 0.03, hy + hh / 2, sx[i] + sw + sg - 0.03, hy + hh / 2, color=TXT)
DARK, LIGHT = "dark", "light"
trows = [
    ("model_network", "forward, from a lever",
     [(LIGHT, "the lever or\nuncertainty"), (DARK, "what it sets\nv1: BAU · middle · top"),
      (DARK, "one step at a time\nv1: values by thirds"), (DARK, "unit, gas, sector\nv1: values by thirds"),
      (DARK, "categories reached\nv1: values by thirds")]),
    ("model_network", "back, from a category",
     [(DARK, "② the levers and\nuncertainties\nthat reach it"), "back", "start", "start", "start"]),
    ("4 technical tools", "the XGBoost",
     [(LIGHT, "policy levels +\nsampled futures"), "skip", "skip", "skip",
      (LIGHT, "predicted, + costs,\nbenefits, GDP")]),
    ("country_context", "one run: BAU",
     [None, (LIGHT, "BAU values: mode\nshares, energy mix"), (LIGHT, "BAU values: GDP,\npopulation, crops"), None, None]),
]
ry, rh, rg = hy + hh + 0.25, 0.68, 0.1
for name, sub, cells in trows:
    text(s, LM, ry, lab_w - 0.15, rh, f"**{name}**\n{sub}", 13, color=TXT, anchor=MSO_ANCHOR.MIDDLE)
    for i, c in enumerate(cells):
        if c in ("skip", "back", "start"):
            continue
        if c is None:
            rect(s, sx[i], ry, sw, rh, fill=None, line=BORDER, dash=True)
            continue
        kind, label = c
        rect(s, sx[i], ry, sw, rh, fill=ACC_LT if kind == DARK else FILL, line=ACC if kind == DARK else BORDER)
        text(s, sx[i] + 0.08, ry, sw - 0.16, rh, label, 12, color=TXT, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if "back" in cells:     # read right to left: ① the agent names a category, ② it gets the levers
        x0, x1 = sx[2], sx[4] + sw
        rect(s, x0, ry, x1 - x0, rh, fill=FILL, line=BORDER)
        text(s, x0 + 0.15, ry, x1 - x0 - 0.3, rh, "① starts here: the agent names a category or a variable\n"
             "and steps back through what it is computed from", 12, color=TXT, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
        arrow(s, x0 - 0.03, ry + rh / 2, sx[0] + sw + 0.03, ry + rh / 2, color=ACC, width=2)
    if "skip" in cells:
        x0, x1 = sx[1], sx[3] + sw
        rect(s, x0, ry + 0.12, x1 - x0, rh - 0.24, fill=None, line=MUTED, dash=True)
        text(s, x0, ry, x1 - x0, rh, "skips the chain: straight from 0–1 values to categories", 12, color=MUTED,
             italic=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        arrow(s, sx[0] + sw + 0.03, ry + rh / 2, sx[1] - 0.03, ry + rh / 2, color=MUTED, head=False)
        arrow(s, x1 + 0.03, ry + rh / 2, sx[4] - 0.03, ry + rh / 2, color=MUTED)
    ry += rh + rg
ly = ry + 0.0
rect(s, LM, ly + 0.04, 0.3, 0.2, fill=ACC_LT, line=ACC)
text(s, LM + 0.4, ly, 2.6, 0.3, "names, + values in the v1 arms", 12, color=MUTED)
rect(s, LM + 3.1, ly + 0.04, 0.3, 0.2, fill=FILL, line=BORDER)
text(s, LM + 3.5, ly, 1.4, 0.3, "names only", 12, color=MUTED)
rect(s, LM + 4.85, ly + 0.04, 0.3, 0.2, fill=None, line=BORDER, dash=True)
text(s, LM + 5.25, ly, 1.2, 0.3, "not read", 12, color=MUTED)
text(s, LM + 6.5, ly, CW - 6.5, 0.3, "Links read from the SISEPUEDE code · NemoMod (electricity) is one box",
     12, color=ACC, bold=True, align=PP_ALIGN.RIGHT)

# 8a2 · What each arm receives while walking the network (one example, lever 35)
s = new_slide("Both arms walk the same network; only v1 sees numbers", "Method · the tools",
              "One example, read left to right. Top: a piece of the real network around lever 35 (shift light-duty "
              "vehicles to other fuels) and uncertainty X57 (GDP growth), in the five levels of the network. The "
              "highlighted path is what an agent walks: each numbered step is one model_network call, and the next "
              "node is a name taken from the previous reply.\n"
              "\n"
              "Bottom: what the reply holds at each step. v0 gets the map: names, units, sectors and links (what a "
              "node is computed from and what it computes). v1 gets the same map plus numbers from the 4,989 model "
              "runs: what a lever level means in real units, and medians (p10-p90) with the lever in its low third "
              "(0-1/3) and high third (2/3-1), optionally only in futures where an uncertainty is low, middle or high.\n"
              "\n"
              "Numbers are 2050, from the tool itself: diesel share 0.174 -> 0.098 and electric share 0.50 -> 0.72 (BAU "
              "-> top of the range run); diesel vehicle-km 8.96 -> 7.36 billion; CO2 from transport 9.70 -> 8.98 Mt; "
              "Transportation category 9.89 -> 9.10 Mt (p10-p90 7.59-12.99 at lever low), with GDP high 11.49 -> 10.44 "
              "Mt. The electric chain goes to NemoMod, one box for the electricity system.")
lab = 1.45
g5 = 0.26
c5 = (CW - lab - 4 * g5) / 5
cx = [LM + lab + i * (c5 + g5) for i in range(5)]
levels = [("Lever / uncertainty", "a 0–1 value"), ("Inputs", "set by the lever"), ("In-between", "SISEPUEDE computes"),
          ("Emissions", "SISEPUEDE computes"), ("Categories", "the XGBoost predicts")]
for i, (h, sub) in enumerate(levels):
    text(s, cx[i], TOP - 0.12, c5, 0.28, h, 13, color=TXT, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
    text(s, cx[i], TOP + 0.13, c5, 0.25, sub, 10.5, color=MUTED, align=PP_ALIGN.CENTER, font=HEAD)
    if i < 4:
        arrow(s, cx[i] + c5 + 0.04, TOP + 0.05, cx[i + 1] - 0.04, TOP + 0.05, color=BORDER, width=1)
text(s, LM, TOP + 0.5, lab - 0.15, 1.9, "**The network**\nsame in v0 and v1", 12, color=TXT, font=HEAD,
     anchor=MSO_ANCHOR.MIDDLE)

nh = 0.4
r1, r2, r3 = TOP + 0.55, TOP + 1.12, TOP + 1.75
nodes_fig = {   # key: (column, row y, label, style)
    "L35": (0, r1, "L35 · light-duty fuel shift", "path"),
    "X57": (0, r2, "X57 · GDP growth", "x"),
    "dsh": (1, r1, "Diesel share of car km", "path"),
    "esh": (1, r3, "Electric share of car km", "plain"),
    "gdp": (1, r2, "GDP", "plain"),
    "dvk": (2, r1, "Diesel vehicle-km", "path"),
    "evk": (2, r3, "Electric vehicle-km", "plain"),
    "pkm": (2, r2, "Passenger-km demand", "plain"),
    "co2": (3, r1, "CO₂ from transport", "path"),
    "nem": (3, r3, "NemoMod (electricity box)", "box"),
    "trn": (4, r1, "Transportation", "path"),
    "ele": (4, r3, "Electricity generation", "plain"),
}
for key, (c, y, label, style) in nodes_fig.items():
    fill, line, col = (ACC_LT, ACC, TXT) if style == "path" else (TXT, TXT, WHITE) if style == "box" else (WHITE, BORDER, TXT)
    rect(s, cx[c], y, c5, nh, fill=fill, line=line, dash=style == "x", line_w=1.5 if style == "path" else 1.0)
    text(s, cx[c] + 0.05, y, c5 - 0.1, nh, label, 11, color=col, bold=style == "path", align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE, font=HEAD)
links_fig = [("L35", "dsh", True), ("L35", "esh", False), ("dsh", "dvk", True), ("esh", "evk", False),
             ("X57", "gdp", False), ("gdp", "pkm", False), ("pkm", "dvk", False), ("pkm", "evk", False),
             ("dvk", "co2", True), ("evk", "nem", False), ("co2", "trn", True), ("nem", "ele", False)]
for a, b, hot in links_fig:
    (ca, ya, _, _), (cb, yb, _, _) = nodes_fig[a], nodes_fig[b]
    if ca == cb:        # within the in-between level: a short vertical arrow
        x = cx[ca] + c5 / 2
        arrow(s, x, ya - 0.02 if yb < ya else ya + nh + 0.02, x, yb + nh + 0.02 if yb < ya else yb - 0.02,
              color=MUTED, width=1.0)
    else:
        arrow(s, cx[ca] + c5 + 0.03, ya + nh / 2, cx[cb] - 0.03, yb + nh / 2, color=ACC if hot else MUTED,
              width=2.25 if hot else 1.0)
for n, key in enumerate(["L35", "dsh", "dvk", "co2", "trn"], start=1):
    c, y, _, _ = nodes_fig[key]
    b = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx[c] - 0.13), Inches(y - 0.13), Inches(0.28), Inches(0.28))
    b.fill.solid(); b.fill.fore_color.rgb = ACC; b.line.fill.background()
    tf = b.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run_ = p.add_run(); run_.text = str(n); run_.font.size = Pt(11); run_.font.bold = True
    run_.font.color.rgb = WHITE; run_.font.name = HEAD
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
text(s, cx[1], r3 + nh + 0.04, cx[4] + c5 - cx[1], 0.28, "① – ⑤ = one model_network call each; the next node is a "
     "name from the last reply", 11, color=ACC, italic=True, align=PP_ALIGN.RIGHT, font=HEAD)

rows_fig = [
    ("v0 receives", "the map: names, units, links", WHITE, BORDER, [
        "**①** sets 4 fuel shares\nreaches 99 variables and 5 categories",
        "**②** fraction (0–1) · Transportation\nused to compute: vehicle-km by fuel …",
        "**③** vehicle-km\ncomputed from: shares, passenger-km …",
        "**④** Mt CO₂e · gas CO₂\nused to compute: Transportation",
        "**⑤** metric emissions_transportation\nlevers that reach it: L31 – L42"]),
    ("v1 also receives", "the numbers from the runs", ACC_LT, ACC, [
        "what a level means:\nelectric share **50% → 72%**\n(BAU → top of the range)",
        "diesel share\n**17% → 10%**\n(BAU → top of the range)",
        "**8.96 → 7.36 bn km**\nlever low → high",
        "**9.70 → 8.98 Mt**\nlever low → high",
        "**9.9 → 9.1 Mt** (p10–p90 7.6–13.0)\nwith GDP high: **11.5 → 10.4 Mt**"]),
]
ry, rh = TOP + 2.72, 1.05
for head, sub, fill, line, cells in rows_fig:
    text(s, LM, ry, lab - 0.15, rh, f"**{head}**\n{sub}", 12, color=ACC if fill == ACC_LT else TXT, font=HEAD,
         anchor=MSO_ANCHOR.MIDDLE)
    for i, cell in enumerate(cells):
        rect(s, cx[i], ry, c5, rh, fill=fill, line=line)
        text(s, cx[i] + 0.08, ry, c5 - 0.16, rh, cell, 11.5, color=TXT, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
    ry += rh + 0.14
text(s, LM, ry - 0.08, CW, 0.28, "Same prompt, same tool, same calls in both arms · numbers: 2050, medians from 4,989 "
     "model runs, lever low (0–⅓) → high (⅔–1)", 11, color=MUTED, italic=True, align=PP_ALIGN.CENTER, font=HEAD)

# 8b · What each tool reads
s = new_slide("Tools read the network, the surrogate or the baseline", "Method · the tools",
              "Where to find each piece (paths from the repo root, ssp_uganda_data/; branch rdm-tools).\n"
              "\n"
              "model_network: metamodel/chatbot_deploy/backend/rdm/tools/network.py (information.py hands it on)\n"
              "  1 Network: backend/rdm/network/out/run_2026_05_30_nodes.csv and _edges.csv (built by inventory.py, "
              "trace.py, static.py, assemble.py in backend/rdm/network/)\n"
              "  2 Attributes: backend/rdm/network/out/run_2026_05_30_node_attributes.csv and _field_attributes.csv "
              "(attributes.py)\n"
              "  3 What a lever sets: backend/rdm/data/tables/run_2026_05_30_lever_inputs.csv (data/lever_inputs.py)\n"
              "  4 Values: backend/rdm/network/out/run_2026_05_30_ranges.parquet (ranges.py), from the cached sample "
              "of 4,989 runs (decomposed_emissions, model_output, model_input from S3 "
              "s3://sisepuede-data/run_database/sisepuede_run_2026-05-30t21;35;56.244639/)\n"
              "  Which arm sees which values: ARMS in backend/rdm/tools/network.py\n"
              "\n"
              "Technical tools: metamodel/chatbot_deploy/backend/rdm/tools/technical.py, surrogate wrapper "
              "backend/rdm/surrogate.py, model "
              "metamodel/surrogate_model_sector/trained_models/xgb_pipeline_sector_independent_2026-05-30t21;35;56.244639.pkl, "
              "ensembles kept in backend/rdm/harness/state.py\n"
              "\n"
              "country_context: metamodel/chatbot_deploy/backend/rdm/tools/context.py, wrapping "
              "backend/services/context.py (BAU row, primary_id 0, from S3)\n"
              "\n"
              "All paths for the run are set in one manifest: metamodel/chatbot_deploy/backend/rdm/runs/run_2026_05_30.yaml")
cols9 = [("Tool", 2.55), ("What it reads", 5.75), ("Where it comes from", CW - 2.55 - 5.75)]
rows9 = [
    ("model_network", "Information · treatment",
     "1 · The network: 804 nodes, 4,379 links read from the SISEPUEDE code\n"
     "2 · Node attributes: name, unit, sector, gas, XGBoost category\n"
     "3 · What a lever sets: the input at BAU · middle · top of the range\n"
     "4 · Values: p10–median–p90 by lever third × uncertainty third, every year",
     "A traced run of the SISEPUEDE code (links) + 4,989 sampled runs (values)\nv0: 1, 2 · v1: adds 3, 4",
     True, 1.6),
    ("4 technical tools", "exploratory · vulnerability · scenarios · trade-offs",
     "The XGBoost surrogate: 67 levers and uncertainties (0–1) → 258 outputs × 6 years.\n"
     "Ensembles and pass / fail labels kept by id in the harness",
     "Trained surrogate (.pkl) + its target list", False, 1.0),
    ("country_context", "Context",
     "Uganda's BAU baseline: energy mix, GDP, population, agriculture, transport",
     "One BAU run (primary_id 0) read from S3", False, 0.7),
]
x = LM
for head, w in cols9:
    text(s, x + 0.15, TOP - 0.05, w - 0.3, 0.3, head, 13, color=MUTED, bold=True, font=HEAD)
    x += w
yy = TOP + 0.35
for name, kind, reads, src, hl, rh in rows9:
    rect(s, LM, yy, CW, rh, fill=ACC_LT if hl else WHITE, line=ACC if hl else BORDER)
    x = LM
    text(s, x + 0.2, yy, cols9[0][1] - 0.3, rh, f"**{name}**\n{kind}", 13, color=TXT, anchor=MSO_ANCHOR.MIDDLE)
    x += cols9[0][1]
    text(s, x + 0.1, yy, cols9[1][1] - 0.25, rh, reads, 13, color=TXT, anchor=MSO_ANCHOR.MIDDLE)
    x += cols9[1][1]
    text(s, x + 0.1, yy, cols9[2][1] - 0.25, rh, src, 12, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)
    yy += rh + 0.12
text(s, LM, yy + 0.02, CW, 0.3, "File paths for every item are in the speaker notes", 12, color=MUTED,
     italic=True, align=PP_ALIGN.CENTER)

# 8c · How the network was built
s = new_slide("The network is read from the code and tested on runs", "Method · the tools",
              "How the network behind model_network was built (full log: metamodel/chatbot_deploy/docs/"
              "rdm_network_plan.md; code: backend/rdm/network/).\n"
              "\n"
              "1 INVENTORY. Every model variable from SISEPUEDE's variable definition tables (714), expanded to its "
              "fields and joined to the run's AWS columns: 100% of model_input (2,441) and model_output (1,025) "
              "columns map to a model variable, 97.6% of decomposed_emissions (the misses are subsector totals). "
              "Attributes: unit, sector, subsector, gas, XGBoost category. (inventory.py, attributes.py)\n"
              "\n"
              "2 TRACE THE CODE. SISEPUEDE 1.4.0 run once on the Uganda base input, with electricity. Every array read "
              "for a variable carries its name; NumPy operations merge the names; every variable written records the "
              "names its array carries = the variables it was computed from. Rules: relations only; edges only from "
              "the code; NemoMod is one box (every input and output of the subsectors it solves); the coupled land use / "
              "crops / livestock loop is one step. (trace.py, static.py, assemble.py)\n"
              "\n"
              "3 TEST ON THE RUNS. The 4,568 lever or uncertainty -> output links seen in the runs (|Spearman rho| >= "
              "0.10 or SISEPUEDE's structural map): 93.9% have a path in the network (levers -> emissions 97.8%). Not "
              "trivially connected: a lever reaches a median 27% of the outputs. Spot checks read right (L35 fuel "
              "fractions -> vehicle-km by fuel -> transport emissions; L15 land use transitions -> conversion CO2). "
              "Gaps: L12 (its input is never read in the traced run); 9 outputs with no link.\n"
              "\n"
              "4 VALUES (v1 only). From the 4,989 sampled runs, every anchor year: median and p10-p90 of every field a "
              "lever reaches, by the lever's thirds, and within each uncertainty's thirds (low, middle, high: every "
              "run falls in one). Inputs a lever sets: exact, at BAU, middle and top of the range run. (ranges.py)")
chain = [
    ("Inventory", "variables and fields",
     "714 SISEPUEDE variables from its definition tables\n"
     "100% of input and output columns in AWS map to one\n"
     "**Attributes:** unit, sector, gas, XGBoost category"),
    ("Trace the code", "one run, tagged arrays",
     "SISEPUEDE run once, with electricity\n"
     "Every array carries the variables it was computed from\n"
     "**Link** = used to compute\n"
     "NemoMod = one box"),
    ("Test on the runs", "is there a path?",
     "4,568 lever / uncertainty → output links seen in the runs\n"
     "**93.9%** have a path (levers → emissions 97.8%)\n"
     "A lever reaches a median 27% of outputs"),
    ("Values", "v1 only",
     "4,989 sampled runs, every year\n"
     "Median, p10–p90 by lever third × uncertainty third\n"
     "Lever inputs: exact, BAU · middle · top"),
]
gap = 0.35
cw4 = (CW - 3 * gap) / 4
for i, (head, sub, body) in enumerate(chain):
    x = LM + i * (cw4 + gap)
    text(s, x, TOP - 0.05, cw4, 0.3, str(i + 1), 14, color=ACC, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
    node(s, x, TOP + 0.3, cw4, 0.85, head, sub, fill=ACC_LT, line=ACC, head_pt=15, sub_pt=12)
    if i < 3:
        arrow(s, x + cw4 + 0.05, TOP + 0.72, x + cw4 + gap - 0.05, TOP + 0.72, color=ACC)
    rect(s, x, TOP + 1.35, cw4, 2.35, fill=WHITE, line=BORDER)
    text(s, x + 0.18, TOP + 1.5, cw4 - 0.36, 2.1, body, 13, color=TXT, space_after=5)
text(s, LM, TOP + 3.9, CW, 0.3, "Relations, not causality: a link means a variable is used to compute another  ·  "
     "rules and full test in the speaker notes", 12, color=MUTED, italic=True, align=PP_ALIGN.CENTER)

# 9 · Questions
s = new_slide("We test the agent on six types of policy question", "Experiment · questions",
              "The categories, and for each: what tools we expect the agent to use vs what it actually uses. "
              "Example questions from the draft question bank. Shown before the flows so the categories are known when "
              "we walk through how the agent moves. The number in the corner is the RDM component the category "
              "exercises; A supports all three and F is outside the model.")
cat_comp = {1: "1", 2: "3", 3: "2", 4: "3"}
cats = [("A · Information", "\"What drives Uganda's emissions from forest land in 2050?\""),
        ("B · Evaluate a policy", "\"What if Uganda's landfills recovered 40% of their landfill gas by 2050?\""),
        ("C · Reach a target", "\"Which policies could cut farming and livestock emissions by a quarter by 2050?\""),
        ("D · Robustness", "\"Under which conditions does this policy fail, and why?\""),
        ("E · Compare", "\"Are cleaner cooking fuels better than cutting deforestation?\""),
        ("F · Outside the model", "\"What if Uganda built three new large hydropower dams?\"")]
cw3 = (CW - 2 * 0.3) / 3
for i, (head, q) in enumerate(cats):
    r, c = divmod(i, 3)
    node(s, LM + c * (cw3 + 0.3), TOP + r * 1.2, cw3, 1.0, head, q, fill=WHITE, head_pt=14, sub_pt=12,
         align=PP_ALIGN.LEFT)
    if i in cat_comp:
        text(s, LM + c * (cw3 + 0.3) + cw3 - 0.4, TOP + r * 1.2 + 0.06, 0.3, 0.25, cat_comp[i], 11, color=ACC,
             bold=True, align=PP_ALIGN.RIGHT, font=HEAD)
fy = TOP + 2.75
text(s, LM, fy, CW, 0.3, "For every question", 15, color=TXT, bold=True, font=HEAD)
fy += 0.45
bw = 2.6
node(s, LM, fy + 0.55, bw, 0.9, "Question", "from one category", fill=FILL, head_pt=14, sub_pt=12)
ex, ey = LM + bw + 0.6, fy
node(s, ex, ey, 3.6, 0.9, "Expected", "tools + parameters (set in advance)", fill=WHITE, head_pt=14, sub_pt=12)
node(s, ex, ey + 1.1, 3.6, 0.9, "Observed", "tools called + parameters (from the log)", fill=WHITE, head_pt=14, sub_pt=12)
arrow(s, LM + bw + 0.05, fy + 1.0, ex - 0.05, ey + 0.45)
arrow(s, LM + bw + 0.05, fy + 1.0, ex - 0.05, ey + 1.55)
mx = ex + 3.6 + 0.6
mw = LM + CW - mx
node(s, mx, fy + 0.1, mw, 1.8, "Compare",
     "Routing: expected vs called tools\nParameters: levers, X ranges, thresholds\nAnswer: what it tells the user",
     fill=ACC_LT, line=ACC, head_pt=14, sub_pt=12, align=PP_ALIGN.LEFT)
arrow(s, ex + 3.65, ey + 0.45, mx - 0.05, fy + 1.0)
arrow(s, ex + 3.65, ey + 1.55, mx - 0.05, fy + 1.0)

# 10 · How the agent moves through the tools
s = new_slide("Each question type has an expected path through tools", "Experiment · questions",
              "Expected flow per question category, set in advance and compared with the tools the agent actually "
              "calls. There is no plan step. In D the agent asks the user which value counts as failure before the "
              "vulnerability analysis. Same rules as the slide 'Which tool for which question'; a question can mix "
              "rows (e.g. a target in real units: model_network from the lever, then exploratory_modeling).")
flows = [   # the same rules as the "Which tool for which question" slide
    ("A · Information", ["one READ tool", "answer"]),
    ("B · Evaluate", ["model_network: lever (if real units)", "exploratory_modeling", "answer"]),
    ("C · Reach target", ["model_network: output", "exploratory_modeling (try levels)", "answer"]),
    ("D · Robustness", ["exploratory_modeling", "user sets threshold", "vulnerability_analysis", "scenario_discovery"]),
    ("E · Compare", ["exploratory_modeling", "trade_off_analysis", "answer"]),
    ("F · Outside", ["decline or clarify"]),
]
knowledge = {"model_network: output", "one READ tool", "model_network: lever (if real units)"}
dialogue = {"answer", "user sets threshold", "decline or clarify"}
lw = 1.85
sx = LM + lw + 0.25
sw = (LM + CW - sx - 4 * 0.26) / 5
rh, rg = 0.6, 0.16
yy = TOP + 0.1
for cat, chain in flows:
    node(s, LM, yy, lw, rh, cat, fill=WHITE, line=None, head_pt=13, align=PP_ALIGN.LEFT)
    for j, step in enumerate(chain):
        x = sx + j * (sw + 0.26)
        if step in dialogue:
            node(s, x, yy, sw, rh, step, fill=WHITE, line=MUTED, head_pt=11.5, head_color=MUTED,
                 dash=True, italic=True, head_font=BODY)
        else:
            hl = step in knowledge
            node(s, x, yy, sw, rh, step, fill=ACC_LT if hl else FILL, line=ACC if hl else BORDER, head_pt=11.5,
                 head_font=BODY)
        if j < len(chain) - 1:
            arrow(s, x + sw + 0.03, yy + rh / 2, x + sw + 0.23, yy + rh / 2)
    yy += rh + rg
lg = yy + 0.05
rect(s, LM, lg + 0.05, 0.3, 0.2, fill=ACC_LT, line=ACC)
text(s, LM + 0.4, lg, 3, 0.3, "Information tool (treatment)", 12, color=MUTED)
rect(s, LM + 3.2, lg + 0.05, 0.3, 0.2, fill=FILL, line=BORDER)
text(s, LM + 3.6, lg, 2.5, 0.3, "Technical tool", 12, color=MUTED)
rect(s, LM + 5.2, lg + 0.05, 0.3, 0.2, fill=WHITE, line=MUTED, dash=True)
text(s, LM + 5.6, lg, 3, 0.3, "Dialogue step, not a tool", 12, color=MUTED)

# 11 · Data
s = new_slide("The treatment: v0 sees relations, v1 also sees values", "Experiment · data",
              "Here we list our data sets and highlight the data we provide as the experiment: the relations and values "
              "from the model runs. v0 and v1 use the same prompt and the same 6 tools; only what the information "
              "tool returns changes. v0 gets the relations (the network read from the SISEPUEDE code: which variable "
              "is computed from which, from the lever to the emission categories, with units and sectors); v1 adds "
              "how much (medians and p10-p90 from the runs, by lever third and uncertainty third, every year).")
data = [
    ("SISEPUEDE network", "804 nodes, 4,379 links read from the model code", "know"),
    ("Crosswalk", "505 emission fields → 23 inventory categories", "know"),
    ("Model runs (sample)", "4,989 runs: emissions, variables and inputs", "know"),
    ("Values table", "Per lever third × uncertainty third, every year", "know"),
    ("XGBoost surrogate", "67 L/X → 258 outputs, 6 years", "exp"),
    ("Country baseline", "Uganda's modelled baseline", "ctx"),
]
dx, dw, dh, dg = LM, 4.1, 0.68, 0.1
ys = {}
yy = TOP + 0.45
text(s, dx, TOP, dw, 0.35, "Data sets", 15, color=TXT, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
for head, sub, k in data:
    hl = k == "know"
    node(s, dx, yy, dw, dh, head, sub, fill=ACC_LT if hl else WHITE, line=ACC if hl else BORDER, head_pt=14, sub_pt=12)
    ys.setdefault(k, []).append(yy + dh / 2)
    yy += dh + dg
tx, tw = LM + 5.0, 2.9
text(s, tx, TOP, tw, 0.35, "Tools that read them", 15, color=TXT, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
for k, label in [("know", "Information tool"), ("exp", "Technical tools"), ("ctx", "Context")]:
    cy = sum(ys[k]) / len(ys[k])
    hl = k == "know"
    node(s, tx, cy - 0.32, tw, 0.64, label, fill=ACC_LT if hl else FILL, line=ACC if hl else BORDER, head_pt=14)
    for y0 in ys[k]:
        arrow(s, dx + dw + 0.05, y0, tx - 0.05, cy)
vx = LM + 8.55
vw = LM + CW - vx
kc = sum(ys["know"]) / len(ys["know"])
text(s, vx, TOP, vw, 0.35, "The treatment", 15, color=ACC, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
node(s, vx, TOP + 0.45, vw, 1.45, "v0 · relations",
     "Which variable is computed from which:\n\"Lever 35 sets the light-duty fuel fractions, which compute vehicle-km by fuel.\"",
     fill=WHITE, head_pt=14, sub_pt=12)
node(s, vx, TOP + 2.2, vw, 1.45, "v1 · relations + values",
     "How much, by lever and uncertainty thirds:\n\"Electric vehicle-km: 17.7 → 22.6 billion as the lever goes low → high; 25.4 with GDP high.\"",
     fill=ACC_LT, line=ACC, head_pt=14, sub_pt=12)
arrow(s, tx + tw + 0.05, kc, vx - 0.05, TOP + 1.2, color=ACC)
arrow(s, tx + tw + 0.05, kc, vx - 0.05, TOP + 2.9, color=ACC)
text(s, vx, TOP + 3.85, vw, 0.9, "Same prompt and same 6 tools in both; only this changes.", 13, color=MUTED,
     align=PP_ALIGN.CENTER)

# 12 · Surrogate interaction
s = new_slide("We compare the variables and magnitudes v0 and v1 set", "Experiment · interaction",
              "What variables we expect the agent to select (sectors) vs what it selects; and how the magnitudes "
              "change when there is more information, i.e. with the treatment.")
qx, qw = LM, 2.2
node(s, qx, TOP + 1.55, qw, 1.1, "Same question", "asked to both versions", fill=FILL, head_pt=15, sub_pt=12)
ax, aw = LM + 2.75, 2.3
rx, rw = LM + 5.6, 3.0
for yb, head, sub, hl in [(TOP + 0.3, "v0 agent", "names only", False),
                          (TOP + 2.8, "v1 agent", "values across L and X", True)]:
    node(s, ax, yb, aw, 1.0, head, sub, fill=ACC_LT if hl else WHITE, line=ACC if hl else BORDER,
         head_pt=15, sub_pt=12)
    arrow(s, qx + qw + 0.05, TOP + 2.1, ax - 0.05, yb + 0.5)
    node(s, rx, yb, rw, 1.0, "What it chooses", "variables (sectors) selected\nmagnitudes set: lever levels, X ranges",
         fill=WHITE, head_pt=14, sub_pt=12)
    arrow(s, ax + aw + 0.05, yb + 0.5, rx - 0.05, yb + 0.5)
cx2 = rx + rw + 0.6
cw2 = LM + CW - cx2
node(s, cx2, TOP + 0.3, cw2, 3.5, "Compare v0 vs v1",
     "1 · Variables: expected sectors vs the ones it selects\n\n2 · Magnitudes: how they move when the agent has more information",
     fill=ACC_LT, line=ACC, head_pt=15, sub_pt=13, align=PP_ALIGN.LEFT)
arrow(s, rx + rw + 0.05, TOP + 0.8, cx2 - 0.05, TOP + 1.6)
arrow(s, rx + rw + 0.05, TOP + 3.3, cx2 - 0.05, TOP + 2.5)
node(s, cx2, TOP + 4.35, cw2, 0.8, "Expected selection", "set in advance per question", fill=FILL, head_pt=14, sub_pt=12)
arrow(s, cx2 + cw2 / 2, TOP + 4.32, cx2 + cw2 / 2, TOP + 3.83)

# 13 · Results
s = new_slide("Results: [one-line finding, after the runs]", "Results",
              "To fill after the runs: one answer per research question, then what it means for DMDU practice.")
cw3 = (CW - 2 * 0.4) / 3
for i, (head, body) in enumerate([
        ("RQ1 · The ecosystem", "[Can policy questions be explored through the three RDM components with the system, and how well does the evaluation catch its errors?]"),
        ("RQ2 · Information given", "[How seeing values (v1) changes tool use, policy levels and uncertainty ranges compared with relations only (v0)]"),
        ("For DMDU practice", "[What this means for putting AI between models and decision makers]")]):
    x = LM + i * (cw3 + 0.4)
    text(s, x, TOP + 0.2, cw3, 0.4, head, 16, color=TXT, bold=True, font=HEAD)
    placeholder(s, x, TOP + 0.75, cw3, 3.6, body, 14)
    if i < 2:
        arrow(s, x + cw3 + 0.06, TOP + 2.55, x + cw3 + 0.34, TOP + 2.55)

# ═════════════════════════════════════════════════════════════════════════════
# Appendix · the harness text, word for word (not presented; for review of the instructions)
APX = "Appendix · not presented"


def _lines(p, cpl):
    return max(1, math.ceil(len(p.replace("**", "")) / cpl))


def flow(title, paras, ncols=2, pt=10.5, notes=None):
    """Pour paragraphs into columns, continuing on new slides when they fill up."""
    gap = 0.35
    col_w = (CW - (ncols - 1) * gap) / ncols
    col_h = 7.0 - TOP - 0.05
    cpl = col_w * 72 / (pt * 0.46)
    cap = col_h * 72 / (pt * 1.25)
    cols, cur, used = [], [], 0.0
    for p in paras:
        n = _lines(p, cpl) + 0.35
        if cur and used + n > cap:
            cols.append(cur)
            cur, used = [], 0.0
        cur.append(p)
        used += n
    cols.append(cur)
    for k in range(0, len(cols), ncols):
        page = k // ncols
        s = new_slide(title + (" (cont.)" if page else ""), APX, notes)
        for c, col in enumerate(cols[k:k + ncols]):
            text(s, LM + c * (col_w + gap), TOP - 0.05, col_w, col_h, "\n".join(col), pt, space_after=3)


def prompt_paras(block):
    out = []
    for ln in block.split("\n"):
        if not ln.strip():
            continue
        out.append(f"**{ln[3:]}**" if ln.startswith("## ") else ("• " + ln[2:] if ln.startswith("- ") else ln))
    return out


src_note = ("Word for word what the agent receives, from the code (snapshot in backend/rdm/deck/harness_text.json, "
            "written by backend/rdm/deck/dump_harness_text.py). Not part of the talk.")

# A1 · What the harness is made of
s = new_slide("Appendix: the text of the harness", APX, src_note)
text(s, LM, TOP, CW, 0.5, "Not part of the presentation. Everything the agent is told, word for word, for review "
     "of the instructions.", 15, color=ACC, bold=True, font=HEAD)
parts = [("System prompt", "method, how the model is organised, the tools, the rules, the catalogue · identical "
          "in every arm", "harness/prompt.py"),
         ("Tool descriptions", "the 6 tools and their parameters, as the agent sees them · identical in every arm",
          "harness/registry.py"),
         ("The loop and the scripted user", "model, limits, when the scripted user replies and with what",
          "harness/agent.py · eval/questions.py"),
         ("Rules checked in code", "the messages the tools return when a call breaks a rule",
          "tools/technical.py · information.py · common.py"),
         ("Fixed text inside the replies", "notes and requests the tools add to their results",
          "tools/*.py")]
for i, (head, sub, path) in enumerate(parts):
    y = TOP + 0.75 + i * 0.95
    node(s, LM, y, 3.6, 0.78, head, fill=ACC_LT if i < 2 else WHITE, line=ACC if i < 2 else BORDER, head_pt=14)
    text(s, LM + 3.9, y + 0.1, 5.6, 0.6, sub, 13, color=TXT, anchor=MSO_ANCHOR.MIDDLE)
    text(s, LM + 9.7, y + 0.1, CW - 9.7, 0.6, path, 11, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)

# A2 · System prompt, then the catalogue it lists
body, cat = HARNESS["system_prompt"].split("## Catalogue")
flow("System prompt", prompt_paras(body), ncols=2, pt=10, notes=src_note)
flow("System prompt: the catalogue (end of the prompt)", prompt_paras(cat), ncols=4, pt=7.5, notes=src_note)


# A3 · Tool descriptions
def param_line(name, spec, required):
    kind = spec.get("type", "")
    extra = f"; one of: {', '.join(map(str, spec['enum']))}" if "enum" in spec else ""
    req = ", required" if name in required else ""
    desc = spec.get("description", "")
    return f"   • **{name}** ({kind}{req}{extra}){': ' + desc if desc else ''}"


paras = []
for t in HARNESS["tools"]:
    sch = t["input_schema"]
    paras.append(f"**{t['name']}**")
    paras.append(t["description"])
    paras += [param_line(n, sp, sch.get("required", [])) for n, sp in sch["properties"].items()]
flow("Tool descriptions (the 6 tools, every arm)", paras, ncols=3, pt=9, notes=src_note)

# A4 · Loop and scripted user
lp = HARNESS["loop"]
flow("The loop and the scripted user", [
    "**One conversation = one question, in one arm, one repetition.** The agent chooses the tools; the harness "
    "runs them and never chooses for it.",
    f"**Model:** {lp['model']}, effort {lp['effort']}, the same in every arm. At most {lp['max_tokens']:,} output "
    f"tokens per request and {lp['max_steps']} requests per conversation.",
    "**Arms:** v0 (relations only), v1_inputs, v1_outputs, v1. Tool names, schemas and descriptions are identical; "
    "only what model_network returns differs.",
    "**The scripted user** sends the question, then the question's scripted replies in order whenever the agent ends "
    "its turn. When none are left and the agent's message ends with \"?\", it replies once with the neutral go-ahead; "
    "otherwise the conversation ends.",
    f"**Neutral go-ahead:** \"{lp['go_ahead']}\"",
    "**No model fallback:** a refusal is recorded as such, because switching model mid-run would confound the arms.",
    "**exploratory_modeling** always draws its futures with the same seed (0), so repeated calls see the same futures.",
    "**Logged per tool call:** turn, tool, arguments, status (ok / error), seconds, arm, reply size and the full "
    "reply; per request: stop reason and tokens. The final answer is the agent's last text.",
], ncols=1, pt=13, notes=src_note)

# A5 · Rules checked in code
errs = [e for e in HARNESS["tool_errors"] if not e["message"].startswith('f"arm must')]
flow("Rules checked in code: what the agent reads when a call breaks one", [
    "When a call breaks a rule the tool returns {\"error\": message} and the agent can try again. Messages as written "
    "in the code ({…} is filled in at run time):"] +
    [f"• {e['message'].lstrip('f').strip(chr(34))}   ({e['file']}:{e['line']})" for e in errs] +
    ["• No ensemble {ensemble_id!r}; known: {…}. Run exploratory_modeling first.   (harness/state.py)",
     "• Unknown tool {name!r}; tools: [the 6 names]   (harness/registry.py)"], ncols=2, pt=10, notes=src_note)

# A6 · Fixed text inside the replies
flow("Fixed text inside the tool replies", [
    "**vulnerability_analysis, no threshold given** → status needs_threshold, with: \"Which value of {metric} in "
    "{year} counts as failure for {policy!r}? Give it in {unit}.\" plus the distribution to help choose.",
    "**exploratory_modeling, scenario_discovery** → \"Uncertainties are positions in their sampled range: 0 = low "
    "end, 0.5 = central, 1 = high end.\"",
    "**scenario_discovery** → \"Balanced accuracy of a small tree separating pass from fail (0.5 = no better than "
    "chance). The gap between the two is what the other uncertainties add.\"",
    "**trade_off_analysis** → \"Changes are against BAU in the same futures. Cost is the sum of the technical, "
    "system and fuel cost types (money spent, positive = more spending); net benefit adds every benefit and "
    "subtracts the cost (positive = better for the country). Cost per tonne counts only the cost types …\" + the "
    "costs note below",
    "**exploratory_modeling (cost or benefit metrics), trade_off_analysis** → \"Costs and benefits are shown only as "
    "changes against BAU on the same futures: their levels are differences against one fixed reference run, not a "
    "policy's money. Every cost_* is money spent; benefit_* and net_benefit are good for the country. cost_pct_gdp "
    "changes are in percentage points of GDP. cost_fuel holds only biogas and waste-to-energy revenue; fuel spending "
    "is in benefit_sector_specific … Costs and benefits that do not depend on a lever's level cancel out and do not "
    "show.\"",
    "**model_network from a lever, v1 arms** → \"Chain: inputs the lever sets → in-between variables → emission "
    "categories (the metrics exploratory_modeling reports). Values are medians over the model runs with every other "
    "lever and uncertainty varying; lever level low/mid/high = 0–⅓/⅓–⅔/⅔–1; uncertainty low/high = bottom/top third "
    "of its range.\" + in v1_outputs and v1: \"Each link's correlation is Spearman ρ across the model runs (−1 to 1; "
    "sign = direction); a variable's link to a category is |ρ| with its emission source in 2070.\"",
    "**model_network from a lever, v0** → \"Chain: inputs the lever sets → in-between variables → emission categories "
    "(the metrics exploratory_modeling reports). Relations only.\"  ·  No links: \"No links recorded for this lever "
    "(the mapping is incomplete for it).\"",
    "**model_network from an output, v1_outputs and v1** → \"Ranked by effect: median of the output with the group in "
    "the top fifth of its range minus the median in the bottom fifth, every other input varying. Low end = 0–0.2, "
    "high end = 0.8–1. Each link's correlation is Spearman ρ across the model runs (−1 to 1; sign = direction); a "
    "variable's link to a category is |ρ| with its emission source in 2070.\"",
    "**model_network from an output, v0 and v1_inputs** → \"Relations only, in id order: which levers and "
    "uncertainties move this output.\"",
    "**country_context** → \"Modelled baseline assumptions (2025–2050), not observed present-day statistics.\"",
], ncols=1, pt=12, notes=src_note + " These notes are copied by hand from backend/rdm/tools/*.py.")

prs.save(OUT)
print("saved", OUT, len(prs.slides), "slides")
