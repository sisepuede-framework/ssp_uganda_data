"""
Integration tests for backend/services/s3_lookup.py.

Test 1 — find_nearest_lhs_trial (local data, no S3 needed)
    find_nearest_lhs_trial({8: 0.8}, design_id=4) returns a valid primary_id
    and the matched LHS row has group 8 value within 0.15 of 0.8.
    (design_id=4 is the L-and-X scenario design the 2026-05-30 run ships;
    the older design_id=3 no longer exists.)

Test 2 — get_model_inputs_row (requires S3)
    get_model_inputs_row(0) returns a dict with >100 keys and gdp_mmm_usd present.

Test 3 — get_scenario_variable_trajectories (requires S3)
    get_scenario_variable_trajectories([8, 30], {8: 0.8, 30: 0.5}) returns the
    documented contract:
      • every requested group appears in 'groups' and resolves to ≥1 input driver
        (the VARIABLE_TRAJECTORY_GROUPS_L fallback guarantees this for all 54);
      • group 8 (TX:FGTV:DEC_LEAKS) has no mapped outputs → has_outputs is False;
      • group 30 (TX:SCOE:SHIFT_FUEL_HEAT) has mapped outputs → has_outputs is True;
      • each record has the shape {field, name, by_year, pct_change}, by_year keys
        are a subset of the anchor years, and input/output lists honor top_n.

Run directly:
    cd metamodel/chatbot_deploy
    conda run -n uganda_metamodel_env python -m tests.test_s3_lookup

Run with pytest:
    cd metamodel/chatbot_deploy
    conda run -n uganda_metamodel_env pytest tests/test_s3_lookup.py -v
"""

import json
import os
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# Allow `python -m tests.test_s3_lookup` from metamodel/chatbot_deploy/
_CHATBOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_CHATBOT_DIR))

# ── AWS credential helper ─────────────────────────────────────────────────────
# The .env sets AWS_PROFILE=alexa (SSO). If the SSO token is expired boto3
# raises TokenRetrievalError. We detect that and skip S3-dependent tests with
# a clear message instead of a red failure.
_S3_SKIP_REASON: str | None = None

try:
    from botocore.exceptions import ClientError, TokenRetrievalError  # type: ignore
    _BOTOCORE_AVAILABLE = True
except ImportError:
    _BOTOCORE_AVAILABLE = False

# ── Import s3_lookup (loads settings + local CSV data) ────────────────────────
from backend.services.s3_lookup import (
    find_nearest_lhs_trial,
    get_model_inputs_row,
    get_scenario_variable_trajectories,
    _INPUT_ANCHORS,
    _OUTPUT_ANCHORS,
    _load_lhs_data,
)
from backend.config import settings

# design_id used by the trajectory lookup (L and X both vary).
_SCENARIO_DESIGN_ID = 4

# Anchor years the summaries are keyed by (derived from the module constants).
_INPUT_YEARS = {year for _tp, year in _INPUT_ANCHORS}
_OUTPUT_YEARS = {year for _tp, year in _OUTPUT_ANCHORS}

# Groups exercised in Test 3, with the invariant each one must satisfy.
# Group 8  (Reduce LEAKS)          → inputs only, no downstream outputs.
# Group 30 (SCOE fuel/heat shift)  → inputs AND downstream outputs.
_GROUP_LEAKS = 8
_GROUP_SCOE = 30


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_s3_auth_error(exc: Exception) -> bool:
    """Return True if exception is an AWS auth/token failure."""
    msg = str(exc).lower()
    return any(kw in msg for kw in (
        "token has expired",
        "tokenretrievalerror",
        "expired",
        "credentialretrievalerror",
        "unable to locate credentials",
    ))


def _get_group(groups: dict, gid: int) -> dict | None:
    """Fetch a group entry whether the dict is keyed by int or str."""
    return groups.get(gid) or groups.get(str(gid))


def _record_shape_errors(rec: dict, allowed_years: set[int]) -> list[str]:
    """Return a list of contract violations for a single trajectory record."""
    errs: list[str] = []
    for key in ("field", "name", "by_year", "pct_change"):
        if key not in rec:
            errs.append(f"record missing key '{key}': {rec!r}")
    by_year = rec.get("by_year")
    if not isinstance(by_year, dict) or not by_year:
        errs.append(f"by_year must be a non-empty dict: {by_year!r}")
    else:
        stray = set(by_year) - allowed_years
        if stray:
            errs.append(f"by_year has non-anchor years {sorted(stray)}")
    return errs


