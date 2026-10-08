# Session log: PMAPS 123-bus tutorial (Session 2) reproduction + first 123-bus size/time measurement

**Date:** 2026-10-08
**Branch:** `eval/upstream-0930` @ `323e31c` (on upstream `7b84352`), worktree `~/Documents/GitHub/idaes-gtep-eval`
**Plan of record:** `admin/prompt/gtep/03-pmaps-123bus-tutorial.md` v1, pre-approved; prompt 01 ground rules apply.
**Env:** `gtep_up` (`/opt/anaconda3/envs/gtep_up/bin/python`), Python 3.11.17, highspy/HiGHS 1.15.1, pyomo 6.10.1.

## Post-plan log

**Goal.** T1: run the 123-bus Session-2 notebook baseline (2 rep days x 1 h) and Experiment 1
(no investment) live and compare cell-22 energy-by-type against the stored outputs (pass: both
`optimal` at 1 % gap, total GWh within 1 %, each type within 10 %); per-generator diff of
Experiment 1 against the shipped `soln_expr1/generation.json`; record objectives (no stored
values exist). T2: build and solve Experiment 2 (10 rep days x 5 commitment periods,
`transmission=True`, `mip_rel_gap=0.01`, `time_limit=7200`) as the first honest 123-bus
size/time measurement on upstream, and put it next to the authors' "around 36 minutes" and
the fork's May Gurobi numbers.

**Approach.** Notebook copied four levels deep (`output/123bus/`) so no path patch is needed;
`soln_expr1/`, `soln_expr2/` copied beside it as references. One nbformat script
(`scripts/patch_tutorial_123bus.py`, signature locator reused from the 5-bus script, 28 cells
asserted) instruments cells 9 / 14 / 17 and inserts three code cells (Experiment 1 live,
Experiment 2 live, metrics). All `instrument`, no `fix`, no package patch.

**Key context.** 581 generators (289 candidates incl. 117 thermal CT-c); helper writes to
`output.log` and returns `None` unless `optimal`, so the patched helper takes a `log_file`
and also writes results on `maxTimeLimit` (legacy HiGHS wrapper loads a feasible incumbent,
default `raise_exception_on_nonoptimal_result=False`). Cell 22's `dispatch_duration=1.0` is
correct for all three setups.

## Incremental log

- 10-08 Fork fingerprints unchanged from prompt 01; worktree clean at `323e31c`.
- 10-08 Choice: nbconvert cell timeout set to 9000 s instead of the prompt's 3600 s, because a
  3600 s cell cannot contain the mandated 7200 s solver time limit. This is the single
  allowed "raise once"; the solver `time_limit` stays 7200.
- 10-08 Problem: the cell-9 signature `opt.options["mip_rel_gap"] = 0.01` also appears in the
  cell-8 markdown. Solved by locating on `mod_object.timer.toc("Finished solving");`.
