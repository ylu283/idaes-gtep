# Operational Violation Methodology — 2035 PCM Analysis

**Date:** 2026-05-21  
**Notebook:** `gtep/pcm_analysis/tsa_benchmark_2035/notebooks/operational_violations_2035.ipynb`  
**Purpose:** Document the mathematical definition and computation method for every operational violation check applied to the 2035 Prescient PCM output.

---

## Data Sources

All violation checks consume Prescient output CSVs and the fleet definition file:

| File | Key Columns Used | Resolution |
|------|-----------------|------------|
| `hourly_summary.csv` | LoadShedding, OverGeneration, ReserveShortfall, RenewablesCurtailment, Demand, Price | Hourly, system-level |
| `thermal_detail.csv` | Generator, Dispatch, Headroom, Unit State | Hourly, per-generator |
| `renewables_detail.csv` | Generator, Output, Curtailment | Hourly, per-generator |
| `reserves_detail.csv` | Magnitude, Shortfall, DA Shortfall | Hourly, system-level |
| `line_detail.csv` | Line, Flow, Violation | Hourly, per-line |
| `bus_detail.csv` | Bus, Demand, Shortfall, Overgeneration, LMP | Hourly, per-bus |
| `gen.csv` | GEN UID, Unit Type, PMin MW, PMax MW, Ramp Rate MW/Min, Min Up Time Hr, Min Down Time Hr | Static fleet definition |
| `branch.csv` | UID, Cont Rating | Static network definition |

---

## 1. Load Shedding

### Definition

Load shedding is involuntary curtailment of demand — electricity that consumers requested but the system could not deliver. This is the most severe operational violation. Any nonzero value indicates insufficient generation or transmission capacity to serve load.

### Mathematical Formulation

Prescient computes load shedding as the slack variable in the nodal power balance constraint. At each bus *b* and hour *t*:

```
Generation_b(t) + Import_b(t) - Export_b(t) + LoadShed_b(t) = Demand_b(t)
```

where `LoadShed_b(t) >= 0` is the unserved energy at bus *b*. Prescient penalizes this in the objective at a very high cost (the value of lost load, typically $10,000/MWh), so it is only nonzero when the system has no feasible dispatch.

System-level load shedding is the sum over all buses:

```
LoadShedding(t) = Σ_b LoadShed_b(t)     [MW]
```

### Notebook Computation (Cell 5)

- **Source column:** `hourly_summary.csv → LoadShedding` (system total per hour)  
- **Annual total:** `Σ_t LoadShedding(t)` [MWh]  
- **Hours affected:** count of hours where `LoadShedding(t) > 0`  
- **Peak value:** `max_t LoadShedding(t)` [MW]

Also available per-bus from `bus_detail.csv → Shortfall`.

### 2035 Result

All zeros for no-extreme runs (both PTDF and btheta, 365 days). Extreme scenario (btheta, 69 days) has 4 hours of load shedding.

---

## 2. Over-Generation

### Definition

Over-generation occurs when total generation exceeds total demand plus transmission losses. It is the opposite of load shedding — excess energy with nowhere to go. This typically happens when inflexible generators (high PMin) cannot reduce output fast enough to accommodate renewable ramps or demand drops.

### Mathematical Formulation

Over-generation is the surplus slack variable in the system power balance:

```
Σ_g Dispatch_g(t) + Σ_r Output_r(t) - OverGen(t) = Demand(t) + Losses(t)
```

where `OverGen(t) >= 0`. Like load shedding, it is penalized in the objective and only nonzero when the optimizer cannot reduce generation further (all dispatchable generators are at PMin or offline).

### Notebook Computation (Cell 5)

- **Source column:** `hourly_summary.csv → OverGeneration` (system total per hour)  
- **Annual total:** `Σ_t OverGeneration(t)` [MWh]  
- **Hours affected:** count of hours where `OverGeneration(t) > 0`  
- **Peak value:** `max_t OverGeneration(t)` [MW]

