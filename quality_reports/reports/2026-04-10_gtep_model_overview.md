# GTEP Model Overview

**Date:** 2026-04-10
**Source:** `gtep/gtep_model.py` (2,326 lines)
**Type:** Mixed-Integer Linear Program with Generalized Disjunctive Programming (MILP/GDP)

---

## 1. What the Model Does

The GTEP model determines the **least-cost plan** for building, retiring, and operating power generators and transmission lines over a multi-decade planning horizon. It simultaneously optimizes:

- **Investment decisions** — which generators/lines to build, retire, or extend (long-term, per stage)
- **Unit commitment** — which generators to turn on/off in each scheduling period (medium-term)
- **Economic dispatch** — how much power each generator produces in each time step (short-term)

The model is formulated as a Generalized Disjunctive Program (GDP) and solved via Big-M reformulation using Gurobi or CPLEX.

---

## 2. Temporal Structure (4-Level Nested Hierarchy)

The model uses a nested block structure to represent multiple time scales:

```
Investment Stage (e.g., 2025, 2030, 2035)
  └── Representative Period (e.g., winter day, summer day, ...)
        └── Commitment Period (e.g., 1-hour scheduling blocks)
              └── Dispatch Period (e.g., 15-minute intervals)
```

| Level | Typical Length | # Per Parent | Decision Type |
|-------|---------------|-------------|---------------|
| Investment Stage | 5 years | 3 stages (2025, 2030, 2035) | Build/retire/extend generators and lines |
| Representative Period | 24 hours | 3–5 per stage | Typical operating days (seasonal) |
| Commitment Period | 1 hour | 24 per rep period | On/off/startup/shutdown decisions |
| Dispatch Period | 15 min | 4 per commitment period | MW output, power flow, reserves |

**Default configuration:** 3 stages × 3 rep periods × 24 commitment × 4 dispatch = **864 time steps total**.

The `weights` parameter (default: `5×365/4 ≈ 456.25`) scales each representative period to represent a full year.

---

## 3. Spatial Structure

- **Buses** — individual nodes in the transmission network (e.g., 123 buses for the Texas case)
- **Regions** — aggregation of buses by area (e.g., 8 ERCOT weather zones)
- **Transmission lines** — connect buses with DC power flow constraints

Each generator is assigned to a bus. Load is defined per bus. Power flows are computed per transmission line.

---

## 4. Generator Types

### Thermal Generators (coal, gas CT, nuclear)
- **Investment status:** Binary disjunctive — each generator is in exactly one of 5 states: Operational, Installed, Retired, Disabled, Extended
- **Commitment status:** Binary disjunctive — each generator is in exactly one of 4 states per commitment period: On, Startup, Shutdown, Off
- **Dispatch:** Continuous MW output with ramp rate limits
- **Cost:** Linear marginal cost `thermalGeneration × fuelCost` (see Section 7)

### Renewable Generators (wind, solar PV)
- **Investment:** Continuous MW capacity — can install fractional amounts
- **Dispatch:** Must-take with curtailment option; `generation + curtailment = capacity`
- **Cost:** Zero marginal cost; curtailment penalized at `2 × max(fuelCost)`

---

## 5. Objective Function

**Minimize total system cost** over all investment stages:

```
Total Cost = Operating Cost + Expansion Cost + Penalty Cost
```

Defined at `gtep_model.py:1608–1641`.

### Operating Cost (per stage)
```
OperatingCost[s] = investmentFactor[s] × Σ_{rp} weight[rp] × Σ_{cp} OperatingCostCommitment[s,rp,cp]
```
Where `OperatingCostCommitment` includes:
- **Fuel cost:** `Σ_g thermalGeneration[g] × fuelCost[g]` for all dispatch periods
- **Fixed O&M:** `Σ_g fixedCost[g] × commitmentPeriodLength × isOn[g]` (thermal), plus fixed cost × capacity (renewable)
- **Startup cost:** `Σ_g startupCost[g] × isStarting[g]`
- **Load shedding penalty:** `Σ_bus loadShed[bus] × loadShedCost`
- **Curtailment penalty:** `Σ_g curtailment[g] × curtailmentCost`

Source: `gtep_model.py:1055–1090` (commitment cost), `gtep_model.py:576–602` (dispatch cost).

### Expansion Cost (per stage)
```
ExpansionCost[s] = investmentFactor[s] × (
    Σ_g investmentCost[g] × capitalMultiplier[g] × isInstalled[g]       (new thermal)
  + Σ_g investmentCost[g] × capitalMultiplier[g] × renewableInstalled[g] (new renewable MW)
  + Σ_g investmentCost[g] × extensionMultiplier[g] × isExtended[g]      (thermal extension)
  + Σ_g investmentCost[g] × extensionMultiplier[g] × renewableExtended[g](renewable extension)
  + Σ_g investmentCost[g] × retirementMultiplier[g] × isRetired[g]      (retirement cost)
)
```

Source: `gtep_model.py:423–475`.

