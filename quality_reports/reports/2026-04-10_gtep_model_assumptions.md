# GTEP Model: Assumptions, Data Flow, and Limitations

**Date:** 2026-04-10
**Source:** `gtep/gtep_model.py`, `gtep/gtep_data.py`, `gtep/config_options.py`, `gtep/driver_coal.py`

---

## 1. Cost Model Assumptions

### 1.1 Linear Marginal Cost (No Heat Rate Curve)

The GTEP model uses a **single linear cost** per generator:

```
generatorCost = thermalGeneration × fuelCost    (line 578)
```

There is **no piecewise heat rate curve** — no `HR_incr_1/2/3`, no `Output_pct` breakpoints. The `fuelCost` parameter is a flat $/MWh value representing the total marginal generation cost.

**Implication:** The cost curve is a straight line through the origin. There is no increasing marginal cost at higher output levels. This is a simplification versus the 4-segment piecewise curves used in the Prescient PCM simulations.

### 1.2 Uniform Fuel Cost Per Fuel Type

All generators of the same fuel type share the **same** `fuelCost` at each stage:

| Stage | CT ($/MWh) | COAL ($/MWh) | NUC ($/MWh) |
|-------|-----------|-------------|-------------|
| 1 (2025) | fuel_cost1 | fuel_cost1 | fuel_cost1 |
| 2 (2030) | fuel_cost2 | fuel_cost2 | fuel_cost2 |
| 3 (2035) | fuel_cost3 | fuel_cost3 | fuel_cost3 |

Source: `Prescient/gen.csv` columns `fuel_cost1/2/3`. For stage 3: CT=$22.80, COAL=$18.94, NUC=$7.38.

**Implication:** The model cannot distinguish between an efficient and an inefficient coal plant — they have identical marginal costs. Investment and retirement decisions are driven by capacity, fixed costs, and investment costs, not efficiency.

### 1.3 Variable O&M Cost Not Active

Line 579 contains dead code that would add `varCost` to the generation cost, but it is unreachable (after an earlier `return` on line 578). Variable O&M is loaded from data (`var_ops1/2/3`) but never used in the objective.

### 1.4 Curtailment and Load Shed Penalties

| Penalty | Value | Source |
|---------|-------|--------|
| Curtailment cost | `2 × max(fuelCost)` | Line 1924 |
| Load shedding cost | $5,000/MWh | Line 1928 |
| Deficit penalty | $1/MWh (placeholder) | Line 1856 |

Curtailment cost scales with the highest fuel cost in the system, making curtailment roughly 2× the most expensive generator.

### 1.5 Fixed Cost Scaling

Fixed O&M costs use a scaling factor of `1000 / (5 × 8760)` (line 1053). This converts an annualized $/kW-yr cost to a $/MW-hr cost, assuming 5-year investment periods and 8760 hours per year.

### 1.6 Investment Cost Multipliers

| Multiplier | Thermal | Renewable | Source |
|-----------|---------|-----------|--------|
| Capital (`capitalMultiplier`) | From data | From data | Line 1955 |
| Extension (`extensionMultiplier`) | **0.06** (Texas override) | **0.06** | Line 1965 |
| Retirement (`retirementMultiplier`) | 0.1 | 1.0 | Line 1967 |

Extension cost is 6% of capital cost (hardcoded for the Texas case). Retirement cost is 10% of capital for thermal, 100% for renewable.

---

## 2. Temporal Representation Assumptions

### 2.1 Representative Days

The model uses 3–5 **representative days** (seasonal) to represent a full year. Each representative period is weighted to scale up to the annual total.

**Default weight:** `5 × 365 / 4 ≈ 456.25` (line 1849). This means each representative day represents roughly 456 hours of operation per year.

**Implication:** Extreme events (peak demand days, low-wind periods) may not be captured if not included in the representative set. The representative day selection is done in `gtep_data.py:load_prescient()` using fixed seasonal dates.

### 2.2 No Chronological Linking Between Representative Periods

Each representative period is treated **independently** — there is no state carry-over (e.g., storage charge level, commitment status) between representative days.

### 2.3 Hardcoded Planning Years

Investment stages are hardcoded as `[2025, 2030, 2035]` (line 2038). This is not parameterized.

### 2.4 Default Temporal Resolution

