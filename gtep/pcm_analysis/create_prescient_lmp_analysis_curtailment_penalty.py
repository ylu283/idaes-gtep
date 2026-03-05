"""Create prescient_lmp_analysis_curtailment_penalty.ipynb.

The notebook analyzes synced curtailment-penalty experiment outputs and
exports summary artifacts for reporting.
"""

from __future__ import annotations

import json
from pathlib import Path


def md_cell(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.split("\n")],
    }


def code_cell(text: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": [line + "\n" for line in text.split("\n")],
    }


def build_notebook() -> dict:
    cells: list[dict] = []

    cells.append(
        md_cell(
            """# Prescient LMP Analysis: Curtailment-Penalty Sweep (Full Available Period)

This notebook is designed to:

1. Process raw synced Prescient outputs for five curtailment-penalty cases (`300/1000/2000/5000/10000`).
2. Reproduce the same analysis style used in your previous benchmark notebooks (clear sectioning, diagnostics, interpretation).
3. Export analysis artifacts (`CSV`, `JSON`) for report/slide reuse.

Ultimate objective: quantify whether penalty settings move PCM behavior closer to the paper-style positive LMP regime, and identify which effects are true signal vs price-cap clipping artifacts."""
        )
    )

    cells.append(
        md_cell(
            """## 1. Imports and Paths

All paths are absolute for reproducibility across local runs and synced environments."""
        )
    )

    cells.append(
        code_cell(
            """import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.style.use("seaborn-v0_8-whitegrid")
pd.set_option("display.max_columns", 200)
pd.set_option("display.width", 220)

repo_root = Path("/Users/yilu/Documents/GitHub/idaes-gtep")
pcm_dir = repo_root / "gtep" / "pcm_analysis"

exp_root = (
    repo_root
    / "gtep"
    / "data"
    / "retirement_allowed_no_extreme_half_load"
    / "Prescient_2"
    / "experiments"
    / "curtailment_penalty"
    / "pcm"
)

log_dir = repo_root / "gtep" / "data" / "retirement_allowed_no_extreme_half_load"
log_candidates = sorted(log_dir.glob("ERCOT_curtailment_penalty_pcm.o*"), key=lambda p: p.stat().st_mtime, reverse=True)

case_dirs = sorted([p for p in exp_root.iterdir() if p.is_dir() and p.name.startswith("penalty_")])
print("Experiment root:", exp_root)
print("Case folders:", [p.name for p in case_dirs])
print("Latest log:", str(log_candidates[0]) if log_candidates else "N/A")"""
        )
    )

    cells.append(
        md_cell(
            """## 2. CRC Log Context and Run Integrity

Why this section exists:
- Confirm synced run completion and detect obvious runtime failures before interpreting economics.
- Capture any warnings that could invalidate comparisons."""
        )
    )

    cells.append(
        code_cell(
            """def read_log_snapshot(path: Path, head_n: int = 10, tail_n: int = 25) -> dict:
    txt = path.read_text(errors="ignore")
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "modified": pd.to_datetime(path.stat().st_mtime, unit="s"),
        "has_traceback": ("Traceback" in txt) or ("ERROR" in txt),
        "completed": "Simulation Complete" in txt,
        "head": "\\n".join(lines[:head_n]),
        "tail": "\\n".join(lines[-tail_n:]),
    }

if log_candidates:
    snap = read_log_snapshot(log_candidates[0])
    print("Log file:", snap["path"])
    print("Size (bytes):", snap["size_bytes"])
    print("Modified:", snap["modified"])
    print("Has traceback:", snap["has_traceback"])
    print("Simulation complete marker:", snap["completed"])
    print("\\n--- LOG TAIL ---")
    print(snap["tail"])
else:
    print("No curtailment logs found in", log_dir)"""
        )
    )

    cells.append(
        md_cell(
            """## 3. Data Load Helpers and Quality Checks

Why this section exists:
- Build a robust loader for Prescient detail files.
- Handle missing manifest metadata gracefully by deriving penalty values from folder names.
- Validate schema and timestamp quality before computing metrics."""
        )
    )

    cells.append(
        code_cell(
            """def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def attach_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Date" not in df.columns:
        return df
    out = df.copy()
    if "Hour" not in out.columns:
        out["Hour"] = 0
    if "Minute" not in out.columns:
        out["Minute"] = 0
    dt = pd.to_datetime(out["Date"], errors="coerce")
    dt = dt + pd.to_timedelta(out["Hour"], unit="h") + pd.to_timedelta(out["Minute"], unit="m")
    out["Datetime"] = dt
    return out


def parse_penalty_from_case(case_name: str) -> float:
    m = re.search(r"penalty_(\\d+)", case_name)
    if not m:
        raise ValueError(f"Cannot parse penalty from case name: {case_name}")
    return float(m.group(1))


def load_case(case_dir: Path) -> dict:
    bus = attach_datetime(safe_read_csv(case_dir / "bus_detail.csv"))
    hourly = attach_datetime(safe_read_csv(case_dir / "hourly_summary.csv"))
    renew = attach_datetime(safe_read_csv(case_dir / "renewables_detail.csv"))
    daily = safe_read_csv(case_dir / "daily_summary.csv")
    return {
        "case": case_dir.name,
        "penalty": parse_penalty_from_case(case_dir.name),
        "bus": bus,
        "hourly": hourly,
        "renew": renew,
        "daily": daily,
    }


raw = [load_case(d) for d in case_dirs]

quality_rows = []
for c in raw:
    bus = c["bus"]
    hourly = c["hourly"]
    renew = c["renew"]
    quality_rows.append(
        {
            "case": c["case"],
            "penalty": c["penalty"],
            "bus_rows": len(bus),
            "hourly_rows": len(hourly),
            "renew_rows": len(renew),
            "bus_start": bus["Datetime"].min() if ("Datetime" in bus.columns and len(bus)) else pd.NaT,
            "bus_end": bus["Datetime"].max() if ("Datetime" in bus.columns and len(bus)) else pd.NaT,
            "hourly_start": hourly["Datetime"].min() if ("Datetime" in hourly.columns and len(hourly)) else pd.NaT,
            "hourly_end": hourly["Datetime"].max() if ("Datetime" in hourly.columns and len(hourly)) else pd.NaT,
            "bus_cols_ok": {"LMP", "LMP DA", "Demand"}.issubset(set(bus.columns)),
            "hourly_cols_ok": {"OverGeneration", "RenewablesCurtailment", "LoadShedding", "ReserveShortfall"}.issubset(set(hourly.columns)),
            "renew_cols_ok": {"Curtailment"}.issubset(set(renew.columns)),
        }
    )

quality_df = pd.DataFrame(quality_rows).sort_values("penalty")
display(quality_df)"""
        )
    )

    cells.append(
        md_cell(
            """## 4. Common Time Window Alignment

Why this section exists:
- Case comparisons must use a common timestamp window.
- This avoids false differences caused by unequal run lengths."""
        )
    )

    cells.append(
        code_cell(
            """bus_starts = [c["bus"]["Datetime"].min() for c in raw if not c["bus"].empty]
bus_ends = [c["bus"]["Datetime"].max() for c in raw if not c["bus"].empty]
hourly_starts = [c["hourly"]["Datetime"].min() for c in raw if not c["hourly"].empty]
hourly_ends = [c["hourly"]["Datetime"].max() for c in raw if not c["hourly"].empty]

common_start = max(bus_starts + hourly_starts)
common_end = min(bus_ends + hourly_ends)

if common_start > common_end:
    raise RuntimeError(
        f"No common overlap. common_start={common_start}, common_end={common_end}"
    )

print("Common overlap start:", common_start)
print("Common overlap end:  ", common_end)

def window(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Datetime" not in df.columns:
        return df
    return df[(df["Datetime"] >= common_start) & (df["Datetime"] <= common_end)].copy()

aligned = []
for c in raw:
    aligned.append(
        {
            "case": c["case"],
            "penalty": c["penalty"],
            "bus": window(c["bus"]),
            "hourly": window(c["hourly"]),
            "renew": window(c["renew"]),
        }
    )

for c in sorted(aligned, key=lambda x: x["penalty"]):
    print(c["case"], "bus rows:", len(c["bus"]), "| hourly rows:", len(c["hourly"]), "| renew rows:", len(c["renew"]))"""
        )
    )

    cells.append(
        md_cell(
            """## 5. Core Benchmark Metrics (Penalty Sweep)

Why this section exists:
- Summarize each case with directly comparable KPIs.
- Separate real economic changes from threshold clipping behavior."""
        )
    )

    cells.append(
        code_cell(
            """def case_metrics(case: dict) -> dict:
    bus = case["bus"]
    hourly = case["hourly"]
    renew = case["renew"]
    penalty = case["penalty"]

    lmp_col = "LMP DA" if "LMP DA" in bus.columns else "LMP"
    lmp = bus[lmp_col].astype(float)

    neg_frac = float((lmp < 0.0).mean())
    floor_frac = float((lmp <= (-penalty + 1e-9)).mean())
    ceil_frac = float((lmp >= (penalty - 1e-9)).mean())

    demand = bus["Demand"].astype(float)
    weighted_lmp = float((demand * lmp).sum() / demand.sum()) if demand.sum() > 0 else np.nan

    hourly_agg = (
        hourly.groupby("Datetime")[["OverGeneration", "LoadShedding", "ReserveShortfall", "RenewablesCurtailment"]]
        .sum()
        .sort_index()
    )
    sys_lmp = (
        bus.groupby("Datetime")
        .apply(lambda x: (x["Demand"] * x[lmp_col]).sum() / x["Demand"].sum())
        .rename("system_lmp")
        .sort_index()
    )

    return {
        "case": case["case"],
        "penalty": penalty,
        "rows_bus": len(bus),
        "rows_hourly": len(hourly),
        "lmp_min": float(lmp.min()),
        "lmp_max": float(lmp.max()),
        "lmp_mean": float(lmp.mean()),
        "lmp_median": float(lmp.median()),
        "neg_lmp_frac": neg_frac,
        "floor_hit_frac": floor_frac,
        "ceiling_hit_frac": ceil_frac,
        "weighted_lmp": weighted_lmp,
        "total_curtailment_mwh": float(renew["Curtailment"].sum()) if "Curtailment" in renew.columns else np.nan,
        "total_overgeneration_mwh": float(hourly["OverGeneration"].sum()) if "OverGeneration" in hourly.columns else np.nan,
        "total_load_shedding_mwh": float(hourly["LoadShedding"].sum()) if "LoadShedding" in hourly.columns else np.nan,
        "total_reserve_shortfall_mwh": float(hourly["ReserveShortfall"].sum()) if "ReserveShortfall" in hourly.columns else np.nan,
        "system_lmp_ts": sys_lmp,
        "hourly_agg_ts": hourly_agg,
    }


metrics = [case_metrics(c) for c in sorted(aligned, key=lambda x: x["penalty"])]
summary_df = pd.DataFrame(
    [
        {k: v for k, v in m.items() if k not in {"system_lmp_ts", "hourly_agg_ts"}}
        for m in metrics
    ]
).sort_values("penalty")

display(summary_df)"""
        )
    )

    cells.append(
        md_cell(
            """### Interpretation Notes

- `neg_lmp_frac`: direct indicator of divergence from paper's mostly positive-price behavior.
- `floor_hit_frac` / `ceiling_hit_frac`: identifies whether penalty settings are actively clipping prices.
- `weighted_lmp`: system-level benchmark metric robust to bus-level volatility.
- Curtailment/overgeneration totals help assess whether penalty changes are solving imbalance or just moving prices."""
        )
    )

    cells.append(
        code_cell(
            """# Export summary for reports/slides
summary_csv = pcm_dir / "curtailment_penalty_benchmark_summary.csv"
summary_json = pcm_dir / "curtailment_penalty_benchmark_summary.json"

summary_df.to_csv(summary_csv, index=False)
summary_json.write_text(
    json.dumps(
        {
            "common_start": str(common_start),
            "common_end": str(common_end),
            "cases": json.loads(summary_df.to_json(orient="records")),
        },
        indent=2,
    ),
    encoding="utf-8",
)

print("Wrote:", summary_csv)
print("Wrote:", summary_json)"""
        )
    )

    cells.append(
        md_cell(
            """## 6. Time-Series Views and Trend Diagnostics

Why this section exists:
- Show whether penalty changes shift trajectory, not only aggregate means.
- Highlight where clipping artifacts dominate."""
        )
    )

    cells.append(
        code_cell(
            """# Build wide hourly export: system LMP + key hourly aggregates by case
wide_parts = []
for m in metrics:
    ts = pd.concat([m["system_lmp_ts"], m["hourly_agg_ts"]], axis=1).reset_index()
    ts["case"] = m["case"]
    ts["penalty"] = m["penalty"]
    wide_parts.append(ts)

wide_df = pd.concat(wide_parts, ignore_index=True)
wide_csv = pcm_dir / "curtailment_penalty_timeseries_wide.csv"
wide_df.to_csv(wide_csv, index=False)
print("Wrote:", wide_csv)
display(wide_df.head())"""
        )
    )

    cells.append(
        code_cell(
            """fig, ax = plt.subplots(figsize=(13, 5))
for m in metrics:
    ax.plot(m["system_lmp_ts"].index, m["system_lmp_ts"].values, label=f"{int(m['penalty'])}")
ax.set_title("System Load-Weighted LMP by Penalty Case")
ax.set_xlabel("Datetime")
ax.set_ylabel("$/MWh")
ax.legend(title="Penalty")
plt.tight_layout()
plt.show()"""
        )
    )

    cells.append(
        md_cell(
            """Interpretation:
- If curves separate mainly by floor/ceiling clipping levels, penalty is acting as a cap mechanism.
- If curves shift in central tendency (not just tails), penalty is changing dispatch economics more fundamentally."""
        )
    )

    cells.append(
        code_cell(
            """fig, axes = plt.subplots(1, 3, figsize=(16, 4))
axes[0].plot(summary_df["penalty"], summary_df["neg_lmp_frac"], marker="o")
axes[0].set_title("Negative LMP Fraction vs Penalty")
axes[0].set_xlabel("Penalty")
axes[0].set_ylabel("Fraction")

axes[1].plot(summary_df["penalty"], summary_df["floor_hit_frac"], marker="o", color="firebrick")
axes[1].set_title("Floor-Hit Fraction vs Penalty")
axes[1].set_xlabel("Penalty")
axes[1].set_ylabel("Fraction")

axes[2].plot(summary_df["penalty"], summary_df["weighted_lmp"], marker="o", color="darkgreen")
axes[2].set_title("Load-Weighted LMP vs Penalty")
axes[2].set_xlabel("Penalty")
axes[2].set_ylabel("$/MWh")

plt.tight_layout()
plt.show()"""
        )
    )

    cells.append(
        md_cell(
            """Interpretation:
- Rising `neg_lmp_frac` with larger penalty values usually indicates deeper allowed negative excursions due to wider caps.
- `floor_hit_frac` trend quantifies clipping burden directly.
- `weighted_lmp` should be interpreted together with clipping metrics to avoid false “improvement” conclusions."""
        )
    )

    cells.append(
        code_cell(
            """fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(summary_df["penalty"], summary_df["total_curtailment_mwh"], marker="o", label="Curtailment")
ax.plot(summary_df["penalty"], summary_df["total_overgeneration_mwh"], marker="o", label="OverGeneration")
ax.set_title("Curtailment and OverGeneration Totals vs Penalty")
ax.set_xlabel("Penalty")
ax.set_ylabel("MWh (common window)")
ax.legend()
plt.tight_layout()
plt.show()"""
        )
    )

    cells.append(
        md_cell(
            """Interpretation:
- Compare curtailment and overgeneration jointly; curtailment alone can be misleading.
- If overgeneration remains high while price tails widen, penalty changes are likely redistributing price effects more than solving physical surplus."""
        )
    )

    cells.append(
        md_cell(
            """## 7. Compact Baseline/Paper Context

This section is intentionally short (per scope): it links curtailment-sweep behavior to prior benchmark evidence.

- Prior report baseline (`model_comparison_prescient_vs_paper_uc_2026-02-28.md`) showed paper UC sampled outputs are nonnegative.
- Your Prescient baseline showed material negative-price share and floor hits.
- This sweep should be interpreted as sensitivity around current Prescient formulation, not as full structural alignment to paper UC."""
        )
    )

    cells.append(
        md_cell(
            """## 8. Summary Discussion

### What this notebook produced

- Parsed and validated five synced curtailment penalty cases.
- Aligned all cases to a common full-period overlap window.
- Exported:
  - `curtailment_penalty_benchmark_summary.csv`
  - `curtailment_penalty_benchmark_summary.json`
  - `curtailment_penalty_timeseries_wide.csv`

### How to interpret for model tuning

1. Use `neg_lmp_frac` and `floor_hit_frac` together to separate true economic shift from cap clipping.
2. If larger penalties mostly increase tail magnitude (near +/- penalty) without reducing overgeneration, this is not a structural benchmark fix.
3. Treat this sweep as a diagnostic layer; structural alignment work (renewable representation, chronology, pricing workflow) remains primary.

### Caveats

- Case-level penalty metadata is inferred from folder names because manifest file is not present in this synced tree.
- Results reflect the common overlap window, not necessarily the entire intended 90-day horizon for each run.
- Paper references are contextual and sourced from existing project benchmark reports."""
        )
    )

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    nb = build_notebook()
    out_path = Path(__file__).resolve().parent / "prescient_lmp_analysis_curtailment_penalty.ipynb"
    out_path.write_text(json.dumps(nb, indent=2), encoding="utf-8")
    print(f"Wrote notebook: {out_path}")
    print(f"Cells: {len(nb['cells'])}")


if __name__ == "__main__":
    main()