class _Result:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.skipped = False
        self.skip_reason: str = ""
        self.details: list[str] = []

    def ok(self, *details: str) -> "_Result":
        self.passed = True
        self.details.extend(details)
        return self

    def fail(self, *details: str) -> "_Result":
        self.passed = False
        self.details.extend(details)
        return self

    def skip(self, reason: str) -> "_Result":
        self.skipped = True
        self.skip_reason = reason
        return self

    def __str__(self) -> str:
        if self.skipped:
            status = "SKIP"
            body = f"  → {self.skip_reason}"
        elif self.passed:
            status = "PASS"
            body = "\n".join(f"  {d}" for d in self.details)
        else:
            status = "FAIL"
            body = "\n".join(f"  ✗ {d}" for d in self.details)
        return f"[{status}] {self.name}\n{body}"


# ── Test 1: find_nearest_lhs_trial ────────────────────────────────────────────

def test_find_nearest_lhs_trial() -> _Result:
    did = _SCENARIO_DESIGN_ID
    r = _Result(f"Test 1 — find_nearest_lhs_trial({{8: 0.8}}, design_id={did})")
    try:
        primary_id = find_nearest_lhs_trial({8: 0.8}, design_id=did)
    except Exception as exc:
        return r.fail(f"raised {type(exc).__name__}: {exc}")

    # primary_id must be a non-negative integer present in ATTRIBUTE_PRIMARY
    if not isinstance(primary_id, int) or primary_id < 0:
        return r.fail(f"primary_id={primary_id!r} is not a non-negative int")

    # Look up the matched row's group 8 value in the LHS data
    lhs_df, attr_primary = _load_lhs_data()
    design = lhs_df[lhs_df["design_id"] == did]

    # Resolve primary_id → future_id via ATTRIBUTE_PRIMARY
    attr_row = attr_primary[
        (attr_primary["design_id"] == did)
        & (attr_primary["primary_id"] == primary_id)
    ]
    if attr_row.empty:
        return r.fail(
            f"primary_id={primary_id} not found in ATTRIBUTE_PRIMARY for design_id={did}"
        )
    future_id = int(attr_row.iloc[0]["future_id"])

    lhs_row = design[design["future_id"] == future_id]
    if lhs_row.empty:
        return r.fail(f"future_id={future_id} not found in LHS CSV for design_id={did}")

    group8_val = float(lhs_row.iloc[0]["8"])
    distance = abs(group8_val - 0.8)

    details = [
        f"primary_id returned : {primary_id}",
        f"future_id matched   : {future_id}",
        f"group 8 value in LHS: {group8_val:.6f}",
        f"distance from 0.8   : {distance:.6f}  (threshold ≤ 0.15)",
    ]

    if distance > 0.15:
        return r.fail(
            *details,
            f"ASSERTION FAILED: distance {distance:.6f} > 0.15",
        )

    return r.ok(*details)


# ── Test 2: get_model_inputs_row ─────────────────────────────────────────────

def test_get_model_inputs_row() -> _Result:
    r = _Result("Test 2 — get_model_inputs_row(0)")
    try:
        row = get_model_inputs_row(0)
    except Exception as exc:
        if _is_s3_auth_error(exc):
            return r.skip(
                f"S3 auth required. Run:  aws sso login --profile alexa\n"
                f"  then re-run this test.\n"
                f"  (Original error: {exc})"
            )
        return r.fail(f"raised {type(exc).__name__}: {exc}")

    n_keys = len(row)
    has_gdp = "gdp_mmm_usd" in row
    gdp_sample = row["gdp_mmm_usd"][:4] if has_gdp else []

    details = [
        f"number of keys      : {n_keys}  (threshold > 100)",
        f"gdp_mmm_usd present : {has_gdp}",
    ]
    if has_gdp:
        formatted = [f"{v:.4f}" for v in gdp_sample]
        details.append(f"gdp_mmm_usd[0:4]    : {formatted}  (tp 0–3, years 2015–2018)")

    failures = []
    if n_keys <= 100:
        failures.append(f"ASSERTION FAILED: {n_keys} keys ≤ 100")
    if not has_gdp:
        failures.append("ASSERTION FAILED: gdp_mmm_usd not in row")

    if failures:
        return r.fail(*details, *failures)
    return r.ok(*details)


# ── Test 3: get_scenario_variable_trajectories ────────────────────────────────

