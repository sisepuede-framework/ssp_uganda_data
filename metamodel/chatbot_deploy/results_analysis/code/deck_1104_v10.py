"""Alexa's handwritten notes on speech draft v9 (05 Nov): inputs and outputs with examples (5), why one scale matters (7),
the 0-1 scale is for the experiment and decisions use real values (8), the focus is the interaction (9), agent turns (13),
SISEPUEDE inside (15), what the surrogate leaves out (16), median and percentiles (18), cars and vans CO2 (19),
500 futures (21), clearer question purposes (22), trade-off row removed (27), the lever node (29), RDM denominator (31, 32).

    python deck_1104_v10.py docs/DMDU_2026_Talk_draft_models_1104_video_v9.pptx \
                            docs/DMDU_2026_Talk_draft_models_1104_video_v10.pptx
"""
import os
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")

INK, BLUE, GREY = "16181D", "1F4E9C", "5B606B"
SANS = "IBM Plex Sans"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
p = Presentation(SRC)
slides = list(p.slides)
assert len(slides) == 56


def run(pg, content, size, bold, color):
    r = pg.add_run()
    r.text = content
    r.font.name, r.font.size, r.font.bold = SANS, Pt(size), bold
    r.font.color.rgb = RGBColor.from_string(color)


def text(s, x, y, w, h, parts, size=24, bold=False, color=INK):
    """parts: a string, or a list of (text, bold, color) runs in one paragraph."""
    b = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for t, bo, c in ([(parts, bold, color)] if isinstance(parts, str) else parts):
        run(tf.paragraphs[0], t, size, bo, c)
    return b


def set_text(shape, new, size=None):
    paras = shape.text_frame.paragraphs
    for extra in paras[1:]:
        extra._p.getparent().remove(extra._p)
    runs = paras[0].runs
    for extra in runs[1:]:
        extra._r.getparent().remove(extra._r)
    runs[0].text = new
    if size:
        runs[0].font.size = Pt(size)


def find(s, start):
    hits = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip().startswith(start)]
    assert len(hits) == 1, (start, len(hits))
    return hits[0]


def swap(s, old, new, size=None):
    set_text(find(s, old), new, size)


def by_id(s, i):
    return [x for x in s.shapes if x.shape_id == i][0]


def move(sh, y=None, h=None):
    if y is not None:
        sh.top = Inches(y)
    if h is not None:
        sh.height = Inches(h)


def clicks_of(s):
    t = s._element.find(f"{{{P_NS}}}timing")
    groups = []
    for c in t.iter(f"{{{P_NS}}}cTn"):
        kind = c.get("nodeType")
        if kind in ("clickEffect", "withEffect", "afterEffect"):
            sh = by_id(s, int(c.find(f".//{{{P_NS}}}spTgt").get("spid")))
            if kind == "clickEffect":
                groups.append([sh])
            else:
                groups[-1].append(sh)
    return groups


def animate(s, clicks):
    for t in s._element.findall(f"{{{P_NS}}}timing"):
        s._element.remove(t)
    n = [2]

    def nid():
        n[0] += 1
        return n[0]

    body, used = [], []
    for group in clicks:
        outer, inner = nid(), nid()
        effects = []
        for k, sh in enumerate(group):
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
    bld = "".join(f'<p:bldP spid="{i}" grpId="0" animBg="1"/>' for i in used)
    el = etree.fromstring(
        f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
        f'<p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq">'
        f'<p:childTnLst>{"".join(body)}</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl>'
        f'<p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/>'
        f'</p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst><p:bldLst>{bld}</p:bldLst>'
        f'</p:timing>')
    ext = s._element.find(f"{{{P_NS}}}extLst")
    if ext is not None:
        ext.addprevious(el)
    else:
        s._element.append(el)


# ---- 5. What goes in and what comes out, with examples (one new click after the XGBoost box); R² line moves down
s = slides[4]
clicks = clicks_of(s)
assert find(s, "Median R²") in clicks[-1]
move(find(s, "Median R²"), y=9.5)
rule = [x for x in clicks[-1] if not x.has_text_frame or not x.text_frame.text.strip()]
assert len(rule) == 1
move(rule[0], y=9.3)
io = [
    text(s, 1.15, 6.85, 17.7, 0.45, [("In: ", True, BLUE), ("54 levers + 13 uncertainties, each from 0 to 1", True, INK)], 24),
    text(s, 1.15, 7.3, 17.7, 0.45,
         "e.g. landfill gas recovered, electric share of cars and vans · GDP growth, fossil fuel prices, population growth",
         21, color=GREY),
    text(s, 1.15, 8.0, 17.7, 0.45, [("Out: ", True, BLUE), ("258 results, 2025–2070", True, INK)], 24),
    text(s, 1.15, 8.45, 17.7, 0.45,
         "e.g. emissions by sector (transport, livestock, deforestation…), costs, benefits (health, air pollution…), GDP",
         21, color=GREY),
]
animate(s, clicks[:-1] + [io] + clicks[-1:])

