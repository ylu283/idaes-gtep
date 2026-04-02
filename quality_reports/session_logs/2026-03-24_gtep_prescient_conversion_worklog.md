# Session Log: GTEP Expansion Output and Prescient Conversion Audit

Date: 2026-03-24

## Goal

Answer and document:
1. How the GTEP model (without PCM) produces expansion planning results.
2. What conversion path exists from GTEP outcomes to Prescient PCM input format.
3. What exact data from GTEP outcomes is required to run Prescient (`gen.csv`, `bus.csv`, etc.).

## Scope and Path Focus

Canonical data path used for this session:
- `gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2`

Deliverable style used:
- Documentation + implementation-ready pseudo-code (no new converter script in this session).

## Work Performed

1. Inspected non-PCM GTEP model architecture:
- `gtep/gtep_data.py`
- `gtep/gtep_model.py`
- `gtep/gtep_solution.py`
- `gtep/driver_coal.py`

2. Inspected existing conversion-related utilities and workflows:
- `gtep/validation.py`
- `gtep/data/retirement_allowed_no_extreme_half_load/output_to_prescient.ipynb`

3. Inspected current Prescient input schema from actual files:
- `bus.csv`, `branch.csv`, `gen.csv`, `timeseries_pointers.csv`, `simulation_objects.csv`
- DA/RT load/wind/solar CSVs

4. Produced two report artifacts in `quality_reports/reports/`:
- `2026-03-24_gtep_non_pcm_model_explainer_and_conversion_spec.md`
- `2026-03-24_gtep_to_prescient_pcm_data_mapping_spec.md`

## Findings Summary

1. GTEP expansion outcomes are encoded in final-stage disjunct states (thermal/transmission) and renewable MW state variables.
2. Repo contains partial conversion logic and notebook workflows, but no clearly canonical production converter script with strong validation and manifesting.
3. Minimum required outcome fields for Prescient conversion are:
- active generator IDs,
- final renewable capacities by generator ID,
- active branch IDs,
- ID consistency with Prescient CSV keys (`GEN UID`, `UID`, bus references).

## Quality Notes

Review checklist applied in drafting:
- domain consistency,
- mapping correctness,
- reproducibility emphasis,
- novice-readable explanation.

No code/model equations were changed in this session; this was documentation and specification work only.
