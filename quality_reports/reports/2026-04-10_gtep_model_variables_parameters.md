# GTEP Model: Variables and Parameters Reference

**Date:** 2026-04-10
**Source:** `gtep/gtep_model.py`

---

## 1. Sets

| Set | Line | Domain | Description |
|-----|------|--------|-------------|
| `m.buses` | 1652 | Bus IDs from data | Network buses (nodes) |
| `m.regions` | 1656 | Area labels from bus data | Aggregated regions/zones |
| `m.generators` | 1678 | Generator IDs from data | All generators (thermal + renewable) |
| `m.thermalGenerators` | 1682 | Subset of `m.generators` | Thermal units only (coal, gas, nuclear) |
| `m.renewableGenerators` | 1692 | Subset of `m.generators` | Renewable units only (wind, solar) |
| `m.storage` | 1705 | Storage IDs (conditional) | Storage units (if data available) |
| `m.stages` | 1712 | `RangeSet(1, N)` | Investment planning stages |
| `m.representativePeriods` | 1714 | Labels (e.g., ["a","b","c"]) | Representative operating periods per stage |
| `m.gensAtRegion[r]` | 2017 | Generator IDs per region | Maps regions to their generators |

**Block-level sets (created within blocks):**

| Set | Level | Description |
|-----|-------|-------------|
| `b.commitmentPeriods` | Representative Period | `RangeSet(1, numCommitmentPeriods)` |
| `b.dispatchPeriods` | Commitment Period | `RangeSet(1, numDispatchPeriods)` |

---

## 2. Parameters

### 2.1 Temporal Parameters

| Parameter | Line | Units | Default | Description |
|-----------|------|-------|---------|-------------|
| `m.representativePeriodLength[rp]` | 129 | hr | 24 | Hours per representative period |
| `m.numCommitmentPeriods[rp]` | 132 | — | 2 | Commitment periods per rep period |
| `m.numDispatchPeriods[rp]` | 138 | — | 2 | Dispatch periods per commitment period |
| `m.commitmentPeriodLength` | 144 | hr | 1 | Duration of each commitment period |
| `m.dispatchPeriodLength` | 146 | hr | 0.25 | Duration of each dispatch period |
| `m.weights[rp]` | 1849 | — | 456.25 | Annualization weight for each rep period (`5×365/4`) |
| `m.investmentFactor[s]` | 1850 | — | 1 | NPV/annualization factor per stage (mutable) |

### 2.2 Generator Capacity Parameters

| Parameter | Line | Units | Source | Description |
|-----------|------|-------|--------|-------------|
| `m.thermalCapacity[g]` | 1726 | MW | `p_max` from data | Maximum thermal output |
| `m.thermalMin[g]` | 1739 | fraction | `p_min / p_max` | Min stable output as fraction of PMax |
| `m.renewableCapacity[g]` | 1745 | MW | `p_max` (float or time-series) | Available renewable capacity |
| `m.renewableCapacityValue[g]` | 1761 | fraction | Computed from `p_max` | Reserve credit fraction for renewables |
| `m.lifetimes[g]` | 1734 | periods | `lifetime` from data | Remaining lifetime in investment periods |

### 2.3 Cost Parameters

| Parameter | Line | Units | Source | Description |
|-----------|------|-------|--------|-------------|
| `m.fuelCost1[g]` | 1883 | $/MWh | `fuel_cost1` from data | Thermal marginal cost, stage 1 |
| `m.fuelCost2[g]` | 1886 | $/MWh | `fuel_cost2` from data | Thermal marginal cost, stage 2 |
| `m.fuelCost3[g]` | 1889 | $/MWh | `fuel_cost3` from data | Thermal marginal cost, stage 3 |
| `m.fixedCost1/2/3[g]` | 1908–1919 | $/MWh | `fixed_ops1/2/3` | Fixed O&M cost per stage |
| `m.varCost1/2/3[g]` | 1908–1919 | $/MWh | `var_ops1/2/3` | Variable O&M cost per stage |
| `m.startupCost[g]` | 1945 | $ | `starting_cost` or `startup_cost` | Cost per startup event |
| `m.curtailmentCost` | 1924 | $/MWh | `2 × max(fuelCost)` | Penalty for curtailing renewables |
| `m.loadShedCost` | 1928 | $/MWh | 5000 | Penalty for unserved load |
| `m.fixedOperatingCost[g]` | 1855 | $/hr | 1 | Fixed operating cost (placeholder) |
| `m.deficitPenalty[s]` | 1856 | $/MWh | 1 | Penalty for renewable quota shortfall |
| `m.startFuel[g]` | 1859 | MMBTU | `start_fuel` from data | Fuel consumed during startup |

