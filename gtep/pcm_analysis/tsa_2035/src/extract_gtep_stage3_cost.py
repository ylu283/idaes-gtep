"""Re-solve the committed GTEP coal-retirement model and dump stage-3 op-cost.

Output: `tsa_2035/results/gtep_stage3_cost.json`.

Schema (consumed by tsa_utils.compute_tsa_error + rep_day_attribution):
    {
      "scenario": "committed_default",   # see note below
      "stage_index": 3,
      "per_rep_period": [
          {"rp": 1, "op_cost": float, "weight": 456.25,
           "investment_factor": 1.0, "annualized": float,
           "calendar_day": "YYYY-MM-DD"},
          ...
      ],
      "total_operating_cost_stage3": float,    # annualized ($); == pyo.value(stage3.operatingCostInvestment)
      "expansion_cost_stage3": float,          # annualized ($)
      "objective_value": float,                # full-horizon objective ($)
      "representative_dates": [str, ...],      # all dates from data_object (may exceed num_reps)
      "notes": [...]
    }

The script solves whatever `driver_coal.py` as committed produces -- today this
is the "no-extreme" planning scenario. The "extreme" scenario's GTEP solve is
not reproducible from committed code (only the post-conversion Prescient
inputs and the resulting investment JSONs are tracked); downstream tooling
must annotate that limitation.

Usage:
    python gtep/pcm_analysis/tsa_2035/src/extract_gtep_stage3_cost.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE.parent / "results"
REPO_ROOT = HERE.parents[3]
DATA_PATH = REPO_ROOT / "gtep" / "data" / "123_Bus_Coal"

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
    total_op = float(pyo.value(stage_block.operatingCostInvestment))
    expansion = float(pyo.value(stage_block.investment_cost))
    inv_factor = float(pyo.value(model.investmentFactor[stage_index]))

    representative_dates = list(getattr(mod_object.data, "representative_dates", []))
    if len(representative_dates) < GTEP_BASELINE_CONFIG["num_reps"]:
        raise RuntimeError(
            "data_object.representative_dates has "
            f"{len(representative_dates)} entries, need at least "
            f"{GTEP_BASELINE_CONFIG['num_reps']}. Inspect gtep_data.py line 73+."
        )

    per_rep = []
    annualized_sum = 0.0
    for rp_index, rp in enumerate(model.representativePeriods, start=1):
        rep_op = 0.0
        for cp in stage_block.representativePeriod[rp].commitmentPeriods:
            rep_op += float(
                pyo.value(
                    stage_block.representativePeriod[rp]
                    .commitmentPeriod[cp]
                    .operatingCostCommitment
                )
            )
        weight = float(pyo.value(model.weights[rp]))
        annualized = rep_op * weight * inv_factor
        annualized_sum += annualized
        # representative_dates may be longer than num_reps; take first num_reps.
        calendar_day = representative_dates[rp_index - 1][:10]
        per_rep.append(
            {
                "rp": int(rp),
                "op_cost": rep_op,
                "weight": weight,
                "investment_factor": inv_factor,
                "annualized": annualized,
                "calendar_day": calendar_day,
            }
        )

    # Consistency assertion: per-rep annualized costs must roll up to the
    # composite operatingCostInvestment expression the GTEP objective uses.
    rel_err = abs(annualized_sum - total_op) / max(abs(total_op), 1.0)
    if rel_err > 1e-6:
        raise AssertionError(
            f"Per-rep annualized sum ({annualized_sum:.6e}) does not match "
            f"stage_block.operatingCostInvestment ({total_op:.6e}); "
            f"relative error {rel_err:.2e}. Check weights / investmentFactor."
        )

    if len(representative_dates) > GTEP_BASELINE_CONFIG["num_reps"]:
        notes.append(
            "data_object.representative_dates has "
            f"{len(representative_dates)} entries; "
            f"mapped first {GTEP_BASELINE_CONFIG['num_reps']} to rep periods. "
            f"Extras: {representative_dates[GTEP_BASELINE_CONFIG['num_reps']:]}"
        )

    return {
        "scenario": "committed_default",
        "stage_index": int(stage_index),
        "per_rep_period": per_rep,
        "total_operating_cost_stage3": total_op,
        "expansion_cost_stage3": expansion,
        "objective_value": objective_value,
        "representative_dates": representative_dates,
        "notes": notes,
    }


def solve_and_dump() -> Path:
    from pyomo.contrib.solver.common.results import TerminationCondition
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

    # Termination check -- no silent failures.
    terminated_ok = (
        getattr(results, "termination_condition", None) == TerminationCondition.convergenceCriteriaSatisfied
    ) or str(getattr(results, "termination_condition", "")).endswith("optimal")
    if not terminated_ok:
        raise RuntimeError(
            f"GTEP solver did not terminate optimally: "
            f"termination_condition={results.termination_condition!r}"
        )

    objective_value = (
        float(results.best_feasible_objective)
        if results.best_feasible_objective is not None
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
