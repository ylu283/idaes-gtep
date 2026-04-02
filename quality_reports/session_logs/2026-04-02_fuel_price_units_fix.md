# Session Log: 2026-04-02 Fuel Price Units Fix

## Goal
Fact-check the 2035 GTEP→Prescient conversion and fix the critical fuel_cost3 units bug.

## Approach
1. Verify `fuel_cost3` units from `gtep_model.py:1889` (confirmed: USD/(MW·hr) = $/MWh)
2. Back-calculate correct Fuel Price per generator: `FP = fuel_cost3 / (HR_incr_1 × 0.001)`
3. Regenerate gen.csv with correct values
4. Update all documentation

## Key Findings
- **CRITICAL**: `fuel_cost3` is $/MWh, not $/MMBTU. Previous version placed it directly in "Fuel Price $/MMBTU" column.
- COAL Gen 26 MC was $168.77/MWh (should be $18.94) — 8.9× too high
- NUC Gen 1 MC was $121.40/MWh (should be $7.38) — 16.5× too high
- CT Gen 2 MC was $21.15/MWh (should be $22.80) — appeared correct by coincidence (HR≈1000)

## Changes Made
- Fixed Cell 3 of `convert_gtep_to_prescient_2035.ipynb` (back-calculate FP from fuel_cost3)
- Regenerated `Prescient_2_2035/gen.csv` with correct fuel prices
- Updated conversion manifest
- Created `quality_reports/lab_logs/lab_log_2026-04-02.md` (fact-check log)
- Updated `lab_log_2026-04-01.md`, session log, domain review, MEMORY.md

## Verification
All thermal generator MCs now equal their fuel_cost3 target:
- CT: MC = $22.80/MWh (all generators)
- COAL: MC = $18.94/MWh (all generators)
- NUC: MC = $7.38/MWh (all generators)

## GTEP Model Cost Structure (follow-up investigation)

Confirmed that GTEP **does use fuel_cost3 directly** in its expansion planning optimization.
The relevant code is `gtep_model.py:577-578`:

```python
def generatorCost(b, gen):
    return b.thermalGeneration[gen] * i_p.fuelCost[gen]
```

- `thermalGeneration` units: MW·hr (energy)
- `fuelCost` = `fuelCost3` (for stage 3), units: USD/(MW·hr) = $/MWh

GTEP uses a **simplified linear cost model** — one flat marginal cost per generator, no heat rate curve.
This is correct within GTEP's own formulation. The bug was only in the GTEP→Prescient conversion,
where the $/MWh value was placed into Prescient's "Fuel Price $/MMBTU" column without accounting
for the fact that Prescient applies its own `FP × HR × 0.001` cost calculation.
