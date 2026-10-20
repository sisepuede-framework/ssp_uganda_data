"""
Answer keys for the draft question bank (docs/question_bank_v1.md) marked "to compute".

Surrogate keys: other levers at 0 (BAU), 1,000 futures with all 13 uncertainties sampled, 2050, changes against BAU in
the same futures. Run-based keys: the cached sample (frame 1: other levers as they varied in the runs).
Rerun after the bank is revised:

    python -m backend.rdm.eval.bank_reference      → backend/rdm/eval/bank_reference.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from backend.rdm.data.store import Store
from backend.rdm.runs import get_run
from backend.rdm.surrogate import get_surrogate
from backend.rdm.tools.common import groups

OUT = Path(__file__).parent / "bank_reference.json"
YEAR = 2050
N = 1000


def _futures(s, x_ranges=None):
    u = np.random.default_rng(0).random((N, len(s.x_ids)))
    f = pd.DataFrame({f"X_{x}": u[:, i] for i, x in enumerate(s.x_ids)})
    for x, (lo, hi) in (x_ranges or {}).items():
        f[f"X_{x}"] = lo + f[f"X_{x}"] * (hi - lo)
    return f.assign(**{f"L_{l}": 0.0 for l in s.lever_ids})


def _q(a, nd=2):
    return [round(float(np.percentile(a, p)), nd) for p in (10, 50, 90)]


def run_policy(s, levers: dict, x_ranges=None) -> tuple:
    base = _futures(s, x_ranges)
    return s.predict(base), s.predict(base.assign(**{f"L_{k}": v for k, v in levers.items()}))


def pct(p, b, col):
    return (p[col] - b[col]) / b[col].abs() * 100


def main():
    run = get_run()
    s, g = get_surrogate(run), groups(run)
    sector = lambda *names: {i: 1.0 for i, v in g.items() if v["kind"] == "L" and v["sector"] in names}
    tot, trns = f"emissions_total_yr{YEAR}", f"emission_transportation_yr{YEAR}"
    ref = {}

    # D3 — 65% electric light-duty travel (L35 = 0.685): share of futures failing "transport ≥ 5% below BAU"
    b, p = run_policy(s, {35: 0.685})
    ch = pct(p, b, trns)
    ref["D3"] = {"level": 0.685, "transport_change_pct_p10_med_p90": _q(ch), "share_failing_5pct": round(float((ch > -5).mean()), 3)}

    # Q10 and D2 — renewables 0.8 + deforestation 0.6; failure = total not ≥ 50% below BAU in 2050
    for qid, xr in (("Q10", None), ("D2", {57: (2 / 3, 1.0)})):
        b, p = run_policy(s, {7: 0.8, 15: 0.6}, xr)
        ch = pct(p, b, tot)
        ref[qid] = {"total_change_pct_p10_med_p90": _q(ch), "share_failing_50pct": round(float((ch > -50).mean()), 3),
                    "gdp_range": list(xr[57]) if xr else "all"}

    # E2 — red meat to 70% (L25 = 0.682) vs 40% landfill gas recovered (L50 = 0.688), total emissions 2050
    b, a = run_policy(s, {25: 0.682})
    _, c = run_policy(s, {50: 0.688})
    ref["E2"] = {"red_meat_total_change_mt": _q(a[tot] - b[tot]), "landfill_total_change_mt": _q(c[tot] - b[tot]),
                 "share_red_meat_lower": round(float((a[tot] < c[tot]).mean()), 3)}

    # E3 — maximum reduction of heat demand (L27 = 1): cost and benefit changes 2050
    b, p = run_policy(s, {27: 1.0})
    ref["E3"] = {"total_change_mt": _q(p[tot] - b[tot]), "cost_change_bn_usd": _q(p[f"cost_total_yr{YEAR}"] - b[f"cost_total_yr{YEAR}"]),
                 "benefit_change_bn_usd": _q(p[f"benefit_total_yr{YEAR}"] - b[f"benefit_total_yr{YEAR}"])}

    # C1 — every transport lever at maximum: can transport emissions fall 30% below BAU?
    tl = sector("Transportation", "Transport Demand")
    b, p = run_policy(s, tl)
    ch = pct(p, b, trns)
    ref["C1"] = {"levers": sorted(tl), "transport_change_pct_all_at_max": _q(ch), "reachable_30pct_share": round(float((ch <= -30).mean()), 3)}

    # C2 — every lever at maximum: can total emissions fall 50% below BAU?
    b, p = run_policy(s, {l: 1.0 for l in s.lever_ids})
    ch = pct(p, b, tot)
    ref["C2"] = {"total_change_pct_all_at_max": _q(ch), "reachable_50pct_share": round(float((ch <= -50).mean()), 3)}

    # C4 — transport and waste levers at maximum: can net 2050 emissions go below 20 Mt?
    tw = sector("Transportation", "Transport Demand", "Solid Waste", "Water & Wastewater Treatment", "Wastewater")
    b, p = run_policy(s, tw)
    ref["C4"] = {"levers": sorted(tw), "total_mt_at_max_p10_med_p90": _q(p[tot]), "share_below_20mt": round(float((p[tot] < 20).mean()), 3),
                 "bau_total_mt": _q(b[tot])}

    # B7 — level of conservation agriculture (L3) where the runs' median improved cropland reaches 2 M ha
    st = Store(run)
    y = st.values("area_lndu_improved_croplands", YEAR)
    L = st.design.loc[y.index, "L_3"]
    edges = np.linspace(0, 1, 11)
    mid = (edges[:-1] + edges[1:]) / 2
    med = np.array([y[(L >= lo) & (L < hi if hi < 1 else L <= hi)].median() for lo, hi in zip(edges[:-1], edges[1:])])
    ref["B7"] = {"median_ha_by_decile": [round(float(m)) for m in med],
                 "level_reaching_2M_ha": round(float(np.interp(2e6, med, mid)), 2) if med.max() >= 2e6 else None}

    OUT.write_text(json.dumps(ref, indent=1))
    print(json.dumps(ref, indent=1))


if __name__ == "__main__":
    main()
