# Run from metamodel/chatbot_deploy:  python3 results_analysis/code/walk_depth.py  → results_analysis/walk_depth.xlsx
"""Does the agent walk the network far enough? The questions whose answer sits on an in-between node of the network
(S50, S3, S35, HA1, HD1): per conversation, whether the agent reached that node with model_network, how many network
calls it made, and whether its answers gave the value from the runs (check 22, Haiku). Reads the logs and
failure_modes.csv; no API calls. Finding of 2026-10-28: with values from the first step (v1), the agent often stops
at the lever and says the tools cannot give the number, or computes one itself.
"""
import json
import re
from pathlib import Path

import pandas as pd

RUNS = Path("backend/rdm/eval/pilot_runs/bank_v3_full")
OUT = Path(__file__).parents[1] / "walk_depth.xlsx"
# the node that holds the answer (its name as the network shows it, or its field)
TARGET = {
    "S50": r"biogas recovered from landfills|gasrecovered_waso_biogas_landfills",
    "S3": r"area of improved land|area_lndu_improved_croplands",
    "S35": r"vehicle distance traveled from electric|vehicle_distance_traveled_trns_road_light_electricity",
    "HA1": r"vehicle distance traveled from electric|vehicle_distance_traveled_trns_road_light_electricity",
    "HD1": r"total electrical energy consumption from transportation|energy_consumption_electricity_trns",
}
# questions whose required statement (check 22) is "gives the value from the model runs"; HA1's answer is a lever
# level (check 03), so it shows the walk only
VALUE_ASKED = ("S50", "S3", "S35", "HD1")


def main():
    fm = pd.read_csv(RUNS / "failure_modes.csv").set_index("file")
    rows = []
    for q, rx in TARGET.items():
        for arm in ("v0", "v1"):
            for rep in range(5):
                f = f"{q}_{arm}_r{rep}.json"
                run = json.loads((RUNS / f).read_text())
                nodes = [str(c["args"].get("node")) for c in run["tool_log"]
                         if c["tool"] == "model_network" and c["status"] == "ok"]
                hit = [i for i, n in enumerate(nodes, 1) if re.search(rx, n, re.I)]
                says = fm.loc[f, "22_statement_missing"]
                rows.append({
                    "question": q, "arm": arm, "rep": rep, "network_calls": len(nodes),
                    "reached_target_node": int(bool(hit)), "calls_to_reach": hit[0] if hit else None,
                    "walk": " → ".join(nodes),
                    "gave_run_value (22 ok)": (None if q not in VALUE_ASKED or pd.isna(says)
                                               else int(str(says) == "False")),
                    "first_answer_start": run["answers"][0][:300],
                    "untraced_numbers (15)": fm.loc[f, "untraced"],
                    "log_file": f})
    t = pd.DataFrame(rows)
    s = (t.groupby(["question", "arm"])
          .agg(conversations=("rep", "size"), reached_target=("reached_target_node", "sum"),
               mean_network_calls=("network_calls", "mean"), gave_run_value=("gave_run_value (22 ok)", "sum"))
          .reset_index())
    v1 = t[(t.arm == "v1") & t.question.isin(VALUE_ASKED)]
    cross = (v1.groupby("reached_target_node")
               .agg(conversations=("rep", "size"), gave_run_value=("gave_run_value (22 ok)", "sum")).reset_index())
    with pd.ExcelWriter(OUT, engine="xlsxwriter") as xw:
        for name, d in (("Summary", s), ("v1 reached vs answered", cross), ("Conversations", t)):
            d.to_excel(xw, sheet_name=name, index=False)
            xw.sheets[name].set_column(0, len(d.columns) - 1, 18)
    print(s.to_string(index=False))
    print(cross.to_string(index=False))
    print(OUT)


if __name__ == "__main__":
    main()
