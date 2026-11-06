"""Slide 18 rebuilt as four numbered steps that start from the XGBoost inputs (Alexa, 06 Nov):
each input on its 0-1 scale -> cut into thirds -> each variable's median and p10-p90 -> from the 100,000 runs.

    python deck_1104_v12.py docs/DMDU_2026_Talk_draft_models_1104_video_v11.pptx \
                            docs/DMDU_2026_Talk_draft_models_1104_video_v12.pptx
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
SANS, MONO = "IBM Plex Sans", "IBM Plex Mono"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
p = Presentation(SRC)
s = p.slides[17]


def find(start):
    hits = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip().startswith(start)]
    assert len(hits) == 1, start
    return hits[0]


def text(x, y, w, h, content, size, bold, color, font=SANS):
    b = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    r = tf.paragraphs[0].add_run()
    r.text = content
    r.font.name, r.font.size, r.font.bold = font, Pt(size), bold
    r.font.color.rgb = RGBColor.from_string(color)
    return b


head = find("The same links, plus")
summary = find("A summary of the runs")
for start in ("The median and the p10–p90", "From the 100,000 runs", "For each third of the lever"):
    sh = find(start)
    sh._element.getparent().remove(sh._element)

STEPS = [("Each XGBoost input, on its 0–1 scale", "the 54 levers and 13 uncertainties"),
         ("Cut into thirds", "low 0–0.33 · middle 0.33–0.67 · high 0.67–1"),
         ("Each variable gets its median and p10–p90", "for each third, all along the network"),
         ("From the 100,000 runs", "the same runs that trained the XGBoost")]
X, Y0, STEP = 10.5, 3.55, 1.12
clicks = []
for k, (bold, line) in enumerate(STEPS):
    y = Y0 + k * STEP
    clicks.append([text(X, y, 0.6, 0.45, f"0{k + 1}", 22, True, BLUE, MONO),
                   text(X + 0.65, y - 0.03, 7.7, 0.45, bold, 25, True, BLUE),
                   text(X + 0.65, y + 0.45, 7.7, 0.4, line, 20, False, GREY)])
clicks[0].insert(0, head)
summary.top, summary.height = Inches(Y0 + 4 * STEP + 0.2), Inches(0.9)
clicks.append([summary])

# rebuild the slide's click builds: one click per step, the summary last
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

p.save(OUT)
print("saved", OUT)
