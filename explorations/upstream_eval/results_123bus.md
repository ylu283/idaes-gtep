# 123-bus tutorial (Session 2) reproduction results (upstream 7b84352)

Executed 2026-10-08 with `gtep_up`: Python 3.11.17, highspy 1.15.1, HiGHS 1.15.1,
pyomo 6.10.1, gridx-egret 0.5.5, gridx-prescient 2.2.2, arm64 / macOS 15.5, 14 cores,
48 GB. Reference: stored notebook outputs (PR #155, Windows x64, Python 3.14.7, HiGHS
and pyomo versions unrecorded), `soln_expr1/generation.json`, and the shipped HTML
pies. `mip_rel_gap = 0.01` everywhere, as shipped.

## T1 comparison (baseline + Experiment 1 live, cell-22 energy, GWh, dispatch_duration=1.0)

| case | quantity | stored | obtained (1 % gap) | rel. diff | re-solve at 1e-4 gap | rel. diff | termination | MIP gap (1 % run) | solve s |
|---|---|---|---|---|---|---|---|---|---|
| baseline | COAL | 6.4307 | 2.2951 | -64.3 % | 9.5695 | +48.8 % | optimal | 0.399 % | 19.06 |
| baseline | CT | 22.4022 | 24.1079 | +7.6 % | 19.2634 | -14.0 % | optimal | 0.399 % | 19.06 |
| baseline | NUC | 0 | 2.4300 | n/a | 0 | n/a | optimal | 0.399 % | 19.06 |
| baseline | WIND | 46.0769 | 46.0769 | 0.00 % | 46.0769 | 0.00 % | optimal | 0.399 % | 19.06 |
| baseline | total | 74.9098 | 74.9098 | 0.00 % | 74.9098 | 0.00 % | optimal | 0.399 % | 19.06 |
| Experiment 1 | COAL | 12.1546 | 12.2764 | +1.0 % | 10.1960 | -16.1 % | optimal | 0.098 % | 6.13 |
| Experiment 1 | CT | 39.8813 | 37.3295 | -6.4 % | 39.1314 | -1.9 % | optimal | 0.098 % | 6.13 |
| Experiment 1 | NUC | 0 | 2.4300 | n/a | 2.7086 | n/a | optimal | 0.098 % | 6.13 |
| Experiment 1 | WIND | 22.8739 | 22.8739 | 0.00 % | 22.8739 | 0.00 % | optimal | 0.098 % | 6.13 |
| Experiment 1 | total | 74.9098 | 74.9098 | 0.00 % | 74.9098 | 0.00 % | optimal | 0.098 % | 6.13 |
| solve time (informational) | baseline | 9.66 s (Windows) | 19.06 s (arm64) | | 94.7 s | | | | |
| solve time (informational) | Experiment 1 | n/a | 6.13 s | | 27.1 s | | | | |

**Gate:** both solves `optimal` within the 1 % gap: pass. Total GWh within 1 %: pass
(identical). Each unit type within 10 %: **miss** (baseline COAL, NUC in both cases;
Experiment 1 CT passes at -6.4 %). The tight-gap re-solve (`mip_rel_gap=1e-4`,
`scripts/resolve_123bus_tight_gap.py`) moves COAL to 9.57 GWh, not toward the stored
6.43, with WIND and totals unchanged: the thermal split among COAL / CT / NUC is
near-degenerate and any HiGHS build at a 1 % gap lands on a different near-optimal vertex.
Model and 123-bus data are identical to the authors' run (no model/data commits between the
stored run and `7b84352`).

Objectives (no stored values; these become the reference for prompt 04):

| case | objective, 1 % gap run | HiGHS gap | objective, 1e-4 gap re-solve | HiGHS gap | nodes (1 % / 1e-4) |
|---|---|---|---|---|---|
| baseline | 160,893,821.9612 | 0.399 % | 160,255,921.5403 | 0.00286 % | 303 / 5135 |
| Experiment 1 | 261,411,080.6851 | 0.098 % | 261,161,454.2164 | 0.00251 % | 1 / 622 |
| Experiment 2 | 22,909,901,015.1818 | 0.0637 % | not run | | 1317 |

Stored baseline timer: build 0.71 s, transform 0.75 s, solve 9.66 s. Ours: build 0.65 s,
transform 0.62 s, solve 19.95 s (timer) / 19.06 s (`perf_counter` around `opt.solve`).

