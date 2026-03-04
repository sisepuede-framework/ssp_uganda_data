"""
Cost–benefit analysis (CBA) pipeline for tornado and whirlpool processes.

Country-agnostic: pass --country, --path-run-output, --path-cb-output (and optional
strategy filters) so the same script works across repos.

Usage:
  From project root with defaults (e.g. uganda):
    python ssp_modeling/cb/tornado_plot/scr/cba_tornado_whirlpool.py both

  With explicit parameters (for any country/repo):
    python ssp_modeling/cb/tornado_plot/scr/cba_uganda_tornado_whirlpool.py both \\
      --country uganda \\
      --path-run-output ssp_modeling/ssp_run_output/sisepuede_summary_results_run_... \\
      --path-cb-output ssp_modeling/cb/tornado_plot/data/input

  With strategy selection (BASE is always included):
    python ... cba_tornado_whirlpool.py both --tornado-strategy "AGRC:DEC_CH4_RICE" --whirlpool-strategy "WHIRLPOOL:TX:..."
"""

from costs_benefits_ssp.cb_calculate import CostBenefits
import argparse
import pathlib
import pandas as pd


STRATEGY_CODE_BASE = "BASE"

# Defaults when not passed via CLI (run from project root)
_DEFAULT_COUNTRY = "uganda"
_DEFAULT_PATH_RUN_OUTPUT = (
    "ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2026-02-18T21;36;42.734194"
)
_DEFAULT_PATH_CB_OUTPUT = "ssp_modeling/cb/tornado_plot/data/input"


def _build_config(args: argparse.Namespace) -> dict:
    """Build path and process config from args (and defaults)."""
    root = pathlib.Path(args.project_root).resolve()
    path_run = root / args.path_run_output
    path_cb_out = root / args.path_cb_output
    country = args.country

    process_config = {
        "tornado": {
            "run_subdir": "tornado",
            "output_subdir": "tornado",
            "output_csv_name": f"cba_results_ssp_modeling_tornado_{country}.csv",
        },
        "whirlpool": {
            "run_subdir": "whirlpool",
            "output_subdir": "whirlpool",
            "output_csv_name": f"cba_results_ssp_modeling_whirlpool_{country}.csv",
        },
    }
    return {
        "root": root,
        "path_run_output": path_run,
        "path_cb_output": path_cb_out,
        "country": country,
        "process_config": process_config,
        "cb_definition_path": root / "ssp_modeling/cb/cb_cost_factors/cb_config_params.xlsx",
    }


# -----------------------------------------------------------------------------
# Pipeline logic
# -----------------------------------------------------------------------------


