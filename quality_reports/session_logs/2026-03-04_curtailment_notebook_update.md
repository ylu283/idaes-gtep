# Session Log: Curtailment Penalty Notebook Update

**Date:** 2026-03-04
**Task:** Update `prescient_lmp_analysis_curtailment_penalty.ipynb` with full LMP analysis

## Goal
Expand the 23-cell curtailment penalty notebook to include deep analysis (Parts 2-6) mirroring the reference notebook's Sections 9-10, plus original curtailment-specific analysis.

## What Was Done

### Part 1 Fix (cell 10)
- Fixed FutureWarning in `case_metrics()` by restructuring the groupby/apply to use `include_groups=False`

### Part 2: Data Extraction (cells 23-28)
- Added configuration cell with `SELECTED_PENALTY = 1000`
- Defined helper functions: `_prescient_output_to_df`, `make_lmp_csv`, `make_dispatch_csv`
- Loaded metadata (gen.csv, bus.csv, branch.csv) and built lookup dicts
- Loaded raw Prescient outputs for both curtailment and baseline cases
- Aligned to common time window
- Computed per-bus LMP statistics and system-level comparison

### Part 3: Curtailment Impact (cells 29-35)
- Curtailment by penalty level bar chart
- Curtailment vs overgeneration comparison
- Economic trade-off curve (LMP vs curtailment)
- Curtailment by fuel type and zone
- Curtailment hour-of-day x month heatmap
- LMP distribution comparison (histogram, scatter, timeseries)
- Zone-level LMP improvement map

### Part 4: Negative LMP Investigation (cells 36-46)
- Severity & prevalence stats
- Zone-level negative LMP patterns (side-by-side)
- Temporal heatmaps (baseline, curtailment, difference)
- Overgeneration correlation analysis
- Thermal inflexibility (coal+nuclear fleet)
- Curtailment as safety valve analysis
- Transmission congestion comparison
- Worst bus 4-panel deep dive
- Worst vs best bus comparison

### Part 5: Paper Benchmarking (cells 47-56)
- Generator fleet comparison (Tables I & II)
- Wind production timeseries & daily profile (Figs 3-4)
- Solar profiles (Figs 6-7)
- Quarterly LMP with paper benchmark bands (Fig 10a-d)
- Nodal LMPs normal day (Fig 11)
- Nodal LMPs peak day (Fig 12)
- Congested lines peak day (Fig 13)
- Q1 normal day LMP profile (Fig 14)
- Alignment assessment summary

### Part 6: Summary (cells 57-59)
- Comprehensive findings summary
- Open questions

## Verification
- Valid JSON: Yes
- All 60 code cells parse with no Python syntax errors
- Not yet executed (requires large data files in memory)

## Key Decisions
- Used `SELECTED_PENALTY = 1000` as default (configurable)
- Used `results/` as baseline (same scenario, no curtailment)
- Adapted reference notebook code for 90-day window (Q1 only)
- Paper Fig 14 shows Q1 instead of Q2 (only Q1 data available)
