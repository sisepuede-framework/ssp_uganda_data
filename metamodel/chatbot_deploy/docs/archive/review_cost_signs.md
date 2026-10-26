# Review: how costs and benefits are signed, from SISEPUEDE to `trade_off_analysis`

Date: 2026-10-19. Read-only audit; no file was changed. Plan item P8 in `rdm_information_layer_plan.md`.

## Bottom line

- **One convention runs end to end: positive = good for the country, negative = bad.** A cost (money spent, damage) is negative and a benefit or saving is positive. This holds for all 19 cb fields and for the surrogate targets. The field name ("cost", "benefit") only says which category a field is in. It does not tell you the sign.
- **The sign flip in `trade_off_analysis` / `surrogate.py` is correct.** `cost_total = −(fuel + system + technical)` so positive = net money spent. `net_benefit` and cost per tonne have consistent signs.
- **What the numbers *mean* is the bigger problem, more than their signs:**
  1. In the 100k run, every run's cb is measured against **one** BASE run (BASE strategy, future 0), not against BASE in the same future. So levels mix the policy effect with the uncertainty effect. Only *policy − BAU on the same futures* isolates the policy. The tools already report that, but they also show levels.
  2. "Cost" in our tools is a hybrid. The fuel bucket holds only biogas/waste-to-energy **revenue**, and the system bucket holds transport **savings**. Meanwhile, fuel-spending changes and technical savings sit in the benefit buckets.
  3. Some items do not depend on lever levels: healthier-diet benefits (~19 bn USD/yr), enteric-fermentation cost, maritime fuel-switch cost. They cancel in policy − BAU, so the tools can never show them.
- **Lever 15 (Reduce DEFORESTATION) = 1 → benefits −2.6 bn USD in 2050 is a real model result, not a sign error.** The raw runs show the same pattern. It comes from valuing grassland at 5,700 $/ha against forest at 300–500 $/ha.

## 1. What `costs_benefits_ssp` (v0.1.19) computes

Generic formula (`cb_calculate.py`, `cb_difference_between_two_strategies`, lines 800 and 806):

```python
data_merged["difference_value"] = data_merged[f"{cb_orm.diff_var}{tx_suffix}"] - data_merged[f"{cb_orm.diff_var}{base_suffix}"]
data_merged["value"] = data_merged["difference_value"]*cb_orm.multiplier*cb_orm.annual_change**data_merged["time_period_for_multiplier_change"]
```

- **Difference vs a baseline strategy:** `value = (pathway − baseline) × multiplier × annual_change^(t−2023)`. The baseline is `strategy_code_base`, which is `"BASE"` in every Uganda script. Pathway and baseline are merged on `region, time_period, future_id` (line 796).
- **Sign:** the formula itself has no sign rule. **The sign comes entirely from the sign of `multiplier` in `cb_config_params.xlsx`.** Uganda's config chooses the multipliers so that bad = negative, for example:

| Item | Multiplier | If the pathway has more of the variable than BASE |
|---|---|---|
| `lndu:ecosystem_services:forests:primary` | +500 $/ha | positive (benefit) |
| `lndu:ecosystem_services_grasslands` | +5,700 $/ha | positive |
| `trns:air_pollution:X:diesel` | −8.47 M$/PJ | negative (damage) |
| `waso:technical_cost:waste_management:*` | −7 to −86 $/t | negative (spending) |
| `entc:technical_cost:electricity:capex` | −1e6 × Δ discounted capital | negative (investment) |
| `scoe:technical_cost:efficiency:building_shell` | +5.56 M$/PJ × Δ demand | demand falls → negative (spending) |
| `waso:fuel_cost:waste_to_energy_value:*` | +323 $/t biogas | positive (revenue) |

  The Uganda pipeline confirms the intent: `cost_benefits_pipeline.py` line 103 says *"Fix ENTC electricity capex sign (must be negative = investment)"*.
  **The bridge doc (`cpat_sisepuede/bridge/docs/costs_benefits_ssp.md` line 105) says the opposite** ("A negative `multiplier` marks a benefit"). That line is wrong for the Uganda config and should be corrected.
