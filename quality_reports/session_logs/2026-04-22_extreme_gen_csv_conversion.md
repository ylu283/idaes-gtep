# Session Log: Extreme Case gen.csv Conversion

**Date:** 2026-04-22
**Branch:** idaes_coal2

## Problem

The extreme case 2035 PCM simulation (`retirement_allowed_extreme_half_load/Prescient_2_2035/`)
was running with the **no-extreme gen.csv** (278 generators). All 11 input data files were
byte-identical between extreme and no-extreme, producing results that differed only by solver
noise (<0.003% on every metric). The "comparison" between scenarios was meaningless.

The extreme GTEP solution (`dispatchable_investments.json` + `renewable_investments.json`)
specifies a **different fleet of 289 generators**.

## Root Cause

During initial setup, gen.csv and all timeseries files were copied directly from the
no-extreme `Prescient_2_2035/` directory without regenerating gen.csv from the extreme
GTEP solution.

## Investigation Findings

| Input | Should differ? | Was different? |
|-------|---------------|---------------|
| Load profiles | No | No (correct — identical to 0.01 MW) |
| Wind profiles | No | No (correct — identical values) |
| Solar profiles | No | No (correct — identical values) |
| Bus/branch network | No | No (correct) |
| **gen.csv (fleet)** | **Yes** | **No — was using no-extreme fleet** |

The "extreme" vs "no-extreme" distinction is the GTEP planning scenario (different
investment/retirement constraints), NOT different load or renewable profiles.

## Conversion

Created `gtep/pcm_analysis/convert_gtep_to_prescient_2035_extreme.py` — adapts the
same pipeline from `convert_gtep_to_prescient_2035.ipynb` with the extreme GTEP solution.

### Extreme vs No-Extreme Fleet Comparison

|  | No-Extreme | Extreme | Delta |
|--|-----------|---------|-------|
| Total generators | 278 | 289 | +11 |
| CT | 135 (62,707 MW) | 138 (63,621 MW) | +3 gens, +914 MW |
| PV | 60 (2,798 MW) | 68 (3,271 MW) | +8 gens, +473 MW |
| WIND | 69 (8,470 MW) | 69 (9,118 MW) | same count, +648 MW |
| COAL | 12 (13,918 MW) | 12 (13,918 MW) | same (all extended) |
| NUC | 2 (5,139 MW) | 2 (5,139 MW) | same |
| **Total** | **278 (93,032 MW)** | **289 (95,067 MW)** | **+11, +2,035 MW** |

Key differences:
- **13 CT candidates at different bus locations** — different investment sites
- **27 generators added, 16 removed** (net +11)
- **65 shared renewables with different PMax** — different MW allocations
  (e.g., pv_31-c: 8.9→73.6 MW, wind_117-c: 156.6→360.5 MW)

### Validation

- MC validation: NUC=$7.38, COAL=$18.94, CT=$22.80 (all match expected)
- All 137 renewable generators have timeseries pointers
- All pointer→timeseries column references valid
- Bus IDs valid, no NaN in critical columns
- 0 errors, 0 warnings

## Files Created/Modified

- `gtep/pcm_analysis/convert_gtep_to_prescient_2035_extreme.py` — conversion script
- `gtep/data/retirement_allowed_extreme_half_load/Prescient_2_2035/gen.csv` — **289 generators** (overwrites old 278-gen copy)
- `gtep/data/retirement_allowed_extreme_half_load/Prescient_2_2035/timeseries_pointers.csv` — 794 rows (filtered to extreme fleet)
- `gtep/data/retirement_allowed_extreme_half_load/Prescient_2_2035/conversion_manifest.json`
- Other files (bus, branch, sim_objects, timeseries CSVs) — overwritten from extreme Prescient_2/ source

## Notebook Updates (completed)

Updated `prescient_lmp_analysis_2035_extreme.ipynb` to match the new 289-gen fleet:
- **Cell 0** (header): 278→289 generators, updated note to reference conversion script
- **Cell 3** (data load): `assert len(gen) == 289`, updated print statement
- **Cell 27** (comparison table): extreme column now shows 289 gens, added Total Capacity row

Updated `run_coal_prescient_2035.py` annotation to reflect corrected gen.csv source.

## Next Steps

1. **Upload corrected `Prescient_2_2035/`** to CRC (gen.csv + timeseries_pointers.csv changed)
2. **Re-run Prescient** via `qsub submit_job_2035.py`
3. **Sync results** back to `Prescient_2_2035/results/`
4. **Re-run the PCM analysis notebook** — notebook is ready, no further code changes needed

## Quality

- Conversion script: verified, all validation checks pass
- Notebook: updated for 289-gen fleet, ready for new results
- Run script: annotation updated
- Existing PCM results in `results/`: **INVALID** — from wrong gen.csv, must be re-run
