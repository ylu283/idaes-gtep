# Model Update + Curtailment Slide Content Review

Date: 2026-03-11  
Deck target: `quality_reports/decks/2026-03-11_Model_Update_and_Curtailment_DeepDive.pptx`

## Scope

This note captures the slide-ready content and key metrics for a 10-slide technical update based on:

- `quality_reports/reports/model_comparison_prescient_vs_paper_uc_2026-02-28.md`
- `quality_reports/reports/curtailment_penalty_experiment_setup_2026-02-28.md`
- `gtep/pcm_analysis/curtailment_penalty_benchmark_summary.csv`
- `gtep/pcm_analysis/curtailment_penalty_benchmark_summary.json`
- `gtep/pcm_analysis/prescient_lmp_analysis_curtailment_penalty.ipynb`

## Key Quantitative Inputs

Common comparison window:
- `2019-01-01 00:00:00` to `2019-03-31 23:00:00`

Curtailment benchmark summary:

| Case | Penalty | Neg LMP % | Floor-hit % | Weighted LMP | Curtailment MWh | OverGen MWh |
|---|---:|---:|---:|---:|---:|---:|
| `penalty_300` | 300 | 9.62% | 1.52% | 9.79 | 118,560 | 888,328 |
| `penalty_1000` | 1000 | 10.51% | 1.50% | 3.96 | 124,325 | 889,003 |
| `penalty_2000` | 2000 | 11.43% | 1.51% | -7.91 | 125,040 | 888,986 |
| `penalty_5000` | 5000 | 11.91% | 1.49% | -39.57 | 121,351 | 889,607 |
| `penalty_10000` | 10000 | 12.80% | 1.49% | -88.35 | 123,328 | 888,693 |

## Slide-by-Slide Messages

1. **Title + purpose**
- Establish deep-dive objective: model update + curtailment evidence integration.

2. **What changed**
- Accuracy-review corrections now reflected in model and curtailment narratives.

3. **Top-impact model differences**
- Structural mismatch remains dominant.

4. **Paper curtailment mechanism (corrected)**
- Bounded net-load slack, no direct curtailment objective cost term.

5. **Our Prescient curtailment realization**
- Threshold-proxy economics in SCED/RUC.

6. **Sweep setup caveat**
- `penalty_1000` is not 1:1 historical baseline.

7. **Results table**
- All core curtailment metrics side-by-side.

8. **Trend interpretation**
- Negative-LMP share increases with cap; weighted LMP declines; overgeneration stays high.

9. **Benchmark implication**
- Cap tuning is diagnostic, not a structural fix.

10. **Action plan**
- Prioritize structural alignment experiments.

## Review Notes

- Terminology standardized:
  - “curtailment proxy”
  - “DA-first LMP (`LMP DA`)”
  - “load-weighted LMP”
  - “bounded net-load slack”
- Slide metrics are sourced from current summary files and should be revalidated after each rerun.
