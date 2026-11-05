"""Walk slide on the saved _v7: Map shows only names and units as the agent sees them; every Map+ box has the same labels and,
except the sector total, the same scope (cars and vans). Values: ranges(run, 2050), lever 35, no uncertainty filter.

    python deck_1104_v8.py docs/DMDU_2026_Talk_draft_models_1104_video_v7.pptx \
                           docs/DMDU_2026_Talk_draft_models_1104_video_v8.pptx
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
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
p = Presentation(SRC)
s = list(p.slides)[18]
by = {x.shape_id: x for x in s.shapes}
assert "same walk" in by[3].text_frame.text


def put(sh, t, size=None):
    runs = sh.text_frame.paragraphs[0].runs
    for extra in runs[1:]:
        extra._r.getparent().remove(extra._r)
    runs[0].text = t
    if size:
        runs[0].font.size = Pt(size)


# ---- clicks as they are, before changing anything
timing = s._element.find(f"{{{P_NS}}}timing")
clicks = []
for c in timing.iter(f"{{{P_NS}}}cTn"):
    k = c.get("nodeType")
    if k in ("clickEffect", "withEffect", "afterEffect"):
        sh = by[int(c.find(f".//{{{P_NS}}}spTgt").get("spid"))]
        if k == "clickEffect":
            clicks.append([sh])
        else:
            clicks[-1].append(sh)

# ---- Map: variable name and unit only
put(by[42], "names and units")
for sid, name, unit in ((44, "Shift FUEL LIGHT DUTY", "level, 0–1"),
                        (46, "Transportation Mode Fuel Fraction Diesel", "fraction, 0–1"),
                        (48, "Vehicle Distance Traveled from Diesel", "vehicle-km"),
                        (50, "CO₂ Emissions from Transportation", "Mt CO₂e"),
                        (52, "Transportation", "Mt CO₂e")):
    put(by[sid], name, 20)
    b = s.shapes.add_textbox(by[sid].left, Inches(6.62), by[sid].width, Inches(0.36))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    r = tf.paragraphs[0].add_run()
    r.text = unit
    r.font.name, r.font.size = "IBM Plex Sans", Pt(18)
    r.font.color.rgb = RGBColor.from_string("5B606B")
    clicks[0].append(b)

# ---- Map+: one set of labels; cars and vans except the sector total
put(by[55], "the same, plus the values")
REPL = {"lever at 0": "lever low", "lever at 1": "lever high", "8.96": "5.31", "7.36": "3.69", "9.70": "2.71", "8.98": "1.88",
        "CO₂e, Mt": "All transport, Mt"}
n = 0
for x in s.shapes:
    if x.has_text_frame and x.text_frame.text.strip() in REPL:
        put(x, REPL[x.text_frame.text.strip()])
        n += 1
assert n == 9, n
foot = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.startswith("Shares:")][0]
put(foot, "Cars and vans, 2050. Shares: the input at each end of the lever. The rest: median of the runs in the lever's lowest and highest third")

s.notes_slide.notes_text_frame.text = (
    "When speaking, note that this is showing the path from the previous two slides.\n\n"
    "When the agent gets a question it can call the model_network tool and navigate the network. With Map, it only sees the names "
    "and units, and the links between them. With Map+, it also sees the values of each variable. That path across the network is "
    "for lever 35.\n\n"
    "What the numbers are, for Q&A. All are 2050. Electric and diesel share: the input with the lever level at 0 and at 1, for cars "
    "and vans; the tool gives a lever's inputs at the ends of its range. Diesel km and CO₂: the median of the runs with the lever in "
    "its lowest third and highest third, for cars and vans (fields vehicle_distance_traveled_trns_road_light_diesel and "
    "emission_co2e_co2_trns_road_light). All transport: the Transportation category, same thirds. Every other lever and uncertainty "
    "varies, so they are not one run: the sector's 9.9 has a p10-p90 of 7.6-13.0.")

# ---- same clicks, with the units in the first one
s._element.remove(timing)
i, body, used = 2, [], []


def nid():
    global i
    i += 1
    return i


for group in clicks:
    outer, inner, eff = nid(), nid(), []
    for k, sh in enumerate(group):
        used.append(sh.shape_id)
        eff.append(f'<p:par><p:cTn id="{nid()}" presetID="1" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" '
                   f'nodeType="{"clickEffect" if k == 0 else "withEffect"}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                   f'<p:set><p:cBhvr><p:cTn id="{nid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                   f'<p:tgtEl><p:spTgt spid="{sh.shape_id}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName>'
                   f'</p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set></p:childTnLst></p:cTn></p:par>')
    body.append(f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst><p:par>'
                f'<p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>{"".join(eff)}</p:childTnLst>'
                f'</p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
bld = "".join(f'<p:bldP spid="{x}" grpId="0" animBg="1"/>' for x in used)
el = etree.fromstring(
    f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
    f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>{"".join(body)}</p:childTnLst>'
    f'</p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst>'
    f'<p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par>'
    f'</p:tnLst><p:bldLst>{bld}</p:bldLst></p:timing>')
ext = s._element.find(f"{{{P_NS}}}extLst")
if ext is not None:
    ext.addprevious(el)
else:
    s._element.append(el)
p.save(OUT)
print("saved", OUT)
