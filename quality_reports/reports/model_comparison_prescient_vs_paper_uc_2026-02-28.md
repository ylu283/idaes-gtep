# Prescient PCM vs Paper SCUC Audit (TX-123BT)

Date: 2026-02-28 (updated)

## 1. Scope

Goal: explain why your Prescient LMPs differ from the paper's UC LMPs, and make the alignment path explicit in practical terms.

Compared:
- Paper model/code/data:
  - `/Users/yilu/Documents/development/nd/research/gtep/123_bus_coal/ERCOT_BUS123_base_XC_editeddata/original_data/Data_public_5year`
  - especially `Sample_Codes_SCUC` and `Sample_Codes_SCUC_HourlyDLR`
- Your Prescient runs/results:
  - `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2`
  - `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/pcm_analysis`

## 2. High-Confidence Quantitative Evidence

### 2.1 LMP sign behavior differs structurally

Paper UC LMP files are nonnegative:
- `Sample_Codes_SCUC/UC_results/Day110/UCcase_lmp.txt`: min 0.0, max 45.2564, neg_frac 0.0
- `Sample_Codes_SCUC_HourlyDLR/UC_results/Day110/UCcase_lmp.txt`: min 0.0, max 46.5146, neg_frac 0.0
- `Sample_Codes_SCUC/UC_results/Day365/UCcase_lmp.txt`: min 12.208, max 39.515, neg_frac 0.0
- `Sample_Codes_SCUC_HourlyDLR/UC_results/Day365/UCcase_lmp.txt`: min 12.208, max 43.3389, neg_frac 0.0

Your Prescient outputs are materially negative:
- `gtep/pcm_analysis/Bus_LMP.csv`: min -1000.0, max 1005.7145, mean -16.99, neg_frac 0.1088
- `gtep/pcm_analysis/Bus_LMP_uc_only.csv`: min -1000.0, max 1000.0, mean -17.92, neg_frac 0.1091

Interpretation: this is a model-design mismatch, not noise.

## 3. Exact Code Evidence for Major Differences

## 3.1 Renewable treatment: paper net-load vs Prescient explicit renewables

### Paper code (exact)

```python
# run_annual_UC(...) in Run_SCUC_annual.py
load_b_t = np.transpose(load_d)
# count wind power
for h in range(24):
    for i in range(len(wind_genidx_list)):
        g_idx = wind_genidx_list[i]
        b_idx = case_inst.gen.bus[g_idx] - 1
        load_b_t[b_idx, h] -= wind_d[i, h]
# count solar power
for h in range(24):
    for i in range(len(solar_genidx_list)):
        g_idx = solar_genidx_list[i]
        b_idx = case_inst.gen.bus[g_idx] - 1
        load_b_t[b_idx, h] -= solar_d[i, h]
```

### Prescient-side code (exact)

```python
# run_coal_prescient_btheta.py
prescient_options = {
    "data_path": "Prescient_2",
    "input_format": "rts-gmlc",
    ...
    "output_directory": "Prescient_2/results_btheta",
    ...
    "compute_market_settlements": True,
    ...
    "day_ahead_pricing": "LMP",
}
Prescient().simulate(**prescient_options)
```

Interpretation: paper removes wind/solar from demand before optimization; Prescient keeps renewable units explicit in market clearing.

## 3.2 Curtailment economics and nodal balance (corrected)

### Paper code (exact)

```python
# UC_function.py (standard SCUC)
model.rnwcur_b_t = Var(model.BUS, model.TIME, domain=NonNegativeReals)

def objfunction(model):
    obj = sum(
        model.gen_cost_P[g] * model.p_g_t[g, t]*BaseMVA + model.gen_cost_NL[g] * model.u_g_t[g, t] + model.gen_cost_SU[g] *
        model.v_g_t[g, t] for g in model.GEN for t in model.TIME)
    return obj

# Renewable curtailment constraint
def rnwcur_f_1(model, b, t):
    if load_b_t[b - 1][t - 1]/BaseMVA >= 0:
        return model.rnwcur_b_t[b, t] == 0
    else:
        return model.rnwcur_b_t[b, t] <= -load_b_t[b - 1][t - 1]/BaseMVA

# Nodal balance
def nodal_balance_f(model, b, t):
    nodal_balance_left = ...
    nodal_balance_right = model.load_b_t[b, t]/BaseMVA + model.rnwcur_b_t[b,t]
    return nodal_balance_left == nodal_balance_right
```

### Prescient-side code (exact)

```python
# run_coal_prescient_btheta.py
"price_threshold": 1000,
"contingency_price_threshold": 100,
"reserve_price_threshold": 5,
```

Additional paper DLR code follows the same mechanism:

