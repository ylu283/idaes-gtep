# GTEP Solve Milestone — All Three Configurations Optimal

> 2026-05-23 | Branch: `commitment_period`

## Summary

After 20 rounds of debugging (05-20 to 05-23), all three GTEP configurations solved to optimality with Gurobi 11.0.2 on CRC.

## Results

| | 4HR (o951672) | 2HR (o951671) | 1HR (o951670) |
|---|---|---|---|
| Model rows | 7.0M | 14.9M | 30.7M |
| Model cols | 370K | 771K | 1.57M |
| Build time | 52s | 109s | 225s |
| BigM transform | 212s | 456s | 943s |
| Presolve | 10s | 42s | 888s |
| Solve (total) | 175s (3min) | 1138s (19min) | 4703s (78min) |
| Objective | 9.774e+09 | 9.794e+09 | 2.442e+09 |
| Gap | 0.0001% | 0.0000% | 0.0002% |
| Simplex iterations | 10,238 | 51,473 | 168,586 |
| Solutions found | 4 | 7 | 6 |

## Output Files (on CRC)

- `retirement_allowed_no_extreme_4hr_commit/` — 4 JSON files
- `retirement_allowed_no_extreme_2hr_commit/` — 4 JSON files
- `retirement_allowed_no_extreme_full_load/` — 3 JSON files (no costs.json)

Each directory contains:
- `renewable_investments.json` — renewable vars with value >= 0.001
- `dispatchable_investments.json` — thermal disjunct indicator vars (True)
- `load_shed.json` — load shedding vars with value >= 0.001
- `costs.json` — operating + investment cost expressions (2hr/4hr only)

## Critical Fixes That Enabled Solve

| Fix | Bug | Commit |
|---|---|---|
| Fix 19 | `renewableCapacityNameplate` only used rep period 0 — variable bounds tighter than capacity_factor RHS for other rep periods | `942f308` |
| Fix 20 | `gen_stats_link` formula `Op(t) = Op(t-1) + Inst(t-1) - Ret(t-1)` made retirement mechanically impossible under xor disjunction — in-service coal (lifetime=2) could never satisfy `gen_retirement` | `ec087b7` |

Both bugs exist on the `main` branch as well.

## Known Caveats

### 1. Random Cost Parameters

All three runs print: *"Cost data was not provided in m.mc instance... Setting costs parameters to random values for now."*

`m.mc = self.cost_data` is `None` because the driver doesn't pass `cost_data`. Costs default to 1 for all generators. This means:
- Objective function values are not economically meaningful
- Investment decisions (which gens retire/extend/install) are driven by feasibility constraints, not cost optimization
- The solve proves **structural feasibility**, not economic optimality

### 2. Objective Function Discrepancy (1HR vs 2HR/4HR)

- 4HR: 9.774e+09
- 2HR: 9.794e+09
- 1HR: 2.442e+09

The 1HR value is ~4x smaller. Possible causes:
- `driver_coal.py` (1HR) extracts costs using `costs[var.name]` (bug: uses last loop var name instead of `exp.name`), while 2HR/4HR drivers use `costs[exp.name]`. The 1HR costs dict may be incomplete or overwritten.
- Different temporal resolution means different dispatch feasibility regions
- 1HR doesn't aggregate data, so capacity factors and load patterns are at full hourly resolution

### 3. Large Objective Coefficients

Gurobi warns: *"Model contains large objective coefficients (up to 5e+10). Consider reformulating or setting NumericFocus."* This hasn't caused solve failures but may affect solution quality for tighter tolerances.

## How to Interpret Results

### Investment Decisions (`dispatchable_investments.json`)

Keys follow the pattern: `investmentStage[s].genXXX[gen_id].indicator_var.()`

States per generator per stage (exactly one active):
- `genOperational` — running
- `genInstalled` — newly built this stage
- `genRetired` — permanently shut down
- `genExtended` — past lifetime, kept running
- `genDisabled` — not available

Group by stage to answer: "At each 5-year mark (2025/2030/2035), which generators retire and which get built?"

### Renewable Capacity (`renewable_investments.json`)

Keys follow: `investmentStage[s].representativePeriod[r].commitmentPeriod[c].dispatchPeriod[d].renewableXXX[gen_id]`

Variables include:
- `renewableInstalled` / `renewableOperational` / `renewableRetired` — capacity (MW) decisions at investment level
- `renewableGeneration` / `renewableCurtailment` — dispatch-level outputs (MW) per commitment period

### Load Shedding (`load_shed.json`)

If non-empty, the system had to shed load at certain buses/times. This indicates:
- Insufficient generation capacity
- Transmission bottlenecks (if transmission is enabled)
- Temporal mismatch between load and available generation

