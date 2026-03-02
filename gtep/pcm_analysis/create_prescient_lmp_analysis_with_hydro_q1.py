"""Create prescient_lmp_analysis_with_hydro_q1.ipynb.

This generator keeps the notebook content reproducible and editable in Python.
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
    cells = []

    cells.append(
        md_cell(
            """# Prescient LMP Analysis With Hydro (Q1)

This notebook is designed to:

1. Process **raw CRC simulation results** from the two hydro runs:
   - `results_btheta` (UC+ED)
   - `results_btheta_uc_only` (UC-only)
2. Benchmark both against your no-hydro 365-day run, using **Q1 slice only**.
3. Compare key price behavior against hardcoded paper reference values already used in prior analyses.

Ultimate objective: evaluate whether current PCM setup is moving toward paper-like behavior while using Q1 as a computationally cheaper proxy for full-year runs."""
        )
    )

    cells.append(
        md_cell(
            """## 1. Imports and Paths

All paths are absolute to avoid ambiguity from copied notebooks."""
        )
    )

    cells.append(
        code_cell(
            """import os
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.style.use("seaborn-v0_8-whitegrid")
pd.set_option("display.max_columns", 200)
pd.set_option("display.width", 200)

# --- Paths ---
repo_root = Path("/Users/yilu/Documents/GitHub/idaes-gtep")
pcm_dir = repo_root / "gtep" / "pcm_analysis"
run_root = repo_root / "gtep" / "data" / "retirement_allowed_no_extreme_half_load"

hydro_uced_path = run_root / "Prescient_2" / "results_btheta"
hydro_uconly_path = run_root / "Prescient_2" / "results_btheta_uc_only"

nohydro_root = Path(
    "/Users/yilu/Documents/development/nd/research/gtep/123_bus_coal/results/"
    "retirement_allowed_no_extreme/12mon_no_hydro_with_curtailment"
)

paper_pdf = Path("/Users/yilu/Zotero/zotero files/storage/LTIFVZDA")

gen_meta_path = run_root / "Prescient_2" / "gen.csv"
bus_meta_path = run_root / "Prescient_2" / "bus.csv"
branch_meta_path = run_root / "Prescient_2" / "branch.csv"

scenarios = {
    "Hydro Btheta UC+ED": {
        "results_path": hydro_uced_path,
        "color": "steelblue",
    },
    "Hydro Btheta UC-only": {
        "results_path": hydro_uconly_path,
        "color": "darkorange",
    },
    "No-hydro Benchmark Q1": {
        "results_path": nohydro_root,
        "color": "forestgreen",
    },
}

print("Notebook output dir:", pcm_dir)
for name, s in scenarios.items():
    print(f"{name:24s} -> {s['results_path']}")"""
        )
    )

    cells.append(
        md_cell(
            """## 2. Simulation Configuration Used

Hydro simulations in this notebook come from:

- `submit_job_btheta.py` -> `run_coal_prescient_btheta.py` -> `output_directory=Prescient_2/results_btheta`
- `submit_job_btheta_uc_only.py` -> `run_coal_prescient_btheta_uc_only.py` -> `output_directory=Prescient_2/results_btheta_uc_only`

### Config summary

| Parameter | Hydro Btheta UC+ED | Hydro Btheta UC-only |
|---|---:|---:|
| `simulate_out_of_sample` | `True` | `False` |
| `run_sced_with_persistent_forecast_errors` | `True` | `False` |
| `sced_horizon` | `6` | `1` |
| `ruc_horizon` | `36` | `36` |
| `ruc_network_type` / `sced_network_type` | `btheta` / `btheta` | `btheta` / `btheta` |
| `price_threshold` | `1000` | `1000` |
| `reserve_factor` | `0.1` | `0.1` |
| Start date / intended duration | 2019-01-01 / 90 days | 2019-01-01 / 90 days |

Q1 is used as the benchmarking horizon to reduce computational cost while preserving seasonal signal."""
        )
    )

    cells.append(md_cell("## 3. Helper Functions"))

    cells.append(
        code_cell(
            """def _safe_read_csv(path: Path) -> pd.DataFrame:
    \"\"\"Read CSV robustly; return empty DataFrame for empty or missing files.\"\"\"
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _prescient_output_to_df(path: Path) -> pd.DataFrame:
    \"\"\"Load Prescient detail file and build Datetime from Date/Hour/Minute.\"\"\"
    df = _safe_read_csv(path)
    if df.empty:
        return df
    req = {"Date", "Hour"}
    if not req.issubset(df.columns):
        return df
    if "Minute" not in df.columns:
        df["Minute"] = 0
    dt = pd.to_datetime(df["Date"], errors="coerce")
    dt = dt + pd.to_timedelta(df["Hour"], unit="h") + pd.to_timedelta(df["Minute"], unit="m")
    df["Datetime"] = dt
    return df


