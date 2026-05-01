# How to Correctly Modify Commitment Period Resolution in GTEP

**Date:** 2026-04-30
**Branch:** commitment_period
**Prerequisite reading:** `quality_reports/reports/2026-04-30_commitment_period_sensitivity_design.md`

---

## 1. Overview

This guide documents the exact steps to run the GTEP model at a different commitment period resolution (e.g., 2hr or 4hr blocks instead of the default 1hr). It covers what the model expects, what must change, and what pitfalls to avoid.

**Approach used:** Approach A — reduce both commitment and dispatch resolution together. Each representative day is divided into `N` equal blocks of `B` hours (`N × B = 24`).

| Config | N (num_commit) | B (block_hours) | Variables per rep-day |
|--------|---------------|-----------------|----------------------|
| Baseline (1hr) | 24 | 1 | 24 dispatch + 24 commit |
| 2hr blocks | 12 | 2 | 12 dispatch + 12 commit |
| 4hr blocks | 6 | 4 | 6 dispatch + 6 commit |
| 6hr blocks | 4 | 6 | 4 dispatch + 4 commit |

---

## 2. What Must Change (Checklist)

### 2.1 Data Aggregation (before `create_model()`)

The model indexes into time-series data using `values[commitment_period - 1]`. With fewer commitment periods, the data arrays must be shortened to match.

| Data | Source | Aggregation | Function |
|------|--------|-------------|----------|
| `p_load["values"]` | Load at each bus | Average B consecutive hours | `aggregate_hourly_to_blocks()` |
| `p_max["values"]` | Renewable capacity factor | Average B consecutive hours | `aggregate_hourly_to_blocks()` |
| `min_up_time` | Hours → block count | `ceil(hours / B)`, cap at N | In `aggregate_data()` |
| `min_down_time` | Hours → block count | `ceil(hours / B)`, cap at N | In `aggregate_data()` |
| `load_scaling` | Hourly scaling factors | Remap hour index, groupby mean | `aggregate_load_scaling()` |

**Key function:**
```python
def aggregate_hourly_to_blocks(values_24, block_hours):
    """Average 24 hourly values into blocks of block_hours."""
    n_blocks = len(values_24) // block_hours
    return [
        sum(values_24[i * block_hours : (i + 1) * block_hours]) / block_hours
        for i in range(n_blocks)
    ]
```

**Why averaging (not summing)?** `p_load` and `p_max` are in MW (power), not MWh (energy). The model's power balance constraint is `generation = load` in MW at each time point. Averaging preserves the correct power level; summing would double/quadruple it.

### 2.2 Model Construction

```python
mod_object = ExpansionPlanningModel(
    stages=3, data=data_object, num_reps=4, len_reps=24,
    num_commit=N,       # e.g., 12 for 2hr blocks
    num_dispatch=1,     # 1 dispatch per commitment (Approach A)
)
```

`len_reps=24` stays unchanged — it's the total hours in a representative day (unused by the model, but kept for documentation).

### 2.3 Post-Construction Parameter Patching

After `create_model()`, patch four temporal parameters:

```python
m = mod_object.model

# Model-level params (used in curtailment cost aggregation)
m.commitmentPeriodLength = B          # hours per commitment block
m.dispatchPeriodLength = B            # hours per dispatch block

# Block-level params (used in operating cost and ramp constraints)
for stage in m.stages:
    i_blk = m.investmentStage[stage]
    for rp in i_blk.representativePeriods:
        r_blk = i_blk.representativePeriod[rp]
        for cp in r_blk.commitmentPeriods:
            cp_blk = r_blk.commitmentPeriod[cp]
            cp_blk.commitmentPeriodLength = B
            for dp in cp_blk.dispatchPeriods:
                cp_blk.dispatchPeriod[dp].periodLength = B
```

**Why this works:** Pyomo `Param` objects are referenced symbolically in constraints. Changing their value before `solve()` updates all constraints that reference them. The BigM transformation reads parameter values, so patching must happen before `TransformationFactory("gdp.bigm").apply_to(m)`.

### 2.4 Where Each Parameter Is Used

| Parameter | Default | Set to | Used in |
|-----------|---------|--------|---------|
| `m.commitmentPeriodLength` | 1 hr | B | `renewable_curtailment_cost` (line 485) |
| `m.dispatchPeriodLength` | 0.25 hr | B | `renewableSurplusCommitment` (line 1043) |
| `cp.commitmentPeriodLength` | 1 hr | B | `operatingCostCommitment` — fixed cost scaling (lines 1064, 1076) |
| `dp.periodLength` | 1 | B | `generatorCost`, `loadShedCost`, `renewableCurtailmentCost` (lines 577, 585, 572); ramp constraints (lines 885, 898, 944, 980) |

