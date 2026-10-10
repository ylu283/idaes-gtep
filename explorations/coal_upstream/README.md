# coal_upstream: ERCOT 123-bus coal case on upstream 7b84352

Prompt 04 (`admin/prompt/gtep/04-coal-case-on-upstream.md`). Reproduces the May 2026 study design
(3 stages x 4 representative days x 24 h; 1 h / 2 h / 4 h commitment) on upstream, cost data off then on.

- `scripts/run_coal.py`: tutorial call chain + timers, size report, `summary.json`. Writes a patched copy of
  `gtep/data/123_Bus_Coal` to `output/_data/` (two data `fix`es, see `results_coal.md`).
- `scripts/aggregate.py`: 2HR / 4HR pre-aggregation, ported from the fork.
- `crc/`: rsync + env + `qsub` kit for Gurobi 11 on CRC (not submitted).
- `results_coal.md`: run table, pass gate, patch table (committed evidence).
- `output/` (ignored): per-run `summary.json`, `highs.log`, `run.out`, `soln/`.

```bash
PY=/opt/anaconda3/envs/gtep_up/bin/python
$PY explorations/coal_upstream/scripts/run_coal.py --config 1HR --cost-data off \
  --scale-texas-loads off --stages 1 --num-reps 1 --solver highs --mip-rel-gap 0.01 \
  --time-limit 3600 --out explorations/coal_upstream/output/A0
```

Report: `quality_reports/reports/2026-10-10_coal_case_on_upstream.md`.
