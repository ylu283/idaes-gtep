# ERCOT 123-bus coal case on upstream 7b84352: stopped at the A0 smoke run

**Date:** 2026-10-10
**Branch:** `eval/upstream-0930` (worktree `~/Documents/GitHub/idaes-gtep-eval`, upstream `7b84352`)
**Plan of record:** `admin/prompt/gtep/04-coal-case-on-upstream.md` v1 (prompt 01 ground rules)
**Author:** ylu283
**Status:** stopped at A0 under the pass gate. Cause: solver capability, not the model. A1 onward
needs Gurobi on CRC (rsync kit ready, nothing submitted).

| item | value |
|---|---|
| Python / pyomo / highspy / HiGHS | 3.11.17 / 6.10.1 / 1.15.1 / 1.15.1 |
| platform | arm64, macOS 15.5, 14 cores, 48 GB; no gurobipy locally |
| env evidence | `gtep.__file__` = `/Users/yilu/Documents/GitHub/idaes-gtep-eval/gtep/__init__.py` |
| unit tests after the port | 70 passed (225 s) |

## 1. Summary

The coal case now builds on upstream for every planned configuration: 1HR / 2HR / 4HR, cost data off
and on, Texas load scaling off and on. Getting there took two data fixes to a copy of
`123_Bus_Coal` and three ports from the fork. Two upstream defects made the shipped Coal data unusable
on upstream: `gen.csv` fails upstream's own required-column check, and the all-numeric `branch.csv`
crashes Egret's branch reader. Texas load scaling needed the fork's table attachment and its
zone-name labels.

The A0 smoke run (one stage, one 24-h day, 525 k rows) **did not pass**. HiGHS ran for an hour and
never left the root node or found an incumbent. A fixed all-off point solves at 4.767e12, so the
model is feasible and the miss is solver capability. Full A1 is 6.32 M rows, about one fifth of the
fork's 30.7 M. It needs more than 20 GB just to build plus solver copy, past the local rule, so A1 to
C belong on CRC with Gurobi 11, as in May. No result exists yet to compare with May.

## 2. Run table

| run | structure | cost data | Texas scaling | solver | rows / cols / binaries | build / transform / solve s | termination | gap | objective | per-stage retired / extended / installed | load shed per stage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 1HR, 1 x 1 x 24 h | off | off | HiGHS, gap 1e-2, 3600 s | 525,096 / 233,065 / 189,386 | 6.1 / 20.1 / 3600.1 | time limit, no incumbent | inf (dual 5.767e8) | none | n/a | n/a |
| A0-diag | A0, all units fixed off | off | off | HiGHS | 525,096 / 227,068 / 183,389 | 6.1 / 18.6 / 0.9 | HiGHS Optimal (instrument) | 0 % | 4.767e12 | n/a | all load shed |
| A1 | 1HR, 3 x 4 x 24 h | off | off | not solved | 6,316,172 / 2,790,100 / 2,271,815 | 103.0 / 256.8 / - | killed at 28 GB (see §3) | - | - | - | - |
| A2 smoke | 1HR, 3 x 1 x 24 h | off | on | build only | 1,595,564 / 706,780 / 574,055 | 21.7 / 56.0 / - | build OK | - | - | - | - |
| B1 smoke | 1HR, 3 x 1 x 24 h | on | on | build only | 1,595,564 / 706,780 / 574,055 | 24.4 / 55.9 / - | build OK | - | - | - | - |
| C 2HR smoke | 2HR, 3 x 1 x 12 | on | on | build only | 785,276 / 350,740 / 282,275 | 12.5 / 27.0 / - | build OK | - | - | - | - |
| C 4HR smoke | 4HR, 3 x 1 x 6 | on | on | build only | 380,132 / 172,720 / 136,385 | 6.1 / 12.6 / - | build OK | - | - | - | - |

Data load: 1 s without Texas scaling, about 31 s with it (the 48 MB `.xlsb`). Smoke builds confirm
the code paths only; they are not runs under the pass gate.

**Representative days.** `representative_dates=None` selects 2019-01-28, 04-24, 07-06 and 10-15. The
fork used 01-28, 04-23, 07-05 and 10-14: upstream picks by day index and its comment assumes a 2020
calendar. Weights are 91/91/91/92 (`--weights may`). Upstream's default with no weights is 1 per
day (`gtep_data.py:325`), which would shrink the objective about 91×.

