"""Instrument the PMAPS 123-bus tutorial notebook (prompt 03, T1 + T2).

Reads the exploration copy of ``docs/source/tutorials/123bus/tutorial_123bus.ipynb``
(placed four levels deep so the shipped ``../../../../gtep/data`` paths resolve
unchanged) and adds, without changing the shipped model setup:

* ``build_model_size_report`` after each Big-M, ``time.perf_counter`` around
  each solve, and the HiGHS log of each experiment in its own file
  (``highs_expr1.log`` / ``highs_expr2.log``; the baseline keeps ``output.log``);
* ``baseline_objective`` printed before the model is deleted;
* Experiment 1 (cell 19 markdown) run live into ``soln_expr1_local/``;
* Experiment 2 (cell 25 markdown) built and solved live into
  ``soln_expr2_local/`` with ``mip_rel_gap=0.01, time_limit=7200``;
* a final metrics cell: cell-22 energy-by-type dicts for every local result,
  per-generator diff of Experiment 1 against the shipped ``soln_expr1/``,
  candidate (``-c``) status in the baseline, Experiment 2 investment summary,
  HiGHS log summaries, peak RSS, tables written to ``metrics_123bus.md``.

Usage::

    python patch_tutorial_123bus.py <in.ipynb> <out.ipynb>

Cells are located by source signature with their shipped index asserted.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat

EXPECTED_CELL_COUNT = 28


def _find_cell(nb, signature: str, expected_index: int):
    hits = [i for i, c in enumerate(nb.cells) if signature in c.source]
    if len(hits) != 1:
        raise RuntimeError(f"signature {signature!r}: {len(hits)} hits, want 1")
    if hits[0] != expected_index:
        raise RuntimeError(
            f"signature {signature!r} found at cell {hits[0]}, expected {expected_index}"
        )
    return hits[0]


BASELINE_SOLVE_SRC = """from gtep.gtep_model import ExpansionPlanningModel
from pyomo.environ import SolverFactory, TransformationFactory
from contextlib import redirect_stdout, redirect_stderr
import time  # [instrument]
import resource  # [instrument]
from pyomo.util.model_size import build_model_size_report  # [instrument]

mod_object = ExpansionPlanningModel(
    data=data_object,
    cost_data=cost_data,
    config={"scale_loads": False},
)
mod_object.create_model()
mod_object.timer.toc("Finished model build")

TransformationFactory("gdp.bigm").apply_to(mod_object.model)
mod_object.timer.toc("Finished model transformation")
size_baseline = build_model_size_report(mod_object.model)  # [instrument]

opt = SolverFactory("highs")
opt.options["mip_rel_gap"] = 0.01

_t0 = time.perf_counter()  # [instrument]
with open("output.log", "w") as f, redirect_stdout(f), redirect_stderr(f):
    result = opt.solve(mod_object.model, tee=True)
wall_baseline = time.perf_counter() - _t0  # [instrument]

mod_object.timer.toc("Finished solving");
print("[instrument] baseline termination:", result["Solver"][0]["Termination condition"])
print(f"[instrument] baseline solve wall (s): {wall_baseline:.2f}")
print(size_baseline)
"""

BASELINE_OBJ_SRC = """import gc
from pyomo.environ import value

baseline_objective = value(mod_object.model.total_cost_objective)
print(f"[instrument] baseline_objective: {baseline_objective:,.4f}")  # [instrument]
metrics = {  # [instrument]
    "baseline": {
        "objective": baseline_objective,
        "termination": str(result["Solver"][0]["Termination condition"]),
        "wall": wall_baseline,
        "size": size_baseline,
        "log": "output.log",
        "soln": "soln",
    }
}
del mod_object, opt
gc.collect();
"""

HELPER_SRC = """from pyomo.environ import value