# ---- 7. The common scale lets one design cover every range evenly, all at once
swap(slides[6], "54 levers + 13 uncertainties",
     "54 levers + 13 uncertainties, about 100,000 runs: every range covered evenly, all at the same time")

# ---- 8. The 0-1 scale is for the experiment; decisions use real values; the full translation chain
s = slides[7]
swap(s, "To answer a real question", "Experiments use 0–1; decisions use real values")
move(find(s, "Between the two ends"), y=6.85)
box = [x for x in s.shapes if x.name == "Rectangle 70"][0]
move(box, y=7.45, h=2.65)
move(find(s, "IMPLICATIONS FOR THE AI AGENT"), y=7.6)
body = find(s, "The surrogate only takes 0–1")
move(body, y=8.05, h=1.95)
set_text(body, "Decisions are made in real values, not on a 0–1 scale. So the agent translates: from the user's words, "
               "to the real value, to the lever level. And back again for the answer.", 24)
for content, bold, color in (("“Half of rural households” → 50% in septic tanks → lever level 0.72", True, BLUE),
                             ("This takes time and expertise, but it is key for engagement.", False, INK)):
    pg = body.text_frame.add_paragraph()
    pg.space_before = Pt(6)
    run(pg, content, 24, bold, color)

# ---- 9. The focus is the interaction of the components
s = slides[8]
swap(s, "Agentic Rules", "The interaction")
swap(s, "How do rules and info", "Our focus is the interaction of all of these components")

# ---- 13. "Requests to the model" reads like SISEPUEDE: say agent turns
swap(slides[12], "At most 20 requests", "At most 20 agent turns per conversation, 16,000 tokens each. The same in Map and Map+")

# ---- 15. Inside the real model
swap(slides[14], "The agent could run the surrogate",
     "The agent could run the surrogate, but it could not see inside SISEPUEDE to understand how the variables in between interact.")

# ---- 16. Why the surrogate alone is not enough (shown from the start, before the three boxes)
text(slides[15], 1.15, 2.3, 17.7, 0.8,
     "The surrogate solved the time, but it predicts only some results. The agent needs the rest to explain results "
     "and to use the surrogate well.", 20, color=GREY)

# ---- 18. Median and percentiles instead of "density"; the thirds in plain words
s = slides[17]
swap(s, "Map+ adds the density", "Map+ adds each variable's median and range")
swap(s, "The density of each variable", "The median and the p10–p90 range")
swap(s, "By lever level and by uncertainty level", "When each lever is low, middle or high")

# ---- 19. That CO2 is cars and vans, not all transport
swap(slides[18], "CO₂ from transport", "CO₂ from cars and vans")

# ---- 21. Which futures
s = slides[20]
swap(s, "Same futures", "Same 500 futures")
swap(s, "Map+: the relations and the densities", "Map+: the relations and the values")

# ---- 22. Two purposes that read alike
s = slides[21]
swap(s, "Find what the surrogate can't report", "Find values only the network has")
swap(s, "Say the model can't answer", "Say what's outside the model")

# ---- 27. Drop the trade-off row (small n, no clear mechanism) and its bar row
s = slides[26]
assert find(s, "Comparison sent to trade_off_analysis").shape_id == 47
gone = {46, 47, 48, 49, 50, 51, 87, 88, 89}   # label, Map and Map+ values with their rules; the fourth bar row
assert all(Inches(5.7) < by_id(s, i).top < Inches(6.4) for i in gone)
clicks = [[x for x in g if x.shape_id not in gone] for g in clicks_of(s)]
clicks = [g for g in clicks if g]
for x in [x for x in s.shapes if x.shape_id in gone]:
    x._element.getparent().remove(x._element)
animate(s, clicks)
swap(s, "290 conversations · rows 1–3", "290 conversations · all rows: p < 0.01")

# ---- 29. Which first step
swap(slides[28], "Values answer the first question",
     "The lever's own values look like an answer, so the agent stops short.")

# ---- 31 and 32. The 22% and 12% are of the conversations that needed RDM steps
swap(slides[30], "required RDM step skipped", "required step skipped, Map → Map+ (of 50 RDM conversations each)", 24)
swap(slides[31], "All 290 conversations finished",
     "All 290 conversations finished, no thresholds invented; with Map+, 12% of RDM conversations still skipped a step.")

p.save(OUT)
print("saved", OUT)
