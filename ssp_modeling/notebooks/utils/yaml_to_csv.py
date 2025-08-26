from pathlib import Path
from typing import Iterable, List, Optional, Dict, Tuple, Union
import re
import yaml
import pandas as pd
import numpy as np


class GenerateTransformationsReport:
    """
    Parse SISEPUEDE transformation YAMLs and strategy definitions using a single,
    robust collector for *default* transformation codes (base TX codes).
    """

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _match_suffix(stem: str, suffixes: Iterable[str], seps: Iterable[str]) -> Optional[str]:
        """Return matched suffix if filename stem ends with it (with/without a separator)."""
        for suf in suffixes:
            if stem.endswith(suf):
                return suf
            for sep in seps:
                if stem.endswith(sep + suf):
                    return suf
        return None

    @staticmethod
    def _strip_strategy_suffix_from_code(
        code: str,
        suffix: str,
        seps: Iterable[str] = ("_", "-", ":")
    ) -> str:
        """
        Strip trailing STRATEGY suffix from a code for a known suffix.
        Matches:
          ..._STRATEGY_<suffix>, ...-STRATEGY-<suffix>, ...:STRATEGY:<suffix>,
          and fallback: ..._<suffix>, ...-<suffix>, ...:<suffix>
        """
        for a in seps:
            for b in seps:
                tail = f"{a}STRATEGY{b}{suffix}"
                if code.endswith(tail):
                    return code[: -len(tail)]
        for a in seps:
            tail = f"{a}{suffix}"
            if code.endswith(tail):
                return code[: -len(tail)]
        return code

    @staticmethod
    def _strip_any_strategy_tail(code: str, known_suffixes: Iterable[str], seps: Iterable[str]) -> str:
        """
        Strip known suffix patterns first, then a generic STRATEGY tail if present.
        This prevents default set from including '..._STRATEGY_XXX' variants.
        """
        base = code
        # Try known suffixes
        for sfx in known_suffixes:
            new_base = GenerateTransformationsReport._strip_strategy_suffix_from_code(base, sfx, seps)
            if new_base != base:
                base = new_base
                break  # assume only one strategy tail
        if base != code:
            return base

        # Generic patterns like ...[_-: ]STRATEGY[_-: ]<alnum>+
        # e.g., TX:AGRC:DEC_EXPORTS_STRATEGY_NDC or TX:...-STRATEGY-NZ
        generic_pattern = re.compile(r"([_\-:])STRATEGY([_\-:])[A-Za-z0-9]+$")
        if generic_pattern.search(base):
            return generic_pattern.sub("", base)

        return base

    # -------------------------
    # Shared: collect defaults (no strategy suffix in filename, TX: codes only)
    # -------------------------
    @staticmethod
    def collect_default_transformation_codes(
        folder_path: str,
        strategy_suffixes: List[str],
        recursive: bool = True,
        suffix_separators: Iterable[str] = ("_", "-", ":"),
        require_tx_prefix: bool = True,
    ) -> List[str]:
        """
        Return a sorted list of *base* transformation codes from YAMLs that do NOT end
        with any strategy suffix in the FILENAME. Codes are read from
        `identifiers.transformation_code` (fallback: filename stem), then any strategy
        tail is stripped (even if not in `strategy_suffixes`), and non-TX codes are dropped.
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
            # Skip strategy-specific YAMLs by filename
            if GenerateTransformationsReport._match_suffix(stem, strategy_suffixes, suffix_separators) is not None:
                continue

            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception:
                data = None

            # Extract code
            if isinstance(data, dict):
                code = (data.get("identifiers") or {}).get("transformation_code") or stem
            else:
                code = stem
            code = str(code).strip()

            # Strip any strategy tail from the code itself (robust)
            base_code = GenerateTransformationsReport._strip_any_strategy_tail(
                code, known_suffixes=strategy_suffixes, seps=suffix_separators
            )

            # Keep only TX: codes (drops config files like 'config_general')
            if require_tx_prefix and not base_code.startswith("TX:"):
                continue

            defaults.add(base_code)

        # Deduplicate and sort
        return sorted(defaults)

    # -------------------------
    # 1) Parameters table (skip strategy YAMLs by passing suffixes)
    # -------------------------
    @staticmethod
    def collect_transformations_params(
        folder_path: str,
        exclude_suffixes: Optional[List[str]] = None,
        recursive: bool = True,
        include_file_path: bool = False,
        require_tx_prefix: bool = True,
        exclude_file_stems: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Scan a folder for .yaml/.yml files, skip files whose *basename* ends with any
        suffix in `exclude_suffixes`, and build a DataFrame with one row per YAML:
        - `transformation_code` from identifiers.transformation_code
        - one column per parameter under `parameters` (union across all YAMLs)

        New:
        - require_tx_prefix: if True, drop YAMLs whose code doesn't start with "TX:"
        - exclude_file_stems: basenames (without extension) to skip (case-insensitive),
            defaults to ("config_general",)
        """
        if exclude_suffixes is None:
            exclude_suffixes = []
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

        # Case-insensitive sets for quick checks
        exclude_suffixes_ci = {s.lower() for s in exclude_suffixes}
        exclude_stems_ci = {s.lower() for s in exclude_file_stems}

        def should_skip_file(p: Path) -> bool:
            stem_lower = p.stem.lower()
            # 1) skip by explicit stems (e.g., "config_general")
            if stem_lower in exclude_stems_ci:
                return True
            # 2) skip by suffixes (e.g., *_NDC, *_NZ)
            if any(stem_lower.endswith(suf) for suf in exclude_suffixes_ci):
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

            # New filter: require TX: prefix if requested
            if require_tx_prefix and not tx_code.startswith("TX:"):
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

        df = df.reindex(columns=col_order)
        df = df.replace({None: np.nan})
        return df


    # -------------------------
    # 2) Presence matrix from strategy_definitions.csv
    # -------------------------
    @staticmethod
    def build_strategy_presence_from_csv(
        csv_path: str,
        strategy_suffixes: List[str],
        *,
        default_codes: Optional[List[str]] = None,
        folder_path_for_defaults: Optional[str] = None,
        recursive: bool = True,
        suffix_separators: Iterable[str] = ("_", "-", ":"),
        col_transformation_spec: str = "transformation_specification",
        return_unknowns: bool = False
    ) -> Union[pd.DataFrame, Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Create a presence matrix:
          rows   = base default transformation codes (TX:...)
          cols   = one boolean column per strategy suffix (strategy_{suffix})
          values = True iff CSV includes that transformation with the matching suffix

        Pass `default_codes` or let it derive from `folder_path_for_defaults`.
        """
        if default_codes is None:
            if not folder_path_for_defaults:
                raise ValueError("Provide either `default_codes` or `folder_path_for_defaults`.")
            default_codes = GenerateTransformationsReport.collect_default_transformation_codes(
                folder_path=folder_path_for_defaults,
                strategy_suffixes=strategy_suffixes,
                recursive=recursive,
                suffix_separators=suffix_separators,
                require_tx_prefix=True,
            )

        # Normalize/defaults set
        default_codes = sorted({str(c).strip() for c in default_codes if str(c).strip().startswith("TX:")})
        defaults_set = set(default_codes)

        # Read CSV
        df = pd.read_csv(csv_path)
        if col_transformation_spec not in df.columns:
            raise ValueError(f"Column '{col_transformation_spec}' not found in {csv_path}")

        # Init presence dict
        presence: Dict[str, Dict[str, bool]] = {code: {s: False for s in strategy_suffixes} for code in default_codes}
        unknown_rows = []

        # Parse each spec cell
        for _, row in df.iterrows():
            spec = row.get(col_transformation_spec)
            if pd.isna(spec) or not isinstance(spec, str) or not spec.strip():
                continue
            items = [x.strip() for x in spec.split("|") if x.strip()]

            for code in items:
                # Try known suffixes first
                matched = False
                for sfx in strategy_suffixes:
                    base = GenerateTransformationsReport._strip_strategy_suffix_from_code(code, sfx, seps=suffix_separators)
                    if base != code:
                        matched = True
                        if base in defaults_set:
                            presence[base][sfx] = True
                        else:
                            unknown_rows.append({"seen_code": code, "base_after_strip": base, "strategy_suffix": sfx})
                        break
                if matched:
                    continue

                # If no known suffix matched, also try generic STRATEGY tail for robustness
                generic_base = GenerateTransformationsReport._strip_any_strategy_tail(code, known_suffixes=[], seps=suffix_separators)
                if generic_base != code:
                    # Generic stripped; cannot infer which suffix it was, so we won't mark presence
                    # but we can record unknown for QA
                    unknown_rows.append({"seen_code": code, "base_after_strip": generic_base, "strategy_suffix": None})

        # Build matrix
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

    @staticmethod
    def collect_strategy_transformations_params(
        folder_path: str,
        strategy_suffixes: List[str],
        recursive: bool = True,
        suffix_separators: Iterable[str] = ("_", "-", ":"),
        include_file_path: bool = False,
        require_tx_prefix: bool = True,
        case_insensitive: bool = False,
    ) -> pd.DataFrame:
        """
        Collect parameters for *strategy-specific* transformations (files whose filename stem
        ends with one of the provided strategy suffixes).

        Output columns:
        - strategy_name                   (the matched suffix, e.g., 'NDC', 'NDC_2')
        - transformation_code             (as-is from YAML identifiers.transformation_code; no stripping)
        - default_transformation_code     (code with STRATEGY_{suffix} stripped for mapping to the default)
        - <parameter columns>             (one column per parameter found under 'parameters')

        Notes:
        - Matches stems like '..._STRATEGY_NDC', '...-STRATEGY-NDC', '...:STRATEGY:NDC', or simply '..._NDC'.
        - If `require_tx_prefix` is True, non 'TX:' codes are skipped.
        - If suffixes overlap (e.g., 'NDC' and 'NDC_2'), the longest suffix wins.
        """
        root = Path(folder_path)

        # Order suffixes by length (desc) so 'NDC_2' wins over 'NDC'
        sfx_order = sorted(strategy_suffixes, key=len, reverse=True)
        sfx_check = [s.lower() for s in sfx_order] if case_insensitive else sfx_order

        # Gather YAMLs
        paths: List[Path] = []
        if recursive:
            paths.extend(root.rglob("*.yaml")); paths.extend(root.rglob("*.yml"))
        else:
            paths.extend(root.glob("*.yaml"));  paths.extend(root.glob("*.yml"))

        rows = []
        all_param_keys: set[str] = set()

        for p in paths:
            stem = p.stem
            chk_stem = stem.lower() if case_insensitive else stem

            # Only keep files whose stem ends with one of the suffixes
            matched_suffix = GenerateTransformationsReport._match_suffix(chk_stem, sfx_check, suffix_separators)
            if matched_suffix is None:
                continue

            # Normalize suffix back to original case from user-provided list
            for orig in sfx_order:
                if (orig.lower() if case_insensitive else orig) == matched_suffix:
                    strategy_name = orig
                    break
            else:
                strategy_name = matched_suffix  # fallback (shouldn't happen)

            # Parse YAML
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue

            # Extract codes
            identifiers = data.get("identifiers") or {}
            tx_code = identifiers.get("transformation_code") or stem
            tx_code = str(tx_code).strip()

            if require_tx_prefix and not tx_code.startswith("TX:"):
                continue

            default_code = GenerateTransformationsReport._strip_strategy_suffix_from_code(
                tx_code, strategy_name, seps=suffix_separators
            )

            # Collect parameters
            params = data.get("parameters") or {}
            if not isinstance(params, dict):
                params = {}

            all_param_keys.update(params.keys())

            row = {
                "strategy_name": strategy_name,
                "transformation_code": tx_code,
                "default_transformation_code": default_code,
                **params,
            }
            if include_file_path:
                row["file_path"] = str(p.relative_to(root))

            rows.append(row)

        # Build DataFrame with union of parameter columns (stable order)
        base_cols = ["strategy_name", "transformation_code", "default_transformation_code"]
        if include_file_path:
            base_cols.append("file_path")
        col_order = base_cols + sorted(all_param_keys)

        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(columns=col_order)

        df = df.reindex(columns=col_order).replace({None: np.nan})
        # Helpful stable sort
        df = df.sort_values(["strategy_name", "default_transformation_code", "transformation_code"], kind="mergesort")
        return df
