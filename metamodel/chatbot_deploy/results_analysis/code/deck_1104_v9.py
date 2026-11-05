"""Slide 3: the bullets beside the video take the deck's style (thin rule, bold heading, grey line).

    python deck_1104_v9.py docs/DMDU_2026_Talk_draft_models_1104_video_v8.pptx \
                           docs/DMDU_2026_Talk_draft_models_1104_video_v9.pptx
"""
import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")
p = Presentation(SRC)
s = p.slides[2]
old = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.startswith("Ask for scenarios")]
assert len(old) == 1
x, w = old[0].left / 914400, 18.85 - old[0].left / 914400
old[0]._element.getparent().remove(old[0]._element)


def text(y, h, content, size, bold, color):
    b = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = b.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    r = tf.paragraphs[0].add_run()
    r.text = content
    r.font.name, r.font.size, r.font.bold = "IBM Plex Sans", Pt(size), bold
    r.font.color.rgb = RGBColor.from_string(color)


for y, head, line in ((2.43, "Beyond the official pathways", "Ask for scenarios outside the NDC pathways"),
                      (5.0, "Direct engagement", "Engage with the model in plain language"),
                      (7.2, "Fast answers", "Emissions, costs and benefits together")):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.03))
    r.shadow.inherit = False
    r.fill.solid()
    r.fill.fore_color.rgb = RGBColor.from_string("16181D")
    r.line.fill.background()
    text(y + 0.2, 1.0, head, 25, True, "16181D")
    text(y + (1.2 if len(head) > 20 else 0.8), 1.1, line, 21, False, "5B606B")
p.save(OUT)
print("saved", OUT)
