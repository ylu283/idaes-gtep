# Commitment Period Sensitivity: Design & Correctness Report

**Date:** 2026-04-30
**Branch:** commitment_period

---

## 1. Background

The GTEP model uses a nested temporal hierarchy:

```
Investment Stage (5 years)
  └─ Representative Period (1 day = 24 hours)
       └─ Commitment Period (default: 1 hour each, 24 total)
            └─ Dispatch Period (default: 0.25 hours each, 4 per commitment)
```

The commitment period sensitivity study tests whether coarser commitment resolution (2hr, 4hr) yields materially different investment/retirement decisions, trading solution accuracy for faster solve times.

---

## 2. Model Cost Structure (How Time Enters)

### 2.1 Objective Function Chain

```
minimize: Σ_stage [ investmentCost + operatingCostInvestment + curtailmentCost ]

operatingCostInvestment = investmentFactor × Σ_rp Σ_cp [
    weights[rp] × operatingCostCommitment[cp]
]

operatingCostCommitment = 
    Σ_dp [ operatingCostDispatch[dp] ]                          ... (A) variable costs
  + Σ_gen [ fixedCost[gen] × commitmentPeriodLength × onoff ]   ... (B) fixed costs
  + Σ_gen [ startupCost[gen] × startup_binary ]                 ... (C) startup costs

operatingCostDispatch = generationCostDispatch + loadShedCostDispatch + curtailmentCostDispatch

generationCostDispatch = Σ_gen [ thermalGeneration[gen] × fuelCost[gen] ]
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                         MW × $/MWh = $/hr  (POWER × PRICE, not ENERGY × PRICE)
```

### 2.2 Where Time Scaling Happens (and Doesn't)

| Cost Component | Formula | Time factor | Correct for non-1hr? |
|---|---|---|---|
| Fixed cost (B) | `fixedCost × commitmentPeriodLength × binary` | `commitmentPeriodLength` ✅ | Yes |
| Startup cost (C) | `startupCost × binary` | None (per-event) ✅ | Yes |
| Fuel cost (A) | `thermalGeneration × fuelCost` | **None** ❌ | **No** — missing `× dispatchPeriodLength` or equivalent |
| Load shed cost | `loadShed × loadShedCost` | **None** ❌ | **No** — same issue |
| Curtailment cost | `curtailment × curtailmentCost` | **None** ❌ | **No** — same issue |
| Renewable surplus | `dispatchPeriodLength × renewableSurplusDispatch` | `dispatchPeriodLength` ✅ | Only if `dispatchPeriodLength` is correctly set |

### 2.3 Why Baseline (1hr) Works by Coincidence

In the baseline configuration:
- `num_commit=24`, `commitmentPeriodLength=1hr`
- `num_dispatch=1`, `dispatchPeriodLength=0.25hr` (but `renewableSurplusCommitment` is the only place that multiplies by it)
- Each dispatch period is implicitly 1 hour (1 commitment = 1 dispatch = 1 hour)
- `generatorCost = MW × $/MWh` = $/hr, and since the period is 1hr, the value in $/hr equals the value in $

The implicit assumption "1 period = 1 hour" is baked into the model. Any deviation breaks fuel/shed/curtailment cost accounting.

---

## 3. Two Approaches to Coarser Commitment

### 3.1 Approach A: Fewer Dispatches, Wider Periods

```
Representative Period (24 hours)
  └─ 12 Commitment Periods × 2hr each
       └─ 1 Dispatch Period × 2hr each
```

**Parameters:**
```python
num_commit = 12
num_dispatch = 1
commitmentPeriodLength = 2    # patch after create_model()
dispatchPeriodLength = 2      # MUST also patch (default 0.25)
```

**Total decision variables per rep-day:** 12 commitment × 1 dispatch = **12 dispatch periods**
(vs. 24 in baseline → 50% reduction)

**Pros:**
- Genuinely reduces problem size — fewer binary commitment variables AND fewer continuous dispatch variables
- Faster solve time (the whole point of the study)
- Simpler data aggregation (24→12 values)

**Cons:**
- Loses within-block dispatch variation (2hr load/renewable average masks peaks)
- `generatorCost` must be multiplied by `dispatchPeriodLength` (=2) to get correct $/period — **requires model fix**
- Same fix needed for `loadShedCost` and `curtailmentCost`

**Required model fix for Approach A:**
```python
# gtep_model.py, in add_dispatch_variables():
@b.Expression(m.thermalGenerators)
def generatorCost(b, gen):
    return b.thermalGeneration[gen] * i_p.fuelCost[gen]  # currently $/hr
    # Should be:
    # return b.thermalGeneration[gen] * i_p.fuelCost[gen] * b.periodLength
    # where periodLength = dispatchPeriodLength for this dispatch block
```

But `b.periodLength` (line 1189) is hardcoded `default=1`, not linked to `dispatchPeriodLength`. This is a second issue.