| Level | Default | Meaning |
|-------|---------|---------|
| Representative periods | 3 per stage | 3 seasonal days |
| Commitment periods | 24 per rep period | Hourly UC decisions |
| Dispatch periods | 4 per commitment | 15-min dispatch intervals |

For the coal case study (`driver_coal.py`), the actual settings vary by run but typical values are `num_reps=4, len_reps=24, num_commit=24, num_dispatch=1`.

---

## 3. Network Assumptions

### 3.1 DC Power Flow Approximation

The model uses DC optimal power flow (DC-OPF), which assumes:
- Voltage magnitudes are 1.0 p.u. at all buses
- Angle differences are small (bounded to ±π/6)
- Reactive power and losses are neglected in the power flow equations
- Power flow = `-1/X × (θ_to - θ_from)`

This is standard for transmission expansion planning but may miss voltage and reactive power issues.

### 3.2 Transmission Losses

Loss rate and distance parameters are loaded from data but **not actively used** in the flow balance constraints. The DC-OPF is lossless.

### 3.3 Branch Investment Costs Disabled

Transmission investment cost terms are **commented out** in the objective function (lines 462–474). The model can decide to invest in/retire transmission lines (if `transmission=True`), but those decisions have zero cost impact.

### 3.4 Copper Plate Option

When `flow_model="CP"`, all power flow constraints are removed and the system becomes a single-node model. All generators can serve any load regardless of location.

---

## 4. Generator Modeling Assumptions

### 4.1 Thermal Generators

- **Status is binary:** A generator is entirely on or off — no partial commitment
- **Ramp rates** are fractions of PMax per hour (default 0.1 = 10% per hour from `load_default_data_settings`)
- **Minimum stable output** (`thermalMin`) is a fraction of PMax
- **Startup/shutdown** takes exactly one commitment period (no multi-period ramping)
- **Reserve constraints are disabled** (commented out due to infeasibility)

### 4.2 Renewable Generators

- **Must-take:** All available capacity must be either generated or curtailed
- **Continuous investment:** MW capacity is a continuous variable (can install 127.3 MW)
- **No minimum operating point:** Renewables can curtail to zero
- **Capacity value** for reserves is computed from the capacity factor (ratio of mean-to-peak `p_max`)

### 4.3 No Storage

Storage is declared as a set (line 1705) but **no constraints or variables** are implemented for it. Storage modeling is a placeholder.

### 4.4 No Hydro in GTEP

Hydro generators are not modeled in the GTEP formulation. The 10 hydro units in the Prescient_2 baseline are not part of the GTEP solution.

---

## 5. Data Flow

### 5.1 Input Data Path (Coal Case Study)

```
gtep/data/123_Bus_Coal/
├── gen.csv            → NOT directly used by GTEP
├── bus.csv            → bus topology
├── branch.csv         → transmission lines
├── timeseries_pointers.csv → maps generators to timeseries
├── DAY_AHEAD_*.csv    → load, wind, solar timeseries
├── REAL_TIME_*.csv    → real-time timeseries
├── Prescient/gen.csv  → 374 rows, HAS fuel_cost1/2/3, capex1/2/3 columns
│                         (broken Prescient columns — FP=1, HR=fuel_cost)
└── simulation_objects.csv → metadata
```

### 5.2 Data Loading Pipeline (`gtep_data.py`)

1. **`load_prescient(data_path)`** — Uses Prescient's `GmlcDataProvider` to read RTS-GMLC format. Creates Egret `ModelData` object with 24×365 timesteps. Marks candidates (suffix "-c") as `in_service=False`. Extracts 5 representative days (seasonal). Stores as `self.representative_data` (list of cloned ModelData objects).

2. **`load_default_data_settings()`** — Fills missing generator and branch fields with defaults:

   | Field | Default | Notes |
   |-------|---------|-------|
   | lifetime | 1 (coal), 3 (other) | In investment periods |
   | spinning_reserve_frac | 0.1 | 10% of PMax |
   | quickstart_reserve_frac | 0.1 | 10% of PMax |
   | ramp_up_rate, ramp_down_rate | 0.1 | 10% of PMax per period |
   | investment_cost | $235,164 | Flat default |
   | capital_multiplier | 1 | |
   | extension_multiplier | 0 | Overridden to 0.06 in model |

