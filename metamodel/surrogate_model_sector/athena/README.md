# Athena training-data pipeline

Build the XGBoost surrogate's training set **directly from a SISEPUEDE run in S3**,
using **Athena** for the heavy lifting and a thin pandas layer for reshaping.

This replaces the old flow (download a 3.8 GB IDE CSV + per-batch `model_output`
CSVs and pivot locally), which does not scale to the 100,000-scenario runs and
depended on an IDE CSV that newer runs no longer produce.

Everything is parameterized by `run_id` + `region`, so the same code works for any
run or country.

---

## 1. What it produces

A parquet at `metamodel/data/training/training_data_sector_<run>.parquet` (and a
shared copy at `s3://sisepuede-data/queries/<run>/training_data_for_surrogate.parquet`)
with:

| Block | Count | Columns |
|---|---|---|
| Emissions, by inventory category × year | 138 | `emission_<category>_yr<year>` (23 official categories × 6 years) |
| Benefits | 96 | `benefit_<type>_yr<year>` (16 types × 6 years, positive) |
| Costs | 18 | `cost_<type>_yr<year>` (3 types × 6 years, **negative — already signed**) |
| GDP | 6 | `gdp_mmm_usd_yr<year>` |
| **Targets total** | **258** | |

> **Sector categories come from the team's official inventory crosswalk**
> (`config/crosswalk_inventory_to_sisepuede_20260510.csv`), which re-aggregates the
> ~620 granular `emission_co2e_*` fields into 23 named categories (e.g. "Forest Land -
> Removals", "Electricity and Heat Generation"). `athena/gen_emissions_sql.py`
> **generates** `emissions_and_gdp.sql` + `config/sector_categories.json` from it — do
> not hand-edit the SQL; re-run the generator if the crosswalk changes.
| Features | varies | `group_*` (the X exogenous uncertainties + L lever effects) |

Target years: **2025, 2035, 2040, 2050, 2060, 2070** (SISEPUEDE `time_period` 10/20/25/35/45/55,
since `year = time_period + 2015`). `retrain_sector.py` splits features vs targets by
the `group_` prefix, so no downstream code hardcodes the target count.

---

## 2. How it works (architecture)

```
                       S3 (run_database/<run>/)
                       ├── decomposed_emissions/region=uganda/...  (FINAL emissions)
                       ├── model_output/region=uganda/...   (gdp inputs)
                       └── cb/region=uganda/...              (cost/benefit)
                                   │
            ┌──────────────────────┴───────────── Athena (server-side) ─────────┐
            │  emissions_and_gdp.sql          cost_benefit.sql                   │
            │  (23 inventory categories       (19 cost/benefit fields)           │
            │   summed from granular fields                                      │
            │   in decomposed_emissions,                                         │
            │   JOIN model_output for gdp)                                       │
            └──────────────────────┬─────────────────────────────────────────── ┘
                                   │  result CSVs -> s3://.../queries/<run>/
                                   ▼
   transfers/<run>/ (LHC X/L,      assemble_training_data.py  (thin pandas)
   ATTRIBUTE_PRIMARY, …)  ───────► pivot to per-year columns, split cost/benefit,
        │  features.py             merge features ⨝ emissions ⨝ cost_benefit on primary_id
        └───────────────────────►  ▼
                                   training_data_sector_<run>.parquet
```

**Why `decomposed_emissions` for emissions, `model_output` for GDP:** the emissions in
`model_output` are *pre*-post-processing. The **final** emissions are produced by a
post-processing step and land in `decomposed_emissions`, which carries both the 15
`emission_co2e_subsector_total_<sector>` columns **and** the ~620 granular
`emission_co2e_*` fields. We sum the granular fields into the 23 official inventory
categories (per the crosswalk) rather than using the raw subsector totals — the raw
codes don't line up with the official pathways (e.g. Uganda's ~62 Mt biomass energy is
"Forest Land - Removals", not "Electricity"). GDP is **not** in `decomposed_emissions`,
so we still derive it from `model_output`'s per-capita GDP × population. The single
`emissions_and_gdp.sql` therefore **joins** the two on `primary_id`+`time_period`
(server-side); the pandas reshaping is unchanged (it's prefix-driven).

**Why features in pandas, not Athena:** the LHC files live as single CSVs per prefix
in `transfers/` (awkward to register as partitioned tables), and the final step is a
column *rename* (each trajectory group → `group_<id>_<common-prefix>`) that is pure
pandas anyway.

---

## 3. Prerequisites

- **Conda env** `uganda_metamodel_env` (has boto3, pandas, pyarrow, yaml):
  `/opt/miniconda3/envs/uganda_metamodel_env/bin/python`
- **AWS access** via a profile in `~/.aws/credentials` with permissions for Athena
  (`StartQueryExecution`, `GetQueryExecution`), Glue (create db/table, get partitions),
  and S3 read on the run + write on `s3://sisepuede-data/queries/`.
- **`config/aws_config.yaml`** (git-ignored) — copy the example and set your profile:
  ```bash
  cp config/aws_config.yaml.example config/aws_config.yaml
  # edit profile_name / region_name
  ```

---

## 4. Configuration

`config/ml_training_workflow_config.yaml` (in git):
```yaml
run_id: "2026-05-30t21;35;56.244639"   # the SISEPUEDE run to process
region: uganda                          # S3 Hive partition
bucket_name: sisepuede-data
```
`config/aws_config.yaml` (git-ignored): `profile_name`, `region_name`.

From these, `config.py` derives the per-run Glue database name
(`sisepuede_run_<run>` sanitized to `[a-z0-9_]`), the S3 table locations, and the
query-output prefix. **Nothing else needs editing to switch runs/countries.**

---

## 5. Running it

```bash
cd metamodel/surrogate_model_sector/athena
PY=/opt/miniconda3/envs/uganda_metamodel_env/bin/python

# Step 1 — DRY RUN: print the DDL + queries, write NOTHING to AWS. Review the DDL.
$PY run_extracts.py

# Step 2 — register the tables (writes to the Glue catalog) AND run the queries:
$PY run_extracts.py --apply-ddl
#   (later, if the tables already exist, use --skip-ddl to just re-run the queries)

# Step 3 — assemble the parquet (also uploads the shared copy to S3):
$PY assemble_training_data.py
```

Then retrain (see the repo `CLAUDE.md` for the full sequence):
```bash
cd ..
$PY retrain_sector.py
```

### The safety gate
`run_extracts.py` **never writes to AWS without `--apply-ddl`**. By default it only
reads CSV headers from S3 and prints the DDL it *would* run, so you can review the
generated `CREATE EXTERNAL TABLE` statements before any Glue catalog object is created.

---

## 6. The two queries

- **`queries/emissions_and_gdp.sql`** — *generated* by `gen_emissions_sql.py`; sums the
  granular `emission_co2e_*` fields in `decomposed_emissions` into the 23 official
  inventory categories (`emission_co2e_category_*`), **joined** to `model_output` on
  `primary_id`+`time_period` for `gdp_mmm_usd`, derived as
  `gdp_per_capita_usd * population_gnrl_total / 1e9` (there is no direct GDP column, and
  GDP is not in `decomposed_emissions`). Filtered to the 6 target `time_period`s.
- **`queries/cost_benefit.sql`** — from `cb`: the 17 original + 2 new
  (`ecosystem_services_grasslands/_wetlands`) cost/benefit fields, same year filter.

Both use `WHERE region = '{region}'`; `{region}` is filled from config. `region` is a
Hive partition, so the filter also **prunes the scan** to that region's files.

---

## 7. Cost

Athena bills **$5/TB scanned**. CSV tables are **full-scan** (no columnar pruning),
so each query reads the whole table even though we only keep a few columns. The
`emissions_and_gdp.sql` JOIN now scans **both** `decomposed_emissions` (the final
emissions) **and** `model_output` (still full-scanned for the GDP inputs), so the
per-build cost is higher than the old single-table query — roughly the sum of both
tables' sizes (`model_output` ≈ **103 GB** for the Uganda 100k run, plus
`decomposed_emissions`, which is wide). `run_extracts.py` prints the bytes scanned + a
`$` estimate per query, so there are no surprises.