def solve_model_and_make_plots(
    model_object: ExpansionPlanningModel,
    data_path: Path|str,
    write_dir: Path|str,
    tee: bool=True,
    solver_options: None|dict=None,
    log_file: str = "output.log",  # [instrument] per-run HiGHS log
):

    # transform and solve
    TransformationFactory("gdp.bigm").apply_to(model_object.model)
    model_object.timer.toc("Finished model transformation")
    size = build_model_size_report(model_object.model)  # [instrument]

    opt = SolverFactory("highs")
    if solver_options is not None:
        for option, val in solver_options.items():
            opt.options[option] = val

    _t0 = time.perf_counter()  # [instrument]
    with open(log_file, "w") as f, redirect_stdout(f), redirect_stderr(f):
        result_object = opt.solve(model_object.model, tee=tee)
    wall = time.perf_counter() - _t0  # [instrument]
    model_object.timer.toc("Finished solving")

    # check termination condition
    term_cond = result_object["Solver"][0]["Termination condition"]
    print("Termination condition:", term_cond)
    print(f"[instrument] {write_dir} solve wall (s): {wall:.2f}")
    print(size)
    # [instrument] a time-limited run with a feasible incumbent is still
    # written out (the legacy HiGHS wrapper loads the incumbent); only a run
    # with nothing to report returns early.
    if term_cond != "optimal" and str(term_cond) != "maxTimeLimit":
        return None, None, result_object, wall, size

    # make solution
    soln_object = ExpansionPlanningSolution(data_path)
    soln_object_path = (Path() / write_dir).resolve()
    soln_object.save_results_in_json_files(model_object, soln_object_path)
    model_object.timer.toc("Finished saving results to json")
    pie = soln_object.create_plots(
        "combined", soln_object_path, data_path, "piechart", savefig=False
    )
    rep_days = [
        value(model_object.model.representativeDate[idx])
        for idx in model_object.model.representativeDate
    ]
    stackgraph = soln_object.create_stackgraph(
        soln_object_path, rep_days, savefig=False
    )
    model_object.timer.toc("Finished plotting")
    pie.write_html(f"{write_dir}_pie.html")  # [instrument]
    stackgraph.write_html(f"{write_dir}_stackgraph.html")  # [instrument]
    return pie, stackgraph, result_object, wall, size
"""

EXPR1_SRC = """# [instrument] Experiment 1 run live (code from the markdown cell above),
# written to soln_expr1_local/ so the shipped soln_expr1/ stays the reference.
mod_object_expr1 = ExpansionPlanningModel(
    data=data_object,  # same data object
    cost_data=cost_data,  # same cost data object
    config={"scale_loads": False, "include_investment": False},
)
mod_object_expr1.create_model()
mod_object_expr1.timer.toc("Finished model build")

pie_exper1, _, result_expr1, wall_expr1, size_expr1 = solve_model_and_make_plots(
    mod_object_expr1,
    data_path,
    "soln_expr1_local",
    solver_options={"mip_rel_gap": 0.01},
    log_file="highs_expr1.log",
)

print(
    "Objective for baseline:",
    f"{baseline_objective :,.0f}",
)
expr1_objective = value(mod_object_expr1.model.total_cost_objective)
print(
    "Objective for experiment 1:",
    f"{expr1_objective :,.0f}",
)
print(f"[instrument] expr1_objective: {expr1_objective:,.4f}")
metrics["expr1"] = {
    "objective": expr1_objective,
    "termination": str(result_expr1["Solver"][0]["Termination condition"]),
    "wall": wall_expr1,
    "size": size_expr1,
    "log": "highs_expr1.log",
    "soln": "soln_expr1_local",
}

display_plotly_as_html(pie, title="Baseline")
display_plotly_as_html(
    pie_exper1,
    title="Experiment 1 (no investment, live)",
)

del mod_object_expr1
gc.collect();
"""

EXPR2_SRC = """# [instrument] Experiment 2 built and solved live (code from the markdown
# cell above), written to soln_expr2_local/, mip_rel_gap 0.01, time_limit 7200 s.
data_object_exper2 = ExpansionPlanningData(
    stages=1,
    num_reps=10,
    num_commit=5,
    num_dispatch=1,
    duration_representative_period=5,
)