**Stage-specific cost assignment** (at investment block level):

| Stage | Fixed Cost | Var Cost | Fuel Cost | Source |
|-------|-----------|----------|-----------|--------|
| 1 | `m.fixedCost1` | `m.varCost1` | `m.fuelCost1` | Line 1540–1542 |
| 2 | `m.fixedCost2` | `m.varCost2` | `m.fuelCost2` | Line 1559–1561 |
| 3 | `m.fixedCost3` | `m.varCost3` | `m.fuelCost3` | Line 1576–1578 |

### 2.4 Investment Cost Parameters

| Parameter | Line | Units | Source | Description |
|-----------|------|-------|--------|-------------|
| `m.generatorInvestmentCost[g]` | 1972 | $/MW | `capex1/2/3` (stage-dependent) | Capital cost per MW |
| `m.capitalMultiplier[g]` | 1955 | — | `capital_multiplier` from data | Investment cost multiplier |
| `m.extensionMultiplier[g]` | 1961 | — | `extension_multiplier` (or 0.06 for Texas) | Life extension cost as fraction of capex |
| `m.retirementMultiplier[g]` | 1967 | — | 0.1 (thermal), 1.0 (renewable) | Retirement cost as fraction of capex |
| `m.branchInvestmentCost[l]` | 1826 | $/MW | `capital_cost` from data | Transmission line investment cost |
| `m.branchCapitalMultiplier[l]` | 1832 | — | `capital_multiplier` from data | Branch investment multiplier |
| `m.branchExtensionMultiplier[l]` | 1838 | — | `extension_multiplier` from data | Branch extension multiplier |

### 2.5 Network Parameters

| Parameter | Line | Units | Source | Description |
|-----------|------|-------|--------|-------------|
| `m.transmissionCapacity[l]` | 1774 | MW | `rating_long_term` from data | Line thermal rating |
| `m.loads[bus]` | 1800 | MW | `p_load` from data | Load demand at each bus |
| `m.lossRate[l]` | 1812 | per-unit | `loss_rate` from data | Loss rate per distance |
| `m.distance[l]` | 1819 | miles | `distance` from data | Line length |

### 2.6 Reserve Parameters

| Parameter | Line | Units | Source | Description |
|-----------|------|-------|--------|-------------|
| `m.spinningReserveFraction[g]` | 1783 | fraction | `spinning_reserve_frac` | Spinning reserve capacity as fraction of PMax |
| `m.quickstartReserveFraction[g]` | 1792 | fraction | `quickstart_reserve_frac` | Quick-start reserve as fraction of PMax |
| `m.maxSpinningReserve[g]` | 1991 | fraction | `max_spinning_reserve` | Max spinning reserve |
| `m.maxQuickstartReserve[g]` | 1998 | fraction | `max_quickstart_reserve` | Max quick-start reserve |
| `m.rampUpRates[g]` | 2004 | fraction/hr | `ramp_up_rate` | Ramp up rate as fraction of PMax |
| `m.rampDownRates[g]` | 2010 | fraction/hr | `ramp_down_rate` | Ramp down rate as fraction of PMax |
| `m.minOperatingReserve[r]` | 1980 | fraction | `min_operating_reserve` | Min total reserve per region |
| `m.minSpinningReserve[r]` | 1985 | fraction | `min_spinning_reserve` | Min spinning reserve per region |

