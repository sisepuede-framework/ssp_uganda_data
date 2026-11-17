"""
working_paper_v2.py (2026-11-16): copy of working_paper_v1.py for paper v2; adds the pre-registered per-group
 numbers (analysis_*.csv) and the re-analysis (results_analysis/reanalysis_v2.xlsx, from reanalysis_v2.py) to the trace.
-------------------
Builds the Overleaf project for the DMDU 2026 working paper.

  1. Recomputes every result number the paper quotes, from results_analysis/*.xlsx and the surrogate metrics,
     and stops if one differs from the number written in main.tex (number trace).
  2. Draws the three result figures (PDF, Times New Roman) into docs/DMDU_2026_working_paper_v2/figures/.
  3. Checks main.tex + references.bib: balanced braces and environments, every \\cite in the .bib,
     every \\ref has a \\label, every figure exists, no raw non-ASCII, no banned terms; lists every \\todo.
  4. Zips the folder to docs/DMDU_2026_working_paper_v2.zip (Overleaf: New project -> Upload project).

main.tex and references.bib are written by hand in the project folder; this script never overwrites them.

Run (needs scipy):  /opt/miniconda3/envs/uganda_metamodel_env/bin/python results_analysis/code/working_paper_v2.py
"""
import os
import re
import sys
import zipfile

import matplotlib
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))          # chatbot_deploy/
RES = os.path.join(ROOT, "results_analysis")
PROJ = os.path.join(ROOT, "docs", "DMDU_2026_working_paper_v2")
FIG = os.path.join(PROJ, "figures")
ZIP = PROJ + ".zip"
SURR = os.path.abspath(os.path.join(ROOT, "..", "surrogate_model_sector", "trained_models"))
RUN_ID = "2026-05-30t21;35;56.244639"

MAP, MAPP = "#eb6834", "#2a78d6"   # categorical slots 2 and 1 of the validated default palette
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})

conv = pd.read_excel(os.path.join(RES, "full_run_analysis.xlsx"), sheet_name="Conversations")
calls = pd.read_excel(os.path.join(RES, "full_run_analysis.xlsx"), sheet_name="Tool calls")
levers = pd.read_excel(os.path.join(RES, "full_run_analysis.xlsx"), sheet_name="Lever settings")
walk = pd.read_excel(os.path.join(RES, "walk_depth.xlsx"), sheet_name="Summary")


# ---------------------------------------------------------------- 1. numbers
def units(check, parts=("Q10b", "D2b", "N1")):
    """Failures and applicable units per arm. The three-question conversation counts as its parts."""
    rows = []
    for _, r in conv.iterrows():
        if pd.notna(r.get(check)):
            rows.append((r.arm, r[check]))
        for p in parts:
            k = f"{p}:{check}"
            if k in conv and pd.notna(r[k]):
                rows.append((r.arm, r[k]))
    d = pd.DataFrame(rows, columns=["arm", "v"])
    g = d.groupby("arm").v.agg(["sum", "count"])
    out = {a: (int(g.loc[a, "sum"]), int(g.loc[a, "count"])) for a in ("v0", "v1")}
    tab = [[out[a][0], out[a][1] - out[a][0]] for a in ("v0", "v1")]
    return out, fisher_exact(tab)[1]


N = {}
for key, col in [("offkey", "03_level_off_key"), ("literal", "02_literal_translation"),
                 ("untraced", "15_untraced_numbers"), ("skipped", "08_required_step_skipped"),
                 ("mention", "19_mention_missing"), ("threshold", "07_invented_threshold"),
                 ("finish", "12_did_not_finish"), ("forecast", "13_forecast_language"),
                 ("winner", "14_names_a_winner"), ("node", "25_required_node_not_visited")]:
    N[key] = units(col)

n_units = N["untraced"][0]["v0"][1]                       # 155 questions asked per arm
mn = conv.groupby("arm").n_model_network.sum()
N["calls_per_q"] = (mn["v0"] / n_units, mn["v1"] / n_units)
N["calls_p"] = mannwhitneyu(conv[conv.arm == "v0"].n_model_network, conv[conv.arm == "v1"].n_model_network).pvalue
hyp = conv[conv.tag == "hypothesis"].groupby("arm")["15_untraced_numbers"].sum()
WALK_QS = ["S35", "HD1", "S50", "S3"]          # answer is an in-between quantity (HA1 is reported elsewhere)
w = walk[walk.question.isin(WALK_QS)].groupby("arm").reached_target.sum()
N["walk"] = (int(w["v0"]), int(w["v1"]), fisher_exact([[w["v0"], 20 - w["v0"]], [w["v1"], 20 - w["v1"]]])[1])

