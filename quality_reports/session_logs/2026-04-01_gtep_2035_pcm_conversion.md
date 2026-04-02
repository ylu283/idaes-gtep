# Session Log: 2026-04-01 GTEP 2035 PCM Conversion

## Goal
Convert GTEP stage 3 (2035) solution to Prescient-compatible PCM input and set up CRC job scripts.

## Approach
- Parse dispatchable/renewable investment JSONs for stage 3
- Merge gen data from 3 sources: Prescient_2/gen.csv (correct cost curves), candidate_generators_initial_list.csv (PV/WIND/CT candidates), and 25 synthesized entries
- Set fuel prices from fuel_cost3 (2035 projection) via Prescient/gen.csv lookup
- Use actual HR_incr values from Prescient_2/gen.csv (NOT the broken Prescient/gen.csv encoding)

## Key Decisions
1. **Base gen source**: `Prescient_2/gen.csv` (292 rows, correct 4-segment cost curves, real ramp rates)
2. **Fuel prices**: `fuel_cost3` column from `Prescient/gen.csv` — Coal $18.94, Gas $22.80, NUC $7.38, Renew $0.00001
3. **Candidate CT HR**: Median from existing CTs in Prescient_2 = HR_incr_1=1360.40, HR_incr_2=1381.58, HR_incr_3=1402.77
4. **25 synthesized generators**: Template-based (copy from same type in Prescient_2, update GEN UID/Bus ID/PMax)
5. **Run config**: PTDF, 30-day test, matching run_coal_prescient.py baseline

## Critical Bug Found and Fixed
**Domain review caught a cost curve double-counting bug** in the initial implementation:
- Initial version used `Prescient/gen.csv` (jkskolf's intermediate) as base
- That file has `Fuel Price=1` and `HR_incr=fuel_cost` encoding
- Setting `Fuel Price = fuel_cost3` without fixing HR_incr created `fuel_cost²` costs
- CT Gen 2: $0.52/MWh (BROKEN) vs $21.15/MWh (CORRECT)
- **Fix**: Switched base to `Prescient_2/gen.csv` (correct curves), use `Prescient/gen.csv` only for fuel_cost3 lookup

Additional fixes from domain review:
- `Output_pct_0 = 0.0` for all renewables (was 0.6 from candidate template)
- 4-digit year in simulation_objects.csv (was 2-digit)
- 4-segment cost curves preserved (was lost with 2-segment source)
- Ramp rates preserved (was all NaN with wrong source)

## Issues Encountered
- Prescient/gen.csv `Fuel Price` column is int64 — needed explicit float cast
- Prescient/gen.csv lacks C0/C1/C2/Csu/BUS ID columns — not needed since using Prescient_2 as base
- 62 candidate renewables not in any gen.csv — added from candidate_generators_initial_list.csv
- 25 generators not in ANY gen.csv (multi-unit CTs and some pv/wind candidates) — synthesized from templates

## Results
- 278 generators: 135 CT, 69 WIND, 60 PV, 12 COAL, 2 NUC
- Total capacity: ~107 GW
- Validation: PASSED (0 errors, 0 warnings)
- CT Gen 2 marginal cost: $21.15/MWh (verified correct)
- All renewables: Output_pct_0 = 0 (verified)
- All files created in Prescient_2_2035/

## Deliverables
- `gtep/pcm_analysis/convert_gtep_to_prescient_2035.ipynb` — conversion notebook (fixed)
- `gtep/data/.../Prescient_2_2035/` — 12 output files + manifest
- `gtep/data/.../run_coal_prescient_2035.py` — Prescient run script
- `gtep/data/.../submit_job_2035.py` — CRC submit script
- `quality_reports/reports/2026-04-01_gtep_2035_conversion_domain_review.md` — domain review report
- `quality_reports/lab_logs/lab_log_2026-04-01.md` — lab log (updated with fixes)

## Lessons Learned
- [LEARN:conversion] Always sanity-check `Fuel Price × HR_incr` gives reasonable $/MWh. Structural validation (>0) is not enough.
- [LEARN:conversion] `Prescient/gen.csv` is jkskolf's intermediate with broken encoding. `Prescient_2/gen.csv` is the correct source for existing generators.
- [LEARN:conversion] `Output_pct_0` must be explicitly set to 0 for renewables after any merge with candidate templates.

## Update (2026-04-02): Fuel Price Units Bug Fix

Fact-check revealed `fuel_cost3` is $/MWh (not $/MMBTU). Previous version placed it directly in "Fuel Price $/MMBTU",
inflating COAL costs 9× and NUC 16×. Fixed by back-calculating `FP = fuel_cost3 / (HR_incr_1 × 0.001)`.
See `quality_reports/lab_logs/lab_log_2026-04-02.md` for details.

## Next Steps
- Upload corrected data to CRC and run 30-day test
- Check for solver errors (especially with synthesized generators)
- If clean, extend to 90/365-day run