- **Not every function is a difference.** `cb_pflo_healthier_diets` (population × a fixed diet schedule), `cb_lvst_enteric` (fixed application schedule), `cb_scale_variable_in_strategy` (maritime), `cb_entc_reduce_losses` and `cb_agrc_lvst_productivity` price the pathway alone. They apply whenever the transformation is in the strategy, whatever its level.
- **No discounting.** `SSP_GLOBAL_COST_YEAR = 4` ("cost everything to 2019") is defined but never used. Values are undiscounted annual flows in constant USD of the factors' source year. The exception is ENTC capex/opex, whose input variables (`nemomod_entc_discounted_capital*`, `…_operating*`) are already discounted inside NemoMod.
- **Units:** USD per year. The 100k post-processing divides by 1e9, giving **billion USD in that year**. This is a flow, not a sum over years. The column name `Cumulative` in `postprocess_cba` means "summed over variables".
- `cb_shift_costs` moves pre-2025 values to 2025 onward. It does not change signs.

## 2. Is the convention the same across cost and benefit types?

The sign rule (negative = bad) is the same for all of them, but **the bucket names do not match their content**:

| cb field (3rd part of the variable name) | What is actually in it (Uganda config) | Typical sign in the run, 2050 |
|---|---|---|
| `technical_cost` | Transformation spending, plus some system items (wetland and grassland upkeep, wastewater, waste collection) | always negative (−13 to −5 bn) |
| `system_cost` | Transport system costs per vkm / t-km | always positive (+2 to +12 bn): fewer km than BASE = savings |
| `fuel_cost` | **Only biogas / waste-to-energy value** (lsmm, trww, waso) | always positive (+0.4 to +1.5 bn): revenue |
| `sector_specific` (surrogate: a *benefit*) | Fuel spending by sector (`{sector}:sector_specific:fuel_cost:X`, −500 × fuel value) | small positive (+0.1 to +0.24 bn) |
| `technical_savings` (surrogate: a *benefit*) | Operating savings of transformations | mostly negative |
| `lvst_value`, `crop_value`, `ecosystem_services_grasslands`, `water_pollution` (benefits) | Output values and ecosystem values | often or always negative |

Why `fuel_cost` holds no fuel spending: the 52 `cb:enfu:fuel_cost:*` rows have `cb_function = cb_strategy_specific_function` or `cb_system_fuel_costs`. Neither name appears in the `match` in `mapping_strategy_specific_functions` (lines 255–285), so the function returns `None` and `pd.concat` drops the row silently. The rename meant to rescue `cb:enfu:fuel_cost:X:X` compares `cb_function` against a variable name (line 358), so it never fires. The same applies to the four `sector_specific:electricity_cost:X` rows. The older variable-level output (`combined_cb_results_…2025-11-12…csv`) has no `cb:enfu:fuel_cost` rows at all, which is consistent with this.

## 3. The run's `cb` table and the surrogate targets

- **Reference in the 100k run.** `100k_run_postprocessing_parallel.py` lines 655–674 concatenate the single BASE run (`primary_id 0`, design 0, future 0) with the current run, then set `cb.ssp_data["future_id"] = 0` for both. So **every run (strategy 6007 PFLO:HBLE, design 4, future k, lever levels L) is compared with BASE in future 0.** It is not compared with BASE in future k, because no such run exists (`ATTRIBUTE_PRIMARY`: 1 BASE row + 100,000 design-4 rows).
  - Consequence: `cb(run) ≈ policy effect(L, X) + uncertainty effect(X vs future 0) + fixed items`. A run with all levers at 0 would *not* have zero cb.
