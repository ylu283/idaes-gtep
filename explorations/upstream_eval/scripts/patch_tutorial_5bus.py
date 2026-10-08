"""Instrument the PMAPS 5-bus tutorial notebook (prompt 01, T2 step 4).

Reads the path-patched exploration copy of
``docs/source/tutorials/5bus/tutorial_5bus.ipynb`` and adds, without changing
the shipped model setup or solver options:

* ``pyomo.util.model_size.build_model_size_report`` after each Big-M
  transformation;
* ``time.perf_counter()`` around each ``opt.solve`` (the baseline cell and
  ``solve_model_and_make_plots``);
* a per-experiment HiGHS log (``highs_<write_dir>.log``) via the notebook's
  own ``redirect_stdout`` pattern (there is no ``logfile=`` option on this
  solver interface);
* ``solve_model_and_make_plots`` returns
  ``(pie, stackgraph, result_object, wall, size)``;
* ``fig.write_html(...)`` for every pie / stack figure;
* the generator-status loop (cell 40) re-run for ``mod_no_invest`` and
  ``mod_fewer_repr_days``;
* a final metrics table (markdown) printed and written to
  ``metrics_5bus.md`` next to the notebook.

Usage::

    python patch_tutorial_5bus.py <in.ipynb> <out.ipynb>

Cells are located by a source signature and their expected index in the
shipped notebook is asserted, so a silently reordered upstream notebook fails
loudly instead of being mis-patched.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat

EXPECTED_CELL_COUNT = 65


def _find_cell(nb, signature: str, expected_index: int):
    hits = [
        i
        for i, c in enumerate(nb.cells)
        if c.cell_type == "code" and signature in c.source
    ]
    if len(hits) != 1:
        raise RuntimeError(f"signature {signature!r}: {len(hits)} hits, want 1")
    if hits[0] != expected_index:
        raise RuntimeError(
            f"signature {signature!r} found at cell {hits[0]}, "
            f"expected {expected_index}"
        )
    return hits[0]


SOLVE_CELL_SRC = """from contextlib import redirect_stdout, redirect_stderr
import time
from pyomo.util.model_size import build_model_size_report

# [instrument] model size after Big-M, wall time around the solve
with open("output.log", "w") as f, redirect_stdout(f), redirect_stderr(f):
    from pyomo.environ import SolverFactory, TransformationFactory

    TransformationFactory("gdp.bigm").apply_to(mod_object.model)  # apply transformation here
    size = build_model_size_report(mod_object.model)
    opt = SolverFactory("highs")  # select your solver here
    _t0 = time.perf_counter()
    result = opt.solve(mod_object.model, tee=True)  # tee=True prints solver updates
    wall = time.perf_counter() - _t0

print(f"[instrument] baseline wall time (s): {wall:.2f}")
print(size)
"""

STATUS_HELPER_SRC = '''# [instrument] generator-status loop from the cell above, as a reusable function
def report_generator_status(model, label="model"):
    """Print the cell-40 generator-status loop and return a summary dict."""
    thermal_on = []
    renewable_cap = {}
    for i in model.stages:
        print("-" * 50)
        print(f"{label}: INVESTMENT STAGE {i}")
        inv = model.investmentStage[i]

        print("Which thermal generators are operational or extended:")
        for thermal_generator in model.thermalGenerators:
            on = bool(
                value(inv.genOperational[thermal_generator].indicator_var)
                or value(inv.genExtended[thermal_generator].indicator_var)
            )
            print(thermal_generator, "   \\t", on)
            if on:
                thermal_on.append(str(thermal_generator))

        print("Renewables operational plus extended generation capacity:")
        for renewable_generator in model.renewableGenerators:
            cap = value(inv.renewableOperational[renewable_generator]) + value(
                inv.renewableExtended[renewable_generator]
            )
            print(renewable_generator, "   \\t", cap)
            renewable_cap[str(renewable_generator)] = cap
    return {"thermal_on": thermal_on, "renewable_cap": renewable_cap}


metrics = {}
metrics["baseline"] = {
    "objective": value(mod_object.model.total_cost_objective),
    "termination": str(result["Solver"][0]["Termination condition"]),
    "wall": wall,
    "size": size,
    **report_generator_status(mod_object.model, "baseline"),
}
'''

SOLVE_FUNC_SRC = """def solve_model_and_make_plots(model_object, data_path, write_dir):

    # transform and solve
    TransformationFactory("gdp.bigm").apply_to(model_object.model)
    size = build_model_size_report(model_object.model)  # [instrument]

    # [instrument] per-experiment HiGHS log + wall time
    with open(f"highs_{write_dir}.log", "w") as f, redirect_stdout(f), redirect_stderr(f):
        _t0 = time.perf_counter()
        result_object = opt.solve(model_object.model, tee=True)
        wall = time.perf_counter() - _t0

    # check termination condition
    term_cond = result_object["Solver"][0]["Termination condition"]
    print("Termination condition:", term_cond)
    print(f"[instrument] {write_dir} wall time (s): {wall:.2f}")
    print(size)
    if term_cond != "optimal":
        return None, None, result_object, wall, size

    # make solution
    soln_object = ExpansionPlanningSolution(data_path)
    soln_object_path = (Path() / write_dir).resolve()
    soln_object.save_results_in_json_files(model_object, soln_object_path)
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
    pie.write_html(f"{write_dir}_pie.html")  # [instrument]
    stackgraph.write_html(f"{write_dir}_stackgraph.html")  # [instrument]
    return pie, stackgraph, result_object, wall, size
