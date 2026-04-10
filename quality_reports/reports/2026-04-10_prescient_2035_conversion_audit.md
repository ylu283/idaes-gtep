# Audit Report: 2035 PCM Data Conversion Reliability

**Date:** 2026-04-10
**Scope:** Verify the GTEP stage 3 (2035) → Prescient data conversion
**Status:** Conversion is mechanically correct; design limitation documented

---

## 1. File Locations

### Data Inputs

| File | Path (relative to repo root) | Rows | Role |
|------|------------------------------|------|------|
| Prescient_2/gen.csv | `gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2/gen.csv` | 292 | Primary source: correct 4-segment HR, ramp rates, cost curves (2019 baseline) |
| Prescient/gen.csv | `gtep/data/123_Bus_Coal/Prescient/gen.csv` | 374 | Lookup only: `fuel_cost3` column for 2035 fuel projections |
| candidate_generators_initial_list.csv | `gtep/data/123_Bus_Coal/candidate_generators_initial_list.csv` | 127 | Candidate generator parameters (PV, WIND, CT) |
| dispatchable_investments.json | External (dev machine, `DEV_ROOT/retirement_allowed_no_extreme_half_load/`) | — | GTEP thermal investment decisions (binary) |
| renewable_investments.json | Same external location | — | GTEP renewable investment decisions (continuous MW) |

### Data Processing

| File | Path |
|------|------|
| Conversion notebook | `gtep/pcm_analysis/convert_gtep_to_prescient_2035.ipynb` |

### Data Output

| File | Path | Rows |
|------|------|------|
| 2035 gen.csv | `gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2_2035/gen.csv` | 278 |
| All 2035 Prescient files | `gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2_2035/` | — |
| Conversion manifest | `gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2_2035/conversion_manifest.json` | — |

### Run Script

| File | Path |
|------|------|
| 2035 PCM run script | `gtep/data/retirement_allowed_no_extreme_half_load_local/run_coal_prescient_2035.py` |

### Prior Reports & Logs

| File | Path |
|------|------|
| Domain review (Apr 1) | `quality_reports/reports/2026-04-01_gtep_2035_conversion_domain_review.md` |
| Session log (conversion) | `quality_reports/session_logs/2026-04-01_gtep_2035_pcm_conversion.md` |
| Session log (fuel fix) | `quality_reports/session_logs/2026-04-02_fuel_price_units_fix.md` |

---

## 2. Why Prescient/gen.csv Was Used (Instead of Prescient_2 Only)

**`Prescient_2/gen.csv`** (`retirement_allowed_no_extreme_half_load_local/Prescient_2/`, 292 rows) is the file used for the actual 2019 baseline Prescient simulations. It has correct Prescient-format columns: GEN UID, Bus ID, Unit Type, Fuel, PMax, HR_incr_1/2/3, Fuel Price $/MMBTU, Ramp Rate MW/Min, etc. **It does NOT have a `fuel_cost3` column** or any other GTEP economic projection columns.

**`Prescient/gen.csv`** (`123_Bus_Coal/Prescient/`, 374 rows) was created by jkskolf as an intermediate GTEP-to-Prescient file. Its Prescient columns are broken:
- `Fuel Price $/MMBTU` = 1.0 for all generators (not a real fuel price)
- `HR_incr_1` = fuel_cost value (not a real heat rate)
- All ramp rates are NaN
- Missing `C0`, `C1`, `C2`, `Csu`, `BUS ID` columns

However, this file **is the only gen.csv that contains GTEP-specific columns**, including `fuel_cost1`, `fuel_cost2`, `fuel_cost3`, `capex1/2/3`, `var_ops1/2/3`, `fixed_ops1/2/3`.

**The conversion correctly uses both files:**
- `Prescient_2/gen.csv` → all engineering parameters (HR_incr, ramp rates, cost curve segments, Output_pct)
- `Prescient/gen.csv` → only the `fuel_cost3` column (2035 projected marginal cost)

