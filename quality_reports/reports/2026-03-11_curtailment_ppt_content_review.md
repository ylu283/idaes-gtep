# Curtailment PPT Content Review (Draft for Slide Update)

Date: 2026-03-11  
Target deck: `quality_reports/decks/2026-03-03_Benchmarking_Update_PCM_vs_Paper.pptx`

## 1. How the Current Prescient Model Realizes Curtailment

### Core message (slide-ready)

- In our current Prescient pipeline, curtailment is realized through **dispatch feasibility + penalty-threshold economics**, not by a single explicit "renewable curtailment penalty" option.
- We tune threshold parameters (`price_threshold`, transmission/interface/contingency/reserve thresholds) that influence how SCED/RUC resolves surplus and congestion.
- Curtailment outcomes are observed directly in result outputs:
  - `renewables_detail.csv` -> `Curtailment`
  - `hourly_summary.csv` -> `RenewablesCurtailment`
- Therefore this is a **curtailment-penalty proxy experiment**: it tests how market-penalty environment changes curtailment and LMP behavior.

### Source traceability

- Runner config and threshold sweep:
  - `gtep/data/retirement_allowed_no_extreme_half_load/run_curtailment_penalty_experiments.py`
- Reported rationale:
  - `quality_reports/reports/curtailment_penalty_experiment_setup_2026-02-28.md`

## 2. Notebook Results and Key Findings (from `prescient_lmp_analysis_curtailment_penalty.ipynb`)

### Common comparison window

- `2019-01-01 00:00:00` to `2019-03-31 23:00:00`

### Metrics table (slide-ready)

| Case | LMP Min | LMP Max | Negative LMP Fraction | Floor-Hit Fraction | Weighted LMP ($/MWh) | Curtailment (MWh) | OverGeneration (MWh) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `penalty_300` | -300 | 382.18 | 9.62% | 1.52% | 9.79 | 118,560.19 | 888,328.44 |
| `penalty_1000` | -1000 | 1273.72 | 10.51% | 1.50% | 3.96 | 124,325.36 | 889,003.40 |
| `penalty_2000` | -2000 | 2549.63 | 11.43% | 1.51% | -7.91 | 125,040.34 | 888,986.03 |
| `penalty_5000` | -5000 | 6373.67 | 11.91% | 1.49% | -39.57 | 121,351.43 | 889,606.53 |
| `penalty_10000` | -10000 | 12749.61 | 12.80% | 1.49% | -88.35 | 123,327.86 | 888,692.76 |

### Key findings (slide-ready)

1. Increasing penalty cap widens LMP tails and increases negative-LMP share.
2. Floor-hit fraction remains near ~1.5% across cases, so clipping artifacts persist.
3. Weighted LMP trends downward strongly with larger caps (`+9.79` -> `-88.35`).
4. Overgeneration remains high and nearly flat (~888-890 GWh), indicating cap tuning alone does not remove surplus conditions.
5. Conclusion: penalty sweep is informative diagnostics, but structural model differences still dominate benchmark gap.

### Source traceability

- Notebook:
  - `gtep/pcm_analysis/prescient_lmp_analysis_curtailment_penalty.ipynb`
- Exported tables:
  - `gtep/pcm_analysis/curtailment_penalty_benchmark_summary.csv`
  - `gtep/pcm_analysis/curtailment_penalty_benchmark_summary.json`
  - `gtep/pcm_analysis/curtailment_penalty_timeseries_wide.csv`

## 3. Corrected Explanation of Paper Pyomo Curtailment Mechanism

### Correct mechanism (slide-ready)

- Paper does not optimize wind/solar as explicit dispatchable market units in SCUC.  
  Wind/solar are first subtracted from load to build net load (`load_b_t`).
- Curtailment variable `rnwcur_b_t` is a nonnegative nodal slack:
  - forced to zero when net load is nonnegative;
  - bounded above by magnitude of negative net load when net load is negative.
- Nodal balance uses:
  - `generation + inflow - outflow = load_b_t/BaseMVA + rnwcur_b_t`
- Objective contains thermal commitment/dispatch costs, but no explicit curtailment cost term.

This means paper curtailment is **net-load balancing relief**, not explicit renewable offer/penalty economics.

### Source traceability

- Standard SCUC:
  - `.../Sample_Codes_SCUC/Run_SCUC_annual.py`
  - `.../Sample_Codes_SCUC/UC_function.py`
- Hourly DLR SCUC:
  - `.../Sample_Codes_SCUC_HourlyDLR/RunUC_annual_dlr.py`
  - `.../Sample_Codes_SCUC_HourlyDLR/UC_function_DLR.py`

## 4. Proposed 3 New Deck Slides (Append-Only)

### Slide 13 title

**How Curtailment Is Realized in Our Prescient Pipeline**

Bullets:
- No standalone "renewable curtailment penalty" switch in current run config.
- Threshold penalties shape SCED/RUC economics and resulting curtailment.
- We observe curtailment in `renewables_detail.csv` and `hourly_summary.csv`.
- This experiment is a curtailment-penalty proxy sensitivity.

### Slide 14 title

**Curtailment Penalty Sweep Results (Jan-Mar overlap)**

Content:
- Use the 5-case metrics table above.
- Highlight trends:
  - higher caps -> wider LMP tails and more negative-LMP share;
  - weighted LMP declines with cap;
  - overgeneration remains high across cases.

### Slide 15 title

**Corrected Paper Curtailment Mechanism vs Our Model**

Left column (Paper):
- net-load construction after wind/solar subtraction.
- bounded slack `rnwcur_b_t` only when net load < 0.
- no explicit curtailment objective term.

Right column (Our Prescient run):
- explicit renewable participation + penalty-threshold economics.
- curtailment emerges from dispatch/constraint economics.
- cap tuning changes tails but does not by itself resolve structural mismatch.
