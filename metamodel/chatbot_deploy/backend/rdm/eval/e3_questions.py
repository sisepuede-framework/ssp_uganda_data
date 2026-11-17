"""
E3 question sets (docs/run_design_E3_2026-11-17.md), approved by Alexa 2026-11-17 as written; frozen with docs/run_design_E3_2026-11-17.md.

Sets
  S   12 share-type targets, general wording ("how much ...")          E3a, E3b, E3c
  SX  the same 12, explicit wording (names the unit of the amount)    E3c
  O   8 other-type targets, general wording                          E3a check
  G   the 15 translation (T1) questions of the bank, unchanged          E3b guard (not written here)

Every question: a policy in plain words, "as ambitiously as is realistically possible" (the range maximum), a quantity
in 2050. Key (as in E2): the answer field's value in model_network for the lever's top third, 2050, median and
p10–p90. E1/E2 wordings are reused word for word where they exist (S50, R1, R3, R6, R8, R4, R5, R7, HD1); S3 and S35
named a unit in E1, so their E1 wording is the explicit (S3) or replaced by a general one (S35, in O).

Share-type (judgement, fixed before the run): the lever's own input is a share or factor of the same quantity the
question asks an amount of.

Run from metamodel/chatbot_deploy:
    /opt/miniconda3/envs/uganda_metamodel_env/bin/python -m backend.rdm.eval.e3_questions
    → backend/rdm/eval/e3_reference.json
"""
import json
from pathlib import Path

from backend.rdm.runs import active_run_name, get_run
from backend.rdm.tools.network import model_network, network

OUT = Path(__file__).parent / "e3_reference.json"
YEAR = 2050
AMB = "as ambitiously as is realistically possible"