def test_get_scenario_variable_trajectories() -> _Result:
    r = _Result(
        "Test 3 — get_scenario_variable_trajectories([8, 30], {8: 0.8, 30: 0.5})"
    )
    group_ids = [_GROUP_LEAKS, _GROUP_SCOE]
    top_n = 6
    try:
        result = get_scenario_variable_trajectories(
            group_ids=group_ids, l_values={8: 0.8, 30: 0.5}, top_n=top_n
        )
    except Exception as exc:
        if _is_s3_auth_error(exc):
            return r.skip(
                f"S3 auth required. Run:  aws sso login --profile alexa\n"
                f"  then re-run this test.\n"
                f"  (Original error: {exc})"
            )
        return r.fail(f"raised {type(exc).__name__}: {exc}")

    primary_id = result.get("primary_id")
    groups = result.get("groups", {})

    leaks = _get_group(groups, _GROUP_LEAKS)
    scoe = _get_group(groups, _GROUP_SCOE)

    details = [
        f"primary_id matched  : {primary_id}",
        f"groups returned     : {sorted(str(k) for k in groups)}",
    ]

    failures: list[str] = []

    # primary_id must be a non-negative int.
    if not isinstance(primary_id, int) or primary_id < 0:
        failures.append(f"ASSERTION FAILED: primary_id={primary_id!r} not a non-negative int")

    # Both requested groups must be present.
    if leaks is None:
        failures.append(f"ASSERTION FAILED: group {_GROUP_LEAKS} missing from result")
    if scoe is None:
        failures.append(f"ASSERTION FAILED: group {_GROUP_SCOE} missing from result")

    # Per-group contract checks (only where the group came back).
    for gid, g in ((_GROUP_LEAKS, leaks), (_GROUP_SCOE, scoe)):
        if g is None:
            continue
        counts = g.get("counts", {})
        n_in, n_out = counts.get("inputs", 0), counts.get("outputs", 0)
        inputs, outputs = g.get("inputs", []), g.get("outputs", [])
        details.append(
            f"group {gid} ({g.get('transformation_code', '')}): "
            f"inputs={n_in} outputs={n_out} has_outputs={g.get('has_outputs')}"
        )

        # Fallback guarantee: every group resolves to ≥1 input driver.
        if n_in < 1 or not inputs:
            failures.append(f"ASSERTION FAILED: group {gid} has no input drivers")

        # top_n cap on both lists.
        if len(inputs) > top_n:
            failures.append(f"ASSERTION FAILED: group {gid} inputs {len(inputs)} > top_n {top_n}")
        if len(outputs) > top_n:
            failures.append(f"ASSERTION FAILED: group {gid} outputs {len(outputs)} > top_n {top_n}")

        # has_outputs flag must agree with the output count.
        if g.get("has_outputs") != (n_out > 0):
            failures.append(
                f"ASSERTION FAILED: group {gid} has_outputs={g.get('has_outputs')} "
                f"disagrees with counts.outputs={n_out}"
            )

        # Record shape / anchor-year checks.
        for rec in inputs:
            failures.extend(f"group {gid} input {e}" for e in _record_shape_errors(rec, _INPUT_YEARS))
        for rec in outputs:
            failures.extend(f"group {gid} output {e}" for e in _record_shape_errors(rec, _OUTPUT_YEARS))

    # Group-specific output expectations (derived from the local variable maps,
    # independent of the S3 data): LEAKS has none, SCOE has some.
    if leaks is not None and leaks.get("has_outputs"):
        failures.append(f"ASSERTION FAILED: group {_GROUP_LEAKS} (LEAKS) should have no mapped outputs")
    if scoe is not None and not scoe.get("has_outputs"):
        failures.append(f"ASSERTION FAILED: group {_GROUP_SCOE} (SCOE) should have mapped outputs")

    if failures:
        return r.fail(*details, *failures)
    return r.ok(*details)


# ── pytest-compatible wrappers ────────────────────────────────────────────────

def test_find_nearest_lhs_trial_pytest():
    res = test_find_nearest_lhs_trial()
    if res.skipped:
        import pytest
        pytest.skip(res.skip_reason)
    assert res.passed, str(res)


def test_get_model_inputs_row_pytest():
    res = test_get_model_inputs_row()
    if res.skipped:
        import pytest
        pytest.skip(res.skip_reason)
    assert res.passed, str(res)


def test_get_scenario_variable_trajectories_pytest():
    res = test_get_scenario_variable_trajectories()
    if res.skipped:
        import pytest
        pytest.skip(res.skip_reason)
    assert res.passed, str(res)


# ── Standalone runner ─────────────────────────────────────────────────────────

def _run_all() -> int:
    """Run all tests and print results. Returns exit code (0 = all pass/skip)."""
    tests = [
        test_find_nearest_lhs_trial,
        test_get_model_inputs_row,
        test_get_scenario_variable_trajectories,
    ]

    results = [t() for t in tests]

    print()
    print("=" * 70)
    print("  s3_lookup integration tests")
    print("=" * 70)
    for res in results:
        print()
        print(str(res))
    print()
    print("=" * 70)

    n_pass = sum(1 for r in results if r.passed)
    n_skip = sum(1 for r in results if r.skipped)
    n_fail = sum(1 for r in results if not r.passed and not r.skipped)
    print(f"  {n_pass} passed  |  {n_skip} skipped  |  {n_fail} failed")
    print("=" * 70)
    print()

    if n_skip:
        print("  To run S3 tests: aws sso login --profile alexa")
        print()

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