```python
# UC_function_DLR.py (hourly DLR)
model.rnwcur_b_t = Var(model.BUS, model.TIME,domain=NonNegativeReals)
...
def rnwcur_f_1(model, b, t):
    if load_b_t[b - 1][t - 1] >= 0:
        return model.rnwcur_b_t[b, t] == 0
    else:
        return model.rnwcur_b_t[b, t] <= -load_b_t[b - 1][t - 1]/BaseMVA
...
def nodal_balance_f(model, b, t):
    ...
    nodal_balance_right = model.load_b_t[b, t]/BaseMVA + model.rnwcur_b_t[b,t]
    return nodal_balance_left == nodal_balance_right
```

Correct interpretation:
- Paper does **not** model renewable curtailment as a direct penalty term in objective.
- Wind/solar are first subtracted from load (`load_b_t` net-load construction in `Run_SCUC_annual.py`/`RunUC_annual_dlr.py`).
- `rnwcur_b_t` is a **bounded nonnegative slack on nodal net-load balance**:
  - forced to zero when bus net load is nonnegative;
  - allowed only up to the magnitude of negative net load.
- So “curtailment” in paper is implemented as balancing relief for net negative load, not as explicit renewable bid/offering economics.

## 3.3 Pricing method: paper two-pass dual pricing vs Prescient market process

### Paper code (exact)

```python
# Run_SCUC_annual.py
UC_case_run1 = build_UC_full(case_inst, load_b_t)
solve_UC(UC_case_run1, "UCresults.pickle", 'UCcase', day_num)
# fixed the u_g_t, solve again and obtain dual variable (electricity prices)
UC_case_run2 = build_UC_full_Run2(case_inst, UC_case_run1, load_b_t)
solve_UC(UC_case_run2, "UCresults_run2.pickle", "UCcase", day_num)
```

```python
# UC_function.py (Run2 objective uses fixed commitment)
def objfunction(model):
    obj = sum(
        model.gen_cost_P[g] * model.p_g_t[g, t]*BaseMVA + model.gen_cost_NL[g] * UC_case.u_g_t[g, t]() + model.gen_cost_SU[g] *
        model.v_g_t[g, t] for g in model.GEN for t in model.TIME)
    return obj
```

```python
# UC_function.py (LMP extraction from nodal balance dual)
nodal_balance_cons = getattr(UC_case, 'nodal_balance_cons')
lmp = UC_case.dual.get(nodal_balance_cons[b,t])
lmp_str += str(lmp/BaseMVA) + ' '
```

### Prescient-side code (exact)

```python
# run_coal_prescient_btheta.py
"compute_market_settlements": True,
"day_ahead_pricing": "LMP",
Prescient().simulate(**prescient_options)
```

Interpretation: paper uses explicit fixed-commitment re-solve for dual prices; Prescient prices come from its integrated RUC/SCED market engine.

## 3.4 Chronology/horizon mismatch

### Paper code (exact)

```python
# Run_SCUC_annual.py
for d in range(dnum_start-1,dnum_end):
    day_num = d + 1
    ... # build one-day data
    UC_case_run1 = build_UC_full(case_inst, load_b_t)
    ...
```

### Prescient-side code (exact)

```python
# run_coal_prescient_btheta.py
"start_date": "01-01-2019",
"num_days": 90,
"sced_horizon": 6,
"ruc_horizon": 36,
"simulate_out_of_sample": True,
```

Interpretation: paper runs daily independent problems; Prescient runs rolling chronology with look-ahead.

## 3.5 Reserve formulation mismatch

### Paper code (exact)

```python
# UC_function.py
def reserve_tot_f(model, g, t):
    reserve_tot_left = sum(model.r_g_t[g_1, t] for g_1 in model.GEN)
    reserve_tot_right = model.p_g_t[g, t] + model.r_g_t[g, t]
    return reserve_tot_left >= reserve_tot_right
model.reserve_tot_cons = Constraint(model.GEN, model.TIME, rule=reserve_tot_f)
```

### Prescient-side code (exact)

```python
# run_coal_prescient_btheta.py
"reserve_factor": 0.1,
```

Interpretation: reserve requirement structure is not equivalent.

## 3.6 Network/rating treatment mismatch

### Paper code (exact)

```python
# Run_SCUC_annual.py
line_annual = np.loadtxt('Line_annual_Dmin.txt')
for l in range(case_inst.branchtotnum):
    case_inst.branch.rateA[l] = line_annual[l][d]
```

Interpretation: paper standard SCUC enforces day-specific line ratings (and has separate hourly DLR workflow). Current Prescient runs use RTS-GMLC branch data path unless explicitly time-varying mapped.

## 4. Impact Ranking: Which Differences Most Likely Drive LMP Divergence

