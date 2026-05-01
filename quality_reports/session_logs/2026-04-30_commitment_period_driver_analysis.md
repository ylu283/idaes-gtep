# Session Log: Commitment Period Driver Analysis

**Date:** 2026-04-30
**Branch:** commitment_period (from idaes_coal2)

## Goal

Diagnose why the 2hr/4hr commitment period GTEP jobs failed on CRC, and audit whether `driver_coal_2hr.py` correctly implements coarser commitment periods.

## 2hr/4hr Job Failure Root Cause

Both jobs (`ERCOT_GTEP_2HR_COMMIT.o871586`, `ERCOT_GTEP_4HR_COMMIT.o871587`) failed at data loading with identical errors:

```
KeyError: '98.0'
  File ".../egret/parsers/rts_gmlc/parser.py", line 448, in _read_branches
    "from_bus": bus_id_to_name[str(row['From Bus'])],
```

**Cause:** The `gtep2` conda env on CRC has an **unpatched Egret** parser. The local Egret (at `~/GitHub/Egret/`) was previously patched to use `str(int(row['From Bus']))` (with `int()` guard), but the pip-installed Egret in `gtep2` uses `str(row['From Bus'])` — no `int()`. When pandas reads `branch.csv` with float-typed Bus IDs, `str(98.0)` != `'98'` → KeyError.

**Fix:** Install the patched Egret into `gtep2`:
```bash
cd ~/GitHub/Egret && conda activate gtep2 && pip install -e .
```

## Driver Correctness Audit: `driver_coal_2hr.py` vs `driver_coal.py`

### What the 2hr driver changes

| Change | Mechanism | Correct? |
|--------|-----------|----------|
| `num_commit=12` (from 24) | Constructor arg | ✅ |
| `p_load` aggregation (24→12 values) | `aggregate_hourly_to_blocks()` averages pairs | ✅ |
| `p_max` aggregation (24→12 values) | Same averaging for renewable time series | ✅ |
| `load_scaling` aggregation | Remap hour 1-24 → block 1-12, groupby mean | ✅ |
| `min_up_time` / `min_down_time` | `ceil(hours / block_hours)`, cap at `num_commit` | ✅ (conservative) |
| `commitmentPeriodLength` = 2 | Post-construction Param patch | ✅ (Pyomo evaluates at solve time) |
| Removed `costs` extraction | Avoids `var.name` leak bug from `driver_coal.py:117` | ✅ |

### Critical bugs found

#### Bug 1: Dispatch-level fuel cost not time-scaled

`gtep_model.py:577`:
```python
def generatorCost(b, gen):
    return b.thermalGeneration[gen] * i_p.fuelCost[gen]  # MW × $/MWh = $/hr
```

This gives $/hr (power × price). At the commitment level, `operatingCostCommitment` sums dispatch costs WITHOUT multiplying by dispatch period duration:

```python
sum(b.dispatchPeriod[disp_per].operatingCostDispatch for disp_per in b.dispatchPeriods)
```

In baseline (1hr commit, 1 dispatch): $/hr × 1 dispatch × (implicit 1hr) = $ — numerically correct by coincidence.

In 2hr commit (2hr blocks, 1 dispatch): $/hr × 1 dispatch × (implicit 1hr) = $ — but should be $/hr × 2hr = $. **Fuel cost underestimated by factor of BLOCK_HOURS.**

Meanwhile, fixed costs ARE correctly scaled: `fixedCost[gen] * b.commitmentPeriodLength * ...`

#### Bug 2: `dispatchPeriodLength` not adjusted

`renewableSurplusCommitment` (`gtep_model.py:1041`):
```python
return sum(m.dispatchPeriodLength * b.dispatchPeriod[disp_per].renewableSurplusDispatch ...)
```

`dispatchPeriodLength` defaults to 0.25hr. With `num_dispatch=1`, only 1 dispatch × 0.25hr = 0.25hr is covered, but each commitment block is 2hr. **Renewable surplus underestimated.**

### Impact

Both bugs cause the model to **undervalue operating costs relative to investment costs**, biasing the solution toward more investment/less retirement than correct.

## Correct Approaches to Commitment Period Sensitivity

### Approach A: Single dispatch, scale `dispatchPeriodLength`

- `num_commit=12`, `num_dispatch=1`
- Patch `dispatchPeriodLength` to `BLOCK_HOURS` (2hr)
- Fixes renewable surplus scaling
- Still needs model-level fix for `generatorCost` to multiply by dispatch period length
- Reduces MILP size (fewer total periods)

### Approach B: Multiple dispatches per commitment

