# Session Log: Report Accuracy Review

Date: 2026-03-11

## Goal

Verify accuracy of all 3 reports in `quality_reports/reports/` against source code. Fix factual errors, add missing context, and correct the summarizer code.

## Review Scope

- 3 reports examined by 2 domain-review agents
- All code quotes verified as exact matches against source files
- Focus: factual accuracy, completeness, consistency with project conventions

## Findings

### Model Comparison Report (`model_comparison_prescient_vs_paper_uc_2026-02-28.md`)

| # | Severity | Finding | Action |
|---|----------|---------|--------|
| M1 | **MAJOR** | Paper uses CONOPT (NLP) for model with Binary variables — solves continuous relaxation, not true MILP | Added Section 3.7, added to Impact Ranking as Rank 5 |
| M2 | MINOR | "rolling 90d/36h" phrasing ambiguous | Reworded Section 3.4 and Rank 3 description |
| M3 | MINOR | DLR `rnwcur_f_1` omits `/BaseMVA` in condition check | Added note after DLR code block |
| M4 | MINOR | Reserve constraint is N-1 adequacy form, not analyzed | Added explanation to Section 3.5 interpretation |
| M5 | MINOR | `formpyomo_UC.py` data generation not examined | Added scope caveat to Section 3 intro |

### Curtailment Experiment Setup Report (`curtailment_penalty_experiment_setup_2026-02-28.md`)

| # | Severity | Finding | Action |
|---|----------|---------|--------|
| C1 | **MAJOR** | Report claims `penalty_1000` preserves baseline — wrong (contingency 10x, reserve 200x, two new thresholds) | Corrected Section 3 with threshold comparison table |
| C2 | **MAJOR** | Summarizer uses RT `LMP` instead of DA `LMP DA` column | Fixed code to use `LMP DA` with fallback; added note in Section 2.2 |
| C3 | MINOR | Summarizer `lmp_mean` uses simple mean, not load-weighted | Added `lmp_load_weighted` to summarizer output; noted in report |

### Curtailment PPT Content Review (`2026-03-11_curtailment_ppt_content_review.md`)

| # | Severity | Finding | Action |
|---|----------|---------|--------|
| P1 | MINOR | Slide 15 title typo "Curtilment" → "Curtailment" | Typo is in `.pptx` deck, not markdown — requires manual PowerPoint fix |

## Files Modified

1. `quality_reports/reports/model_comparison_prescient_vs_paper_uc_2026-02-28.md` — M1-M5
2. `quality_reports/reports/curtailment_penalty_experiment_setup_2026-02-28.md` — C1-C3
3. `gtep/pcm_analysis/summarize_curtailment_penalty_results.py` — C2 (LMP DA column), C3 (load-weighted LMP)

## Additional Fix (from review)

- **Summarizer LMP column validation**: Added column-existence check before the row loop. If neither `"LMP DA"` nor `"LMP"` exists in `bus_detail.csv` headers, the case returns `status="no_lmp_column"` instead of silently producing all-zero LMP data. Also added `"no_lmp_column"` to the `--strict` failure check.

## Open Questions

- M1: Should we verify whether CONOPT was actually used for the final paper results, or was it only in the shared code? (Could be a development artifact.)
- P1: "Curtilment" typo in PowerPoint deck needs manual fix.
- C4 (deferred): `--strict` flag doesn't check manifest `run_status` — partial failures with some output still pass.

## Quality Assessment

- Reports: largely accurate (all code quotes exact matches), but contained 3 major factual issues now corrected
- Code: summarizer had wrong LMP column and lacked load-weighted metric, both fixed