### Cross-Check: Supply-Demand Balance (Cell 23)

The notebook independently verifies by computing:

```
TotalSupply(t) = Σ_g Dispatch_g(t) + RenewablesUsed(t)
Imbalance(t)   = TotalSupply(t) - Demand(t)
```

where `Dispatch_g(t)` comes from `thermal_detail.csv` and `RenewablesUsed(t)` from `hourly_summary.csv`. A positive imbalance confirms over-generation; a negative imbalance would indicate unserved energy.

### 2035 Result

All zeros for no-extreme runs. Extreme scenario: 344–351 hours with over-generation, peak +2,202 MW (+9% of demand).

---

## 3. Reserve Shortfall

### Definition

Reserve shortfall occurs when the system's available spinning reserve falls below the required level. Spinning reserve is the additional generation capacity that online generators can provide within minutes to respond to a contingency (e.g., sudden generator trip). A shortfall means the system is vulnerable to contingencies.

### Mathematical Formulation

Prescient enforces a reserve requirement (typically 10% of demand):

```
ReserveRequirement(t) = 0.10 × Demand(t)    [MW]
```

The available spinning reserve is the sum of headroom across all online thermal generators:

```
AvailableReserve(t) = Σ_{g: online(t)} [PMax_g - Dispatch_g(t)]    [MW]
```

The shortfall is:

```
Shortfall(t) = max(0, ReserveRequirement(t) - ReserveProcured(t))    [MW]
```

where `ReserveProcured(t)` is the reserve actually committed by Prescient's unit commitment.

### Notebook Computation

**System-level (Cell 5):**  
- **Source column:** `hourly_summary.csv → ReserveShortfall`  
- **Annual total:** `Σ_t ReserveShortfall(t)` [MWh]  
- **Hours affected:** count where `ReserveShortfall(t) > 0`

**Detailed reserve analysis (Cell 10):**  
- **Source:** `reserves_detail.csv → Shortfall, Magnitude, DA Shortfall`  
- `Magnitude`: the reserve requirement for that hour [MW]  
- `Shortfall`: the unmet portion [MW]  
- Reports RT and DA shortfall hours separately

### Reserve Margin Analysis (Cell 9)

A complementary metric computed from thermal headroom:

```
ReserveMargin(t) = [Σ_g Headroom_g(t)] / Demand(t) × 100    [%]
```

where `Headroom_g(t)` comes from `thermal_detail.csv → Headroom` column (Prescient pre-computes this as `PMax_g - Dispatch_g(t)` for online generators).

**Thresholds:**
- **< 10% ("tight"):** ERCOT planning reserve margin target. The system is operating near its capacity limit.
- **< 15% ("cautionary"):** NERC recommended level. Some regions use this as the binding target.

The notebook chose 10% as the headline threshold because the test system is modeled after ERCOT topology.

### 2035 Result

No-extreme: 0 shortfall hours, minimum margin 16.5–23.7%. Extreme: 2 RT shortfall hours per config, worst shortfall 527 MW (extreme_B, 2035-02-07 H11), minimum margin 7.9%.

---

## 4. Renewable Curtailment

### Definition

Renewable curtailment is available wind or solar energy that the system chose not to dispatch. This is "wasted" clean energy — the resource was available but the grid could not absorb it, typically due to transmission congestion, minimum-generation constraints on thermal units, or over-supply during low-demand periods.

### Mathematical Formulation

For each renewable generator *r* at hour *t*:

```
Available_r(t) = CapacityFactor_r(t) × PMax_r    [MW]
Output_r(t) ≤ Available_r(t)
Curtailment_r(t) = Available_r(t) - Output_r(t)    [MW]
```

System total:

```
RenewablesCurtailment(t) = Σ_r Curtailment_r(t)    [MW]
```

### Notebook Computation