| Rank | Difference | Impact on LMP sign/trend | Confidence | Why |
|---:|---|---|---|---|
| 1 | Renewable representation (net-load vs explicit renewable units) | Very high | High | Directly changes supply-demand balance shape and overgeneration regimes. |
| 2 | Curtailment treatment/economics | Very high | High | Paper uses a bounded net-load slack (`rnwcur_b_t`) with no direct curtailment objective term; Prescient uses penalty-threshold economics in market clearing, which can produce deep negative tails. |
| 3 | Chronology/horizon (daily independent vs rolling 90d/36h) | High | High | Commitment coupling and look-ahead materially alter marginal conditions. |
| 4 | Pricing workflow (paper two-pass dual vs Prescient engine) | High | Medium-High | Price definition/extraction pathway differs, even with similar dispatch. |
| 5 | Price caps/thresholds | Medium-High | High | Observed -1000 floor confirms clipping behavior influences tails and averages. |
| 6 | Reserve formulation | Medium | Medium | Can shift scarcity and dispatch margins, but typically secondary to 1-3. |
| 7 | Line rating treatment (daily/Hourly DLR vs current input handling) | Medium | Medium | Congestion pattern changes can be large but depend on how ratings are loaded. |
| 8 | Solver stack differences | Low-Medium | Medium | Matters, but usually not enough alone to explain sign reversal from all-positive to ~11% negative. |

## 5. What “Change Prescient PCM Toward Their Model” Means (Novice + Deep)

Below each item: concept -> concrete action -> expected LMP effect -> tradeoff.

## 5.1 Make renewables paper-like (net-load form)

- Concept: in paper, wind/solar are not optimized as explicit generators in SCUC; they are subtracted from load first.
- Concrete action:
  1. Build a benchmark input variant where wind/solar are removed from `gen.csv` as market-participating units.
  2. Add their profiles to bus loads by time before Prescient run.
- Expected LMP effect: fewer forced overgeneration events, less negative pricing, shapes closer to paper’s positive LMP behavior.
- Tradeoff: less realistic modern market representation; this is for benchmark matching, not production realism.

## 5.2 Match curtailment behavior more closely

- Concept: paper “curtailment” is a bounded nodal slack applied only when net load is negative (after wind/solar subtraction), with no direct objective penalty term.
- Concrete action:
  1. Use alignment-mode settings that avoid punitive overgeneration behavior.
  2. If needed, implement a custom benchmark variant that mimics free curtailment logic.
- Expected LMP effect: reduces deep negative events and floor hits.
- Tradeoff: may hide true market economics if used outside benchmarking.

## 5.3 Match time structure (daily isolated runs)

- Concept: paper solves one day at a time; your Prescient runs use rolling 90-day chronology.
- Concrete action:
  1. Run day-by-day (or fixed short windows) with no inter-day coupling for benchmark mode.
  2. Keep horizon structure as close as possible to 24h daily optimization.
- Expected LMP effect: commitment and scarcity patterns become more comparable to paper.
- Tradeoff: loses realism in startup/shutdown continuity across days.

## 5.4 Match pricing method as much as possible

- Concept: paper uses two-pass pricing (fix UC commitments, then take duals).
- Concrete action:
  1. For benchmark, prioritize DA-equivalent outputs and minimize RT complexity.
  2. Compare against dual-style price outputs where feasible.
- Expected LMP effect: price interpretation aligns better (especially sign and level).
- Tradeoff: may require custom post-processing or limited-mode runs.

## 5.5 Reduce cap-clipping artifacts

- Concept: your current `price_threshold=1000` creates visible floor hits at -1000.
- Concrete action:
  1. In benchmark mode, test higher thresholds (e.g., 2000/5000/10000).
  2. Track floor-hit fraction as a diagnostics metric.
- Expected LMP effect: less artificial clipping in tails; easier comparison of natural price dynamics.
- Tradeoff: can increase volatility and expose infeasibility/penalty events more strongly.

## 5.6 Align reserve and line-rating assumptions

- Concept: reserve and transmission assumptions differ materially.
- Concrete action:
  1. Use simplified/disabled reserve for first alignment pass, then add paper-like reserve constraints.
  2. Align line rating treatment (daily Dmin first, then hourly DLR variant).
- Expected LMP effect: changes congestion/scarcity hours and trend shape.
- Tradeoff: additional data pipeline work and careful validation required.

## 6. Recommended Alignment Order (Reliable, Low-Risk)

1. Freeze one comparison day (Day110).
2. Switch to paper-like renewable/net-load representation.
3. Use daily isolated run structure.
4. Relax cap-clipping for diagnostics.
5. Compare LMP sign/trend first, magnitude second.
6. Add reserve and line-rating alignment after sign/trend improves.

## 7. Practical Conclusion

Your LMP gap is primarily due to **model formulation and market design assumptions**, not input scale mismatch.

If your objective is benchmark similarity to paper, you should treat this as an alignment exercise with a dedicated “paper-like mode” in Prescient, rather than expecting a modern rolling PCM setup to match paper SCUC prices directly.