surr = open(os.path.join(SURR, f"metrics_{RUN_ID}_summary.md")).read()

# v2: the pre-registered analysis (per group, permutation within question) and the exploratory re-analysis
BANK = os.path.join(ROOT, "backend", "rdm", "eval", "pilot_runs", "bank_v3_full")
ck = pd.read_csv(os.path.join(BANK, "analysis_checks.csv")).set_index(["group", "check"])
prim = pd.read_csv(os.path.join(BANK, "analysis_primary.csv"))
lt = pd.read_csv(os.path.join(BANK, "analysis_long.csv"))
re2 = os.path.join(RES, "reanalysis_v2.xlsx")
summ = pd.read_excel(re2, sheet_name="Summaries").set_index("measure")
prov = pd.read_excel(re2, sheet_name="Provenance (28)")


def grp(group, check):
    r = ck.loc[(group, check)]
    return f"{round(r.v0 * r.n_v0):.0f} of {r.n_v0:.0f} against {round(r.v1 * r.n_v1):.0f} of {r.n_v1:.0f}", r.p


def fails(group, check, kind=None):
    d = lt[(lt.group == group) & (lt.check == check) & ((lt.kind == kind) if kind else True)]
    g = d.groupby("arm").value.agg(["sum", "count"])
    return (f"{g.loc['v0', 'sum']:.0f} of {g.loc['v0', 'count']} & {g.loc['v1', 'sum']:.0f} of "
            f"{g.loc['v1', 'count']}")


def calls_by(group):
    m = lt[(lt.group == group) & (lt.check == "network_calls")].groupby("arm").value.mean()
    return f"{m['v0']:.2f} & {m['v1']:.2f}"


def pfmt(p):
    return "$<0.001$" if p < 0.001 else f"{p:.3f}".rstrip("0") if p < 0.01 else f"{p:.2f}"


pp = prim.set_index(["outcome", "group"]).p
fit = pd.read_csv(os.path.join(SURR, f"rdm_fitness_{RUN_ID}.csv"))
fa, fb, fc, fd = (fit[fit.check == k] for k in ("A threshold", "B region", "C scenario discovery", "D ordering"))
fd = fd.set_index("metric")
codes = prov.groupby(["proposed code", "arm"]).size()

