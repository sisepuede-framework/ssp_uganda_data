"""
Step 2 · trace the data flow of one SISEPUEDE run: which model variables are used to compute which.

Every array SISEPUEDE reads with ModelAttributes.extract_model_variable becomes a TagArray carrying the name
of its variable. NumPy operations (ufuncs and array functions) and item assignment merge the tags of their
operands, so an array carries every variable it was computed from. When the model writes an array with
array_to_df(array, variable), each tag becomes an edge "tag → variable", with the function that wrote it.

Relations only (plan rule 1): an edge means "used to compute", not a direction or size of effect. Tags are lost
where the code leaves NumPy (Python lists, scalars, pandas arithmetic); step 3 fills those gaps from the code.

Runs in ssp_uganda_env (SISEPUEDE 1.4.0) on the Uganda base input, with the input fields the 1.4.0 model
needs and the file lacks set to their default (0). With --electricity the run includes the electricity model (NemoMod, Julia); its Python wrapper reads and
writes model variables like the rest, so the trace sees what goes into NemoMod and what comes out.

    /opt/miniconda3/envs/ssp_uganda_env/bin/python -m backend.rdm.network.trace <input.csv> run_2026_05_30 [--electricity]
writes
    network/out/<run>_edges_traced.csv   source, target, model, function, n (times the edge was written)
    network/out/<run>_trace_log.csv      every write: target, function, number of tags
"""

import inspect
import logging
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "out"
# NemoMod reference tables: not shipped in the installed 1.4.0 package; taken from the local SISEPUEDE repository
NEMOMOD_REF = Path("/Users/alexa/Documents/centro_decisiones/sisepuede/sisepuede/ref/nemo_mod")
SHAPE_ONLY = {np.zeros_like, np.ones_like, np.empty_like, np.full_like, np.shape, np.ndim, np.size}
_NP = {name: getattr(np, name) for name in ("zeros", "ones", "empty", "full", "array", "asarray")}


class TagArray(np.ndarray):
    """An ndarray that carries the set of model variables it was computed from."""

    def __new__(cls, arr, tags=()):
        obj = _NP["asarray"](arr).view(cls)
        obj.tags = set(tags)
        return obj

    def __array_finalize__(self, obj):
        self.tags = set(getattr(obj, "tags", ()))

    def __getitem__(self, key):
        # one element would come back as a NumPy scalar, which cannot carry tags: keep it a 0-d TagArray
        res = super().__getitem__(key)
        if self.tags and isinstance(res, np.generic) and res.dtype != object:
            return TagArray(res, self.tags)
        return res

    def __setitem__(self, key, value):
        self.tags |= tags_of(value)
        super().__setitem__(key, plain(value))

    def __array_ufunc__(self, ufunc, method, *inputs, out=None, **kwargs):
        tags = tags_of(inputs)
        if out is not None:
            tags |= tags_of(out)
            kwargs["out"] = tuple(plain(o) for o in out)
        res = getattr(ufunc, method)(*plain(inputs), **kwargs)
        arrays = [x for x in inputs if isinstance(x, TagArray) and x.ndim > 0]
        parent = arrays[0] if len(arrays) == 1 and all(
            isinstance(x, TagArray) and x.ndim > 0 or np.ndim(x) == 0 for x in inputs) else None
        if out is not None:
            for o in out:
                if isinstance(o, TagArray):
                    o.tags |= tags
            return out[0] if len(out) == 1 else out
        res = wrap(res, tags)
        if parent is not None and isinstance(res, TagArray):
            res.parent = parent       # the same quantity, rescaled (unit conversion): see array_to_df below
        return res

    def __array_function__(self, func, types, args, kwargs):
        # copying only a shape (zeros_like …) is not a relation
        tags = set() if func in SHAPE_ONLY else tags_of(args) | tags_of(kwargs)
        res = func(*plain(args), **plain(kwargs))
        if res is None:     # in place (np.put, np.copyto …): the destination takes the tags of the values
            for a in args[:1]:
                if isinstance(a, TagArray):
                    a.tags |= tags
            return None
        return wrap(res, tags)


