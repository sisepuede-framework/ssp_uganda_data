"""
Question sets for the pilots, with the reference answer each one is scored against.

  pilot  Q04b, Q10, Q14 from the question bank (docs/archive/decision_charter_and_question_bank.md).
  bank   The question bank v3 (docs/question_bank_v3.md), frozen 2026-10-19, with what each question expects
         (BANK_SPECS, read by failure_modes.py).
  pairs  Same lever, two kinds of target (decided 2026-10-13): an INPUT target — a quantity the lever
         sets directly (answer exact: value(L) = BASE + L × (HBLE − BASE)) — and an OUTPUT target — an
         emission change the lever causes (answer from the surrogate: the level that meets the target,
         per future, other levers at 0). Run in the arms v0 and v1.

    python -m backend.rdm.eval.questions     → prints and saves the reference answers (eval/pairs_reference.json)
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

GO_AHEAD = "Please go ahead with what you think is reasonable and tell me what you assumed."

PILOT = {
    "Q04b": {"question": "What if 60% of light-duty vehicle-km were electric by 2050?", "replies": []},
    "Q10": {"question": "Is a policy of renewables at 0.8 plus reduced deforestation at 0.6 robust?",
            "replies": ["Count it as a failure if net emissions in 2050 are not at least 50% below business as usual "
                        "in that same future."]},
    "Q14": {"question": "Is electrifying transport better than cutting deforestation for Uganda?", "replies": []},
}

PAIRS = {
    "P35i": {"question": "What if 60% of light-duty vehicle-km were electric by 2050?",
             "lever": 35, "kind": "input", "field": "frac_trns_fuelmix_road_light_electricity", "target": 0.60, "year": 2050},
    "P35o": {"question": "How far would we need to shift light-duty vehicles to electricity to cut transport emissions "
                         "5% below business as usual by 2050?",
             "lever": 35, "kind": "output", "category": "transportation", "target_pct": -5.0, "year": 2050},
    "P50i": {"question": "What if Uganda's landfills recovered 40% of their landfill gas by 2050?",
             "lever": 50, "kind": "input", "field": "frac_waso_landfill_gas_recovered", "target": 0.40, "year": 2050},
    "P50o": {"question": "How much landfill gas capture would it take to cut solid-waste emissions 10% below business "
                         "as usual by 2050?",
             "lever": 50, "kind": "output", "category": "solid_waste", "target_pct": -10.0, "year": 2050},
    "P12i": {"question": "What if the clinker share of cement fell to 65% by 2050?",
             "lever": 12, "kind": "input", "field": "frac_ippu_cement_clinker", "target": 0.65, "year": 2050},
    "P12o": {"question": "How far would cement clinker reduction need to go to cut industrial process (IPPU) emissions "
                         "6% below business as usual by 2050?",
             "lever": 12, "kind": "output", "category": "ippu", "target_pct": -6.0, "year": 2050},
}
for q in PAIRS.values():
    q.setdefault("replies", [])

# Translation 3: a lever scenario → an in-between quantity the surrogate does not report (decided 2026-10-14).
SCENARIO = {
    "S35": {"question": "If Uganda pushed the shift of light-duty vehicles to electricity to its maximum, how much electric "
                        "light-duty travel would there be in 2050?",
            "lever": 35, "kind": "scenario", "variable": "vehicle_distance_traveled_trns_road_light_electricity", "year": 2050},
    "S50": {"question": "If landfill gas capture were pushed to its maximum, how much landfill gas would Uganda recover "
                        "in 2050?",
            "lever": 50, "kind": "scenario", "variable": "gasrecovered_waso_biogas_landfills_tonne", "year": 2050},
    "S3": {"question": "If conservation agriculture were scaled up to its maximum, how much cropland would be under "
                       "improved practices in 2050?",
           "lever": 3, "kind": "scenario", "variable": "area_lndu_improved_croplands", "year": 2050},
}
for q in SCENARIO.values():
    q.setdefault("replies", [])

# ── Question bank v3 (docs/question_bank_v3.md) ──────────────────────────────────────────────────────────────
# One entry per conversation. Q10b, D2b and N1 are one conversation: D2b and N1 arrive as scripted replies.
THRESHOLD_5 = ("Count it as a failure if total emissions in 2050 are not at least 5% below business as usual in that "
               "same future.")
D2B = "Does the policy we just tested still work if the economy grows fast?"
N1 = "It fails when the economy grows fast. What could we change so it holds up, and does it?"

BANK = {
    "P50i": "What if Uganda's landfills captured 40% of the methane their rubbish gives off (landfill gas) by 2050?",
    "P12i": "What if cement made in Uganda used less clinker, its most polluting ingredient, so that clinker was 65% of "
            "the cement by 2050 instead of about 72%?",
    "B6": "What if 45% of the distance driven by cars, vans and other light vehicles were electric by 2050?",
    "AG1": "What if farmers stopped ploughing on 30% of the land where they grow cereals by 2050, and what would that do "
           "to emissions?",
    "LV1": "What if 40% of the manure from dairy cows were used to make biogas by 2050?",
    "BLD1": "What if homes and businesses used a quarter less energy for cooking and heating by 2050?",
    "WW1": "What if half of rural households' wastewater went to septic tanks by 2050?",
    "H1": "What if about a quarter of the manure from chickens went into biogas digesters by 2050?",
    "H2": "What if half of Uganda's chemical production captured its CO₂ by 2050?",
    "H3": "What if each Ugandan threw away a fifth less food by 2050?",
    "X1": "What if Uganda halved deforestation by 2050?",
    "S50": "If Uganda captured methane from its landfills as ambitiously as is realistically possible, how much landfill "
           "gas would it capture in 2050?",
    "S3": "If Uganda promoted soil-friendly farming (less ploughing, keeping crop residues on the field) as ambitiously "
          "as is realistically possible, how many hectares of farmland would use these methods in 2050?",
    "S35": "If Uganda moved cars and vans to electricity as ambitiously as is realistically possible, how many "
           "kilometres would electric cars and vans travel in 2050?",
    "AG2": "Which policies could cut emissions from farming and livestock by a quarter compared with business as usual "
           "by 2050?",
    "C4b": "Can Uganda cut its total emissions by 20% by 2050 using only waste and wastewater policies?",
    "X2": "Uganda has pledged to cut its emissions 24.7% below business as usual by 2030. Which policies in the model "
          "could get us there, and roughly what would they cost?",
    "Q10b": "Is a policy with a strong push on renewable electricity and a moderate cut in deforestation robust?",
    "D3b": "Is having only 70% of Ugandans eat red meat by 2050 a robust way to cut livestock emissions?",
    "Q14b": "Is moving homes and businesses to cleaner cooking and heating fuels better than cutting deforestation?",
    "TO1": "Which cuts more emissions by 2050, and at what cost: landfills capturing 40% of their methane, or homes and "
           "businesses using a quarter less energy for cooking and heating?",
    "B8b": "What if Uganda built three new large hydropower dams by 2040?",
    "F2": "Make Uganda greener.",
    "F3b": "Slow down economic growth so that emissions fall.",
    # v3.1 hypothesis questions (pre-registered 2026-10-21, docs/question_bank_v3.md)
    "HA1": "How far would Uganda need to push the shift of cars and vans to electricity for them to drive 21 billion "
           "kilometres on electricity in 2050?",
    "HB1": "Which policies outside livestock farming itself could also reduce Uganda's livestock emissions?",
    "HC1": "Would moving homes and businesses to cleaner cooking and heating fuels still cut emissions in 2050 if "
           "Uganda's economy were larger than about 580 billion dollars by then?",
    "HD1": "If cars and vans moved to electricity as far as the model allows, how much more electricity would transport "
           "use in 2050?",
    "HE1": "If cement made in Uganda used as little clinker as the model allows, how much clinker would it contain and "
           "how much would emissions from industrial processes fall by 2050?",
}
BANK_REPLIES = {
    "Q10b": [THRESHOLD_5, D2B, N1],
    "D3b": ["Count it as a failure if livestock emissions in 2050 are not at least 9% below business as usual in that "
            "same future."],
    "F2": ["I mean less deforestation and cleaner cooking in homes."],
}
BANK = {qid: {"question": q, "replies": BANK_REPLIES.get(qid, [])} for qid, q in BANK.items()}

GDP = 57                                    # uncertainty: GDP growth trajectory
EXPLORE, VULN, SD, TRADE = "exploratory_modeling", "vulnerability_analysis", "scenario_discovery", "trade_off_analysis"
FARM_LEVERS = [1, 2, 3, 4, 19, 20, 21, 22, 23, 24, 25]     # agriculture, manure, livestock, and diets (acts on livestock)
WASTE_LEVERS = list(range(43, 55))                         # wastewater and solid waste
T2_SOURCE = "the model runs (model_network), not the surrogate"
BEYOND = "says the user's target is beyond the most ambitious level explored in the model runs (for 2050)"


def _t1(lever, key, user, tag, **kw) -> dict:
    return {"tag": tag, "kind": "T1", "lever": lever, "key_level": key, "tol": 0.02, "user_number": user, **kw}


def _t2(lever, value) -> dict:
    return {"tag": "dev", "kind": "T2", "lever": lever, "run_expected": False, "expected_source": T2_SOURCE,
            "must_say": [f"gives a value from the model runs between {value}",
                         "says this is the most ambitious level explored in the model runs"]}


# What each bank question expects (fields: see _pilot_specs). Pre-registered with the bank; "auto" rules are read
# from the tool calls, must_mention from the answer text, must_say / expected_* by the reader (--reader).
BANK_SPECS = {
    "P50i": _t1(50, 0.688, 0.40, "dev"),
    "P12i": _t1(12, 0.583, 0.65, "dev"),
    "B6": _t1(35, 0.0, 0.45, "dev", run_expected=False, must_mention=[r"\b50\s*%|\bhalf\b"],
              must_say=["says business as usual already reaches about 50%, above the 45% asked, so no extra action "
                        "is needed"]),
    "AG1": _t1(3, 0.51, 0.30, "designed", expected_direction="agricultural emissions rise slightly (up), not a cut"),
    "LV1": _t1(20, 1.0, 0.40, "designed", run_expected=False, must_mention=[r"\b3[23](\.\d)?\s*%"], must_say=[BEYOND]),
    "BLD1": _t1(27, 0.67, [0.25, 0.75], "designed"),
    "WW1": _t1(46, 0.716, 0.50, "designed"),
    "H1": _t1(22, 0.573, 0.25, "blind"),
    "H2": _t1(26, 1.0, 0.50, "blind", run_expected=False, must_mention=[r"\b4[12](\.\d)?\s*%"], must_say=[BEYOND]),
    "H3": _t1(48, 1.0, [0.20, 0.80], "blind", run_expected=False, must_mention=[r"\b1[67](\.\d)?\s*%|0\.8[34]"],
              must_say=[BEYOND]),
    # X1 key (2026-10-21): 0.5 halves the deforestation rates the lever sets; forest loss in hectares halves at about
    # 0.60 (2035) to 0.65 (2050) in the runs. Both readings are right: the key accepts 0.50–0.65.
    "X1": {"tag": "designed", "kind": "T1", "lever": 15, "key_level": 0.575, "tol": 0.075,
           "must_say": ["states which lever level it used for 'halving deforestation' and why"]},
    # S keys (2026-10-21): the lever's top third (⅔–1), the cell model_network reports, 2050, p10–p90
    "S50": _t2(50, "120,000 and 1.4 million tonnes of landfill gas"),
    "S3": _t2(3, "2.2 and 3.1 million hectares"),
    "S35": _t2(35, "18 and 28 billion vehicle-km"),
    "AG2": {"tag": "designed", "kind": "T3", "allowed_levers": FARM_LEVERS, "package": True, "required_tools": [EXPLORE]},
    "C4b": {"tag": "designed", "kind": "T3", "allowed_levers": WASTE_LEVERS, "required_tools": [EXPLORE],
            "must_say": ["states the baseline the 20% is measured against (business as usual, or today's emissions)",
                         "says a 20% cut is not reachable with waste and wastewater policies alone",
                         "gives the best case it found"]},
    # X2 key (2026-10-21, surrogate, other levers at BAU, 1,000 futures, 2035 vs BAU): every lever at the top gives
    # −31.0% (−31.6 to −30.3), cost +2.84 bn USD (1.90–3.61); the smallest package reaching −24.7% in the median is
    # L30, L29, L9, L15, L23 at the top: −26.1% (−26.8 to −25.4), 99% of futures, cost +1.37 bn USD (1.05–1.64).
    "X2": {"tag": "blind", "kind": "T3", "required_tools": [EXPLORE],
           "must_say": ["says 2030 is not a year the model reports and states which year it uses instead",
                        "does not present any number as computed for 2030",
                        "describes costs as changes compared with business as usual"]},
    "Q10b": {"tag": "dev", "parts": [
        {"id": "Q10b", "question": BANK["Q10b"]["question"], "from_user_turn": 1, "kind": "T0",
         "needs_threshold": True, "required_tools": [EXPLORE, VULN, SD]},
        {"id": "D2b", "question": D2B, "from_user_turn": 3, "kind": "T0", "x_side": {GDP: "high"},
         "required_tools": [EXPLORE, VULN]},
        {"id": "N1", "question": N1, "from_user_turn": 4, "kind": "T0", "x_side": {GDP: "high"}, "retest": True,
         "must_say": ["every claim that the revised policy holds up is backed by a test reported in the answer"]}]},
    "D3b": _t1(25, 0.682, 0.70, "designed", needs_threshold=True, required_tools=[EXPLORE, VULN, SD],
               must_mention=[r"export"]),
    "Q14b": {"tag": "dev", "kind": "T0", "compare": True, "required_tools": [EXPLORE, TRADE]},
    # v3.1 hypothesis questions; keys computed 2026-10-21 by the pre-registered rules (docs/question_bank_v3.md)
    # HA1: target = median electric vehicle-km of the runs with L35 in 0.5–0.6 (21 bn); reached at L35 ≈ 0.62
    "HA1": {"tag": "designed", "kind": "T1", "lever": 35, "key_level": 0.62, "tol": 0.1, "run_expected": False,
            "visit": [r"^(l|lever\s*)?35$|vehicle.?distance.*electric"],
            "must_say": ["says electric vehicle-km cannot be tested on the surrogate and that the number comes from the "
                         "model runs"]},
    # HB1: levers outside the livestock sectors with a path to emissions_livestock: L25 diets (−7.4 Mt from its low
    # to its high third), L15 deforestation (−2.5), L4 crop productivity (+1.2, raises them), L2, L17, L18 (small)
    "HB1": {"tag": "designed", "kind": "T0", "visit": [r"livestock"],
            "must_mention": [r"diet|red meat|\bmeat\b", r"deforest"]},
    # HC1: GDP 2050 median by X57 third 444 / 540 / 632 bn; 580 = median of runs with X57 in 0.6–0.7 → top third.
    # L30 at the top, X57 in its top third: total −5.95 Mt (−7.18 to −4.84), −3.3%: it still cuts.
    "HC1": {"tag": "designed", "kind": "T0", "x_side": {GDP: "high"}, "required_tools": [EXPLORE],
            "must_say": ["says which part of the economic growth uncertainty matches an economy above about 580 billion "
                         "dollars in 2050", "says total emissions still fall in those futures"]},
    # HD1: total electricity used by transport, L35 top third vs bottom third, 2050: 56.0 → 59.9 PJ (+3.8 PJ, ~7%)
    "HD1": {"tag": "designed", "kind": "T2", "lever": 35, "run_expected": False, "expected_source": T2_SOURCE,
            "visit": [r"electrical energy consumption.*transport|energy_consumption_electricity_trns"],
            # added 2026-10-26 after the smoke test (v1 got 56.0 → 59.9 PJ and did not report it); v0 cannot pass it
            "must_mention": [r"\b[3-5](\.\d+)?\s*PJ|\b59\.\d|\b60\s*PJ"],
            "must_say": ["gives an increase of about 3 to 5 PJ (about 56 to 60 PJ) from the model runs, not the "
                         "surrogate"]},
    # HE1: clinker 72% → 60% (L12 at the top, 2050); surrogate, L12 = 1 vs BAU: IPPU −1.4 Mt (−1.75 to −1.0), −12.4%
    "HE1": {"tag": "designed", "kind": "T1", "lever": 12, "key_level": 1.0, "tol": 0.05, "required_tools": [EXPLORE],
            "visit": [r"^(l|lever\s*)?12$"], "must_mention": [r"\b60\s*%|\b0\.60?\b"],
            "must_say": ["says the model network shows no link from the clinker lever to emissions, so the emissions "
                         "come from the surrogate"]},
    "TO1": {"tag": "designed", "kind": "T1", "levers": {50: {"key_level": 0.688, "user_number": 0.40},
                                                        27: {"key_level": 0.67, "user_number": [0.25, 0.75]}},
            "tol": 0.02, "compare": True, "required_tools": [EXPLORE, TRADE],
            "must_say": ["reports how often, or by how much, one cuts more than the other (share of futures or "
                         "overlapping ranges), without calling one better overall",
                         "describes costs as changes compared with business as usual"]},
    "B8b": {"tag": "designed", "kind": "T4",
            "must_say": ["says the model has no dams or power-plant counts",
                         "offers the renewable electricity lever as a stand-in"]},
    "F2": {"tag": "designed", "kind": "T4", "must_say": ["asks what 'greener' means before running anything"]},
    "F3b": {"tag": "designed", "kind": "T0",
            "must_say": ["says GDP growth is an uncertainty Uganda does not choose, not a policy"]},
}

SETS = {"pilot": PILOT, "pairs": PAIRS, "scenario": SCENARIO, "bank": BANK}
SCENARIO_REFERENCE = Path(__file__).parent / "scenario_reference.json"
REFERENCE = Path(__file__).parent / "pairs_reference.json"


def _pilot_specs() -> dict:
    """What each pilot question expects, in the shape failure_modes.check reads:
    kind (T0–T4) · lever · key_level, tol · user_number (the user's own number, to catch a literal
    translation) · run_expected · required_tools · needs_threshold · compare · x_side ({x_id: "high"|"low"}) ·
    expected_direction, expected_source (for the reader). The question bank v3 has its own (BANK_SPECS)."""
    ref = json.loads(REFERENCE.read_text()) if REFERENCE.exists() else {}
    specs = {}
    for qid, q in PAIRS.items():
        r = ref.get(qid, {})
        if q["kind"] == "input":
            specs[qid] = {"kind": "T1", "lever": q["lever"], "key_level": r.get("level"), "tol": 0.02,
                          "user_number": q["target"]}
        else:
            specs[qid] = {"kind": "T3", "lever": q["lever"], "key_level": r.get("level"), "tol": 0.1}
    for qid, q in SCENARIO.items():
        specs[qid] = {"kind": "T2", "lever": q["lever"], "run_expected": False,
                      "expected_source": T2_SOURCE}
    specs["Q04b"] = {**specs["P35i"]}
    specs["Q10"] = {"kind": "T0", "required_tools": ["exploratory_modeling", "vulnerability_analysis"],
                    "needs_threshold": True}
    specs["Q14"] = {"kind": "T0", "compare": True}
    return specs


SPECS = _pilot_specs()


def reference_input(run, q: dict) -> dict:
    t = pd.read_csv(Path(__file__).parents[1] / "data/tables" / f"{run.name}_lever_inputs.csv")
    r = t[(t.lever_id == q["lever"]) & (t.field == q["field"]) & (t.year == q["year"])].iloc[0]
    level = (q["target"] - r.at_0) / (r.at_1 - r.at_0)
    return {"level": round(float(level), 3), "level_range": [round(float(level), 3)] * 2,
            "note": f"{q['field']} = {r.at_0:.4f} at 0 and {r.at_1:.4f} at 1 in {q['year']}; exact in every future"}


def reference_output(run, q: dict, n: int = 1000, step: float = 0.025) -> dict:
    """Level of the lever that meets the target, other levers at 0, per future; median and p10–p90."""
    from backend.rdm.surrogate import get_surrogate
    s = get_surrogate(run)
    u = np.random.default_rng(0).random((n, len(s.x_ids)))
    fut = pd.DataFrame({f"X_{x}": u[:, i] for i, x in enumerate(s.x_ids)})
    base = fut.assign(**{f"L_{l}": 0.0 for l in s.lever_ids})
    col = f"emission_{q['category']}_yr{q['year']}"
    bau = s.predict(base)[col]
    grid = np.round(np.arange(0, 1 + 1e-9, step), 3)
    pct = np.column_stack([(s.predict(base.assign(**{f"L_{q['lever']}": L}))[col] - bau) / bau.abs() * 100 for L in grid])
    med = np.median(pct, axis=0)
    level_med = float(np.interp(q["target_pct"], med[::-1], grid[::-1])) if med.min() <= q["target_pct"] else None
    per_future = []
    for row in pct:
        hit = np.nonzero(row <= q["target_pct"])[0]
        per_future.append(np.nan if not len(hit) else grid[hit[0]])
    pf = np.array(per_future, dtype=float)
    return {"level": None if level_med is None else round(level_med, 3),
            "level_range": [round(float(np.nanpercentile(pf, 10)), 3), round(float(np.nanpercentile(pf, 90)), 3)],
            "share_of_futures_reachable": round(float(np.mean(~np.isnan(pf))), 3),
            "effect_at_full_pct": [round(float(np.percentile(pct[:, -1], p)), 2) for p in (10, 50, 90)],
            "monotonic_median": bool(np.all(np.diff(med) <= 1e-6)),
            "note": "surrogate, other levers at 0, all 13 uncertainties sampled; level where the median change reaches the target"}


def reference_scenario(run, store, q: dict) -> dict:
    """The in-between variable when the lever is at its maximum, from the runs only (no model): the key is the
    lever's top third (⅔–1), every other lever at its random level — the cell model_network reports. The runs
    with the lever ≥ 0.9 and ≤ 0.1 are kept for comparison. No run has the other levers near BAU, so this is the
    only answer the data gives directly."""
    from backend.rdm.tools.information import unit
    y = store.values(q["variable"], q["year"])
    L = store.design.loc[y.index, f"L_{q['lever']}"]
    q3 = lambda a: [round(float(np.percentile(a, p)), 4) for p in (10, 50, 90)]
    return {"unit": unit(q["variable"]),
            "key_lever_top_third_p10_median_p90": q3(y[L >= 2 / 3]), "n_runs": int((L >= 2 / 3).sum()),
            "lever_ge_0.9_p10_median_p90": q3(y[L >= 0.9]),
            "lever_le_0.1_p10_median_p90": q3(y[L <= 0.1])}


def references(run) -> dict:
    return {qid: {**{k: v for k, v in q.items() if k != "replies"},
                  **(reference_input(run, q) if q["kind"] == "input" else reference_output(run, q))}
            for qid, q in PAIRS.items()}


if __name__ == "__main__":
    import sys

    from backend.rdm.runs import get_run
    if sys.argv[1:] == ["scenario"]:
        from backend.rdm.data.store import Store
        run = get_run()
        st = Store(run)
        ref = {qid: {**{k: v for k, v in q.items() if k != "replies"}, **reference_scenario(run, st, q)}
               for qid, q in SCENARIO.items()}
        SCENARIO_REFERENCE.write_text(json.dumps(ref, indent=1))
        print(json.dumps(ref, indent=1))
        raise SystemExit
    ref = references(get_run())
    REFERENCE.write_text(json.dumps(ref, indent=1))
    for qid, r in ref.items():
        print(qid, r["kind"], "level", r["level"], "range", r["level_range"], r.get("effect_at_full_pct", ""),
              r.get("share_of_futures_reachable", ""), r.get("monotonic_median", ""))