EXPECT = [  # (what, value we compute, text that must appear in main.tex)
    ("conversations", len(conv), "290"),
    ("off key Map", N["offkey"][0]["v0"][0], "59 of 75"),
    ("off key Map+", N["offkey"][0]["v1"][0], "1 of 75"),
    ("literal Map", N["literal"][0]["v0"][0], "30 of 60"),
    ("literal Map+", N["literal"][0]["v1"][0], "0 of 60"),
    ("untraced Map", N["untraced"][0]["v0"][0], "11 of 155"),
    ("untraced Map+", N["untraced"][0]["v1"][0], "17 of 155"),
    ("skipped Map", N["skipped"][0]["v0"][0], "11 of 50"),
    ("skipped Map+", N["skipped"][0]["v1"][0], "6 of 50"),
    ("mention Map", N["mention"][0]["v0"][0], "27 of 40"),
    ("mention Map+", N["mention"][0]["v1"][0], "4 of 40"),
    ("calls Map", round(N["calls_per_q"][0], 2), "2.36"),
    ("calls Map+", round(N["calls_per_q"][1], 2), "1.28"),
    ("hypothesis untraced Map+", int(hyp["v1"]), "5 of 25"),
    ("walk Map", N["walk"][0], "16 of 20"),
    ("walk Map+", N["walk"][1], "7 of 20"),
    ("off key dev", fails("dev", "03_level_off_key", "T1"), "12 of 15 & 1 of 15"),
    ("off key designed", fails("designed", "03_level_off_key", "T1"), "29 of 35 & 0 of 35"),
    ("off key hypothesis", fails("hypothesis", "03_level_off_key", "T1"), "5 of 10 & 0 of 10"),
    ("off key blind", fails("blind", "03_level_off_key", "T1"), "13 of 15 & 0 of 15"),
    ("off key p hypothesis", pfmt(pp[("1 · level off the key (T1)", "hypothesis")]), "0.008"),
    ("calls dev", calls_by("dev"), "2.00 & 1.10"),
    ("calls designed", calls_by("designed"), "2.27 & 1.23"),
    ("calls hypothesis", calls_by("hypothesis"), "3.12 & 1.92"),
    ("calls blind", calls_by("blind"), "2.50 & 1.05"),
    ("untraced dev", grp("dev", "15_untraced_numbers")[0], "3 of 50 against 7 of 50"),
    ("untraced dev p", round(grp("dev", "15_untraced_numbers")[1], 2), "$p = 0.24$"),
    ("untraced designed", grp("designed", "15_untraced_numbers")[0], "7 of 60 against 5 of 60"),
    ("untraced designed p", round(grp("designed", "15_untraced_numbers")[1], 2), "$p = 0.68$"),
    ("untraced hypothesis", grp("hypothesis", "15_untraced_numbers")[0], "0 of 25 against 5 of 25"),
    ("untraced hypothesis p", round(grp("hypothesis", "15_untraced_numbers")[1], 3), "$p = 0.050$"),
    ("skipped dev", grp("dev", "08_required_step_skipped")[0], "5 of 15 against 4 of 15"),
    ("skipped designed", grp("designed", "08_required_step_skipped")[0], "6 of 20 against 2 of 20"),
    ("skipped designed p", round(grp("designed", "08_required_step_skipped")[1], 3), "$p = 0.084$"),
    ("answer valid", (summ.loc["ANSWER: value inside the key", "Map"],
                      summ.loc["ANSWER: value inside the key", "Map+"]), "(7 of 20, against 0 of 20)"),
    ("walk perm p", round(summ.loc["PROCESS: reached the node", "p (permutation within question)"], 3),
     "$p < 0.001$ for the process"),
    ("answer perm p", round(summ.loc["ANSWER: value inside the key", "p (permutation within question)"], 3),
     "$p = 0.001$ for the answer"),
    ("source named", summ.loc["ANSWER: names the source (runs / network)", "Map+"], "20 of 20 answers"),
    ("prov artefact", (int(codes.get(("A", "Map"), 0)), int(codes.get(("A", "Map+"), 0))), "& 4 & 3"),
    ("prov derived", (int(codes.get(("B", "Map"), 0)), int(codes.get(("B", "Map+"), 0))), "& 7 & 13"),
    ("prov wrong", (int(codes.get(("D", "Map"), 0)), int(codes.get(("D", "Map+"), 0))), "& 0 & 1"),
    ("fit agreement", f"{100 * fa.agreement.min():.1f}--{100 * fa.agreement.max():.1f}\\%", "96.9--99.3\\%"),
    ("fit region", f"{100 * fb.abs_diff_share.max():.1f} pp", "0.7 pp"),
    ("fit pair", f"{int(fc.same_pair.sum())} of {len(fc)}", "4 of 4"),
    ("fit order", f"{100 * fd.loc['emissions_total_2050', 'agreement']:.1f}\\% / "
                  f"{100 * fd.loc['cost_total_2050', 'agreement']:.1f}\\%", "97.4\\% / 97.2\\%"),
    ("fit order close", f"{100 * fd.loc['emissions_total_2050', 'agreement_within_2pct']:.1f}\\% / "
                        f"{100 * fd.loc['cost_total_2050', 'agreement_within_2pct']:.1f}\\%", "73.5\\% / 52.5\\%"),
    ("tool calls", len(calls), "1,082"),
    ("tool errors", int((calls.ok == 0).sum()), "eight"),
    ("max requests", int(conv.api_steps.max()), "16 requests"),
    ("invented thresholds", N["threshold"][0]["v0"][0] + N["threshold"][0]["v1"][0], "0"),
    ("not finished", N["finish"][0]["v0"][0] + N["finish"][0]["v1"][0], "0"),
    ("test rows", "19,918" in surr, "19,918"),
    ("R2 all", "| **All** | 215 | 0.9937" in surr, "0.994"),
    ("below 0.8", "| 1.57 | 15 |" in surr, "15 of the 215"),
]
EXPECT_VALUES = {"off key Map": 59, "off key Map+": 1, "literal Map": 30, "literal Map+": 0, "untraced Map": 11,
                 "untraced Map+": 17, "skipped Map": 11, "skipped Map+": 6,
                 "mention Map": 27, "mention Map+": 4, "calls Map": 2.36, "calls Map+": 1.28,
                 "hypothesis untraced Map+": 5, "walk Map": 16, "walk Map+": 7, "tool calls": 1082,
                 "off key dev": "12 of 15 & 1 of 15", "off key designed": "29 of 35 & 0 of 35",
                 "off key hypothesis": "5 of 10 & 0 of 10", "off key blind": "13 of 15 & 0 of 15",
                 "off key p hypothesis": "0.008", "calls dev": "2.00 & 1.10", "calls designed": "2.27 & 1.23",
                 "calls hypothesis": "3.12 & 1.92", "calls blind": "2.50 & 1.05",
                 "untraced dev": "3 of 50 against 7 of 50", "untraced dev p": 0.24,
                 "untraced designed": "7 of 60 against 5 of 60", "untraced designed p": 0.68,
                 "untraced hypothesis": "0 of 25 against 5 of 25", "untraced hypothesis p": 0.05,
                 "skipped dev": "5 of 15 against 4 of 15", "skipped designed": "6 of 20 against 2 of 20",
                 "skipped designed p": 0.084, "answer valid": ("0 of 20", "7 of 20"), "walk perm p": 0.0,
                 "answer perm p": 0.001, "source named": "20 of 20", "prov artefact": (4, 3),
                 "prov derived": (7, 13), "prov wrong": (0, 1),
                 "fit agreement": "96.9--99.3\\%", "fit region": "0.7 pp", "fit pair": "4 of 4",
                 "fit order": "97.4\\% / 97.2\\%", "fit order close": "73.5\\% / 52.5\\%",
                 "tool errors": 8, "max requests": 16, "invented thresholds": 0, "not finished": 0,
                 "conversations": 290, "test rows": True, "R2 all": True, "below 0.8": True}

