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
s = new_slide("The problem we are addressing", "Context",
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

# 3 · Three components of RDM
s = new_slide("What the tool facilitates: three components of RDM", "Context",
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
text(s, x1c, ly1 + 0.1, x3c - x1c, 0.3, "revise vulnerable plans and test them again", 13, color=ACC,
     italic=True, align=PP_ALIGN.CENTER)
text(s, LM, TOP + 4.75, CW, 0.4, "The tool is not an RDM analysis in itself: it lets a non-technical user carry out "
     "these three components through an agent.", 15, color=MUTED, align=PP_ALIGN.CENTER)

# 4 · Research questions
s = new_slide("Research questions", "Context",
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

# 5 · Surrogate (left blank on purpose)
s = new_slide("What a surrogate is and how it is built", "Method · the surrogate",
              "This slide will be prepared by a teammate. Left blank on purpose.")
placeholder(s, LM, TOP + 0.2, CW, 5.0, "[To be prepared by the surrogate team]", 16)

# 6 · Surrogate training details
s = new_slide("How the surrogate was trained", "Method · the surrogate",
              "Brief training facts of the XGBoost surrogate the technical tools run. Sources: "
              "metamodel/surrogate_model_sector/retrain_sector.py, utils/ml_utils_v2.py (XGBMultiOutputPipeline), "
              "athena/README.md (rows dropped), trained_models/metrics_<run>_summary.md (scores), "
              "trained_models/split_<run>.csv (which run is in which half). Retrained 2026-10-16.")
bw4 = (CW - 3 * 0.45) / 4
steps = [("100,000 SISEPUEDE runs", "Latin hypercube over 54 levers and 13 uncertainties, each 0–1.\n"
                                    "99,588 kept: runs with a missing output, GDP ≤ 0 or an emission blow-up dropped; "
                                    "no outlier filter"),
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
s = new_slide("How we built the ecosystem: the rules", "Method · the ecosystem",
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
s = new_slide("The ecosystem: who does what", "Method · the ecosystem",
              "We include the harness, list the tools and talk about the design. The agent decides which tool to use; "
              "the harness never does. A fixed sequence would remove what the experiment measures. There is no "
              "plan step: we measure only the actions the agent takes, from the log.")
cx, colw = LM + 0.3, 4.6
rows6 = [("Policy maker", "Asks in plain language", FILL, BORDER),
         ("Agent (Claude)", "Chooses the tools and their arguments", ACC_LT, ACC),
         ("7 tools", "Deterministic methods, one data source each", WHITE, BORDER),
         ("Data", "Surrogate · model runs · (L, X) object", FILL, BORDER)]
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
s = new_slide("The tools: one question, one data source each", "Method · the tools",
              "Seven tools in three groups. Information tools read the model runs and tell the agent what a lever "
              "moves and what moves an output; they are the treatment. Technical tools run on the surrogate, one per "
              "step of the three RDM components (the small numbers). Context is the country baseline. The crosswalk "
              "(505 emission fields to 23 categories) links the runs to the surrogate.")
groups = [
    ("Information", [("lever_x_profile", "What does this lever move, across X?"),
                     ("output_levers", "What moves this output?")],
     "Model runs: mapping · (L, X) object · crosswalk", True),
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
text(s, LM, data_y + 0.7, CW, 0.3, "Highlighted: the information tools, where the experiment changes what the agent "
     "receives  ·  1 · 2 · 3 = the RDM component a tool serves", 12, color=MUTED, align=PP_ALIGN.CENTER)

# 8b · What each tool does and does not do
s = new_slide("What each tool does, and what it does not", "Method · the tools",
              "Two families. READ tools describe the 100,000 model runs that already exist; they never compute "
              "anything new. RUN tools compute new results on the surrogate: only exploratory_modeling creates "
              "results, the other three analyse the ensemble it returns. Examples are from the question bank.")
cols = [("Tool", 1.85), ("The question it answers", 2.15), ("You give it", 2.2),
        ("You get back (example)", 3.6), ("It does NOT", 2.33)]
rows = [
    ("lever_x_profile", "What does this lever do?", "one lever, one uncertainty, a year",
     "what it changes in the runs: lever 35 takes electric light-duty travel from 50% (BAU) to 72%; "
     "electric vehicle-km; transport emissions", "run a policy, combine levers, or test across futures"),
    ("output_levers", "What moves this result?", "one result: an emission category or a variable "
     "(e.g. primary forest area)", "the levers and uncertainties that move it (v1: ranked by how much)",
     "say how far to push each lever"),
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
hy, rh = TOP - 0.05, 0.6
x = LM
for name, w in cols:
    text(s, x + 0.06, hy, w - 0.12, 0.3, name, 12, color=MUTED, bold=True, font=HEAD)
    x += w
for i, row in enumerate(rows):
    y = hy + 0.38 + i * (rh + 0.05) + (0.18 if i >= 3 else 0)
    read = i < 3
    rect(s, LM, y, CW, rh, fill=ACC_LT if read else FILL, line=None)
    x = LM
    for j, ((_, w), cell) in enumerate(zip(cols, row)):
        text(s, x + 0.08, y + 0.05, w - 0.16, rh - 0.1, f"**{cell}**" if j < 2 else cell, 11.5 if j < 2 else 10.5,
             color=TXT if j < 4 else MUTED, anchor=MSO_ANCHOR.MIDDLE, font=BODY)
        x += w
text(s, LM, 6.68, CW, 0.3,
     "Blue = READ tools: describe the model runs (the experiment changes what the first two show)   ·   "
     "Grey = RUN tools: new results on the surrogate", 12, color=MUTED, align=PP_ALIGN.CENTER)

# 8c · Which tool for which question
s = new_slide("Which tool for which question", "Method · the tools",
              "A guide to assign tools to any question, used to set the expected flow of each question in the bank. "
              "Read the question, find the first row that fits, use those tools in that order.")
guide = [
    ("asks what a lever does", ["lever_x_profile"], "e.g. \"What does reducing deforestation change in the model?\""),
    ("asks what moves a result", ["output_levers"], "e.g. \"What drives livestock emissions in 2050?\""),
    ("asks about Uganda's baseline", ["country_context"], "e.g. \"How much land is under cereals?\""),
    ("gives a policy as lever levels", ["exploratory_modeling"], "e.g. \"Set reduced deforestation to 0.6 …\""),
    ("gives a policy in real-world units", ["lever_x_profile", "exploratory_modeling"],
     "P50i · \"What if landfills recovered 40% of their gas?\""),
    ("asks for an emissions target", ["output_levers", "exploratory_modeling"],
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
        read = t in ("lever_x_profile", "output_levers", "country_context")
        if t.startswith("no tool"):
            node(s, tx, y, tw, gh, t, fill=WHITE, line=MUTED, head_pt=11, head_color=MUTED, dash=True,
                 italic=True, head_font=BODY)
        else:
            node(s, tx, y, tw, gh, t, fill=ACC_LT if read else FILL, line=ACC if read else BORDER, head_pt=11,
                 head_font=BODY)
        if j < len(tools) - 1:
            arrow(s, tx + tw + 0.02, y + gh / 2, tx + tw + tg2 - 0.02, y + gh / 2)
    text(s, ex_x, y, LM + CW - ex_x, gh, ex, 11, color=MUTED, italic=True, anchor=MSO_ANCHOR.MIDDLE)

# 8a · The SISEPUEDE pipeline and what each tool shows of it
s = new_slide("What the agent sees of the SISEPUEDE pipeline", "Method · the tools",
              "Top row: the SISEPUEDE pipeline, left to right. A lever (or uncertainty) is a 0-1 value; it sets "
              "input trajectories (model_input). SISEPUEDE receives those inputs and runs its process; what it "
              "outputs are the drivers (in-between variables: vehicle-km, crop area, fuel demand) and the emissions "
              "they produce, 505 detailed emission fields (the sub-emissions). Our crosswalk adds them into the 23 "
              "inventory categories, which is what the XGBoost predicts. (We use the post-processed emissions; "
              "the adjustment is left out of this slide.)\n"
              "\n"
              "Rows: what each tool shows the agent at each step. Dark = names and, in the v1 arms, values; light = "
              "names only; empty = not read.\n"
              "- lever_x_profile walks the chain for one lever: inputs (values in v1_inputs, v1), drivers and "
              "categories (values in v1_outputs, v1), sub-emissions as names under each category.\n"
              "- output_levers is the reverse look-up: the agent names one output (a driver, an emission field or a "
              "category) and gets the levers and uncertainties that move it (v1 adds how much: median with the lever "
              "low vs high, effect, rho). It does not find the level that reaches a value; for that the agent goes on "
              "to lever_x_profile and exploratory_modeling. Used in A (what drives X?) and as the first step of C "
              "(which lever can reach this target?).\n"
              "- The technical tools never walk the chain: the XGBoost goes straight from the 0-1 levers and "
              "uncertainties to the 23 categories (plus costs, benefits and GDP).\n"
              "- country_context reads one run, the BAU baseline: some inputs (mode shares, energy mix) and some "
              "outputs (GDP, population, crop area, livestock).\n"
              "\n"
              "What the agent is told about the links: each box is linked to the lever (the mapping), and each "
              "driver to the category it feeds (the drivers file). It is never told which input feeds which driver: "
              "that step is SISEPUEDE itself, and we only see it through the runs.\n"
              "\n"
              "Files: inputs backend/rdm/data/tables/run_2026_05_30_lever_inputs.csv; mapping "
              "backend/rdm/mapping/maps/run_2026_05_30.csv; drivers backend/rdm/links/run_2026_05_30_drivers_by_category.csv; "
              "values backend/rdm/data/tables/run_2026_05_30_values.parquet; crosswalk backend/sector_categories.json "
              "(all under metamodel/chatbot_deploy/). S3 tables: s3://sisepuede-data/run_database/"
              "sisepuede_run_2026-05-30t21;35;56.244639/{model_input, model_output, decomposed_emissions}.")
stages = [("Levers & uncertainties", "0–1 values"),
          ("Inputs", "model_input"),
          ("Drivers", "model_output"),
          ("Sub-emissions", "505 emission fields"),
          ("Categories", "crosswalk · 23")]
lab_w = 2.0
sg = 0.22
sw = (CW - lab_w - 4 * sg) / 5
sx = [LM + lab_w + i * (sw + sg) for i in range(5)]
hy, hh = TOP + 0.55, 0.8
# SISEPUEDE bracket: from the inputs' outgoing arrow to the end of the sub-emissions
bx0, bx1 = sx[1] + sw + sg / 2, sx[3] + sw
rect(s, bx0, TOP - 0.05, bx1 - bx0, 0.42, fill=WHITE, line=TXT, line_w=1.25)
text(s, bx0, TOP - 0.05, bx1 - bx0, 0.42, "**SISEPUEDE** outputs: drivers + emissions", 12, color=TXT,
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
    ("lever_x_profile", "one lever, walks the chain",
     [(LIGHT, "the lever + one uncertainty"), (DARK, "what it sets\nv1: value at 0 / 0.5 / 1"),
      (DARK, "what it moves\nv1: p10–median–p90"), (LIGHT, "names, under\neach category"),
      (DARK, "what it moves\nv1: p10–median–p90")]),
    ("output_levers", "reverse look-up: name an output, get the levers",
     [(DARK, "② the L and X\nthat move it\nv1: + how much"), "back", "start", "start", "start"]),
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
    if name == "output_levers":     # read right to left: ① the agent names an output, ② it gets the levers
        x0, x1 = sx[2], sx[4] + sw
        rect(s, x0, ry, x1 - x0, rh, fill=FILL, line=BORDER)
        text(s, x0 + 0.15, ry, x1 - x0 - 0.3, rh, "① starts here: the agent names one output\n"
             "a driver, an emission field or a category", 12, color=TXT, align=PP_ALIGN.CENTER,
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
text(s, LM + 6.5, ly, CW - 6.5, 0.3, "Never given as a link: which input feeds which driver (that is SISEPUEDE)",
     12, color=ACC, bold=True, align=PP_ALIGN.RIGHT)

# 8b · What each tool reads
s = new_slide("What each tool reads", "Method · the tools",
              "Where to find each piece (paths from the repo root, ssp_uganda_data/; branch rdm-tools).\n"
              "\n"
              "lever_x_profile and output_levers: metamodel/chatbot_deploy/backend/rdm/tools/information.py\n"
              "  1 Lever inputs table: metamodel/chatbot_deploy/backend/rdm/data/tables/run_2026_05_30_lever_inputs.csv "
              "(built by backend/rdm/data/lever_inputs.py)\n"
              "  2 Mapping, lever/X -> outputs: metamodel/chatbot_deploy/backend/rdm/mapping/maps/run_2026_05_30.csv "
              "(built by backend/rdm/mapping/build_mapping.py)\n"
              "  3 Drivers (in-between variables per category): "
              "metamodel/chatbot_deploy/backend/rdm/links/run_2026_05_30_drivers_by_category.csv "
              "(built by backend/rdm/links/drivers.py; per-source detail in run_2026_05_30_drivers_by_source.csv)\n"
              "  4 Values table: metamodel/chatbot_deploy/backend/rdm/data/tables/run_2026_05_30_values.parquet "
              "(built by backend/rdm/data/values.py)\n"
              "  5 Crosswalk: metamodel/chatbot_deploy/backend/sector_categories.json, generated from "
              "metamodel/surrogate_model_sector/config/crosswalk_inventory_to_sisepuede_20260510.csv\n"
              "  Run store for output_levers values: backend/rdm/data/store.py over the cached sample "
              "(backend/rdm/data/sample.py; 4,989 runs, decomposed_emissions + model_output from S3 "
              "s3://sisepuede-data/run_database/sisepuede_run_2026-05-30t21;35;56.244639/)\n"
              "  Which arm sees which values: ARMS in backend/rdm/tools/information.py\n"
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
    ("lever_x_profile", "Information · treatment",
     "1 · Inputs the lever sets, with their value at lever 0 / 0.5 / 1\n"
     "2 · Outputs the lever moves (mapping)  ·  3 · In-between variables (drivers)\n"
     "4 · Values: p10–median–p90 per lever level × X low / high  ·  5 · Crosswalk",
     "Tables built from the model runs\nv0: names only (1, 2, 3, 5) · v1: adds the values (1, 4)", True, 1.3),
    ("output_levers", "Information · treatment",
     "Which levers and uncertainties move an output (mapping + crosswalk).\n"
     "v1 adds values from the runs: median at the low vs high end, effect, ρ",
     "Mapping + run store: 4,989 runs, emissions (decomposed_emissions) and variables (model_output)", True, 1.0),
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

# 8c · How the variables were selected
s = new_slide("How the variables in the chain were selected", "Method · the tools",
              "What lever_x_profile returns is a chain: lever -> inputs it sets -> in-between variables -> emission "
              "categories. Each link was selected differently.\n"
              "\n"
              "1 INPUTS. Not selected by us: they come from the file where the run defines its levers, "
              "VARIABLE_TRAJECTORY_GROUPS_L.csv (each lever group: transformation code + the input fields it sets; "
              "54 levers, 527 fields). Values: from the experiment's own runs (model_input, 4,989 sampled runs, 2050 and "
              "2070): each field is a straight line in its lever's level, fitted over the runs, read at the bottom "
              "(BAU), middle and top of the range the experiment explored. No dependence on X. Cross-check only: the "
              "line matches the fixed BASE and HBLE pathway runs within 0.4% of the range (the experiment scales that "
              "strategy). Shown: the fields the lever moves.\n"
              "  Definition file: metamodel/data/ssp/sisepuede_run_2026-05-30t21;35;56.244639/VARIABLE_TRAJECTORY_GROUPS_L.csv\n"
              "  Code: metamodel/chatbot_deploy/backend/rdm/data/groups.py and backend/rdm/data/lever_inputs.py\n"
              "  Table: metamodel/chatbot_deploy/backend/rdm/data/tables/run_2026_05_30_lever_inputs.csv\n"
              "\n"
              "2 MAPPING (which outputs a lever moves). Structural: SISEPUEDE's transformation -> output map "
              "(metamodel/data/ssp/transformation_output_variable_map.csv). Empirical: |Spearman rho| >= 0.10 between "
              "the lever and the output across the sampled runs at any anchor year, every other lever and uncertainty "
              "varying. 4,805 links (1,169 both, 3,107 empirical only, 400 structural only); 129 structural links "
              "whose output never moves in the runs are dropped.\n"
              "  Code: metamodel/chatbot_deploy/backend/rdm/mapping/build_mapping.py\n"
              "  Table: metamodel/chatbot_deploy/backend/rdm/mapping/maps/run_2026_05_30.csv\n"
              "\n"
              "3 IN-BETWEEN VARIABLES (drivers). For each emission source (an emission field without its gas) in "
              "each category, at the last run year: 0 constant across runs -> no driver; 1 exact name: a variable "
              "containing the whole source name, up to 2; 2 group: the source sums a dimension the variables split "
              "(e.g. per fuel) -> the whole family; 3 correlation: the 1-2 candidates from the subsector-name rule "
              "that move most with the source, weak if rho < 0.3. Result: 176 (category, variable) rows, 151 "
              "variables, 15 categories; awaiting expert review. For a lever, lever_x_profile shows the drivers of "
              "its categories that the lever moves, plus the 2 variables it moves most (its 'channel').\n"
              "  Code: metamodel/chatbot_deploy/backend/rdm/links/drivers.py (rules), backend/rdm/links/subsector.py "
              "(subsector-name candidates), backend/rdm/data/values.py (lever_outputs, lever_channel)\n"
              "  Review files: metamodel/chatbot_deploy/backend/rdm/links/run_2026_05_30_drivers_by_category.csv and "
              "run_2026_05_30_drivers_by_source.csv\n"
              "\n"
              "4 CATEGORIES. The official inventory crosswalk: 505 emission fields -> 23 categories, the ones the "
              "XGBoost predicts.\n"
              "  metamodel/surrogate_model_sector/config/crosswalk_inventory_to_sisepuede_20260510.csv -> "
              "metamodel/chatbot_deploy/backend/sector_categories.json\n"
              "\n"
              "Design log: metamodel/chatbot_deploy/docs/rdm_information_layer_plan.md")
chain = [
    ("Inputs", "what the lever sets",
     "**Source:** the run's lever definition file, not chosen by us:\n"
     "VARIABLE_TRAJECTORY_\nGROUPS_L.csv\n"
     "54 levers, 527 input fields\n"
     "**Values:** from the experiment's runs: a straight line in the lever level, read at BAU and at the top of the "
     "range run"),
    ("Outputs it moves", "the mapping",
     "**Structural:** SISEPUEDE's transformation → output map\n"
     "**Empirical:** |Spearman ρ| ≥ 0.10 in the runs, any year, all else varying\n"
     "4,805 links; links whose output never moves are dropped"),
    ("In-between variables", "the drivers",
     "Per emission source, last year:\n"
     "0 · constant → none\n1 · exact name (≤ 2)\n2 · group (e.g. per fuel)\n"
     "3 · correlation, subsector rule (weak if ρ < 0.3)\n"
     "+ the lever's 2 strongest variables\n"
     "151 variables · expert review pending"),
    ("Emission categories", "the crosswalk",
     "Official inventory crosswalk: 505 emission fields → 23 categories\n"
     "The same categories the XGBoost predicts"),
]
gap = 0.35
cw4 = (CW - 3 * gap) / 4
for i, (head, sub, body) in enumerate(chain):
    x = LM + i * (cw4 + gap)
    text(s, x, TOP - 0.05, cw4, 0.3, str(i + 1), 14, color=ACC, bold=True, align=PP_ALIGN.CENTER, font=HEAD)
    node(s, x, TOP + 0.3, cw4, 0.85, head, sub, fill=ACC_LT, line=ACC, head_pt=15, sub_pt=12)
    if i < 3:
        arrow(s, x + cw4 + 0.05, TOP + 0.72, x + cw4 + gap - 0.05, TOP + 0.72, color=ACC)
    rect(s, x, TOP + 1.35, cw4, 3.45, fill=WHITE, line=BORDER)
    text(s, x + 0.18, TOP + 1.5, cw4 - 0.36, 3.2, body, 13, color=TXT, space_after=5)
text(s, LM, TOP + 4.95, CW, 0.3, "Lever → inputs → in-between variables → categories: the chain lever_x_profile "
     "returns  ·  file paths and full rules in the speaker notes", 12, color=MUTED, italic=True, align=PP_ALIGN.CENTER)

# 9 · Questions
s = new_slide("The questions we use to test the agent", "Experiment · questions",
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
s = new_slide("How the agent moves through the tools", "Method · the tools",
              "Expected flow per question category, set in advance and compared with the tools the agent actually "
              "calls. There is no plan step. In D the agent asks the user which value counts as failure before the "
              "vulnerability analysis. Same rules as the slide 'Which tool for which question'; a question can mix "
              "rows (e.g. a target in real units: lever_x_profile, then exploratory_modeling).")
flows = [   # the same rules as the "Which tool for which question" slide
    ("A · Information", ["one READ tool", "answer"]),
    ("B · Evaluate", ["lever_x_profile (if real units)", "exploratory_modeling", "answer"]),
    ("C · Reach target", ["output_levers", "exploratory_modeling (try levels)", "answer"]),
    ("D · Robustness", ["exploratory_modeling", "user sets threshold", "vulnerability_analysis", "scenario_discovery"]),
    ("E · Compare", ["exploratory_modeling", "trade_off_analysis", "answer"]),
    ("F · Outside", ["decline or clarify"]),
]
knowledge = {"lever_x_profile", "output_levers", "one READ tool", "lever_x_profile (if real units)"}
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
s = new_slide("The data we give the agent", "Experiment · data",
              "Here we list our data sets and highlight the data we provide as the experiment: the relations and values "
              "from the model runs. v0 and v1 use the same prompt and the same 7 tools; only what the information "
              "tools return changes. v0 gets the relations (which lever moves which variable and emission, and its "
              "category); v1 adds how much (values, ranges, direction, units).")
data = [
    ("Lever / X → output mapping", "4,805 links: which L and X move which output", "know"),
    ("Crosswalk", "505 emission fields → 23 inventory categories", "know"),
    ("Model runs (sample)", "4,989 runs: 505 emissions, 1,025 variables", "know"),
    ("(L, X) object", "Values per lever level × X bin", "know"),
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
for k, label in [("know", "Information tools"), ("exp", "Technical tools"), ("ctx", "Context")]:
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
     "Which lever moves which variable and emission:\n\"Lever 35 moves light-duty biofuel vehicle-km.\"",
     fill=WHITE, head_pt=14, sub_pt=12)
node(s, vx, TOP + 2.2, vw, 1.45, "v1 · relations + values",
     "How much, across L and X:\n\"From 3.0 to 2.0 billion vehicle-km as the lever goes 0 → 1; higher if GDP is high.\"",
     fill=ACC_LT, line=ACC, head_pt=14, sub_pt=12)
arrow(s, tx + tw + 0.05, kc, vx - 0.05, TOP + 1.2, color=ACC)
arrow(s, tx + tw + 0.05, kc, vx - 0.05, TOP + 2.9, color=ACC)
text(s, vx, TOP + 3.85, vw, 0.9, "Same prompt and same 7 tools in both; only this changes.", 13, color=MUTED,
     align=PP_ALIGN.CENTER)

# 12 · Surrogate interaction
s = new_slide("Surrogate interaction: what changes with the treatment", "Experiment · interaction",
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
s = new_slide("Results and conclusions", "Results",
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
         ("Tool descriptions", "the 7 tools and their parameters, as the agent sees them · identical in every arm",
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
flow("Tool descriptions (the 7 tools, every arm)", paras, ncols=3, pt=9, notes=src_note)

# A4 · Loop and scripted user
lp = HARNESS["loop"]
flow("The loop and the scripted user", [
    "**One conversation = one question, in one arm, one repetition.** The agent chooses the tools; the harness "
    "runs them and never chooses for it.",
    f"**Model:** {lp['model']}, effort {lp['effort']}, the same in every arm. At most {lp['max_tokens']:,} output "
    f"tokens per request and {lp['max_steps']} requests per conversation.",
    "**Arms:** v0 (relations only), v1_inputs, v1_outputs, v1. Tool names, schemas and descriptions are identical; "
    "only what lever_x_profile and output_levers return differs.",
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
     "• Unknown tool {name!r}; tools: [the 7 names]   (harness/registry.py)"], ncols=2, pt=10, notes=src_note)

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
    "**lever_x_profile, v1 arms** → \"Chain: inputs the lever sets → in-between variables → emission categories (the "
    "metrics exploratory_modeling reports). Values are medians over the model runs with every other lever and "
    "uncertainty varying; lever level low/mid/high = 0–⅓/⅓–⅔/⅔–1; uncertainty low/high = bottom/top third of its "
    "range.\"",
    "**lever_x_profile, v0** → \"Chain: inputs the lever sets → in-between variables → emission categories (the "
    "metrics exploratory_modeling reports). Relations only.\"  ·  No links: \"No links recorded for this lever (the "
    "mapping is incomplete for it).\"",
    "**output_levers, v1 arms** → \"Ranked by effect: median of the output with the group in the top fifth of its "
    "range minus the median in the bottom fifth, every other input varying. Low end = 0–0.2, high end = 0.8–1.\"",
    "**output_levers, v0** → \"Relations only, in id order: which levers and uncertainties move this output.\"",
    "**country_context** → \"Modelled baseline assumptions (2025–2050), not observed present-day statistics.\"",
], ncols=1, pt=12, notes=src_note + " These notes are copied by hand from backend/rdm/tools/*.py.")

prs.save(OUT)
print("saved", OUT, len(prs.slides), "slides")