data_object_exper2.load_prescient(
    data_path,
    representative_dates=[
        "2019-01-28 00:00",
        "2019-03-07 00:00",
        "2019-03-16 00:00",
        "2019-05-10 00:00",
        "2019-06-10 00:00",
        "2019-06-30 00:00",
        "2019-07-15 00:00",
        "2019-10-29 00:00",
        "2019-11-03 00:00",
        "2019-12-10 00:00",
    ],
    representative_weights={
        "2019-01-28 00:00": 45,
        "2019-03-07 00:00": 35,
        "2019-03-16 00:00": 25,
        "2019-05-10 00:00": 35,
        "2019-06-10 00:00": 30,
        "2019-06-30 00:00": 35,
        "2019-07-15 00:00": 45,
        "2019-10-29 00:00": 35,
        "2019-11-03 00:00": 40,
        "2019-12-10 00:00": 40,
    },
)

_t_build0 = time.perf_counter()
mod_object_expr2 = ExpansionPlanningModel(
    data=data_object_exper2,
    cost_data=cost_data,  # same cost data
    config={"scale_loads": False, "transmission": True},
)
mod_object_expr2.create_model()
build_expr2 = time.perf_counter() - _t_build0
mod_object_expr2.timer.toc("Finished model build")

_t_tr0 = time.perf_counter()
pie_exper2, stackgraph_exper2, result_expr2, wall_expr2, size_expr2 = solve_model_and_make_plots(
    mod_object_expr2,
    data_path,
    "soln_expr2_local",
    solver_options={"mip_rel_gap": 0.01, "time_limit": 7200},
    log_file="highs_expr2.log",
)
transform_expr2 = time.perf_counter() - _t_tr0 - wall_expr2  # transform + post-solve I/O

expr2_objective = value(mod_object_expr2.model.total_cost_objective)
print(f"[instrument] expr2_objective: {expr2_objective:,.4f}")
print(f"[instrument] expr2 build (s): {build_expr2:.2f}")
peak_rss_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9
print(f"[instrument] peak RSS (GB): {peak_rss_gb:.2f}")
metrics["expr2"] = {
    "objective": expr2_objective,
    "termination": str(result_expr2["Solver"][0]["Termination condition"]),
    "wall": wall_expr2,
    "size": size_expr2,
    "log": "highs_expr2.log",
    "soln": "soln_expr2_local",
    "build": build_expr2,
    "peak_rss_gb": peak_rss_gb,
}
if pie_exper2 is not None:
    display_plotly_as_html(pie, title="Baseline")
    display_plotly_as_html(pie_exper2, title="Experiment 2 (live)")
    display_plotly_as_html(stackgraph_exper2, title="Experiment 2 (live)")