**History:** The initial (broken) version of the notebook used `Prescient/gen.csv` as the primary source for everything (CRITICAL-1 and CRITICAL-2 in the Apr 1 domain review). This was fixed on 2026-04-01 by switching the base to `Prescient_2/gen.csv`.

---

## 3. What fuel_cost3 Is and Why It's Used as Marginal Price

### Definition

`fuel_cost3` is the GTEP model's fuel cost parameter for **investment stage 3 (year 2035)**. Despite the name "fuel_cost", it represents the **total marginal generation cost** in $/MWh, not a raw fuel price in $/MMBTU.

### Evidence (traced through code)

**Step 1 — Data loading** at `gtep_model.py:1873`:
```python
fuelCost3[gen] = m.md.data["elements"]["generator"][gen]["fuel_cost3"]
```
Reads `fuel_cost3` from the generator data (sourced from `Prescient/gen.csv`).

**Step 2 — Pyomo parameter declaration** at `gtep_model.py:1889-1891`:
```python
m.fuelCost3 = Param(
    m.thermalGenerators, initialize=fuelCost3, units=u.USD / (u.MW * u.hr)
)
```
The Pyomo units annotation **`USD/(MW·hr)` = $/MWh** confirms this is a per-MWh cost, not a fuel price.

**Step 3 — Assigned to stage 3 investment block** at `gtep_model.py:1578`:
```python
b.fuelCost = Param(m.generators, initialize=m.fuelCost3)  # investment_stage == 3
```

**Step 4 — Used in the GTEP objective function** at `gtep_model.py:578`:
```python
def generatorCost(b, gen):
    return b.thermalGeneration[gen] * i_p.fuelCost[gen]
```
The GTEP model computes generation cost as: `cost = MW_dispatched × fuelCost ($/MWh)`. It is a **linear cost per MWh** — no heat rate multiplication. The GTEP model does NOT use `Fuel Price × HR_incr`; it uses `fuel_cost3` directly as the marginal cost coefficient.

### Values (uniform per fuel type)

| Fuel Type | fuel_cost3 ($/MWh) | Source |
|-----------|-------------------|--------|
| CT (Gas)  | 22.80128 | `Prescient/gen.csv`, column `fuel_cost3` |
| COAL      | 18.93942 | Same |
| NUC       | 7.378403 | Same |
| PV        | 0.0 | Same |
| WIND      | 0.0 | Same |

Note: `fuel_cost1` (stage 1), `fuel_cost2` (stage 2), and `fuel_cost3` (stage 3) are all present in `Prescient/gen.csv` with 4 unique values each (one per fuel type + renewables).

### Conversion to Prescient format

Prescient computes marginal cost as: `MC = Fuel Price ($/MMBTU) × HR_incr_1 (BTU/kWh) × 0.001`

To make `MC = fuel_cost3`, the notebook back-calculates a per-generator Fuel Price:
```
Fuel Price ($/MMBTU) = fuel_cost3 ($/MWh) / (HR_incr_1 (BTU/kWh) × 0.001)
```

This ensures: `Fuel Price × HR_incr_1 × 0.001 = fuel_cost3` exactly for every generator.

**Bug history:** Before the 2026-04-02 fix (CRITICAL-3), `fuel_cost3` was placed directly in the `Fuel Price $/MMBTU` column without back-calculation. This caused double-counting for generators where HR_incr_1 ≠ 1000, inflating COAL costs 9× and NUC costs 16×.

---

## 4. Uniform MC Design Decision — Impact on Dispatch

### The Issue

Because `fuel_cost3` is the **same for all generators of a given fuel type**, the back-calculation gives every generator of the same type the same first-segment marginal cost. This **erases per-generator efficiency differences** that existed in the 2019 baseline.

### COAL Fleet (12 generators in 2035) — Largest Impact