FIELD_TO_VARIABLE: dict = {}     # set by patch_pandas: a DataFrame's columns tell which variables it holds


def frame_tags(x) -> set:
    """The model variables of a DataFrame's columns (only where the frame itself becomes an array)."""
    if isinstance(x, (pd.DataFrame, pd.Series)) and FIELD_TO_VARIABLE:
        cols = [x.name] if isinstance(x, pd.Series) else list(x.columns)
        return {FIELD_TO_VARIABLE[c] for c in cols if isinstance(c, str) and c in FIELD_TO_VARIABLE}
    return set()


def tags_of(x) -> set:
    if isinstance(x, TagArray):
        return set(x.tags)
    if isinstance(x, (list, tuple)):
        return set().union(*(tags_of(v) for v in x)) if x else set()
    if isinstance(x, dict):
        return set().union(*(tags_of(v) for v in x.values())) if x else set()
    return set()


def plain(x):
    if isinstance(x, TagArray):
        return x.view(np.ndarray)
    if isinstance(x, tuple):
        return tuple(plain(v) for v in x)
    if isinstance(x, list):
        return [plain(v) for v in x]
    if isinstance(x, dict):
        return {k: plain(v) for k, v in x.items()}
    return x


def wrap(res, tags):
    if isinstance(res, np.ndarray) and not isinstance(res, TagArray) and res.dtype != object:
        return TagArray(res, tags)
    if isinstance(res, TagArray):
        res.tags |= tags
        return res
    if isinstance(res, tuple):
        return tuple(wrap(r, tags) for r in res)
    return res


def wrap_deep(res, tags):
    if isinstance(res, dict):
        for k, v in res.items():
            res[k] = wrap_deep(v, tags)
        return res
    if isinstance(res, list):
        return [wrap_deep(v, tags) for v in res]
    if isinstance(res, tuple):
        return tuple(wrap_deep(v, tags) for v in res)
    return wrap(res, tags)


def _caller():
    """(model file, function) of the SISEPUEDE model code that made the call."""
    for fr in inspect.stack()[2:12]:
        f = fr.filename
        if "/sisepuede/models/" in f:
            return Path(f).stem, fr.function
    return "", ""


def patch_numpy():
    """New arrays (np.zeros, then filled by item) must be able to collect tags, and np.array / np.asarray over
    tagged values keep them."""
    def from_models() -> bool:      # SISEPUEDE's model and utility code; pandas and NumPy internals keep plain arrays
        f = sys._getframe(2).f_code.co_filename
        return "/sisepuede/models/" in f or "/sisepuede/utilities/" in f

    def blank(name):
        f = _NP[name]
        return lambda *a, **k: wrap(f(*a, **k), set()) if from_models() else f(*a, **k)

    def carry(name):
        f = _NP[name]
        return lambda obj=None, *a, **k: (wrap(f(plain(obj), *a, **k), tags_of(obj) | frame_tags(obj)) if from_models()
                                          else f(obj, *a, **k))

    for name in ("zeros", "ones", "empty", "full"):
        setattr(np, name, blank(name))
    for name in ("array", "asarray"):
        setattr(np, name, carry(name))


# Functions treated as one step: they get plain arrays and their result carries the tags of every argument.
# Either they check `type(x) == np.ndarray` (a TagArray fails it) or they call a solver that returns new arrays
# (the land use transition adjustment, QAdjuster).
STRICT = [("sisepuede.models.circular_economy", "CircularEconomy", "fod"),
          ("sisepuede.models.circular_economy", "CircularEconomy", "get_waso_historical_solid_waste"),
          ("sisepuede.models.afolu", "AFOLU", "qadj_adjust_transitions"),
          # one loop per period where land use, crops, livestock and pasture are adjusted together: everything in
          # relates to everything out (they are coupled in SISEPUEDE)
          ("sisepuede.models.afolu", "AFOLU", "project_integrated_land_use")]


