# GTEP → PCM Data Pipeline Overview

**Date:** 2026-05-06
**Purpose:** Backup slide material — one-page overview of how GTEP results feed into Prescient PCM simulations.

---

## Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  GTEP (Capacity Expansion Model)                                     │
│  ─────────────────────────────────                                   │
│  Input: 123-bus Texas system (292 generators, 209 branches)          │
│  Solver: Gurobi (MILP via GDP BigM)                                  │
│  Output: Investment decisions for stages 2025 / 2030 / 2035          │
│    • genOperational / genInstalled / genRetired / genExtended        │
│    • renewableOperational (continuous MW capacity)                    │
│    • branchOperational / branchInstalled                             │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Conversion (convert_gtep_to_prescient_2035.ipynb)                    │
│  ──────────────────────────────────────────────────                   │
│  1. Extract final-stage (2035) active fleet from GTEP solution       │
│  2. Filter base gen.csv → keep only active generators (278 of 292)   │
│  3. Update renewable PMax MW from GTEP continuous decisions           │
│  4. Map fuel_cost3 ($/MWh) → Fuel Price ($/MMBTU) via HR curve      │
│  5. Filter branch.csv → keep only active transmission lines          │
│  6. Filter timeseries_pointers.csv → remove retired gen pointers     │
│  7. Copy through: bus.csv, load/wind/solar time series (unchanged)   │
│  8. Emit conversion_manifest.json (audit trail)                      │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Prescient (Production Cost Model)                                    │
│  ──────────────────────────────────                                   │
│  Input: Prescient_2_2035/ directory (278 generators)                 │
│  Solver: Gurobi (LP/MILP for UC + ED)                                │
│  Simulation: 365-day chronological, hourly resolution                │
│  Output: Bus LMPs, generator dispatch, total generation costs        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## What Flows Between Stages

| From | To | Data | Format |
|------|----|------|--------|
| GTEP solution | Conversion | Binary investment states (install/retire/extend) | `dispatchable_investments.json` |
| GTEP solution | Conversion | Continuous renewable MW capacity | `renewable_investments.json` |
| GTEP data | Conversion | 2035 fuel cost projections | `fuel_cost3` column in `123_Bus_Coal/Prescient/gen.csv` |
| Base PCM data | Conversion | Engineering params (HR, ramp, cost curves) | `Prescient_2/gen.csv` (292 rows) |
| Conversion | Prescient | Complete input dataset for 2035 fleet | `Prescient_2_2035/` (gen, branch, bus, timeseries) |
| Prescient | Analysis | Hourly dispatch + prices | `Bus_LMP_*.csv`, `Generator_Dispatch_*.csv` |

---

## Key Conversion Rules

### Generator Filtering (GTEP → Prescient gen.csv)

```
Active fleet = Operational ∪ Installed ∪ Extended
Inactive     = Retired ∪ Disabled

gen.csv rows kept = { g | g ∈ Active fleet at stage 3 }
```

- **Thermal:** binary decision (on/off) — either in gen.csv or not
- **Renewable:** continuous capacity — row kept, `PMax MW` updated to GTEP value

### Cost Curve Translation

GTEP uses a linear cost model: `cost = generation × fuel_cost3` ($/MWh, uniform per fuel type).

Prescient uses piecewise heat rate curves: `cost = Fuel_Price × HR_incr × 0.001` ($/MWh per segment).

Translation: `Fuel_Price = fuel_cost3 / (HR_incr_1 × 0.001)`

| Fuel | fuel_cost3 ($/MWh) | Typical HR_incr_1 (BTU/kWh) | Derived Fuel Price ($/MMBTU) |
|------|-------------------|----------------------------|------------------------------|
| Gas (CT) | 22.80 | ~10,500 | ~2.17 |
| Coal | 18.94 | ~9,200 | ~2.06 |
| Nuclear | 7.38 | ~10,400 | ~0.71 |

### What Stays Unchanged

- Network topology (bus.csv) — no bus additions/removals
- Transmission parameters (R, X, ratings) — only membership changes
- Load time series — identical demand profile for 2035
- Wind/solar capacity factors — same normalized profiles, scaled by new PMax

---

## Validation Checkpoints

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Generator count | `wc -l gen.csv` | 278 + header = 279 lines |
| No orphan pointers | `timeseries_pointers[Object] ⊆ gen[GEN UID]` | Zero orphans |
| Fuel price sanity | `FP × HR × 0.001` for each fuel type | CT: $15-30, Coal: $15-25, NUC: $5-10 |
| HR convexity | `HR_incr_1 ≤ HR_incr_2 ≤ HR_incr_3` | All generators pass |
| Supply adequacy | `Σ PMax > peak_load × 1.15` | 15% reserve margin |
| Renewable PMax | All ≥ 0, matches GTEP investment | Exact match to solution |

---

## Known Limitations

1. **Linear → Piecewise gap:** GTEP assumes uniform MC per fuel type; Prescient uses generator-specific HR curves. This creates a "CEM vs PCM modeling gap" — the focus of the validation study.

2. **No transmission investment propagation:** Current conversion keeps all branches from the base case. GTEP branch investment decisions exist but are disabled (commented out in model).

3. **Static demand:** 2035 Prescient uses the same hourly load profile as the base year, scaled by zone-level growth factors from `load_scaling.xlsx`. No demand elasticity.

4. **5-year stage granularity:** GTEP decides at 5-year intervals. The conversion takes the stage-3 (2035) snapshot — intermediate builds (2025-2030) are not represented.

---

## File Reference

| Artifact | Path |
|----------|------|
| Conversion notebook | `gtep/pcm_analysis/convert_gtep_to_prescient_2035.ipynb` |
| Data mapping spec (detailed) | `quality_reports/reports/2026-03-24_gtep_to_prescient_pcm_data_mapping_spec.md` |
| Conversion audit (2035) | `quality_reports/reports/2026-04-10_prescient_2035_conversion_audit.md` |
| GTEP model explainer | `quality_reports/reports/2026-03-24_gtep_non_pcm_model_explainer_and_conversion_spec.md` |
| 2035 output data | `gtep/data/retirement_allowed_no_extreme_half_load_local/Prescient_2_2035/` |
| PCM run script | `gtep/data/retirement_allowed_no_extreme_half_load_local/run_coal_prescient_2035.py` |
