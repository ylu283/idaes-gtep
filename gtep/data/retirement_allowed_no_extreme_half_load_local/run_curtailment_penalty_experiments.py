"""Run curtailment-penalty proxy experiments for Prescient PCM/UC.

Prescient does not expose a dedicated renewable curtailment penalty option in
the run configuration. This script uses price/violation penalty thresholds as
the practical proxy lever for curtailment pricing behavior in SCED/RUC.

Design goals:
- isolate each case in its own output directory;
- keep an incremental manifest for reproducibility/debugging;
- fail fast by default, with optional continue-on-error behavior.
"""

from __future__ import annotations

import argparse
import json
import traceback
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _patch_prescient_curtailment_report() -> bool:
    """Patch legacy Prescient curtailment reporting for scalar renewable ``p_max``.

    Some Prescient builds assume renewable ``p_max`` is always time-series data.
    RTS-GMLC hydro units may use a scalar ``p_max`` and trigger a TypeError in
    reporting code. This monkey patch keeps reporting non-fatal for both forms.
    """
    try:
        from prescient.engine.egret import reporting
    except Exception as err:
        print(
            "WARNING: failed to import prescient.engine.egret.reporting for "
            f"hydro curtailment patch: {type(err).__name__}: {err}"
        )
        return False

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
    patched_func = reporting.report_curtailment_for_deterministic_ruc
    print(
        "Applied hydro-safe curtailment reporting patch: "
        f"{patched_func.__module__}.{patched_func.__name__}"
    )
    return True


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
    """Create sanitized Prescient options for one case.

    Case dicts contain metadata keys (e.g., ``name``) used by this runner.
    Those keys are removed to avoid passing unknown options into Prescient.
    """
    options = deepcopy(BASE_COMMON_OPTIONS)
    options.update(MODE_OPTIONS[mode])
    for key, value in case.items():
        # metadata keys are not valid Prescient configuration options
        if key in {"name"}:
            continue
        options[key] = value
    return options


def _validate_case(case: dict[str, Any]) -> None:
    """Validate case metadata and threshold values before launch."""
    case_name = case.get("name")
    if not isinstance(case_name, str) or not case_name.strip():
        raise ValueError("Each case must define a non-empty string 'name'.")

    for key, value in case.items():
        if not key.endswith("_threshold"):
            continue
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(
                f"Case '{case_name}' has invalid threshold '{key}={value}'. "
                "Thresholds must be positive numeric values."
            )


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _parse_args() -> argparse.Namespace:
    """Define CLI arguments for the case sweep runner."""
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
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running remaining cases after a case failure.",
    )
    return parser.parse_args()


def main() -> None:
    """Run configured cases, recording per-case status in a manifest."""
    args = _parse_args()

    case_root = Path(args.output_root) / args.mode
    case_root.mkdir(parents=True, exist_ok=True)

    patch_applied = False
    if not args.dry_run:
        # Late import allows dry-run and local linting in environments without Prescient.
        from prescient.simulator import Prescient
        # Apply patch after Prescient import to avoid module reload/order issues.
        patch_applied = _patch_prescient_curtailment_report()

    case_manifest: list[dict[str, Any]] = []
    manifest_path = case_root / "experiment_manifest.json"
    manifest: dict[str, Any] = {
        "mode": args.mode,
        "case_set": args.case_set,
        "data_path": args.data_path,
        "start_date": args.start_date,
        "num_days": args.num_days,
        "continue_on_error": args.continue_on_error,
        "cases": case_manifest,
    }
    for case in CASE_SETS[args.case_set]:
        _validate_case(case)
        case_name = case["name"]
        output_directory = case_root / case_name

        options = _build_case_options(args.mode, case)
        options["output_directory"] = str(output_directory)
        options["data_path"] = args.data_path
        options["start_date"] = args.start_date
        options["num_days"] = args.num_days

        case_record: dict[str, Any] = {
            "case_name": case_name,
            "status": "pending",
            "start_ts_utc": _utc_now_iso(),
            "options": options,
        }
        case_manifest.append(case_record)

        print(f"\n=== Running case: {case_name} ===")
        print(f"Output: {output_directory}")
        print(
            "Penalty settings: "
            f"price={options.get('price_threshold')}, "
            f"trans={options.get('transmission_price_threshold')}, "
            f"cont={options.get('contingency_price_threshold')}, "
            f"reserve={options.get('reserve_price_threshold')}"
        )

        try:
            if args.dry_run:
                case_record["status"] = "dry_run"
            else:
                if not patch_applied:
                    # Try once more before each case in case environment import order changed.
                    patch_applied = _patch_prescient_curtailment_report()
                Prescient().simulate(**options)
                case_record["status"] = "ok"
        except Exception as err:
            case_record["status"] = "error"
            case_record["error_type"] = type(err).__name__
            case_record["error_message"] = str(err)
            case_record["traceback"] = traceback.format_exc()
            case_record["end_ts_utc"] = _utc_now_iso()
            # Persist failure details immediately for post-mortem debugging.
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(f"Case '{case_name}' failed: {type(err).__name__}: {err}")
            if not args.continue_on_error:
                raise
        else:
            case_record["end_ts_utc"] = _utc_now_iso()
            # Persist successful case completion incrementally as checkpointing.
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"\nWrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