"""

EXP1_CALL_OLD = """pie_no_invest, stackgraph_no_invest = solve_model_and_make_plots(
    mod_no_invest,
    data_path,
    "soln_no_invest"
)"""
EXP1_CALL_NEW = """(
    pie_no_invest,
    stackgraph_no_invest,
    result_no_invest,
    wall_no_invest,
    size_no_invest,
) = solve_model_and_make_plots(mod_no_invest, data_path, "soln_no_invest")"""

EXP2_CALL_OLD = """pie_fewer_repr_days, stackgraph_fewer_repr_days = solve_model_and_make_plots(
    mod_fewer_repr_days,
    data_path,
    "soln_fewer_repr_days",
)"""
EXP2_CALL_NEW = """(
    pie_fewer_repr_days,
    stackgraph_fewer_repr_days,
    result_fewer_repr_days,
    wall_fewer_repr_days,
    size_fewer_repr_days,
) = solve_model_and_make_plots(mod_fewer_repr_days, data_path, "soln_fewer_repr_days")"""

EXP1_STATUS_SRC = """# [instrument] generator status + metrics for Experiment 1
metrics["no_invest"] = {
    "objective": value(mod_no_invest.model.total_cost_objective),
    "termination": str(result_no_invest["Solver"][0]["Termination condition"]),
    "wall": wall_no_invest,
    "size": size_no_invest,
    **report_generator_status(mod_no_invest.model, "no_invest"),
}
"""

EXP2_STATUS_SRC = """# [instrument] generator status + metrics for Experiment 2
metrics["fewer_repr_days"] = {
    "objective": value(mod_fewer_repr_days.model.total_cost_objective),
    "termination": str(result_fewer_repr_days["Solver"][0]["Termination condition"]),
    "wall": wall_fewer_repr_days,
    "size": size_fewer_repr_days,
    **report_generator_status(mod_fewer_repr_days.model, "fewer_repr_days"),
}
"""

METRICS_TABLE_SRC = """# [instrument] metrics table (T2 step 4, second table)
import platform, sys, importlib.metadata as _md
import highspy, pyomo

header = (
    "| case | objective | thermal gens operational/extended | "
    "renewable capacity by gen (MW) | wall time (s) | rows / cols / binaries | termination |"
)
rows = [header, "|---|---|---|---|---|---|---|"]
for case, m in metrics.items():
    a = m["size"].activated
    rows.append(
        f"| {case} | {m['objective']:,.4f} | {', '.join(m['thermal_on'])} | "
        + "; ".join(f"{g}: {v:,.1f}" for g, v in m["renewable_cap"].items())
        + f" | {m['wall']:.2f} | {a.constraints} / {a.variables} / {a.binary_variables} "
        f"| {m['termination']} |"
    )
env_line = (
    f"Python {sys.version.split()[0]}, highspy {_md.version('highspy')}, "
    f"HiGHS {highspy.Highs().version()}, pyomo {pyomo.version.version}, "
    f"{platform.machine()} / {platform.platform()}"
)
table = "\\n".join(rows)
print(env_line)
print(table)
with open("metrics_5bus.md", "w") as f:
    f.write(env_line + "\\n\\n" + table + "\\n")
"""


def patch(nb):
    if len(nb.cells) != EXPECTED_CELL_COUNT:
        raise RuntimeError(f"{len(nb.cells)} cells, expected {EXPECTED_CELL_COUNT}")

    i_solve = _find_cell(nb, 'with open("output.log", "w")', 28)
    i_status = _find_cell(nb, "for i in mod_object.model.stages:", 40)
    i_pie = _find_cell(nb, 'pie = soln.create_plots("combined"', 48)
    i_stack = _find_cell(nb, "stackgraph = soln.create_stackgraph(", 52)
    i_func = _find_cell(nb, "def solve_model_and_make_plots", 57)
    i_exp1 = _find_cell(nb, "mod_no_invest = ExpansionPlanningModel(", 59)
    i_exp2 = _find_cell(nb, "data_object_fewer_repr_days = ExpansionPlanningData(", 63)

    nb.cells[i_solve].source = SOLVE_CELL_SRC
    nb.cells[i_pie].source += '\npie.write_html("soln_pie.html")  # [instrument]\n'
    nb.cells[
        i_stack
    ].source += '\nstackgraph.write_html("soln_stackgraph.html")  # [instrument]\n'
    nb.cells[i_func].source = SOLVE_FUNC_SRC

    for idx, old, new in (
        (i_exp1, EXP1_CALL_OLD, EXP1_CALL_NEW),
        (i_exp2, EXP2_CALL_OLD, EXP2_CALL_NEW),
    ):
        if old not in nb.cells[idx].source:
            raise RuntimeError(f"call site not found in cell {idx}")
        nb.cells[idx].source = nb.cells[idx].source.replace(old, new)

    # Insert new cells from the back so earlier indices stay valid.
    # Inserting twice at i_exp2 + 1 leaves the metrics table after the status cell.
    inserts = [
        (i_exp2 + 1, METRICS_TABLE_SRC),
        (i_exp2 + 1, EXP2_STATUS_SRC),
        (i_exp1 + 1, EXP1_STATUS_SRC),
        (i_status + 1, STATUS_HELPER_SRC),
    ]
    for idx, src in inserts:
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
