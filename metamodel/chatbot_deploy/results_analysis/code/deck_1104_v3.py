"""Four slides changed on Alexa's saved _v2 (19, 20, 30, 33). Everything else, including her edits, is kept.

    python deck_1104_v3.py docs/DMDU_2026_Talk_draft_models_1104_video_v2.pptx \
                           docs/DMDU_2026_Talk_draft_models_1104_video_v3.pptx
"""
import os
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")

INK, BLUE, GREY, MUTE, PALE, TINT, MAP = "16181D", "1F4E9C", "5B606B", "6B707B", "F4F5F7", "E8EEF8", "A3A9B4"
SANS, MONO = "IBM Plex Sans", "IBM Plex Mono"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
p = Presentation(SRC)
slides = list(p.slides)
assert len(slides) == 56


def rgb(h):
    return RGBColor.from_string(h)


def text(s, x, y, w, h, content, size=24, bold=False, color=INK, font=SANS):
    b = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    r = tf.paragraphs[0].add_run()
    r.text = content
    r.font.name, r.font.size, r.font.bold = font, Pt(size), bold
    r.font.color.rgb = rgb(color)
    return b


def rect(s, x, y, w, h, fill):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    r.shadow.inherit = False
    r.fill.solid()
    r.fill.fore_color.rgb = rgb(fill)
    r.line.fill.background()
    return r


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
    assert hits, start
    return hits[0]


def by_id(s, i):
    return [x for x in s.shapes if x.shape_id == i][0]


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


# ---- 19. Map+: say "from the 100,000 runs"; the exact sample goes in the notes
s = slides[18]
b = find(s, "From a sample")
runs = b.text_frame.paragraphs[0].runs
runs[0].text = "From the 100,000 runs"
for extra in runs[1:]:
    extra._r.getparent().remove(extra._r)
tf = s.notes_slide.notes_text_frame
tf.text = (tf.text + "\n\nExact, for Q&A: the values the agent saw in the experiment were computed on a random sample of 4,989 of "
           "the 100,000 runs, with at least 482 runs per cell. Comparison with all 100,000: pending.")

# ---- 20. The walk: links only for Map, one clear reading for the blue values
s = slides[19]
line = by_id(s, 39)
line._element.getparent().remove(line._element)
set_text(by_id(s, 42), "the links, no numbers")
for sid, new in ((44, "Sets the diesel share"), (46, "Used to compute diesel km"), (48, "Used to compute CO₂"),
                 (50, "Used to compute the sector total"), (52, "The sector total")):
    set_text(by_id(s, sid), new, 22)
set_text(by_id(s, 55), "the links, plus values as the lever goes up")
set_text(by_id(s, 63), "diesel km, billion")
set_text(by_id(s, 66), "CO₂, Mt")
set_text(by_id(s, 69), "CO₂e, Mt")
by_id(s, 69).height = by_id(s, 66).height
by_id(s, 70).top = by_id(s, 67).top
for sid in (57, 60, 63, 66, 69):
    by_id(s, sid).text_frame.paragraphs[0].runs[0].font.size = Pt(20)
for sid in (58, 61, 64, 67, 70):
    by_id(s, sid).text_frame.paragraphs[0].runs[0].font.size = Pt(28)
G = lambda *ids: [by_id(s, i) for i in ids]
animate(s, [G(40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52),
            G(*range(53, 71)),
            G(75)])
s.notes_slide.notes_text_frame.text = (
    "When speaking, note that this is showing the path from the previous two slides.\n\n"
    "When the agent gets a question it can call the model_network tool and navigate the network. With Map, it only sees the "
    "relations. With Map+, it also sees the values of each variable. That path across the network is for lever 35.\n\n"
    "What the blue numbers are, for Q&A. All are 2050. Electric share and diesel share: the input at BAU and at the top of the "
    "range run (dial 0 and dial 1). Diesel km, CO₂ and CO₂e: the median across the runs with the lever in its lowest third and "
    "in its highest third of the range, with every other lever and uncertainty varying. So they are not one run: the "
    "CO₂e median of 9.9 has a p10-p90 of 7.6-13.0. Electric and diesel share are cars and vans only. Diesel km and CO₂ cover "
    "all transport modes, and are the sum of each mode's median; the agent sees them mode by mode, not as this sum.")

# ---- 30. Early stops: Map vs Map+ on the same four questions
s = slides[29]
keep = {x.shape_id for x in s.shapes if x.has_text_frame and (
    x.text_frame.text.strip() in {"Findings", "DMDU Society Annual Meeting 2026"} or x.top < Inches(2.2))}
for x in list(s.shapes):
    if x.shape_id not in keep:
        x._element.getparent().remove(x._element)
text(s, 1.15, 2.75, 17.7, 0.5, "Four questions whose answer is a few steps along the network", 28, color=GREY)
text(s, 1.15, 3.4, 17.7, 0.5, "Conversations that reached the answer's variable", 24, True)
X, TRACK = 3.2, 11.8
rows = []
for y, label, n, color in ((4.0, "Map", 16, MAP), (4.75, "Map+", 7, BLUE)):
    c = BLUE if color == BLUE else GREY
    rows += [text(s, 1.15, y, 1.9, 0.6, label, 28, True, c), rect(s, X, y + 0.08, TRACK, 0.42, PALE),
             rect(s, X, y + 0.08, TRACK * n / 20, 0.42, color),
             text(s, X + TRACK + 0.3, y, 3.4, 0.6, f"{n} of 20", 28, True, c)]
said = text(s, 1.15, 5.6, 17.7, 0.6, "When Map+ got there, it always gave the value (7 of 7). When it stopped early, it never did (0 of 13).", 26)
c0 = rect(s, 1.15, 6.4, 17.7, 2.0, TINT)
c1 = text(s, 1.5, 6.55, 17, 0.45, "THE AGENT TOLD THE USER", 20, color=BLUE, font=MONO)
c2 = text(s, 1.5, 7.0, 17, 0.7, "“The tools don't report transport electricity demand.”", 32, True)
c3 = text(s, 1.5, 7.75, 17, 0.5, "The network had it, two steps further on: 56.0 → 59.9 PJ.", 26, color=GREY)
end = text(s, 1.15, 8.75, 17.7, 0.7, "Values answer the first question so well that the agent stops looking.", 32, True)
animate(s, [rows, [said], [c0, c1, c2, c3], [end]])
s.notes_slide.notes_text_frame.text = (
    "Map walks further, but it has no values to report when it gets there. Map+ sees numbers from the first step, so it often "
    "stops walking. When it did walk on, it answered.\n\n"
    "Questions S35, HD1, S50 and S3, 5 repetitions per version (20 conversations each). Map reached the variable 5, 5, 5 and 1 "
    "times; Map+ 5, 2, 0 and 0. The quote is from HD1. Full table in the appendix.")

# ---- 33. Conclusion: point 3 now rests on a result shown in the talk (RQ1)
s = slides[32]
set_text(find(s, "Test what the tools tell"), "A simulated user can work through RDM")
set_text(find(s, "Tool instructions need"), "All 290 conversations finished, no thresholds invented; 12% still skipped a required step with Map+.")
tf = s.notes_slide.notes_text_frame
tf.text = (tf.text + "\n\nPoint 3 used to be 'Test what the tools tell the agent: tool instructions need to be tested like a "
           "model'. Its evidence is in the appendix (design lessons), not in the talk, so it can come up in discussion.")

p.save(OUT)
print("saved", OUT)
