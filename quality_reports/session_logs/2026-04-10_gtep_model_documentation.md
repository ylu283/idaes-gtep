# Session Log: GTEP Model Documentation & 2035 Conversion Audit

**Date:** 2026-04-10
**Goal:** (1) Audit 2035 PCM conversion reliability, (2) Document the GTEP model structure

---

## Part 1: 2035 Conversion Audit

### Key Findings
- `Prescient_2/gen.csv` (292 rows, correct HR) used as primary source — confirmed via HR_incr match
- `Prescient/gen.csv` (374 rows, broken encoding) used ONLY for `fuel_cost3` lookup — Prescient_2 lacks this column
- `fuel_cost3` traced through `gtep_model.py:1873→1889→1578→578` — units confirmed as $/MWh, used as linear MC in objective
- Back-calculation `FP = fuel_cost3 / (HR_incr_1 × 0.001)` verified correct for all thermal generators
- Uniform MC per fuel type is a GTEP model design choice, not a conversion bug

### Design Decision: Uniform MC
- All CTs: MC=$22.80, all COALs: MC=$18.94, all NUCs: MC=$7.38
- Coal fleet had 10× MC spread in 2019 ($2.47–$24.32) — completely flattened in 2035
- Root cause: GTEP uses single fuelCost per fuel type (line 578)

### Data Quality Issue
- 28 CTs have HR_incr_1 < 500 BTU/kWh (physically impossible) — inherited from Prescient_2 source
- 2.6% of CT capacity affected; MC still correct due to back-calculation

### Deliverable
- `quality_reports/reports/2026-04-10_prescient_2035_conversion_audit.md`

---

## Part 2: GTEP Model Documentation

### Approach
- Read all of `gtep_model.py` (2,326 lines), `gtep_data.py` (192 lines), `config_options.py` (133 lines), `driver_coal.py` (167 lines), `gtep_solution.py` (1,291 lines), `validation.py` (143 lines)
- Documented every Set, Parameter, Variable, Constraint, Expression with line numbers
- Wrote mathematical formulation for all active constraints

### Key Model Observations
1. **MILP/GDP formulation** — uses Pyomo's Generalized Disjunctive Programming for investment and commitment status
2. **4-level nested blocks** — investment stage → representative period → commitment period → dispatch period
3. **Linear cost model** — `cost = generation × fuelCost` (no heat rate curve)
4. **Reserve constraints disabled** — commented out due to infeasibility issues
5. **Renewable quota vacuous** — `ed=0` always, making the quota constraint have no effect
6. **Branch investment costs disabled** — commented out (work in progress)
7. **Dead code at line 579** — varCost addition unreachable (second return after first return)
8. **Hardcoded years** — `[2025, 2030, 2035]` at line 2038

### Deliverables
- `quality_reports/reports/2026-04-10_gtep_model_overview.md` — structure, objective, constraints summary
- `quality_reports/reports/2026-04-10_gtep_model_variables_parameters.md` — complete var/param reference
- `quality_reports/reports/2026-04-10_gtep_model_equations.md` — mathematical formulation
- `quality_reports/reports/2026-04-10_gtep_model_assumptions.md` — assumptions, data flow, limitations
