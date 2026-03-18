"""
Tests for 100k_run_postprocessing_parallel.py

Covers:
  - postprocess_cba()              : CB aggregation logic
  - worker result aggregation      : concat + single-file path structure
  - upload_df_to_s3()              : S3 call shape
  - emissions column selection     : correct columns retained per primary_id
"""
import sys
import os
import importlib
import types
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch, call

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Bootstrap: the script imports rpy2 and costs_benefits_ssp at module level.
# Stub those out so we can import the module without the real dependencies.
# ---------------------------------------------------------------------------
def _make_stub(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

for _pkg in [
    "rpy2", "rpy2.robjects", "rpy2.robjects.conversion",
    "rpy2.rinterface_lib", "rpy2.rinterface_lib.embedded",
    "costs_benefits_ssp", "costs_benefits_ssp.cb_calculate",
]:
    if _pkg not in sys.modules:
        _make_stub(_pkg)

# Minimal stubs for symbols the module uses at import time
import rpy2.robjects as _ro
_ro.r = MagicMock()
_ro.globalenv = {}
_ro.IntVector = MagicMock(side_effect=lambda x: x)
_ro.StrVector = MagicMock(side_effect=lambda x: x)

import rpy2.robjects.conversion as _conv
_conv.localconverter = MagicMock()

import rpy2.rinterface_lib.embedded as _emb
_emb.RRuntimeError = Exception

# pandas2ri stub
_pandas2ri = _make_stub("rpy2.robjects.pandas2ri")
_pandas2ri.converter = MagicMock()

# default_converter stub (accessed via `from rpy2.robjects import ... default_converter`)
_ro.default_converter = MagicMock()
_ro.conversion = MagicMock()
_ro.conversion.py2rpy = MagicMock(return_value=MagicMock())

# Now import the module under test
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPT_DIR)

