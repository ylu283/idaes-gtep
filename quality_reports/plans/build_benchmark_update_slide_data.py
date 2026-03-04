"""Build structured slide data for the benchmark update presentation.

This script keeps the presentation generator lean by extracting key metrics
from the existing report artifacts and writing a single JSON payload.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path("/Users/yilu/Documents/GitHub/idaes-gtep")
MODEL_COMPARE_MD = ROOT / "quality_reports/model_comparison_prescient_vs_paper_uc_2026-02-28.md"
CURTAILMENT_SETUP_MD = ROOT / "quality_reports/curtailment_penalty_experiment_setup_2026-02-28.md"
HYDRO_Q1_JSON = ROOT / "gtep/pcm_analysis/PCM_result_hydro_q1_comparison.json"
OUT_JSON = ROOT / "quality_reports/plans/data/benchmark_update_slide_data.json"


def _extract_metric_block(pattern: str, text: str) -> dict[str, float] | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return {
        "min": float(match.group("min")),
        "max": float(match.group("max")),
        "mean": float(match.group("mean")),
        "neg_frac": float(match.group("neg")),
    }


def parse_model_comparison(md_text: str) -> dict[str, Any]:
    paper_nonneg = "Paper UC LMP files are nonnegative" in md_text

    base_pattern = (
        r"`gtep/pcm_analysis/Bus_LMP\.csv`: min (?P<min>-?[0-9.]+), "
        r"max (?P<max>-?[0-9.]+), mean (?P<mean>-?[0-9.]+), neg_frac (?P<neg>-?[0-9.]+)"
    )
    uc_pattern = (
        r"`gtep/pcm_analysis/Bus_LMP_uc_only\.csv`: min (?P<min>-?[0-9.]+), "
        r"max (?P<max>-?[0-9.]+), mean (?P<mean>-?[0-9.]+), neg_frac (?P<neg>-?[0-9.]+)"
    )

    base = _extract_metric_block(base_pattern, md_text)
    uc_only = _extract_metric_block(uc_pattern, md_text)

    return {
        "paper_lmp_nonnegative": paper_nonneg,
        "prescient_baseline": base,
        "prescient_uc_only": uc_only,
    }


def parse_curtailment_setup(md_text: str) -> dict[str, Any]:
    values_match = re.search(
        r"Tested benchmark sweep values:\s*-\s*`([^`]+)`, `([^`]+)`, `([^`]+)`, `([^`]+)`, `([^`]+)`",
        md_text,
    )
    if values_match:
        values = [int(values_match.group(i)) for i in range(1, 6)]
    else:
        values = [300, 1000, 2000, 5000, 10000]

    return {
        "penalty_values_usd_per_mwh": values,
        "status": "Ongoing 4-day simulation for 90-day experiment; run not finished yet.",
        "script": "run_curtailment_penalty_experiments.py",
    }


def parse_hydro_q1(hydro_payload: dict[str, Any]) -> dict[str, Any]:
    scenarios = {}
    for row in hydro_payload.get("metrics", []):
        name = row.get("Scenario", "Unknown")
        scenarios[name] = {
            "neg_lmp_frac": row.get("neg_lmp_frac"),
            "floor_hit_frac": row.get("floor_hit_frac"),
            "lmp_weighted": row.get("lmp_weighted"),
            "lmp_min": row.get("lmp_min"),
            "lmp_max": row.get("lmp_max"),
        }
    return {
        "overlap_start": hydro_payload.get("overlap_start"),
        "overlap_end": hydro_payload.get("overlap_end"),
        "scenarios": scenarios,
        "summary": (
            "Hydro UC+ED and hydro UC-only remain very close to no-hydro Q1; "
            "negative LMP share and floor-hits persist."
        ),
    }


def build_payload() -> dict[str, Any]:
    model_text = MODEL_COMPARE_MD.read_text(encoding="utf-8")
    curtailment_text = CURTAILMENT_SETUP_MD.read_text(encoding="utf-8")
    hydro_payload = json.loads(HYDRO_Q1_JSON.read_text(encoding="utf-8"))

    return {
        "meta": {
            "deck_title": "Prescient PCM vs Paper UC: Benchmarking Status and Effort",
            "date": "2026-03-03",
            "audience": "Collaborators and supervisor",
            "scope_minutes": 20,
        },
        "model_comparison": parse_model_comparison(model_text),
        "curtailment": parse_curtailment_setup(curtailment_text),
        "hydro_q1": parse_hydro_q1(hydro_payload),
        "sources": {
            "model_comparison_report": str(MODEL_COMPARE_MD),
            "curtailment_setup_report": str(CURTAILMENT_SETUP_MD),
            "hydro_q1_summary_json": str(HYDRO_Q1_JSON),
            "hydro_q1_notebook": str(ROOT / "gtep/pcm_analysis/prescient_lmp_analysis_with_hydro_q1.ipynb"),
        },
    }


def main() -> None:
    payload = build_payload()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