**System-level (Cell 5):**  
- **Source column:** `hourly_summary.csv → RenewablesCurtailment`

**Per-generator detail (Cell 21):**  
- **Source:** `renewables_detail.csv → Output, Curtailment`  
- Computes total output, total curtailed, available (output + curtailed), and curtailment rate  
- Reports by technology type (WIND, PV)  
- Computes realized capacity factor: `CF = Output / (PMax × Hours) × 100`

### 2035 Result

Zero curtailment across all runs (no-extreme and extreme). The fleet has sufficient transmission and flexibility to absorb all renewable output.

---

## 5. Line Flow Violations

### Definition

A line flow violation occurs when the power flow on a transmission line exceeds its thermal rating. This is a hard physical constraint — sustained overloads cause conductor heating and eventual failure. Prescient models this as a constraint on the DC power flow.

### Mathematical Formulation

For each line *l* at hour *t*:

```
|Flow_l(t)| ≤ Rating_l
Violation_l(t) = max(0, |Flow_l(t)| - Rating_l)    [MW]
```

Prescient reports the `Violation` column as the excess flow above the rating.

### Notebook Computation (Cell 12)

- **Source:** `line_detail.csv → Violation`
- **Count:** number of line-hours where `Violation > 0`
- **Total line-hours:** (number of lines) × (number of hours)

### Near-Congestion Analysis (Cell 13)

Even when violations are zero, congestion stress is measured by how close flows are to their limits:

```
FlowPercent_l(t) = |Flow_l(t)| / ContRating_l × 100    [%]
```

where `ContRating_l` is the continuous thermal rating from `branch.csv → Cont Rating`.

**Near-congested** is defined as `FlowPercent_l(t) > 90%`. This threshold is a standard industry practice — lines above 90% loading are considered operationally stressed and at risk of violation under small perturbations.

The notebook reports:
- Total line-hours above 90%
- Number of unique lines affected
- Number of hours with any line above 90%
- Top 10 most frequently congested lines

### 2035 Result

Zero violations across all runs. Near-congestion: 18 lines with >90% loading in no-extreme (21,381 line-hours), 39–40 lines in extreme.

---

## 6. PMin/PMax Compliance

### Definition

When a thermal generator is online (`Unit State = True`), its dispatch must be within its rated operating range: at or above its minimum stable output (PMin) and at or below its maximum capacity (PMax). Dispatching below PMin risks flame instability; above PMax is physically impossible.

### Mathematical Formulation

For each thermal generator *g* at hour *t*, when online:

```
PMin_g ≤ Dispatch_g(t) ≤ PMax_g
```

When offline (`Unit State = False`), dispatch must be zero:

```
Dispatch_g(t) = 0    if offline
```

### Notebook Computation (Cell 16)

- **Source:** `thermal_detail.csv → Dispatch, Unit State` merged with `gen.csv → PMin MW, PMax MW`
- **Online filter:** `Unit State == True`
- **Below-PMin violations:** count where `Dispatch < PMin × 0.99`
- **Above-PMax violations:** count where `Dispatch > PMax × 1.01`
- **Offline-nonzero:** count where `Unit State == False` and `|Dispatch| > 0.01`

The **1% tolerance** accounts for numerical solver precision — Prescient solves a MILP to optimality tolerances (typically 0.01% MIP gap), and floating-point dispatch values may differ from integer bounds by small amounts.

### 2035 Result

All PASS. Zero violations across all runs.

---

## 7. Ramp Rate Compliance

### Definition

The ramp rate limits how fast a generator can change its output between consecutive hours. Physical constraints include thermal stress on turbine components, boiler pressure dynamics, and shaft torque limits. Violating ramp rates causes equipment damage and reduces generator lifetime.

### Mathematical Formulation

For each thermal generator *g* between consecutive hours:

```
|Dispatch_g(t) - Dispatch_g(t-1)| ≤ RampRate_g × 60    [MW/hr]
```

