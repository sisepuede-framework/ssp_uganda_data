"""
Generate docs/ui_text_inventory.md — every word the tool shows on screen, plus the
exact question each button sends to the assistant.

Why
---
The experts review wording in Word, with the comment tool. They cannot click through
the app, and a hand-typed transcript drifts the moment the UI changes. So this reads
the REAL sources — frontend/index.html for static copy, frontend/app.js for the
question templates, feature_registry.json for the levers and conditions, and the
stored CDPM runs for the card figures — and writes one document.

Usage
-----
    # needs the project env (pandas / boto3) because it reads the stored runs:
    /opt/miniconda3/envs/uganda_metamodel_env/bin/python backend/scripts/build_ui_text_inventory.py
    # then, for the Word version (python-docx lives in the base env):
    python backend/scripts/md_to_docx.py docs/ui_text_inventory.md

Regenerate after ANY wording change, then re-send the .docx.
"""

import html
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

INDEX = REPO_ROOT / "frontend" / "index.html"
APP_JS = REPO_ROOT / "frontend" / "app.js"
REGISTRY = REPO_ROOT / "backend" / "feature_registry.json"
OUT = REPO_ROOT / "docs" / "ui_text_inventory.md"

# Question templates. These MIRROR app.js — the assertions below fail loudly if the
# code changes and this file does not.
LEVER_Q = ('What does the "{name}" lever ({sector}) actually change in the model, and what happens to '
           'emissions, costs and development benefits at the ambitious end of its range?')
SECTOR_Q = ('What can Uganda change in the {sector} sector, and what would the ambitious end of the '
            'range there do to emissions, costs and development benefits?')
CONDITION_Q = ('What happens to emissions, costs and development benefits if {name} sits at '
               'the high end of its uncertainty range instead of the median future?')
CONDITION_CHIP_Q = ('What happens to emissions, costs and development benefits if {name} sits at the '
                    'high end of its uncertainty range instead of the median future?')
SECTOR_CHIP_Q = ('What can Uganda change in the {sector} sector, and what would the ambitious end of '
                 'the range there do to emissions, costs and development benefits?')

CHIPS_SHOWN = 6          # mirrors app.js
X_HEADLINE = [57, 60, 56, 55]

# Markup patterns, hoisted out of the f-strings below (Python 3.11 forbids
# backslashes inside f-string expressions).
RE_TITLE = r"<title>(.*?)</title>"
RE_H1 = r"<h1>(.*?)</h1>"
RE_PANEL_TITLE = r'class="panel-title">(.*?)</h2>'
RE_PANEL_LEDE = r'class="panel-lede">(.*?)</p>'
RE_PROV_BADGE = r'class="prov-badge[^"]*">(.*?)</span>'
RE_CHIP_LABEL = r'class="chip-row-label">(.*?)</span>'
RE_INTRO_HEADLINE = r'class="intro-headline">(.*?)</h2>'
RE_DOC_TITLE = r'class="doc-title">(.*?)</h2>'
RE_DOC_LEDE = r'class="doc-lede">(.*?)</p>'
RE_DOC_H = r'class="doc-h">(.*?)</h3>'
RE_DOC_P = r'class="doc-p[^"]*">(.*?)</p>'
RE_FILTER_PH = r'id="lever-filter"[^>]*placeholder="([^"]*)"'


# ── helpers ──────────────────────────────────────────────────────────────────

def strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = " ".join(html.unescape(text).split())
    # Inline tags leave a space before punctuation ("(CDPM) , built") — close it up.
    return re.sub(r"\s+([,.;:!?%])", r"\1", text)


def one(pattern: str, source: str, label: str) -> str:
    match = re.search(pattern, source, re.S)
    if not match:
        raise SystemExit(f"Could not find {label} in the source — has the markup changed?")
    return strip_tags(match.group(1))


def panel(source: str, panel_id: str) -> str:
    """The full markup of one tab panel, counting nested <section> tags — the
    reference tab wraps each part in its own <section>, so stopping at the first
    closing tag silently swallowed most of it."""
    start = source.index(f'id="{panel_id}"')
    depth = 1   # the panel's own <section> opened just before `start`
    for match in re.finditer(r"<section\b|</section>", source[start:]):
        depth += 1 if match.group(0).startswith("<section") else -1
        if depth <= 0:
            return source[start:start + match.start()]
    return source[start:]


