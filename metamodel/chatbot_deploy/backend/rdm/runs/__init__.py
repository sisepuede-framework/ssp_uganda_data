"""
Run manifests: one YAML file per SISEPUEDE run, holding every run-specific path.

Code never names a run. It calls ``get_run()`` and reads paths from the returned ``Run``.
To switch to a new run with the same structure:

  1. Copy an existing manifest in this folder to ``<new_name>.yaml`` and edit its values.
  2. Activate it: set ``RDM_RUN=<new_name>``, or write ``<new_name>`` in the ``ACTIVE`` file.

Which run is active: the ``RDM_RUN`` environment variable if set, otherwise the name in
``ACTIVE``. Relative paths in a manifest resolve against the ``metamodel/`` directory, and
``{run_id}`` is substituted everywhere.

Data roles (where each kind of data comes from):
  emissions       final emissions per field          → s3 table ``decomposed_emissions``
  variables       intermediate variables per field   → s3 table ``model_output``
  inputs          input variable trajectories        → s3 table ``model_input``
  costs_benefits  cost and benefit fields            → s3 table ``cb``
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

RUNS_DIR = Path(__file__).parent
ACTIVE_FILE = RUNS_DIR / "ACTIVE"
# metamodel/ — relative manifest paths resolve against it.
METAMODEL_DIR = RUNS_DIR.parents[3]

DATA_ROLES = ("emissions", "variables", "inputs", "costs_benefits")


@dataclass(frozen=True)
class Run:
    """Every run-specific location, resolved. Built only by ``get_run()``."""

    name: str
    run_id: str
    region: str
    bucket: str
    run_prefix: str               # S3 key prefix of the run, ending in "/"
    tables: dict = field(hash=False)   # data role → S3 table name
    glue_database: str            # Athena catalog holding the run's tables
    query_output: str             # S3 key prefix where Athena writes results
    run_dir: Path                 # local folder: LHC design, group definitions, primary ids
    cache_dir: Path               # local folder for samples and stores built from S3
    structural_map: Path          # transformation → output variables, extracted from SISEPUEDE
    registry: Path                # display names and sectors of the L and X groups
    surrogate_path: Path          # trained XGBoost pipeline for this run
    years: tuple = ()             # anchor years reported by the tools
    local_files: dict = field(default_factory=dict, hash=False)   # logical name → file in run_dir

    def table(self, role: str) -> str:
        """S3 table name for a data role (``emissions``, ``variables``, …)."""
        if role not in self.tables:
            raise KeyError(f"Run {self.name!r} has no table for role {role!r}; "
                           f"known roles: {sorted(self.tables)}")
        return self.tables[role]

    def s3_table_uri(self, role: str) -> str:
        """s3://… location of a data role's table (parent of its region=<x>/ partitions)."""
        return f"s3://{self.bucket}/{self.run_prefix}{self.table(role)}/"

    def query_output_uri(self) -> str:
        return f"s3://{self.bucket}/{self.query_output}"

    def local(self, name: str) -> Path:
        """Path of a run-level file by logical name (``lhc_levers``, ``groups_l``, …)."""
        if name not in self.local_files:
            raise KeyError(f"Run {self.name!r} has no local file {name!r}; "
                           f"known: {sorted(self.local_files)}")
        return self.run_dir / self.local_files[name]


def active_run_name() -> str:
    name = os.environ.get("RDM_RUN", "").strip()
    if name:
        return name
    if ACTIVE_FILE.exists():
        name = ACTIVE_FILE.read_text().strip()
        if name:
            return name
    raise RuntimeError(f"No active run: set RDM_RUN or write a manifest name in {ACTIVE_FILE}")


def list_runs(runs_dir: Path = RUNS_DIR) -> list:
    return sorted(p.stem for p in runs_dir.glob("*.yaml"))


def get_run(name: str | None = None, runs_dir: Path = RUNS_DIR, base_dir: Path = METAMODEL_DIR) -> Run:
    """Load a run manifest. ``name`` defaults to the active run."""
    name = name or active_run_name()
    path = runs_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No manifest {path.name} in {runs_dir}; available: {list_runs(runs_dir)}")
    raw = yaml.safe_load(path.read_text())

    run_id = str(raw["run_id"])
    sub = lambda s: str(s).replace("{run_id}", run_id)
    resolve = lambda s: Path(sub(s)) if Path(sub(s)).is_absolute() else base_dir / sub(s)

    tables = dict(raw["s3"]["tables"])
    missing = [r for r in DATA_ROLES if r not in tables]
    if missing:
        raise ValueError(f"Manifest {path.name} lacks tables for roles {missing}")

    return Run(
        name=name,
        run_id=run_id,
        region=str(raw.get("region", "uganda")),
        bucket=str(raw["s3"]["bucket"]),
        run_prefix=sub(raw["s3"]["run_prefix"]).rstrip("/") + "/",
        tables=tables,
        glue_database=str(raw["s3"]["glue_database"]),
        query_output=sub(raw["s3"]["query_output"]).rstrip("/") + "/",
        run_dir=resolve(raw["local"]["run_dir"]),
        cache_dir=resolve(raw["local"]["cache_dir"]),
        structural_map=resolve(raw["local"]["structural_map"]),
        registry=resolve(raw["local"]["registry"]),
        surrogate_path=resolve(raw["surrogate"]),
        years=tuple(int(y) for y in raw["years"]),
        local_files=dict(raw["local"].get("files", {})),
    )