### 2.7 Policy Parameters

| Parameter | Line | Units | Source | Description |
|-----------|------|-------|--------|-------------|
| `m.peakLoad[s]` | 1846 | MW | 0 | Peak load requirement per stage |
| `m.reserveMargin[s]` | 1847 | MW | 0 | Reserve margin per stage |
| `m.renewableQuota[s]` | 1848 | MW | 0 | Renewable energy target per stage |
| `m.emissionsFactor[g]` | 1934 | tCO2/MWh | `emissions_factor` | Full-lifecycle emissions factor |
| `b.carbonTax` | 1114 | $/tCO2 | 0 | Carbon tax (placeholder, not active) |

---

## 3. Decision Variables

### 3.1 Investment Variables (per stage)

**Thermal generator status** — Disjunctive (binary indicators):

| Variable | Line | Type | Description |
|----------|------|------|-------------|
| `b.genOperational[g]` | 206 | Disjunct | Generator is operational (continuing from previous stage) |
| `b.genInstalled[g]` | 211 | Disjunct | Generator is newly installed this stage |
| `b.genRetired[g]` | 217 | Disjunct | Generator is retired this stage |
| `b.genDisabled[g]` | 224 | Disjunct | Generator is permanently disabled |
| `b.genExtended[g]` | 229 | Disjunct | Generator's life is extended this stage |

Each generator is in **exactly one** of these 5 states per stage. Access the binary indicator via `b.genOperational[g].indicator_var.get_associated_binary()`.

**Renewable generator investment** — Continuous (MW):

| Variable | Line | Domain | Units | Description |
|----------|------|--------|-------|-------------|
| `b.renewableOperational[g]` | 271 | NonNeg | MW | MW of operational renewable capacity |
| `b.renewableInstalled[g]` | 274 | NonNeg | MW | MW newly installed this stage |
| `b.renewableRetired[g]` | 277 | NonNeg | MW | MW retired this stage |
| `b.renewableExtended[g]` | 280 | NonNeg | MW | MW life-extended this stage |
| `b.renewableDisabled[g]` | 283 | NonNeg | MW | MW disabled |

**Other investment variables:**

| Variable | Line | Domain | Units | Description |
|----------|------|--------|-------|-------------|
| `b.quotaDeficit` | 288 | NonNeg | MWh | Shortfall against renewable energy quota |
| `b.renewableCurtailmentInvestment` | 290 | NonNeg | $ | Total curtailment penalty for the stage |

**Transmission investment** (if `transmission` config enabled) — Disjunctive:

| Variable | Line | Type | Description |
|----------|------|------|-------------|
| `b.branchOperational[l]` | 238 | Disjunct | Line is operational |
| `b.branchInstalled[l]` | 244 | Disjunct | Line is newly installed |
| `b.branchRetired[l]` | 250 | Disjunct | Line is retired |
| `b.branchDisabled[l]` | 256 | Disjunct | Line is disabled |
| `b.branchExtended[l]` | 262 | Disjunct | Line's life is extended |

### 3.2 Dispatch Variables (per dispatch period)

| Variable | Line | Domain | Bounds | Units | Description |
|----------|------|--------|--------|-------|-------------|
| `b.thermalGeneration[g]` | 530 | NonNeg | [0, thermalCapacity] | MW | Thermal MW output |
| `b.renewableGeneration[g]` | 542 | NonNeg | [0, renewableCapacity] | MW | Renewable MW output |
| `b.renewableCurtailment[g]` | 554 | NonNeg | [0, renewableCapacity] | MW | Renewable MW curtailed |
| `b.loadShed[bus]` | 584 | NonNeg | — | MWh | Unserved load at each bus |
| `b.powerFlow[l]` | 615 | Reals | [-8×cap, +cap] | MW | Power flow on transmission line |
| `b.spinningReserve[g]` | 736 | NonNeg | [0, fraction×PMax] | MWh | Spinning reserve provided |
| `b.quickstartReserve[g]` | 751 | NonNeg | [0, fraction×PMax] | MWh | Quick-start reserve provided |