def buttons(fragment: str) -> list[tuple[str, str]]:
    """[(label shown, question sent)] for every data-ask button in a fragment."""
    found = re.findall(r'<button class="q-(?:chip|btn)"\s+data-ask="([^"]*)"[^>]*>(.*?)</button>',
                       fragment, re.S)
    return [(strip_tags(lbl), html.unescape(q)) for q, lbl in found]


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    esc = lambda c: str(c).replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    out += ["| " + " | ".join(esc(c) for c in row) + " |" for row in rows]
    out.append("")
    return out


# ── sources ──────────────────────────────────────────────────────────────────

index_html = INDEX.read_text()
app_js = APP_JS.read_text()
registry = json.loads(REGISTRY.read_text())

for snippet, what in [
    # Keep snippets short enough to sit inside ONE app.js string literal — the
    # templates there are split across concatenated lines.
    ('actually change in the model', "the lever Ask question"),
    ("What can Uganda change in the", "the sector question"),
    ("high end of its uncertainty range instead of the median future", "the condition question"),
]:
    if snippet not in app_js:
        raise SystemExit(f"app.js no longer contains {what} — update the templates in this script.")

levers = list(registry["lever_features"].values())
exogenous = sorted(registry["exogenous_features"].values(), key=lambda x: x["group_id"])

by_sector: dict[str, list[dict]] = {}
for lever in levers:
    by_sector.setdefault(lever["sector"], []).append(lever)
sectors = sorted(by_sector.items(), key=lambda kv: (-len(kv[1]), kv[0]))

from backend.services import pathways_lookup   # noqa: E402  (after sys.path setup)
cards = pathways_lookup.build_pathway_cards()

pathway_presets = dict(re.findall(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)",\s*$',
                                  app_js[app_js.index("const PATHWAY_PRESETS"):
                                         app_js.index("/** Put text in the input")], re.M))
tab_meta = app_js[app_js.index("const TAB_META"):app_js.index("function switchTab")]
placeholders = {}
for key, body in re.findall(r"(\w+):\s*\{(.*?)\},", tab_meta, re.S):
    found = re.search(r'placeholder:\s*"((?:[^"\\]|\\.)*)"', body)
    if found:
        placeholders[key] = found.group(1)


# ── build the document ───────────────────────────────────────────────────────

L: list[str] = []
A = L.append

A("# What the tool says — full text inventory")
A("")
A("**Uganda Climate Pathways Explorer · generated 29 July 2026**")
A("")
A("Every word the tool displays, and — for each button — the exact question it sends to the "
  "assistant on the user's behalf. Please comment directly on any wording you would change, using "
  "Word's comment tool.")
A("")
A("Two things worth knowing while you read:")
A("")
A("- The questions under each button are **what the assistant receives**, not what the user sees. "
  "They are written to route correctly (naming a pathway exactly, for instance) as well as to read "
  "naturally, so if you rewrite one, keep any pathway or sector name intact.")
A("- This document is generated from the running code. If you change wording in it, the change has "
  "to be made in the app as well — mark it clearly and we will apply it.")
A("")
A("---")
A("")

# ── 1. Everywhere ────────────────────────────────────────────────────────────
A("## 1. Names and labels used everywhere")
A("")
A(f"**Browser tab title:** {one(RE_TITLE, index_html, 'the page title')}")
A("")
A(f"**Tool name, shown in the header:** {one(RE_H1, index_html, 'the tool name')}")
A("")
A("**The three tabs, left to right:**")
A("")
tab_rows = []
for key, label in re.findall(r'data-tab="(\w+)"[^>]*>(.*?)</button>', index_html, re.S):
    # The reference tab has no input at all — questions there open in Explore.
    box = "no input on this tab" if key == "how" else placeholders.get(key, "—")
    tab_rows.append([strip_tags(label), box])
L.extend(md_table(["Tab label", "What the input box says on that tab"], tab_rows))

A("**The control that folds the top section away:** “Hide ▴”, becoming “Show pathways ▾”, "
  "“Show questions ▾” or “Show reference ▾” depending on the tab.")
A("")
A("**Under every answer:** a badge — “◆ Official pathway result” or “≈ Metamodel estimate” — and a "
  "collapsible panel headed **“How I got this answer”**, listing the steps that were actually run.")
A("")

# ── 2. Tab 1 ─────────────────────────────────────────────────────────────────
official = panel(index_html, "panel-official")
A("## 2. Tab 1 — Official pathways")
A("")
A(f"**Section heading:** {one(RE_PANEL_TITLE, official, 'tab 1 title')}")
A("")
A(f"**Section text:** {one(RE_PANEL_LEDE, official, 'tab 1 lede')}")
A("")
A(f"**Badge on this section:** {one(RE_PROV_BADGE, official, 'tab 1 badge')}")
A("")
A("### 2.1 The six pathway cards")
A("")
A("Each card shows a name, a one-line description, its emissions trajectory as a small chart, and its "
  "2070 net emissions with the change against BAU. **The descriptions are drafts and need your "
  "sign-off.** Figures come from the stored runs and are shown here for context, not for comment.")