# id: lever, answer node, answer field (None = the node's only field), share-type, why, general, explicit (None if O)
TARGETS = {
    # ── S: share-type ────────────────────────────────────────────────────────────────────────────────────────────────
    "S50": (50, "Biogas Recovered from Landfills", None, True, "fraction of landfill gas recovered ↔ landfill gas captured",
            f"If Uganda captured methane from its landfills {AMB}, how much landfill gas would it capture in 2050?",
            f"If Uganda captured methane from its landfills {AMB}, how many tonnes of landfill gas would it capture in 2050?"),
    "S3": (3, "Area of Improved Land", None, True, "no-till crop fraction ↔ farmland using the methods",
           f"If Uganda promoted soil-friendly farming (less ploughing, keeping crop residues on the field) {AMB}, how much "
           f"farmland would use these methods in 2050?",
           f"If Uganda promoted soil-friendly farming (less ploughing, keeping crop residues on the field) {AMB}, how many "
           f"hectares of farmland would use these methods in 2050?"),
    "R1": (43, "Biogas Recovered from Wastewater Treatment Plants", None, True,
           "biogas recovery factor ↔ biogas recovered",
           f"If Uganda's wastewater treatment plants captured biogas {AMB}, how much biogas would they recover in 2050?",
           f"If Uganda's wastewater treatment plants captured biogas {AMB}, how many tonnes of biogas would they recover in 2050?"),
    "R3": (5, "Electrical Transmission Loss", None, True, "transmission loss fraction ↔ electricity lost",
           f"If Uganda cut the losses in its electricity grid {AMB}, how much electricity would still be lost in "
           f"transmission in 2050?",
           f"If Uganda cut the losses in its electricity grid {AMB}, how many petajoules (PJ) of electricity would still "
           f"be lost in transmission in 2050?"),
    "R6": (2, "Total Food Produced Lost Before Consumption", None, True, "fraction of food lost ↔ food lost",
           f"If Uganda reduced food losses along the supply chain {AMB}, how much food would still be lost before it "
           f"reaches consumers in 2050?",
           f"If Uganda reduced food losses along the supply chain {AMB}, how many tonnes of food would still be lost "
           f"before it reaches consumers in 2050?"),
    "R8": (52, "Total MSW Recovered for Energy", None, True,
           "fraction of incinerated municipal waste recovered for energy ↔ municipal waste recovered for energy",
           f"If Uganda recovered energy from the municipal waste it burns {AMB}, how much municipal solid waste would be "
           f"recovered for energy in 2050?",
           f"If Uganda recovered energy from the municipal waste it burns {AMB}, how many tonnes of municipal solid waste "
           f"would be recovered for energy in 2050?"),
    "N1": (52, "Total ISW Recovered for Energy", None, True,
           "fraction of incinerated industrial waste recovered for energy ↔ industrial waste recovered for energy",
           f"If Uganda recovered energy from the industrial waste it burns {AMB}, how much industrial waste would be "
           f"recovered for energy in 2050?",
           f"If Uganda recovered energy from the industrial waste it burns {AMB}, how many tonnes of industrial waste "
           f"would be recovered for energy in 2050?"),
    "N2": (19, "LSMM Biogas Recovered from Anaerobic Digesters", None, True,
           "biogas recovery factor at manure digesters ↔ biogas recovered from manure",
           f"If Uganda's manure digesters captured biogas {AMB}, how much biogas would be recovered from manure in 2050?",
           f"If Uganda's manure digesters captured biogas {AMB}, how many tonnes of biogas would be recovered from manure "
           f"in 2050?"),
    "N3": (20, "Dung Incinerated", None, True, "share of cattle and pig manure incinerated ↔ manure incinerated",
           f"If manure from cattle and pigs were managed {AMB}, how much manure would still be incinerated in 2050?",
           f"If manure from cattle and pigs were managed {AMB}, how many tonnes of manure would still be incinerated in 2050?"),
    "N4": (54, "Total Waste Recycled", "qty_waso_recycled_glass_tonne", True, "fraction of glass recycled ↔ glass recycled",
           f"If Uganda recycled its waste {AMB}, how much glass would be recycled in 2050?",
           f"If Uganda recycled its waste {AMB}, how many tonnes of glass would be recycled in 2050?"),
    "N5": (49, "Total Waste Composted", "qty_waso_compost_food_tonne", True,
           "fraction of food waste composted ↔ food waste composted",
           f"If Uganda composted and digested its organic waste {AMB}, how much food waste would be composted in 2050?",
           f"If Uganda composted and digested its organic waste {AMB}, how many tonnes of food waste would be composted "
           f"in 2050?"),
    "N6": (49, "Total Waste Anaerobic Biogas", "qty_waso_biogas_food_tonne", True,
           "fraction of food waste treated anaerobically ↔ food waste to anaerobic digestion",
           f"If Uganda composted and digested its organic waste {AMB}, how much food waste would go to anaerobic "
           f"digestion in 2050?",
           f"If Uganda composted and digested its organic waste {AMB}, how many tonnes of food waste would go to "
           f"anaerobic digestion in 2050?"),
    # ── O: other-type (general wording only) ─────────────────────────────────────────────────────────────────────────
    "R4": (11, "Total Electrical Energy Consumption from Industrial Energy", None, False,
           "industrial fuel fractions ↔ electricity used (a fuel mix, not an amount)",
           f"If Uganda's industry switched its energy use to electricity {AMB}, how much electricity would industry use in 2050?",
           None),
    "R5": (28, "Total Electrical Energy Consumption from SCOE", None, False,
           "appliance demand multiplier ↔ electricity used",
           f"If homes and businesses used appliances that were efficient {AMB}, how much electricity would buildings use "
           f"in 2050?", None),
    "R7": (31, "Total Energy Consumption from Transportation", None, False, "transport demand multiplier ↔ energy used",
           f"If Uganda reduced the demand for passenger and freight transport {AMB}, how much energy would transport use "
           f"in 2050?", None),
    "S35": (35, "Vehicle Distance Traveled from Electricity", "vehicle_distance_traveled_trns_road_light_electricity", False, "light-duty fuel fractions ↔ distance",
            f"If Uganda moved cars and vans to electricity {AMB}, how far would electric cars and vans travel in 2050?",
            None),
    "HD1": (35, "Total Electrical Energy Consumption from Transportation", None, False,
            "light-duty fuel fractions ↔ electricity used",
            "If cars and vans moved to electricity as far as the model allows, how much more electricity would transport "
            "use in 2050?", None),
    "O1": (27, "Total Energy Consumption from SCOE", None, False, "heat demand multiplier ↔ energy used",
           f"If homes and businesses reduced the energy they need for heating {AMB}, how much energy would buildings use "
           f"in 2050?", None),
    "O2": (47, "Total Nitrogen Removed in Treatment", None, False,
           "shares of urban wastewater by treatment type ↔ nitrogen removed (a share of wastewater, not of nitrogen)",
           f"If Uganda treated its urban wastewater {AMB}, how much nitrogen would be removed in wastewater treatment in "
           f"2050?", None),
    "O3": (10, "Total Energy Consumption from Industrial Energy", None, False, "fuel efficiency factor ↔ energy used",
           f"If Uganda's industry used energy as efficiently as is realistically possible, how much energy would industry "
           f"use in 2050?", None),
}
REUSED = {"S50", "S3", "R1", "R3", "R6", "R8", "R4", "R5", "R7", "S35", "HD1"}
# HD1 asks for a change ("how much more"): key as in the E1 bank spec, the lever's top vs bottom third, an increase of
# about 3 to 5 PJ (56.0 → 59.9 PJ); a level near 60 PJ is also accepted (as in reanalysis_v2.py)
CHANGE_KEY = {"HD1": "an increase of about 3 to 5 PJ (bottom third 56.0 PJ → top third 59.9 PJ); a level of 59–60.5 PJ also counts"}


