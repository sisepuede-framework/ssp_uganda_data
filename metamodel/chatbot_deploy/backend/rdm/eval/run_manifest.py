"""
Manifests of the conversation logs (version control for data that is not in git).

The logs under pilot_runs/ are kept out of git (47 MB of JSON). For each run folder this writes a manifest that IS
committed: every file with its size and SHA-256, and what the log records about its own version (model, effort, code
commit, prompt and tool fingerprints, start time). Anyone holding the logs can check they are the ones analysed;
anyone holding only git can see exactly what each run contained and which code produced it.

    python -m backend.rdm.eval.run_manifest            → backend/rdm/eval/run_manifests/<folder>.csv + index.csv
    python -m backend.rdm.eval.run_manifest --check    → recompute and report any file that changed or went missing

A manifest is rewritten only when the folder changed; --check never writes.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from backend.rdm.harness.agent import RUNS_DIR

OUT = Path(__file__).parent / "run_manifests"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(p: Path) -> dict:
    row = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    if p.suffix == ".json":
        try:
            r = json.loads(p.read_text())
        except ValueError:
            return row
        v = r.get("versions") or {}
        row.update(question_id=r.get("question_id"), arm=r.get("arm"), rep=r.get("rep"),
                   question_set=r.get("question_set"), condition=r.get("condition"), model=r.get("model"),
                   effort=r.get("effort"), git_commit=(v.get("git_commit") or "")[:10],
                   uncommitted_code=v.get("rdm_code_uncommitted_changes"), system_prompt_sha=v.get("system_prompt_sha"),
                   tools_sha=v.get("tools_sha"), started=r.get("started"), error=bool(r.get("error")))
    return row


def manifest(folder: Path) -> pd.DataFrame:
    rows = [{"file": str(p.relative_to(folder)), **describe(p)}
            for p in sorted(folder.rglob("*")) if p.is_file() and not p.name.startswith(".")]
    return pd.DataFrame(rows)


def folders():
    return sorted(d for d in RUNS_DIR.iterdir() if d.is_dir())


def main(check: bool):
    OUT.mkdir(exist_ok=True)
    index, problems = [], []
    for d in folders():
        m = manifest(d)
        path = OUT / f"{d.name}.csv"
        if path.exists():
            old = pd.read_csv(path)
            changed = set(zip(old.file, old.sha256)) ^ set(zip(m.file, m.sha256))
            if changed:
                problems.append(f"{d.name}: {len(changed)} file(s) added, removed or changed since the manifest")
        if not check and (not path.exists() or problems and problems[-1].startswith(d.name)):
            m.to_csv(path, index=False)
        logs = m[m.file.str.endswith(".json") & ~m.file.str.startswith("_infra")] if len(m) else m
        index.append({"folder": d.name, "files": len(m), "conversation_logs": int(logs.get("question_id",
                      pd.Series(dtype=object)).notna().sum()) if len(m) else 0,
                      "arms": " ".join(sorted(map(str, logs["arm"].dropna().unique()))) if "arm" in logs else "",
                      "git_commits": " ".join(sorted(map(str, logs["git_commit"].dropna().unique()))) if "git_commit" in logs else "",
                      "models": " ".join(sorted(map(str, logs["model"].dropna().unique()))) if "model" in logs else "",
                      "first_started": logs["started"].dropna().min() if "started" in logs else "",
                      "last_started": logs["started"].dropna().max() if "started" in logs else ""})
    if not check:
        pd.DataFrame(index).to_csv(OUT / "index.csv", index=False)
    print(pd.DataFrame(index).to_string(index=False))
    print("\n" + ("\n".join(problems) if problems else "every folder matches its manifest" if check else
                  f"manifests written to {OUT}"))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--check", action="store_true")
    main(a.parse_args().check)