A("")
L.extend(md_table(
    ["Name shown", "Description shown", "2070 figure", "vs BAU"],
    [[c["short_label"], c["description"], f'{c["net_2070"]} {c["unit"]}',
      "baseline" if c["pct_vs_bau_2070"] is None else f'{c["pct_vs_bau_2070"]:+.1f}%']
     for c in cards],
))
A("**What clicking a card asks the assistant:**")
A("")
L.extend(md_table(["Card", "Question sent"],
                  [[name, pathway_presets.get(name, "—")] for name in pathway_presets]))

A("### 2.2 “Or ask across all six”")
A("")
A(f"**Row label:** {one(RE_CHIP_LABEL, official, 'chip row label')}")
A("")
L.extend(md_table(["Button text", "Question sent"], [[lbl, q] for lbl, q in buttons(official)]))

intro_official = index_html[index_html.index('id="intro-official"'):index_html.index('id="intro-explore"')]
A("### 2.3 The assistant's opening message on this tab")
A("")
A(f"> **{one(RE_INTRO_HEADLINE, intro_official, 'tab 1 headline')}**")
A(">")
for para in re.findall(r"<p>(.*?)</p>", intro_official, re.S):
    A(f"> {strip_tags(para)}")
A("")

# ── 3. Tab 2 ─────────────────────────────────────────────────────────────────
explore = panel(index_html, "panel-explore")
A("## 3. Tab 2 — Explore")
A("")
A(f"**Section heading:** {one(RE_PANEL_TITLE, explore, 'tab 2 title')}")
A("")
A(f"**Section text:** {one(RE_PANEL_LEDE, explore, 'tab 2 lede')}")
A("")
A(f"**Badge on this section:** {one(RE_PROV_BADGE, explore, 'tab 2 badge')}")
A("")

col_heads = [strip_tags(h) for h in re.findall(r"<h3>(.*?)</h3>", explore, re.S)]
col_subs = [strip_tags(p) for p in re.findall(r'class="explore-sub">(.*?)</p>', explore, re.S)]
counts = [strip_tags(c) for c in re.findall(r'class="explore-count"[^>]*>(.*?)</span>', explore, re.S)]
explore_buttons = buttons(explore)

A("### 3.1 Left column — ambition")
A("")
A(f"**Heading:** {col_heads[0]}  ·  **Counter shown:** {counts[0]}")
A("")
A(f"**Sub-line:** {col_subs[0]}")
A("")
L.extend(md_table(["Button text", "Question sent"], [[l, q] for l, q in explore_buttons[:3]]))

A("### 3.2 Right column — conditions")
A("")
A(f"**Heading:** {col_heads[1]}  ·  **Counter shown:** {counts[1]}")
A("")
A(f"**Sub-line:** {col_subs[1]}")
A("")
L.extend(md_table(["Button text", "Question sent"], [[l, q] for l, q in explore_buttons[3:]]))

A("### 3.3 The small sector chips (left column)")
A("")
A(f"The first {CHIPS_SHOWN} sectors are shown, then a chip reading "
  f"“{len(sectors) - CHIPS_SHOWN} more sectors” reveals the rest. Each chip shows the sector name and "
  "its number of levers.")
A("")
L.extend(md_table(["Chip", "Question sent"],
                  [[f'{s} {len(g)}', SECTOR_CHIP_Q.format(sector=s)] for s, g in sectors[:CHIPS_SHOWN]]))

A("### 3.4 The small condition chips (right column)")
A("")
chip_order = sorted(exogenous, key=lambda x: (X_HEADLINE.index(x["group_id"])
                                              if x["group_id"] in X_HEADLINE
                                              else len(X_HEADLINE) + x["group_id"]))
A(f"The first {CHIPS_SHOWN} are shown, then “{len(exogenous) - CHIPS_SHOWN} more” reveals the rest.")
A("")
L.extend(md_table(["Chip", "Question sent"],
                  [[x["display_name"], CONDITION_CHIP_Q.format(name=x["display_name"])]
                   for x in chip_order[:CHIPS_SHOWN]]))

intro_explore = index_html[index_html.index('id="intro-explore"'):index_html.index("<!-- No intro for")]
A("### 3.5 The assistant's opening message on this tab")
A("")
A(f"> **{one(RE_INTRO_HEADLINE, intro_explore, 'tab 2 headline')}**")
A(">")
for para in re.findall(r"<p>(.*?)</p>", intro_explore, re.S):
    A(f"> {strip_tags(para)}")