- **Athena → training data.** `queries/cost_benefit.sql` takes the 19 fields unchanged. `assemble_training_data.py` names the three `*_cost` fields `cost_<type>` and the other 16 `benefit_<type>`, with no re-sign. The comments "costs negative, benefits positive" are only half true. Costs are negative as a sign rule (and `system_cost`/`fuel_cost` are in fact positive). Several "benefits" are negative.
- The ENTC capex sign fix in `cost_benefits_pipeline.py` is **not** applied in the 100k path. This hardly matters: the multiplier already makes more capex negative.
- **Does "change vs BAU on the same futures" work?** Yes, and it is the only meaningful reading. Subtracting BAU (all L = 0) in the same futures cancels the uncertainty effect and the fixed items, leaving the lever effect. Two caveats:
  - BAU (all L = 0) is **outside the training data**. No run has all 50+ levers below 0.1; the most any run has is 32% of levers below 0.1. The surrogate extrapolates there. For example, it predicts `cost_fuel` = −0.07 at BAU, while every real run is positive.
  - Lever-independent items (diets, enteric, maritime) drop out. The tools cannot show the health and consumer-savings value of the diet lever, nor the cost of the enteric-fermentation lever.

## 4. Our tools: sign at each step

| Step | Quantity | Positive means | Negative means | Correct? |
|---|---|---|---|---|
| Package | `value` per cb variable | benefit / saving / revenue vs BASE | cost / damage vs BASE | yes (by config) |
| 100k post-processing | 19 cb fields, bn USD/yr, vs BASE future 0 | net good vs the reference run | net bad | yes; reference is one fixed future |
| Training data / surrogate | `cost_<type>` (3), `benefit_<type>` (16) | good for the country | bad | yes; names misleading |
| `surrogate.py` | `cost_total = −Σ cost_<type>` | net money spent (after biogas revenue and transport savings) | net savings | sign yes; definition hybrid |
| `surrogate.py` | `benefit_total = Σ benefit_<type>` | net benefit | net loss | yes |
| `surrogate.py` | `net_benefit = benefit_total − cost_total` (= sum of all 19 signed fields) | good | bad | **yes** |
| `surrogate.py` | `cost_pct_gdp = cost_total / GDP` | — | — | sign yes; **level is meaningless** (BAU −3.9 bn → negative %) |
| `trade_off_analysis` | `cost_change_vs_bau = Δcost_total` | policy costs more than BAU | policy saves money | yes |
| `trade_off_analysis` | `cost_per_tonne = 1000·Δcost_total / abated` (only where abated > 0.1 Mt) | USD spent per t avoided | money saved per t avoided | yes; excludes technical savings and fuel savings |
| `trade_off_analysis` | `cost` (level) | — | — | **misleading**: a difference vs BASE future 0, not money spent |
| `exploratory_modeling` | `cost_<type>` raw | saving | spending | **unlabelled**; the agent is told nothing about the sign |
| `vulnerability_analysis` | default `pass_if` | — | — | **wrong for `cost_<type>`** ("below" passes when *more* is spent); with `reduction_vs_bau_pct` on a benefit metric, it passes when the benefit *falls* |
| `scripts/build_lever_response_map.py` | `cost_total = Σ cost_<type>` (not flipped), label "Total costs" | saving | spending | **opposite sign** to `surrogate.py`'s `cost_total` under the same name |

## 5. Numerical checks (surrogate, 1,000 futures, other levers at 0, 2050, bn USD)

| Lever | Δ cost_technical | Δ cost_fuel | Δ cost_total (flipped) | Δ benefit_total | Δ net_benefit | Abated (Mt) | USD/t | Reading |
|---|---|---|---|---|---|---|---|---|
| 15 Reduce DEFORESTATION = 1 | +0.11 | −0.005 | −0.05 | **−2.64** | −2.58 | 11.1 | −5 | Grassland ES −1.49, livestock −0.95, crops −0.65, forest ES +0.12. The raw runs agree (top vs bottom quintile of L15: grassland −1.80, livestock −0.83, crops −0.69, forest +0.16). **Real result** under the convention, driven by the 5,700 $/ha grassland value and the absence of any implementation cost for this lever. |
| 27 Reduce DEMAND HEAT = 0.67 | −0.21 | +0.01 | +0.21 | +0.02 | −0.08 | 2.1 | 76 | Building-shell spending is negative, as it should be. Fuel savings are almost invisible (sector_specific +0.002). The raw-run quintile contrast gives a small *positive* Δ technical (+0.04), so the surrogate's BAU-corner value is uncertain. |
| 50 Increase CAPTURE BIOGAS = 0.688 | −0.17 | **+0.06** | +0.11 | +0.25 | +0.16 | 2.3 | 58 | Capture cost negative, biogas revenue positive (in the *cost* bucket), technical savings +0.34 (in the *benefit* bucket). Counting all financial items, the lever pays for itself. Cost per tonne counts only part of them. The wetlands ES −0.13 is likely a surrogate artefact. Raw runs agree on fuel (+0.21) and technical (−0.36). |