tex = open(os.path.join(PROJ, "main.tex")).read()
bad = []
print("Number trace (computed -> text in main.tex):")
for what, val, txt in EXPECT:
    ok_val = val == EXPECT_VALUES[what]
    ok_txt = txt in tex
    print(f"  {'ok ' if ok_val and ok_txt else 'BAD'} {what:26s} {val!s:>8}  '{txt}'")
    if not (ok_val and ok_txt):
        bad.append(what)
print(f"  p-values: off key {N['offkey'][1]:.1e}, literal {N['literal'][1]:.1e}, mention {N['mention'][1]:.1e}, "
      f"calls {N['calls_p']:.1e}, node {N['node'][1]:.2f}")


# ---------------------------------------------------------------- 2. figures
os.makedirs(FIG, exist_ok=True)


def fig_translation():
    first = levers[levers.question.isin(["WW1", "P50i"])].copy()
    first = first[first.groupby("conversation").call_no.transform("min") == first.call_no]
    qs = [("WW1", 46, 0.716, "Half of rural households' wastewater to septic tanks"),
          ("P50i", 50, 0.688, "Landfills capture 40% of their methane")]
    fig, axes = plt.subplots(2, 1, figsize=(6.3, 3.3), sharex=True)
    for ax, (q, lev, key, title) in zip(axes, qs):
        d = first[(first.question == q) & (first.lever == lev)]
        for row, (arm, col, lab) in enumerate([("v0", MAP, "Map"), ("v1", MAPP, "Map+")]):
            y = 1 - row
            ax.hlines(y, 0, 1, color=GRID, lw=1, zorder=1)
            for rep in range(5):
                lv = d[(d.arm == arm) & (d.rep == rep)].level.unique()
                ax.scatter(lv, [y + (rep - 2) * 0.07] * len(lv), s=26, color=col, edgecolor="white",
                           linewidth=1, zorder=3)
            ax.text(-0.03, y, lab, ha="right", va="center", color=INK)
        ax.axvline(key, color=INK, lw=1, ls="--", zorder=2)
        ax.text(key, 1.55, f"answer key {key:.3f}", ha="center", va="bottom", color=INK, fontsize=9)
        ax.set_title(title, loc="left", fontsize=10, color=INK, pad=14)
        ax.set_ylim(-0.5, 1.5)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
    axes[-1].set_xlim(-0.02, 1.02)
    axes[-1].set_xlabel("Lever level set in the first run of each conversation (5 conversations per row)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_translation.pdf"))
    plt.close(fig)


def fig_pooled():
    rows = [("Lever level off the answer key", "offkey"), ("Words taken literally", "literal"),
            ("Required statement missing", "mention"), ("Number no tool gave", "untraced"),
            ("Required RDM step skipped", "skipped")]
    fig, ax = plt.subplots(figsize=(6.3, 3.0))
    for i, (lab, k) in enumerate(rows):
        for j, (arm, col) in enumerate([("v0", MAP), ("v1", MAPP)]):
            f, n = N[k][0][arm]
            y = -i * 1.0 - j * 0.36
            ax.barh(y, f / n, height=0.32, color=col, zorder=2)
            ax.text(f / n + 0.01, y, f"{f}/{n}", va="center", fontsize=8.5, color=MUTED)
        ax.text(-0.01, -i * 1.0 - 0.18, lab, ha="right", va="center", color=INK)
    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    ax.set_xlabel("Share of applicable questions")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=MAP, label="Map (relations)"), Patch(color=MAPP, label="Map+ (relations and values)")],
              loc="lower right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_pooled.pdf"))
    plt.close(fig)


