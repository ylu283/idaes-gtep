# Project Memory (Lean)

Last updated: 2026-03-11

## Current Focus

- Compare Prescient PCM vs paper SCUC UC pricing behavior.
- Primary discrepancy: Prescient LMP has frequent negatives; paper UC LMP is nonnegative in tested samples.

## Confirmed Findings

- Dataset scale matches across paper and Prescient inputs (123 buses / 255 lines / 292 generators).
- Negative LMP behavior in Prescient is persistent across runs (not hydro-only).
- `-1000` LMP floor events align with current threshold settings.
- Curtailment sweep log `ERCOT_curtailment_penalty_pcm.o269980` failed before solving due to invalid Prescient option key `name` passed from case metadata.
- Curtailment sweep Jan-Mar common-window results now available:
  - negative-LMP fraction increases from `9.62%` (`penalty_300`) to `12.80%` (`penalty_10000`);
  - weighted LMP decreases from `+9.79` to `-88.35` $/MWh;
  - overgeneration remains high and near-flat (~888-890 GWh).
- Paper curtailment interpretation corrected: paper uses bounded net-load slack `rnwcur_b_t` (no direct curtailment objective term), not explicit renewable offer-penalty economics.

## Key Paths

- Baseline b-theta run scripts:
  - `gtep/data/retirement_allowed_no_extreme_half_load/run_coal_prescient_btheta.py`
  - `gtep/data/retirement_allowed_no_extreme_half_load/run_coal_prescient_btheta_uc_only.py`
- Curtailment-penalty experiment runner:
  - `gtep/data/retirement_allowed_no_extreme_half_load/run_curtailment_penalty_experiments.py`
- Experiment submit helper:
  - `gtep/data/retirement_allowed_no_extreme_half_load/submit_job_curtailment_penalty.py`
- Experiment summarizer:
  - `gtep/pcm_analysis/summarize_curtailment_penalty_results.py`

## Current Experiment Convention

- Output root:
  - `gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2/experiments/curtailment_penalty/<mode>/<case>/`
- Analysis sink:
  - `gtep/pcm_analysis/curtailment_penalty_benchmark_summary.csv`

## Debug Update (2026-02-28)

- Fixed sweep runner to sanitize case metadata before calling `Prescient().simulate`.
- Added per-case manifest status/error checkpointing and optional `--continue-on-error`.
- Added summary strict mode and explicit missing-root failure in:
  - `gtep/pcm_analysis/summarize_curtailment_penalty_results.py`

## Reference Reports

- Prescient vs paper UC comparison:
  - `quality_reports/reports/model_comparison_prescient_vs_paper_uc_2026-02-28.md`
- Curtailment-penalty setup and rationale:
  - `quality_reports/reports/curtailment_penalty_experiment_setup_2026-02-28.md`
- Curtailment slide-content review (for updated benchmark deck):
  - `quality_reports/reports/2026-03-11_curtailment_ppt_content_review.md`

## Quality Reports Canonical Paths

- Governance doc:
  - `quality_reports/README.md`
- Latest index:
  - `quality_reports/INDEX.md`
- Final reports:
  - `quality_reports/reports/`
- Deck outputs:
  - `quality_reports/decks/`
- Lab notes:
  - `quality_reports/lab_logs/`

## Next Decision Point

- Decide whether to benchmark with paper-like net-load treatment (remove explicit wind/solar generators and embed into load) after penalty sensitivity results are reviewed.
