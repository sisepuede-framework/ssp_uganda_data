"""
Figure of the (L_i, X_j) object for one output: what the v1 agent sees and the v0 agent does not.

  A · the 5 × 5 grid from Store.pair: median per cell (sequential blue), p10–p90 underneath.
  B · the lever's curve at the lowest and at the highest uncertainty bin (median line, p10–p90
      band): the slope is what the lever does, the gap is what the uncertainty does.

Usage:
  python -m backend.rdm.figures.pair_figure --lever 35 --x 57 \
      --output vehicle_distance_traveled_trns_road_light_electricity --year 2050 \
      --scale 1e9 --unit "billion vehicle-km" --label "Electric light-duty vehicle-km" \
      --out docs/figures/pair_L35_X57_ev_vkm_2050
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from backend.rdm.data.store import Store  # noqa: E402
from backend.rdm.runs import get_run  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
SERIES = {"low": "#2a78d6", "high": "#eb6834"}          # categorical slots 1 and 2 (low / high X bin)
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def _names(run) -> dict:
    reg = json.loads(run.registry.read_text())
    return {int(f["group_id"]): f["display_name"]
            for block in ("lever_features", "exogenous_features") for f in reg[block].values()}


def draw(store: Store, lever: int, x: int, output: str, year: int, scale: float, unit: str,
         label: str, out: Path) -> None:
    names = _names(store.run)
    grid = store.pair(lever, x, output, year)
    for c in ("p10", "median", "p90"):
        grid[c] = grid[c] / scale

    plt.rcParams.update({"font.family": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 10,
                         "text.color": TEXT, "axes.labelcolor": TEXT_2, "xtick.color": TEXT_2,
                         "ytick.color": TEXT_2})
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(12.5, 5.4), gridspec_kw={"width_ratios": [1.05, 1]})
    fig.patch.set_facecolor(SURFACE)

    # A · heatmap of the median
    n = int(len(grid) ** 0.5)
    med = grid.pivot(index="L_from", columns="X_from", values="median").sort_index(ascending=False)
    p10 = grid.pivot(index="L_from", columns="X_from", values="p10").loc[med.index]
    p90 = grid.pivot(index="L_from", columns="X_from", values="p90").loc[med.index]
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ)
    vmin, vmax = med.values.min(), med.values.max()
    ax_a.imshow(med.values, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    for i in range(n):
        for j in range(n):
            v = med.values[i, j]
            dark = (v - vmin) / (vmax - vmin) > 0.4
            ink = "#ffffff" if dark else TEXT
            ax_a.text(j, i - 0.12, f"{v:.1f}", ha="center", va="center", fontsize=12, fontweight="bold", color=ink)
            ax_a.text(j, i + 0.22, f"{p10.values[i, j]:.1f}–{p90.values[i, j]:.1f}", ha="center",
                      va="center", fontsize=8, color="#e8eef8" if dark else TEXT_2)
    ticks = [f"{a:.1f}–{a + 1 / n:.1f}" for a in med.columns]
    ax_a.set_xticks(range(n), ticks)
    ax_a.set_yticks(range(n), [f"{a:.1f}–{a + 1 / n:.1f}" for a in med.index])
    ax_a.set_xlabel(f"{names[x]} (uncertainty X{x}, position in its range)")
    ax_a.set_ylabel(f"{names[lever]} (lever L{lever}, 0 = BAU, 1 = maximum)")
    ax_a.tick_params(length=0)
    for s in ax_a.spines.values():
        s.set_visible(False)
    ax_a.set_title(f"A · Median {label.lower()}, {year} ({unit})\nsmall print: p10–p90 across the runs in each cell",
                   loc="left", fontsize=11, color=TEXT)

    # B · the lever's curve at the lowest and highest uncertainty bin: slope = lever, gap = uncertainty
    lo, hi = grid.X_from.min(), grid.X_from.max()
    for key, x_from, word in (("low", lo, "low"), ("high", hi, "high")):
        df = grid[grid.X_from == x_from].sort_values("L_from")
        mid = df.L_from + (df.L_to - df.L_from) / 2
        col = SERIES[key]
        ax_b.fill_between(mid, df.p10, df.p90, color=col, alpha=0.12, linewidth=0)
        ax_b.plot(mid, df["median"], color=col, linewidth=2, marker="o", markersize=8,
                  markeredgecolor=SURFACE, markeredgewidth=2)
        ax_b.annotate(f"{names[x]} {word}\n(X{x} {x_from:.1f}–{x_from + 1 / n:.1f}): "
                      f"{df['median'].iloc[0]:.1f} → {df['median'].iloc[-1]:.1f}",
                      xy=(mid.iloc[-1], df["median"].iloc[-1]), xytext=(10, 0), textcoords="offset points",
                      va="center", fontsize=9, color=TEXT)
    ax_b.set_xlim(0, 1.45)
    ax_b.set_xticks([0.1, 0.3, 0.5, 0.7, 0.9], ["0.0–0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "0.8–1.0"])
    ax_b.set_xlabel(f"{names[lever]} (lever L{lever}, 0 = BAU, 1 = maximum)")
    ax_b.set_ylabel(unit)
    ax_b.grid(axis="y", color=GRID, linewidth=0.8)
    ax_b.set_axisbelow(True)
    for s_ in ("top", "right", "left"):
        ax_b.spines[s_].set_visible(False)
    ax_b.spines["bottom"].set_color(GRID)
    ax_b.tick_params(length=0)
    ax_b.set_facecolor(SURFACE)
    ax_b.set_title(f"B · The lever's effect when {names[x].split()[0]} growth is low vs high\n"
                   f"slope = the lever · gap = the uncertainty · band = p10–p90",
                   loc="left", fontsize=11, color=TEXT)

    runs = int(grid.n.sum())
    fig.text(0.01, 0.01, f"SISEPUEDE runs ({store.run.run_id}), sample of {runs:,} runs; "
             f"≈{runs // len(grid)} runs per cell. Values in original units.", fontsize=8, color=TEXT_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(out.with_suffix(f".{ext}"), dpi=200, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--lever", type=int, required=True)
    p.add_argument("--x", type=int, required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--year", type=int, default=2050)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--unit", default="")
    p.add_argument("--label", default="")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    draw(Store(get_run()), a.lever, a.x, a.output, a.year, a.scale, a.unit, a.label or a.output, a.out)
    print(f"figure → {a.out}.png / .svg")