- 10-08 Choice: Experiment 1 and 2 models are `del`-ed after their metrics are captured
  (mirrors cell 14's own pattern) to keep kernel memory down.
- 10-08 Choice: peak RSS via `resource.getrusage(RUSAGE_SELF).ru_maxrss`, reported as the
  kernel's cumulative high-water mark (not per-model).
- 10-08 Run launched: 31-cell instrumented notebook, in place, `output/123bus/`.
- 10-08 Note: `$PY -m jupyter nbconvert` dispatches to the base-env `jupyter-nbconvert` driver,
  but the kernel is the `gtep_up` kernelspec (verified: kernel process is
  `/opt/anaconda3/envs/gtep_up/bin/python`); same as in prompt 01. Execution env is correct.
- 10-08 T1 live results (from the JSONs, before the notebook finished): baseline optimal, HiGHS
  gap 0.399 %, 17.76 s, 303 nodes, objective 160,893,821.96; Experiment 1 optimal, gap 0.098 %,
  4.12 s, root node, objective 261,411,080.69. Total GWh 74.9098 in both cases = stored exactly;
  WIND identical to stored in both cases. **Finding:** thermal mix differs. Baseline COAL
  2.2951 vs stored 6.4307 (-64 %), CT +7.6 %, NUC 2.43 GWh vs stored 0 (gen `1`, 2430 MW, rep
  period 1 only). Experiment 1 COAL +1.0 %, CT -6.4 %, NUC 2.43 vs 0. Per the plan both cases
  are re-solved once at `mip_rel_gap=1e-4` (`scripts/resolve_123bus_tight_gap.py`, run as a
  separate process alongside Experiment 2; 14 cores, HiGHS MIP single-threaded, so timing
  contamination is small; safety `time_limit=3600` added by me, logged here).
- 10-08 Upstream history check: between the tutorial's stored run (commits of 09-15/16) and
  `7b84352` the only commit touching model/data/tutorial is `e9b2ea5` (stackgraph display
  only). Model and 123-bus data are identical to what the authors ran, so the thermal-mix
  difference is solver-side (HiGHS version / platform / 1 % gap), not a code or data change.
- 10-08 Observation (continues prompt 01): baseline `renewable_investments.json` has 82 `wind_*-c`
  candidates with non-zero `renewableOperational` (e.g. `wind_3-c` 690 MW) and **no**
  `renewableInstalled` entries at all; all 117 `ct_fe_*-c` are `genDisabled`. Candidate wind
  generates in the baseline through the unfixed stage-1 `renewableOperational`
  (`gen.py:119@7b84352`), not through an investment decision. The stored run's WIND total is
  identical, so the authors' "Wind candidates were the only ones to be installed" (cell 12)
  describes the same effect.
- 10-08 Data note: `gen.csv` has `Fuel Price $/MMBTU = 0` and `HR_avg_0 = 0` for NUC; costs come
  from `cost_data` (ATB), so NUC/COAL/CT marginal costs are set there.
- 10-08 Tight-gap re-solve done (134 s total). Baseline at 1e-4: objective 160,255,921.54
  (vs 160,893,821.96 at 1 %, i.e. the 1 % run sat 0.40 % above the tight optimum), 5135 nodes,
  94.7 s; mix COAL 9.5695 / CT 19.2634 / NUC 0 / WIND 46.0769 GWh. Experiment 1 at 1e-4:
  261,161,454.22, 622 nodes, 27.1 s; COAL 10.1960 / CT 39.1314 / NUC 2.7086 / WIND 22.8739.
  **Conclusion:** the thermal split is near-degenerate; tightening the gap moves COAL from
  2.30 to 9.57 GWh (stored 6.43) rather than toward the stored value. WIND and total GWh are
  identical in every run. The 10 % per-type band is therefore not a reproducibility criterion
  this problem can meet across HiGHS builds; totals + termination are. Reported as a formal
  per-type miss with this explanation, no further re-solves.
- 10-08 Model size at Big-M (same model in notebook and re-solve): baseline 15504 rows / 10625
  cols / 5196 binaries; Experiment 1 15503 / 10163 / 5079.
- 10-08 Experiment 2: build + transform about 2.5 min (02:42:30 -> HiGHS log opened 02:45),
  kernel RSS 6.4 GB at solve start.
- 10-08 Notebook run finished: 0 errors, 1765 s wall. Experiment 2: build 15.4 s, transform
  36.1 s, 1,192,289 rows / 514,805 cols / 399,216 binaries, solve wall 1518.1 s (HiGHS 1440.9 s),
  optimal, gap 0.0637 %, 1317 nodes, objective 22,909,901,015.18, peak RSS 8.06 GB. Time limit
  7200 s not reached. No candidate installed; branches 30 retired / 2 disabled / 2 extended.
- 10-08 Visual check done numerically: pie values embedded in the shipped and local HTML are
  identical for Experiment 1 and 2 (Experiment 2 Wind 42,980 MW, Gas CT 172,070 MW).
- 10-08 Choice: executed 123-bus notebook (13.5 MB) not committed; cleared copy committed.

## End-of-session summary

- **Outcome.** T1: both live solves optimal, totals and WIND identical to stored; per-type
  thermal mix misses the 10 % band, re-solved once at 1e-4 as the plan requires, explained as
  near-degeneracy (model/data unchanged since the authors' run). T2: Experiment 2 optimal in
  25.3 min, first honest 123-bus size/time point on upstream (1.19 M rows, 399 k binaries).
- **Patches.** 0 `fix`, instrumentation only, no package patch, no fork fix.
- **Report.** `quality_reports/reports/2026-10-08_pmaps_123bus_tutorial_reproduction.md`;
  tables in `explorations/upstream_eval/results_123bus.md`; INDEX row added.
- **Open questions.** Per-type criterion; loose candidate `renewableOperational` now visible in
  every 123-bus result and in the shipped pies; no investment in Experiment 2; pie capacity
  accounting (172 GW Gas CT); hydro at zero.
- **Blockers.** None. Nothing pushed.