**A2 load scaling confirmed.** Total load in the first period of rep day 1: stage 1 = 36.9 GW
(unscaled 34.4 GW), stage 2 = 88.2 GW, stage 3 = 95.0 GW. Existing thermal capacity is 75.9 GW
(128 units, 13 coal = 14.8 GW); candidate CTs add 116 GW. Scaling uses the factor for Jan 1, hour 1
of each stage year for every hour (`.iloc[0]`). The fork did the same.

## 3. Pass-gate checklist

| item | A0 |
|---|---|
| termination optimal, or time limit with gap <= 1 % | **miss** (time limit, no incumbent) |
| objective finite, plausible magnitude vs May | **miss** (none) |
| stage-1 load shed = 0 | not evaluable |
| coal at lifetime Extended or Retired | not evaluable (1 stage) |
| no negative / above-nameplate dispatch | not evaluable |

**Diagnosis (A0).** Presolve reduces A0 to 210,835 rows × 75,450 cols (69,522 binaries). The first
cut round lifts the root bound from 5.87e7 to 5.77e8. HiGHS then spends the full hour in root
separation (753,677 LP iterations, 0 B&B nodes), and none of its heuristics finds a feasible point
(`output/A0/highs.log`).

The model itself is feasible. All units off, candidate CTs disabled and all load shed is a feasible
point by construction. `--diag-fix-all-off` fixes that point, and HiGHS certifies it as Optimal with
zero bound violation at 4.767e12. The miss is solver capability on this formulation:
- big-M coefficients up to 1e7, which HiGHS itself warns about;
- 10-period startup/shutdown logical chains from the uniform 0.1 ramp fraction.

None of the prompt's "What is known" items explains it. May's runs used Gurobi 11, which is the next step.

**A1 locally.** The build-only run reached RSS 10.2 GB and a peak footprint of 21.7 GB after Big-M.
The solving process grew to 28 GB (peak footprint 32.8 GB) while Chrome held about 20 GB and swap was
16.2 of 17.4 GB. I killed it under the prompt's ~20 GB rule; it produced no result.

## 4. Patch table

| file | where | kind | reason | source / upstream issue? |
|---|---|---|---|---|
| copy of `123_Bus_Coal/gen.csv` (written by `run_coal.py`) | QMax/QMin for 289 candidates; `Ramp Rate MW/Min` for 581 rows | fix 1/3 | shipped file fails upstream `validate_required_columns` (`gtep_data.py:753`) | values from upstream 42961c0 (same fix applied to `123_Bus_Resil_Week` only); yes |
| copy of `123_Bus_Coal/branch.csv` (written by `run_coal.py`) | extra text column `Notes` | fix 2/3 | Egret `_read_branches` (`parser.py:448`) uses `iterrows()`; all-numeric rows upcast to float, `KeyError: '98.0'` | yes (Egret or data). Resil_Week escapes only because its candidate UIDs are strings |
| `gtep/gtep_model.py` | `create_stages`, after `b_inv.year` | port | attach `b_inv.load_scaling` when `scale_texas_loads` | fork `gtep_model.py:2481@commitment_period` |
| `gtep/model_library/scaling.py` | `add_load_scaling`, Texas branch | port | read the table via the investment-stage block | fork `gtep_model.py:2035@commitment_period` |
| `scripts/run_coal.py` | after `import_load_scaling` | port | zone columns "1".."8" → COAST..WEST | fork `gtep_data.py:154-155@commitment_period`; upstream changed the labels in 181a307 for Texas_2000 |
| `scripts/aggregate.py` | whole file | port | 2HR/4HR block averaging; min up/down hours → block counts | fork `driver_coal_2hr.py:32-89@commitment_period` |
| `scripts/run_coal.py` | `--diag-fix-all-off`, no-incumbent handling, load printout | instrument | certify feasibility; record a no-incumbent result | n/a |

Fix patches: 2 of 3. No model-formulation fix was ported (Fix 19 / Fix 20 untouched). The shipped
data is unchanged.

## 5. May vs now (data-difference caveat)

| config | May (fork, Gurobi 11, CRC, 293-row gen.csv, no candidates) | now (upstream, 581-row gen.csv with 289 candidates) |
|---|---|---|
| 1HR | 30.7 M rows, 78 min, gap ≤ 2e-6; 128 thermal units operational; 13 coal Extended in stage 3; shed 0 / 2.06 M / 2.82 M MW-periods | 6.32 M rows (built); no solve |
| 2HR | 14.9 M rows, 19 min; 13 coal Extended in stage 3 | about 3.1 M rows (4 × 3-stage, 1-rep smoke build); no solve |
| 4HR | 7.0 M rows, 3 min; 13 coal Extended in stage 2 | about 1.5 M rows (same estimate); no solve |

