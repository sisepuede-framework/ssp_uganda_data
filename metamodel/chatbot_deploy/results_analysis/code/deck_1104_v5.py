"""Engagement wording on slides 3 (title) and 10 (box 4): the tool does not replace technical people.

    python deck_1104_v5.py docs/DMDU_2026_Talk_draft_models_1104_video_v4.pptx \
                           docs/DMDU_2026_Talk_draft_models_1104_video_v5.pptx
"""
import os
import sys

from pptx import Presentation

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")
p = Presentation(SRC)
for idx, old, new in ((2, "Using a model now requires no technical expertise", "Engaging with a model no longer requires technical expertise"),
                      (9, "Stands in for the technical expertise", "Makes the technical expertise accessible")):
    hits = [sh for sh in p.slides[idx].shapes if sh.has_text_frame and sh.text_frame.text.strip() == old]
    assert len(hits) == 1, old
    runs = hits[0].text_frame.paragraphs[0].runs
    for extra in runs[1:]:
        extra._r.getparent().remove(extra._r)
    runs[0].text = new
p.save(OUT)
