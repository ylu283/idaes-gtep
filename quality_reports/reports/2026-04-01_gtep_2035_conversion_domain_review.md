# Domain Review: GTEP 2035 PCM Data Conversion

**Date:** 2026-04-01
**Reviewer:** Domain Review Agent (automated)
**Notebook:** `gtep/pcm_analysis/convert_gtep_to_prescient_2035.ipynb`
**Output:** `gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2_2035/`

---

## Summary

A domain review was conducted on the GTEP stage 3 (2035) → Prescient PCM data conversion. The initial implementation contained **2 CRITICAL**, **3 MAJOR**, and **3 MINOR** issues. All were fixed and verified before finalizing the conversion.

---

## Findings

### CRITICAL-1: Cost Curve Double-Counting (Fuel Price × HR_incr)

**Severity:** CRITICAL
**Status:** FIXED

**Problem:** The initial notebook used `Prescient/gen.csv` (374 rows, jkskolf's intermediate file) as the base source for existing generators. This file encodes cost curves as `Fuel Price = 1` and `HR_incr_1 = fuel_cost` (i.e., the fuel price is stored in the heat rate column). The conversion then overwrote `Fuel Price` with `fuel_cost3` (2035 projection) without correcting `HR_incr_1`, creating a `fuel_cost²` cost:

```
Egret MC = Fuel Price × HR_incr × 0.001 × ΔMW

BROKEN:  MC = 22.80 × 22.80 × 0.001 = $0.52/MWh  (fuel_cost × fuel_cost)
CORRECT: MC = 22.80 × 927.39 × 0.001 = $21.15/MWh (fuel_cost × heat_rate)
```

**Impact:** All thermal generator marginal costs would be off by 1–2 orders of magnitude, producing nonsensical dispatch and LMPs.

**Fix:** Switched the base source from `Prescient/gen.csv` to `Prescient_2/gen.csv` (292 rows, correct 4-segment cost curves with real heat rates). `Prescient/gen.csv` is now used only for its `fuel_cost3` column.

**Verification:** CT Gen 2 marginal cost = $21.15/MWh (correct range for a gas CT at $22.80/MMBTU fuel).

---

### CRITICAL-2: Wrong Source File for Existing Generators

**Severity:** CRITICAL
**Status:** FIXED

**Problem:** `Prescient/gen.csv` (jkskolf's intermediate) was used as the primary source, but this file:
- Has only 2-segment cost curves (vs. 4-segment in `Prescient_2/gen.csv`)
- Has all ramp rates as NaN
- Lacks `C0`, `C1`, `C2`, `Csu`, `BUS ID` columns
- Was never used for actual Prescient simulations

**Fix:** `Prescient_2/gen.csv` (the file actually used for the 2019 baseline simulations) is now the primary source. It has correct 4-segment cost curves, real ramp rates, and all required columns.

---

### MAJOR-1: Loss of Multi-Segment Cost Curves

**Severity:** MAJOR
**Status:** FIXED (via CRITICAL-2)

**Problem:** Using `Prescient/gen.csv` gave all generators 2-segment (linear) cost curves. The correct 4-segment piecewise-linear curves in `Prescient_2/gen.csv` provide substantially better dispatch accuracy, especially for large coal and nuclear units with nonlinear heat rate curves.

**Fix:** Resolved by switching to `Prescient_2/gen.csv`. All existing generators now retain their original 4-segment cost curves (`HR_incr_1` through `HR_incr_3`, `Output_pct_0` through `Output_pct_3`). Candidate CTs are assigned 3-segment curves using median heat rates from existing CTs:
- `HR_incr_1 = 1360.40`
- `HR_incr_2 = 1381.58`
- `HR_incr_3 = 1402.77`

---

### MAJOR-2: Missing Ramp Rate Data

**Severity:** MAJOR
**Status:** FIXED (via CRITICAL-2)

**Problem:** `Prescient/gen.csv` has NaN for all ramp rate columns (`Ramp Up Rate MW/Min`, `Ramp Down Rate MW/Min`). Without ramp constraints, the dispatch model would allow unrealistic instant power changes.

**Fix:** `Prescient_2/gen.csv` has correct ramp rates for all existing generators. Candidate CTs inherit ramp rates from their synthesis templates (existing CTs of the same type). Renewable generators have NaN ramp rates, which is correct (Prescient treats them as curtailable without ramp limits).

---

### MAJOR-3: Output_pct_0 = 0.6 for Renewable Candidates

**Severity:** MAJOR
**Status:** FIXED

**Problem:** `candidate_generators_initial_list.csv` has `Output_pct_0 = 0.6` for all candidates including PV and WIND. This forces a 60% minimum operating point on renewables, meaning they cannot be curtailed below 60% of PMax — physically incorrect for wind and solar.

**Fix:** Added explicit override: `Output_pct_0 = 0.0` for all renewable generators (PV, WIND) after merging. Verified that all 130 renewable generators (69 WIND + 61 PV) have `Output_pct_0 = 0` in the final gen.csv.

---

### MINOR-1: 2-Digit Year in simulation_objects.csv

**Severity:** MINOR
**Status:** FIXED

**Problem:** The copied `simulation_objects.csv` had dates like `"1/1/35 0:00"` (2-digit year). While some parsers handle this correctly, others may interpret "35" as 1935.

**Fix:** Updated to 4-digit year format: `"1/1/2035 0:00"`.

---

### MINOR-2: Extra Timeseries Columns

**Severity:** MINOR
**Status:** ACCEPTED (no action needed)

**Problem:** The timeseries CSVs (DAY_AHEAD_wind.csv, etc.) contain columns for generators not in the 2035 invested set. Prescient ignores extra columns, so this is cosmetic.

**Recommendation:** No action required. Stripping extra columns would reduce file size but adds conversion complexity for no functional benefit.

---

### MINOR-3: No HYDRO in 2035

**Severity:** MINOR
**Status:** ACCEPTED (expected behavior)

**Problem:** No HYDRO generators appear in the 2035 invested set. The 10 HYDRO generators in `Prescient_2/gen.csv` are not in the GTEP solution for stage 3.

**Assessment:** This is expected — the GTEP model did not invest in or retain HYDRO capacity for 2035 in this scenario. The Prescient HYDRO reporting bug (scalar `p_max` TypeError) is therefore avoided.

---

## Verification Results (Post-Fix)

| Check | Result |
|-------|--------|
| Total generators | 278 (134 CT, 69 WIND, 61 PV, 12 COAL, 2 NUC) |
| Total capacity | 107,164 MW |
| Required files (12) | All present |
| Empty GEN UIDs | 0 |
| Negative PMax/PMin | 0 |
| Orphan timeseries pointers | 0 |
| Thermal Fuel Price > 0 | All pass |
| Thermal HR_incr_1 > 0 | All pass |
| Renewable Output_pct_0 = 0 | All 130 pass |
| CT Gen 2 marginal cost | $21.15/MWh (correct) |
| Bus ID integrity | All gen Bus IDs exist in bus.csv |
| **Overall** | **PASSED** |

---

## Source File Reference

| File | Role | Rows | Key Columns |
|------|------|------|-------------|
| `Prescient_2/gen.csv` | Base for existing generators | 292 | Correct HR, Fuel Price (2019), ramp rates, 4-segment curves |
| `Prescient/gen.csv` | Fuel price lookup only | 374 | `fuel_cost3` column (2035 projections) |
| `candidate_generators_initial_list.csv` | Renewable + CT candidates | 127 | GTEP cost columns, PMax, Bus ID |
| `dispatchable_investments.json` | GTEP thermal solution | — | Binary investment states per stage |
| `renewable_investments.json` | GTEP renewable solution | — | Continuous MW per stage |

---

## Lessons Learned

1. **Always verify cost curve encoding**: `Fuel Price × HR_incr` must give physically reasonable marginal costs. A quick sanity check (expected $/MWh range for fuel type) catches encoding errors that pass structural validation.

2. **Know which gen.csv is which**: The project has multiple gen.csv files with different encodings:
   - `123_Bus_Coal/gen.csv` (581 rows) — original with HR but no fuel_cost3
   - `Prescient/gen.csv` (374 rows) — jkskolf's intermediate with `FP=1, HR=fuel_cost` encoding
   - `Prescient_2/gen.csv` (292 rows) — correct file used for actual simulations

3. **Structural validation is necessary but not sufficient**: Checking `Fuel Price > 0` and `HR_incr > 0` passes even when the values are semantically wrong (fuel price in heat rate column). Domain-aware validation (checking MC ranges) is essential.

4. **Renewable minimum output**: Always verify `Output_pct_0 = 0` for PV/WIND after any merge operation, since candidate templates may have nonzero defaults.
