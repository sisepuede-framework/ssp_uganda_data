"""
Step 3 · fill the gaps of the trace from the code: for each output variable the trace saw written with no
incoming edge, or never saw at all, the variables referenced in the function(s) that write it.

Coarser than the trace (every variable the function mentions, used or not), so these edges are flagged
`static` and only fill gaps: a target that already has traced edges is left alone, and a function that mentions
more than MAX_REFS variables (AFOLU.project mentions 128) is too coarse to use; its outputs stay listed as gaps.

Reads SISEPUEDE 1.4.0's source as text (no import): `self.modvar_x = "Name"` assignments give each attribute's
variable name; a function writes a variable when it passes `self.modvar_x` to array_to_df.

    python -m backend.rdm.network.static run_2026_05_30
writes
    network/out/<run>_edges_static.csv   source, target, model, function, n
"""

import ast
import re
import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).parent / "out"
MODELS = Path("/opt/miniconda3/envs/ssp_uganda_env/lib/python3.11/site-packages/sisepuede/models")
ASSIGN = re.compile(r'self\.(modvar_[a-z0-9_]+)\s*=\s*"([^"]+)"')
REF = re.compile(r"self\.(modvar_[a-z0-9_]+)\b")
MAX_REFS = 40
WRITE = re.compile(r"array_to_df\(\s*[^,]+,\s*self\.(modvar_[a-z0-9_]+)", re.S)


def functions():
    """(model, function name, source, {attribute: variable}) for every function in the model files."""
    for f in sorted(MODELS.glob("*.py")):
        src = f.read_text()
        names = dict(ASSIGN.findall(src))
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.FunctionDef):
                yield f.stem, node.name, ast.get_source_segment(src, node) or "", names


def build(targets: set) -> pd.DataFrame:
    rows = []
    for model, func, src, names in functions():
        written = {names.get(a) for a in WRITE.findall(src)} & targets
        if not written:
            continue
        used = {names[a] for a in REF.findall(src) if a in names}
        if len(used) > MAX_REFS:
            continue
        for t in written:
            rows += [{"source": s, "target": t, "model": model, "function": func, "n": 1} for s in sorted(used - {t})]
    return pd.DataFrame(rows, columns=["source", "target", "model", "function", "n"])


if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "run_2026_05_30"
    traced = pd.read_csv(OUT / f"{run}_edges_traced.csv")
    variables = pd.read_csv(OUT / f"{run}_variables.csv")
    outputs = set(variables[(variables.type == "Output") & (variables.n_fields_in_aws > 0)].variable)
    targets = outputs - set(traced.target)
    e = build(targets)
    e.to_csv(OUT / f"{run}_edges_static.csv", index=False)
    print(f"output variables with no traced edge: {len(targets)} · filled from the code: {e.target.nunique()} "
          f"({len(e)} edges)")
    for t in sorted(targets - set(e.target)):
        print("   still none:", t)