| Gen UID | PMax (MW) | HR_incr_1 (BTU/kWh) | Fuel Price 2035 ($/MMBTU) | MC_2019 ($/MWh) | MC_2035 ($/MWh) |
|---------|-----------|----------------------|--------------------------|-----------------|-----------------|
| 250     | 410       | 1,388                | 13.646 | **$2.47** | $18.94 |
| 269     | 801       | 3,456                | 5.481 | $6.15 | $18.94 |
| 175     | 852       | 3,803                | 4.980 | $6.77 | $18.94 |
| 232     | 940       | 4,206                | 4.503 | $7.49 | $18.94 |
| 177     | 1,108     | 5,424                | 3.492 | $9.65 | $18.94 |
| 165     | 1,175     | 5,875                | 3.224 | $10.46 | $18.94 |
| 241     | 1,176     | 6,009                | 3.152 | $10.70 | $18.94 |
| 185     | 1,187     | 6,007                | 3.153 | $10.69 | $18.94 |
| 187     | 1,315     | 7,077                | 2.676 | $12.60 | $18.94 |
| 261     | 1,444     | 8,160                | 2.321 | $14.52 | $18.94 |
| 26      | 1,530     | 8,911                | 2.125 | $15.86 | $18.94 |
| 181     | 1,980     | 13,663               | 1.386 | **$24.32** | $18.94 |

**Dispatch impact:**
- In 2019, the coal fleet had a **10× MC spread** ($2.47–$24.32). Efficient plants dispatched first.
- In 2035, all coal plants have **identical MC** ($18.94). Dispatch within the coal fleet is determined by ramp rates and min-up/down-time constraints, not thermal efficiency.
- The least-efficient unit (Gen 181, 1,980 MW, HR=13,663) gets the same marginal cost as the most-efficient (Gen 250, 410 MW, HR=1,388).
- Total coal capacity in 2035: ~14,718 MW across 12 units.

### NUC Fleet (2 generators) — Minor Impact

| Gen UID | PMax (MW) | HR_incr_1 | MC_2019 | MC_2035 |
|---------|-----------|-----------|---------|---------|
| 1       | 2,430     | 16,453    | $13.33  | $7.38   |
| 93      | 2,709     | 18,883    | $15.30  | $7.38   |

Impact is small — only 2 nuclear units, both run baseload. Flattening a $2/MWh difference has minimal dispatch effect.

### CT Fleet (135 generators) — Significant Impact

- 2019 MC range: $0.11–$64.58/MWh (mean $5.59, std $7.91)
- 2035 MC: all exactly $22.80/MWh (std $0.00)
- Within-fleet merit order completely lost
- Higher cost curve segments (HR_incr_2, HR_incr_3) still differ, providing minor differentiation beyond the first segment

### Root Cause

The GTEP model itself uses a single `fuelCost` per fuel type per investment stage (see `gtep_model.py:578`). It does not model per-generator efficiency in its dispatch cost function. The conversion faithfully reproduces what the GTEP model assumed when it made its investment decisions.

### Potential Alternative (Not Implemented)

An efficiency-preserving approach would scale each generator's fuel price proportionally to maintain relative efficiency ordering while matching the fleet-average `fuel_cost3`. For example:
```
FP_2035[gen] = FP_2019[gen] × (fleet_avg_fuel_cost3 / fleet_avg_MC_2019)
```
This would preserve the merit order within each fuel type while shifting the overall cost level to 2035 projections. Whether this is appropriate depends on whether the 2035 PCM should match GTEP's simplification or model more realistic dispatch.

---

## 5. Inherited HR Anomalies (from 2019 Source)

### Finding

28 out of 135 CTs in the 2035 gen.csv have HR_incr_1 < 500 BTU/kWh. Typical CT heat rates are 7,000–12,000 BTU/kWh, so these values are physically impossible.

### Source

These values are **inherited directly** from the 2019 baseline source file:
`gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2/gen.csv`