where `RampRate_g` is in MW/min (from `gen.csv → Ramp Rate MW/Min`) and the factor of 60 converts to MW/hr for hourly dispatch intervals.

### Notebook Computation (Cell 17)

- **Source:** `thermal_detail.csv → Dispatch` (sorted by Generator, Date, Hour) merged with `gen.csv → Ramp Rate MW/Min`
- **Ramp computation:** `Ramp_MW = |Dispatch(t) - Dispatch(t-1)|` using `groupby('Generator').shift(1)`
- **Ramp limit:** `RampLimit_MW_hr = RampRate_MW_Min × 60`
- **Violations:** count where `Ramp_MW > RampLimit_MW_hr × 1.01`

The 1% tolerance again accounts for solver numerical precision.

The notebook also reports the maximum observed ramp across the fleet as a diagnostic.

### 2035 Result

All PASS. Zero violations. Maximum observed ramp: 1,674.5 MW/hr (PTDF), 1,217.6 MW/hr (btheta).

---

## 8. Min Up/Down Time Compliance

### Definition

Minimum up time is the shortest period a generator must remain online after starting up. Minimum down time is the shortest period it must remain offline after shutting down. These constraints reflect physical startup/cooldown processes — restarting a steam turbine before it has properly warmed up causes thermal fatigue; shutting down before the boiler has stabilized wastes fuel and stresses components.

### Mathematical Formulation

Define the state sequence for generator *g*: `s_g(t) ∈ {True, False}` from `Unit State`.

A **startup event** occurs at hour *t* when `s_g(t) = True` and `s_g(t-1) = False`.  
A **shutdown event** occurs at hour *t* when `s_g(t) = False` and `s_g(t-1) = True`.

For each contiguous run of online hours between a startup and the next shutdown:

```
OnlineDuration_g ≥ MinUpTime_g    [hours]
```

For each contiguous run of offline hours between a shutdown and the next startup:

```
OfflineDuration_g ≥ MinDownTime_g    [hours]
```

### Notebook Computation (Cell 18)

- **Source:** `thermal_detail.csv → Unit State` (sorted by Generator, Date, Hour) merged with `gen.csv → Min Up Time Hr, Min Down Time Hr`
- **Algorithm:** For each generator, compute run-length encoding of the `Unit State` sequence. Each run is a contiguous block of `True` (online) or `False` (offline) with a measured duration in hours.
- **Violation check:** For interior runs (excluding the first and last run in the simulation, which may be truncated by the simulation boundary):
  - If `state = True` and `duration < MinUpTime`: min-up-time violation
  - If `state = False` and `duration < MinDownTime`: min-down-time violation
- The first and last runs are excluded because the simulation starts and ends mid-operation — a generator that was already online at hour 0 may have been online for days before the simulation began.

### 2035 Result

All PASS. Zero violations across all runs.

---

## 9. Unit Cycling Analysis

### Definition

Unit cycling counts startup events — each time a generator transitions from offline to online. Unlike violations, cycling is not inherently wrong, but excessive cycling indicates operational stress. Each startup incurs physical costs (fuel for warmup, thermal fatigue, emissions) that the GTEP model does not account for because it uses 4 representative days and does not include startup costs in its objective.

### Mathematical Formulation

A startup event for generator *g* at hour *t*:

```
Startup_g(t) = 1    if s_g(t) = True  AND  s_g(t-1) = False
             = 0    otherwise
```

Total startups for the fleet:

```
TotalStartups = Σ_g Σ_t Startup_g(t)
```

### Notebook Computation (Cell 19)

- **Source:** `thermal_detail.csv → Unit State` sorted by Generator, Date, Hour
- **Startup detection:** `startup = (UnitState == True) & (UnitState.shift(1) == False)` within each generator group
- **Aggregation:** count by Unit Type and by individual generator
- Reports starts/gen and starts/day for NUC, COAL, CT
- Lists top 10 cyclers by total startups

