"""Slide 18: say which scale the thirds are on. On Alexa's saved v10 (her edits to slides 8, 12, 13 kept).

    python deck_1104_v11.py docs/DMDU_2026_Talk_draft_models_1104_video_v10_alexa.pptx \
                            docs/DMDU_2026_Talk_draft_models_1104_video_v11.pptx
"""
import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Pt

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")
p = Presentation(SRC)
s = p.slides[17]
hits = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.strip() == "When each lever is low, middle or high"]
assert len(hits) == 1
tf = hits[0].text_frame
tf.paragraphs[0].runs[0].text = "For each third of the lever's 0–1 range"
pg = tf.add_paragraph()
pg.space_before = Pt(4)
r = pg.add_run()
r.text = "low 0–0.33 · middle 0.33–0.67 · high 0.67–1, as sampled in the Latin hypercube"
r.font.name, r.font.size, r.font.bold = "IBM Plex Sans", Pt(20), False
r.font.color.rgb = RGBColor.from_string("5B606B")
p.save(OUT)
print("saved", OUT)
