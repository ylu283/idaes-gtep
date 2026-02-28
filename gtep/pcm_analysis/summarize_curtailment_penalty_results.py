"""Summarize curtailment-penalty experiment outputs into one analysis CSV.

The script joins three levels of information:
- run metadata from ``experiment_manifest.json`` (if present),
- bus-level LMP statistics from ``bus_detail.csv``,
- curtailment/shortfall/overgeneration totals from detail and hourly files.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import fmean
from typing import Any


def _safe_float(raw: str | None) -> float:
    """Convert nullable CSV numeric values to float with zero default."""
    if raw is None or raw == "":
        return 0.0
    return float(raw)


def _load_manifest(experiment_root: Path) -> dict[str, Any] | None:
    """Load experiment manifest if it exists."""
    manifest_path = experiment_root / "experiment_manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _case_price_cap(manifest: dict[str, Any] | None, case_name: str) -> float | None:
    """Get case price cap from manifest, if available."""
    if manifest is None:
        return None
    for case in manifest.get("cases", []):
        if case.get("case_name") == case_name:
            return case.get("options", {}).get("price_threshold")
    return None


def _case_status(manifest: dict[str, Any] | None, case_name: str) -> tuple[str, str]:
    """Get case execution status and error message from manifest."""
    if manifest is None:
        return "", ""
    for case in manifest.get("cases", []):
        if case.get("case_name") == case_name:
            return case.get("status", ""), case.get("error_message", "")
    return "", ""


def _summarize_case(case_dir: Path, cap: float | None, run_status: str, run_error: str) -> dict[str, Any]:
    """Compute summary metrics for a single case directory."""
    bus_path = case_dir / "bus_detail.csv"
    ren_path = case_dir / "renewables_detail.csv"
    hourly_path = case_dir / "hourly_summary.csv"

    if not bus_path.exists() or not ren_path.exists() or not hourly_path.exists():
        return {
            "case": case_dir.name,
            "status": "missing_outputs",
            "run_status": run_status,
            "run_error": run_error,
        }

    lmp_values: list[float] = []
    cap_floor_hits = 0
    cap_ceiling_hits = 0
    with bus_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lmp = _safe_float(row.get("LMP"))
            lmp_values.append(lmp)
            if cap is not None:
                if lmp <= -cap + 1e-9:
                    cap_floor_hits += 1
                if lmp >= cap - 1e-9:
                    cap_ceiling_hits += 1

    total_curtailment = 0.0
    with ren_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_curtailment += _safe_float(row.get("Curtailment"))

    total_overgeneration = 0.0
    total_load_shedding = 0.0
    total_reserve_shortfall = 0.0
    total_hourly_renew_curtailment = 0.0
    hourly_rows = 0
    with hourly_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hourly_rows += 1
            total_overgeneration += _safe_float(row.get("OverGeneration"))
            total_load_shedding += _safe_float(row.get("LoadShedding"))
            total_reserve_shortfall += _safe_float(row.get("ReserveShortfall"))
            total_hourly_renew_curtailment += _safe_float(row.get("RenewablesCurtailment"))

    if not lmp_values:
        return {
            "case": case_dir.name,
            "status": "header_only_or_empty",
            "run_status": run_status,
            "run_error": run_error,
        }

    negative_count = sum(1 for x in lmp_values if x < 0.0)
    return {
        "case": case_dir.name,
        "status": "ok",
        "run_status": run_status,
        "run_error": run_error,
        "price_cap": cap if cap is not None else "",
        "n_bus_records": len(lmp_values),
        "lmp_min": min(lmp_values),
        "lmp_max": max(lmp_values),
        "lmp_mean": fmean(lmp_values),
        "negative_lmp_fraction": negative_count / len(lmp_values),
        "cap_floor_hits": cap_floor_hits,
        "cap_ceiling_hits": cap_ceiling_hits,
        "total_renewables_curtailment_mwh": total_curtailment,
        "total_hourly_summary_curtailment_mwh": total_hourly_renew_curtailment,
        "total_overgeneration_mwh": total_overgeneration,
        "total_load_shedding_mwh": total_load_shedding,
        "total_reserve_shortfall_mwh": total_reserve_shortfall,
        "n_hourly_rows": hourly_rows,
    }


def _parse_args() -> argparse.Namespace:
    """Define CLI arguments for summary generation."""
    parser = argparse.ArgumentParser(description="Summarize Prescient curtailment penalty experiments.")
    parser.add_argument(
        "--experiment-root",
        default="../data/retirement_allowed_no_extreme_half_load/Prescient_2/experiments/curtailment_penalty/pcm",
        help="Case root that contains case subfolders and experiment_manifest.json",
    )
    parser.add_argument("--output-csv", default="curtailment_penalty_summary.csv")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any case is missing outputs or empty.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate per-case summary table and optional strict validation failure."""
    args = _parse_args()
    experiment_root = Path(args.experiment_root).resolve()
    if not experiment_root.exists():
        raise SystemExit(f"Experiment root not found: {experiment_root}")
    manifest = _load_manifest(experiment_root)

    case_dirs = sorted(
        d for d in experiment_root.iterdir() if d.is_dir() and not d.name.startswith(".")
    )
    if not case_dirs:
        raise SystemExit(f"No case directories found in: {experiment_root}")
    summaries = [
        _summarize_case(
            case_dir,
            _case_price_cap(manifest, case_dir.name),
            *_case_status(manifest, case_dir.name),
        )
        for case_dir in case_dirs
    ]

    output_csv = Path(args.output_csv).resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    all_columns = [
        "case",
        "status",
        "run_status",
        "run_error",
        "price_cap",
        "n_bus_records",
        "lmp_min",
        "lmp_max",
        "lmp_mean",
        "negative_lmp_fraction",
        "cap_floor_hits",
        "cap_ceiling_hits",
        "total_renewables_curtailment_mwh",
        "total_hourly_summary_curtailment_mwh",
        "total_overgeneration_mwh",
        "total_load_shedding_mwh",
        "total_reserve_shortfall_mwh",
        "n_hourly_rows",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        for row in summaries:
            writer.writerow(row)

    print(f"Wrote: {output_csv}")
    for row in summaries:
        print(
            f"{row.get('case')}: status={row.get('status')}, "
            f"neg_lmp_frac={row.get('negative_lmp_fraction', '')}, "
            f"curtailment={row.get('total_renewables_curtailment_mwh', '')}"
        )
    if args.strict:
        bad = [row for row in summaries if row.get("status") in {"missing_outputs", "header_only_or_empty"}]
        if bad:
            names = ", ".join(row["case"] for row in bad)
            raise SystemExit(f"Strict mode failure: incomplete cases detected: {names}")


if __name__ == "__main__":
    main()
