# PMAPS 123-bus tutorial (Session 2) reproduction + first 123-bus size/time measurement on upstream 7b84352

**Date:** 2026-10-08
**Branch:** `eval/upstream-0930` (worktree `~/Documents/GitHub/idaes-gtep-eval`, upstream `7b84352`)
**Plan of record:** `admin/prompt/gtep/03-pmaps-123bus-tutorial.md` v1 (prompt 01 ground rules)
**Author:** ylu283
**Status:** complete. T1: solves and totals reproduce, per-type thermal mix does not (near-degenerate). T2: Experiment 2 solved to optimality in 25.3 min.

## Header: environment

| item | this run | reference (stored outputs, PR #155) |
|---|---|---|
| Python / highspy / HiGHS / pyomo | 3.11.17 / 1.15.1 / 1.15.1 / 6.10.1 | 3.14.7 / unrecorded / unrecorded / unrecorded |
| platform | arm64, macOS 15.5, 14 cores, 48 GB | Windows x64 |
| `mip_rel_gap` | 0.01 (as shipped); re-solves at 1e-4 | 0.01 |
| env evidence | `/Users/yilu/Documents/GitHub/idaes-gtep-eval/gtep/__init__.py` | |

## 1. Summary

The 123-bus Session-2 notebook runs green end to end on upstream `7b84352` with no path
patch and no package patch: 31 instrumented cells, 0 errors, 29.4 min wall. Baseline and
Experiment 1 both terminate `optimal` within the shipped 1 % gap and reproduce the stored
total energy exactly (74.9098 GWh) and the stored WIND energy exactly. The thermal split
among COAL / CT / NUC does **not** reproduce: our baseline dispatches 2.43 GWh of nuclear
and 2.30 GWh of coal where the stored run had 0 and 6.43. A one-time re-solve at a 1e-4 gap
moves coal to 9.57 GWh, not toward the stored value, while the objective drops only 0.40 %.
The thermal dispatch is near-degenerate, so the plan's 10 % per-type band is not a criterion
this problem can meet across HiGHS builds; the model and data are the same as the authors'.

Experiment 2 (10 rep days x 5 commitment periods, transmission on) built in 15 s,
transformed in 36 s, and solved to `optimal` (gap 0.064 %) in **25.3 min** on HiGHS with
1.19 M rows, 515 k columns, 399 k binaries and 8.1 GB peak RSS. The authors reported
"around 36 minutes". The shipped Experiment 2 capacity pie is numerically identical to
ours. No candidate asset was installed in any of the three cases.

## 2. T1 comparison table

| case | quantity | stored | obtained (1 % gap) | rel. diff | re-solve 1e-4 gap | rel. diff | termination | MIP gap | solve s |
|---|---|---|---|---|---|---|---|---|---|
| baseline | COAL GWh | 6.4307 | 2.2951 | -64.3 % | 9.5695 | +48.8 % | optimal | 0.399 % | 19.06 |
| baseline | CT GWh | 22.4022 | 24.1079 | +7.6 % | 19.2634 | -14.0 % | optimal | 0.399 % | 19.06 |
| baseline | NUC GWh | 0 | 2.4300 | n/a | 0 | n/a | optimal | 0.399 % | 19.06 |
| baseline | WIND GWh | 46.0769 | 46.0769 | 0.00 % | 46.0769 | 0.00 % | optimal | 0.399 % | 19.06 |
| baseline | total GWh | 74.9098 | 74.9098 | 0.00 % | 74.9098 | 0.00 % | optimal | 0.399 % | 19.06 |
| Experiment 1 | COAL GWh | 12.1546 | 12.2764 | +1.0 % | 10.1960 | -16.1 % | optimal | 0.098 % | 6.13 |
| Experiment 1 | CT GWh | 39.8813 | 37.3295 | -6.4 % | 39.1314 | -1.9 % | optimal | 0.098 % | 6.13 |
| Experiment 1 | NUC GWh | 0 | 2.4300 | n/a | 2.7086 | n/a | optimal | 0.098 % | 6.13 |
| Experiment 1 | WIND GWh | 22.8739 | 22.8739 | 0.00 % | 22.8739 | 0.00 % | optimal | 0.098 % | 6.13 |
| Experiment 1 | total GWh | 74.9098 | 74.9098 | 0.00 % | 74.9098 | 0.00 % | optimal | 0.098 % | 6.13 |
| solve time (informational) | baseline | 9.66 s (Windows) | 19.06 s (arm64) | | 94.7 s | | | | |

**Gate result.** Termination: pass. Total GWh within 1 %: pass. Per-type within 10 %:
miss on baseline COAL and on NUC (both cases); Experiment 1 COAL and CT pass. The finding
was handled per the plan (one re-solve at 1e-4, both numbers reported).

**Objectives** (no stored values exist; reference for prompt 04): baseline
160,893,821.9612 (1 % gap) / 160,255,921.5403 (1e-4); Experiment 1 261,411,080.6851 /
261,161,454.2164; Experiment 2 22,909,901,015.1818 (1 % gap run, actual gap 0.064 %).

**Per-generator check, Experiment 1** (local vs shipped `generation.json`): 259 shipped
keys, 253 local, 313 in the union; max |delta| 4008.4 MW; 117 generators differ by more
than 1 MW; the five largest are gen 235 (CT, +4008.4), gen 1 (NUC, +2430.0), gen 181
(COAL, -1980.0 in both rep periods), gen 176 (CT, -1850.8). Whole units swap in and out;
this is unit commitment degeneracy, not numerical noise.

**Candidates in the baseline.** All 117 `ct_fe_*-c` are `genDisabled`; 82 `wind_*-c`
carry non-zero `renewableOperational` (e.g. `wind_3-c` 690 MW) and there is no
`renewableInstalled` entry at all. Candidate wind generates via the unfixed stage-1
`renewableOperational` (`gtep/model_library/gen.py:119@7b84352`), continuing prompt 01's
observation; the stored WIND total being identical shows the authors' run did the same,
which is what cell 12's "Wind candidates were the only ones to be installed" is describing.

## 3. T2 measurement table (Experiment 2)

| quantity | value |
|---|---|
| structure | 1 stage x 10 rep days x 5 commitment periods x 1 dispatch, `transmission=True`, `scale_loads=False` |
| build / Big-M transform | 15.4 s / 36.1 s |
| rows / cols / binaries (activated, after Big-M) | 1,192,289 / 514,805 / 399,216 |
| disjunctions / disjuncts (overall) | 84,300 / 194,600 |
| peak RSS (kernel, cumulative over the whole notebook) | 8.06 GB |
| solve wall / HiGHS `Timing` | 1518.1 s (25.3 min) / 1440.9 s (presolve 44 s) |
| termination / final gap | optimal / 0.0637 % (tolerance 1 %, time limit 7200 s not reached) |
| B&B nodes / LP iterations | 1,317 / 1,416,435 |
| objective | 22,909,901,015.1818 |
| energy by type (GWh over 10 x 5 h) | COAL 123.98, CT 647.18, NUC 43.00, WIND 942.22 |
| investment summary | no `genInstalled` / `renewableInstalled`; 82 wind-c via `renewableOperational` (e.g. `wind_3-c` 780 MW); branches `branchRetired` 30, `branchDisabled` 2, `branchExtended` 2 |
| visual check vs shipped pie | identical values: Coal 14,761 / Gas CT 172,070 / Hydro 498 / Nuclear 5,139 / Solar 9,316 / Wind 42,980 MW |

### Scale table

| run | structure | network | solver | rows | binaries | solve time |
|---|---|---|---|---|---|---|
| Experiment 2, this run | 1 stage x 10 rep days x 5 h | transmission on | HiGHS 1.15.1, 1 % gap, arm64 | 1.19 M | 399 k | 25.3 min, optimal 0.064 % |
| Experiment 2, authors | same | same | HiGHS (unrecorded), Windows x64 | n/a | n/a | "around 36 minutes" |
| fork May 2026, 4HR config | 3 stages x 4 rep days x 24 h, 4-h commitment | no transmission investment | Gurobi 11 | 7.0 M | n/a | 3 min |
| fork May 2026, 1HR config | 3 stages x 4 rep days x 24 h, 1-h commitment | same | Gurobi 11 | 30.7 M | n/a | 78 min |

Scale, not equivalence: 50 operating hours with transmission on an open-source solver
versus 288 hours over three stages without it on Gurobi. Per row, HiGHS on this machine
spent about 1.3 ms per row; the May 4HR Gurobi run about 0.03 ms per row.

## 4. Patch table

| file | where | kind | reason | upstream issue? |
|---|---|---|---|---|
| `output/123bus/tutorial_123bus.ipynb` (copy of `docs/source/tutorials/123bus/tutorial_123bus.ipynb`, no path patch) | cell 9 | instrument | size report after Big-M, `perf_counter` around solve, termination print | no |
| same | cell 14 | instrument | print `baseline_objective`; metrics dict | no |
| same | cell 17 helper | instrument | `log_file` parameter (per-run HiGHS log), size report, wall time, 5-tuple return, saves results on `maxTimeLimit` too, `write_html` | no |
| same | new cell after 19 | instrument | Experiment 1 live into `soln_expr1_local/`, `highs_expr1.log`, model deleted after capture | no |
| same | new cell after 25 | instrument | Experiment 2 live into `soln_expr2_local/`, `mip_rel_gap 0.01`, `time_limit 7200`, `highs_expr2.log`, peak RSS | no |
| same | new final cell | instrument | metrics tables, per-generator diff, candidate status, `metrics_123bus.md` | no |
| `scripts/resolve_123bus_tight_gap.py` | standalone | instrument | T1 step 3 re-solve at `mip_rel_gap=1e-4` (safety `time_limit=3600`, not hit) | no |

`fix` patches: 0 of 3. Package patches: none. No fork fix ported.
nbconvert cell timeout was set to 9000 s (one raise, from the prompt's 3600 s) because a
3600 s cell cannot hold the mandated 7200 s solver limit; the solver limit itself stayed 7200 s.

## 5. Observations

- **Thermal-mix degeneracy.** Gap 1 % -> 1e-4 changes the baseline objective by 0.40 % and
  swaps whole units (coal 2.3 -> 9.6 GWh, nuclear 2.4 -> 0). With one-hour horizons and
  startup costs, several commitments cost nearly the same. Any "reproduces the stored
  dispatch" claim for this tutorial needs a per-type tolerance far wider than 10 %, or a
  comparison on objective and totals only.
- **Nuclear dispatch.** The stored run never dispatches either NUC unit (2,430 and 2,709 MW);
  our 1 % runs dispatch one of them in one rep period, our tight baseline none, our tight
  Experiment 1 the other. `gen.csv` has `Fuel Price = 0` and `HR_avg_0 = 0` for NUC, so its
  cost comes entirely from `cost_data`.
- **No investment in any case.** Even Experiment 2 with transmission on installs nothing;
  candidate wind shows up only via the loose `renewableOperational`. Candidate branches end
  up `branchRetired` (30) / `branchDisabled` (2) / `branchExtended` (2) in stage 1.
- **Pie chart semantics.** The capacity pie counts the candidate `renewableOperational` as
  installed capacity (Wind 42,980 MW in Experiment 2 vs 20,320 in Experiment 1), and shows
  Gas CT at 172 GW against 109 GW of existing capacity in the data notes. Which capacity
  variables the pie sums is worth a look in `gtep_solution.py` before any 123-bus claim is
  made from it.
- **No PV or hydro energy** in any case: all three setups cover hours 00:00-01:00 or
  00:00-05:00, so zero solar is expected; hydro at 0 is not explained here.
- **Timing.** Baseline solve 19 s here vs 9.7 s on the authors' Windows machine; Experiment 2
  25 min vs their 36. Big-M overall vs activated counts differ by a factor of 1.25 in rows
  (1.48 M vs 1.19 M) and the size report again warns of unassociated disjuncts (193,866).
- **`$PY -m jupyter nbconvert`** dispatches to the base-env `jupyter-nbconvert` driver, but
  the kernel is `gtep_up` (verified by process list); execution env is correct.

## 6. Left for Kay

1. Whether to treat objective + totals as the 123-bus reproduction criterion and drop the
   per-type band; not changed in the plan here.
2. Whether the unfixed candidate `renewableOperational` (`gen.py:119`) should be fixed
   upstream or reported; it now affects every 123-bus result including the shipped pies.
3. Why no candidate is ever installed in Experiment 2 (cost data vs. free candidate wind);
   not investigated.
4. The pie's capacity accounting (172 GW Gas CT) not traced.
5. No Experiment 2 re-solve at a tighter gap, no threads / scaling options tried.
6. Executed 123-bus notebook (13.5 MB, embeds the shipped plotly HTML) not committed;
   the cleared copy is.
7. Nothing pushed; no upstream issue opened.

## 7. Files

- `explorations/upstream_eval/results_123bus.md`, `scripts/patch_tutorial_123bus.py`,
  `scripts/resolve_123bus_tight_gap.py`, `scripts/tutorial_123bus.ipynb` (committed)
- `explorations/upstream_eval/output/123bus/` (ignored): executed notebook, `output.log`,
  `highs_expr1.log`, `highs_expr2.log`, `highs_*_tight.log`, `soln*/`, `*_pie.html`,
  `*_stackgraph.html`, `metrics_123bus.md`, `tight_gap_results.md`
- Session log: `quality_reports/session_logs/2026-10-08_pmaps_123bus_tutorial.md`
