# Session log: coal case on upstream 7b84352 (prompt 04)

**Date:** 2026-10-10 · **Branch:** `eval/upstream-0930` (worktree `~/Documents/GitHub/idaes-gtep-eval`)
**Plan of record:** `admin/prompt/gtep/04-coal-case-on-upstream.md` v1 (prompt 01 ground rules apply)

## Post-plan

- Goal: run the May 2026 coal study design (3 stages x 4 rep days x 24 h; 1HR/2HR/4HR) on upstream,
  cost data off then on; report "normal" per the prompt's pass gate; stop at the first abnormal run.
- Approach: `explorations/coal_upstream/scripts/run_coal.py` mirroring the 123-bus tutorial call chain;
  A0 smoke -> A1 -> A2 -> B1 -> C.
- Fork fingerprints at start: status `bd6bef6224c163de1fb3fd517415618f3a7bdbf1`, stash `08b39f418971c27b8df374ef5a5e6516dbcd884a` (match prompt 01).
- Machine: arm64 macOS, 14 cores, 48 GB. gurobipy not installed locally -> HiGHS only.

## Incremental

- Finding 1 (fix #1): shipped `123_Bus_Coal/gen.csv` fails upstream `validate_required_columns`
  (QMax/QMin empty for 289 candidates; `Ramp Rate MW/Min` empty for all 581). Upstream fixed the same gap
  in `123_Bus_Resil_Week` (42961c0: QMax 1, QMin -1, ramp 30). Script writes a patched copy under
  `output/_data/`; shipped data untouched.
- Decision: weights. Upstream `load_prescient(representative_weights=None)` gives weight 1 per date
  (`gtep_data.py:325`); the fork used 91 each. Script default `--weights may` = 91/91/91/92 (sum 365, upstream's rule)
  on the auto-selected dates, so the objective magnitude is comparable to May.
- Observation: `gtep_data.py:229` slices `default_representative_dates[: num_reps + 1]` -> num_reps=1 yields 2 dates
  (model uses only the first, since rep periods = 1..num_reps).
- Observation: upstream overwrites ramp rates to 0.1 (fraction of capacity) for every generator in
  `load_default_data_settings` (`gtep_data.py:584-585`); the gen.csv `Ramp Rate MW/Min` column is never used by the model.
- Observation: `min_up_time` / `min_down_time` are consumed as counts of commitment periods
  (`representative_period.py:208-283`, `int(...)`), so the fork's ceil(h/block) rescaling is the right conversion.
- Finding 2 (fix #2): Egret `_read_branches` (`egret/parsers/rts_gmlc/parser.py:448`) iterates `branch.csv` with
  `iterrows()`; Coal's branch.csv is all-numeric, so rows upcast to float64 and the bus lookup fails
  (`KeyError: '98.0'`). Resil_Week escapes only because its candidate UIDs are strings (`222-c`). Fork shipped the
  same file. Fix in the copy: add a text column `Notes`; all UIDs/values unchanged.
- Upstream auto dates (Coal, 2019): 01-28, 04-24, 07-06, 10-15 (index-based; comment assumes 2020). Fork: 01-28, 04-23, 07-05, 10-14.
- A0 size (1 stage x 1 day x 24 h, Big-M): 525,096 rows / 233,065 cols / 189,386 binaries; build 6.1 s, bigm 20.1 s, RSS 2.15 GB.
- Finding 3 (port, for A2): upstream `import_load_scaling` labels zone columns "1".."8" (181a307, Texas_2000), but Coal
  loads carry zone names (NCENT, COAST, ...). Script renames to the fork's `cap_zones` (same order). Package port:
  `b_inv.load_scaling` attachment (gtep_model.py) + read via investment block (scaling.py).
- Observation: load scaling uses `.iloc[0]` = the Jan-1 hour-1 factor of the stage year for every hour (fork identical).
  2030/2035 factors are large (zone 5 ~6.8x, zone 8 ~6.3x).
- A1 local (informational): build 120.6 s, bigm 280.9 s; HiGHS process reached 28 GB (+ Chrome ~20 GB, swap 16.2/17.4 GB) -> killed per the prompt's ~20 GB rule. A1_build: peak footprint 21.7 GB, RSS 10.2 GB, 6,316,172 rows / 2,790,100 cols / 2,271,815 bin. A1 of record -> CRC (Kay: rsync).
- Kay (10-10): CRC transfer = rsync. crcfe01.crc.nd.edu did not resolve (VPN off) -> CRC kit written, nothing submitted.
- A0 result: HiGHS time limit 3600 s, no incumbent, 0 nodes, dual bound 5.767e8 -> pass-gate miss -> stop.
- A0-diag (instrument `--diag-fix-all-off`): fixed all-off point, HiGHS Optimal 4.767e12, 0 bound viol. -> model feasible; miss = solver capability.
  pyomo HiGHS wrapper raised NoFeasibleSolutionError on that Optimal solve (primal_solution_status != 2 on a fully fixed model).
- Smoke builds (3 stages x 1 rep, build only): A2 / B1 / C2 / C4 all build; Texas scaling confirmed (rep1 first-period load 36.9 / 88.2 / 95.0 GW by stage).
- Unit tests after the port: 70 passed (225 s). black --check clean on touched .py.

## End of session

- Outcome: stopped at A0 per the pass gate; diagnosis = HiGHS capability, model feasible. A1 6.32 M rows (fork 30.7 M) needs CRC Gurobi.
- Patches: fix 2/3 (gen.csv required columns, branch.csv iterrows) in a data copy; ports: load-scaling attachment (package), zone labels, 2HR/4HR aggregation.
- Open: CRC submission (VPN + Kay OK); weights/dates choice; collaborator questions in the report appendix.
- Report: `quality_reports/reports/2026-10-10_coal_case_on_upstream.md`.
