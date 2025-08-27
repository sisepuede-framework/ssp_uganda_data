from pathlib import Path
from typing import Iterable, List, Optional, Dict, Tuple, Union
import re
import yaml
import pandas as pd
import numpy as np


class GenerateTransformationsReport:
    """
    Parse SISEPUEDE transformation YAMLs and strategy definitions.

    RULES:
    - Any code or filename that ends with ...<sep>STRATEGY<sep><suffix> (sep in {'_', '-', ':'})
      is a *custom/strategy-specific* transformation and MUST NOT be part of the default set.
    - Default (non-custom) collectors NEVER accept a suffix list; they exclude *all* STRATEGY_*.
    - Strategy-driven methods accept suffix lists to decide which strategies to include,
      but they always rely on the default set that excludes STRATEGY_*.
    """

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _has_any_strategy_tail(text: str) -> bool:
        """
        Return True if `text` ends with ...<sep>STRATEGY<sep><suffix> for ANY suffix.
        Accepts letters, digits, underscore, hyphen in the suffix (e.g., NDC_2).
        """
        return bool(re.search(r"([_\-:])STRATEGY([_\-:])[A-Za-z0-9_-]+$", str(text), flags=re.IGNORECASE))


    @staticmethod
    def _endswith_strategy_tail(
        text: str,
        suffixes: Iterable[str],
        seps: Iterable[str] = ("_", "-", ":"),
        case_insensitive: bool = False,
    ) -> Optional[str]:
        """
        Strict detector for specific suffixes:
        Return the matched suffix if `text` ends with one of the patterns:
          <sep>STRATEGY<sep><suffix>
        e.g., "..._STRATEGY_NDC", "...-STRATEGY-NZ", "...:STRATEGY:NDC_2"
        """
        if case_insensitive:
            text_cmp = text.lower()
            STRAT = "strategy"
            suffixes_cmp = [s.lower() for s in suffixes]
        else:
            text_cmp = text
            STRAT = "STRATEGY"
            suffixes_cmp = list(suffixes)

        for i, sfx in enumerate(suffixes_cmp):
            for a in seps:
                for b in seps:
                    if text_cmp.endswith(f"{a}{STRAT}{b}{sfx}"):
                        # Return suffix in the original casing provided by caller
                        return list(suffixes)[i]
        return None

    @staticmethod
    def _strip_strategy_suffix_from_code(
        code: str,
        suffix: str,
        seps: Iterable[str] = ("_", "-", ":"),
    ) -> str:
        """
        Strip trailing STRATEGY suffix from a code for a known suffix.
        Matches ONLY:
          ..._STRATEGY_<suffix>, ...-STRATEGY-<suffix>, ...:STRATEGY:<suffix>
        """
        for a in seps:
            for b in seps:
                tail = f"{a}STRATEGY{b}{suffix}"
                if code.endswith(tail):
                    return code[: -len(tail)]
        return code

    # -------------------------
    # Defaults: collect transformation codes (EXCLUDES ALL STRATEGY_*)
    # -------------------------
    @staticmethod
    def collect_default_transformation_codes(
        folder_path: str,
        recursive: bool = True,
        require_tx_prefix: bool = True,
    ) -> List[str]:
        """
        Return a sorted list of base/default transformation codes from YAMLs.

        EXCLUDES customs by:
          - filename stem ending with ...STRATEGY_*   (any suffix)
          - code (identifiers.transformation_code) ending with ...STRATEGY_*   (any suffix)
        """
        root = Path(folder_path)
        paths: List[Path] = []
        if recursive:
            paths.extend(root.rglob("*.yaml")); paths.extend(root.rglob("*.yml"))
        else:
            paths.extend(root.glob("*.yaml"));  paths.extend(root.glob("*.yml"))

        defaults: set[str] = set()
        for p in paths:
            stem = p.stem

            # Skip custom by filename (any STRATEGY_* tail)
            if GenerateTransformationsReport._has_any_strategy_tail(stem):
                continue

            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception:
                data = None

            if isinstance(data, dict):
                code = (data.get("identifiers") or {}).get("transformation_code") or stem
            else:
                code = stem
            code = str(code).strip()

            # Skip custom by code (any STRATEGY_* tail)
            if GenerateTransformationsReport._has_any_strategy_tail(code):
                continue

            if require_tx_prefix and not code.startswith("TX:"):
                continue

            defaults.add(code)

        return sorted(defaults)

    # -------------------------
    # 1) Parameters for DEFAULT (non-custom) transformations
    # -------------------------
    @staticmethod
    def collect_transformations_params(
        folder_path: str,
        recursive: bool = True,
        include_file_path: bool = False,
        require_tx_prefix: bool = True,
        exclude_file_stems: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Build a DataFrame of DEFAULT (non-custom) transformations:
          - transformation_code
          - <parameter columns>

        Customs are excluded if filename OR code ends with ANY ...STRATEGY_*.

        `exclude_file_stems`: explicit basenames to skip (e.g., ["config_general"]).
        """
        if exclude_file_stems is None:
            exclude_file_stems = ["config_general"]

        folder = Path(folder_path)
        yaml_paths: List[Path] = []
        if recursive:
            yaml_paths.extend(folder.rglob("*.yml"))
            yaml_paths.extend(folder.rglob("*.yaml"))
        else:
            yaml_paths.extend(folder.glob("*.yml"))
            yaml_paths.extend(folder.glob("*.yaml"))

        exclude_stems_ci = {s.lower() for s in exclude_file_stems}

        def should_skip_file(p: Path) -> bool:
            stem = p.stem
            if stem.lower() in exclude_stems_ci:
                return True
            # Strict: skip if filename shows ANY STRATEGY tail
            if GenerateTransformationsReport._has_any_strategy_tail(stem):
                return True
            return False

        yaml_paths = [p for p in yaml_paths if not should_skip_file(p)]

        rows = []
        all_param_keys = set()

        for p in yaml_paths:
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            identifiers = data.get("identifiers", {})
            tx_code = identifiers.get("transformation_code") if isinstance(identifiers, dict) else None
            if not tx_code:
                tx_code = p.stem
            tx_code = str(tx_code).strip()

            if require_tx_prefix and not tx_code.startswith("TX:"):
                continue
            # Strict: skip if CODE shows ANY STRATEGY tail
            if GenerateTransformationsReport._has_any_strategy_tail(tx_code):
                continue

            params = data.get("parameters", {})
            if not isinstance(params, dict):
                params = {}

            all_param_keys.update(params.keys())

            row = {"transformation_code": tx_code, **params}
            if include_file_path:
                row["file_path"] = str(p.relative_to(folder))
            rows.append(row)

        col_order = ["transformation_code"] + (["file_path"] if include_file_path else []) + sorted(all_param_keys)
        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(columns=col_order)

        df = df.reindex(columns=col_order).replace({None: np.nan})
        return df

    # -------------------------
    # 2) Presence matrix from strategy_definitions.csv (requires suffix list)
    # -------------------------
    @staticmethod
    def build_strategy_presence_from_csv(
        csv_path: str,
        strategy_suffixes: List[str],
        *,
        default_codes: Optional[List[str]] = None,
        folder_path_for_defaults: Optional[str] = None,
        recursive: bool = True,
        col_transformation_spec: str = "transformation_specification",
        return_unknowns: bool = False
    ) -> Union[pd.DataFrame, Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Create a presence matrix:
          rows   = default (non-custom) transformation codes (TX:...)
          cols   = one boolean column per strategy suffix (strategy_{suffix})
          values = True iff CSV includes that transformation with the matching STRATEGY_{suffix}

        - Derives defaults from folder if not provided (excluding ALL STRATEGY_*).
        - Only entries with explicit STRATEGY_{suffix} are considered strategy-specific.
        """
        # Derive defaults if not provided (and enforce non-custom)
        if default_codes is None:
            if not folder_path_for_defaults:
                raise ValueError("Provide either `default_codes` or `folder_path_for_defaults`.")
            default_codes = GenerateTransformationsReport.collect_default_transformation_codes(
                folder_path=folder_path_for_defaults,
                recursive=recursive,
                require_tx_prefix=True,
            )

        # Normalize & guarantee non-custom defaults set
        default_codes = sorted({
            str(c).strip()
            for c in default_codes
            if str(c).strip().startswith("TX:") and not GenerateTransformationsReport._has_any_strategy_tail(c)
        })
        defaults_set = set(default_codes)

        df = pd.read_csv(csv_path)
        if col_transformation_spec not in df.columns:
            raise ValueError(f"Column '{col_transformation_spec}' not found in {csv_path}")

        presence: Dict[str, Dict[str, bool]] = {code: {s: False for s in strategy_suffixes} for code in default_codes}
        unknown_rows = []

        for _, row in df.iterrows():
            spec = row.get(col_transformation_spec)
            if pd.isna(spec) or not isinstance(spec, str) or not spec.strip():
                continue
            items = [x.strip() for x in spec.split("|") if x.strip()]

            for code in items:
                # Detect which suffix this code belongs to (must include STRATEGY token)
                sfx = GenerateTransformationsReport._endswith_strategy_tail(code, strategy_suffixes, case_insensitive=True)
                if not sfx:
                    continue  # not a strategy-specific entry for our suffixes
                base = GenerateTransformationsReport._strip_strategy_suffix_from_code(code, sfx)
                if base in defaults_set:
                    presence[base][sfx] = True
                else:
                    unknown_rows.append({"seen_code": code, "base_after_strip": base, "strategy_suffix": sfx})

        rows = []
        for code in sorted(defaults_set):
            row = {"transformation_code": code}
            for sfx in strategy_suffixes:
                row[f"strategy_{sfx}"] = presence[code][sfx]
            rows.append(row)
        matrix = pd.DataFrame(rows)

        if return_unknowns:
            unknown_df = pd.DataFrame(unknown_rows, columns=["seen_code", "base_after_strip", "strategy_suffix"])
            return matrix, unknown_df

        return matrix

    # -------------------------
    # 3) Parameters for CUSTOM (strategy-specific) transformations only
    # -------------------------
    @staticmethod
    def collect_strategy_transformations_params(
        folder_path: str,
        strategy_suffixes: List[str],
        recursive: bool = True,
        suffix_separators: Iterable[str] = ("_", "-", ":"),
        include_file_path: bool = False,
        require_tx_prefix: bool = True,
    ) -> pd.DataFrame:
        """
        Collect parameters for *custom* transformations (files OR codes that end with 'STRATEGY_{suffix}').

        Output columns:
        - strategy_name
        - transformation_code             (as-is from YAML identifiers.transformation_code; no stripping)
        - default_transformation_code     (code with STRATEGY_{suffix} stripped)
        - <parameter columns>
        """
        root = Path(folder_path)

        # deterministic suffix resolution (longest first)
        sfx_order = sorted(strategy_suffixes, key=len, reverse=True)

        paths: List[Path] = []
        if recursive:
            paths.extend(root.rglob("*.yaml")); paths.extend(root.rglob("*.yml"))
        else:
            paths.extend(root.glob("*.yaml"));  paths.extend(root.glob("*.yml"))

        rows = []
        all_param_keys: set[str] = set()

        for p in paths:
            stem = p.stem

            # First try to match by FILENAME (case-insensitive)
            matched_suffix = GenerateTransformationsReport._endswith_strategy_tail(
                stem, sfx_order, seps=suffix_separators, case_insensitive=True
            )

            # Parse YAML so we can also match by CODE
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            identifiers = data.get("identifiers") or {}
            tx_code = str(identifiers.get("transformation_code") or stem).strip()
            if require_tx_prefix and not tx_code.startswith("TX:"):
                continue

            # If filename didn't match, try to match by CODE (case-insensitive)
            if matched_suffix is None:
                matched_suffix = GenerateTransformationsReport._endswith_strategy_tail(
                    tx_code, sfx_order, seps=suffix_separators, case_insensitive=True
                )

            # If neither matched, this YAML is not a custom for the requested suffixes
            if matched_suffix is None:
                continue

            # Strip to base default code using the matched suffix (case-sensitive strip)
            default_code = GenerateTransformationsReport._strip_strategy_suffix_from_code(
                tx_code, matched_suffix, seps=suffix_separators
            )

            params = data.get("parameters") or {}
            if not isinstance(params, dict):
                params = {}

            all_param_keys.update(params.keys())

            row = {
                "strategy_name": matched_suffix,
                "transformation_code": tx_code,
                "default_transformation_code": default_code,
                **params,
            }
            if include_file_path:
                row["file_path"] = str(p.relative_to(root))
            rows.append(row)

        base_cols = ["strategy_name", "transformation_code", "default_transformation_code"]
        if include_file_path:
            base_cols.append("file_path")
        col_order = base_cols + sorted(all_param_keys)

        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(columns=col_order)

        df = df.reindex(columns=col_order).replace({None: np.nan})
        df = df.sort_values(["strategy_name", "default_transformation_code", "transformation_code"], kind="mergesort")
        return df
