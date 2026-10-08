# upstream_eval

Evaluation of upstream `IDAES/idaes-gtep` at `7b84352` (PR #190 merge,
2026-09-30) on branch `eval/upstream-0930`. Plan of record: prompt 01
(`admin/prompt/gtep/01-upstream-resync-assessment.md`, v4). Report:
`quality_reports/reports/2026-10-08_pmaps_5bus_tutorial_reproduction.md`.

## Environment (`gtep_up`)

Evidence line (2026-10-08):

```
/Users/yilu/Documents/GitHub/idaes-gtep-eval/gtep/__init__.py
python 3.11.17
highspy 1.15.1 HiGHS 1.15.1 pyomo 6.10.1
egret 0.5.5 prescient 2.2.2
macOS-15.5-arm64-arm-64bit arm64
```

Interpreter: `/opt/anaconda3/envs/gtep_up/bin/python`; kernelspec `gtep_up`.
Full `pip freeze`: `README_pip_freeze.txt`.

## Layout

- `scripts/patch_tutorial_5bus.py` -- nbformat instrumentation of the 5-bus
  tutorial (model size, wall time, per-experiment HiGHS logs, generator status,
  metrics table). Usage: `python patch_tutorial_5bus.py <in.ipynb> <out.ipynb>`.
- `scripts/tutorial_5bus.ipynb` -- the path-patched + instrumented notebook,
  outputs cleared (every patch is visible in the diff against
  `docs/source/tutorials/5bus/tutorial_5bus.ipynb`).
- `results_5bus.md` -- committed copy of the comparison and metrics tables.
- `output/` -- ignored; executed notebooks, `output.log`, `highs_*.log`,
  `soln*/`, `*.html` plots, `metrics_5bus.md` land here.

## Reproduce

```bash
PY=/opt/anaconda3/envs/gtep_up/bin/python
cd explorations/upstream_eval
cp scripts/tutorial_5bus.ipynb output/tutorial_5bus.ipynb
$PY -m jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=1800 --ExecutePreprocessor.kernel_name=gtep_up \
  output/tutorial_5bus.ipynb
```
