# GTEP (Without PCM) Explainer and Expansion-to-Prescient Conversion Spec

Date: 2026-03-24

## 1. Your Questions

1. Check how the GTEP model produces expansion planning results.
2. Convert that output into a data format usable by Prescient PCM (and note if conversion is not available in repo).
3. State what data columns/information from GTEP outcomes are required to run Prescient (`gen.csv`, `bus.csv`, etc. in `Prescient_2`).
4. Explain the GTEP model (without PCM) in clear language.

## 2. Short Answer

- The GTEP expansion model is implemented in `gtep/gtep_model.py`, fed by `gtep/gtep_data.py`, and solved by driver scripts like `gtep/driver_coal.py`.
- Expansion results are encoded in solved Pyomo variables/disjunct indicator states, and can be exported through `ExpansionPlanningSolution` (`gtep/gtep_solution.py`) and/or direct variable extraction.
- The repo has partial conversion support in `gtep/validation.py` and notebook workflows (notably `output_to_prescient.ipynb`), but no single robust production converter script with full schema validation.
- For Prescient runs in `gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2`, the minimum practical requirement is: valid network tables (`bus.csv`, `branch.csv`), generator table (`gen.csv`) consistent with selected investment outcomes, and coherent time-series inputs plus pointers (`timeseries_pointers.csv`, DA/RT load/wind/solar files, `simulation_objects.csv`).

## 3. How GTEP Produces Expansion Results (Without PCM)

### 3.1 Data loading and preparation

Code path:
- `ExpansionPlanningData.load_prescient(...)` in `gtep/gtep_data.py`

What it does:
- Loads RTS-GMLC style data via Prescient/Egret provider into an Egret `ModelData` object.
- Populates long-horizon actuals and then slices representative periods (`representative_data`).
- Applies defaults (`load_default_data_settings`) for fields the model expects (lifetime, reserve fractions, cost multipliers, etc.).
- Marks candidate assets (`-c` suffix) as initially out of service.

Plain-language interpretation:
- This stage builds a standardized system model with generators, network, load/time series, and extra planning fields needed by the expansion formulation.

### 3.2 Model structure

Code path:
- `ExpansionPlanningModel.create_model()` in `gtep/gtep_model.py`

Core structure:
- Investment stages (`m.stages`) for planning horizon.
- Representative periods per stage.
- Commitment periods and dispatch periods nested under representative periods.
- GDP disjunctions for asset status logic.

Main investment decision mechanisms:
- Thermal generators: disjunctive states (`genOperational`, `genInstalled`, `genRetired`, `genDisabled`, `genExtended`).
- Transmission branches: analogous state disjunctions when transmission is enabled.
- Renewable assets: continuous MW state variables (`renewableOperational`, `renewableInstalled`, `renewableRetired`, `renewableExtended`, `renewableDisabled`).

### 3.3 Constraints and objective logic

Key modeled components:
- Dispatch-level balance and operating constraints.
- Commitment-level unit logic and transitions.
- Investment-level cost accounting.
- Optional renewable quota and curtailment accounting.

Objective (high level):
- Minimize total cost across stages = investment cost + weighted operating cost + penalty terms (e.g., load shed / curtailment related terms defined in formulation).

### 3.4 Solve and output extraction

Typical run flow:
1. Build model (`create_model`).
2. Apply GDP transforms (e.g., `gdp.bigm` in drivers).
3. Solve with MIP solver.
4. Extract decisions from solution values.

Where results are stored:
- `mod_object.results` after solve.
- `ExpansionPlanningSolution._to_dict()` serializes a tree of primals/expressions (`primals_tree`, `expressions_tree`).

How expansion outcomes are identified:
- Thermal/branch binary disjunct states active in final stage.
- Renewable capacities from summed final-stage renewable state variables.

## 4. Existing Conversion Capability in This Repo

### 4.1 What exists

- `gtep/validation.py` includes reusable functions:
  - `populate_generators(...)`
  - `populate_transmission(...)`
  - `filter_pointers(...)`
  - `clone_timeseries(...)`

These functions already implement core pieces of GTEP -> Prescient dataset adaptation:
- Keep only selected final-stage generators/branches.
- Update renewable `PMax MW` values.
- Filter generator timeseries pointers to active units.
- Copy remaining timeseries/static files.

### 4.2 What is missing

