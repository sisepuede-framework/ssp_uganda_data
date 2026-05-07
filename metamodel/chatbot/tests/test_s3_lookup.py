"""
Integration tests for backend/services/s3_lookup.py.

Test 1 — find_nearest_lhs_trial (local data, no S3 needed)
    find_nearest_lhs_trial({8: 0.8}, design_id=3) returns a valid primary_id
    and the matched LHS row has group 8 value within 0.15 of 0.8.

Test 2 — get_model_inputs_row (requires S3)
    get_model_inputs_row(0) returns a dict with >100 keys and gdp_mmm_usd present.

Test 3 — get_changed_variables (requires S3)
    get_changed_variables([8], {8: 0.8}) returns a dict whose 'variables' keys
    exactly match the variable field names for group 8 in feature_registry.json
    (minus any that don't appear in the model inputs).

Run directly:
    cd metamodel/chatbot
    conda run -n uganda_metamodel_env python -m tests.test_s3_lookup

Run with pytest:
    cd metamodel/chatbot
    conda run -n uganda_metamodel_env pytest tests/test_s3_lookup.py -v
"""

import json
import os
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# Allow `python -m tests.test_s3_lookup` from metamodel/chatbot/
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
    get_changed_variables,
    get_model_inputs_row,
    _load_lhs_data,
)
from backend.config import settings

# Load group 8 variable list from feature registry
with open(settings.feature_registry_path) as _fh:
    _REGISTRY = json.load(_fh)

_GROUP8_VARS: list[str] = _REGISTRY["lever_features"]["8"]["variables"]


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
    r = _Result("Test 1 — find_nearest_lhs_trial({8: 0.8}, design_id=3)")
    try:
        primary_id = find_nearest_lhs_trial({8: 0.8}, design_id=3)
    except Exception as exc:
        return r.fail(f"raised {type(exc).__name__}: {exc}")

    # primary_id must be a non-negative integer present in ATTRIBUTE_PRIMARY
    if not isinstance(primary_id, int) or primary_id < 0:
        return r.fail(f"primary_id={primary_id!r} is not a non-negative int")

    # Look up the matched row's group 8 value in the LHS data
    lhs_df, attr_primary = _load_lhs_data()
    d3 = lhs_df[lhs_df["design_id"] == 3]

    # Resolve primary_id → future_id via ATTRIBUTE_PRIMARY
    attr_row = attr_primary[
        (attr_primary["design_id"] == 3)
        & (attr_primary["primary_id"] == primary_id)
    ]
    if attr_row.empty:
        return r.fail(
            f"primary_id={primary_id} not found in ATTRIBUTE_PRIMARY for design_id=3"
        )
    future_id = int(attr_row.iloc[0]["future_id"])

    lhs_row = d3[d3["future_id"] == future_id]
    if lhs_row.empty:
        return r.fail(f"future_id={future_id} not found in LHS CSV for design_id=3")

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


# ── Test 3: get_changed_variables ────────────────────────────────────────────

def test_get_changed_variables() -> _Result:
    r = _Result("Test 3 — get_changed_variables([8], {8: 0.8})")
    try:
        result = get_changed_variables(group_ids=[8], l_values={8: 0.8})
    except Exception as exc:
        if _is_s3_auth_error(exc):
            return r.skip(
                f"S3 auth required. Run:  aws sso login --profile alexa\n"
                f"  then re-run this test.\n"
                f"  (Original error: {exc})"
            )
        return r.fail(f"raised {type(exc).__name__}: {exc}")

    variables_returned = set(result.get("variables", {}).keys())
    expected_vars = set(_GROUP8_VARS)

    # Some variables may be absent from model inputs if SISEPUEDE didn't write
    # them for this run; we only assert that returned vars ⊆ expected vars,
    # and that at least one expected var was returned (not an empty set).
    unexpected = variables_returned - expected_vars
    missing = expected_vars - variables_returned

    details = [
        f"primary_id matched  : {result.get('primary_id')}",
        f"expected variables  : {sorted(expected_vars)}",
        f"returned variables  : {sorted(variables_returned)}",
        f"missing from result : {sorted(missing) if missing else 'none'}",
        f"unexpected in result: {sorted(unexpected) if unexpected else 'none'}",
    ]

    failures = []
    if unexpected:
        failures.append(
            f"ASSERTION FAILED: returned vars not in registry group 8: {sorted(unexpected)}"
        )
    if not variables_returned:
        failures.append(
            "ASSERTION FAILED: no variables returned at all"
        )

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


def test_get_changed_variables_pytest():
    res = test_get_changed_variables()
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
        test_get_changed_variables,
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