### Penalty Cost (per stage)
```
PenaltyCost[s] = deficitPenalty[s] × investmentFactor[s] × quotaDeficit[s]
               + renewableCurtailmentInvestment[s]
```

Source: `gtep_model.py:1621–1627`.

---

## 6. Key Constraints

### 6.1 Power Balance (per bus, per dispatch period)

Every bus must balance injections and withdrawals:

```
Σ_g thermalGeneration[g] + Σ_g renewableGeneration[g]
  + Σ_in powerFlow[line] - Σ_out powerFlow[line]
  + loadShed[bus] - load[bus] = 0
```

Source: `gtep_model.py:771–794`. This is a standard nodal balance constraint.

### 6.2 DC Power Flow (per line, per dispatch period)

For in-use transmission lines:
```
powerFlow[line] = (-1/X[line]) × (busAngle[to] - busAngle[from] + phaseShift[line])
```

For not-in-use lines: `powerFlow[line] = 0`

Implemented as a disjunction (`branchInUse` vs `branchNotInUse`). Bus angles bounded to ±π/6. Source: `gtep_model.py:623–695`.

### 6.3 Renewable Capacity Factor (per renewable gen, per dispatch period)

All available renewable capacity must be either generated or curtailed:
```
renewableGeneration[g] + renewableCurtailment[g] = renewableCapacity[g]
```

Source: `gtep_model.py:798–803`. Renewables are must-take; curtailment is penalized in the objective.

### 6.4 Thermal Operating Limits (per thermal gen, per dispatch period)

Depend on commitment state:

| State | Min Output | Max Output |
|-------|-----------|------------|
| **On** | `thermalMin × capacity` | `capacity - spinningReserve` |
| **Startup** | 0 | `thermalMin × capacity` |
| **Shutdown** | 0 | `thermalMin × capacity` |
| **Off** | 0 | 0 |

Source: `gtep_model.py:854–1006`.

### 6.5 Ramp Rate Limits (per thermal gen, per dispatch period)

When generator is On:
```
generation[t] - generation[t-1] ≤ rampUpRate × capacity     (ramp up)
generation[t-1] - generation[t] ≤ rampDownRate × capacity   (ramp down)
```

During Startup/Shutdown, ramp limits use `max(thermalMin, rampRate)`. Source: `gtep_model.py:879–986`.

### 6.6 Minimum Up/Down Time (per thermal gen, across commitment periods)

Enforced through logical sequencing constraints within representative periods:
- After startup, must stay on for at least `minUpTime` commitment periods
- After shutdown, must stay off for at least `minDownTime` commitment periods

Source: `gtep_model.py:1335–1496`.

### 6.7 Commitment Logic (per thermal gen, per commitment period)

Each thermal generator must be in exactly one state:
```
genOn[g] ⊕ genStartup[g] ⊕ genShutdown[g] ⊕ genOff[g]
```

Additionally: a generator can only be committed (On/Startup/Shutdown) if its investment status is Operational, Installed, or Extended:
```
(genOn ∨ genStartup ∨ genShutdown) ⟹ (genOperational ∨ genInstalled ∨ genExtended)
```

Source: `gtep_model.py:1018–1030`.

### 6.8 Investment Linking (across stages)

These logical constraints ensure consistent investment state transitions:

| Constraint | Rule | Source |
|-----------|------|--------|
| `consistent_operation` | Operational at stage t ⟹ operational or installed at t-1 | Line 2157 |
| `consistent_operation_future` | Operational at t-1 ⟹ operational, extended, or retired at t | Line 2171 |
| `full_retirement` | Retired at t-1 ⟹ disabled at t | Line 2186 |
| `consistent_disabled` | Disabled at t-1 ⟹ disabled or installed at t | Line 2200 |
| `consistent_extended` | Extended at t-1 ⟹ extended or retired at t | Line 2214 |
| `full_investment` | Installed at t-1 ⟹ operational at t | Line 2228 |
| `gen_retirement` | Units active before their lifetime expires must be retired or extended by deadline | Line 2088 |
| `renewable_stats_link` | `operational[t] = operational[t-1] + installed[t-1] + extended[t-1] - retired[t-1]` | Line 2129 |

**State transition diagram for thermal generators:**

```
                    ┌──────────────┐
                    │   Disabled   │←──────────────┐
                    └──────┬───────┘               │
                           │ install               │ retire
                           ▼                       │
┌──────────┐         ┌──────────────┐        ┌─────┴──────┐
│ Disabled │────────→│  Installed   │───────→│ Operational│
└──────────┘ install └──────────────┘  next  └─────┬──────┘
                                       stage       │
                                              ┌────┴─────┐
                                              │          │
                                         extend      retire
                                              │          │
                                              ▼          ▼
                                        ┌──────────┐ ┌──────────┐
                                        │ Extended │ │ Retired  │
                                        └────┬─────┘ └────┬─────┘
                                             │            │
                                          retire       disable
                                             │            │
                                             ▼            ▼
                                        ┌──────────┐ ┌──────────┐
                                        │ Retired  │ │ Disabled │
                                        └──────────┘ └──────────┘
```

