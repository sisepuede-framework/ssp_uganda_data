# Ablation: the z-score outlier filter on training targets

Run `2026-05-30t21;35;56.244639`. One split on the full frame (seed 42, test_size 0.2): 79,672 training rows, **19,919 untruncated test rows unseen by both arms**. The control drops 19,076 of its training rows to the filter (23.9%); the treatment keeps all of them. Nothing else differs.


## Accuracy on the common test set (2035-2070)

| Family | n | median R2 filtered | median R2 no-filter | median SMAPE filtered | median SMAPE no-filter |
|---|---|---|---|---|---|
| Emissions | 115 | 0.9928 | 0.9933 | 1.41 | 1.40 |
| Benefits | 80 | 0.9958 | 0.9962 | 1.85 | 1.82 |
| Costs | 15 | 0.9891 | 0.9899 | 3.55 | 3.53 |
| GDP | 5 | 1.0000 | 1.0000 | 0.05 | 0.05 |

- **filtered**: median R2 0.9931, mean 0.9533, min -0.0018, median SMAPE 1.58%, 15 targets below R2 0.8

- **nofilter**: median R2 0.9938, mean 0.9488, min -0.6795, median SMAPE 1.52%, 15 targets below R2 0.8

## Reachable ceiling: total 2070 emissions at the corners of the input space

| Corner | filtered | no-filter | change |
|---|---|---|---|
| L=0.0, X=0.5 | 219.1 | 220.0 | +0.9 |
| L=0.0, X=1.0 | 243.3 | 250.7 | +7.4 |
| L=1.0, X=0.5 | 3.7 | 1.7 | -2.0 |
| L=1.0, X=1.0 | 25.8 | -18.0 | -43.8 |

The official BAU run reaches **286.8 Mt** at 2070. Maximum-emission corner: filtered 243.3 Mt (-15.2% vs official), no-filter 250.7 Mt (-12.6%).


## Targets most changed by lifting the filter

| Target | R2 filtered | R2 no-filter | delta |
|---|---|---|---|
| `emission_other_land_use_conversion_yr2070` | 0.5760 | 0.6789 | +0.1029 |
| `emission_other_land_use_conversion_yr2060` | 0.7097 | 0.7473 | +0.0376 |
| `emission_other_not_estimated_conversion_yr2040` | 0.6843 | 0.6996 | +0.0153 |
| `benefit_land_pollution_yr2035` | 0.9720 | 0.9808 | +0.0088 |
| `emission_other_land_use_conversion_yr2040` | 0.8978 | 0.9056 | +0.0077 |
| `emission_other_land_use_conversion_yr2050` | 0.8852 | 0.8903 | +0.0051 |
| `benefit_ecosystem_services_wetlands_yr2040` | -0.0018 | -0.6795 | -0.6777 |
| `emission_fuel_production_yr2035` | 0.0972 | -0.0064 | -0.1035 |
| `benefit_ecosystem_services_wetlands_yr2050` | 0.4598 | 0.3709 | -0.0888 |
| `emission_fuel_production_yr2040` | 0.4746 | 0.4143 | -0.0603 |
