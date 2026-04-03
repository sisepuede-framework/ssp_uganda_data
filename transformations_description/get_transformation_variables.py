"""
get_transformation_variables.py
-------------------------------
Maps each transformation (TX:…) to BOTH:

  1) Input variables  — the fields the transformation directly modifies
  2) Output variables — the model outputs that change when the sector models
                        (AFOLU, Circular Economy, IPPU, non-electric Energy)
                        process the modified inputs

The approach is empirical: run each transformation, feed it through the
SISEPUEDE models, and compare against the baseline to detect changes.

Outputs
-------
  transformation_variable_map.csv        — input variable mapping
  transformation_output_variable_map.csv — output variable mapping

Usage
-----
  cd ssp_modeling/transformations_description
  python get_transformation_variables.py
"""

import os
import sys
import pathlib
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Paths (mirror the notebook layout) ──────────────────────────────────────
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SSP_MODELING_DIR = SCRIPT_DIR.parent
NOTEBOOKS_DIR = SSP_MODELING_DIR / "notebooks"
DATA_DIR = SSP_MODELING_DIR / "input_data"
TRANSFORMATIONS_DIR = SSP_MODELING_DIR / "transformations"
CONFIG_DIR = NOTEBOOKS_DIR / "config_files"

sys.path.insert(0, str(NOTEBOOKS_DIR))

# ── SISEPUEDE imports ───────────────────────────────────────────────────────
from sisepuede.manager.sisepuede_examples import SISEPUEDEExamples
from sisepuede.manager.sisepuede_file_structure import SISEPUEDEFileStructure
from sisepuede.manager.sisepuede_models import SISEPUEDEModels
import sisepuede.core.attribute_table as att
import sisepuede.transformers as trf

from ssp_transformations_handler.GeneralUtils import GeneralUtils

# ── Load config ─────────────────────────────────────────────────────────────
g_utils = GeneralUtils()
config_params = g_utils.read_yaml(str(CONFIG_DIR / "config.yaml"))

country_name = config_params["country_name"]
ssp_input_file_name = config_params["ssp_input_file_name"]
sim_end_year = config_params.get("sim_end_year", 2050)

print(f"Country: {country_name}")
print(f"Input file: {ssp_input_file_name}")
print(f"Simulation end year: {sim_end_year}")

# ── File structure and attribute table ──────────────────────────────────────
file_struct = SISEPUEDEFileStructure(initialize_directories=False)
matt = file_struct.model_attributes

key_tp = matt.dim_time_period
key_yr = matt.field_dim_year
years = np.arange(2015, sim_end_year + 1).astype(int)

attr_time_period = att.AttributeTable(
    pd.DataFrame({key_tp: range(len(years)), key_yr: years}),
    key_tp,
)
matt.update_dimensional_attribute_table(attr_time_period)

# ── Build input DataFrame ──────────────────────────────────────────────────
examples = SISEPUEDEExamples()
df_example = examples("input_data_frame")
df_raw = pd.read_csv(DATA_DIR / ssp_input_file_name)

if "time_period" not in df_raw.columns and "period" in df_raw.columns:
    df_raw = df_raw.rename(columns={"period": "time_period"})

df_input = g_utils.add_missing_cols(df_example, df_raw.copy())
df_input["region"] = country_name
df_input = df_input[df_input["year"] <= sim_end_year]

print(f"Input shape: {df_input.shape}")

# ── Initialize Transformers ────────────────────────────────────────────────
print("\nInitializing Transformers …")
t0 = time.time()
transformers = trf.transformers.Transformers(
    {},
    attr_time_period=attr_time_period,
    df_input=df_input,
)
print(f"  done in {time.time() - t0:.1f}s")

# ── Initialize Transformations ─────────────────────────────────────────────
print("Loading Transformations from YAML directory …")
t0 = time.time()
transformations = trf.Transformations(
    TRANSFORMATIONS_DIR,
    transformers=transformers,
)
print(f"  done in {time.time() - t0:.1f}s")
print(f"  {len(transformations.all_transformation_codes)} transformation codes found")