3. **`import_load_scaling(load_file_name)`** — Reads Excel workbook with future load forecasts. Filters to years [2025, 2030, 2035]. Computes per-zone scaling factors for 8 ERCOT weather zones.

4. **`texas_case_study_updates(data_path)`** — Reads `Prescient/gen.csv` (the 374-row file). Populates each generator's `fuel_cost1/2/3`, `capex1/2/3`, `fixed_ops1/2/3`, `var_ops1/2/3` into the ModelData.

### 5.3 Model Creation

```python
mod_object = ExpansionPlanningModel(
    stages=3,           # 3 investment periods
    data=data_object,   # full ExpansionPlanningData with representative_data
    num_reps=4,         # 4 representative periods
    len_reps=24,        # 24 hours each
    num_commit=24,      # 24 commitment periods
    num_dispatch=1      # 1 dispatch period per commitment
)
mod_object.config["include_investment"] = True
mod_object.config["flow_model"] = "CP"
mod_object.config["scale_texas_loads"] = True
mod_object.config["transmission"] = False
mod_object.create_model()
```

### 5.4 GDP Transformation and Solve

```python
TransformationFactory("gdp.bound_pretransformation").apply_to(mod_object.model)
TransformationFactory("gdp.bigm").apply_to(mod_object.model)
opt = Gurobi()
mod_object.results = opt.solve(mod_object.model, tee=True)
```

### 5.5 Solution Extraction

```python
sol_object = ExpansionPlanningSolution()
sol_object.load_from_model(mod_object)
sol_object.dump_json("./gtep_solution.json")
```

Output JSON contains a `primals_tree` with nested investment → representative → commitment → dispatch structure, plus variable values, bounds, and metadata.

### 5.6 Post-Solve Data Generation (`validation.py`)

```python
populate_generators(input_dir, sol_object, output_dir)  # filters gen.csv by solution
populate_transmission(input_dir, sol_object, output_dir) # filters branch.csv
filter_pointers(input_dir, output_dir)                   # updates timeseries_pointers
clone_timeseries(input_dir, output_dir)                  # copies timeseries files
```

This produces the Prescient-ready data directory (e.g., `Prescient_2_2035/`).

---

## 6. Known Limitations and TODOs in Code

| Item | Location | Description |
|------|----------|-------------|
| Reserve infeasibility | Line 818 | Reserve constraints commented out; "causes infeasibility issues" |
| Renewable quota vacuous | Line 503 | `ed = 0` always; quota constraint has no effect |
| Branch costs disabled | Line 462–474 | Transmission investment costs commented out |
| varCost dead code | Line 579 | Variable O&M never added to cost (unreachable return) |
| Fixed cost scaling | Line 1053 | `1000/(5*8760)` hardcoded — fragile if period length changes |
| Hardcoded years | Line 2038 | `[2025, 2030, 2035]` not parameterized |
| Storage placeholder | Line 1705 | Set exists but no variables/constraints |
| Investment cost FIXME | Line 421 | "investment cost definition needs to be revisited" |
| Extension multiplier override | Line 1965 | Forced to 0.06 for Texas case; not from data |
| Retirement multiplier | Line 1967 | Hardcoded 0.1/1.0; not from data |

---

## 7. Relationship to Prescient PCM

The GTEP model determines **what** infrastructure exists in each planning year. Prescient then simulates **how** that infrastructure operates hour-by-hour.

| Aspect | GTEP Model | Prescient PCM |
|--------|-----------|---------------|
| Time horizon | Multi-decade (3 stages) | 1 year (8760 hours) |
| Investment | Decides build/retire/extend | Takes infrastructure as given |
| Commitment | Simplified (4 states per hour) | Full MILP UC with detailed constraints |
| Dispatch | Linear cost, 15-min to 1-hr | Piecewise cost curves, 1-hr SCED |
| Cost model | Single fuelCost per fuel type | `Fuel Price × HR_incr` per segment |
| Network | DC-OPF or copper plate | PTDF or B-theta |
| Reserves | Disabled (commented out) | Active (reserve factor = 10%) |

The conversion from GTEP to Prescient (`convert_gtep_to_prescient_2035.ipynb`) bridges these differences by mapping the GTEP's linear `fuelCost` back into Prescient's `Fuel Price × HR` format.