def run_cba_pipeline(
    process_name: str,
    run_strategy_by_process: dict,
    config: dict,
) -> None:
    """
    Run the full CBA pipeline for one process (tornado or whirlpool).

    Parameters
    ----------
    process_name : str
        One of "tornado" or "whirlpool".
    run_strategy_by_process : dict
        Optional strategy selection: {"tornado": None | str | list, "whirlpool": None | str | list}.
        None = all strategies; string or list = only those strategy_codes (BASE is always added).
    config : dict
        From _build_config(): path_run_output, path_cb_output, country, process_config, cb_definition_path.
    """
    process_config = config["process_config"]
    if process_name not in process_config:
        raise ValueError(
            f"Unknown process '{process_name}'. Must be one of: {list(process_config.keys())}"
        )

    cfg = process_config[process_name]
    ssp_run_dir = config["path_run_output"] / cfg["run_subdir"]
    cb_output_dir = config["path_cb_output"] / cfg["output_subdir"]
    output_csv_name = cfg["output_csv_name"]
    country = config["country"]

    country_csv = ssp_run_dir / f"{country}.csv"
    att_primary_csv = ssp_run_dir / "ATTRIBUTE_PRIMARY.csv"
    att_strategy_csv = ssp_run_dir / "ATTRIBUTE_STRATEGY.csv"

    for p in (country_csv, att_primary_csv, att_strategy_csv):
        if not p.exists():
            raise FileNotFoundError(f"Required input not found: {p}")

    ssp_data = pd.read_csv(country_csv)
    att_primary = pd.read_csv(att_primary_csv)
    att_strategy = pd.read_csv(att_strategy_csv)

    # Optional: filter to one or more strategies for this process (BASE always included)
    strategy_filter = run_strategy_by_process.get(process_name)
    if strategy_filter is not None:
        if isinstance(strategy_filter, str):
            chosen_codes = [strategy_filter]
        else:
            chosen_codes = list(strategy_filter)
        strategy_codes = set(chosen_codes)
        strategy_codes.add(STRATEGY_CODE_BASE)

        before_n = len(att_strategy)
        att_strategy = att_strategy[att_strategy["strategy_code"].isin(strategy_codes)].copy()
        after_n = len(att_strategy)
        if after_n == 0:
            raise ValueError(
                f"No rows in ATTRIBUTE_STRATEGY for strategy_code(s) {strategy_codes} "
                f"for process '{process_name}'."
            )
        print(
            f"[{process_name}] Filtering ATTRIBUTE_STRATEGY from {before_n} to {after_n} rows "
            f"for strategy_code(s): {sorted(strategy_codes)} (including BASE)"
        )

    cb = CostBenefits(ssp_data, att_primary, att_strategy, STRATEGY_CODE_BASE)
    cb.load_cb_parameters(str(config["cb_definition_path"]))

    # Compute costs
    results_system = cb.compute_system_cost_for_all_strategies()
    results_tx = cb.compute_technical_cost_for_all_strategies()
    results_all = pd.concat([results_system, results_tx], ignore_index=True)

    # Post-process: interactions and cost shifting
    results_all_pp = cb.cb_process_interactions(results_all)
    results_all_pp_shifted = cb.cb_shift_costs(results_all_pp)

    # Save
    cb_output_dir.mkdir(parents=True, exist_ok=True)
    output_path = cb_output_dir / output_csv_name
    results_all_pp_shifted.to_csv(output_path, index=False)
    print(f"[{process_name}] Results saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run CBA pipeline for tornado and/or whirlpool (country-agnostic).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "process",
        nargs="?",
        default="both",
        choices=["tornado", "whirlpool", "both"],
        help="Which process to run: tornado, whirlpool, or both (default).",
    )
    parser.add_argument(
        "--country",
        type=str,
        default=_DEFAULT_COUNTRY,
        help=f"Country code for input/output filenames (default: {_DEFAULT_COUNTRY}).",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory (default: current directory).",
    )
    parser.add_argument(
        "--path-run-output",
        type=str,
        default=_DEFAULT_PATH_RUN_OUTPUT,
        help="Path from project root to run output folder containing tornado/ and whirlpool/ subdirs.",
    )
    parser.add_argument(
        "--path-cb-output",
        type=str,
        default=_DEFAULT_PATH_CB_OUTPUT,
        help="Path from project root to folder where CBA CSVs are written.",
    )
    parser.add_argument(
        "--tornado-strategy",
        type=str,
        default=None,
        help="Run only this strategy_code for tornado (BASE is always included). Omit to run all.",
    )
    parser.add_argument(
        "--whirlpool-strategy",
        type=str,
        default=None,
        help="Run only this strategy_code for whirlpool (BASE is always included). Omit to run all.",
    )
    args = parser.parse_args()

    config = _build_config(args)
    run_strategy_by_process = {
        "tornado": args.tornado_strategy,
        "whirlpool": args.whirlpool_strategy,
    }

    if args.process == "both":
        for name in ("tornado", "whirlpool"):
            run_cba_pipeline(name, run_strategy_by_process, config)
    else:
        run_cba_pipeline(args.process, run_strategy_by_process, config)


if __name__ == "__main__":
    main()
