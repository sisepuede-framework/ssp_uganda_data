"""On the saved _v5: the implications move to the translation slide, the 'same dial move' slide goes, a new slide explains
the harness in plain words, and the six rules move to the appendix.

    python deck_1104_v6.py docs/DMDU_2026_Talk_draft_models_1104_video_v5.pptx \
                           docs/DMDU_2026_Talk_draft_models_1104_video_v6.pptx
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

INK, BLUE, GREY, MUTE, TINT = "16181D", "1F4E9C", "5B606B", "6B707B", "E8EEF8"
SANS, MONO = "IBM Plex Sans", "IBM Plex Mono"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
p = Presentation(SRC)
slides = list(p.slides)
assert len(slides) == 56


def text(s, x, y, w, h, content, size=24, bold=False, color=INK, font=SANS, align=None):
    b = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    pg = tf.paragraphs[0]
    if align:
        pg.alignment = align
    r = pg.add_run()
    r.text = content
    r.font.name, r.font.size, r.font.bold = font, Pt(size), bold
    r.font.color.rgb = RGBColor.from_string(color)
    return b


def rect(s, x, y, w, h, fill):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    r.shadow.inherit = False
    r.fill.solid()
    r.fill.fore_color.rgb = RGBColor.from_string(fill)
    r.line.fill.background()
    return r


def set_text(shape, new):
    paras = shape.text_frame.paragraphs
    for extra in paras[1:]:
        extra._p.getparent().remove(extra._p)
    runs = paras[0].runs
    for extra in runs[1:]:
        extra._r.getparent().remove(extra._r)
    runs[0].text = new


def find(s, start):
    hits = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip().startswith(start)]
    assert hits, start
    return hits[0]


def by_id(s, i):
    return [x for x in s.shapes if x.shape_id == i][0]


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


# ---- 8. Translate back: rows move up to make room; the implications come here from slide 9
s = slides[7]
assert find(s, "To answer a real question")
groups = clicks_of(s)
for x in s.shapes:
    top = x.top / 914400
    if 3.8 <= top < 4.85:
        x.top -= Inches(0.2)
    elif 5.25 <= top < 6.3:
        x.top -= Inches(0.45)
    elif 6.7 <= top < 7.7:
        x.top -= Inches(0.7)
find(s, "Between the two ends").top = Inches(6.95)
c0 = rect(s, 1.15, 7.65, 17.7, 1.95, TINT)
c1 = text(s, 1.5, 7.85, 17.0, 0.5, "IMPLICATIONS FOR THE AI AGENT", 20, color=BLUE, font=MONO)
c2 = text(s, 1.5, 8.35, 17.0, 1.1, "The surrogate only takes 0–1 and people speak in real units, so the agent has to translate both "
          "ways to get the size of a change right.", 30)
animate(s, groups + [[c0, c1, c2]])
tf = s.notes_slide.notes_text_frame
tf.text = (tf.text + "\n\nWhy it matters: the same move on the dial is a different real change on each lever. From 0 to 0.5: landfill gas "
           "+24 points, septic tanks +22, electric cars and vans +11. To approximate the magnitude of a change correctly, we need "
           "to go from the real value to the dial and back.")

# ---- 13. Pipeline: Alexa's layout and clicks stay; the harness only names its four parts, the next slide explains them
s = slides[12]
assert find(s, "The pipeline depends")
set_text(by_id(s, 22), "Remembers results between calls")
set_text(by_id(s, 24), "Checks each call")
set_text(by_id(s, 26), "Records every step")
set_text(by_id(s, 28), "Caps each conversation")

# ---- New. The harness in plain words
sH = p.slides.add_slide(p.slide_layouts[0])
for ph in list(sH.placeholders):
    ph._element.getparent().remove(ph._element)
text(sH, 1.15, 0.92, 18.3, 0.36, "METHOD · THE HARNESS", 18, color=BLUE, font=MONO)
text(sH, 1.15, 1.39, 18.33, 0.73, "The harness sets how the agent and the tools interact", 45, True)
text(sH, 1.15, 10.26, 4.46, 0.36, "DMDU Society Annual Meeting 2026", 18, color=MUTE)
text(sH, 15.0, 10.26, 3.94, 0.36, "Method", 18, color=MUTE, align=PP_ALIGN.RIGHT)
parts = (("State", "What it remembers", "Keeps each set of results under an id, so the next tool can use them"),
         ("Rules", "What it won't allow", "Rejects a lever outside its range or an uncertainty fixed at one value. The failure threshold must come from the user"),
         ("Log", "What it records", "Every tool call, reply and answer, plus a summary of the agent's thinking"),
         ("Limits", "How far the agent can go", "At most 20 requests to the model per conversation, 16,000 tokens each. The same in Map and Map+"))
groups, w = [], 4.1
for k, (name, plain, detail) in enumerate(parts):
    x = 1.15 + k * (w + 0.43)
    groups.append([rect(sH, x, 2.75, w, 0.03, INK),
                   text(sH, x, 2.95, w, 0.55, name, 25, True, BLUE),
                   text(sH, x, 3.6, w, 1.3, plain, 30, True),
                   text(sH, x, 5.0, w, 3.0, detail, 24, color=GREY)])
end = text(sH, 1.15, 8.45, 17.7, 0.7, "No script of steps: the agent chooses the tools and their order.", 30, True, BLUE)
animate(sH, groups + [[end]])
ns = sH.notes_slide
if ns.notes_text_frame is None:
    ns.shapes._spTree.append(etree.fromstring(
        f'<p:sp xmlns:p="{P_NS}" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:nvSpPr>'
        f'<p:cNvPr id="{max([x.shape_id for x in ns.shapes] + [1]) + 1}" name="Notes"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
        f'<p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>'))
ns.notes_text_frame.text = (
    "State: the agent does not copy data around. A run gets an id, and the next tool reads it by that id.\n\n"
    "Rules: when a call breaks a rule, the agent gets an error message and can try again. It is also told to speak the policy "
    "maker's language, and to describe trade-offs without naming a winner. The six rules are in the appendix, and the rules do "
    "not script the agent's steps.\n\n"
    "Log: this is what lets us evaluate the agent. The harness asks the model for a summary of its reasoning and stores it. "
    "It is display only and is never scored.\n\n"
    "Limits: the conversation stops at 20 requests to the model, and each reply can use up to 16,000 tokens. They are the same "
    "in both versions so they do not affect the comparison.\n\n"
    "No conversation reached a limit in the full run: all 290 ended normally, with at most 16 requests and a median of 4.")

# ---- Order: slide 9 goes, the harness slide follows the pipeline, the six rules move to the start of the appendix
ids = p.slides._sldIdLst
all_ = list(ids)
new = all_[-1]
assert p.part.related_part(new.rId) is sH.part
old = all_[:-1]
dup, rules, appendix = old[8], old[13], old[33]
assert find(p.part.related_part(appendix.rId).slide, "Appendix: details")
assert find(p.part.related_part(rules.rId).slide, "Six rules")
assert find(p.part.related_part(dup.rId).slide, "The same dial move")
order = []
for sid in old:
    if sid is dup or sid is rules:
        continue
    order.append(sid)
    if sid is old[12]:
        order.append(new)
    if sid is appendix:
        order.append(rules)
p.part.drop_rel(dup.rId)
for sid in list(ids):
    ids.remove(sid)
for sid in order:
    ids.append(sid)
p.save(OUT)
print("saved", OUT, len(order))
