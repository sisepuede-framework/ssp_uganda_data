"""
build_lever_digest.py
---------------------
Object 1 of the experiment's information digest: what model variables each lever
moves, summarised so it fits in a tool response.

Why a summary is needed at all: lever groups are wildly uneven. 16 of the 54 move a
single variable field, 39 move five or fewer -- but group 11 moves 186. Dumping the
raw list is impossible for the heavy ones and unnecessary for the light ones, so the
rule has to be per-lever and it has to be documented, because the summarisation rule
is itself part of the artefact the study proposes.

The rule:
  <= SMALL fields      -> list every field verbatim
  <= MEDIUM fields     -> collapse to templated families
  >  MEDIUM fields     -> collapse to families, keep the largest TOP_FAMILIES
Jointly-constrained sets are never split (see `constrained_group`).

Templating finds the token positions that VARY across a lever's fields, wherever they
sit. A naive "strip the last token" rule fails on group 33, whose fields are
`fuelefficiency_trns_<mode>_<fuel>_km_per_<unit>` -- the varying tokens are in the
middle, and stripping the suffix collapses 36 fields to 36 families, i.e. nothing.

Run:  python backend/scripts/build_lever_digest.py [--out backend/lever_digest.json]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

SMALL, MEDIUM, TOP_FAMILIES = 5, 20, 8

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent.parent.parent
_VTL = (_REPO / "metamodel" / "data" / "ssp"
        / "sisepuede_run_2026-05-30t21;35;56.244639"
        / "VARIABLE_TRAJECTORY_GROUPS_L.csv")
_REGISTRY = _BACKEND / "feature_registry.json"

# Field sets that are jointly constrained: they sum to one, so reporting a member in
# isolation hides what raising it costs the others and can make an unreachable target
# look reachable. Detected by shared prefix rather than hard-coded per lever.
_CONSTRAINED_PREFIXES = ("frac_",)


def _common_prefix(split: list[list[str]]) -> int:
    """Number of leading tokens every field shares."""
    n = 0
    for toks in zip(*split):
        if len({t for t in toks}) > 1:
            break
        n += 1
    return n


def _summarise(fields: list[str], max_members: int = 14) -> dict:
    """Describe a large field set by its shared quantity and its category axes.

    An earlier version replaced every varying token with `*`. That destroys the
    information on exactly the levers that need summarising: group 11 crosses ~25
    industrial subsectors with ~8 fuels, so nearly every position varies and the
    whole set collapses to `frac_inen_energy_*_*`, which tells a reader nothing.

    Instead: the longest common token prefix is the physical quantity the lever sets,
    and what remains is the category. Where the remainders share a small set of final
    tokens, that set is reported as a second axis -- for a fuel mix, the fuels.
    """
    split = [f.split("_") for f in fields]
    k = _common_prefix(split)
    quantity = "_".join(split[0][:k]) if k else ""
    remainders = ["_".join(s[k:]) for s in split]

    # Find the category axis by searching suffix LENGTHS, not assuming one token.
    # Taking only the last token mis-splits multi-token members: group 11's fuels
    # include `natural_gas`, `furnace_gas` and `solid_biomass`, so a one-token rule
    # leaves "natural" and "furnace" glued to the industry and inflates that axis
    # from ~25 members to 75. Score each candidate length by how few distinct values
    # it yields while still covering the set, and keep the best.
    axis = heads = None
    best = None
    for width in (1, 2, 3):
        vals, hs, ok = [], [], 0
        for r in remainders:
            toks = r.split("_")
            if len(toks) <= width:
                continue
            vals.append("_".join(toks[-width:]))
            hs.append("_".join(toks[:-width]))
            ok += 1
        if not ok or ok < 0.8 * len(remainders):
            continue
        n_vals, n_heads = len(set(vals)), len(set(hs))
        if n_vals > max_members or n_vals < 2:
            continue
        # Prefer a clean rectangle: few members on the axis, few on the head axis.
        score = (n_vals * n_heads, n_vals)
        if best is None or score < best[0]:
            best = (score, sorted(set(vals)), sorted(set(hs)))
    if best is not None:
        _, axis, heads = best

    out: dict = {"quantity": quantity, "n_fields": len(fields)}
    if axis is not None:
        out["axes"] = [
            {"name": "category", "n": len(heads), "members": heads[:max_members],
             "truncated": max(0, len(heads) - max_members)},
            {"name": "sub_category", "n": len(axis), "members": axis},
        ]
    else:
        uniq = sorted(set(remainders))
        out["members"] = uniq[:max_members]
        out["truncated"] = max(0, len(uniq) - max_members)
    return out


def _constrained(fields: list[str]) -> bool:
    return any(f.startswith(_CONSTRAINED_PREFIXES) for f in fields)


def build() -> dict:
    vtl = pd.read_csv(_VTL)
    registry = json.loads(_REGISTRY.read_text())
    levers = registry["lever_features"]

    digest: dict[str, dict] = {}
    for gid_str, meta in sorted(levers.items(), key=lambda kv: int(kv[0])):
        gid = int(gid_str)
        rows = vtl[vtl["variable_trajectory_group"] == gid]
        fields = sorted(rows["variable_field"].dropna().unique().tolist())
        entry: dict = {
            "group_id": gid,
            "display_name": meta["display_name"],
            "sector": meta["sector"],
            "n_fields": len(fields),
            "jointly_constrained": _constrained(fields),
        }
        if not fields:
            entry.update(detail="none", note="no variable map for this group")
            digest[gid_str] = entry
            continue

        if len(fields) <= SMALL:
            entry.update(detail="fields", fields=fields)
        else:
            entry.update(detail="summary", summary=_summarise(fields))
        digest[gid_str] = entry

    counts = Counter(e["detail"] for e in digest.values())
    return {
        "_metadata": {
            "object": "1 - lever to variable map",
            "source": _VTL.name,
            "rule": {"small": SMALL, "medium": MEDIUM, "top_families": TOP_FAMILIES},
            "n_levers": len(digest),
            "detail_mode_counts": dict(counts),
        },
        "levers": digest,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(_BACKEND / "lever_digest.json"))
    args = ap.parse_args()

    d = build()
    Path(args.out).write_text(json.dumps(d, indent=2))
    md = d["_metadata"]
    print(f"levers: {md['n_levers']}  modes: {md['detail_mode_counts']}")
    print(f"written: {args.out}")

    for gid in ("11", "33", "35"):
        e = d["levers"][gid]
        print(f"\n--- group {gid}: {e['display_name']} ({e['sector']})")
        print(f"    {e['n_fields']} fields, mode={e['detail']}"
              + (", JOINTLY CONSTRAINED" if e["jointly_constrained"] else ""))
        for f in e.get("fields", []):
            print(f"      {f}")
        s = e.get("summary")
        if s:
            print(f"      quantity: {s['quantity']}_*")
            for ax in s.get("axes", []):
                shown = ", ".join(ax["members"])
                more = f" (+{ax['truncated']} more)" if ax.get("truncated") else ""
                print(f"      {ax['name']} [{ax['n']}]: {shown}{more}")
            if "members" in s:
                more = f" (+{s['truncated']} more)" if s.get("truncated") else ""
                print(f"      members [{s['n_fields']}]: {', '.join(s['members'])}{more}")


if __name__ == "__main__":
    main()
