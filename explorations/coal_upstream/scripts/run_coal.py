"""Run the ERCOT 123-bus coal case (May 2026 study design) on upstream 7b84352.

Prompt 04 (admin/prompt/gtep/04-coal-case-on-upstream.md). Mirrors the call
chain of ``docs/source/tutorials/123bus/tutorial_123bus.ipynb``:
``ExpansionPlanningData`` -> ``load_prescient`` -> (optional) load scaling,
Texas updates, ``DataProcessing.load_gen_data`` -> ``ExpansionPlanningModel``
-> ``create_model`` -> ``gdp.bigm`` -> solve ->
``ExpansionPlanningSolution.save_results_in_json_files``.

Data-side steps this script adds (see the patch table in results_coal.md):

- ``fix``: shipped ``gtep/data/123_Bus_Coal/gen.csv`` fails upstream's own
  ``validate_required_columns`` (QMax/QMin empty for the 289 candidates,
  ``Ramp Rate MW/Min`` empty for all 581 rows). The script writes a copy of
  the directory under ``<out>/../_data/123_Bus_Coal`` with the values
  upstream itself used for ``123_Bus_Resil_Week`` in commit 42961c0
  (QMax 1, QMin -1, ramp 30). Shipped data is not touched.
- ``port``: 2HR / 4HR pre-aggregation (``aggregate.py``).
- weights: ``--weights may`` sets 91/91/91/92 (sum 365, upstream's rule) on
  the dates upstream auto-selects; upstream's default with no weights is 1
  per day.

Usage (from the worktree root)::

    $PY explorations/coal_upstream/scripts/run_coal.py --config 1HR \
        --cost-data off --scale-texas-loads off --stages 1 --num-reps 1 \
        --solver highs --mip-rel-gap 0.01 --time-limit 3600 \
        --out explorations/coal_upstream/output/A0
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import resource
import shutil
import sys
import time
import warnings
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pandas as pd
import pyomo.environ as pyo
from pyomo.contrib.solver.common.util import NoFeasibleSolutionError
from pyomo.util.model_size import build_model_size_report

from gtep.gtep_data import ExpansionPlanningData
from gtep.gtep_data_processing import DataProcessing
from gtep.gtep_model import ExpansionPlanningModel
from gtep.gtep_solution import ExpansionPlanningSolution

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate  # noqa: E402

logging.getLogger().setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[3]
SHIPPED_DATA = REPO / "gtep" / "data" / "123_Bus_Coal"
COSTS = REPO / "gtep" / "data" / "costs"
BLOCK_HOURS = {"1HR": 1, "2HR": 2, "4HR": 4}
CANDIDATES = ["Natural Gas_FE", "Solar - Utility PV", "Land-Based Wind"]
ZONE_NAMES = ["COAST", "EAST", "FWEST", "NCENT", "NORTH", "SCENT", "SOUTH", "WEST"]
STATUSES = ["Operational", "Installed", "Retired", "Disabled", "Extended"]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", choices=list(BLOCK_HOURS), default="1HR")
    p.add_argument("--cost-data", choices=["off", "on"], default="off")
    p.add_argument("--scale-texas-loads", choices=["off", "on"], default="off")
    p.add_argument("--stages", type=int, default=3)
    p.add_argument("--num-reps", type=int, default=4)
    p.add_argument("--weights", choices=["may", "upstream-default"], default="may")
    p.add_argument("--solver", choices=["highs", "gurobi"], default="highs")
    p.add_argument("--mip-rel-gap", type=float, default=0.01)
    p.add_argument("--time-limit", type=float, default=14400)
    p.add_argument("--threads", type=int, default=0, help="0 = solver default")
    p.add_argument(
        "--build-only", action="store_true", help="stop after Big-M + size report"
    )
    p.add_argument(
        "--diag-fix-all-off",
        action="store_true",
        help="instrument: fix every thermal unit genOff and candidate CTs "
        "genDisabled (a feasible point by construction) to certify feasibility",
    )
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args(argv)


def prepare_data_copy(dest_root: Path) -> Path:
    """Copy 123_Bus_Coal (top-level files) and fill the required gen.csv columns."""
    dest = dest_root / "123_Bus_Coal"
    dest.mkdir(parents=True, exist_ok=True)
    for f in SHIPPED_DATA.iterdir():
        if f.is_file():
            shutil.copy2(f, dest / f.name)
    # validate_required_columns looks for <data_path>.parent/required_data_files.csv
    shutil.copy2(SHIPPED_DATA.parent / "required_data_files.csv", dest_root)

    gen = pd.read_csv(SHIPPED_DATA / "gen.csv")
    cand = gen["GEN UID"].astype(str).str.endswith("-c")
    gen.loc[cand & gen["QMax MVAR"].isna(), "QMax MVAR"] = 1.0
    gen.loc[cand & gen["QMin MVAR"].isna(), "QMin MVAR"] = -1.0
    gen.loc[gen["Ramp Rate MW/Min"].isna(), "Ramp Rate MW/Min"] = 30
    gen.to_csv(dest / "gen.csv", index=False)

    # Egret's _read_branches iterates rows with iterrows(); an all-numeric
    # branch.csv upcasts each row to float64 and the bus lookup fails on
    # '98.0'. One text column keeps the row dtype object; values unchanged.
    branch = pd.read_csv(SHIPPED_DATA / "branch.csv")
    branch["Notes"] = "eval-fix"
    branch.to_csv(dest / "branch.csv", index=False)
    return dest


def may_weights(dates, num_reps):
    """Spread 365 days over the first num_reps dates (91/91/91/92 for 4)."""
    base, extra = divmod(365, num_reps)
    w = {d: base for d in dates}
    for d in dates[num_reps - extra : num_reps]:
        w[d] += 1
    return w


def highs_summary(log: Path) -> dict:
    txt = log.read_text(errors="replace")
    out = {}
    for label, pat in (
        ("status", r"^\s+Status\s+(.*)$"),
        ("primal_bound", r"^\s+Primal bound\s+(.*)$"),
        ("dual_bound", r"^\s+Dual bound\s+(.*)$"),
        ("gap", r"^\s+Gap\s+(.*)$"),
        ("nodes", r"^\s+Nodes\s+(\d+)"),
        ("timing", r"^\s+Timing\s+([\d.]+)"),
    ):
        m = re.search(pat, txt, re.M)
        out[label] = m.group(1).strip() if m else None
    return out


def binary_value(disjunct) -> bool:
    v = disjunct.binary_indicator_var.value
    return v is not None and v > 0.5


def summarize(mod, unit_type: dict, block_hours: int) -> dict:
    """Per-stage investment counts, load shed, costs and pass-gate checks."""
    m = mod.model
    out = {"stages": {}}
    lifetimes = {g: pyo.value(m.lifetimes[g]) for g in m.thermalGenerators}
    status_by_gen = defaultdict(dict)
    for s in m.stages:
        b = m.investmentStage[s]
        st = {"thermal": {}, "renewable_MW": {}}
        for status in STATUSES:
            counts = defaultdict(int)
            for g in m.thermalGenerators:
                if binary_value(getattr(b, "gen" + status)[g]):
                    counts[unit_type[g]] += 1
                    status_by_gen[g][s] = status
            st["thermal"][status] = dict(sorted(counts.items()))
            mw = defaultdict(float)
            for g in m.renewableGenerators:
                v = getattr(b, "renewable" + status)[g].value or 0.0
                if v > 1e-3:
                    key = unit_type[g] + ("-c" if str(g).endswith("-c") else "")
                    mw[key] += v
            st["renewable_MW"][status] = {k: round(v, 3) for k, v in sorted(mw.items())}

        shed_mw_periods = 0.0
        shed_mwh_weighted = 0.0
        load_mwh_weighted = 0.0
        max_over = 0.0
        neg = 0
        for r in b.representativePeriods:
            rb = b.representativePeriod[r]
            w = pyo.value(m.weights[r])
            for c in rb.commitmentPeriods:
                cb = rb.commitmentPeriod[c]
                clen = pyo.value(cb.commitmentPeriodLength)
                load_mwh_weighted += (
                    w * clen * sum(pyo.value(cb.loads[bus]) for bus in m.buses)
                )
                for d in cb.dispatchPeriods:
                    db = cb.dispatchPeriod[d]
                    dlen = pyo.value(db.dispatchPeriodLength) / 60.0
                    shed = sum(db.loadShed[bus].value or 0.0 for bus in m.buses)
                    shed_mw_periods += shed
                    shed_mwh_weighted += w * dlen * shed
                    for g in m.thermalGenerators:
                        v = db.thermalGeneration[g].value or 0.0
                        neg += v < -1e-6
                        max_over = max(max_over, v - pyo.value(m.thermalCapacity[g]))
                    for g in m.renewableGenerators:
                        v = db.renewableGeneration[g].value or 0.0
                        neg += v < -1e-6
                        cap = pyo.value(cb.renewableCapacityExpected[g])
                        max_over = max(max_over, v - cap)
        st["load_shed_MW_periods"] = shed_mw_periods
        st["load_shed_MWh_weighted"] = shed_mwh_weighted
        st["load_MWh_weighted"] = load_mwh_weighted
        st["dispatch_negative_count"] = int(neg)
        st["dispatch_max_above_cap_MW"] = max_over
        st["operatingCostInvestment"] = pyo.value(b.operatingCostInvestment)
        st["investment_cost"] = pyo.value(b.investment_cost)
        out["stages"][s] = st

    # Coal units reaching lifetime: operational in stage s - lifetime must be
    # Retired or Extended at s (upstream gen.py thermalgen_retirement).
    stuck = []
    reaching = 0
    for g in m.thermalGenerators:
        if unit_type[g] != "COAL":
            continue
        lt = int(lifetimes[g])
        for s in m.stages:
            if s > lt and status_by_gen[g].get(s - lt) in ("Operational", "Installed"):
                reaching += 1
                if status_by_gen[g].get(s) not in ("Retired", "Extended"):
                    stuck.append((g, s, status_by_gen[g].get(s)))
    out["coal_reaching_lifetime"] = reaching
    out["coal_stuck_operational"] = stuck
    out["extended_units"] = sorted(
        {
            (g, s)
            for g, d in status_by_gen.items()
            for s, v in d.items()
            if v == "Extended"
        }
    )
    out["retired_units"] = sorted(
        {
            (g, s)
            for g, d in status_by_gen.items()
            for s, v in d.items()
            if v == "Retired"
        }
    )
    out["installed_units"] = sorted(
        {
            (g, s)
            for g, d in status_by_gen.items()
            for s, v in d.items()
            if v == "Installed"
        }
    )
    out["costs"] = {
        "operatingCostTotal": pyo.value(m.operatingCostTotal),
        "expansionCostTotal": pyo.value(m.expansionCostTotal),
        "penaltyCostTotal": pyo.value(m.penaltyCostTotal),
    }
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    block = BLOCK_HOURS[args.config]
    num_commit = 24 // block
    timers = {}
    rec = {"args": {k: str(v) for k, v in vars(args).items()}}

    data_path = prepare_data_copy(out.parent / "_data")
    unit_type = pd.read_csv(data_path / "gen.csv", index_col="GEN UID")[
        "Unit Type"
    ].to_dict()
    unit_type = {str(k): v for k, v in unit_type.items()}

    t0 = time.perf_counter()
    data_object = ExpansionPlanningData(
        stages=args.stages,
        num_reps=args.num_reps,
        num_commit=num_commit,
        num_dispatch=1,
        duration_representative_period=24,
    )
    data_object.load_prescient(data_path)
    rec["representative_dates_upstream"] = list(data_object.representative_dates)
    if args.weights == "may":
        data_object.representative_weights_dict = may_weights(
            data_object.representative_dates, args.num_reps
        )
    rec["representative_weights"] = data_object.representative_weights_dict

    if args.scale_texas_loads == "on":
        data_object.import_load_scaling(data_path / "ERCOT-Adjusted-Forecast.xlsb")
        # port: upstream labels the zone columns "1".."8" (181a307, for
        # Texas_2000); Coal loads carry zone names. Same column order as the
        # fork's cap_zones (gtep_data.py:154-155@commitment_period).
        data_object.load_scaling = data_object.load_scaling.rename(
            columns={str(i + 1): z for i, z in enumerate(ZONE_NAMES)}
        )
        data_object.texas_case_study_updates(data_path)
        if block > 1:
            aggregate.aggregate_load_scaling(data_object, block)
    if block > 1:
        aggregate.aggregate_data(data_object, block, num_commit)

    cost_data = None
    if args.cost_data == "on":
        cost_data = DataProcessing()
        cost_data.load_gen_data(
            bus_data_path=COSTS / "Bus_data_gen_weights_mappings.csv",
            cost_data_path=COSTS
            / "2022_v3_Annual_Technology_Baseline_Workbook_Mid-year_update_2-15-2023_Clean.xlsx",
            ng_cost_path=COSTS
            / "Total_Energy_Supply_Disposition_and_Price_Summary.csv",
            candidate_gens=CANDIDATES,
        )
    timers["data_s"] = time.perf_counter() - t0
    print(
        f"data loaded in {timers['data_s']:.1f} s; dates {rec['representative_dates_upstream']}",
        flush=True,
    )

    config = {
        "include_investment": True,
        "scale_loads": False,
        "scale_texas_loads": args.scale_texas_loads == "on",
        "transmission": False,
        "flow_model": "CP",
    }
    rec["config"] = config
    mod = ExpansionPlanningModel(data=data_object, cost_data=cost_data, config=config)
    t0 = time.perf_counter()
    mod.create_model()
    timers["build_s"] = time.perf_counter() - t0
    if args.diag_fix_all_off:
        m = mod.model
        for s in m.stages:
            b = m.investmentStage[s]
            for g in m.thermalGenerators:
                if str(g).endswith("-c"):
                    b.genDisabled[g].indicator_var.fix(True)
            for r in b.representativePeriods:
                rb = b.representativePeriod[r]
                for c in rb.commitmentPeriods:
                    for g in m.thermalGenerators:
                        rb.commitmentPeriod[c].genOff[g].indicator_var.fix(True)
        rec["diag_fix_all_off"] = True
    print(f"build {timers['build_s']:.1f} s", flush=True)

    t0 = time.perf_counter()
    pyo.TransformationFactory("gdp.bigm").apply_to(mod.model)
    timers["transform_s"] = time.perf_counter() - t0
    print(f"bigm {timers['transform_s']:.1f} s", flush=True)

    size = build_model_size_report(mod.model)
    rec["size"] = {
        "rows": size.activated.constraints,
        "cols": size.activated.variables,
        "binaries": size.activated.binary_variables,
        "integers": size.activated.integer_variables,
        "disjunctions": size.overall.disjunctions,
        "disjuncts": size.overall.disjuncts,
    }
    rec["peak_rss_GB_after_bigm"] = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9
    )
    print(
        "size", rec["size"], f"rss {rec['peak_rss_GB_after_bigm']:.2f} GB", flush=True
    )
    m = mod.model
    rec["total_load_MW_rep1"] = {
        s: [
            round(
                sum(
                    pyo.value(
                        m.investmentStage[s]
                        .representativePeriod[1]
                        .commitmentPeriod[c]
                        .loads[bus]
                    )
                    for bus in m.buses
                ),
                1,
            )
            for c in m.investmentStage[s].representativePeriod[1].commitmentPeriods
        ]
        for s in m.stages
    }
    print("total load rep1 per stage", rec["total_load_MW_rep1"], flush=True)
    rec["commitment_length_h"] = pyo.value(
        m.investmentStage[1]
        .representativePeriod[1]
        .commitmentPeriod[1]
        .commitmentPeriodLength
    )
    if args.build_only:
        rec["timers"] = timers
        (out / "summary.json").write_text(json.dumps(rec, indent=2, default=str))
        return 0

    log = out / f"{args.solver}.log"
    if args.solver == "highs":
        opt = pyo.SolverFactory("highs")
        opt.options["mip_rel_gap"] = args.mip_rel_gap
        opt.options["time_limit"] = args.time_limit
        if args.threads:
            opt.options["threads"] = args.threads
        kw = {}
    else:
        opt = pyo.SolverFactory("gurobi_direct")
        opt.options["MIPGap"] = args.mip_rel_gap
        opt.options["TimeLimit"] = args.time_limit
        opt.options["LogFile"] = str(log.with_suffix(".grb.log"))
        if args.threads:
            opt.options["Threads"] = args.threads
        kw = {}
    t0 = time.perf_counter()
    try:
        with open(log, "w") as f, redirect_stdout(f), redirect_stderr(f):
            result = opt.solve(mod.model, tee=True, **kw)
    except NoFeasibleSolutionError:
        timers["solve_s"] = time.perf_counter() - t0
        rec["timers"] = timers
        rec["termination"] = "no incumbent (solver returned no feasible solution)"
        if args.solver == "highs":
            rec["highs"] = highs_summary(log)
        rec["peak_rss_GB"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9
        (out / "summary.json").write_text(json.dumps(rec, indent=2, default=str))
        print("solve: no incumbent", rec.get("highs"), flush=True)
        return 2
    timers["solve_s"] = time.perf_counter() - t0
    rec["timers"] = timers
    term = str(result["Solver"][0]["Termination condition"])
    rec["termination"] = term
    rec["objective"] = pyo.value(mod.model.total_cost_objective)
    prob = result["Problem"][0]
    lb, ub = prob.get("Lower bound"), prob.get("Upper bound")
    try:
        lb, ub = float(lb.value if hasattr(lb, "value") else lb), float(
            ub.value if hasattr(ub, "value") else ub
        )
        rec["bounds"] = [lb, ub]
        rec["gap_from_bounds"] = abs(ub - lb) / max(abs(ub), 1e-10)
    except (TypeError, ValueError, AttributeError):
        rec["bounds"] = None
    if args.solver == "highs":
        rec["highs"] = highs_summary(log)
    rec["peak_rss_GB"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9
    print(
        f"solve {timers['solve_s']:.1f} s term {term} obj {rec['objective']:.6g}",
        flush=True,
    )

    ExpansionPlanningSolution(data_path).save_results_in_json_files(mod, out / "soln")
    rec["summary"] = summarize(mod, unit_type, block)
    (out / "summary.json").write_text(json.dumps(rec, indent=2, default=str))
    print(json.dumps(rec["summary"]["stages"], indent=1, default=str)[:4000])
    print("costs", rec["summary"]["costs"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
