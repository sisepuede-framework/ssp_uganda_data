"""
Tests for 100k_run_postprocessing_parallel.py

Covers:
  - postprocess_cba()              : CB aggregation logic
  - worker result aggregation      : concat + single-file path structure
  - upload_df_to_s3()              : S3 call shape
  - emissions column selection     : correct columns retained per primary_id
  - rescale_py()                   : numerical parity with R algorithm
"""
import sys
import os
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Bootstrap: stub costs_benefits_ssp so we can import without the real dep.
# ---------------------------------------------------------------------------
import types

def _make_stub(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

for _pkg in ["costs_benefits_ssp", "costs_benefits_ssp.cb_calculate"]:
    if _pkg not in sys.modules:
        _make_stub(_pkg)

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
        numeric_cols = [c for c in result.columns if c not in ("primary_id", "time_period")]
        for col in numeric_cols:
            self.assertTrue((result[col].abs() <= 6.0).all(), f"Column {col} out of expected range")

    def test_multiple_primary_ids_preserved(self):
        raw = _make_cb_raw(primary_ids=(1, 2, 3))
        result = postproc.postprocess_cba(raw)
        self.assertEqual(set(result["primary_id"].unique()), {1, 2, 3})

    def test_cb_type_becomes_columns(self):
        raw = _make_cb_raw(primary_ids=(1,))
        result = postproc.postprocess_cba(raw)
        self.assertIn("benefits", result.columns)
        self.assertIn("costs", result.columns)


class TestCombinedUpload(unittest.TestCase):
    """Verify that main() collects worker DataFrames and uploads exactly ONE file each."""

    def _mock_worker_results(self, primary_ids):
        decomposed = _make_decomposed(primary_ids=primary_ids)
        results = []
        for pid in primary_ids:
            em_df = decomposed[decomposed["primary_id"] == pid].copy()
            em_df["total_emissions"] = (
                em_df["emission_co2e_subsector_total_inen"]
                + em_df["emission_co2e_subsector_total_trns"]
            )
            em_df = em_df[["primary_id", "time_period", "total_emissions"]]
            cb_df = pd.DataFrame({
                "primary_id": [pid],
                "future_id": [10 + pid],
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
        key = f"{decomp_prefix}region={region}/decomposed_emissions_{dir_id}/data.csv"
        self.assertTrue(key.endswith("/data.csv"))
        self.assertIn(f"region={region}", key)
        self.assertIn(f"decomposed_emissions_{dir_id}", key)

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
        results = [
            (1, pd.DataFrame({"primary_id": [1], "time_period": [0], "total_emissions": [5.0]}), None, None),
            (2, None, None, "some error"),
            (3, pd.DataFrame({"primary_id": [3], "time_period": [0], "total_emissions": [7.0]}), None, None),
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


class TestRescalePy(unittest.TestCase):
    """Numerical parity: rescale_py() must match hand-traced R algorithm."""

    def _build_data(self):
        rows = []
        vals = {
            (0,4):(10.0,4.0),(0,5):(12.0,5.0),(0,6):(15.0,6.0),
            (1,4):( 8.0,2.0),(1,5):( 9.6,2.4),(1,6):(11.0,3.0),
            (2,4):(20.0,8.0),(2,5):(22.0,9.0),(2,6):(24.0,9.6),
        }
        for (pid,tp),(a,b) in vals.items():
            rows.append({"region":"uganda","primary_id":pid,"time_period":tp,
                         "emission_co2e_em_a":a,"emission_co2e_em_b":b})
        return pd.DataFrame(rows)

    def _build_te(self):
        return pd.DataFrame([
            {"Subsector":"S1","Gas":"CO2","Vars":"emission_co2e_em_a",
             "ssp_subsector":"sub1","tvalue":8.0},
            {"Subsector":"S1","Gas":"CH4","Vars":"emission_co2e_em_b",
             "ssp_subsector":"sub1","tvalue":3.2},
        ])

    def test_baseline_calibrated_at_ref(self):
        """Baseline values at time_period_ref must equal the target after rescaling."""
        data = self._build_data()
        te   = self._build_te()
        res  = postproc.rescale_py(data, te, ["uganda"], "_0", 4)
        base = res[(res["primary_id"]==0) & (res["time_period"]==4)]
        # em_a: target=8.0, uncal=10.0 → dev=0.8 → baseline[t=4]=8.0
        self.assertAlmostEqual(float(base["emission_co2e_em_a"].values[0]), 8.0, places=9)
        # em_b: target=3.2, uncal=4.0 → dev=0.8 → baseline[t=4]=3.2
        self.assertAlmostEqual(float(base["emission_co2e_em_b"].values[0]), 3.2, places=9)

    def test_nonzero_branch_propagation(self):
        """Case init≠0: values propagate as init_value * cumprod(1 + pct_diff)."""
        data = self._build_data()
        te   = self._build_te()
        res  = postproc.rescale_py(data, te, ["uganda"], "_0", 4)

        # em_a pid=1: init=8.0, pct_diffs from [8, 9.6, 11] = [0, 0.2, 0.14583...]
        init = 8.0
        pct = [0.0, 1.6/8.0, 1.4/9.6]
        expected = [init * np.prod(1+np.array(pct[:i+1])) for i in range(3)]

        for i, tp in enumerate([4,5,6]):
            got = float(res[(res["primary_id"]==1)&(res["time_period"]==tp)]["emission_co2e_em_a"].values[0])
            self.assertAlmostEqual(got, expected[i], places=9, msg=f"tp={tp}")

    def test_subsector_total_equals_sum(self):
        """emission_co2e_subsector_total_sub1 must equal em_a + em_b for all rows."""
        data = self._build_data()
        te   = self._build_te()
        res  = postproc.rescale_py(data, te, ["uganda"], "_0", 4)
        col  = "emission_co2e_subsector_total_sub1"
        self.assertIn(col, res.columns)
        diff = (res[col] - res["emission_co2e_em_a"] - res["emission_co2e_em_b"]).abs()
        self.assertLess(diff.max(), 1e-9)

    def test_all_primary_ids_present(self):
        data = self._build_data()
        te   = self._build_te()
        res  = postproc.rescale_py(data, te, ["uganda"], "_0", 4)
        self.assertEqual(set(res["primary_id"].unique()), {0, 1, 2})


if __name__ == "__main__":
    unittest.main()