- `num_commit=12`, `num_dispatch=BLOCK_HOURS` (2)
- Keep `dispatchPeriodLength=1hr` (or adjust to 1hr from default 0.25hr)
- Each 2hr commitment block contains 2 × 1hr dispatches
- Total dispatch periods = 12 × 2 = 24 — same problem size as baseline
- More accurate (preserves hourly dispatch resolution within commitment blocks)
- Still needs `dispatchPeriodLength` fix (0.25 → 1.0)

### Recommendation

Neither approach works correctly without fixing `generatorCost` to include time scaling. The model has a latent bug where `generatorCost = MW × $/MWh` without `× hours`, masked in baseline because every period is implicitly 1 hour.

## Bug: Ghost Rows in `123_Bus_Coal/gen.csv` (CRITICAL)

`gtep/data/123_Bus_Coal/gen.csv` had **289 ghost rows** — rows where cell contents were cleared but the rows themselves were not deleted. Total 581 rows, only 292 had actual data.

**Impact chain (two cascading failures):**

1. **First run (pip Egret in `gtep2`):** Ghost rows had `Bus ID` values (int column) but NaN in most other columns. Pandas kept `Bus ID` as int64 (no NaN in that column), but the Egret parser's `_read_branches` used `str(row['From Bus'])` without `int()` guard → `'98.0'` KeyError. This was the **unpatched Egret** issue, not the ghost rows directly.

2. **Second run (patched Egret installed):** Bus ID issue fixed. But ghost rows have `Unit Type=NaN`, which doesn't match `Storage`, `CSP`, or `RENEWABLE_TYPES` → parser treats them as thermal generators. `PMin MW=NaN` → `isnan()` check at line 529-531 deletes `p_min` from `gen_dict` → line 622 `gen_dict["p_min_agc"] = gen_dict["p_min"]` → **KeyError: 'p_min'**.

**Fix:** Dropped all rows where `GEN UID` is NaN. gen.csv: 581 → 293 lines (292 generators + header). This is the same known bug pattern documented in MEMORY.md: *"Deleting generators by clearing cell contents (not deleting rows) leaves empty rows."*

**Verification:** After cleanup — 0 NaN in GEN UID, Bus ID, PMin MW, PMax MW. Bus ID dtype is int64. Unit type distribution: CT=113, WIND=82, PV=72, COAL=13, HYDRO=10, NUC=2.

## Implementation (Approach A Chosen)

**Decision:** Approach A — reduce both commitment and dispatch resolution together.

### Model Fix: `gtep_model.py` (3 expressions)

All three dispatch-level cost expressions were missing `× b.periodLength`:

| Line | Expression | Before | After |
|------|-----------|--------|-------|
| 572 | `renewableCurtailmentCost` | `curtailment × curtailmentCost` | `curtailment × curtailmentCost × periodLength` |
| 577 | `generatorCost` | `thermalGen × fuelCost` | `thermalGen × fuelCost × periodLength` |
| 585 | `loadShedCost` | `loadShed × loadShedCost` | `loadShed × loadShedCost × periodLength` |

Also removed dead code: unreachable `varCost` return (line 579) and orphaned `# * b.dispatchLength` comment (line 581).

**Backwards compatible:** `periodLength` defaults to `Param(default=1)` at line 1189 — baseline (1hr) behavior is unchanged.

### Driver Fix: `driver_coal_2hr.py` and `driver_coal_4hr.py`

Added patching for `dispatchPeriodLength` and `periodLength` alongside the existing `commitmentPeriodLength` patch:

```python
m.dispatchPeriodLength = BLOCK_HOURS                    # model-level
...
    cp_blk.dispatchPeriod[dp].periodLength = BLOCK_HOURS  # block-level
```

### Verification

- 16/16 non-pyomo tests pass (pyomo tests skip — no pyomo in local env)
- Model diff is minimal: 3 expressions gain `* b.periodLength`
- Baseline `driver_coal.py` is unaffected (no `periodLength` patches, default=1)

### Reports Created

- `quality_reports/reports/2026-04-30_commitment_period_sensitivity_design.md` — Approach A vs B comparison
- `quality_reports/reports/2026-04-30_commitment_period_modification_guide.md` — step-by-step guide for future commitment period variants

## Next Steps

1. **Fix Egret on CRC** — `cd ~/GitHub/Egret && conda activate gtep2 && pip install -e .`
2. **Push fixes** — model time-scaling fix + driver patches
3. **Re-run 2hr/4hr jobs** on CRC
4. **Compare results** — investment/retirement decisions across 1hr/2hr/4hr resolutions
