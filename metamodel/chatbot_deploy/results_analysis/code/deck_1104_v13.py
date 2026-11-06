"""Slide 32: say which model is which in the scope box, and that the explanations to check are the ones the agent gives
the user. On Alexa's edited v12 (her changes to slides 5, 15, 21 and 32 kept).

    python deck_1104_v13.py docs/DMDU_2026_Talk_draft_models_1104_video_v12.pptx \
                            docs/DMDU_2026_Talk_draft_models_1104_video_v13.pptx
"""
import os
import sys

from pptx import Presentation

SRC, OUT = sys.argv[1], sys.argv[2]
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists: reviewed files are never overwritten")
p = Presentation(SRC)
s = p.slides[31]


def box(start):
    hits = [x for x in s.shapes if x.has_text_frame and x.text_frame.text.startswith(start)]
    assert len(hits) == 1, start
    return hits[0]


def set_para(pg, new):
    runs = [r for r in pg.runs if r.font.size is not None] or pg.runs
    keep = runs[0]
    for r in list(pg.runs):
        if r._r is not keep._r:
            r._r.getparent().remove(r._r)
    keep.text = new


scope = box("One model and one country").text_frame.paragraphs
assert scope[1].text.strip() == "One agent model"
set_para(scope[0], "One simulation model (SISEPUEDE) and one country (Uganda)")
set_para(scope[1], "One AI model as the agent's brain (Claude Sonnet 5.5)")

nxt = box("Sessions with real users").text_frame.paragraphs
assert nxt[1].text.strip() == "Checking the agent’s explanations"
set_para(nxt[1], "Checking the agent’s explanations to the user")

p.save(OUT)
print("saved", OUT)