# ── Initialize SISEPUEDEModels ──────────────────────────────────────────────
# Non-electricity models (fast) for all transformations
print("\nInitializing SISEPUEDEModels (no electricity) …")
t0 = time.time()
models_no_elec = SISEPUEDEModels(
    matt,
    allow_electricity_run=False,
    initialize_julia=False,
)
MODELS_TO_RUN = ["AFOLU", "Circular Economy", "IPPU", "Energy"]
print(f"  done in {time.time() - t0:.1f}s")

# Electricity-enabled models (slow) — only for ENTC/FGTV transformations
ELEC_SECTORS = {"ENTC", "FGTV"}
print("Initializing SISEPUEDEModels WITH electricity (Julia) …")
t0 = time.time()
models_elec = SISEPUEDEModels(
    matt,
    allow_electricity_run=True,
    fp_julia=str(file_struct.dir_jl),
    fp_nemomod_reference_files=str(file_struct.dir_ref_nemo),
    initialize_julia=True,
)
print(f"  done in {time.time() - t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════
# PART 1 — INPUT variable mapping
# ═══════════════════════════════════════════════════════════════════════════

ERROR_THRESH = 1e-3

print("\n" + "=" * 70)
print("PART 1: Input variable mapping")
print("=" * 70)
t0 = time.time()

baseline_tx = transformations.get_transformation(transformations.code_baseline)
df_base_inputs = baseline_tx()

fields_compare = transformers.model_attributes.all_variable_fields_input
field_to_var = transformers.model_attributes.dict_variable_fields_to_model_variables

rows_input = []
codes = [c for c in transformations.all_transformation_codes
         if c != transformations.code_baseline]

transformed_inputs = {}

for i, code in enumerate(codes, 1):
    tx = transformations.get_transformation(code)
    if tx is None:
        continue

    try:
        df_cur = tx()
    except Exception as exc:
        print(f"  [{i}/{len(codes)}] {code} — FAILED: {exc}")
        continue

    transformed_inputs[code] = df_cur

    vec_dist = (
        np.abs(
            1 - np.nan_to_num(
                df_cur[fields_compare].values / df_base_inputs[fields_compare].values,
                nan=1.0,
                posinf=0.0,
            )
        )
        .max(axis=0)
    )

    w = np.where(vec_dist >= ERROR_THRESH)[0]
    if len(w) == 0:
        continue

    for j in w:
        fld = fields_compare[j]
        rows_input.append({
            "transformation_code": code,
            "variable": field_to_var.get(fld, fld),
            "variable_field": fld,
        })

elapsed = time.time() - t0
df_input_map = pd.DataFrame(rows_input)
print(f"  {df_input_map.shape[0]} input-variable mappings in {elapsed:.1f}s")

out_input = SCRIPT_DIR / "transformation_variable_map.csv"
df_input_map.to_csv(out_input, index=False)
print(f"  Saved → {out_input}")


# ═══════════════════════════════════════════════════════════════════════════
# PART 2 — OUTPUT variable mapping (run sector models)
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 2: Output variable mapping (running sector models)")
print("=" * 70)

# ── Helper to detect changed output columns ────────────────────────────────
def detect_changed_outputs(df_tx_out, df_base_out, code, field_to_var, thresh):
    common = [c for c in df_base_out.columns
              if c in df_tx_out.columns and c not in ("time_period", "region")]
    dist = (
        np.abs(
            1 - np.nan_to_num(
                df_tx_out[common].values / df_base_out[common].values,
                nan=1.0, posinf=0.0,
            )
        ).max(axis=0)
    )
    hits = []
    for j in np.where(dist >= thresh)[0]:
        fld = common[j]
        hits.append({
            "transformation_code": code,
            "variable": field_to_var.get(fld, fld),
            "variable_field": fld,
        })
    return hits

# ── 2a: Non-electricity baseline ───────────────────────────────────────────
print("\n  Running baseline (no electricity) …", end=" ", flush=True)
t0 = time.time()
df_base_output_no_elec = models_no_elec.project(
    df_base_inputs,
    models_run=MODELS_TO_RUN,
    include_electricity_in_energy=False,
    check_results=False,
)
print(f"done in {time.time() - t0:.1f}s  ({df_base_output_no_elec.shape[1]} cols)")

# Split transformations: ENTC/FGTV need electricity, others don't
codes_elec = [c for c in transformed_inputs
              if any(f":{s}:" in c for s in ELEC_SECTORS)]
codes_no_elec = [c for c in transformed_inputs if c not in codes_elec]

print(f"\n  Non-electricity transformations: {len(codes_no_elec)}")
print(f"  Electricity transformations (ENTC/FGTV): {len(codes_elec)}")

# ── 2b: Run non-electricity transformations ─────────────────────────────────
rows_output = []
print(f"\n  Running {len(codes_no_elec)} non-electricity transformations …")
t0_all = time.time()
for i, code in enumerate(codes_no_elec, 1):
    try:
        df_tx_out = models_no_elec.project(
            transformed_inputs[code],
            models_run=MODELS_TO_RUN,
            include_electricity_in_energy=False,
            check_results=False,
        )
    except Exception as exc:
        print(f"    [{i}/{len(codes_no_elec)}] {code} — FAILED: {exc}")
        continue

    rows_output.extend(
        detect_changed_outputs(df_tx_out, df_base_output_no_elec, code,
                               field_to_var, ERROR_THRESH)
    )

    if i % 20 == 0 or i == len(codes_no_elec):
        print(f"    [{i}/{len(codes_no_elec)}] progress …")

print(f"  Non-electricity done in {time.time() - t0_all:.1f}s")

# ── 2c: Run ENTC/FGTV transformations WITH electricity ──────────────────────
print(f"\n  Running baseline WITH electricity …", end=" ", flush=True)
t0 = time.time()
df_base_output_elec = models_elec.project(
    df_base_inputs,
    models_run=MODELS_TO_RUN,
    include_electricity_in_energy=True,
    check_results=False,
)
print(f"done in {time.time() - t0:.1f}s  ({df_base_output_elec.shape[1]} cols)")

print(f"\n  Running {len(codes_elec)} ENTC/FGTV transformations with electricity …")
t0_all = time.time()
for i, code in enumerate(codes_elec, 1):
    print(f"    [{i}/{len(codes_elec)}] {code} …", end=" ", flush=True)
    t0 = time.time()
    try:
        df_tx_out = models_elec.project(
            transformed_inputs[code],
            models_run=MODELS_TO_RUN,
            include_electricity_in_energy=True,
            check_results=False,
        )
    except Exception as exc:
        print(f"FAILED: {exc}")
        continue

    hits = detect_changed_outputs(df_tx_out, df_base_output_elec, code,
                                  field_to_var, ERROR_THRESH)
    rows_output.extend(hits)
    print(f"done in {time.time() - t0:.1f}s — {len(hits)} fields changed")

print(f"  Electricity runs done in {time.time() - t0_all:.1f}s")

df_output_map = pd.DataFrame(rows_output)
print(f"\n  Total: {df_output_map.shape[0]} output-variable mappings")

out_output = SCRIPT_DIR / "transformation_output_variable_map.csv"
df_output_map.to_csv(out_output, index=False)
print(f"  Saved → {out_output}")

# ── Summary ─────────────────────────────────────────────────────────────────
n_tx_input  = df_input_map["transformation_code"].nunique() if len(df_input_map) else 0
n_tx_output = df_output_map["transformation_code"].nunique() if len(df_output_map) else 0
print(f"\n{'=' * 70}")
print(f"Summary")
print(f"  Input mapping:  {df_input_map.shape[0]} rows across {n_tx_input} transformations")
print(f"  Output mapping: {df_output_map.shape[0]} rows across {n_tx_output} transformations")
print(f"{'=' * 70}")