The conversion copies HR_incr values exactly — all 195 generators common to both files have identical HR_incr_1/2/3 values.

### Examples (worst cases)

| Gen UID | PMax (MW) | HR_incr_1 (BTU/kWh) | Fuel Price 2035 ($/MMBTU) | MC_2035 ($/MWh) |
|---------|-----------|----------------------|--------------------------|-----------------|
| 150     | 10.0      | 47.72                | 477.78 | 22.80 |
| 149     | 10.0      | 58.11                | 392.41 | 22.80 |
| 228     | 10.2      | 54.80                | 416.08 | 22.80 |
| 14      | 22.0      | 54.06                | 421.77 | 22.80 |
| 148     | 13.9      | 67.66                | 337.00 | 22.80 |
| 239     | 15.0      | 54.01                | 422.14 | 22.80 |

### Impact

- Capacity affected: 1,603 MW out of 62,707 MW total CT capacity (**2.6%**)
- The back-calculation produces extreme Fuel Price values ($337–$478/MMBTU) to compensate for the tiny HR, but the MC is still correct ($22.80/MWh) for all segments
- These generators also had wrong MC in the 2019 baseline ($0.11–$0.15/MWh), suggesting the source data was already incorrect
- This is NOT a conversion error — it is a pre-existing data quality issue

---

## 6. Verification Results

### Automated Checks on `Prescient_2_2035/gen.csv`

| Check | Result | Status |
|-------|--------|--------|
| Total generators | 278 (135 CT, 69 WIND, 60 PV, 12 COAL, 2 NUC) | PASS |
| HR_incr preserved from Prescient_2 source | All 195 common generators: identical | PASS |
| HR convexity (HR_incr non-decreasing) | 0 violations across all 149 thermal generators | PASS |
| CT first-segment MC | All 135 = $22.80/MWh | PASS |
| COAL first-segment MC | All 12 = $18.94/MWh | PASS |
| NUC first-segment MC | All 2 = $7.38/MWh | PASS |
| Renewable Output_pct_0 = 0 | All 129 PV+WIND = 0.0 | PASS |
| Bus ID integrity | dtype=int64, no NaN, range 1–120 | PASS |
| Row count | 278 data rows + 1 header = 279 lines | PASS |
| Negative PMax or PMin | None | PASS |

### Sample Generators (Sanity Check)

```
Gen 1  (NUC):  FP=0.44844 × HR=16453.39 × 0.001 = $7.38/MWh   ✓
Gen 2  (CT):   FP=24.5866 × HR=927.39   × 0.001 = $22.80/MWh  ✓
Gen 26 (COAL): FP=2.12541 × HR=8911.0   × 0.001 = $18.94/MWh  ✓
```

### Critical Bug Fixes (All Verified as Applied)

| Bug | Date Fixed | Verification |
|-----|-----------|--------------|
| CRITICAL-1: Wrong source file (Prescient/ used as base) | 2026-04-01 | HR_incr values match Prescient_2, not Prescient |
| CRITICAL-2: 2-segment cost curves from wrong source | 2026-04-01 | All thermals have 4-segment curves (HR_incr_1/2/3 all populated) |
| CRITICAL-3: fuel_cost3 units ($/MWh placed in $/MMBTU column) | 2026-04-02 | MC = FP × HR × 0.001 = fuel_cost3 for all thermals |

---

## 7. Summary

The 2035 PCM data conversion is **mechanically correct**:
- Engineering parameters (HR, ramp rates, cost curve segments) are faithfully preserved from the 2019 baseline (`Prescient_2/gen.csv`)
- The `fuel_cost3` values from `Prescient/gen.csv` are correctly back-calculated into per-generator Fuel Prices
- All three critical bugs from April 1-2 are fixed and verified
- Structural and domain-level validations pass