def steps(net, lever: int, node_id: str) -> int:
    frontier, seen, d = {f"L{lever}"}, {f"L{lever}"}, 0
    while frontier and node_id not in frontier:
        d += 1
        frontier = {t for n in frontier for t in net.out.get(n, []) if t not in seen}
        seen |= frontier
    return d if node_id in frontier else -1


def main():
    run = get_run(active_run_name())
    net = network(run)
    out = {}
    for qid, (lever, node, field, share, why, general, explicit) in TARGETS.items():
        node_id, _ = net.resolve(node)
        r = model_network(run, node, YEAR, "v1", lever=lever)
        f = next(x for x in r["fields"] if field in (None, x["field"]))
        v = f["values"]
        lev = model_network(run, lever, YEAR, "v1")
        inputs = (lev.get("input_values") or {}).get("fields") or []
        out[qid] = {
            "set": "S" if share else "O", "share_type": share, "why_share_label": why,
            "lever": lever, "lever_name": lev["name"], "lever_inputs": len(inputs),
            "lever_input_example": (f"{inputs[0]['field']}: {inputs[0]['bau']} → {inputs[0]['top_of_range']}"
                                    if inputs else ""),
            "node": node, "field": f["field"], "unit": f["unit"], "year": YEAR,
            "steps_from_lever": steps(net, lever, node_id),
            "key_median": v["high"]["median"], "key_p10": v["high"]["p10_p90"][0], "key_p90": v["high"]["p10_p90"][1],
            "low_third_median": v["low"]["median"], "runs_in_top_third": v["high"]["runs"],
            "question_general": general, "question_explicit": explicit,
            "key_rule": CHANGE_KEY.get(qid, "value inside p10–p90 of the lever's top third"),
            "new": qid not in REUSED, "visit": node_id,
            "status": "approved by Alexa 2026-11-17 as written; frozen with docs/run_design_E3_2026-11-17.md"}
        print(f"{qid:4s} {'S' if share else 'O'} L{lever:<3} {node[:48]:48s} {out[qid]['steps_from_lever']} steps  key "
              f"{v['high']['median']:.4g} ({v['high']['p10_p90'][0]:.4g}–{v['high']['p10_p90'][1]:.4g}) {f['unit']}")
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