- No single production script that orchestrates full conversion with robust checks, manifesting, and strict failure diagnostics.
- Some conversion workflow is notebook-centric (`output_to_prescient.ipynb`), which is harder to standardize and test for repeated runs.

Conclusion:
- Conversion is partially available, but a polished standalone converter is not yet a clear canonical repo entry point.

## 5. What Information From GTEP Outcomes Is Needed for Prescient Inputs

For your selected canonical target path:
- `gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2`

From GTEP solution outputs, you need at least:

1. Final active thermal generator set
- Derived from final-stage thermal status indicators (`Operational`, `Installed`, `Extended` considered active; retired/disabled excluded).

2. Final renewable capacity per generator (MW)
- Derived from final-stage renewable state variables (typically summed operational + installed + extended, depending on formulation semantics).
- Mapped into Prescient `gen.csv` column `PMax MW` for renewable units.

3. Final active transmission branch set
- Derived from final-stage branch status indicators; used to filter `branch.csv`.

4. Generator identity consistency keys
- GTEP generator names must match Prescient `GEN UID` values used in:
  - `gen.csv`
  - `timeseries_pointers.csv` (`Category == Generator`, `Object` column)
  - time-series file columns referenced by pointers.

5. Optional but strongly recommended metadata for diagnostics
- Per-asset decision provenance (which state triggered inclusion/exclusion).
- Renewable capacity before/after update.
- Counts of dropped generators/branches/pointers.

## 6. Clear-Language Explanation for a Novice

Think of the non-PCM GTEP model as a "planner" that chooses future system build/retire decisions while also enforcing operational realism in representative periods.

- First, it loads a power-system dataset (plants, lines, loads, renewable profiles).
- Then it creates planning choices: keep, add, retire, or extend assets.
- It embeds simplified operations (commitment/dispatch) so planning decisions are evaluated under realistic constraints.
- The solver finds the least-cost plan under those constraints.
- The output is not directly a Prescient run; it is a set of final planning decisions and variable values that must be translated into a Prescient-compatible dataset.

So GTEP answers: "what should the future fleet/network look like?"
Prescient then answers: "how does that fleet operate hour-by-hour in market simulation?"

## 7. Implementation-Ready Pseudo-Code (No Script Yet)

```text
function convert_gtep_solution_to_prescient_dataset(
    base_prescient_dir,
    gtep_solution,
    output_dir
):
    # 1) Parse final-stage decisions
    active_thermal = extract_active_thermal_generators(gtep_solution)
    active_branches = extract_active_branches(gtep_solution)
    renewable_capacity = extract_renewable_capacities(gtep_solution)

    # 2) Load base CSVs
    gen_df = read_csv(base_prescient_dir / "gen.csv")
    branch_df = read_csv(base_prescient_dir / "branch.csv")
    pointers_df = read_csv(base_prescient_dir / "timeseries_pointers.csv")

    # 3) Filter/update generator table
    keep_gen = active_thermal union renewable_capacity.keys()
    gen_df = gen_df where GEN UID in keep_gen
    for each renewable generator r in renewable_capacity:
        set gen_df[PMax MW] for GEN UID == r to renewable_capacity[r]

    # 4) Filter branch table
    branch_df = branch_df where UID in active_branches

    # 5) Filter generator pointers; keep non-generator pointers unchanged
    pointers_df = pointers_df where (
        Category != "Generator" OR Object in keep_gen
    )

    # 6) Copy through remaining required Prescient files
    copy bus.csv, simulation_objects.csv,
         DAY_AHEAD_*.csv, REAL_TIME_*.csv, and other non-overridden files

    # 7) Write outputs
    write gen.csv, branch.csv, timeseries_pointers.csv to output_dir

    # 8) Validate
    assert required files exist
    assert all generator pointers map to surviving generators
    assert renewable PMax values are numeric and nonnegative

    # 9) Emit conversion manifest for audit
    write conversion_manifest.json with counts and warnings
```

## 8. Verification Notes for This Report

Cross-checked local code paths:
- `gtep/gtep_model.py`
- `gtep/gtep_data.py`
- `gtep/gtep_solution.py`
- `gtep/validation.py`
- `gtep/data/retirement_allowed_no_extreme_half_load/output_to_prescient.ipynb`
- `gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2/*.csv`

Quality review checklist applied:
- Domain consistency (power-model semantics)
- Conversion-path feasibility
- Novice readability and terminology consistency
