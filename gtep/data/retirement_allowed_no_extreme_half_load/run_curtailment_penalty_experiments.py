"""Run a curtailment-penalty proxy experiment sweep in Prescient.

Prescient does not expose a dedicated renewable curtailment penalty option in
the run configuration. This script uses price/violation penalty thresholds as
the practical proxy lever for curtailment pricing behavior in SCED/RUC.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from prescient.simulator import Prescient


def _patch_prescient_curtailment_report() -> None:
    """Handle renewable generators with scalar p_max (e.g., HYDRO in RTS-GMLC)."""
    try:
        from prescient.engine.egret import reporting
    except Exception:
        return

    def _at_time(value: Any, idx: int) -> float:
        if isinstance(value, dict):
            return value["values"][idx]
        return value

    def _safe_report_curtailment_for_deterministic_ruc(ruc):
        rn_gens = dict(ruc.elements("generator", generator_type="renewable"))
        time_periods = ruc.data["system"]["time_keys"]

        curtailment_in_some_period = False
        for i, t in enumerate(time_periods):
            quantity_curtailed_this_period = sum(
                _at_time(gdict["p_max"], i) - _at_time(gdict["pg"], i)
                for gdict in rn_gens.values()
            )
            if quantity_curtailed_this_period >= 5e-3:
                if not curtailment_in_some_period:
                    print("Renewables curtailment summary (time-period, aggregate_quantity):")
                    curtailment_in_some_period = True
                print(f"{t} {quantity_curtailed_this_period:12.2f}")

    reporting.report_curtailment_for_deterministic_ruc = _safe_report_curtailment_for_deterministic_ruc


_patch_prescient_curtailment_report()


BASE_COMMON_OPTIONS: dict[str, Any] = {
    "data_path": "Prescient_2",
    "input_format": "rts-gmlc",
    "start_date": "01-01-2019",
    "num_days": 90,
    "ruc_mipgap": 0.01,
    "deterministic_ruc_solver": "gurobi_persistent",
    "deterministic_ruc_solver_options": "TimeLimit=3600",
    "sced_solver": "gurobi",
    "sced_frequency_minutes": 60,
    "ruc_horizon": 36,
    "compute_market_settlements": True,
    "monitor_all_contingencies": False,
    "output_solver_logs": False,
    "ruc_network_type": "btheta",
    "sced_network_type": "btheta",
    "enforce_sced_shutdown_ramprate": False,
    "reserve_factor": 0.1,
    "day_ahead_pricing": "LMP",
}


MODE_OPTIONS: dict[str, dict[str, Any]] = {
    "pcm": {
        "simulate_out_of_sample": True,
        "run_sced_with_persistent_forecast_errors": True,
        "sced_horizon": 6,
    },
    "uc_only": {
        "simulate_out_of_sample": False,
        "run_sced_with_persistent_forecast_errors": False,
        "sced_horizon": 1,
    },
}


CASE_SETS: dict[str, list[dict[str, Any]]] = {
    # quick smoke test around your current setting and two broader caps
    "quick": [
        {
            "name": "baseline_current",
            "price_threshold": 1000.0,
            "contingency_price_threshold": 100.0,
            "reserve_price_threshold": 5.0,
        },
        {
            "name": "penalty_2000",
            "price_threshold": 2000.0,
            "transmission_price_threshold": 2000.0,
            "contingency_price_threshold": 2000.0,
            "interface_price_threshold": 2000.0,
            "reserve_price_threshold": 2000.0,
        },
        {
            "name": "penalty_5000",
            "price_threshold": 5000.0,
            "transmission_price_threshold": 5000.0,
            "contingency_price_threshold": 5000.0,
            "interface_price_threshold": 5000.0,
            "reserve_price_threshold": 5000.0,
        },
    ],
    # benchmark sweep from conservative cap to wide cap
    "benchmark": [
        {
            "name": "penalty_300",
            "price_threshold": 300.0,
            "transmission_price_threshold": 300.0,
            "contingency_price_threshold": 300.0,
            "interface_price_threshold": 300.0,
            "reserve_price_threshold": 300.0,
        },
        {
            "name": "penalty_1000",
            "price_threshold": 1000.0,
            "transmission_price_threshold": 1000.0,
            "contingency_price_threshold": 1000.0,
            "interface_price_threshold": 1000.0,
            "reserve_price_threshold": 1000.0,
        },
        {
            "name": "penalty_2000",
            "price_threshold": 2000.0,
            "transmission_price_threshold": 2000.0,
            "contingency_price_threshold": 2000.0,
            "interface_price_threshold": 2000.0,
            "reserve_price_threshold": 2000.0,
        },
        {
            "name": "penalty_5000",
            "price_threshold": 5000.0,
            "transmission_price_threshold": 5000.0,
            "contingency_price_threshold": 5000.0,
            "interface_price_threshold": 5000.0,
            "reserve_price_threshold": 5000.0,
        },
        {
            "name": "penalty_10000",
            "price_threshold": 10000.0,
            "transmission_price_threshold": 10000.0,
            "contingency_price_threshold": 10000.0,
            "interface_price_threshold": 10000.0,
            "reserve_price_threshold": 10000.0,
        },
    ],
}


def _build_case_options(mode: str, case: dict[str, Any]) -> dict[str, Any]:
    options = deepcopy(BASE_COMMON_OPTIONS)
    options.update(MODE_OPTIONS[mode])
    options.update(case)
    return options


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Prescient curtailment-penalty sweep.")
    parser.add_argument("--mode", choices=["pcm", "uc_only"], default="pcm")
    parser.add_argument("--case-set", choices=sorted(CASE_SETS), default="benchmark")
    parser.add_argument(
        "--output-root",
        default="Prescient_2/experiments/curtailment_penalty",
        help="Root output directory for experiment outputs.",
    )
    parser.add_argument("--data-path", default="Prescient_2")
    parser.add_argument("--start-date", default="01-01-2019")
    parser.add_argument("--num-days", type=int, default=90)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    case_root = Path(args.output_root) / args.mode
    case_root.mkdir(parents=True, exist_ok=True)

    case_manifest: list[dict[str, Any]] = []
    for case in CASE_SETS[args.case_set]:
        case_name = case["name"]
        output_directory = case_root / case_name

        options = _build_case_options(args.mode, case)
        options["output_directory"] = str(output_directory)
        options["data_path"] = args.data_path
        options["start_date"] = args.start_date
        options["num_days"] = args.num_days

        case_manifest.append({"case_name": case_name, "options": options})

        print(f"\n=== Running case: {case_name} ===")
        print(f"Output: {output_directory}")
        print(
            "Penalty settings: "
            f"price={options.get('price_threshold')}, "
            f"trans={options.get('transmission_price_threshold')}, "
            f"cont={options.get('contingency_price_threshold')}, "
            f"reserve={options.get('reserve_price_threshold')}"
        )
        if args.dry_run:
            continue
        Prescient().simulate(**options)

    manifest = {
        "mode": args.mode,
        "case_set": args.case_set,
        "data_path": args.data_path,
        "start_date": args.start_date,
        "num_days": args.num_days,
        "cases": case_manifest,
    }
    manifest_path = case_root / "experiment_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
