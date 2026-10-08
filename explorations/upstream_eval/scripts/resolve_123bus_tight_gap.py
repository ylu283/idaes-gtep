"""Re-solve the 123-bus tutorial baseline and Experiment 1 at mip_rel_gap=1e-4.

Prompt 03 T1 step 3: a per-type energy miss beyond the 10 % band is a finding
and the case is re-solved once with a tight gap, reporting both numbers. This
script repeats the notebook's own setup (cells 5, 7, 9, 19) verbatim except
for the gap, a safety time limit, and separate output directories / logs.

Run from ``explorations/upstream_eval/output/123bus/`` (the notebook's cwd)::

    /opt/anaconda3/envs/gtep_up/bin/python ../../scripts/resolve_123bus_tight_gap.py

Writes ``soln_<case>_tight/``, ``highs_<case>_tight.log`` and
``tight_gap_results.md``.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pandas as pd
from pyomo.environ import SolverFactory, TransformationFactory, value
from pyomo.util.model_size import build_model_size_report

from gtep.gtep_data import ExpansionPlanningData
from gtep.gtep_data_processing import DataProcessing
from gtep.gtep_model import ExpansionPlanningModel
from gtep.gtep_solution import ExpansionPlanningSolution

logging.getLogger().setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

MIP_REL_GAP = 1e-4
TIME_LIMIT = 3600  # safety only; reported if hit

DATA_PATH = Path("../../../../gtep/data/123_Bus_Resil_Week")
COSTS = Path("../../../../gtep/data/costs")
REP_DAYS = ["2019-01-28 00:00", "2019-06-10 00:00"]
REP_WEIGHTS = {"2019-01-28 00:00": 140, "2019-06-10 00:00": 225}
CASES = {
    "baseline": {"scale_loads": False},
    "expr1": {"scale_loads": False, "include_investment": False},
}
STORED = {
    "baseline": {"COAL": 6.4307, "CT": 22.402249999999995, "WIND": 46.076880000000024},
    "expr1": {
        "COAL": 12.154599999999995,
        "CT": 39.881330000000034,
        "WIND": 22.873900000000003,
    },
}


def energy_by_type(gen_json: Path, unit_type: dict) -> dict:
    data = json.loads(gen_json.read_text())
    totals: dict[str, float] = {}
    for key, val in data.items():
        ut = unit_type[key.split(".")[-1]]
        totals[ut] = totals.get(ut, 0.0) + val / 1000
    return {k: totals[k] for k in sorted(totals)}


def highs_summary(log: Path) -> dict:
    import re

    txt = log.read_text()
    out = {}
    for label, pat in (
        ("status", r"^\s+Status\s+(.*)$"),
        ("gap", r"^\s+Gap\s+(.*)$"),
        ("nodes", r"^\s+Nodes\s+(\d+)"),
        ("timing", r"^\s+Timing\s+([\d.]+)"),
    ):
        m = re.search(pat, txt, re.M)
        out[label] = m.group(1).strip() if m else "n/a"
    return out


def main() -> int:
    unit_type = pd.read_csv(DATA_PATH / "gen.csv", index_col="GEN UID")[
        "Unit Type"
    ].to_dict()

    data_object = ExpansionPlanningData(
        stages=1,
        num_reps=2,
        num_commit=1,
        num_dispatch=1,
        duration_representative_period=1,
    )
    data_object.load_prescient(
        DATA_PATH, representative_dates=REP_DAYS, representative_weights=REP_WEIGHTS
    )
    cost_data = DataProcessing()
    cost_data.load_gen_data(
        bus_data_path=COSTS / "Bus_data_gen_weights_mappings.csv",
        cost_data_path=COSTS
        / "2022_v3_Annual_Technology_Baseline_Workbook_Mid-year_update_2-15-2023_Clean.xlsx",
        ng_cost_path=COSTS / "Total_Energy_Supply_Disposition_and_Price_Summary.csv",
        candidate_gens=["Natural Gas_FE", "Solar - Utility PV", "Land-Based Wind"],
    )

    lines = [
        f"# Tight-gap re-solve (mip_rel_gap={MIP_REL_GAP}, time_limit={TIME_LIMIT} s)",
        "",
        "| case | quantity | stored | 1 % gap run | 1e-4 gap run | rel. diff (tight vs stored) |",
        "|---|---|---|---|---|---|",
    ]
    summary = {}
    for case, config in CASES.items():
        mod = ExpansionPlanningModel(
            data=data_object, cost_data=cost_data, config=config
        )
        mod.create_model()
        TransformationFactory("gdp.bigm").apply_to(mod.model)
        size = build_model_size_report(mod.model)
        opt = SolverFactory("highs")
        opt.options["mip_rel_gap"] = MIP_REL_GAP
        opt.options["time_limit"] = TIME_LIMIT
        log = Path(f"highs_{case}_tight.log")
        t0 = time.perf_counter()
        with open(log, "w") as f, redirect_stdout(f), redirect_stderr(f):
            result = opt.solve(mod.model, tee=True)
        wall = time.perf_counter() - t0
        term = str(result["Solver"][0]["Termination condition"])
        obj = value(mod.model.total_cost_objective)
        out_dir = Path(f"soln_{case}_tight").resolve()
        ExpansionPlanningSolution(DATA_PATH).save_results_in_json_files(mod, out_dir)
        tight = energy_by_type(out_dir / "generation.json", unit_type)
        loose_dir = Path("soln" if case == "baseline" else "soln_expr1_local")
        loose = energy_by_type(loose_dir / "generation.json", unit_type)
        hs = highs_summary(log)
        summary[case] = dict(
            objective=obj,
            termination=term,
            wall=wall,
            gap=hs["gap"],
            nodes=hs["nodes"],
            timing=hs["timing"],
            rows=size.activated.constraints,
            cols=size.activated.variables,
            binaries=size.activated.binary_variables,
        )
        for ut in sorted(set(STORED[case]) | set(tight) | set(loose)) + ["total"]:
            s = (
                sum(STORED[case].values())
                if ut == "total"
                else STORED[case].get(ut, 0.0)
            )
            l = sum(loose.values()) if ut == "total" else loose.get(ut, 0.0)
            t = sum(tight.values()) if ut == "total" else tight.get(ut, 0.0)
            rd = f"{(t - s) / s:+.2%}" if s else "n/a (not in stored)"
            lines.append(f"| {case} | {ut} GWh | {s:.4f} | {l:.4f} | {t:.4f} | {rd} |")
        print(case, summary[case], tight, flush=True)
        del mod, opt

    lines += [
        "",
        "| case | objective (tight) | termination | HiGHS gap | nodes | solve wall s | rows / cols / binaries |",
        "|---|---|---|---|---|---|---|",
    ]
    for case, s in summary.items():
        lines.append(
            f"| {case} | {s['objective']:,.4f} | {s['termination']} | {s['gap']} | {s['nodes']} | "
            f"{s['wall']:.1f} | {s['rows']} / {s['cols']} / {s['binaries']} |"
        )
    Path("tight_gap_results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
