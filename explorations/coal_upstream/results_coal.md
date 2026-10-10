# Coal case on upstream 7b84352: results (prompt 04)

Machine: arm64 macOS 15.5, 14 cores, 48 GB; Python 3.11.17, pyomo 6.10.1, highspy / HiGHS 1.15.1.
Gurobi: none locally (CRC kit in `crc/`, not submitted). Status 2026-10-10: **stopped at A0** (pass-gate miss, see diagnosis).

## Run table

| run | structure | cost data | Texas scaling | solver | rows / cols / binaries (after Big-M) | build / transform / solve s | termination | gap | objective | per-stage retired / extended / installed | load shed per stage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 1HR, 1 stage x 1 rep x 24 h | off | off | HiGHS 1.15.1, gap 1e-2, 3600 s | 525,096 / 233,065 / 189,386 | 6.1 / 20.1 / 3600.1 | time limit, **no incumbent** (0 B&B nodes) | inf (dual bound 5.767e8) | none | n/a | n/a |
| A0-diag (instrument) | A0 with every thermal unit fixed `genOff`, candidate CTs `genDisabled` | off | off | HiGHS 1.15.1 | 525,096 / 227,068 / 183,389 | 6.1 / 18.6 / 0.9 | HiGHS `Optimal`, 0 bound violation (pyomo wrapper still raised `NoFeasibleSolutionError`) | 0 % | 4.767e12 (all load shed) | n/a | all |
| A1 | 1HR, 3 stages x 4 reps x 24 h | off | off | not solved locally (exceeds ~20 GB rule) | 6,316,172 / 2,790,100 / 2,271,815 | 103.0 / 256.8 / killed | not run: HiGHS process at 28 GB, peak footprint 32.8 GB | n/a | n/a | n/a | n/a |
| A2 / B1 / C2 / C4 | build-only smoke, 3 stages x 1 rep | off / on / on / on | on | none | 1,595,564 / 1,595,564 / 785,276 / 380,132 rows | see report | build OK (no solve) | n/a | n/a | n/a | n/a |

A1 build-only: RSS 10.2 GB after Big-M, peak footprint 21.7 GB, size report + teardown 28 min wall.

Upstream auto-selected dates (`representative_dates=None`): 2019-01-28, 04-24, 07-06, 10-15
(fork: 01-28, 04-23, 07-05, 10-14). Weights 91/91/91/92 (`--weights may`; upstream default is 1 per day).

## Pass gate, A0

| item | result |
|---|---|
| termination optimal, or time limit with gap <= 1 % | **miss**: time limit, no feasible solution found |
| objective finite, plausible magnitude | **miss**: no objective |
| stage-1 load shed = 0 | not evaluable |
| coal units at lifetime Extended or Retired | not evaluable (1 stage; coal lifetime 2) |
| dispatch within [0, nameplate] | not evaluable |

**Diagnosis.** HiGHS presolves A0 to 210,835 rows x 75,450 cols (69,522 binaries), raises the root
bound from 5.87e7 to 5.77e8 in the first cut round, then spends the full hour in root separation
(754 k LP iterations, 0 nodes) without any heuristic finding an incumbent. The model is feasible:
A0-diag fixes a point that is feasible by construction (all units off, candidates disabled, all load
shed) and HiGHS certifies it with zero bound violation at 4.767e12. The miss is therefore solver
capability on this formulation (big-M with 1e7 coefficients, 10-period startup/shutdown logical
chains from the uniform 0.1 ramp fraction), not an infeasible or broken model. None of the "What is
known" items explains it; the May runs used Gurobi 11, which is the next step (CRC, needs Kay's OK).

## Patch table

| file | where | kind | reason | source / upstream issue? |
|---|---|---|---|---|
| copy of `gtep/data/123_Bus_Coal/gen.csv` (written by `run_coal.py`) | QMax/QMin of 289 candidates, `Ramp Rate MW/Min` of 581 rows | fix 1/3 | shipped file fails upstream's own `validate_required_columns` | values from upstream 42961c0 (same fix for `123_Bus_Resil_Week`); yes, Coal data not updated |
| copy of `gtep/data/123_Bus_Coal/branch.csv` (written by `run_coal.py`) | extra text column `Notes` | fix 2/3 | Egret `_read_branches` `iterrows()` upcasts all-numeric rows to float; `KeyError: '98.0'` | yes (Egret parser or data) |
| `gtep/gtep_model.py` | `create_stages`, after `b_inv.year` | port | attach `b_inv.load_scaling` when `scale_texas_loads` | fork `gtep_model.py:2481@commitment_period` |
| `gtep/model_library/scaling.py` | `add_load_scaling`, Texas branch | port | read the table from the investment-stage block | fork `gtep_model.py:2035@commitment_period` (`i_p.load_scaling`) |
| `run_coal.py` (data object) | after `import_load_scaling` | port | rename zone columns "1".."8" -> COAST..WEST (Coal loads carry zone names) | fork `gtep_data.py:154-155@commitment_period` |
| `scripts/aggregate.py` | whole file | port | 2HR / 4HR block averaging + min up/down rescale | fork `driver_coal_2hr.py:32-89@commitment_period` |
| `run_coal.py` | `--diag-fix-all-off` | instrument | certify A0 feasibility | n/a |

No model-formulation fix ported (Fix 19 / Fix 20 untouched).