### 6.9 Reserve Constraints (currently commented out)

Operating reserve and spinning reserve constraints exist in the code but are **commented out** due to infeasibility issues. See `gtep_model.py:815–844`. The variables (`spinningReserve`, `quickstartReserve`) still exist and are bounded.

---

## 7. Key Assumptions

### Cost Model
- **Thermal fuel cost is linear:** `cost = generation × fuelCost` (no piecewise heat rate curve). The GTEP model does NOT use `Fuel Price × HR_incr`. Instead, `fuelCost` is a single $/MWh value per fuel type per stage. (Source: `gtep_model.py:578`)
- **fuel_cost is uniform per fuel type:** All CTs share the same `fuelCost`, all COALs share the same `fuelCost`, etc. No per-generator efficiency differentiation. (Source: `Prescient/gen.csv` `fuel_cost1/2/3` columns)
- **Curtailment cost** = 2× the maximum thermal fuel cost (Source: line 1924)
- **Load shedding cost** = $5,000/MWh (Source: line 1928)
- **Fixed cost coefficient** uses `1000 / (5 × 8760)` scaling factor (Source: line 1053)
- **Extension multiplier** forced to 0.06 for the Texas case (Source: line 1965)
- **Retirement multiplier:** 0.1 for thermal, 1.0 for renewable (Source: line 1967)

### Temporal Representation
- Uses **representative days** (3–5) to represent a full year; each weighted by `5×365/4 ≈ 456.25` hours
- **No chronological linkage** between representative periods — each is treated independently
- Planning years are **hardcoded** as [2025, 2030, 2035] (Source: line 2038)

### Network Model
- **DC power flow** approximation (linearized AC power flow)
- Losses modeled via `lossRate × distance` parameters (data exists but not actively used in constraints)
- Branch investment costs are **commented out** in the current version (Source: lines 462–474)

### Renewable Treatment
- Must-take generation with curtailment penalty
- Continuous investment (fractional MW)
- Capacity value for reserves computed from capacity factor (Source: line 1761)
- `Output_pct_0` handling is NOT in the GTEP model (that's a Prescient detail)

### Reserves
- Reserve constraints are **disabled** (commented out) in the current code
- Reserve variables still exist with bounds from data
- The code notes infeasibility issues when reserves are enforced (Source: line 818)

---

## 8. Configuration Options

| Option | Default | Effect |
|--------|---------|--------|
| `include_investment` | True | Enable/disable investment decisions |
| `include_commitment` | True | Enable/disable unit commitment (on/off decisions) |
| `include_redispatch` | True | Enable/disable multiple dispatch periods per commitment |
| `flow_model` | "DC" | "DC" for DC-OPF with angles; "CP" for copper plate |
| `transmission` | False | Enable/disable transmission investment decisions |
| `scale_texas_loads` | False | Use Texas-specific load scaling and stage-indexed costs |
| `scale_loads` | True | Allow load scaling to future years |

Source: `gtep/config_options.py` (133 lines).

---

## 9. Data Pipeline

```
RTS-GMLC data (gen.csv, bus.csv, branch.csv, timeseries)
    │
    ▼
ExpansionPlanningData.load_prescient()     ← gtep/gtep_data.py
    │  creates Egret ModelData, extracts representative days
    ▼
ExpansionPlanningData.texas_case_study_updates()
    │  adds capex1/2/3, fuel_cost1/2/3, var_ops1/2/3 from gen.csv
    ▼
ExpansionPlanningData.import_load_scaling()
    │  reads Excel forecast, computes per-zone scaling factors
    ▼
ExpansionPlanningModel(data=..., config=...)   ← gtep/gtep_model.py
    │  builds Pyomo model with all sets, params, vars, constraints
    ▼
GDP Transformation (BigM)
    │
    ▼
Gurobi Solver
    │
    ▼
ExpansionPlanningSolution.load_from_model()   ← gtep/gtep_solution.py
    │  extracts investment decisions, dispatch, costs
    ▼
dump_json() → gtep_solution.json
    │
    ▼
validation.populate_generators() → filtered gen.csv for Prescient   ← gtep/validation.py
```

Source files: `gtep/driver_coal.py` (167 lines), `gtep/gtep_data.py` (192 lines).

---

## 10. Supporting Files

| File | Lines | Purpose |
|------|-------|---------|
| `gtep/gtep_model.py` | 2,326 | Core Pyomo optimization model |
| `gtep/gtep_data.py` | 192 | Data loading (Prescient/Egret format) |
| `gtep/config_options.py` | 133 | Configuration schema |
| `gtep/driver_coal.py` | 167 | Main workflow driver (123-bus coal case) |
| `gtep/driver.py` | 61 | Small test workflow (5-bus) |
| `gtep/gtep_solution.py` | 1,291 | Solution extraction, JSON serialization, plotting |
| `gtep/validation.py` | 143 | Post-solve data transformation (gen.csv filtering) |
| `gtep/map_bus_to_vars.py` | 255 | Technology-to-bus mapping (reference, not yet integrated) |