def _load_scenario_raw(results_path: Path) -> dict:
    \"\"\"Load all raw result files needed for this benchmark notebook.\"\"\"
    return {
        "bus": _prescient_output_to_df(results_path / "bus_detail.csv"),
        "renew": _prescient_output_to_df(results_path / "renewables_detail.csv"),
        "thermal": _prescient_output_to_df(results_path / "thermal_detail.csv"),
        "hourly": _prescient_output_to_df(results_path / "hourly_summary.csv"),
        "daily": _safe_read_csv(results_path / "daily_summary.csv"),
    }


def _load_weighted_lmp(bus_df: pd.DataFrame, lmp_col: str = "LMP DA") -> pd.Series:
    \"\"\"Compute hourly load-weighted system LMP.\"\"\"
    if bus_df.empty:
        return pd.Series(dtype=float)
    if lmp_col not in bus_df.columns:
        lmp_col = "LMP"
    g = bus_df.groupby("Datetime")
    wsum = g.apply(lambda x: (x["Demand"] * x[lmp_col]).sum())
    dsum = g["Demand"].sum()
    out = (wsum / dsum.replace(0, np.nan)).fillna(0.0)
    out.name = "sys_lmp"
    return out.sort_index()


def _build_q1(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Datetime" not in df.columns:
        return df
    return df[df["Datetime"].dt.month <= 3].copy()


def _window_filter(df: pd.DataFrame, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> pd.DataFrame:
    if df.empty or "Datetime" not in df.columns:
        return df
    return df[(df["Datetime"] >= start_dt) & (df["Datetime"] <= end_dt)].copy()"""
        )
    )

    cells.append(md_cell("## 4. Parse Latest CRC Logs for Context"))

    cells.append(
        code_cell(
            """# Latest btheta logs from this run directory
log_dir = run_root
hydro_logs = sorted(log_dir.glob("ERCOT_btheta_hydro.o*"), key=lambda p: p.stat().st_mtime, reverse=True)
uc_only_logs = sorted(log_dir.glob("ERCOT_btheta_uc_hydro.o*"), key=lambda p: p.stat().st_mtime, reverse=True)

latest_logs = []
if hydro_logs:
    latest_logs.append(("Hydro Btheta UC+ED", hydro_logs[0]))
if uc_only_logs:
    latest_logs.append(("Hydro Btheta UC-only", uc_only_logs[0]))

def _extract_log_summary(path: Path) -> dict:
    txt = path.read_text(errors="ignore")
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    has_traceback = "Traceback" in txt or "TypeError" in txt or "ValueError" in txt
    return {
        "file": str(path),
        "size_bytes": path.stat().st_size,
        "last_modified": pd.to_datetime(path.stat().st_mtime, unit="s"),
        "has_traceback": has_traceback,
        "head": "\\n".join(lines[:8]),
        "tail": "\\n".join(lines[-12:]),
    }

log_rows = []
for label, p in latest_logs:
    s = _extract_log_summary(p)
    s["scenario"] = label
    log_rows.append(s)

log_df = pd.DataFrame(log_rows)
if not log_df.empty:
    display(log_df[["scenario", "file", "size_bytes", "last_modified", "has_traceback"]])
    for _, r in log_df.iterrows():
        print("\\n" + "="*90)
        print(r["scenario"], "->", r["file"])
        print("- Head -")
        print(r["head"])
        print("- Tail -")
        print(r["tail"])
else:
    print("No btheta logs found in", log_dir)"""
        )
    )

    cells.append(md_cell("## 5. Load Raw Simulation Results and Build Q1 Datasets"))

    cells.append(
        code_cell(
            """raw = {}
for name, cfg in scenarios.items():
    d = _load_scenario_raw(cfg["results_path"])
    # Q1 subset only for benchmark comparison target
    for k in ["bus", "renew", "thermal", "hourly"]:
        d[k] = _build_q1(d[k])
    raw[name] = d

availability_rows = []
for name, d in raw.items():
    for key in ["bus", "renew", "thermal", "hourly"]:
        df = d[key]
        n = len(df)
        if n > 0 and "Datetime" in df.columns:
            start = df["Datetime"].min()
            end = df["Datetime"].max()
        else:
            start, end = pd.NaT, pd.NaT
        availability_rows.append(
            {
                "Scenario": name,
                "Dataset": key,
                "Rows": n,
                "Start": start,
                "End": end,
            }
        )

availability_df = pd.DataFrame(availability_rows)
display(availability_df.sort_values(["Scenario", "Dataset"]))"""
        )
    )

    cells.append(
        md_cell(
            """## 6. Common Comparison Window

To keep a fair comparison when one run has fewer timestamps, we use the overlapping datetime window across all three bus-level datasets."""
        )
    )

    cells.append(
        code_cell(
            """bus_ranges = []
for name, d in raw.items():
    b = d["bus"]
    if b.empty or "Datetime" not in b.columns:
        continue
    bus_ranges.append((name, b["Datetime"].min(), b["Datetime"].max()))

if len(bus_ranges) < 2:
    raise RuntimeError("Not enough non-empty bus datasets to compare.")

overlap_start = max(x[1] for x in bus_ranges)
overlap_end = min(x[2] for x in bus_ranges)
if overlap_start > overlap_end:
    raise RuntimeError("No overlapping datetime window across scenarios.")

print("Overlap window:", overlap_start, "to", overlap_end)
for x in bus_ranges:
    print(f"{x[0]:24s}: {x[1]} -> {x[2]}")

windowed = {}
for name, d in raw.items():
    windowed[name] = {
        k: _window_filter(v, overlap_start, overlap_end) if isinstance(v, pd.DataFrame) else v
        for k, v in d.items()
    }"""
        )
    )

    cells.append(md_cell("## 7. Export Analysis-Ready Wide CSVs (mimicking existing workflow)"))

    cells.append(
        code_cell(
            """def _wide_lmp(bus_df: pd.DataFrame) -> pd.DataFrame:
    if bus_df.empty:
        return pd.DataFrame()
    cols = ["Datetime", "Bus", "LMP", "LMP DA"]
    cols = [c for c in cols if c in bus_df.columns]
    sub = bus_df[cols].copy()
    out = sub.pivot_table(index="Datetime", columns="Bus", values="LMP", aggfunc="mean")
    out.columns = [f"{c}_LMP" for c in out.columns]
    if "LMP DA" in sub.columns:
        out_da = sub.pivot_table(index="Datetime", columns="Bus", values="LMP DA", aggfunc="mean")
        out_da.columns = [f"{c}_LMP_DA" for c in out_da.columns]
        out = out.join(out_da, how="outer")
    return out.sort_index()


def _wide_dispatch(thermal_df: pd.DataFrame, renew_df: pd.DataFrame) -> pd.DataFrame:
    parts = []
    if not thermal_df.empty and {"Datetime", "Generator", "Dispatch"}.issubset(thermal_df.columns):
        t = thermal_df.pivot_table(index="Datetime", columns="Generator", values="Dispatch", aggfunc="mean")
        t.columns = [f"Gen{c}_ThermalDispatch" for c in t.columns]
        parts.append(t)
    if not renew_df.empty and {"Datetime", "Generator", "Output"}.issubset(renew_df.columns):
        r = renew_df.pivot_table(index="Datetime", columns="Generator", values="Output", aggfunc="mean")
        r.columns = [f"Gen{c}_RenewOutput" for c in r.columns]
        parts.append(r)
        if "Curtailment" in renew_df.columns:
            rc = renew_df.pivot_table(index="Datetime", columns="Generator", values="Curtailment", aggfunc="mean")
            rc.columns = [f"Gen{c}_Curtailment" for c in rc.columns]
            parts.append(rc)
    if not parts:
        return pd.DataFrame()
    out = parts[0]
    for p in parts[1:]:
        out = out.join(p, how="outer")
    return out.sort_index()


output_map = {
    "Hydro Btheta UC+ED": ("Bus_LMP_hydro_btheta.csv", "Generator_Dispatch_hydro_btheta.csv"),
    "Hydro Btheta UC-only": ("Bus_LMP_hydro_uc_only.csv", "Generator_Dispatch_hydro_uc_only.csv"),
    "No-hydro Benchmark Q1": ("Bus_LMP_no_hydro_q1.csv", "Generator_Dispatch_no_hydro_q1.csv"),
}

for name, (lmp_name, disp_name) in output_map.items():
    b = windowed[name]["bus"]
    t = windowed[name]["thermal"]
    r = windowed[name]["renew"]
    lmp_w = _wide_lmp(b)
    disp_w = _wide_dispatch(t, r)
    lmp_path = pcm_dir / lmp_name
    disp_path = pcm_dir / disp_name
    lmp_w.to_csv(lmp_path)
    disp_w.to_csv(disp_path)
    print(f"{name}: wrote {lmp_path.name} ({lmp_w.shape}) and {disp_path.name} ({disp_w.shape})")"""
        )
    )

    cells.append(md_cell("## 8. Compute Core Benchmark Metrics"))

    cells.append(
        code_cell(
            """paper_reference = {
    "price_range_typical": "10-50 $/MWh (mostly positive)",
    "q2_daily_dlr_mean_lmp": 18.66,
    "q2_hourly_dlr_mean_lmp": 17.98,
    "table_vii_q2_daily_operational_cost_musd": 8.09,
}

def _scenario_metrics(name: str, d: dict) -> dict:
    bus = d["bus"]
    renew = d["renew"]
    hourly = d["hourly"]
    out = {"Scenario": name}
    if bus.empty:
        out.update({
            "n_bus_rows": 0,
            "lmp_mean": np.nan,
            "lmp_median": np.nan,
            "lmp_min": np.nan,
            "lmp_max": np.nan,
            "neg_lmp_frac": np.nan,
            "floor_hit_frac": np.nan,
            "sys_lmp_load_weighted": np.nan,
        })
    else:
        lmp_col = "LMP DA" if "LMP DA" in bus.columns else "LMP"
        out["n_bus_rows"] = len(bus)
        out["lmp_mean"] = float(bus[lmp_col].mean())
        out["lmp_median"] = float(bus[lmp_col].median())
        out["lmp_min"] = float(bus[lmp_col].min())
        out["lmp_max"] = float(bus[lmp_col].max())
        out["neg_lmp_frac"] = float((bus[lmp_col] < 0).mean())
        out["floor_hit_frac"] = float((bus[lmp_col] <= -1000).mean())
        denom = bus["Demand"].sum()
        out["sys_lmp_load_weighted"] = float(((bus["Demand"] * bus[lmp_col]).sum() / denom) if denom > 0 else np.nan)

    if renew.empty:
        out["renew_curtailment_total"] = np.nan
    else:
        out["renew_curtailment_total"] = float(renew["Curtailment"].sum()) if "Curtailment" in renew.columns else np.nan

    if hourly.empty:
        out["overgeneration_total"] = np.nan
        out["load_shedding_total"] = np.nan
        out["reserve_shortfall_total"] = np.nan
    else:
        out["overgeneration_total"] = float(hourly["OverGeneration"].sum()) if "OverGeneration" in hourly.columns else np.nan
        out["load_shedding_total"] = float(hourly["LoadShedding"].sum()) if "LoadShedding" in hourly.columns else np.nan
        out["reserve_shortfall_total"] = float(hourly["ReserveShortfall"].sum()) if "ReserveShortfall" in hourly.columns else np.nan
    return out


metrics_df = pd.DataFrame([_scenario_metrics(name, d) for name, d in windowed.items()])
display(metrics_df)

summary_json = {
    "overlap_window_start": str(overlap_start),
    "overlap_window_end": str(overlap_end),
    "paper_reference": paper_reference,
    "metrics": metrics_df.to_dict(orient="records"),
}
summary_path = pcm_dir / "PCM_result_hydro_q1_comparison.json"
summary_path.write_text(json.dumps(summary_json, indent=2))
print("Wrote", summary_path)"""
        )
    )

    cells.append(md_cell("## 9. Comparative Plots"))

    cells.append(
        code_cell(
            """# Hourly load-weighted LMP trajectories
fig, axes = plt.subplots(2, 2, figsize=(16, 10))

ax = axes[0, 0]
for name, d in windowed.items():
    s = _load_weighted_lmp(d["bus"])
    if s.empty:
        continue
    ax.plot(s.index, s.values, label=name, linewidth=1.0, color=scenarios[name]["color"])
ax.axhline(0, color="black", linewidth=0.7)
ax.set_title("Hourly Load-Weighted LMP (Overlap Window)")
ax.set_ylabel("$/MWh")
ax.legend(fontsize=8)

# Daily average
ax = axes[0, 1]
for name, d in windowed.items():
    s = _load_weighted_lmp(d["bus"])
    if s.empty:
        continue
    daily = s.resample("D").mean()
    ax.plot(daily.index, daily.values, marker="o", label=name, color=scenarios[name]["color"])
ax.axhline(0, color="black", linewidth=0.7)
ax.set_title("Daily Avg Load-Weighted LMP")
ax.set_ylabel("$/MWh")
ax.legend(fontsize=8)

# LMP distribution
ax = axes[1, 0]
for name, d in windowed.items():
    bus = d["bus"]
    if bus.empty:
        continue
    col = "LMP DA" if "LMP DA" in bus.columns else "LMP"
    ax.hist(bus[col], bins=120, alpha=0.4, label=name, color=scenarios[name]["color"], density=True)
ax.axvline(0, color="black", linewidth=0.7)
ax.set_title("LMP Distribution")
ax.set_xlabel("$/MWh")
ax.legend(fontsize=8)

# Negative LMP by hour-of-day
ax = axes[1, 1]
for name, d in windowed.items():
    bus = d["bus"]
    if bus.empty:
        continue
    col = "LMP DA" if "LMP DA" in bus.columns else "LMP"
    tmp = bus.copy()
    tmp["H"] = tmp["Datetime"].dt.hour
    neg_h = tmp.groupby("H").apply(lambda x: (x[col] < 0).mean() * 100)
    ax.plot(neg_h.index, neg_h.values, marker="o", label=name, color=scenarios[name]["color"])
ax.set_title("Negative LMP Frequency by Hour")
ax.set_xlabel("Hour")
ax.set_ylabel("%")
ax.legend(fontsize=8)

plt.tight_layout()
plt.show()"""
        )
    )

    cells.append(
        md_cell(
            """## 10. Paper Benchmark Comparison (Hardcoded References)

This section uses paper reference values hardcoded from prior notebook analysis:

- Typical positive LMP range: **10–50 $/MWh**
- Q2 Daily DLR mean LMP: **$18.66/MWh**
- Q2 Hourly DLR mean LMP: **$17.98/MWh**
- Table VII operational cost reference: **$8.09M/day (Q2 normal day)**"""
        )
    )

    cells.append(
        code_cell(
            """paper_rows = [
    {"Metric": "Typical LMP range", "Paper": "10 to 50 (mostly positive)"},
    {"Metric": "Q2 daily DLR mean LMP", "Paper": "18.66"},
    {"Metric": "Q2 hourly DLR mean LMP", "Paper": "17.98"},
    {"Metric": "Q2 daily operational cost ($M/day)", "Paper": "8.09"},
]
paper_df = pd.DataFrame(paper_rows)

comp = metrics_df[[
    "Scenario",
    "lmp_mean",
    "lmp_median",
    "lmp_min",
    "lmp_max",
    "neg_lmp_frac",
    "sys_lmp_load_weighted",
]].copy()
comp["neg_lmp_frac_pct"] = comp["neg_lmp_frac"] * 100
display(paper_df)
display(comp.sort_values("Scenario"))"""
        )
    )

    cells.append(
        md_cell(
            """## 11. Benchmark-Oriented Discussion

### Interpretation notes

- If hydro scenarios still show frequent negative LMP and floor hits (`-1000`), the model remains far from paper-like positive-price behavior.
- Compare hydro UC+ED vs hydro UC-only first to isolate dispatch-mode effect under the same network.
- Compare both hydro scenarios against no-hydro Q1 baseline to quantify hydro/case-design impact on price distribution.
- Q1 is intentionally used as a low-cost benchmark proxy; if Q1 alignment improves, then scale to longer runs.

### Next-step tuning directions for PCM closer to paper

1. Validate curtailment treatment and renewable representation consistency against paper assumptions.
2. Recheck price-cap and mismatch penalty settings for benchmark mode.
3. Align chronology/horizon and reserve assumptions before comparing absolute price magnitudes.
4. When Q1 improves, promote to longer horizon to test robustness."""
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
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    notebook = build_notebook()
    out_path = Path(
        "/Users/yilu/Documents/GitHub/idaes-gtep/gtep/pcm_analysis/"
        "prescient_lmp_analysis_with_hydro_q1.ipynb"
    )
    out_path.write_text(json.dumps(notebook, indent=2))
    print(f"Wrote notebook: {out_path}")


if __name__ == "__main__":
    main()