**DC power flow variables** (within branch disjuncts):

| Variable | Line | Domain | Bounds | Units | Description |
|----------|------|--------|--------|-------|-------------|
| `disj.busAngle[bus]` | 643 | Reals | [-π/6, +π/6] | rad | Voltage angle at bus |
| `disj.deltaBusAngle` | 659 | Reals | [-π/6, +π/6] | rad | Angle difference across line |

### 3.3 Commitment Variables (per commitment period)

**Thermal unit commitment** — Disjunctive (one of four states):

| Variable | Line | Type | Constraints Active |
|----------|------|------|--------------------|
| `b.genOn[g]` | 854 | Disjunct | Min output, max output, ramp up/down, spinning reserve |
| `b.genStartup[g]` | 915 | Disjunct | Output ≤ min output, startup ramp, startup cost |
| `b.genShutdown[g]` | 952 | Disjunct | Output ≤ min output, shutdown ramp |
| `b.genOff[g]` | 988 | Disjunct | Output = 0, quick-start reserve only |

Each generator is in **exactly one** of these 4 states per commitment period.

---

## 4. Expressions (Computed Quantities)

### 4.1 Dispatch-Level Expressions

| Expression | Line | Formula | Description |
|-----------|------|---------|-------------|
| `b.renewableGenerationSurplus[g]` | 563 | `generation - curtailment` | Net renewable output |
| `b.renewableCurtailmentCost[g]` | 570 | `curtailment × curtailmentCost` | Curtailment penalty per gen |
| `b.generatorCost[g]` | 576 | `thermalGeneration × fuelCost` | Thermal fuel cost per gen |
| `b.loadShedCost[bus]` | 587 | `loadShed × loadShedCost` | Load shedding penalty per bus |
| `b.renewableSurplusDispatch` | 592 | `Σ_g renewableGenerationSurplus` | Total net renewable |
| `b.generationCostDispatch` | 594 | `Σ_g generatorCost` | Total thermal fuel cost |
| `b.loadShedCostDispatch` | 596 | `Σ_bus loadShedCost` | Total load shed cost |
| `b.curtailmentCostDispatch` | 598 | `Σ_g renewableCurtailmentCost` | Total curtailment cost |
| `b.operatingCostDispatch` | 600 | `genCost + loadShedCost + curtailmentCost` | Total dispatch cost |

### 4.2 Commitment-Level Expressions

| Expression | Line | Formula | Description |
|-----------|------|---------|-------------|
| `b.renewableSurplusCommitment` | 1040 | `Σ_dp dispatchLength × renewableSurplusDispatch` | Total renewable MWh |
| `b.operatingCostCommitment` | 1055 | Dispatch costs + fixed O&M + startup costs | Total commitment period cost |
| `b.renewableCurtailmentCommitment` | 1093 | `Σ_dp renewableCurtailmentDispatch` | Total curtailment MW |

### 4.3 Investment-Level Expressions

| Expression | Line | Formula | Description |
|-----------|------|---------|-------------|
| `b.operatingCostInvestment` | 407 | `invFactor × Σ_rp weight × Σ_cp operatingCostCommitment` | Annualized operating cost |
| `b.investment_cost` | 423 | `invFactor × (install + extend + retire costs)` | Annualized capital cost |

---

## 5. Note on Dead Code

Line 579 contains a second `return` statement that is **unreachable**:
```python
def generatorCost(b, gen):
    return b.thermalGeneration[gen] * i_p.fuelCost[gen]         # ← ACTIVE
    return b.thermalGeneration[gen] * (i_p.fuelCost[gen] + i_p.varCost[gen])  # ← DEAD
```

The active cost formulation uses fuel cost only. The dead line would add variable O&M cost. The comment `## TEXAS: added varCost below` suggests this was an intended change that was never activated.