---

## 3. The Time-Scaling Fix (Critical)

### 3.1 The Bug (Pre-Fix)

Three dispatch-level cost expressions computed `MW × $/MWh = $/hr` without converting to `$/period`:

```python
# OLD (wrong for non-1hr periods):
generatorCost     = thermalGeneration × fuelCost           # $/hr
loadShedCost      = loadShed × loadShedCost_param          # $/hr
curtailmentCost   = curtailment × curtailmentCost_param    # $/hr
```

For 1hr periods, $/hr = $/period (coincidence). For 2hr periods, each dispatch covers 2 hours, so cost should be `$/hr × 2hr = $`. Without this, fuel costs are underestimated by `1/B`.

### 3.2 The Fix (Applied)

Multiply each by `b.periodLength`:

```python
# NEW (correct for any period length):
generatorCost     = thermalGeneration × fuelCost × periodLength         # $
loadShedCost      = loadShed × loadShedCost_param × periodLength        # $
curtailmentCost   = curtailment × curtailmentCost_param × periodLength  # $
```

**Backwards compatible:** `periodLength` defaults to 1 (line 1189), so baseline (1hr) results are unchanged.

### 3.3 Changed Lines in `gtep_model.py`

| Line | Expression | Change |
|------|-----------|--------|
| 572 | `renewableCurtailmentCost` | Added `* b.periodLength` |
| 577 | `generatorCost` | Added `* b.periodLength`; removed dead `varCost` return |
| 585 | `loadShedCost` | Added `* b.periodLength` |

### 3.4 What Was NOT Changed (and Why)

| Expression | Why no change needed |
|-----------|---------------------|
| `operatingCostCommitment` fixed costs | Already multiplied by `b.commitmentPeriodLength` (line 1064) |
| `startupCost` | Per-event cost, not per-hour — no time scaling needed |
| `renewableSurplusCommitment` | Already multiplied by `m.dispatchPeriodLength` (line 1043) |
| Ramp constraints | Already multiplied by `b.periodLength` (lines 885, 898, 944, 980) |
| Power balance `flow_balance` | MW = MW balance, no time dimension |
| `capacity_factor` | MW = MW constraint, no time dimension |

---

## 4. Complete Recipe: Adding a New Commitment Period Variant

To create a driver for `B`-hour commitment blocks:

```bash
cp gtep/driver_coal_2hr.py gtep/driver_coal_${B}hr.py
```

Then edit:
1. `BLOCK_HOURS = B`
2. `OUTPUT_DIR = "retirement_allowed_no_extreme_${B}hr_commit"`
3. `solver_options={"LogFile": "basic_logging_${B}hr.log"}`

Create a CRC submit script:
```bash
cp gtep/data/retirement_allowed_no_extreme_half_load_local/submit_job_2hr_commit.py \
   gtep/data/retirement_allowed_no_extreme_half_load_local/submit_job_${B}hr_commit.py
```

Edit the job name and driver path.

### CRC Pre-Flight

- [ ] Patched Egret installed in conda env (`pip install -e ~/GitHub/Egret`)
- [ ] `gen.csv` has no empty rows (`wc -l` matches expected count)
- [ ] Branch is pushed and pulled on CRC
- [ ] Correct conda env in submit script (`conda activate gtep2`)

---

## 5. Interpreting Results

When comparing 1hr vs 2hr vs 4hr results:

| Metric | Expected Behavior |
|--------|-------------------|
| Total operating cost | Should scale consistently (not drop with coarser resolution) |
| Investment decisions | May change — the sensitivity study's main output |
| Retirement decisions | May change — fewer commitment periods = less flexibility |
| Load shedding | May increase — coarser blocks can't match peak demand as well |
| Solve time | Should decrease roughly proportional to block count reduction |

**Red flags** (indicates a bug):
- Operating cost drops by exactly `1/B` → time-scaling not applied
- Operating cost unchanged despite `B > 1` → `periodLength` patch not effective
- Investment decisions identical across all resolutions → model may not be sensitive to temporal resolution (valid finding, but verify cost differences first)

---

## 6. Files Modified

| File | Change | Backwards Compatible? |
|------|--------|----------------------|
| `gtep/gtep_model.py` | `generatorCost`, `loadShedCost`, `renewableCurtailmentCost` × `periodLength` | Yes (`periodLength` defaults to 1) |
| `gtep/driver_coal_2hr.py` | Patch `dispatchPeriodLength` and `periodLength` in addition to `commitmentPeriodLength` | N/A (new file) |
| `gtep/driver_coal_4hr.py` | Same as 2hr driver | N/A (new file) |
