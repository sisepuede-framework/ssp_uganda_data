# Investigation request: `uganda_pathways.csv` — granular emission columns don't reconcile to the subsector totals in future years

## TL;DR
In `uganda_pathways.csv`, the **granular** `emission_co2e_*` columns and the **aggregate**
`emission_co2e_subsector_total_*` columns **agree at 2019 but diverge for every future
year**. The granular columns sum ~2–10 Mt CO₂e *higher* than the subsector totals, and the
gap grows with biomass-energy use (larger in BAU, smaller in the deep-mitigation HBLE
pathway). The same reconciliation is **exact at all years in `decomposed_emissions`** for the
same run — so the crosswalk/aggregation logic is fine; something in how *this file's*
granular vs. total columns are produced is inconsistent after the base year.

## Run / file
- Run: `sisepuede_run_2026-05-30t21;35;56.244639`
- File: `.../pathways/uganda_pathways.csv` (WIDE: one row per (primary_id, time_period))
- ~4,119 columns, incl. 623 granular `emission_co2e_*` and 133 `emission_co2e_subsector_total_*`.

## Symptom (reproducible)
Summing the two column families for the same row should give the same national total. It
doesn't, except at 2019 (time_period 4):

```
BAU (primary_id=0):   year | Σ subsector_total | Σ granular fields | gap
   2019   112.345   112.345   +0.000
   2035   154.731   157.245   +2.514
   2050   195.144   204.997   +9.853
   2060   240.142   250.055   +9.913
   2070   277.590   286.786   +9.196

HBLE (primary_id=5005):
   2019   112.345   112.345   +0.000
   2035   101.400   103.580   +2.181
   2050    49.124    52.376   +3.252
   2060    28.206    29.883   +1.676
   2070     6.347     8.207   +1.860
```

("Σ granular fields" here = the sum of the ~505 granular fields our inventory crosswalk maps
into the 23 aggregation categories, i.e. `crosswalk_inventory_to_sisepeude_20260510.csv`
column `sisepuede_fields`. Using the crosswalk isn't the point — see the control below.)

## The control that isolates it to this file
Run the **identical** reconciliation on `decomposed_emissions` for the same run (the
post-processed FINAL emissions table). There, Σ(crosswalk granular fields) equals
Σ(subsector_total columns) **exactly at every year**:

```
decomposed_emissions:  year | Σ subsector_total | Σ crosswalk granular | gap
   2019   112.345   112.345   0.000
   2050    99.113    99.113   0.000
   2070   103.117   103.117   0.000
```

So the aggregation definition is self-consistent. The problem is specific to how
`uganda_pathways.csv` is assembled: **its granular `emission_co2e_*` columns and its
`emission_co2e_subsector_total_*` columns are not from the same, consistent stage** for
future years.

## Strongest clue
The gap correlates with **biomass-combustion CO₂** (firewood/charcoal). It's ~0 at 2019
(where both column families include it), and in future years it's large in BAU (heavy biomass
use, ~+9 Mt) and small in HBLE (biomass phased out, ~+1.9 Mt). This looks like the
**subsector-total columns had a biomass adjustment applied (e.g. biomass CO₂ moved/zeroed per
the LULUCF memo convention) while the granular columns were left at a pre-adjustment stage**
— or the two column families were written from different processing steps / different vintages
of the run.

## Questions for you (the file's producer)
1. Are the granular `emission_co2e_*` columns and the `emission_co2e_subsector_total_*`
   columns in `uganda_pathways.csv` written from the **same** post-processed object, or are the
   granular ones carried over from an earlier/raw step?
2. Is any biomass-CO₂ / LULUCF-memo reallocation applied to the subsector totals but **not**
   to the granular columns (or vice-versa)?
3. Should `uganda_pathways.csv` match `decomposed_emissions` field-for-field for the named
   pathways? (If the named pathway primary_ids exist in `decomposed_emissions`, a direct
   row-by-row diff would localize the broken columns immediately.)

## Why we care (context)
We're moving the chatbot's sectors to the **official 23 inventory categories** (your crosswalk),
computing each category as the sum of its `sisepuede_fields`. This works perfectly off
`decomposed_emissions` (the surrogate's training data). But for the 6 real named pathways we
read `uganda_pathways.csv`, and its broken granular columns make the per-category breakdown —
and the net total — wrong for future years (e.g. HBLE 2070 comes out 8.2 instead of the
correct 6.35). We'd like the granular columns fixed so the real pathways can use the same 23
categories consistently. In the meantime we'll trust the `subsector_total_*` columns for the
net total.

## Minimal repro (Python)
```python
import pandas as pd
df = pd.read_csv("uganda_pathways.csv")
cw = pd.read_csv("crosswalk_inventory_to_sisepeude_20260510.csv")
fields = sorted({f.strip() for s in cw["sisepuede_fields"] for f in s.split(":") if f.strip()})
totcols = [c for c in df.columns if c.startswith("emission_co2e_subsector_total_")][:15]
for pid in (0, 5005):
    for tp in (4, 35, 55):  # 2019, 2050, 2070
        r = df[(df.primary_id==pid) & (df.time_period==tp)].iloc[0]
        A = r[totcols].fillna(0).sum()
        B = r[[f for f in fields if f in df.columns]].fillna(0).sum()
        print(pid, 2015+tp, round(A,3), round(B,3), round(B-A,3))
```
