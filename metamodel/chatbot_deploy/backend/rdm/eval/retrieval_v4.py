"""
Eight new retrieval questions (R1–R8) for working paper v2, drafted and approved by Alexa 2026-11-16 (as written);
frozen with docs/run_design_v4_2026-11-16.md.

Why: the retrieval result of the full run (reached the node holding the answer: Map 16/20, Map+ 7/20; value inside
the key: 0/20 vs 7/20) rests on four questions and was defined after the results were seen. These eight are written
before any conversation is run on them, to test it prospectively in all three arms (v0 Map, v1 Map+, v2 Map+lever).

How they were chosen (no agent run involved): every lever's in-between variables two or three steps away in the
network, with one field and values in the runs; kept those the lever moves by at least 10% between its bottom and top
third (58 candidates); picked one per sector, none used by an existing question, in plain words a policy maker could
use. R7 is three steps from its lever (the others two).

Key rule (as for S50, S3, S35): the value model_network shows for the lever's top third, 2050: median and p10–p90.
A valid answer gives a value inside p10–p90 and says it comes from the model runs, not the surrogate.

Run from metamodel/chatbot_deploy:
    /opt/miniconda3/envs/uganda_metamodel_env/bin/python -m backend.rdm.eval.retrieval_v4
    → backend/rdm/eval/retrieval_v4_reference.json   (read by docs writer and, once frozen, by questions.py)
"""
import json
from pathlib import Path

from backend.rdm.runs import active_run_name, get_run
from backend.rdm.tools.network import model_network, network

OUT = Path(__file__).parent / "retrieval_v4_reference.json"
YEAR = 2050
AMBITIOUS = "as ambitiously as is realistically possible"   # = the range maximum, the lever's top third (S questions)

QUESTIONS = {
    "R1": {"lever": 43, "node": "Biogas Recovered from Wastewater Treatment Plants", "sector": "Wastewater",
           "question": f"If Uganda's wastewater treatment plants captured biogas {AMBITIOUS}, how much biogas would "
                       f"they recover in 2050?"},
    "R2": {"lever": 20, "node": "LSMM Biogas Recovered from Anaerobic Digesters", "sector": "Livestock manure",
           "question": f"If manure from cattle and pigs were managed {AMBITIOUS}, with more of it going to anaerobic "
                       f"digesters, how much biogas would be recovered from manure in 2050?"},
    "R3": {"lever": 5, "node": "Electrical Transmission Loss", "sector": "Electricity",
           "question": f"If Uganda cut the losses in its electricity grid {AMBITIOUS}, how much electricity would "
                       f"still be lost in transmission in 2050?"},
    "R4": {"lever": 11, "node": "Total Electrical Energy Consumption from Industrial Energy", "sector": "Industry",
           "question": f"If Uganda's industry switched its energy use to electricity {AMBITIOUS}, how much "
                       f"electricity would industry use in 2050?"},
    "R5": {"lever": 28, "node": "Total Electrical Energy Consumption from SCOE", "sector": "Buildings",
           "question": f"If homes and businesses used appliances that were efficient {AMBITIOUS}, how much "
                       f"electricity would buildings use in 2050?"},
    "R6": {"lever": 2, "node": "Total Food Produced Lost Before Consumption", "sector": "Agriculture",
           "question": f"If Uganda reduced food losses along the supply chain {AMBITIOUS}, how much food would still "
                       f"be lost before it reaches consumers in 2050?"},
    "R7": {"lever": 31, "node": "Total Energy Consumption from Transportation", "sector": "Transport demand",
           "question": f"If Uganda reduced the demand for passenger and freight transport {AMBITIOUS}, how much "
                       f"energy would transport use in 2050?"},
    "R8": {"lever": 52, "node": "Total MSW Recovered for Energy", "sector": "Solid waste",
           "question": f"If Uganda recovered energy from the municipal waste it burns {AMBITIOUS}, how much "
                       f"municipal solid waste would be recovered for energy in 2050?"},
}


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
    for qid, q in QUESTIONS.items():
        node_id, _ = net.resolve(q["node"])
        r = model_network(run, q["node"], YEAR, "v1", lever=q["lever"])
        f = r["fields"][0]
        v = f["values"]
        lev = model_network(run, q["lever"], YEAR, "v1")
        out[qid] = {**q, "lever_name": lev["name"], "field": f["field"], "unit": f["unit"], "year": YEAR,
                    "steps_from_lever": steps(net, q["lever"], node_id),
                    "key_median": v["high"]["median"], "key_p10": v["high"]["p10_p90"][0],
                    "key_p90": v["high"]["p10_p90"][1], "low_third_median": v["low"]["median"],
                    "runs_in_top_third": v["high"]["runs"],
                    "visit": node_id, "status": "approved by Alexa 2026-11-16 as written; frozen with docs/run_design_v4_2026-11-16.md"}
        print(f"{qid} L{q['lever']:<3} {q['node'][:55]:55s} {out[qid]['steps_from_lever']} steps  key "
              f"{v['high']['median']:.4g} ({v['high']['p10_p90'][0]:.4g}–{v['high']['p10_p90'][1]:.4g}) {f['unit']}")
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
