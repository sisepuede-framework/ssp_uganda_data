"""
Tests for backend/rdm/runs: the run manifest that keeps code independent of any one run.

Test 1 — the active manifest resolves to files that exist locally (LHC design, group
         definitions, structural map, surrogate).
Test 2 — data roles point at the right S3 tables: emissions from decomposed_emissions,
         variables from model_output.
Test 3 — switching runs: a second manifest (by argument or by RDM_RUN) moves every path,
         and no path keeps the old run id.
Test 4 — a manifest missing a data role is rejected.
"""

import shutil
import sys
from pathlib import Path

import pytest
import yaml

_CHATBOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_CHATBOT_DIR))

from backend.rdm.runs import RUNS_DIR, Run, active_run_name, get_run  # noqa: E402


def test_active_manifest_resolves_to_existing_files():
    run = get_run()
    assert isinstance(run, Run)
    assert run.name == active_run_name()
    assert run.run_dir.is_dir(), run.run_dir
    for name in ("lhc_levers", "lhc_uncertainties", "primary", "groups_l", "groups_x"):
        assert run.local(name).is_file(), run.local(name)
    assert run.structural_map.is_file(), run.structural_map
    assert run.surrogate_path.is_file(), run.surrogate_path
    assert run.years == (2025, 2035, 2040, 2050, 2060, 2070)


def test_data_roles_point_at_the_right_tables():
    run = get_run()
    assert run.table("emissions") == "decomposed_emissions"
    assert run.table("variables") == "model_output"
    assert run.s3_table_uri("emissions") == (
        f"s3://{run.bucket}/run_database/sisepuede_run_{run.run_id}/decomposed_emissions/")
    with pytest.raises(KeyError):
        run.table("pathways")


def _write_copy(tmp_path: Path, new_id: str) -> Path:
    src = RUNS_DIR / f"{active_run_name()}.yaml"
    raw = yaml.safe_load(src.read_text())
    raw["run_id"] = new_id
    (tmp_path / "next_run.yaml").write_text(yaml.safe_dump(raw))
    shutil.copy(src, tmp_path / src.name)
    return tmp_path


def test_switching_runs_moves_every_path(tmp_path, monkeypatch):
    old = get_run()
    runs_dir = _write_copy(tmp_path, "2027-01-01t00;00;00.000000")

    new = get_run("next_run", runs_dir=runs_dir)
    for path in (new.run_dir, new.surrogate_path, new.local("groups_l")):
        assert "2027-01-01" in str(path)
        assert old.run_id not in str(path)
    assert "2027-01-01" in new.s3_table_uri("variables")

    monkeypatch.setenv("RDM_RUN", "next_run")
    assert get_run(runs_dir=runs_dir).run_id == "2027-01-01t00;00;00.000000"


def test_manifest_missing_a_role_is_rejected(tmp_path):
    raw = yaml.safe_load((RUNS_DIR / f"{active_run_name()}.yaml").read_text())
    del raw["s3"]["tables"]["emissions"]
    (tmp_path / "broken.yaml").write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="emissions"):
        get_run("broken", runs_dir=tmp_path)