def patch_strict():
    import importlib
    for module, cls_name, name in STRICT:
        cls = getattr(importlib.import_module(module), cls_name)
        f = getattr(cls, name)

        def call(self, *a, _f=f, **k):
            return wrap_deep(_f(self, *plain(a), **plain(k)), tags_of(a) | tags_of(k))
        setattr(cls, name, call)


NEMOMOD = "NemoMod (electricity optimisation)"


def install(ma, writes: list, reads: list):
    """Patch ModelAttributes so reads are tagged and writes are recorded."""
    cls = type(ma)
    read, write = cls.extract_model_variable, cls.array_to_df

    def name_of(modvar):
        return modvar.name if hasattr(modvar, "name") else str(modvar)

    def extract(self, df, modvar, *a, **kw):
        res = read(self, df, modvar, *a, **kw)
        model, func = _caller()
        reads.append({"variable": name_of(modvar), "model": model, "function": func})
        if isinstance(res, np.ndarray) and res.dtype != object:
            return TagArray(res, {name_of(modvar)})
        return res

    def to_df(self, arr, modvar, *a, **kw):
        model, func = _caller()
        writes.append({"target": name_of(modvar), "tags": sorted(tags_of(arr)), "model": model, "function": func})
        if isinstance(arr, TagArray):
            # the array now is that variable: what is computed from it later in the code comes from it, so
            # in-between outputs (vehicle-km before fuel demand and emissions) sit on the chain. When the array
            # written is another one times a number (a unit conversion), that one is the variable too.
            arr.tags.add(name_of(modvar))
            p = getattr(arr, "parent", None)
            if p is not None:
                p.tags.add(name_of(modvar))
        return write(self, plain(arr), modvar, *a, **kw)

    cls.extract_model_variable, cls.array_to_df = extract, to_df

    # every other ModelAttributes helper (merge to all categories, unit conversion …): a result computed from a
    # tagged array keeps its tags, including arrays inside a returned dict, list or tuple
    def carry(f):
        def call(self, *a, **k):
            tags = tags_of(a) | tags_of(k)
            res = f(self, *a, **k)
            return wrap_deep(res, tags) if tags else res
        return call

    for name, f in list(vars(cls).items()):
        if callable(f) and not name.startswith("__") and name not in ("extract_model_variable", "array_to_df"):
            setattr(cls, name, carry(f))


def patch_pandas(field_to_variable: dict, reads: list):
    """Model code that reads columns straight from a DataFrame (df[fields].to_numpy(), .values) gets an array
    tagged with the model variables of those columns, and the read is recorded. np.array(df[fields]) is covered
    by frame_tags, which reads a DataFrame's columns."""
    FIELD_TO_VARIABLE.update(field_to_variable)
    # the Socioeconomic model hands the growth rates to the other models in an internal frame (not model fields)
    FIELD_TO_VARIABLE.update({"vec_rates_gdp": "GDP", "vec_rates_gdp_per_capita": "GDP per Capita"})
    def from_models() -> bool:
        f = sys._getframe(2).f_code.co_filename
        return "/sisepuede/models/" in f or "/sisepuede/utilities/" in f

    def tagged(obj, res):
        cols = [obj.name] if isinstance(obj, pd.Series) else list(obj.columns)
        tags = {field_to_variable[c] for c in cols if isinstance(c, str) and c in field_to_variable}
        if not tags or not isinstance(res, np.ndarray) or res.dtype == object:
            return res
        model, func = _caller()
        reads.extend({"variable": t, "model": model, "function": func} for t in tags)
        return TagArray(res, tags)

    for cls in (pd.DataFrame, pd.Series):
        to_numpy, values = cls.to_numpy, cls.values

        def to_np(self, *a, _f=to_numpy, **k):
            res = _f(self, *a, **k)
            return tagged(self, res) if from_models() else res

        def vals(self, _p=values):
            res = _p.fget(self)
            return tagged(self, res) if from_models() else res

        cls.to_numpy, cls.values = to_np, property(vals)


