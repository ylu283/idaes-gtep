"""Re-solve the committed GTEP coal-retirement model and dump stage-3 op-cost.

Output: `cem_vs_pcm_validation_2035/results/gtep_stage3_cost.json`.

## 5-year vs 1-year scaling (IMPORTANT)

`m.investmentStage[3].operatingCostInvestment` is the operating cost over the
FULL 5-year investment stage (stages are spaced 5 years apart: 2025, 2030,
2035 -> each stage represents 5 years of operation). The per-rep weight in
`gtep_model.py:1849` is `5*365/4 = 456.25 days per rep x 4 reps = 1825 days
= 5 calendar years`. The extractor therefore emits BOTH:

- `total_operating_cost_stage3_5yr` -- the raw Pyomo expression value
- `total_operating_cost_stage3_1yr` -- annualized (5yr / 5)

Use `_1yr` to compare against a 1-year PCM realized cost
(`overall_simulation_output.csv["Total generation costs"]`). Subtracting the
5-year value from a 1-year PCM cost over-states the CEM-vs-PCM gap by ~5x.

## Schema

    {
      "scenario": "committed_default",
      "stage_index": 3,
      "stage_length_years": 5,
      "per_rep_period": [
          {"rp": 1, "op_cost_per_rep": float, "weight_days": float,
           "investment_factor": 1.0,
           "stage_contribution_5yr_$": float,
           "single_year_contribution_$": float,
           "calendar_day": "YYYY-MM-DD"},
          ...
      ],
      "total_operating_cost_stage3_5yr": float,   # == pyo.value(stage3.operatingCostInvestment)
      "total_operating_cost_stage3_1yr": float,   # stage3_5yr / 5
      "expansion_cost_stage3_5yr": float,
      "objective_value": float,                   # full-horizon objective
      "representative_dates": [str, ...],
      "notes": [...]
    }

Usage (local or on CRC):
    python gtep/pcm_analysis/cem_vs_pcm_validation_2035/src/extract_gtep_stage3_cost.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE.parent / "results"
REPO_ROOT = HERE.parents[3]
DATA_PATH = REPO_ROOT / "gtep" / "data" / "123_Bus_Coal"

# GTEP plans at 5-year stage granularity: stages {2025, 2030, 2035}.
STAGE_LENGTH_YEARS = 5

GTEP_BASELINE_CONFIG = {
    "stages": 3,
    "num_reps": 4,
    "len_reps": 24,
    "num_commit": 24,
    "num_dispatch": 1,
}


def _extract(mod_object, objective_value: float | None) -> dict:
    import pyomo.environ as pyo

    model = mod_object.model
    notes: list[str] = []

    stages = list(model.stages)
    stage_index = stages[-1]
    if stage_index != 3:
        notes.append(f"Expected stage index 3, got {stage_index}; using last stage")

    stage_block = model.investmentStage[stage_index]
    total_op_5yr = float(pyo.value(stage_block.operatingCostInvestment))
    expansion_5yr = float(pyo.value(stage_block.investment_cost))
    inv_factor = float(pyo.value(model.investmentFactor[stage_index]))

    # investmentFactor != 1 means NPV discounting is active (see gtep_model.py:1854
    # for the disabled 1/(1.04^(5 stage)) formula). Comparing an NPV-discounted
    # CEM cost to a realized-dollar PCM cost is a currency mismatch; refuse.
    if abs(inv_factor - 1.0) > 1e-9:
        raise RuntimeError(
            f"investmentFactor[{stage_index}] = {inv_factor} (expected 1). "
            "NPV discounting is active -- CEM cost is in present-value dollars, "
            "while PCM cost is realized. Disable NPV in gtep_model.py:1854 or "
            "un-discount here before comparing."
        )

    representative_dates = list(getattr(mod_object.data, "representative_dates", []))
    if len(representative_dates) < GTEP_BASELINE_CONFIG["num_reps"]:
        raise RuntimeError(
            "data_object.representative_dates has "
            f"{len(representative_dates)} entries, need at least "
            f"{GTEP_BASELINE_CONFIG['num_reps']}. Inspect gtep_data.py line 73+."
        )

    per_rep = []
    stage_contribution_sum = 0.0
    for rp_index, rp in enumerate(model.representativePeriods, start=1):
        rep_op_per_rep = 0.0
        for cp in stage_block.representativePeriod[rp].commitmentPeriods:
            rep_op_per_rep += float(
                pyo.value(
                    stage_block.representativePeriod[rp]
                    .commitmentPeriod[cp]
                    .operatingCostCommitment
                )
            )
        weight_days = float(pyo.value(model.weights[rp]))
        stage_contribution_5yr = rep_op_per_rep * weight_days * inv_factor
        stage_contribution_sum += stage_contribution_5yr
        calendar_day = representative_dates[rp_index - 1][:10]
        per_rep.append(
            {
                "rp": int(rp),
                "op_cost_per_rep": rep_op_per_rep,
                "weight_days": weight_days,
                "investment_factor": inv_factor,
                "stage_contribution_5yr_$": stage_contribution_5yr,
                "single_year_contribution_$": stage_contribution_5yr / STAGE_LENGTH_YEARS,
                "calendar_day": calendar_day,
            }
        )

    # Consistency: per-rep contributions must sum to operatingCostInvestment.
    rel_err = abs(stage_contribution_sum - total_op_5yr) / max(abs(total_op_5yr), 1.0)
    if rel_err > 1e-6:
        raise AssertionError(
            f"Per-rep stage-contribution sum ({stage_contribution_sum:.6e}) does not "
            f"match stage_block.operatingCostInvestment ({total_op_5yr:.6e}); "
            f"relative error {rel_err:.2e}. Check weights / investmentFactor."
        )

    if len(representative_dates) > GTEP_BASELINE_CONFIG["num_reps"]:
        notes.append(
            "data_object.representative_dates has "
            f"{len(representative_dates)} entries; "
            f"mapped first {GTEP_BASELINE_CONFIG['num_reps']} to rep periods. "
            f"Extras: {representative_dates[GTEP_BASELINE_CONFIG['num_reps']:]}"
        )
    notes.append(
        f"Stage horizon is {STAGE_LENGTH_YEARS} years. "
        f"Use total_operating_cost_stage3_1yr for 1-year PCM comparison."
    )

    return {
        "scenario": "committed_default",
        "stage_index": int(stage_index),
        "stage_length_years": STAGE_LENGTH_YEARS,
        "per_rep_period": per_rep,
        "total_operating_cost_stage3_5yr": total_op_5yr,
        "total_operating_cost_stage3_1yr": total_op_5yr / STAGE_LENGTH_YEARS,
        "expansion_cost_stage3_5yr": expansion_5yr,
        "objective_value": objective_value,
        "representative_dates": representative_dates,
        "notes": notes,
    }


def solve_and_dump() -> Path:
    from pyomo.contrib.solver.solvers.gurobi_direct import GurobiDirect
    from pyomo.core import TransformationFactory

    from gtep.gtep_data import ExpansionPlanningData
    from gtep.gtep_model import ExpansionPlanningModel

    data_object = ExpansionPlanningData()
    data_object.load_prescient(str(DATA_PATH))
    data_object.import_load_scaling(str(DATA_PATH / "ERCOT-Adjusted-Forecast.xlsb"))
    data_object.texas_case_study_updates(str(DATA_PATH))

    mod_object = ExpansionPlanningModel(data=data_object, **GTEP_BASELINE_CONFIG)
    mod_object.config["include_investment"] = True
    mod_object.config["scale_loads"] = False
    mod_object.config["scale_texas_loads"] = True
    mod_object.config["transmission"] = False
    mod_object.config["flow_model"] = "CP"

    mod_object.create_model()
    TransformationFactory("gdp.bigm").apply_to(mod_object.model)

    opt = GurobiDirect()
    results = opt.solve(
        mod_object.model, tee=True, solver_options={"LogFile": "basic_logging.log"}
    )
    mod_object.results = results

    # Termination check -- portable across pyomo versions. The enum location
    # (pyomo.contrib.solver.common.results vs pyomo.opt) moved between 6.7
    # and 6.9, so we check by string suffix.
    tc = getattr(results, "termination_condition", None)
    tc_str = str(tc).lower()
    terminated_ok = tc_str.endswith("optimal") or tc_str.endswith("convergencecriteriasatisfied")
    if not terminated_ok:
        raise RuntimeError(
            f"GTEP solver did not terminate optimally: termination_condition={tc!r}"
        )

    objective_value = (
        float(results.best_feasible_objective)
        if getattr(results, "best_feasible_objective", None) is not None
        else None
    )

    payload = _extract(mod_object, objective_value)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "gtep_stage3_cost.json"
    with out_path.open("w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"Wrote {out_path}")
    return out_path


def main() -> None:
    solve_and_dump()


if __name__ == "__main__":
    main()
