"""Build structured data for model-update + curtailment deep-dive deck."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path("/Users/yilu/Documents/GitHub/idaes-gtep")
MODEL_COMPARE_MD = ROOT / "quality_reports/reports/model_comparison_prescient_vs_paper_uc_2026-02-28.md"
CURTAILMENT_SETUP_MD = ROOT / "quality_reports/reports/curtailment_penalty_experiment_setup_2026-02-28.md"
CURTAILMENT_SUMMARY_CSV = ROOT / "gtep/pcm_analysis/curtailment_penalty_benchmark_summary.csv"
CURTAILMENT_SUMMARY_JSON = ROOT / "gtep/pcm_analysis/curtailment_penalty_benchmark_summary.json"
CURTAILMENT_NOTEBOOK = ROOT / "gtep/pcm_analysis/prescient_lmp_analysis_curtailment_penalty.ipynb"
OUT_JSON = ROOT / "quality_reports/decks/data/model_update_curtailment_deepdive_data.json"


def _extract_prescient_stats(text: str) -> dict[str, float] | None:
    m = re.search(
        r"`gtep/pcm_analysis/Bus_LMP\.csv`: min (?P<min>-?[0-9.]+), max (?P<max>-?[0-9.]+), mean (?P<mean>-?[0-9.]+), neg_frac (?P<neg>-?[0-9.]+)",
        text,
    )
    if not m:
        return None
    return {
        "min": float(m.group("min")),
        "max": float(m.group("max")),
        "mean": float(m.group("mean")),
        "neg_frac": float(m.group("neg")),
    }


def _extract_ranking_rows(text: str) -> list[dict[str, str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        if "Rank |" in line or line.startswith("|---"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5:
            continue
        if cols[0].isdigit():
            rows.append(
                {
                    "rank": cols[0],
                    "difference": cols[1],
                    "impact": cols[2],
                    "confidence": cols[3],
                    "why": cols[4],
                }
            )
    return rows


def _load_summary_rows(csv_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "case": r["case"],
                    "penalty": float(r["penalty"]),
                    "neg_lmp_frac": float(r["neg_lmp_frac"]),
                    "floor_hit_frac": float(r["floor_hit_frac"]),
                    "weighted_lmp": float(r["weighted_lmp"]),
                    "lmp_min": float(r["lmp_min"]),
                    "lmp_max": float(r["lmp_max"]),
                    "total_curtailment_mwh": float(r["total_curtailment_mwh"]),
                    "total_overgeneration_mwh": float(r["total_overgeneration_mwh"]),
                }
            )
    return sorted(rows, key=lambda x: x["penalty"])


def build_payload() -> dict[str, Any]:
    model_text = MODEL_COMPARE_MD.read_text(encoding="utf-8")
    curtail_text = CURTAILMENT_SETUP_MD.read_text(encoding="utf-8")
    summary_rows = _load_summary_rows(CURTAILMENT_SUMMARY_CSV)
    summary_json = json.loads(CURTAILMENT_SUMMARY_JSON.read_text(encoding="utf-8"))

    return {
        "meta": {
            "title": "Model Update and Curtailment Analysis Deep Dive",
            "subtitle": "Prescient PCM vs Paper UC | TX-123BT",
            "date": "2026-03-11",
            "audience": "Collaborators and supervisor",
        },
        "model_update": {
            "prescient_baseline": _extract_prescient_stats(model_text),
            "paper_nonnegative_statement_present": "Paper UC LMP files are nonnegative" in model_text,
            "impact_ranking": _extract_ranking_rows(model_text),
            "solver_note_present": "CONOPT is a nonlinear programming (NLP) solver" in model_text,
            "scope_caveat_present": "formpyomo_UC.py" in model_text,
        },
        "curtailment_setup": {
            "proxy_statement_present": "curtailment-penalty *proxy*" in curtail_text
            or "curtailment-penalty proxy" in curtail_text,
            "baseline_1000_not_equal_present": "penalty_1000" in curtail_text
            and "NOT" in curtail_text
            and "baseline" in curtail_text,
            "da_lmp_note_present": "LMP DA" in curtail_text,
            "load_weighted_note_present": "lmp_load_weighted" in curtail_text,
        },
        "curtailment_results": {
            "common_start": summary_json.get("common_start"),
            "common_end": summary_json.get("common_end"),
            "rows": summary_rows,
        },
        "sources": {
            "model_comparison_report": str(MODEL_COMPARE_MD),
            "curtailment_setup_report": str(CURTAILMENT_SETUP_MD),
            "curtailment_summary_csv": str(CURTAILMENT_SUMMARY_CSV),
            "curtailment_summary_json": str(CURTAILMENT_SUMMARY_JSON),
            "curtailment_notebook": str(CURTAILMENT_NOTEBOOK),
        },
    }


def main() -> None:
    payload = build_payload()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