The upstream model is about 5× smaller at every resolution. Upstream data includes candidate units,
so May's "no installs" is not a comparison target.

## 6. Observations recorded (not patched)

- **min up/down units.** `min_up_time` / `min_down_time` are used as counts of commitment periods
  (`int(...)`, `representative_period.py:208-283`). The ported ceil(h / block) rescaling is the right
  conversion for 2HR/4HR.
- **Ramp rates.** The gen.csv `Ramp Rate MW/Min` column is never used. `load_default_data_settings`
  sets `ramp_up_rate = ramp_down_rate = 0.1` for every generator (`gtep_data.py:584-585`). The logical
  constraints then require ceil(1/0.1) = 10 startup/shutdown periods whatever the period length; in
  4HR that is 40 h, longer than a rep day.
- **Candidate renewables.** Stage-1 `renewableOperational` for candidates is `set_value(0)`, not
  fixed (`gen.py:119-121`), so candidate wind/PV is free capacity. Not reached in a solve here.
- **Uniform thermal costs with cost data.** `repopulate_cost_parameters` assigns NG-CT capex, fixed,
  variable and fuel costs to every thermal unit, coal and nuclear included (`components.py:721-806`).
  `extension_multiplier` = 0 makes extension free, while retirement costs 0.1 × capex. Retirement is
  therefore structurally disfavoured in B1. This is a reading of the code, not a run result.
- **Small defects.** `gtep_data.py:229` slices `[: num_reps + 1]`, so num_reps = 1 returns two dates.
  The pyomo HiGHS wrapper raises `NoFeasibleSolutionError` on an Optimal status when
  `primal_solution_status != 2` (seen on the fully fixed A0-diag).

## 7. Verification

- Unit tests (`$PY -m pytest gtep/tests/unit -q`) after the port: `70 passed, 150 warnings in 225.44s`
- `black --check` clean on `run_coal.py`, `aggregate.py`, `gtep_model.py`, `scaling.py`.
- Fork fingerprints unchanged; nothing pushed (see session log).

## 8. Left for Kay

1. CRC: connect the VPN, rsync (`explorations/coal_upstream/crc/README.md`), set up the env, then
   approve `qsub` for A0 on Gurobi (a one-day check) and A1.
2. Accept the two data fixes and three ports as the baseline, or raise them with Sandia first.
3. Weights 91/91/91/92 instead of upstream's default of 1; auto dates instead of the fork's dates.
4. HiGHS tuning (heuristic effort, presolve options) was not tried, per the stop rule.
5. Expected B1 behaviour from the code: CT installs likely, retirements unlikely (see §6). This is a
   prediction to check, not a result.

## Appendix: questions for the collaborators (reference only, not sent)

1. **Load scaling.** `scaling.py:47-51` reads `b.load_scaling` on the commitment block, but nothing
   attaches it. `import_load_scaling` labels zones "1".."8" (181a307), while the 123-bus loads carry
   zone names. `.iloc[0]` applies the Jan-1 hour-1 factor to every hour of a stage. Which of these is
   intended, and is `scale_texas_loads` still supported for 123-bus?
2. **Coal data.** `123_Bus_Coal/gen.csv` lacks QMax/QMin and ramp values (fixed for Resil_Week in
   42961c0), and its all-numeric `branch.csv` breaks Egret's `iterrows()` parser. Is
   `123_Bus_Coal` maintained, or is `123_Bus_Resil_Week` its successor? `config_123bus_coal.toml`
   hits the same errors.
3. **Aggregation intent.** With `num_commit < 24` on a 24-h day, data are read as
   `values[commitment_period - 1]` (the first hours), not aggregated. Is a coarser commitment meant to
   pre-aggregate, as the fork did?
4. **Candidate-wind variable.** Should stage-1 `renewableOperational` for `-c` units be fixed to 0
   (`gen.py:119-121`)? As written, candidate renewables are free capacity.
5. **min up/down units.** Hours are used as period counts. Is that intended only for 1-h periods?
6. **Ramp units.** gen.csv `Ramp Rate MW/Min` is ignored and overwritten with 0.1 per dispatch
   period, which forces 10-period startup/shutdown windows at any resolution. Intended?
7. **Cost data for thermal units.** All thermal units get NG-CT costs, coal included; extension is
   free while retirement costs 0.1 × capex. Is that the intended economics for a coal-retirement study?
8. **Solver.** Have the authors solved a multi-stage, 24-h 123-bus case on HiGHS? A single stage-day
   found no incumbent in 1 h here. Any recommended settings?
