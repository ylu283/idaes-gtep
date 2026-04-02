# GTEP Output -> Prescient PCM Data Mapping Specification

Date: 2026-03-24
Target dataset: `gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2`

## 1. Purpose

Define exactly what Prescient files/columns are required, what must come from GTEP expansion outcomes, and how to transform the base dataset consistently for PCM runs.

## 2. Prescient Input Files Required in This Repo Layout

Observed canonical files under `Prescient_2`:

1. Static topology/device files
- `bus.csv`
- `branch.csv`
- `gen.csv`
- `timeseries_pointers.csv`
- `simulation_objects.csv`

2. Time-series files
- `DAY_AHEAD_load.csv`
- `REAL_TIME_load.csv`
- `DAY_AHEAD_wind.csv`
- `REAL_TIME_wind.csv`
- `DAY_AHEAD_solar.csv`
- `REAL_TIME_solar.csv`

## 3. Critical Columns by File (Observed Headers)

### 3.1 `gen.csv`

Critical columns used by Prescient/Egret compatibility and conversion logic:

- `GEN UID`
- `Bus ID`
- `Unit Type`
- `Fuel`
- `PMax MW`
- `PMin MW`
- `Min Down Time Hr`
- `Min Up Time Hr`
- `Ramp Rate MW/Min`
- `Fuel Price $/MMBTU`
- cost-curve columns:
  - `Output_pct_0`, `Output_pct_1`, ...
  - `HR_avg_0`, `HR_incr_1`, `HR_incr_2`, ...
- startup/economic columns used in baseline file:
  - `Start Heat Cold MBTU`, `Start Heat Warm MBTU`, `Start Heat Hot MBTU`
  - `Non Fuel Start Cost $`
  - `C0`, `C1`, `C2`, `Csu`

### 3.2 `bus.csv`

- `Bus ID`
- `Bus Name`
- `BaseKV`
- `Bus Type`
- `Area`
- `Zone`

### 3.3 `branch.csv`

- `UID`
- `From Bus`
- `To Bus`
- `R`
- `X`
- `B`
- `Cont Rating`
- `LTE Rating`
- `STE Rating`

### 3.4 `timeseries_pointers.csv`

- `Simulation`
- `Category`
- `Object`
- `Parameter`
- `Data File`

### 3.5 DA/RT time-series tables

Common structure:
- `Year`, `Month`, `Day`, `Period`, then object-specific columns (bus IDs for load, generator IDs for wind/solar).

## 4. What Must Come From GTEP Outcome

Minimum required data extracted from solved expansion model:

1. `active_thermal_gens: set[str]`
- Final-stage thermal units with active state (operational/installed/extended).

2. `renewable_capacity_mw: dict[str, float]`
- Final-stage renewable capacity by generator ID.

3. `active_branches: set[str]`
- Final-stage active transmission branch IDs.

4. Optional trace metadata (recommended)
- Decision-state source for each asset.
- Stage index used for extraction.
- Any IDs present in solution but absent from base Prescient files.

## 5. Mapping Table: GTEP Decision -> Prescient File/Column

| GTEP outcome element | Source pattern in solution | Prescient target | Transformation |
|---|---|---|---|
| Active thermal generator IDs | `genOperational[...]`, `genInstalled[...]`, `genExtended[...]` indicators in final stage | `gen.csv` (`GEN UID`) | Keep rows with matching IDs; remove inactive thermal rows |
| Renewable final capacity MW | `renewableOperational[...]`, `renewableInstalled[...]`, `renewableExtended[...]` (and retirement/disabled effects as modeled) | `gen.csv` (`PMax MW`) | Update `PMax MW` for matching renewable `GEN UID` |
| Active transmission branches | `branchOperational[...]`, `branchInstalled[...]`, `branchExtended[...]` indicators in final stage | `branch.csv` (`UID`) | Keep matching branch rows |
| Active generator set | Union of active thermal + renewable IDs | `timeseries_pointers.csv` (`Category`,`Object`) | Keep non-generator rows unchanged; for `Category == Generator`, keep `Object` in active set |
| Static network base | Base Prescient files | `bus.csv`, `simulation_objects.csv`, DA/RT profiles | Copy through unchanged unless explicit scenario edit is intended |

## 6. Practical Conversion Workflow (Pseudo-Code)

```text
INPUTS:
  base_dir = .../Prescient_2
  solution = GTEP solution object or dumped json
  out_dir = .../Prescient_2_converted

STEP A: Extract final-stage decisions
  active_thermal = parse binary states from final stage
  renewable_capacity = aggregate renewable MW states at final stage
  active_branches = parse branch binary states from final stage

STEP B: Build generator table
  gen = read base gen.csv
  keep_gen = active_thermal union keys(renewable_capacity)
  gen = gen[GEN UID in keep_gen]
  for g in renewable_capacity:
    gen.loc[GEN UID == g, PMax MW] = renewable_capacity[g]

STEP C: Build branch table
  branch = read base branch.csv
  branch = branch[UID in active_branches]

STEP D: Build pointers
  ptr = read base timeseries_pointers.csv
  ptr = ptr[(Category != "Generator") OR (Object in keep_gen)]

STEP E: Copy-through and write
  copy bus.csv, simulation_objects.csv, DA/RT csv files
  write gen.csv, branch.csv, timeseries_pointers.csv

STEP F: Validate
  - required files present
  - no generator pointer references missing generators
  - all renewable PMax MW values numeric and >= 0
  - all remaining branches reference existing buses

STEP G: Emit manifest
  conversion_manifest.json with counts and warnings
```

## 7. Current Repo Capability Assessment

Existing partial conversion components:
- `gtep/validation.py` provides core filtering/updating utilities.
- `output_to_prescient.ipynb` in scenario folder demonstrates end-to-end notebook workflow.

Gap:
- A single maintained CLI converter script with strict validation and reproducible manifesting is not clearly present as canonical workflow code.

## 8. Data Needed From GTEP Outcome to Run Prescient (Direct Answer)

To run Prescient with a converted expansion scenario, you need this information from GTEP outcome:

1. Which generators survive in final stage (thermal and renewable IDs).
2. What renewable capacities survive in final stage (MW, by generator ID).
3. Which transmission branches survive in final stage.
4. ID consistency mapping from GTEP asset IDs to Prescient CSV IDs (`GEN UID`, `UID`, bus references).
5. (Recommended) Any changed operational parameters if you choose to propagate them (e.g., future fuel/cost assumptions), though current repo conversion utilities primarily adjust membership and renewable `PMax MW`.

Without these fields, you cannot correctly construct `gen.csv`, `branch.csv`, and `timeseries_pointers.csv` for the post-expansion Prescient run.

## 9. Notes on Risks and Common Failure Modes

1. Generator IDs in solution not matching `GEN UID` in `gen.csv`.
2. Pointer rows referencing removed generators after filtering.
3. Renewable `PMax MW` updates with missing or nonnumeric values.
4. Inconsistent branch filtering causing topology disconnects.
5. Notebook-only conversion causing repeatability drift across runs.

## 10. Evidence Paths Reviewed

- `gtep/validation.py`
- `gtep/gtep_model.py`
- `gtep/gtep_solution.py`
- `gtep/gtep_data.py`
- `gtep/data/retirement_allowed_no_extreme_half_load/output_to_prescient.ipynb`
- `gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2/*`
