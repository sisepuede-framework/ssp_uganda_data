"""
metrics_all_targets.py
----------------------
Writes a readable report of the DEPLOYED surrogate's held-out performance for every one of its 258 targets,
from the per-target metrics that evaluate_sector_model.py saved. It reads the CSV only: no model, no data.

Run:  python metrics_all_targets.py
Out:  trained_models/metrics_<RUN_ID>_all_targets.md
"""
import os

import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "config", "ml_training_workflow_config.yaml")) as f:
    RUN_ID = str(yaml.safe_load(f)["run_id"])
TM = os.path.join(HERE, "trained_models")
CSV = os.path.join(TM, f"metrics_{RUN_ID}.csv")
SPLIT = os.path.join(TM, f"split_{RUN_ID}.csv")
OUT = os.path.join(TM, f"metrics_{RUN_ID}_all_targets.md")

UNITS = {"Emissions": "Mt CO₂e", "Benefits": "billion USD", "Costs": "billion USD",
         "GDP": "billion international $ (PPP, constant prices)"}
FAMILIES = ["Emissions", "Benefits", "Costs", "GDP"]
NO_VAR = 1e-6   # a target whose spread across the test runs is below this does not vary: R² is meaningless there

m = pd.read_csv(CSV)
m["name"] = m["target"].str.replace(r"_yr\d{4}$", "", regex=True)
split = pd.read_csv(SPLIT)["split"].value_counts()
years = sorted(m["year"].unique())
later = m[m["year"] > 2025]


def r2_cell(row):
    if row["y_std"] < NO_VAR:
        return "no var."
    return f"{row['r2']:.3f}" if abs(row["r2"]) < 1000 else f"{row['r2']:.1e}"


def num(x):
    if x == 0:
        return "0"
    return f"{x:.4f}" if abs(x) >= 1e-3 else f"{x:.1e}"


L = []
L.append("# How well the surrogate predicts each variable\n")
L.append(f"This is the performance of the XGBoost surrogate on the runs it never saw during training, for every one of "
         f"its {len(m)} targets. A target is one output of the model in one year: {m['name'].nunique()} outputs "
         f"(emissions by sector, benefits, costs and GDP) × {len(years)} years. We trained it on "
         f"{split.get('train', 0):,} of the SISEPUEDE runs and kept {split.get('test', 0):,} apart to test it. This is "
         f"the model we retrained on 2026-10-16, without the outlier filter, and it's the engine the agent used in the "
         f"290 conversations.\n")
L.append(f"Run `{RUN_ID}` · model `xgb_pipeline_sector_independent_{RUN_ID}.pkl`.\n")
L.append("## How to read it\n")
L.append("For each target we report four numbers, and each one answers a different question:\n")
L.append("- **R²**: how much of the difference between runs the surrogate reproduces. 1 means it gets all of it, 0 "
         "means it does no better than always giving the average, and below 0 means it does worse than that.")
L.append("- **MAE**: how far the prediction is from the real value on average, in the target's own units. **RMSE** is "
         "the same idea, but big errors count more.")
L.append("- **SMAPE**: that same error as a percentage of the value, so we can compare targets with different units.")
L.append("- **Spread**: how much the real value changes from one run to another (standard deviation over the test "
         "runs). When the spread is almost zero, R² stops being meaningful, so there we read MAE instead. *no var.* "
         "means a spread below 10⁻⁶.")
L.append("- Units: " + "; ".join(f"{k}: {v}" for k, v in UNITS.items()) + ".\n")

L.append("## Summary by family (2035–2070)\n")
L.append("| Family | Targets | Median R² | Mean R² | Min R² | Median SMAPE % | R² < 0.8 |")
L.append("|---|---|---|---|---|---|---|")
for fam in FAMILIES + ["All"]:
    d = later if fam == "All" else later[later["family"] == fam]
    b = "**" if fam == "All" else ""
    L.append(f"| {b}{fam}{b} | {len(d)} | {d['r2'].median():.3f} | {d['r2'].mean():.3f} | {d['r2'].min():.3f} | "
             f"{d['smape'].median():.2f} | {(d['r2'] < 0.8).sum()} |")
L.append("")

L.append("## Why 2025 is reported separately\n")
y25 = m[m["year"] == 2025]
n_flat = (y25["y_std"] < NO_VAR).sum()
L.append("The story is simple: in 2025 there is almost nothing to predict.\n")
L.append(f"R² compares the surrogate's error with how much the target changes between runs, R² = 1 − (error ÷ "
         f"variation between runs). The policies and uncertainties ramp in from the 2019 base, so by 2025 they have "
         f"barely moved anything, and the runs look almost the same. In {n_flat} of the 43 outputs the spread is below "
         f"10⁻⁶ (median {y25['y_std'].median():.1e}, against {later['y_std'].median():.2f} in 2035–2070). When we divide "
         f"by a number that is almost zero, R² explodes to huge negative values, as low as {y25['r2'].min():.1e}, even "
         f"though the error itself is tiny: median MAE {y25['mae'].median():.1e}, and the largest is "
         f"{y25['mae'].max():.4f}.\n")
r25 = y25.set_index("name")
L.append("So the surrogate is not failing in 2025. It predicts a value that hardly changes, and its errors are tiny. "
         "Among the few outputs that already move a little by 2025, some score well, like transport emissions (R² "
         f"{r25.loc['emission_transportation', 'r2']:.2f}), and others don't, like technical costs "
         f"({r25.loc['cost_technical', 'r2']:.2f}) or deforestation ({r25.loc['emission_deforestation', 'r2']:.2f}), "
         "but even there the spread is so small that the error is too. If we mixed 2025 into the averages, it would "
         "pull them down for a reason that has nothing to do with accuracy, so we keep it apart and list it in full "
         "below.\n")

L.append("## R² by output and year\n")
L.append("One row per output, one column per year. The last column is the median over 2035–2070, and the rows "
         "go from the weakest to the strongest in each family, so the outputs to be careful with are at the top.\n")
for fam in FAMILIES:
    d = m[m["family"] == fam]
    order = d[d["year"] > 2025].groupby("name")["r2"].median().sort_values()
    L.append(f"### {fam} ({UNITS[fam]})\n")
    L.append("| Output | " + " | ".join(str(y) for y in years) + " | Median 2035–70 |")
    L.append("|---|" + "---|" * (len(years) + 1))
    for name, med in order.items():
        row = d[d["name"] == name].set_index("year")
        L.append(f"| `{name}` | " + " | ".join(r2_cell(row.loc[y]) for y in years) + f" | **{med:.3f}** |")
    L.append("")

L.append("## Every target, all metrics\n")
for fam in FAMILIES:
    d = m[m["family"] == fam].sort_values(["name", "year"])
    L.append(f"### {fam} ({UNITS[fam]})\n")
    L.append("| Target | Year | R² | MAE | RMSE | SMAPE % | Spread |")
    L.append("|---|---|---|---|---|---|---|")
    for _, r in d.iterrows():
        L.append(f"| `{r['name']}` | {r['year']} | {r2_cell(r)} | {num(r['mae'])} | {num(r['rmse'])} | "
                 f"{r['smape']:.2f} | {num(r['y_std'])} |")
    L.append("")

with open(OUT, "w") as f:
    f.write("\n".join(L))
print(OUT, len(L), "lines")