**Workaround without model changes:**
Patch `b.dispatchPeriod[dp].periodLength` to `BLOCK_HOURS` for each dispatch period after `create_model()`, and multiply `generatorCost` expression by `periodLength` in the model.

### 3.2 Approach B: Same Dispatches, Grouped into Commitments

```
Representative Period (24 hours)
  └─ 12 Commitment Periods × 2hr each
       └─ 2 Dispatch Periods × 1hr each
```

**Parameters:**
```python
num_commit = 12
num_dispatch = 2              # 2 hourly dispatches per 2hr commitment block
commitmentPeriodLength = 2    # patch after create_model()
dispatchPeriodLength = 1      # patch from default 0.25 to 1hr
```

**Total decision variables per rep-day:** 12 commitment × 2 dispatch = **24 dispatch periods**
(same as baseline — no reduction in continuous variables)

**Pros:**
- Preserves hourly dispatch resolution — no data aggregation needed for load/renewable p_max
- Only commitment decisions are coarser (on/off every 2hr instead of every 1hr)
- `generatorCost` per dispatch period is still $/hr × 1hr = $ — works if `periodLength=1`
- More faithful to the physical system (load peaks within 2hr blocks are captured)

**Cons:**
- Does NOT reduce dispatch variable count — solve time reduction comes only from fewer binary commitment variables
- Still needs `dispatchPeriodLength` fix (0.25 → 1.0) for `renewableSurplusCommitment`
- Data indexing becomes trickier: `p_load["values"]` has 24 entries but commitment periods are 1-12, so `values[commitment_period - 1]` indexing breaks — **loads must be re-indexed to dispatch periods, not commitment periods**

**Data indexing problem with Approach B:**

The model loads data at commitment period level (line 1148):
```python
m.md.data["elements"]["load"][load_n]["p_load"]["values"][commitment_period - 1]
```

With 24 hourly values and 12 commitment periods, `values[11]` is the max index — hours 12-23 are lost. To use Approach B correctly, load and renewable p_max data must be indexed at the **dispatch** level, not the commitment level. This requires model changes to `commitment_period_rule()`.

---

## 4. Comparison

| Dimension | Approach A | Approach B |
|-----------|-----------|-----------|
| Commitment variables (binary) | 12/day | 12/day |
| Dispatch variables (continuous) | **12/day** | 24/day |
| Problem size reduction | **~50%** | ~0% (binary only) |
| Data aggregation needed | Yes (24→12) | No |
| Hourly resolution preserved | No | **Yes** |
| Model changes required | `generatorCost` × time | Load/p_max indexing at dispatch level |
| `dispatchPeriodLength` fix | Set to BLOCK_HOURS | Set to 1hr |
| Sensitivity study validity | Tests commitment + dispatch coarsening together | **Isolates commitment coarsening** |

---

## 5. Recommendation

**For the commitment period sensitivity study, Approach A is the right choice** because:

1. The research question is "does coarser temporal resolution change investment decisions?" — Approach A tests this directly by reducing both commitment and dispatch granularity.
2. Approach B doesn't reduce problem size much — it only removes binary variables but keeps all continuous variables, so solve time improvement is marginal.
3. Approach A is simpler to implement: aggregate data from 24→N values, adjust period lengths.

**But Approach A requires fixing the time-scaling bug.** The cleanest fix:

```python
# After create_model(), patch dispatch period lengths:
for stage in m.stages:
    i_blk = m.investmentStage[stage]
    for rp in i_blk.representativePeriods:
        r_blk = i_blk.representativePeriod[rp]
        for cp in r_blk.commitmentPeriods:
            cp_blk = r_blk.commitmentPeriod[cp]
            for dp in cp_blk.dispatchPeriods:
                cp_blk.dispatchPeriod[dp].periodLength = BLOCK_HOURS
```

Then also patch `m.dispatchPeriodLength = BLOCK_HOURS` for `renewableSurplusCommitment`.

This still leaves `generatorCost` without time scaling. Three options:

1. **Model fix** (best): multiply `generatorCost` by `b.periodLength` in `gtep_model.py`
2. **Cost scaling in driver** (fragile): multiply `fuelCost` by `BLOCK_HOURS` before model creation — but this conflates fuel price with temporal resolution
3. **Accept the approximation** (if aware): document that fuel costs are per-period not per-hour, and compare 1hr vs 2hr vs 4hr results knowing this bias exists — valid if you only care about relative investment decisions, not absolute cost magnitudes

---

## 6. Pre-Flight Checklist (Before Re-Submitting Jobs)

- [ ] Install patched Egret in `gtep2` on CRC: `cd ~/GitHub/Egret && pip install -e .`
- [ ] Decide Approach A or B
- [ ] Fix `dispatchPeriodLength` and `periodLength` patching in driver
- [ ] Fix or document `generatorCost` time-scaling gap
- [ ] Verify `gen.csv` in `123_Bus_Coal/` has no NaN rows (581 rows, 289 with NaN in GEN UID)
- [ ] Test locally with small instance before CRC submission