The main **limitation** is the uniform MC per fuel type, which is a simplification inherited from the GTEP model's cost formulation (`gtep_model.py:578`), not a conversion error. This flattens the within-fleet merit order for all fuel types, with the largest impact on the coal fleet (10× MC spread in 2019 → uniform in 2035).

A secondary concern is 28 CTs with physically impossible HR values inherited from the 2019 source data, affecting 2.6% of CT capacity.

---

## 8. CRITICAL-4 Fix: Corrupted HR_avg_0 / HR_incr (2026-04-10)

### Problem Found

The 2035 Prescient simulation had **zero NUC/COAL dispatch** despite correct MCs. The previous audit (Sections 1-7) verified MC = fuel_cost3 but missed the real issue: PMin commitment cost computed from HR_avg_0.

**Root cause:** `demo_processing_prescient.ipynb` (Cell 21) computed HR values using wrong formulas:
- `HR_avg_0 = Csu × PMax / FP` — a startup cost formula, NOT a heat rate
- `HR_incr = delta_cost / FP` — total segment fuel, NOT per-MW incremental rate

These corrupted values were inherited by the 2035 conversion. Egret parser (`parser.py:574`) uses HR_avg_0 to compute PMin fuel cost: `FP × (HR_avg_0 / 1000) × PMin`. With HR_avg_0 = 3.6M for NUC Gen 1, the PMin cost was **$1.2M/hr** — making nuclear impossible to commit.

### Fix Applied

Added `recompute_hr_from_cost_curve()` to `convert_gtep_to_prescient_2035.ipynb` Cell 3. The function derives proper BTU/kWh heat rates from the quadratic cost coefficients (C0/C1/C2) in `Prescient_2/gen.csv`:

```
C(P) = C0 + C1*P + C2*P^2
HR_avg_0 = C(PMin) / (FP × PMin) × 1000   (BTU/kWh)
HR_incr_i = delta_C / (FP × delta_MW) × 1000  (BTU/kWh)
```

Applied to all thermal generators with valid C0/C1/C2 columns, before the fuel price back-calculation.

### Before/After Comparison

| Metric | NUC (before) | NUC (after) | COAL (before) | COAL (after) |
|--------|-------------|-------------|---------------|--------------|
| HR_avg_0 range | ~3,600,000 | 24,220–24,530 | 35K–309K | 17,409–22,026 |
| PMin cost/hr | $1.2M | $4,490–4,922 | $50K–500K | $3,537–7,266 |
| MC ($/MWh) | $7.38 | $7.38 | $18.94 | $18.94 |

MC is **invariant** — the recomputation only affects HR_avg_0 (PMin cost) and HR_incr (segment slopes), not the first-segment MC which is locked by the fuel price back-calculation.

### Additional Changes

- SCENARIO updated to `retirement_allowed_no_extreme_half_load_local`
- SOLUTION_DIR decoupled from SCENARIO (GTEP solution at non-`_local` dev path)
- Added PMin cost sanity check (warns if any thermal gen > $100K/hr)
- Output regenerated at `_local/Prescient_2_2035/` (278 generators, validation PASSED)

### Verification

| Check | Result |
|-------|--------|
| NUC HR_avg_0 in 5K–50K range | 24,220–24,530 PASS |
| COAL HR_avg_0 in 5K–50K range | 17,409–22,026 PASS |
| NUC PMin cost < $100K/hr | $4,490–4,922 PASS |
| COAL PMin cost < $100K/hr | $3,537–7,266 PASS |
| CT PMin cost < $100K/hr | $84–21,259 PASS |
| MC invariant (CT=$22.80, COAL=$18.94, NUC=$7.38) | All match PASS |
| Notebook validation (0 errors, 0 warnings) | PASS |

### Note on Candidate CTs

22 synthesized candidate CTs (no C0/C1/C2 columns) were skipped by the recomputation and keep their median-based HR_incr values. Their HR_avg_0 was set to 0 by the candidate fill code. Since CT PMin costs were already in normal range, this has no dispatch impact.