BAU levels (all L = 0) in 2050: cost_total −3.9, benefit_total 18.0, net_benefit 21.6 bn USD. Diets alone contribute about 18 bn of that benefit level (human health 8.5, consumer savings 9.5). These are not policy effects.

## 6. Verdict and minimal fix

**What the tools tell the agent now:**
- The direction of every change is right, and the cost flip is right.
- Net benefit is right.
- Cost per tonne is right in sign but uses a partial cost definition.
- Levels of cost, benefit and cost_pct_gdp are presented as if they were the policy's money, which they are not.
- Raw `cost_<type>` metrics carry no sign label.
- `vulnerability_analysis` gets the default direction wrong for them.

**Minimal fix (no retraining):**
1. In `trade_off_analysis` and `exploratory_modeling`, report cost and benefit **only as change vs BAU** (drop or demote the levels). State in the note: *"Costs and benefits are differences against a reference run; only the change vs BAU is a policy effect. Positive cost change = more money spent."*
2. Also report `net_benefit` change in `trade_off_analysis`. Optionally report cost per tonne on a "net financial" basis: technical + system + fuel + sector_specific + technical_savings + consumer_savings.
3. Flip raw `cost_<type>` in `surrogate.py` too, so that every metric starting with `cost` means "positive = money spent". Alternatively, label them "signed: negative = spending".
4. Fix `vulnerability_analysis` default `pass_if`: for costs (after step 3) "below". For benefits and net, "above" with `absolute`. With `reduction_vs_bau_pct` on benefits, "below" (a reduction is bad). Better still, refuse `%` thresholds on cost and benefit metrics, since their BAU can be near zero or negative.
5. Drop `cost_pct_gdp` or redefine it as `Δcost_total / GDP`.
6. Align `build_lever_response_map.py` naming ("Total costs" → signed "Net cost items, negative = spending"), or flip it.
7. Tell the agent (`services/agent.py` output lines and tool descriptions) the sign rule and that "fuel" = biogas revenue, plus that lever-independent items (diet health, enteric) do not show up.
8. Correct line 105 of `cpat_sisepuede/bridge/docs/costs_benefits_ssp.md`.

## 7. Open questions for the SISEPUEDE team

1. **Reference run:** was comparing every 100k run with BASE in *future 0* intended? Or should each future have its own BASE, or should the cb be re-based on L = 0?
2. **Fuel costs:** are the `cb:enfu:fuel_cost:*` rows (`cb_strategy_specific_function`, `cb_system_fuel_costs`) and the `sector_specific:electricity_cost` rows meant to be skipped? Fuel spending is currently only in `sector_specific`, at a multiplier of −500 on `totalvalue_enfu_fuel_consumed_*`. What unit is that variable in?
3. **Missing Uganda rows:** `agrc_lvst_productivity_costgdp` and `entc_reduce_losses_cost_file` have no UGA row, so productivity and grid-loss costs are silently zero. Is that intended?
4. **Lever-independent items:** diets, enteric fermentation and maritime are priced from fixed schedules, regardless of lever level. Should they scale with the lever in the design-4 runs?
5. **Valuations:** grassland ecosystem services at 5,700 $/ha and wetlands at 10,672 $/ha, against forest at 300–500 $/ha. Is this the intended relative valuation? It makes forest protection look like a net loss.
6. **No cost for deforestation reduction:** no `transformation_costs` row covers the deforestation lever. Is that intended?
7. **Discounting / price year:** values are undiscounted except the NemoMod capex/opex inputs. What price year are the factors in, and what discount rate and year does NemoMod use?
8. **`entc:technical_cost:electricity:transmission`** has a positive multiplier (+740,000 $/PJ), so more electricity production shows as a *benefit*. Sign error?