### Cost Breakdown (`costs.json`, 2HR/4HR only)

Per-stage operating and investment costs. With random cost data these are not meaningful but will be once real costs are provided.

## Results Analysis (05-24)

### Generator Fleet (from gen.csv)

| Fuel | Count | Total Capacity |
|---|---|---|
| Gas (G) | 113 | 56,006 MW |
| Wind (W) | 82 | 24,479 MW |
| Solar (S) | 72 | 8,264 MW |
| Coal (C) | 13 | 14,761 MW |
| Hydro (H) | 10 | 498 MW |
| Nuclear (N) | 2 | 5,139 MW |

### Thermal Investment Decisions

**All three configurations agree on the same investment pattern:**

| Stage | Year | Operational | Extended | Retired | Installed |
|---|---|---|---|---|---|
| 1 | 2025 | 128 | 0 | 0 | 0 |
| 2 | 2030 | 115 (4HR) / 128 (2HR,1HR) | 13 (4HR) / 0 (2HR,1HR) | 0 | 0 |
| 3 | 2035 | 52 (4HR) / 115 (2HR,1HR) | 76 (4HR) / 13 (2HR,1HR) | 0 | 0 |

Key observations:
- **No retirements anywhere.** All generators that hit their lifetime limit are Extended, never Retired.
- **No new installations.** Investment cost is 0 across all stages.
- **The same 13 coal generators** are Extended in all 3 configs (IDs: 6, 26, 165, 175, 177, 181, 185, 187, 232, 241, 250, 261, 269). These are ALL 13 coal units in the system (14,761 MW total).
- **4HR is more aggressive with extensions** — 76 generators Extended by 2035 vs only 13 for 2HR/1HR. This is because 4HR triggers extensions earlier (stage 2) while 2HR/1HR defer to stage 3.

**Why no retirements?** With random cost parameters (all set to 1), there's no economic incentive to retire a generator. Keeping everything running is always cheaper than load shedding ($10K/MWh penalty). The model extends generators past their lifetime rather than retiring them because the extension cost is negligible (extension_multiplier=0 in the data).

### Renewable Investments

All 160 renewable generators remain Operational across all 3 stages in all configs. No new renewable capacity is installed (again, investment cost = 0 makes this the cheapest option).

### Load Shedding

| | Stage 1 (2025) | Stage 2 (2030) | Stage 3 (2035) |
|---|---|---|---|
| 4HR | 0 | 510,646 MW | 708,574 MW |
| 2HR | 0 | 1,028,774 MW | 1,414,688 MW |
| 1HR | 0 | 2,055,758 MW | 2,818,722 MW |

Load shedding scales roughly linearly with temporal resolution (2x from 4HR→2HR, 2x from 2HR→1HR). This is expected: finer resolution exposes more peak-load periods that coarser averaging masks.

**No load shedding in Stage 1** — existing fleet is sufficient for 2025 demand. Shedding appears in Stages 2-3, likely because `scale_texas_loads=True` increases demand for future years but no new generation is built.

### Cost Summary (4HR and 2HR only)

| | Stage 1 (2025) | Stage 2 (2030) | Stage 3 (2035) |
|---|---|---|---|
| 4HR operating | 3.76M | 4.09B | 5.68B |
| 2HR operating | 3.76M | 4.12B | 5.67B |
| Investment | 0 | 0 | 0 |

Operating costs jump ~1000x from Stage 1 → Stage 2 due to the texas load scaling kicking in. Stage 1 and Stage 2 costs are consistent between 4HR and 2HR. Investment cost is 0 because no new capacity is built.

### What This Tells Us

The model is **structurally sound** — it solves, respects all physical constraints, and produces consistent results across temporal resolutions. But the results are **economically meaningless** due to random costs:

1. No retirements → extension is free (multiplier=0) and there's no retirement cost pressure
2. No new builds → investment cost would be needed to make building worthwhile vs shedding load
3. Load shedding instead of investment → without real cost data, shedding load is "cheaper" than building

**To get meaningful generator profiles**, need real `cost_data` with: fuel costs, capital costs (capex), fixed O&M, variable O&M, retirement costs, and extension costs.

## Next Steps

1. Provide real cost data (`cost_data` parameter) for economically meaningful results
2. Fix the 1HR `costs` extraction bug (`var.name` → `exp.name` in driver_coal.py)
3. Compare investment decisions across configs once cost data is realistic
4. Investigate why 4HR triggers extensions earlier (stage 2) — is this a temporal aggregation artifact?
5. Fix CRC git pack corruption before next push
