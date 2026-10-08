# Session log: PMAPS 5-bus tutorial reproduction on upstream 7b84352

**Date:** 2026-10-08
**Branch:** `eval/upstream-0930` (worktree `~/Documents/GitHub/idaes-gtep-eval`)
**Plan of record:** `admin/prompt/gtep/01-upstream-resync-assessment.md` (v4), pre-approved.

## Post-plan log

**Goal.** Stand up an eval worktree on upstream `7b84352` (PR #190 merge), build a
clean `gtep_up` env with the worktree installed editable, run the unit test gate,
and reproduce the PMAPS 2026 5-bus tutorial notebook
(`docs/source/tutorials/5bus/tutorial_5bus.ipynb`, PR #155) under HiGHS. Pass gate:
all three objectives (baseline, no-invest, fewer-rep-days) `optimal` and within
2e-4 relative of the stored outputs. Then instrument (model size, wall time,
per-experiment HiGHS logs, generator status) only if the pass gate holds.

**Approach.** Worktree, never a checkout in the dirty fork. Two seed commits
(`chore:` gitignore first so `.claude/`, `CLAUDE.md` never get tracked; `eval:`
conventions carried from `commitment_period`). Notebook patches live only in the
exploration copy; package patches as separate `eval:` commits; no fork fixes ported.

**Rationale.** Kay (10-07): June baseline was unconvincing and solved too fast;
Sandia collaborators pointed at data PR #152, tutorial PR #155, and the PMAPS
tutorial. Mechanical first step before the 123-bus re-run proposal (prompts 02/03).

**Key context.**
- Fork fingerprints at start: status `bd6bef6224c163de1fb3fd517415618f3a7bdbf1`,
  stash `08b39f418971c27b8df374ef5a5e6516dbcd884a` (both match the prompt).
- Upstream `.gitignore` ignores `*.json *.csv *.log *.html *.png`, so solver logs,
  solution JSON and plots can never be committed; `results_5bus.md` carries the tables.
- `num_commit=6, duration=6` means hours 00:00-06:00 of each rep day, not a
  compressed day.

## Incremental log

- 10-08 Worktree created at `7b84352`; branch `eval/upstream-0930`. Commits
  `1c4a794` (chore: gitignore) and `c4a9373` (eval: conventions). `.claude/` copied
  from the fork, `Bash(git push*)` added to the deny list, worktree `CLAUDE.md` written.
- 10-08 Choice: Python 3.11 for `gtep_up` (prompt allows 3.10-3.14; 3.11 is the
  safest for the pinned Pyomo/Egret/Prescient stack).
- 10-08 Env evidence: `gtep.__file__` = `/Users/yilu/Documents/GitHub/idaes-gtep-eval/gtep/__init__.py`;
  Python 3.11.17, highspy 1.15.1, HiGHS 1.15.1, pyomo 6.10.1, egret 0.5.5, prescient 2.2.2, arm64.
- 10-08 Test gate: `70 passed, 150 warnings in 245.86s (0:04:05)`; exit 0; tree clean afterwards.
- 10-08 Patch #1 (`fix`): path sed on the exploration copy, 19 occurrences, 0 left at four levels.
- 10-08 Baseline nbconvert run: 0 errors, 51 s wall. Objectives 3168393.4448161027 /
  3767479.025134868 / 3265990.381766974 vs stored 3168393.4448128548 / 3767479.0251299744 /
  3265990.3817659924; rel diffs 1.0e-12 / 1.3e-12 / 3.0e-13; all `optimal`, HiGHS gap 0%. **Pass.**
  `mip_rel_gap=1e-6` re-solve not triggered.
- 10-08 Decision: step 4 instrumentation goes ahead. Script locates cells by source signature and
  asserts the shipped index, so an upstream reorder fails loudly. Metrics dict + markdown table
  written by the notebook itself (`metrics_5bus.md`, ignored dir) and copied into `results_5bus.md`.
- 10-08 Problem: `nbconvert --clear-output` forces in-place and ignores `--output-dir`. Solved by
  having the patch script clear outputs and `cp` the result into `scripts/`.
- 10-08 Instrumented run: 0 errors, objectives bitwise identical to the baseline run. Wall
  12.59 / 3.73 / 1.65 s; rows/cols/binaries 16175/9159/3952, 16174/9150/3952, 8095/4599/1984.
- 10-08 Observation (not fixed): candidate renewables show `renewableOperational` equal to the
  existing unit's capacity in the baseline (`gen.py` sets it with `set_value`, does not fix it).
  Logged for prompt 02. No thermal candidates reach the 5-bus model. Size report warns
  `unassociated_disjuncts: 2704`.
- 10-08 Upstream restructure noted: model logic now lives in `gtep/model_library/`.

## End-of-session summary

- **Outcome.** T2 complete. Pass gate met (3/3 optimal, rel diff ~1e-12). 70/70 unit tests green.
  One `fix` patch (path), zero package patches, no fork fixes ported. Instrumentation done and
  committed (`scripts/patch_tutorial_5bus.py`, `scripts/tutorial_5bus.ipynb`, executed copy).
- **Report.** `quality_reports/reports/2026-10-08_pmaps_5bus_tutorial_reproduction.md`; tables
  also in `explorations/upstream_eval/results_5bus.md`; INDEX row added.
- **Open questions.** Loose stage-1 `renewableOperational` for `*-c` renewables; intended meaning of
  `num_commit=6, duration=6` (hours 00:00-06:00); none of this bears on the pass gate.
- **Blockers.** None. Nothing pushed; `eval/upstream-0930` is local only.
- **Quality.** Quality-gate scoring is off for this branch per the worktree `CLAUDE.md`;
  `check_structure.py` passes; `black --check` clean on the one `.py` touched.