This is a **one-time** cost: the result CSVs are cached locally, so you only pay it
again if you rebuild. If you expect to re-run repeatedly (or for many countries),
convert `model_output` to Parquet once with `CREATE TABLE ... AS SELECT` — Parquet is
columnar, so subsequent reads scan only the ~16 columns we need (megabytes, ~free).
The CTAS itself scans the 103 GB once, so it only pays off across multiple rebuilds.

---

## 8. Adapting to another run or country

1. Set `run_id` (and `region`, if not `uganda`) in `ml_training_workflow_config.yaml`.
2. `python run_extracts.py` (review DDL) → `--apply-ddl` → `assemble_training_data.py`.

Each run gets its own Glue database (`sisepuede_run_<run>`), so runs never clobber each
other. The DDL is generated from the live CSV header, so it adapts automatically if a
run adds/removes columns. The SQL is versioned here in git (it is **not** uploaded to S3).

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `Missing config/aws_config.yaml` | `cp config/aws_config.yaml.example config/aws_config.yaml` and set your profile. |
| Query `FAILED` | Open the Athena console → Query history → click the failed query for the error. |
| Query returns 0 rows | Partitions not indexed — `--apply-ddl` runs `MSCK REPAIR TABLE`; confirm it ran, and that `region` matches the S3 `region=<x>/` folder. |
| `NaNs in target columns` (assemble) | A `primary_id` is missing from one source — check that all three sources (emissions, cb, features) cover the same scenarios. |
| GDP looks wrong | Sanity-check: Uganda GDP should be tens of `mmm_usd` (billions). The derivation assumes `population_gnrl_total` is in persons. |

---

## 10. Files

| File | Role |
|---|---|
| `config.py` | Loads both YAMLs; derives all names/paths (single source of truth). |
| `athena_client.py` | Thin boto3 wrappers: run/poll query, download result, sniff S3 headers. |
| `ddl.py` | Generates `CREATE EXTERNAL TABLE` / `MSCK REPAIR` from a CSV header. |
| `features.py` | Downloads LHC X/L + builds the `group_*` features (ports the notebook logic). |
| `run_extracts.py` | Orchestrator: DDL gate → register tables (`model_output`, `cb`, `decomposed_emissions`) → run queries → download. |
| `assemble_training_data.py` | Reshape + merge → training parquet (+ upload shared copy). |
| `queries/*.sql` | The two Athena queries (versioned here, not in S3). |
