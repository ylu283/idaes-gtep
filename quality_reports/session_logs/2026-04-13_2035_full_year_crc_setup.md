# Session Log: 2035 Full-Year CRC Run Setup

**Date:** 2026-04-13
**Branch:** idaes_coal2
**Goal:** Configure 365-day full-year Prescient simulation for 2035 GTEP solution

## Context

The 30-day sanity check (January 2035) confirmed the HR_avg_0 fix works:
- NUC dispatches at 88% CF (was ZERO with broken HR)
- COAL at 49.5% CF
- LMP dropped from $30.48 to $21.73/MWh
- All MC validations pass (NUC $7.38, COAL $18.94, CT $22.80)

## Changes Made

### 1. Run script (`run_coal_prescient_2035.py`)
- `num_days`: 30 → 365
- `output_directory`: `Prescient_2_2035/results_30` → `Prescient_2_2035/results`
- Comment updated to "365-day full-year run"

### 2. Analysis notebook (`prescient_lmp_analysis_2035.ipynb`)
- **Cell 0**: Title changed to "Full-Year PCM Analysis", period updated to 365 days / 8760 hours
- **Cell 1**: `RESULTS_DIR` → `results` (from `results_30`)
- **Cell 3**: `N_DAYS = 365`, `N_HOURS = 8760`
- **Cell 12**: Added quarterly generation breakdown (Q1-Q4), kept monthly
- **Cell 13**: Monthly x-axis ticks (was weekly)
- **Cell 15**: All 12 monthly bar labels, quarterly boxplot in panel 4, quarterly LMP stats
- **Cell 16-17**: 4-panel quarterly weekday/weekend hourly LMP profiles
- **Cell 25**: Monthly x-axis ticks for demand plot
- **Cell 27**: Comparison label updated to "365 days (full year)"
- **Cell 29**: Bimonthly x-axis ticks for runtime plots
- **Cell 30**: Full-year findings template (replaces sanity-check checklist)

## Verification Results (365-day run)

Full-year simulation completed on CRC. All checks pass.

| Check | Result | Details |
|-------|--------|---------|
| Dimensions | PASS | 8,760 hours, 365 days, 278 gens, 123 buses |
| NUC CF > 80% | PASS | 88.5% (39.85 TWh, both units ran 8,760 hrs) |
| COAL dispatching | PASS | CF 49.3% (60.06 TWh) |
| MC validation | PASS | NUC $7.3–7.8, COAL $15.9–17.3, CT $22.80 |
| LMP < $25/MWh | PASS | Load-weighted mean $21.50/MWh |
| Reliability | PASS | Zero load shedding, zero curtailment, zero reserve shortfall |

### Notable Findings
- Fleet: NUC(2, 5139 MW) + COAL(12, 13918 MW) + CT(135, 62707 MW) + PV(60, 2798 MW) + WIND(69, 8470 MW) = 278 gens, 93032 MW. No HYDRO in 2035.
- CT provides 28.9% generation share despite only 12.6% CF (huge installed base: 62.7 GW)
- 94/123 buses saw at least one hour below −$100/MWh LMP (congestion-driven)
- Two buses (Houston 46, Wadsworth 2) stuck near $9.69/MWh (congested behind NUC)
- Compared to 2019 baseline: LMP $24.73 → $21.50 (−13%), renewables 27.5% → 29.2%

### Notebook Updates
- Cell 27: Replaced `'TBD'` with dynamic CF computation (`Active (88% CF)`, `Active (49% CF)`)
- Cell 30: Filled in all findings with verified numbers

## Next Steps

1. ~~Upload updated `run_coal_prescient_2035.py` to CRC~~ DONE
2. ~~Submit via `qsub submit_job_2035.py`~~ DONE
3. ~~After completion, download results to `_local/Prescient_2_2035/results/`~~ DONE
4. ~~Execute notebook and fill in findings template~~ DONE