def patch_other_writers(writes: list):
    """AFOLU writes the land use conversion matrices with its own function (modvar=…), not array_to_df."""
    from sisepuede.models.afolu import AFOLU
    f = AFOLU.format_transition_matrix_as_input_dataframe

    def call(self, arr, *a, _f=f, **k):
        modvar = k.get("modvar")
        if modvar is not None:
            writes.append({"target": modvar.name if hasattr(modvar, "name") else str(modvar),
                           "tags": sorted(tags_of(arr)), "model": "afolu", "function": "project"})
        return _f(self, plain(arr), *a, **k)
    AFOLU.format_transition_matrix_as_input_dataframe = call


def run(input_csv: Path, electricity: bool = False):
    warnings.filterwarnings("ignore")
    from sisepuede.manager.sisepuede_file_structure import SISEPUEDEFileStructure
    from sisepuede.manager.sisepuede_models import SISEPUEDEModels
    ma = SISEPUEDEFileStructure(initialize_directories=False).model_attributes
    df = pd.read_csv(input_csv)
    f2v = ma.dict_variable_fields_to_model_variables
    missing = [f for f in ma.all_variable_fields_input if f not in df.columns]
    df = pd.concat([df, pd.DataFrame({f: [float(ma.get_variable(f2v[f]).default_value or 0)] * len(df)
                                      for f in missing})], axis=1)
    writes, reads = [], []
    install(ma, writes, reads)
    patch_numpy()
    patch_strict()
    patch_pandas(f2v, reads)
    patch_other_writers(writes)
    log = logging.getLogger("trace")
    log.setLevel(logging.WARNING)
    log.addHandler(logging.StreamHandler(sys.stdout))
    models = SISEPUEDEModels(ma, allow_electricity_run=electricity, initialize_julia=electricity, logger=log,
                             fp_nemomod_reference_files=str(NEMOMOD_REF) if electricity else None,
                             fp_julia=str(Path(sys.modules["sisepuede"].__file__).parent / "julia") if electricity else None,
                             fp_nemomod_temp_sqlite_db=str(OUT / "nemomod_trace.sqlite") if electricity else None)
    models.project(df, include_electricity_in_energy=electricity)
    return writes, reads, missing


def edges(writes: list, reads: list) -> pd.DataFrame:
    """Traced edges, plus the electricity model as one black box (plan rule 5): every variable the electricity
    model reads goes into the NemoMod node; every variable it writes comes out of it (results are read back from
    NemoMod's database, so their own tags only show the Python steps around the optimisation)."""
    c = Counter((t, w["target"], w["model"], w["function"]) for w in writes for t in w["tags"] if t != w["target"])
    c.update((r["variable"], NEMOMOD, r["model"], r["function"]) for r in reads if r["model"] == "energy_production")
    c.update((NEMOMOD, w["target"], w["model"], w["function"]) for w in writes if w["model"] == "energy_production")
    return pd.DataFrame([{"source": s, "target": t, "model": m, "function": f, "n": n} for (s, t, m, f), n in c.items()])


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    inp, run_name = Path(args[0]), args[1] if len(args) > 1 else "run_2026_05_30"
    writes, reads, missing = run(inp, electricity="--electricity" in sys.argv)
    e = edges(writes, reads)
    e.to_csv(OUT / f"{run_name}_edges_traced.csv", index=False)
    pd.DataFrame([{**w, "n_tags": len(w["tags"]), "tags": " | ".join(w["tags"])} for w in writes]) \
        .to_csv(OUT / f"{run_name}_trace_log.csv", index=False)
    targets = {w["target"] for w in writes}
    untagged = {w["target"] for w in writes if not w["tags"]} - {t for t in e.target}
    print(f"input fields set to default: {len(missing)}")
    print(f"writes: {len(writes)} · variables written: {len(targets)} · edges: {len(e)} "
          f"({e[['source', 'target']].drop_duplicates().shape[0]} distinct pairs)")
    print(f"variables written with no incoming edge: {len(untagged)}")
    for t in sorted(untagged)[:15]:
        print("   ", t)