del mod_object_expr2
gc.collect();
"""

METRICS_SRC = '''# [instrument] metrics tables -> metrics_123bus.md
import re, platform, sys, importlib.metadata as _md
import highspy, pyomo

gen_df = pd.read_csv(data_path / "gen.csv", index_col="GEN UID")
pmax = gen_df["PMax MW"].to_dict()


def gen_by_type_dict(path_to_gen_result, dispatch_duration=1.0):
    with open(path_to_gen_result) as f:
        generation_data = json.load(f)
    totals = {}
    for key, val in generation_data.items():
        ut = gen_unit_type_mapping[key.split(".")[-1]]
        totals[ut] = totals.get(ut, 0.0) + val * dispatch_duration / 1000
    return {k: totals[k] for k in sorted(totals)}


def parse_highs_log(path):
    txt = open(path).read()
    out = {}
    for label, pat in (
        ("gap", r"^\\s+Gap\\s+(.*)$"),
        ("nodes", r"^\\s+Nodes\\s+(\\d+)"),
        ("timing", r"^\\s+Timing\\s+([\\d.]+)"),
        ("status", r"^\\s+Status\\s+(.*)$"),
        ("lp_iters", r"^\\s+LP iterations\\s+(\\d+)"),
    ):
        m = re.search(pat, txt, re.M)
        out[label] = m.group(1).strip() if m else "n/a"
    return out


def investments(soln_dir):
    """Non-zero investment-status entries from the solution JSONs."""
    d = {}
    for p in sorted(Path(soln_dir).glob("*.json")):
        if "invest" in p.name.lower():
            d.update(json.load(open(p)))
    return d


def candidate_summary(soln_dir):
    """-c candidates with a non-zero investment-status value, by variable."""
    rows = {}
    for key, val in investments(soln_dir).items():
        var, gen = key.rsplit(".", 1)
        var = var.split(".")[-1]
        if gen.endswith("-c"):
            rows.setdefault(var, []).append((gen, val))
    return rows


def new_capacity_by_type(soln_dir):
    """Installed candidate capacity (MW) by unit type."""
    cap = {}
    for key, val in investments(soln_dir).items():
        var, gen = key.rsplit(".", 1)
        var = var.split(".")[-1]
        if not gen.endswith("-c") or "Installed" not in var:
            continue
        ut = gen_unit_type_mapping[gen]
        mw = val if var.startswith("renewable") else pmax[gen] * val
        cap[ut] = cap.get(ut, 0.0) + mw
    return {k: cap[k] for k in sorted(cap)}


stored = {
    "baseline": {"COAL": 6.4307, "CT": 22.402249999999995, "WIND": 46.076880000000024},
    "expr1": {"COAL": 12.154599999999995, "CT": 39.881330000000034, "WIND": 22.873900000000003},
}
energy = {k: gen_by_type_dict(Path(m["soln"]) / "generation.json") for k, m in metrics.items()}
logs = {k: parse_highs_log(m["log"]) for k, m in metrics.items()}

lines = []
lines.append(
    f"Python {sys.version.split()[0]}, highspy {_md.version('highspy')}, "
    f"HiGHS {highspy.Highs().version()}, pyomo {pyomo.version.version}, "
    f"{platform.machine()} / {platform.platform()}"
)
lines += ["", "## T1 comparison", "",
          "| case | quantity | stored | obtained | rel. diff | termination | MIP gap | solve s |",
          "|---|---|---|---|---|---|---|---|"]
for case in ("baseline", "expr1"):
    m, e, lg = metrics[case], energy[case], logs[case]
    types = sorted(set(stored[case]) | set(e))
    for ut in types + ["total"]:
        s = sum(stored[case].values()) if ut == "total" else stored[case].get(ut, 0.0)
        o = sum(e.values()) if ut == "total" else e.get(ut, 0.0)
        rd = (o - s) / s if s else float("nan")
        lines.append(
            f"| {case} | {ut} GWh | {s:.4f} | {o:.4f} | {rd:+.2%} | "
            f"{m['termination']} | {lg['gap']} | {m['wall']:.2f} |"
        )
lines += ["", "## Objectives", ""]
for k, m in metrics.items():
    lines.append(f"- {k}: {m['objective']:,.4f} ({m['termination']}, gap {logs[k]['gap']})")

lines += ["", "## Model size / time", "",
          "| case | rows | cols | binaries | solve wall s | HiGHS timing s | nodes | LP iters | termination | gap |",
          "|---|---|---|---|---|---|---|---|---|---|"]
for k, m in metrics.items():
    a, lg = m["size"].activated, logs[k]
    lines.append(
        f"| {k} | {a.constraints} | {a.variables} | {a.binary_variables} | {m['wall']:.1f} | "
        f"{lg['timing']} | {lg['nodes']} | {lg['lp_iters']} | {m['termination']} | {lg['gap']} |"
    )
if "expr2" in metrics:
    lines.append(
        f"\\nexpr2 build {metrics['expr2']['build']:.1f} s; peak RSS {metrics['expr2']['peak_rss_gb']:.2f} GB "
        f"(whole kernel, cumulative)."
    )

lines += ["", "## Energy by type (GWh, dispatch_duration=1.0)", ""]
for k, e in energy.items():
    lines.append(f"- {k}: {e}")

# per-generator diff, Experiment 1 vs shipped
shipped = json.load(open("soln_expr1/generation.json"))
local = json.load(open("soln_expr1_local/generation.json"))
keys = set(shipped) | set(local)
deltas = {k: local.get(k, 0.0) - shipped.get(k, 0.0) for k in keys}
big = sorted(deltas.items(), key=lambda kv: -abs(kv[1]))
lines += ["", "## Experiment 1 per-generator diff (local - shipped, MW)", "",
          f"- keys: shipped {len(shipped)}, local {len(local)}, union {len(keys)}",
          f"- max |delta|: {max(abs(v) for v in deltas.values()):.3f} MW",
          f"- generators with |delta| > 1 MW: {sum(abs(v) > 1 for v in deltas.values())}",
          "- five largest:"]
for k, v in big[:5]:
    lines.append(f"  - {k.split('.',1)[1] if '.' in k else k}: {v:+.3f} (shipped {shipped.get(k,0):.3f}, local {local.get(k,0):.3f})")

lines += ["", "## Candidate (-c) status in the baseline (non-zero entries)", ""]
for var, rows in candidate_summary("soln").items():
    lines.append(f"- {var}: {len(rows)} candidates, e.g. " + "; ".join(f"{g}={v:.1f}" for g, v in rows[:6]))

if "expr2" in metrics:
    lines += ["", "## Experiment 2 investment summary (installed candidate MW by type)", "",
              f"- {new_capacity_by_type('soln_expr2_local')}",
              "", "## Experiment 2 candidate status (non-zero entries)", ""]
    for var, rows in candidate_summary("soln_expr2_local").items():
        lines.append(f"- {var}: {len(rows)} candidates, e.g. " + "; ".join(f"{g}={v:.1f}" for g, v in rows[:6]))
lines += ["", "## Baseline investment summary (installed candidate MW by type)", "",
          f"- {new_capacity_by_type('soln')}"]

report = "\\n".join(lines)
print(report)
with open("metrics_123bus.md", "w") as f:
    f.write(report + "\\n")
'''


def patch(nb):
    if len(nb.cells) != EXPECTED_CELL_COUNT:
        raise RuntimeError(f"{len(nb.cells)} cells, expected {EXPECTED_CELL_COUNT}")

    i_solve = _find_cell(nb, 'mod_object.timer.toc("Finished solving");', 9)
    i_obj = _find_cell(nb, "baseline_objective = value(", 14)
    i_help = _find_cell(nb, "def solve_model_and_make_plots", 17)
    i_md1 = _find_cell(nb, "mod_object_expr1 = ExpansionPlanningModel(", 19)
    i_gen = _find_cell(nb, "def total_gen_by_type", 22)
    i_md2 = _find_cell(nb, "data_object_exper2 = ExpansionPlanningData(", 25)
    i_last = _find_cell(nb, "stackgraph_exper2_html = HTML(filename=", 26)
    assert (
        nb.cells[i_md1].cell_type == "markdown"
        and nb.cells[i_md2].cell_type == "markdown"
    )
    assert nb.cells[i_gen].cell_type == "code"

    nb.cells[i_solve].source = BASELINE_SOLVE_SRC
    nb.cells[i_obj].source = BASELINE_OBJ_SRC
    nb.cells[i_help].source = HELPER_SRC

    # Back to front so earlier indices stay valid.
    for idx, src in (
        (i_last + 1, METRICS_SRC),
        (i_md2 + 1, EXPR2_SRC),
        (i_md1 + 1, EXPR1_SRC),
    ):
        nb.cells.insert(idx, nbformat.v4.new_code_cell(src))

    for c in nb.cells:
        if c.cell_type == "code":
            c.outputs = []
            c.execution_count = None
    return nb


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    src, dst = Path(argv[1]), Path(argv[2])
    nb = nbformat.read(src, as_version=4)
    nb = patch(nb)
    nbformat.write(nb, dst)
    n_code = sum(c.cell_type == "code" for c in nb.cells)
    print(f"wrote {dst} ({len(nb.cells)} cells, {n_code} code cells, outputs cleared)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