A("")

# ── 4. Tab 3 ─────────────────────────────────────────────────────────────────
how = panel(index_html, "panel-how")
A("## 4. Tab 3 — How this works")
A("")
A("This tab is a reference document: no conversation on it. Every lever, sector and condition carries "
  "an **Ask** button, which opens the question in Explore.")
A("")
A("**Section list down the left:** " +
  " · ".join(strip_tags(x) for x in re.findall(r'class="doc-nav-link"[^>]*>(.*?)</button>', how, re.S)))
A("")
A(f"**Page title:** {one(RE_DOC_TITLE, how, 'doc title')}")
A("")
A(f"**Page introduction:** {one(RE_DOC_LEDE, how, 'doc lede')}")
A("")

sections = re.findall(r'<section id="(sec-[\w-]+)">(.*?)</section>', how, re.S)
# One pass in document order, so the transcript matches what the reader sees
# (paragraph before its definitions in one section, cards before the note in another).
IN_ORDER = re.compile(
    r'class="prov-badge[^"]*">(?P<badge>.*?)</span>\s*<p>(?P<badge_text>.*?)</p>'
    r'|<dt>(?P<dt>.*?)</dt>\s*<dd>(?P<dd>.*?)</dd>'
    r'|class="doc-p[^"]*">(?P<para>.*?)</p>',
    re.S,
)

for _, body in sections:
    heading = one(RE_DOC_H, body, "a section heading")
    A(f"### {heading}")
    A("")
    for m in IN_ORDER.finditer(body):
        if m.group("badge") is not None:
            A(f'- **{strip_tags(m.group("badge"))}** — {strip_tags(m.group("badge_text"))}')
            A("")
        elif m.group("dt") is not None:
            key = re.sub(r"^([LX])\s+", r"\1 — ", strip_tags(m.group("dt")))
            A(f'- **{key}** — {strip_tags(m.group("dd"))}')
            A("")
        else:
            A(strip_tags(m.group("para")))
            A("")
    if 'id="lever-filter"' in body:
        placeholder = one(RE_FILTER_PH, body, "the filter placeholder")
        A(f"**Filter box placeholder:** {placeholder}")
        A("")
    A("")

A("### 4.1 Every lever, and what its Ask button asks")
A("")
A(f"{len(levers)} levers across {len(sectors)} sectors. Each sector heading also has an "
  "“Ask about this sector” button.")
A("")
for sector, group in sectors:
    A(f"#### {sector} ({len(group)} levers)")
    A("")
    A(f"*“Ask about this sector” sends:* {SECTOR_Q.format(sector=sector)}")
    A("")
    L.extend(md_table(
        ["ID", "Lever name shown", "Question its Ask button sends"],
        [[l["group_id"], l["display_name"], LEVER_Q.format(name=l["display_name"], sector=l["sector"])]
         for l in sorted(group, key=lambda x: x["group_id"])],
    ))

A("### 4.2 Every condition, and what its Ask button asks")
A("")
L.extend(md_table(
    ["ID", "Name shown", "Domain shown", "Question its Ask button sends"],
    [[x["group_id"], x["display_name"], x["sector"].replace("Exogenous / ", ""),
      CONDITION_Q.format(name=x["display_name"])] for x in exogenous],
))

# ── 5. Chart labels ──────────────────────────────────────────────────────────
from backend.services.predictor import COST_BENEFIT_LABELS   # noqa: E402
sector_meta = json.loads((REPO_ROOT / "backend" / "sector_categories.json").read_text())

A("## 5. Labels inside the charts")
A("")
A("**Panel titles:** “Business as Usual” (left) and “Selected pathway” (right); the cost chart is "
  "titled “Annual Cost & Benefit by Year (Selected pathway)”. **Axis labels:** “Mt CO₂e / yr” and "
  "“Billion USD / yr”. **Reference lines:** “Real BAU net” and “HBLE net (frontier)”.")
A("")
A(f"**The {len(sector_meta)} emission categories in the legend:** " +
  " · ".join(sorted(v.get("display", k) for k, v in sector_meta.items())))
A("")
A("**The cost and benefit types in the legend:** " + " · ".join(COST_BENEFIT_LABELS.values()))
A("")

OUT.write_text("\n".join(L) + "\n")
print(f"Wrote {OUT.relative_to(REPO_ROOT)} — {len(L)} lines, {len(levers)} levers, "
      f"{len(exogenous)} conditions, {len(cards)} pathway cards.")
