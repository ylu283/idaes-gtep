# 5-bus tutorial reproduction results (upstream 7b84352)

Executed 2026-10-08 with `gtep_up`: Python 3.11.17, highspy 1.15.1, HiGHS 1.15.1,
pyomo 6.10.1, gridx-egret 0.5.5, gridx-prescient 2.2.2, arm64 / macOS 15.5.
Reference (stored notebook outputs, PR #155): Windows x64, Python 3.14.7, HiGHS and
pyomo versions unrecorded. No `mip_rel_gap` set on either side (HiGHS default 1e-4).
Pass gate: all three `optimal` and |obtained - expected| / expected <= 2e-4.

## Table 1: comparison against stored outputs (baseline run, un-instrumented)

| case | expected | obtained | rel. diff | termination | MIP gap (HiGHS log) | wall time (s) |
|---|---|---|---|---|---|---|
| baseline (4 rep days, investment) | 3,168,393.4448 | 3,168,393.4448 | 1.0e-12 | optimal | 0% (tol 0.01%) | 12.59 |
| Experiment 1 (`mod_no_invest`) | 3,767,479.0251 | 3,767,479.0251 | 1.3e-12 | optimal | 0% (tol 0.01%) | 3.73 |
| Experiment 2 (`mod_fewer_repr_days`, 2 rep days) | 3,265,990.3818 | 3,265,990.3818 | 3.0e-13 | optimal | 0% (tol 0.01%) | 1.65 |

Full-precision obtained values: 3168393.4448161027, 3767479.025134868,
3265990.381766974 (expected 3168393.4448128548, 3767479.0251299744,
3265990.3817659924). Result: **pass**, all three within 2e-4 (in fact at
floating-point noise). Objectives are identical between the un-instrumented
baseline run and the instrumented re-run. Wall time is `time.perf_counter()`
around `opt.solve` from the instrumented re-run (HiGHS-internal `Timing`:
11.43 / 2.40 / 1.17 s); the un-instrumented baseline HiGHS `Timing` was 11.90 s.
Whole notebook (65 cells) executes in 51 s wall under nbconvert.

## Table 2: metrics (instrumented re-run)

| case | objective | thermal gens operational/extended | renewable capacity by gen (MW) | wall time (s) | rows / cols / binaries | termination |
|---|---|---|---|---|---|---|
| baseline | 3,168,393.4448 | 3_CT, 10_STEAM, 4_CC, 4_STEAM | 10_PV: 20.8; 2_RTPV: 7.8; 1_HYDRO: 48.5; 4_WIND: 118.5; 10_PV-c: 20.8; 2_RTPV-c: 0.0; 1_HYDRO-c: 48.5; 4_WIND-c: 118.5 | 12.59 | 16175 / 9159 / 3952 | optimal |
| no_invest | 3,767,479.0251 | 3_CT, 10_STEAM, 4_CC, 4_STEAM | 10_PV: 20.8; 2_RTPV: 7.8; 1_HYDRO: 48.5; 4_WIND: 118.5; 10_PV-c: 0.0; 2_RTPV-c: 0.0; 1_HYDRO-c: 0.0; 4_WIND-c: 0.0 | 3.73 | 16174 / 9150 / 3952 | optimal |
| fewer_repr_days | 3,265,990.3818 | 3_CT, 10_STEAM, 4_CC, 4_STEAM | 10_PV: 20.0; 2_RTPV: 7.2; 1_HYDRO: 39.1; 4_WIND: 118.5; 10_PV-c: 20.0; 2_RTPV-c: 0.0; 1_HYDRO-c: 39.1; 4_WIND-c: 118.5 | 1.65 | 8095 / 4599 / 1984 | optimal |

rows / cols / binaries = `build_model_size_report(...).activated`
constraints / variables / binary_variables after `gdp.bigm`. "Renewable capacity"
is the notebook's own cell-40 quantity, `renewableOperational + renewableExtended`.
B&B nodes: 172 / 1 / 1; LP iterations 41,774 / 12,269 / 7,492.

Notes on the numbers (observations, not fixes; see the T2 report):

- `model.thermalGenerators` contains only the four existing thermal units;
  the `Natural Gas_FE` candidate from `cost_data` does not appear as a
  thermal candidate in the 5-bus model.
- For the candidate renewables (`*-c`, not in service) the reported
  `renewableOperational + renewableExtended` equals the existing unit's
  capacity in the baseline (e.g. `10_PV-c` = 20.8 = `10_PV`). In
  `gtep/model_library/gen.py:119-121` an out-of-service renewable gets
  `renewableOperational.set_value(0)` but is not fixed, while
  `renewableExtended` and `renewableRetired` are fixed to 0.
- The size report warns `unassociated_disjuncts: 2704` after Big-M.
