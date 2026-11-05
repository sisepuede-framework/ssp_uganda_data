"""Slide 3: the tool is about engagement, not replacing analysts.

    python deck_1104_v4.py docs/DMDU_2026_Talk_draft_models_1104_video_v3.pptx \
                           docs/DMDU_2026_Talk_draft_models_1104_video_v4.pptx
"""
import os
import sys

from pptx import Presentation

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")
p = Presentation(SRC)
hits = 0
for sh in p.slides[2].shapes:
    if sh.has_text_frame:
        for pg in sh.text_frame.paragraphs:
            if "no analyst" in pg.text:
                for extra in pg.runs[1:]:
                    extra._r.getparent().remove(extra._r)
                pg.runs[0].text = "Engage with the model directly, in plain language"
                hits += 1
assert hits == 1
p.save(OUT)