### Experiment 1 per-generator diff, `soln_expr1_local/generation.json` minus shipped (MW)

- keys: shipped 259, local 253, union 313
- max |delta|: 4008.4 MW; generators with |delta| > 1 MW: 117
- five largest: gen 235 (CT) +4008.4 (rep 1); gen 1 (NUC) +2430.0 (rep 1);
  gen 181 (COAL) -1980.0 (rep 2) and -1980.0 (rep 1); gen 176 (CT) -1850.8 (rep 1)

### Candidate (`-c`) status in the baseline (non-zero investment-JSON entries)

- `genDisabled`: all 117 `ct_fe_*-c` (no thermal candidate installed)
- `renewableOperational`: 82 `wind_*-c` with non-zero MW (e.g. `wind_3-c` 690.0, `wind_1-c`
  567.7); **no `renewableInstalled` entry anywhere**. Continues prompt 01's observation
  (`gtep/model_library/gen.py:119@7b84352`): candidate wind generates through the unfixed
  stage-1 `renewableOperational`, not through an investment decision.

## T2 measurement (Experiment 2 live: 1 stage x 10 rep days x 5 commitment periods, transmission on)

| quantity | value |
|---|---|
| build (`create_model`) | 15.4 s |
| Big-M transform (timer) | 36.1 s |
| rows / cols / binaries after Big-M (activated) | 1,192,289 / 514,805 / 399,216 |
| disjunctions / disjuncts (overall) | 84,300 / 194,600 |
| peak RSS (kernel, cumulative) | 8.06 GB |
| solve wall (`perf_counter`) / HiGHS `Timing` | 1518.1 s (25.3 min) / 1440.9 s (presolve 44.3 s, solve 1396.6 s) |
| termination / final gap | optimal / 0.0637 % (tolerance 1 %) |
| B&B nodes / LP iterations | 1,317 / 1,416,435 |
| objective | 22,909,901,015.1818 |
| save JSON / plotting | 57.0 s / 0.5 s |
| energy by type (GWh, 10 days x 5 h) | COAL 123.98, CT 647.18, NUC 43.00, WIND 942.22 |
| installed candidate capacity by type | none (`renewableInstalled` / `genInstalled` absent) |
| candidate status entries | `genDisabled` 117 CT-c; `renewableOperational` 82 wind-c (e.g. `wind_3-c` 780.2, `wind_1-c` 643.3); branches: `branchRetired` 30, `branchDisabled` 2, `branchExtended` 2 (`233-c`, `236-c`) |

Whole notebook under nbconvert: 29.4 min wall (1765 s).

### Visual comparison with the shipped `soln_expr2/piechart_combined_2019.html`

Values embedded in the plotly HTML (installed capacity, MW): shipped and local are
identical: Coal 14,761 (6.0 %), Gas CT 172,070 (70.3 %), Hydro 498 (0.2 %), Nuclear
5,139 (2.1 %), Solar 9,316 (3.8 %), Wind 42,980 (17.6 %). Experiment 1 pies are also
identical (Solar 8,395, Wind 20,320). The pie is a capacity view, so it does not see the
thermal-dispatch degeneracy; the extra Wind / Solar relative to Experiment 1 is the
candidate `renewableOperational`, which the pie counts as capacity.

### Scale table (this run vs the authors vs the fork's May numbers)

| run | structure | network | solver | rows (after transform) | binaries | solve time |
|---|---|---|---|---|---|---|
| Experiment 2, this run | 1 stage x 10 rep days x 5 h (5 commit x 1 dispatch) | transmission on (DC flow, candidate branches) | HiGHS 1.15.1, 1 % gap, arm64 | 1.19 M | 399 k | 25.3 min (optimal, 0.064 %) |
| Experiment 2, authors | same | same | HiGHS (version unrecorded), 1 % gap, Windows x64 | not reported | not reported | "around 36 minutes" |
| fork, May 2026, 4HR config | 3 stages x 4 rep days x 24 h, 4-h commitment | no PTDF / no transmission investment | Gurobi 11 | 7.0 M | n/a | 3 min |
| fork, May 2026, 1HR config | 3 stages x 4 rep days x 24 h, 1-h commitment | same | Gurobi 11 | 30.7 M | n/a | 78 min |

The point is scale, not equivalence: Experiment 2 has 50 hours of operation on a 123-bus
network with transmission, the May runs 288 hours over 3 stages without it, on a
commercial solver.