def fig_walk():
    names = {"S50": "Landfill gas captured", "S3": "Area under conservation agriculture",
             "S35": "Electric light-duty vehicle-km", "HD1": "Extra electricity used by transport"}
    order = ["S35", "HD1", "S50", "S3"]
    fig, ax = plt.subplots(figsize=(6.3, 2.4))
    for i, q in enumerate(order):
        for j, (arm, col) in enumerate([("v0", MAP), ("v1", MAPP)]):
            v = int(walk[(walk.question == q) & (walk.arm == arm)].reached_target.iloc[0])
            y = -i - j * 0.36
            ax.barh(y, v, height=0.32, color=col, zorder=2)
            ax.text(v + 0.06, y, str(v), va="center", fontsize=8.5, color=MUTED)
        ax.text(-0.05, -i - 0.18, names[q], ha="right", va="center", color=INK)
    ax.set_xlim(0, 5)
    ax.set_xticks(range(6))
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    ax.set_xlabel("Conversations (of 5) that reached the variable holding the answer")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=MAP, label="Map"), Patch(color=MAPP, label="Map+")],
              loc="lower right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_walk.pdf"))
    plt.close(fig)


fig_translation()
fig_pooled()
fig_walk()


# ---------------------------------------------------------------- 3. LaTeX checks
bib = open(os.path.join(PROJ, "references.bib")).read()
body = re.sub(r"(?<!\\)%.*", "", tex)                          # drop comments
problems = []
if body.count("{") != body.count("}"):
    problems.append(f"braces: {body.count('{')} open vs {body.count('}')} close")
for env in set(re.findall(r"\\begin\{(\w+\*?)\}", body)):
    if body.count(f"\\begin{{{env}}}") != body.count(f"\\end{{{env}}}"):
        problems.append(f"environment {env} unbalanced")
bibkeys = set(re.findall(r"@\w+\{([^,]+),", bib))
cited = {k.strip() for grp in re.findall(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]+)\}", body) for k in grp.split(",")}
for k in sorted(cited - bibkeys):
    problems.append(f"cite without bib entry: {k}")
labels = set(re.findall(r"\\label\{([^}]+)\}", body))
for k in sorted(set(re.findall(r"\\(?:auto)?ref\{([^}]+)\}", body)) - labels):
    problems.append(f"ref without label: {k}")
for g in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body):
    if not os.path.exists(os.path.join(PROJ, g)):
        problems.append(f"missing figure: {g}")
for i, line in enumerate(tex.splitlines(), 1):
    if any(ord(ch) > 127 for ch in line):
        problems.append(f"non-ASCII character on line {i}: {line.strip()[:60]}")
for term in ["HBLE", "maximum feasible", "Calibri", "P50i", "WW1", "HD1", "Q10b"]:
    for i, line in enumerate(tex.splitlines(), 1):
        if term in line and not line.lstrip().startswith("%"):
            problems.append(f"banned term '{term}' on line {i}")
unused = sorted(bibkeys - cited)
todos = re.findall(r"\\todo(?:\[[^\]]*\])?\{((?:[^{}]|\{[^{}]*\})*)\}", body)
words = len(re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?|[{}$\\]", " ", body.split("\\begin{document}")[1]).split())

print("\nLaTeX checks:", "all passed" if not problems else "")
for p in problems:
    print("  PROBLEM:", p)
if unused:
    print("  note, bib entries not cited:", ", ".join(unused))
print(f"  about {words:,} words; {len(cited)} works cited")
print(f"\n{len(todos)} items left for the authors (\\todo):")
for t in todos:
    print("  -", t)

if bad or problems:
    sys.exit("\nNot zipped: fix the problems above.")


# ---------------------------------------------------------------- 4. zip
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for dirpath, _, files in os.walk(PROJ):
        for f in files:
            if f.startswith("."):
                continue
            full = os.path.join(dirpath, f)
            z.write(full, os.path.relpath(full, PROJ))
print(f"\nZipped: {ZIP}")