### 2035 Result

No-extreme: 7,400–7,600 total startups. NUC: 0 (always online — baseload). COAL: 116–125 starts (10/gen/year). CT: 7,366–7,505 starts (55/gen/year). Top cycler: Gen 244 (CT) with 341–346 starts.

Extreme (69 days): NUC 14–17 starts (abnormal — baseload forced to cycle), COAL 390–415 starts (6x higher rate), CT 4,137–4,335 starts.

---

## 10. Negative LMP Analysis

### Definition

Negative locational marginal prices (LMPs) at a bus indicate that adding load at that bus would decrease system cost — a counterintuitive result caused by transmission congestion. When a bus has excess generation trapped behind a congested line, the marginal cost of serving additional load there is negative because the congestion relief value exceeds the generation cost.

### Mathematical Formulation

The LMP at bus *b* is the dual variable (shadow price) of the nodal power balance constraint:

```
LMP_b(t) = λ(t) + μ_b(t)
```

where `λ(t)` is the system energy price and `μ_b(t)` is the congestion component. When `μ_b(t)` is sufficiently negative (generation trapped behind congested lines), `LMP_b(t) < 0`.

### Notebook Computation (Cell 14)

- **Source:** `bus_detail.csv → LMP`
- **Negative LMP count:** bus-hours where `LMP < 0`
- **High LMP count:** bus-hours where `LMP > $100/MWh` and `LMP > $500/MWh`
- **Reports:** count, percentage of total bus-hours, affected buses, min/max LMP

**Threshold choices:**
- Any negative LMP is flagged (structural congestion signal)
- `$100/MWh`: moderate scarcity or congestion
- `$500/MWh`: severe scarcity or binding transmission constraint

### 2035 Result

No-extreme PTDF: 1,024 negative LMP bus-hours at 100/123 buses. LMP range: −$882.91 to +$1,000.00. 42 bus-hours above $100, 4 above $500.

---

## Summary Table

| # | Check | Formula | Tolerance | Source | Cell | No-Extreme | Extreme |
|---|-------|---------|-----------|--------|------|------------|---------|
| 1 | Load shedding | `Σ_b LoadShed_b(t)` | exact (>0) | hourly_summary | 5 | PASS (0) | 4 hrs (btheta) |
| 2 | Over-generation | `Σ_g Dispatch_g(t) + Renewables(t) - Demand(t)` | exact (>0) | hourly_summary | 5, 23 | PASS (0) | 344–351 hrs |
| 3 | Reserve shortfall | `max(0, Required(t) - Procured(t))` | exact (>0) | reserves_detail | 10 | PASS (0) | 2 RT hrs |
| 4 | Renewable curtailment | `Available_r(t) - Output_r(t)` | exact (>0) | renewables_detail | 21 | PASS (0) | PASS (0) |
| 5 | Line violations | `max(0, \|Flow_l(t)\| - Rating_l)` | exact (>0) | line_detail | 12 | PASS (0) | PASS (0) |
| 6 | PMin/PMax | `PMin ≤ Dispatch ≤ PMax` (online) | 1% | thermal_detail + gen | 16 | PASS (0) | PASS (0) |
| 7 | Ramp rate | `\|ΔDispatch\| ≤ RampRate × 60` | 1% | thermal_detail + gen | 17 | PASS (0) | PASS (0) |
| 8 | Min up/down time | `RunLength ≥ MinTime` (interior runs) | exact | thermal_detail + gen | 18 | PASS (0) | PASS (0) |
| 9 | Cycling | `Σ Startup_g(t)` | informational | thermal_detail | 19 | 7,400+ starts | NUC cycling |
| 10 | Negative LMPs | `LMP_b(t) < 0` | exact | bus_detail | 14 | 1,024 bus-hrs | 2,717+ bus-hrs |
