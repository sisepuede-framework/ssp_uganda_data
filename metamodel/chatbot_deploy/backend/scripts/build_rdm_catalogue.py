"""
Generate the full L / X catalogue inside docs/rdm_levers_and_uncertainties.md.

Why
---
That document goes to the technical team for review, and its whole value is that it
shows EXACTLY what the assistant knows about the levers and uncertainties — not a
hand-written paraphrase that can drift. So the catalogue tables are generated from
`backend/feature_registry.json`, the same file `agent._build_system_prompt()` reads.

Usage
-----
    python backend/scripts/build_rdm_catalogue.py

Everything between the BEGIN/END GENERATED CATALOGUE markers in the doc is replaced;
the hand-written sections around it are left untouched. Re-run after any registry
rebuild (see build_feature_registry.py).
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]      # .../chatbot_deploy
REGISTRY = REPO_ROOT / "backend" / "feature_registry.json"
DOC = REPO_ROOT / "docs" / "rdm_levers_and_uncertainties.md"

BEGIN = "<!-- BEGIN GENERATED CATALOGUE -->"
END = "<!-- END GENERATED CATALOGUE -->"


def _escape(cell: str) -> str:
    """Markdown tables break on raw pipes; nothing else needs escaping here."""
    return str(cell).replace("|", "\\|").strip()


def build_lever_table(levers: dict) -> list[str]:
    """One row per policy lever, grouped by sector so a sector expert can find
    their own rows quickly. The last column is deliberately empty — it is where
    the team writes the description a policymaker should read."""
    by_sector: dict[str, list[tuple[int, dict]]] = {}
    for gid, meta in levers.items():
        by_sector.setdefault(meta["sector"], []).append((int(gid), meta))

    lines = [
        f"### Policy levers (L) — {len(levers)} levers across {len(by_sector)} sectors",
        "",
        "Scale for every lever: **0 = no action** (business as usual) → **1 = maximum "
        "technically feasible deployment by 2070**, reached via a ramp, not a step change.",
        "",
        "The *Current wording* column is what the assistant says today; it is generated from the "
        "SISEPUEDE transformation code. **Expert description** is empty on purpose — please fill it in.",
        "",
    ]

    for sector in sorted(by_sector, key=lambda s: (-len(by_sector[s]), s)):
        rows = sorted(by_sector[sector], key=lambda r: r[0])
        lines.append(f"#### {sector} ({len(rows)} levers)")
        lines.append("")
        lines.append("| ID | Lever | SISEPUEDE transformation | Current wording at L = 1 | Expert description |")
        lines.append("|---|---|---|---|---|")
        for gid, meta in rows:
            lines.append(
                f"| {gid} "
                f"| {_escape(meta['display_name'])} "
                f"| `{_escape(meta['transformation_code'])}` "
                f"| {_escape(meta['semantic_max'])} "
                f"|  |"
            )
        lines.append("")
    return lines


def build_exogenous_table(exog: dict) -> list[str]:
    """One row per exogenous uncertainty. The 0 / 0.5 / 1 wording is formulaic in the
    registry, so the convention is stated once and the table stays readable."""
    lines = [
        f"### Exogenous uncertainties (X) — {len(exog)} factors",
        "",
        "Scale for every factor: **0 = low end** of its uncertainty range · "
        "**0.5 = median (central) future** (the default when the user says nothing) · "
        "**1 = high end**. These are positions within the model's range, *not* percentage changes.",
        "",
        "*Recognised as* lists the words the assistant matches when a user names the factor in "
        "plain language.",
        "",
        "| ID | Factor | Domain | Recognised as | Expert description |",
        "|---|---|---|---|---|",
    ]
    for gid, meta in sorted(exog.items(), key=lambda kv: int(kv[0])):
        domain = meta["sector"].replace("Exogenous / ", "")
        aliases = ", ".join(meta.get("aliases", []))
        lines.append(
            f"| {gid} "
            f"| {_escape(meta['display_name'])} "
            f"| {_escape(domain)} "
            f"| {_escape(aliases)} "
            f"|  |"
        )
    lines.append("")
    return lines


def main() -> None:
    registry = json.loads(REGISTRY.read_text())
    levers = registry["lever_features"]
    exog = registry["exogenous_features"]
    meta = registry.get("_metadata", {})

    body = [
        BEGIN,
        "",
        f"*Generated from `backend/feature_registry.json` "
        f"(version {meta.get('version', '?')}, model run {meta.get('model_run_id', '?')}) — "
        f"{len(levers)} policy levers, {len(exog)} exogenous uncertainties.*",
        "",
    ]
    body += build_exogenous_table(exog)
    body += build_lever_table(levers)
    body.append(END)

    doc = DOC.read_text()
    if BEGIN not in doc or END not in doc:
        raise SystemExit(
            f"Markers not found in {DOC}. Add the BEGIN/END GENERATED CATALOGUE comments back."
        )
    head, _, rest = doc.partition(BEGIN)
    _, _, tail = rest.partition(END)
    DOC.write_text(head + "\n".join(body) + tail)

    print(f"Wrote catalogue to {DOC.relative_to(REPO_ROOT)}: "
          f"{len(levers)} levers, {len(exog)} uncertainties.")


if __name__ == "__main__":
    main()
