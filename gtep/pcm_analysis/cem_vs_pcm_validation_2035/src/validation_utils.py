"""Shared helpers for the 2035 TSA-error analysis notebook.

Factorial: 2 EP scenarios (no-extreme, extreme) x 2 PCM configs (A=PTDF/sh6/rh36,
B=btheta/sh24/rh48) = 4 runs. Helpers re-expose the patterns from
prescient_lmp_analysis_2035.ipynb as importable functions so the notebook stays
thin; the Prescient IO primitive is imported from gtep.pcm_analysis._io.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from gtep.pcm_analysis._io import prescient_output_to_df

REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = REPO_ROOT / "gtep" / "data"
TSA_ROOT = REPO_ROOT / "gtep" / "pcm_analysis" / "tsa_2035"
RESULTS_ROOT = TSA_ROOT / "results"

EXPECTED_FUEL_MC = {"NUC": 7.38, "COAL": 18.94, "CT": 22.80}
GTEP_REP_WEIGHT = 5 * 365 / 4  # 456.25 hours per representative period


@dataclass
class RunSpec:
    """One of four (scenario x config) runs."""

    key: str
    scenario: str
    config: str
    results_dir: Path
    gen_csv: Path
    expected_n_gens: int
    label: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            self.label = f"{self.scenario} / {self.config}"


@dataclass
class RunData:
    """Loaded artifacts plus a validity banner."""

    spec: RunSpec
    valid: bool
    reasons: list[str] = field(default_factory=list)
    overall: pd.DataFrame | None = None
    hourly: pd.DataFrame | None = None
    daily: pd.DataFrame | None = None
    bus_detail: pd.DataFrame | None = None
    thermal_detail: pd.DataFrame | None = None
    renewables_detail: pd.DataFrame | None = None
    gen: pd.DataFrame | None = None

    @property
    def banner(self) -> str:
        if self.valid:
            return ""
        return " [INVALID - stand-in only: " + "; ".join(self.reasons) + "]"


def run_registry() -> Mapping[str, RunSpec]:
    """Canonical 4-cell factorial. Edit here when results dirs move."""

    no_ext = DATA_ROOT / "retirement_allowed_no_extreme_half_load_local" / "Prescient_2_2035"
    ext = DATA_ROOT / "retirement_allowed_extreme_half_load" / "Prescient_2_2035"

    return {
        "no_extreme_A": RunSpec(
            key="no_extreme_A",
            scenario="no_extreme",
            config="A_ptdf_sh6_rh36",
            results_dir=no_ext / "results",
            gen_csv=no_ext / "gen.csv",
            expected_n_gens=278,
            label="no-extreme / PTDF sh=6 rh=36",
        ),
        "no_extreme_B": RunSpec(
            key="no_extreme_B",
            scenario="no_extreme",
            config="B_btheta_sh24_rh48",
            results_dir=no_ext / "results_2",
            gen_csv=no_ext / "gen.csv",
            expected_n_gens=278,
            label="no-extreme / btheta sh=24 rh=48",
        ),
        "extreme_A": RunSpec(
            key="extreme_A",
            scenario="extreme",
            config="A_ptdf_sh6_rh36",
            results_dir=ext / "results",
            gen_csv=ext / "gen.csv",
            expected_n_gens=289,
            label="extreme / PTDF sh=6 rh=36",
        ),
        "extreme_B": RunSpec(
            key="extreme_B",
            scenario="extreme",
            config="B_btheta_sh24_rh48",
            results_dir=ext / "results_2",
            gen_csv=ext / "gen.csv",
            expected_n_gens=289,
            label="extreme / btheta sh=24 rh=48",
        ),
    }


def load_run(spec: RunSpec, *, heavy: bool = True) -> RunData:
    """Load one run. If the directory is empty or fleet count mismatches,
    return RunData(valid=False, reasons=[...]) so the notebook can banner it.

    Set heavy=False to skip the big bus/thermal/renewables details (cheaper QC).
    """
    data = RunData(spec=spec, valid=True)
    rd = spec.results_dir

    overall_path = rd / "overall_simulation_output.csv"
    if not overall_path.exists():
        data.valid = False
        data.reasons.append("overall_simulation_output.csv missing")
        return data

    data.overall = pd.read_csv(overall_path)
    try:
        data.hourly = prescient_output_to_df(rd / "hourly_summary.csv")
    except FileNotFoundError:
        data.valid = False
        data.reasons.append("hourly_summary.csv missing")
        return data

    daily_path = rd / "daily_summary.csv"
    if daily_path.exists():
        data.daily = prescient_output_to_df(daily_path)

    if heavy:
        data.bus_detail = prescient_output_to_df(rd / "bus_detail.csv")
        data.thermal_detail = prescient_output_to_df(rd / "thermal_detail.csv")
        data.renewables_detail = prescient_output_to_df(rd / "renewables_detail.csv")

    if spec.gen_csv.exists():
        data.gen = pd.read_csv(spec.gen_csv)
        if len(data.gen) != spec.expected_n_gens:
            data.valid = False
            data.reasons.append(
                f"gen.csv has {len(data.gen)} rows, expected {spec.expected_n_gens}"
            )

    if heavy and data.thermal_detail is not None:
        observed = data.thermal_detail["Generator"].nunique()
        gen_df = data.gen if data.gen is not None else pd.DataFrame({"Unit Type": []})
        expected_thermal = int(
            (~gen_df.get("Unit Type", pd.Series(dtype=str)).isin(["WIND", "PV", "HYDRO"])).sum()
        )
        if expected_thermal > 0 and observed != expected_thermal:
            data.valid = False
            data.reasons.append(
                f"thermal_detail has {observed} generators, expected {expected_thermal}"
            )
            if data.gen is not None:
                counts = data.gen["Unit Type"].value_counts().to_dict()
                print(f"[tsa_utils] {spec.key} fleet diagnosis: {counts}")
    return data


def load_weighted_lmp(bus_df: pd.DataFrame, demand_floor_mw: float = 1.0) -> float:
    """System-wide load-weighted LMP DA over the whole period.

    Falls back to simple mean when total demand is below the floor (per MEMORY.md).
    Silently drops rows with NaN in LMP DA or Demand so spurious buses don't
    contaminate the aggregate.
    """
    clean = bus_df.dropna(subset=["LMP DA", "Demand"])
    total_demand = clean["Demand"].sum()
    if total_demand < demand_floor_mw:
        warnings.warn(
            "Total demand below floor; using simple mean LMP as fallback",
            UserWarning,
            stacklevel=2,
        )
        return float(clean["LMP DA"].mean())
    weighted = (clean["Demand"] * clean["LMP DA"]).sum()
    return float(weighted / total_demand)


def load_weighted_lmp_hourly(bus_df: pd.DataFrame) -> pd.DataFrame:
    """Hourly load-weighted LMP timeseries.

    Hours with zero total demand land as NaN (not 0) so downstream plotters
    show a gap rather than a misleading zero point.
    """
    tmp = bus_df.dropna(subset=["LMP DA", "Demand"])[["Datetime", "Demand", "LMP DA"]].copy()
    tmp["_wt_lmp"] = tmp["Demand"] * tmp["LMP DA"]
    agg = tmp.groupby("Datetime").agg(demand=("Demand", "sum"), wt=("_wt_lmp", "sum"))
    agg["LW_LMP"] = np.where(agg["demand"] > 0, agg["wt"] / agg["demand"], np.nan)
    return agg.reset_index()[["Datetime", "demand", "LW_LMP"]]


def curtailment_total(renew_df: pd.DataFrame) -> float:
    """Total MWh curtailed. Uses the Prescient-emitted `Curtailment` column."""
    if "Curtailment" not in renew_df.columns:
        raise KeyError(
            "renewables_detail.csv is missing the 'Curtailment' column. "
            "Do not use Output DA - Output as a proxy; that is DA->RT re-dispatch, "
            "not curtailment."
        )
    return float(renew_df["Curtailment"].sum())


def headline_metrics(data: RunData) -> dict[str, float]:
    """One-row metrics dict per run."""
    if data.overall is None or data.overall.empty:
        return {"key": data.spec.key, "valid": data.valid}
    o = data.overall.iloc[0]
    row: dict[str, float] = {
        "key": data.spec.key,
        "scenario": data.spec.scenario,
        "config": data.spec.config,
        "valid": data.valid,
        "total_demand_TWh": float(o.get("Total demand", float("nan"))) / 1e6,
        "total_gen_cost_B$": float(o.get("Total generation costs", float("nan"))) / 1e9,
        "total_fixed_cost_B$": float(o.get("Total fixed costs", float("nan"))) / 1e9,
        "total_cost_B$": float(o.get("Total costs", float("nan"))) / 1e9,
        "cumulative_avg_price_$MWh": float(o.get("Cumulative average price", float("nan"))),
        "total_energy_payments_B$": float(o.get("Total energy payments", float("nan"))) / 1e9,
        "load_shedding_MWh": float(o.get("Total load shedding", float("nan"))),
        "curtailment_MWh_overall": float(o.get("Total renewables curtailment", float("nan"))),
        "reserve_shortfall_MWh": float(o.get("Total reserve shortfall", float("nan"))),
        "on_offs": float(o.get("Total on/offs", float("nan"))),
    }
    if data.bus_detail is not None:
        row["load_weighted_lmp_$MWh"] = load_weighted_lmp(data.bus_detail)
    return row


def factorial_dataframe(datasets: Mapping[str, RunData]) -> pd.DataFrame:
    """Collect headline_metrics across all runs into a 4-row DataFrame."""
    return pd.DataFrame([headline_metrics(d) for d in datasets.values()])


def load_gtep_stage3_cost() -> Mapping[str, object] | None:
    """Read the JSON produced by extract_gtep_stage3_cost.py. Returns None if missing.

    The extractor now emits a single JSON for the committed GTEP configuration,
    not per-scenario. Callers should interpret the payload as applying to
    whichever EP scenario matches `driver_coal.py` as committed (today: the
    no-extreme case).
    """
    path = RESULTS_ROOT / "gtep_stage3_cost.json"
    if not path.exists():
        return None
    with path.open() as fh:
        return json.load(fh)


def compute_tsa_error(
    gtep_payload: Mapping[str, object] | None,
    pcm_total_gen_cost: float,
) -> dict[str, float | str]:
    """Aggregate the GTEP rep-period op-cost and compute the GTEP-vs-PCM gap.

    Primary path reads `total_operating_cost_stage3` (already equal to
    `m.investmentStage[3].operatingCostInvestment`, which bakes in weight and
    investment_factor per gtep_model.py:407-418).
    Fallback sums `op_cost * weight * investment_factor` across per_rep_period.
    """
    if gtep_payload is None:
        return {
            "gtep_annualized_opcost_B$": float("nan"),
            "pcm_total_gen_cost_B$": pcm_total_gen_cost / 1e9,
            "tsa_error_B$": float("nan"),
            "tsa_error_pct": float("nan"),
            "note": "GTEP cost JSON missing; run extract_gtep_stage3_cost.py",
        }
    gtep_total = gtep_payload.get("total_operating_cost_stage3")
    if gtep_total is None:
        reps: Iterable[Mapping[str, float]] = gtep_payload.get("per_rep_period", [])
        gtep_total = sum(
            float(rp["op_cost"])
            * float(rp["weight"])
            * float(rp.get("investment_factor", 1.0))
            for rp in reps
        )
    gtep_total = float(gtep_total)
    error = gtep_total - pcm_total_gen_cost
    pct = error / pcm_total_gen_cost * 100 if pcm_total_gen_cost else float("nan")
    return {
        "gtep_annualized_opcost_B$": gtep_total / 1e9,
        "pcm_total_gen_cost_B$": pcm_total_gen_cost / 1e9,
        "tsa_error_B$": error / 1e9,
        "tsa_error_pct": pct,
        "note": "",
    }


def slice_rep_days(hourly_df: pd.DataFrame, calendar_days: list[str]) -> pd.DataFrame:
    """Keep only hours that fall on the given calendar days (YYYY-MM-DD strings)."""
    if hourly_df is None or hourly_df.empty or not calendar_days:
        return pd.DataFrame()
    targets = pd.to_datetime(calendar_days).normalize()
    return hourly_df[hourly_df["Datetime"].dt.normalize().isin(targets)].copy()


def _daily_gen_cost_usd(data: RunData) -> pd.Series:
    """PCM generation cost (fuel + startup) per calendar day, USD.

    Prefers Prescient's pre-aggregated `daily_summary.csv["Generation costs"]`;
    falls back to hourly roll-up of `thermal_detail["Unit Cost"]`.
    """
    if data.daily is not None and "Generation costs" in data.daily.columns:
        s = data.daily.set_index(data.daily["Datetime"].dt.normalize())["Generation costs"]
        s.index.name = "day"
        return s.astype(float)
    if data.thermal_detail is None:
        return pd.Series(dtype=float, name="day")
    tmp = data.thermal_detail[["Datetime", "Unit Cost"]].copy()
    tmp["day"] = tmp["Datetime"].dt.normalize()
    return tmp.groupby("day")["Unit Cost"].sum().astype(float)


def rep_day_attribution(
    data: RunData,
    gtep_payload: Mapping[str, object] | None,
) -> pd.DataFrame:
    """Per-rep-period decomposition of the TSA error.

    Columns (all USD unless noted):
        rp, calendar_day, season_bucket, weight, investment_factor,
        gtep_opcost_scaled,      -- op_cost * weight * investment_factor
        pcm_day_cost,            -- PCM cost on calendar_day
        pcm_day_cost_scaled,     -- weight * pcm_day_cost
        pcm_season_cost,         -- PCM cost summed over season_bucket
        sampling_error,          -- GTEP day vs PCM day (scaled)
        aggregation_error,       -- PCM day * weight vs PCM season
        total_error              -- sum of the two

    Sum of `total_error` over rows reconstructs the headline TSA error (up
    to one shared investment_factor; defaults to 1).

    PCM per-day cost source: daily_summary["Generation costs"] if present,
    else thermal_detail groupby. Season bucket default: the calendar quarter
    containing the rep day (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec).
    """
    if gtep_payload is None or data.overall is None:
        return pd.DataFrame()
    reps = list(gtep_payload.get("per_rep_period", []))
    if not reps:
        return pd.DataFrame()

    daily_cost = _daily_gen_cost_usd(data)
    if daily_cost.empty:
        return pd.DataFrame()

    # Build quarter buckets once; the rep day's calendar-year quarter gets
    # matched against the PCM year's quarter (year in PCM data is 2035, rep
    # calendar dates are 2019 — we align on month).
    days = pd.to_datetime(daily_cost.index)
    quarter_map = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3, 9: 3, 10: 4, 11: 4, 12: 4}
    quarters = pd.Series(days.month.map(quarter_map).values, index=daily_cost.index, name="quarter")
    season_totals = daily_cost.groupby(quarters).sum()

    rows = []
    for rp in reps:
        rp_idx = int(rp["rp"])
        day_raw = rp.get("calendar_day")
        day_ts = pd.to_datetime(day_raw) if day_raw is not None else None
        rep_quarter = quarter_map.get(day_ts.month) if day_ts is not None else None

        # Align the rep day (2019) onto the PCM year (2035) by month+day.
        pcm_day_cost = float("nan")
        if day_ts is not None:
            pcm_year = daily_cost.index[0].year if len(daily_cost.index) else None
            if pcm_year is not None:
                try:
                    target = pd.Timestamp(year=pcm_year, month=day_ts.month, day=day_ts.day)
                    pcm_day_cost = float(daily_cost.get(target, float("nan")))
                except ValueError:  # Feb 29 on a non-leap year, etc.
                    pcm_day_cost = float("nan")

        weight = float(rp.get("weight", GTEP_REP_WEIGHT))
        inv_factor = float(rp.get("investment_factor", 1.0))
        op_cost = float(rp["op_cost"])
        gtep_scaled = op_cost * weight * inv_factor

        pcm_season_cost = (
            float(season_totals.get(rep_quarter, float("nan")))
            if rep_quarter is not None
            else float("nan")
        )
        pcm_day_scaled = pcm_day_cost * weight if pcm_day_cost == pcm_day_cost else float("nan")

        sampling = (
            gtep_scaled - pcm_day_scaled if pcm_day_scaled == pcm_day_scaled else float("nan")
        )
        aggregation = (
            pcm_day_scaled - pcm_season_cost
            if pcm_day_scaled == pcm_day_scaled and pcm_season_cost == pcm_season_cost
            else float("nan")
        )
        total = (
            sampling + aggregation
            if sampling == sampling and aggregation == aggregation
            else float("nan")
        )

        rows.append(
            {
                "rp": rp_idx,
                "calendar_day": day_raw,
                "season_bucket": f"Q{rep_quarter}" if rep_quarter else None,
                "weight": weight,
                "investment_factor": inv_factor,
                "gtep_opcost_scaled_$": gtep_scaled,
                "pcm_day_cost_$": pcm_day_cost,
                "pcm_day_cost_scaled_$": pcm_day_scaled,
                "pcm_season_cost_$": pcm_season_cost,
                "sampling_error_$": sampling,
                "aggregation_error_$": aggregation,
                "total_error_$": total,
            }
        )
    return pd.DataFrame(rows)


def marginal_cost_sanity(data: RunData) -> pd.DataFrame:
    """Per-fuel observed MC from Unit Cost / Dispatch. Compare to EXPECTED_FUEL_MC."""
    if data.thermal_detail is None or data.gen is None:
        return pd.DataFrame()
    gen_info = data.gen[["GEN UID", "Unit Type"]].rename(columns={"GEN UID": "Generator"})
    merged = data.thermal_detail.merge(gen_info, on="Generator", how="left")
    disp = merged[merged["Dispatch"] > 0.1].copy()
    if disp.empty:
        return pd.DataFrame()
    disp["observed_mc"] = disp["Unit Cost"] / disp["Dispatch"]
    summary = disp.groupby("Unit Type").agg(
        n_hours=("observed_mc", "size"),
        mc_median=("observed_mc", "median"),
        mc_mean=("observed_mc", "mean"),
        gen_gwh=("Dispatch", lambda s: s.sum() / 1e3),
    )
    summary["expected_mc"] = [EXPECTED_FUEL_MC.get(u, float("nan")) for u in summary.index]
    summary["pct_err"] = (
        (summary["mc_median"] - summary["expected_mc"]).abs()
        / summary["expected_mc"].where(summary["expected_mc"] > 0, 1.0)
    ) * 100
    return summary.reset_index()


def banner_title(base: str, data: RunData) -> str:
    """Attach the invalid-run banner to a plot/table title."""
    return f"{base}{data.banner}" if data.banner else base