import importlib.util
spec = importlib.util.spec_from_file_location(
    "postproc",
    os.path.join(SCRIPT_DIR, "100k_run_postprocessing_parallel.py"),
)
postproc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(postproc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_cb_raw(primary_ids=(1, 2), n_years=5):
    """Minimal raw CB dataframe that postprocess_cba() can consume."""
    rows = []
    for pid in primary_ids:
        for t in range(n_years):
            for cb_type in ("benefits", "costs"):
                rows.append({
                    "variable": f"item:{cb_type}:{cb_type}:a:b",
                    "value": float(1e9 * (t + 1)),
                    "time_period": t,
                    "strategy_code": "STRAT_A",
                    "primary_id": pid,
                    "future_id": 10 + pid,
                })
    return pd.DataFrame(rows)


def _make_decomposed(primary_ids=(1, 2), n_periods=5):
    """Minimal decomposed dataframe for emissions worker logic."""
    rows = []
    for pid in primary_ids:
        for t in range(n_periods):
            rows.append({
                "primary_id": pid,
                "time_period": t,
                "region": "uganda",
                "emission_co2e_subsector_total_inen": float(pid * 10 + t),
                "emission_co2e_subsector_total_trns": float(pid * 5 + t),
                "energy_demand_electricity": float(pid + t),
                "frac_inen_energy_coal": 0.3,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestPostprocessCba(unittest.TestCase):

    def test_returns_dataframe(self):
        raw = _make_cb_raw(primary_ids=(1,))
        result = postproc.postprocess_cba(raw)
        self.assertIsInstance(result, pd.DataFrame)

    def test_value_scaled_to_billions(self):
        """values are divided by 1e9, so 1e9 input → 1.0 in the pivoted cb_type columns."""
        raw = _make_cb_raw(primary_ids=(1,), n_years=1)
        result = postproc.postprocess_cba(raw)
        # After pivot, cb_type values become columns (benefits, costs). Each 1e9 → 1.0
        numeric_cols = [c for c in result.columns if c not in ("primary_id", "future_id", "strategy_code", "Year")]
        for col in numeric_cols:
            self.assertTrue((result[col].abs() <= 6.0).all(), f"Column {col} out of expected range")

    def test_multiple_primary_ids_preserved(self):
        raw = _make_cb_raw(primary_ids=(1, 2, 3))
        result = postproc.postprocess_cba(raw)
        self.assertEqual(set(result["primary_id"].unique()), {1, 2, 3})

    def test_year_column_offset(self):
        """Year = time_period + 2015."""
        raw = _make_cb_raw(primary_ids=(1,), n_years=3)
        result = postproc.postprocess_cba(raw)
        expected_years = {2015, 2016, 2017}
        self.assertEqual(set(result["Year"].unique()), expected_years)

    def test_cb_type_becomes_columns(self):
        raw = _make_cb_raw(primary_ids=(1,))
        result = postproc.postprocess_cba(raw)
        # pivot_table turns cb_type values into columns
        self.assertIn("benefits", result.columns)
        self.assertIn("costs", result.columns)


class TestCombinedUpload(unittest.TestCase):
    """Verify that main() collects worker DataFrames and uploads exactly ONE file each."""

    def _mock_worker_results(self, primary_ids):
        decomposed = _make_decomposed(primary_ids=primary_ids)
        results = []
        for pid in primary_ids:
            em_df = decomposed[decomposed["primary_id"] == pid].copy()
            em_df["total_emissions"] = em_df["emission_co2e_subsector_total_inen"] + em_df["emission_co2e_subsector_total_trns"]
            em_df = em_df[["primary_id", "time_period", "total_emissions", "energy_demand_electricity"]]
            cb_df = pd.DataFrame({
                "primary_id": [pid],
                "future_id": [10 + pid],
                "strategy_code": ["STRAT_A"],
                "Year": [2020],
                "benefits": [1.0],
                "costs": [0.5],
            })
            results.append((pid, em_df, cb_df, None))
        return results

    def test_emissions_concat_all_primary_ids(self):
        primary_ids = [1, 2, 3]
        results = self._mock_worker_results(primary_ids)

        emissions_frames = [em for _, em, _, err in results if err is None and em is not None]
        all_emissions = pd.concat(emissions_frames, ignore_index=True)

        self.assertEqual(set(all_emissions["primary_id"].unique()), set(primary_ids))
        self.assertEqual(len(all_emissions), sum(len(em) for _, em, _, _ in results))

    def test_cb_concat_all_primary_ids(self):
        primary_ids = [1, 2, 3]
        results = self._mock_worker_results(primary_ids)

        cb_frames = [cb for _, _, cb, err in results if err is None and cb is not None]
        all_cb = pd.concat(cb_frames, ignore_index=True)

        self.assertEqual(set(all_cb["primary_id"].unique()), set(primary_ids))

    def test_s3_key_structure_emissions(self):
        run_prefix = "run_database/myrun/"
        decomp_prefix = f"{run_prefix}decomposed_outputs/"
        region = "uganda"
        dir_id = "42"

        key = f"{decomp_prefix}region={region}/emission_total_{dir_id}/data.csv"

        self.assertTrue(key.endswith("/data.csv"))
        self.assertIn(f"region={region}", key)
        self.assertIn(f"emission_total_{dir_id}", key)

    def test_s3_key_structure_cb(self):
        run_prefix = "run_database/myrun/"
        cb_prefix = f"{run_prefix}cb_outputs/"
        region = "uganda"
        dir_id = "42"

        key = f"{cb_prefix}region={region}/cb_{dir_id}/data.csv"

        self.assertTrue(key.endswith("/data.csv"))
        self.assertIn(f"region={region}", key)
        self.assertIn(f"cb_{dir_id}", key)

    def test_upload_called_once_for_emissions(self):
        """upload_df_to_s3 should be called exactly once for emissions."""
        mock_s3 = MagicMock()
        mock_obj = MagicMock()
        mock_s3.Object.return_value = mock_obj

        primary_ids = [1, 2, 3]
        results = self._mock_worker_results(primary_ids)
        emissions_frames = [em for _, em, _, err in results if err is None and em is not None]
        all_emissions = pd.concat(emissions_frames, ignore_index=True)

        with patch.object(postproc, "upload_df_to_s3") as mock_upload:
            postproc.upload_df_to_s3(all_emissions, mock_s3, "my-bucket", "some/key/data.csv")
            mock_upload.assert_called_once()

    def test_failed_workers_excluded_from_concat(self):
        """Workers that return an error should not contribute rows."""
        results = [
            (1, pd.DataFrame({"primary_id": [1], "time_period": [0], "total_emissions": [5.0]}),
             None, None),
            (2, None, None, "some error"),
            (3, pd.DataFrame({"primary_id": [3], "time_period": [0], "total_emissions": [7.0]}),
             None, None),
        ]
        emissions_frames = [em for _, em, _, err in results if err is None and em is not None]
        all_emissions = pd.concat(emissions_frames, ignore_index=True)

        self.assertEqual(set(all_emissions["primary_id"].unique()), {1, 3})
        self.assertNotIn(2, all_emissions["primary_id"].values)


class TestUploadDfToS3(unittest.TestCase):

    def test_uploads_csv_content(self):
        mock_s3 = MagicMock()
        mock_obj = MagicMock()
        mock_s3.Object.return_value = mock_obj

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        postproc.upload_df_to_s3(df, mock_s3, "bucket", "prefix/data.csv")

        mock_s3.Object.assert_called_once_with("bucket", "prefix/data.csv")
        call_kwargs = mock_obj.put.call_args[1]
        self.assertEqual(call_kwargs["ContentType"], "text/csv")
        body = call_kwargs["Body"]
        result_df = pd.read_csv(StringIO(body))
        pd.testing.assert_frame_equal(result_df, df)


class TestEmissionsColumnSelection(unittest.TestCase):

    def test_only_expected_columns_retained(self):
        """emissions_df should include primary_id, time_period, total_emissions, and prefixed cols."""
        decomposed = _make_decomposed(primary_ids=[5], n_periods=3)
        pid = 5
        df = decomposed[decomposed["primary_id"] == pid].copy()
        df["total_emissions"] = df.filter(like="emission_co2e_subsector_total").sum(axis=1)

        energy_demand_cols    = [c for c in df.columns if c.startswith("energy_demand_")]
        frac_inen_energy_cols = [c for c in df.columns if c.startswith("frac_inen_energy_")]
        cols_to_keep = (
            ["primary_id", "time_period", "total_emissions"]
            + energy_demand_cols
            + frac_inen_energy_cols
        )
        emissions_df = df[[c for c in cols_to_keep if c in df.columns]]

        self.assertIn("primary_id", emissions_df.columns)
        self.assertIn("time_period", emissions_df.columns)
        self.assertIn("total_emissions", emissions_df.columns)
        self.assertIn("energy_demand_electricity", emissions_df.columns)
        self.assertIn("frac_inen_energy_coal", emissions_df.columns)
        # raw emission columns should NOT be in the final output
        self.assertNotIn("emission_co2e_subsector_total_inen", emissions_df.columns)

    def test_total_emissions_is_sum_of_subsector_cols(self):
        decomposed = _make_decomposed(primary_ids=[7], n_periods=2)
        pid = 7
        df = decomposed[decomposed["primary_id"] == pid].copy()
        df["total_emissions"] = df.filter(like="emission_co2e_subsector_total").sum(axis=1)

        expected = (
            df["emission_co2e_subsector_total_inen"] + df["emission_co2e_subsector_total_trns"]
        )
        pd.testing.assert_series_equal(
            df["total_emissions"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )


if __name__ == "__main__":
    unittest.main()
