"""On the saved _v6: 'dial' becomes 'lever level', and each Map+ value on the walk slide is labeled in its box.

    python deck_1104_v7.py docs/DMDU_2026_Talk_draft_models_1104_video_v6.pptx \
                           docs/DMDU_2026_Talk_draft_models_1104_video_v7.pptx
"""
import os
import re
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")

BLUE, GREY, MUTE = "1F4E9C", "5B606B", "6B707B"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
p = Presentation(SRC)
slides = list(p.slides)
assert len(slides) == 56

# ---- 'dial' -> 'lever level', run by run so the format stays
RUNS = (
    ("One dial lets us treat every lever the same way.", "One scale lets us treat every lever the same way."),
    ("Latin hypercube tests every part of every dial", "Latin hypercube tests every part of every lever's range"),
    ("Dial A, cut into equal slices", "Lever A, its range cut into equal slices"),
    ("Dial B", "Lever B"),
    ("Cut each dial ", "Cut each range "),
    ("of every dial, so no part of a range is left out", "of every range, so nothing is left out"),
    ("Mix the dials ", "Mix the levers "),
    ("The dial at…", "The lever level at…"),
)
done = set()
for s in slides[:32]:
    for sh in s.shapes:
        if sh.has_text_frame:
            for pg in sh.text_frame.paragraphs:
                for r in pg.runs:
                    for a, b in RUNS:
                        if a in r.text:
                            r.text = r.text.replace(a, b)
                            done.add(a)
assert done == {a for a, _ in RUNS}, {a for a, _ in RUNS} - done

NOTES = (
    ("a dial from 0 to 1", "a lever level from 0 to 1"),
    ("Picture: schematic for two dials and 8 slices", "Picture: schematic for two levers and 8 slices"),
    ("The surrogate only understands the dial, but people ask in real terms. So we also have to go the other way, from the dial back",
     "The surrogate only understands the lever level, but people ask in real terms. So we also have to go the other way, from the lever level back"),
    ("the same move on the dial is a different", "the same move in lever level is a different"),
    ("from the real value to the dial and back", "from the real value to the lever level and back"),
    ("(dial 0 and dial 1)", "(lever level 0 and 1)"),
    ("Each line is the lever's dial, from 0 to 1.", "Each line is the lever level, from 0 to 1."),
)
for s in slides[:32]:
    if s.has_notes_slide and s.notes_slide.notes_text_frame:
        tf = s.notes_slide.notes_text_frame
        new = tf.text
        for a, b in NOTES:
            new = new.replace(a, b)
        if new != tf.text:
            tf.text = new


# ---- Walk slide: every value says what it is
def text(s, x, y, w, h, content, size, bold=False, color=GREY, align=None):
    b = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    pg = tf.paragraphs[0]
    if align:
        pg.alignment = align
    r = pg.add_run()
    r.text = content
    r.font.name, r.font.size, r.font.bold = "IBM Plex Sans", Pt(size), bold
    r.font.color.rgb = RGBColor.from_string(color)
    return b


s = slides[18]
by = {x.shape_id: x for x in s.shapes}
assert "same walk" in by[3].text_frame.text
set_tx = lambda sh, t: (sh.text_frame.paragraphs[0].runs[0].__setattr__("text", t))
set_tx(by[55], "the links, plus the values")
cells = ((56, 57, 58, "Electric share", "lever at 0", "50%", "lever at 1", "72%"),
         (59, 60, 61, "Diesel share", "lever at 0", "17%", "lever at 1", "10%"),
         (62, 63, 64, "Diesel km, billion", "lever low", "8.96", "lever high", "7.36"),
         (65, 66, 67, "CO₂, Mt", "lever low", "9.70", "lever high", "8.98"),
         (68, 69, 70, "CO₂e, Mt", "lever low", "9.9", "lever high", "9.1"))
added = []
for bg, lab, val, name, l1, v1, l2, v2 in cells:
    x, w = by[bg].left / 914400 + 0.12, by[bg].width / 914400 - 0.24
    set_tx(by[lab], name)
    by[lab].left, by[lab].top, by[lab].width = Inches(x), Inches(7.3), Inches(w)
    by[lab].text_frame.paragraphs[0].runs[0].font.size = Pt(20)
    by[lab].text_frame.paragraphs[0].runs[0].font.bold = True
    by[val]._element.getparent().remove(by[val]._element)
    for y, l, v in ((7.8, l1, v1), (8.35, l2, v2)):
        added += [text(s, x, y + 0.06, 1.5, 0.4, l, 18),
                  text(s, x + 1.2, y, w - 1.2, 0.5, v, 26, True, BLUE, PP_ALIGN.RIGHT)]
foot = text(s, 1.15, 9.77, 18.24, 0.36, "Shares: the input at each end of the lever. The rest: median of the runs with the lever in its lowest and highest third · 2050", 18, color=MUTE)

# rebuild the three clicks without the removed shapes
for t in s._element.findall(f"{{{P_NS}}}timing"):
    s._element.remove(t)
ids = {x.shape_id: x for x in s.shapes}
clicks = [[ids[i] for i in range(40, 53)],
          [ids[i] for i in range(53, 71) if i in ids] + added + [foot],
          [ids[75]]]
n, body, used = 2, [], []


def nid():
    global n
    n += 1
    return n


for group in clicks:
    outer, inner, effects = nid(), nid(), []
    for k, sh in enumerate(group):
        used.append(sh.shape_id)
        effects.append(
            f'<p:par><p:cTn id="{nid()}" presetID="1" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" '
            f'nodeType="{"clickEffect" if k == 0 else "withEffect"}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:set><p:cBhvr><p:cTn id="{nid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            f'<p:tgtEl><p:spTgt spid="{sh.shape_id}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName>'
            f'</p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set></p:childTnLst></p:cTn></p:par>')
    body.append(f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
                f'<p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                f'{"".join(effects)}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
bld = "".join(f'<p:bldP spid="{i}" grpId="0" animBg="1"/>' for i in used)
el = etree.fromstring(
    f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
    f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>{"".join(body)}'
    f'</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
    f'<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst>'
    f'</p:cTn></p:par></p:tnLst><p:bldLst>{bld}</p:bldLst></p:timing>')
ext = s._element.find(f"{{{P_NS}}}extLst")
if ext is not None:
    ext.addprevious(el)
else:
    s._element.append(el)

# ---- nothing called a dial is left in the talk
left = []
for i, sl in enumerate(slides[:32], 1):
    parts = [x.text_frame.text for x in sl.shapes if x.has_text_frame]
    if sl.has_notes_slide and sl.notes_slide.notes_text_frame:
        parts.append(sl.notes_slide.notes_text_frame.text)
    left += [(i, a[:70]) for a in parts if re.search(r"\bdials?\b", a, re.I)]
assert not left, left
p.save(OUT)
print("saved", OUT)
