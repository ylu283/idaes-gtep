# PMAPS 5-bus tutorial reproduction on upstream 7b84352

**Date:** 2026-10-08
**Branch:** `eval/upstream-0930` (worktree `~/Documents/GitHub/idaes-gtep-eval`, based on upstream `7b84352`, PR #190 merge of 2026-09-30)
**Plan of record:** `admin/prompt/gtep/01-upstream-resync-assessment.md` v4 (T2)
**Author:** ylu283
**Status:** complete; pass gate met; instrumentation done

## Header: environment

| item | this run | reference (stored notebook outputs, PR #155) |
|---|---|---|
| Python | 3.11.17 | 3.14.7 |
| highspy / HiGHS | 1.15.1 / 1.15.1 | unrecorded |
| pyomo | 6.10.1 | unrecorded |
| gridx-egret / gridx-prescient | 0.5.5 / 2.2.2 (pinned in `pyproject.toml`) | same pins |
| CPU arch / platform | arm64 / macOS 15.5 | Windows x64 |
| `mip_rel_gap` | not set (HiGHS default 1e-4) | not set |

Env evidence line (`gtep_up`, `/opt/anaconda3/envs/gtep_up/bin/python`):

```
/Users/yilu/Documents/GitHub/idaes-gtep-eval/gtep/__init__.py
highspy 1.15.1 HiGHS 1.15.1 pyomo 6.10.1
```

Test gate (`$PY -m pytest gtep/tests/unit -q`):

```
70 passed, 150 warnings in 245.86s (0:04:05)
```

## 1. Summary

The shipped tutorial `docs/source/tutorials/5bus/tutorial_5bus.ipynb` (65 cells)
runs green end to end under HiGHS on this machine after a single path patch, and
all three objectives reproduce the stored outputs to floating-point noise
(relative difference about 1e-12, pass gate 2e-4). The whole notebook executes
in 51 s; the baseline MILP (4 representative days, investment on) solves in
12.6 s with 172 branch-and-bound nodes, the two experiments at the root node.
No package-level patch was needed. Instrumentation (model size, wall time,
per-experiment HiGHS logs, generator status for every case) was added as an
nbformat script and the instrumented copy re-executed; objectives are bitwise
identical between the two runs.

## 2. Comparison table (T2 step 3, pass gate)

| case | expected | obtained | rel. diff | termination | MIP gap (HiGHS log) | wall time (s) |
|---|---|---|---|---|---|---|
| baseline (4 rep days, investment) | 3,168,393.4448 | 3,168,393.4448 | 1.0e-12 | optimal | 0% (tol 0.01%) | 12.59 |
| Experiment 1 (`mod_no_invest`) | 3,767,479.0251 | 3,767,479.0251 | 1.3e-12 | optimal | 0% (tol 0.01%) | 3.73 |
| Experiment 2 (`mod_fewer_repr_days`) | 3,265,990.3818 | 3,265,990.3818 | 3.0e-13 | optimal | 0% (tol 0.01%) | 1.65 |

**Pass.** Full-precision values and HiGHS-internal timings are in
`explorations/upstream_eval/results_5bus.md`. Wall time is `perf_counter()`
around `opt.solve` in the instrumented re-run; the un-instrumented baseline
run reported HiGHS `Timing 11.90` s. Because the diffs are far below 1e-4,
the optional `mip_rel_gap = 1e-6` re-solve was not triggered.

## 3. Metrics table (T2 step 4)

| case | objective | thermal gens operational/extended | renewable capacity by gen (MW) | wall time (s) | rows / cols / binaries | termination |
|---|---|---|---|---|---|---|
| baseline | 3,168,393.4448 | 3_CT, 10_STEAM, 4_CC, 4_STEAM | 10_PV: 20.8; 2_RTPV: 7.8; 1_HYDRO: 48.5; 4_WIND: 118.5; 10_PV-c: 20.8; 2_RTPV-c: 0.0; 1_HYDRO-c: 48.5; 4_WIND-c: 118.5 | 12.59 | 16175 / 9159 / 3952 | optimal |
| no_invest | 3,767,479.0251 | 3_CT, 10_STEAM, 4_CC, 4_STEAM | 10_PV: 20.8; 2_RTPV: 7.8; 1_HYDRO: 48.5; 4_WIND: 118.5; 10_PV-c: 0.0; 2_RTPV-c: 0.0; 1_HYDRO-c: 0.0; 4_WIND-c: 0.0 | 3.73 | 16174 / 9150 / 3952 | optimal |
| fewer_repr_days | 3,265,990.3818 | 3_CT, 10_STEAM, 4_CC, 4_STEAM | 10_PV: 20.0; 2_RTPV: 7.2; 1_HYDRO: 39.1; 4_WIND: 118.5; 10_PV-c: 20.0; 2_RTPV-c: 0.0; 1_HYDRO-c: 39.1; 4_WIND-c: 118.5 | 1.65 | 8095 / 4599 / 1984 | optimal |

rows / cols / binaries are `build_model_size_report(model).activated`
constraints / variables / binary_variables after `gdp.bigm`. B&B nodes
172 / 1 / 1, LP iterations 41,774 / 12,269 / 7,492.

## 4. Patch table

| file | line / cell | kind | reason | upstream issue? |
|---|---|---|---|---|
| `explorations/upstream_eval/output/tutorial_5bus.ipynb` (copy of `docs/source/tutorials/5bus/tutorial_5bus.ipynb`) | 19 text occurrences, 4 source cells (9, 17, and the two data-path strings) | `fix` | copy lives one directory level shallower, so `../../../../gtep/data` -> `../../../gtep/data` | no (location artifact) |
| same, cell 28 | solve cell | `instrument` | `build_model_size_report` after Big-M, `perf_counter` around `opt.solve`, print wall + size | no |
| same, new cell after 40 | generator status | `instrument` | cell-40 loop wrapped as `report_generator_status(model, label)`, baseline metrics dict | no |
| same, cells 48 / 52 | plots | `instrument` | `fig.write_html(...)` for pie and stack figures | no |
| same, cell 57 | `solve_model_and_make_plots` | `instrument` | per-experiment `highs_<write_dir>.log` via the notebook's `redirect_stdout` pattern, `perf_counter`, size report, `write_html`, returns `(pie, stackgraph, result_object, wall, size)` | no |
| same, cells 59 / 63 | call sites | `instrument` | unpack the 5-tuple | no |
| same, new cells after 59 / 63, final cell | status + metrics | `instrument` | generator status for `mod_no_invest`, `mod_fewer_repr_days`; metrics table printed and written to `metrics_5bus.md` | no |

Package-level (`eval:`) patches: **none**. Fix-patch count: 1 of 3 allowed.
No fork fix (Fix 19 / Fix 20 or other) was ported.

Patch script: `explorations/upstream_eval/scripts/patch_tutorial_5bus.py`
(black-clean). Patched notebook with outputs cleared:
`explorations/upstream_eval/scripts/tutorial_5bus.ipynb` (69 cells);
executed copy `scripts/tutorial_5bus_executed.ipynb` (231 KB, plotly via cdn).

## 5. What was run, in order

1. Fork fingerprints recorded (status `bd6bef62...`, stash `08b39f41...`,
   both equal to the prompt's values); worktree `../idaes-gtep-eval` created
   at `7b84352` on branch `eval/upstream-0930`.
2. Commits `1c4a794` (chore: ignore local tooling) and `c4a9373` (eval: carry
   conventions). `.claude/` copied, never staged; `Bash(git push*)` denied
   in the worktree's `settings.local.json`; 13-line worktree `CLAUDE.md`.
3. `gtep_up` env (Python 3.11), worktree installed editable, kernelspec
   `gtep_up` registered, `README_pip_freeze.txt` written (133 lines).
4. Unit test gate: 70 passed (4 min 06 s, dominated by `test_drivers.py`).
5. Notebook copied to `explorations/upstream_eval/output/`, path patch
   applied (patch #1), executed with nbconvert in place: 0 errors, 51 s.
6. Objectives compared: pass.
7. `patch_tutorial_5bus.py` written and run; cleared copy committed under
   `scripts/`; instrumented copy executed in place: 0 errors; metrics table
   and per-experiment logs collected.

## 6. Observations (not findings against the pass gate; for prompts 02/03)

- **Upstream restructure.** `gtep_model.py` now delegates to a
  `gtep/model_library/` package (`gen.py`, `commitment.py`, `dispatch.py`,
  `investment.py`, `objective.py`, `representative_period.py`, `scaling.py`,
  `storage.py`, `transmission.py`, `hydropower_generation.py`). Any
  line-number references from the fork's model docs are stale on upstream.
- **Interpretation of `num_commit=6, duration_representative_period=6`.**
  Confirmed at `gtep/model_library/commitment.py:42@7b84352`
  (`p_max["values"][commitment_period - 1]`) and `scaling.py:36`: the model
  uses hours 00:00-06:00 of each representative day, with no aggregation.
  The tutorial objective is therefore a 6-hour-per-day planning problem
  weighted by the rep-day weights, not a full-day one.
- **Candidate renewables report non-zero "operational" capacity.** In the
  baseline, cell 40's `renewableOperational + renewableExtended` for each
  `*-c` renewable equals the existing unit's capacity (10_PV-c = 20.8 =
  10_PV; 4_WIND-c = 118.5). `gtep/model_library/gen.py:119-121@7b84352`
  sets `renewableOperational` of an out-of-service renewable to 0 with
  `set_value`, not `fix`, while fixing `renewableExtended` and
  `renewableRetired`. Under `include_investment=False` (lines 123-138) all
  five are fixed to 0, which is why Experiment 1 shows 0.0. Whether the
  stage-1 candidate value is a modelling choice or a loose variable is a
  question for prompt 02, not changed here.
- **No thermal candidates in the 5-bus model.** `model.thermalGenerators`
  has only the four existing units, although `cost_data` was loaded with
  `Natural Gas_FE` as a candidate. The candidate set that reaches the model
  is the renewable `*-c` units from the 5-bus CSVs.
- **Size report warning.** `unassociated_disjuncts: 2704` after Big-M in all
  three cases; binaries in `no_invest` equal the baseline (3952) because the
  candidate thermal disjuncts are fixed rather than removed.
- **Solve speed.** The baseline 5-bus MILP has 3952 binaries and solves in
  12.6 s; the two experiments solve at the root node. This is consistent with
  the tutorial being a teaching case, and says nothing yet about the
  "solved too fast" concern on the 123-bus case (prompts 02/03).
- **`%pip install highspy` cell** ran as "Requirement already satisfied"
  with no network access needed, as the prompt predicted.
- **nbconvert quirk.** `--clear-output` forces in-place and ignores
  `--output-dir`; the cleared `scripts/` copy was produced by the patch
  script itself (it clears outputs) plus `cp`.

## 7. Left for Kay (decisions deliberately not taken)

1. Whether the loose stage-1 `renewableOperational` for `*-c` renewables
   (`gen.py:119`) is intended; not patched, not reported upstream.
2. Whether the 6-hours-per-rep-day interpretation is what the tutorial
   authors meant; the notebook text does not say.
3. No `mip_rel_gap` tightening was run (not triggered by the gate).
4. No upstream issue was opened for anything above.
5. Nothing pushed; `eval/upstream-0930` exists only locally.
6. Python 3.11 was chosen over 3.14 (tutorial authors' version); the
   reproduction matched, so no 3.14 cross-check was run.
7. `test_drivers.py` subprocess outputs, if any, were not inspected beyond
   the pass line (`git status` is clean, so nothing landed in the tree).

## 8. Files

- `explorations/upstream_eval/README.md`, `SESSION_LOG.md`,
  `README_pip_freeze.txt`, `results_5bus.md`,
  `scripts/patch_tutorial_5bus.py`, `scripts/tutorial_5bus.ipynb`,
  `scripts/tutorial_5bus_executed.ipynb` (committed)
- `explorations/upstream_eval/output/` (ignored): `output.log`,
  `highs_soln_no_invest.log`, `highs_soln_fewer_repr_days.log`, `soln*/`,
  `*_pie.html`, `*_stackgraph.html`, `metrics_5bus.md`, executed notebook
- Session log: `quality_reports/session_logs/2026-10-08_pmaps_5bus_tutorial.md`
