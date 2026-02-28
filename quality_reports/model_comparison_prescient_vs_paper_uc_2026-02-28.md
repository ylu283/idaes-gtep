# Prescient PCM vs Paper SCUC Audit (TX-123BT)

Date: 2026-02-28

## 1. Scope

Goal: explain why your Prescient LMPs differ from the paper's UC LMPs (paper LMPs always nonnegative, yours often negative and with different temporal patterns), and identify what to change for benchmark-style alignment.

Compared:
- Paper model/code/data at:
  - `/Users/yilu/Documents/development/nd/research/gtep/123_bus_coal/ERCOT_BUS123_base_XC_editeddata/original_data/Data_public_5year`
  - especially `Sample_Codes_SCUC` and `Sample_Codes_SCUC_HourlyDLR`
- Your Prescient pipelines/results at:
  - `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/data/retirement_allowed_no_extreme_half_load/Prescient_2`
  - `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/pcm_analysis`
  - `/Users/yilu/Documents/development/nd/research/gtep/123_bus_coal/results/retirement_allowed_no_extreme/...`

## 2. High-Confidence Findings (Quantitative)

### 2.1 Dataset scale is matched (not the root cause)

Both have the same network/generator counts and capacity scale:
- 123 buses, 255 branches, 292 generators
- Generation mix matches:
  - thermal gas 113, wind 82, solar 72, coal 13, hydro 10, nuclear 2
- Total Pmax/Pmin also match (~109145.9 MW / 22771.53 MW)

Implication: major LMP differences are primarily **modeling/market-clearing differences**, not gross topology size mismatch.

### 2.2 LMP sign behavior is fundamentally different

Paper SCUC LMP files (`UCcase_lmp.txt`) are nonnegative:
- Day110 standard SCUC: min 0.0, max 45.26, neg_frac 0.0
- Day110 hourly-DLR SCUC: min 0.0, max 46.51, neg_frac 0.0
- Day365 standard SCUC: min 12.208, max 39.515, neg_frac 0.0
- Day365 hourly-DLR SCUC: min 12.208, max 43.339, neg_frac 0.0

Your Prescient LMP distributions are materially negative in both repo and external analysis outputs:
- `gtep/pcm_analysis/Bus_LMP.csv`: neg_frac ≈ 10.88%, min -1000
- `gtep/pcm_analysis/Bus_LMP_uc_only.csv`: neg_frac ≈ 10.91%, min -1000
- external `12mon_no_hydro_without_curtailment/analysis/Bus_LMP.csv`: neg_frac ≈ 11.78%, min -1000

Implication: this is not a hydro-only artifact and not a one-off run issue.

## 3. Formulation and Assumption Differences Driving LMP Divergence

## 3.1 Renewable treatment differs radically

### Paper SCUC

In `Run_SCUC_annual.py`, wind/solar are subtracted from load before optimization (net-load model):
- wind subtraction: lines 58-63
- solar subtraction: lines 64-68

Only conventional generators are modeled as dispatch decision variables (`reg_gen_list`), while wind/solar are not explicit dispatchable generator vars in SCUC.

### Prescient

Prescient keeps renewables as explicit generators with time-series and economic dispatch/curtailment behavior in RUC/SCED.

Why this matters for LMP sign:
- Net-load formulation suppresses many overgeneration price events.
- Explicit renewable + commitment/ramping/network can create overgeneration and negative prices.

## 3.2 Curtailment economics differ

### Paper SCUC

`rnwcur_b_t` (renewable curtailment) is in nodal balance with **no explicit objective penalty**:
- variable defined: `UC_function.py` line 114
- nodal balance uses `+ rnwcur_b_t`: line 191
- objective includes thermal energy + no-load + startup only: lines 117-123

Constraint structure:
- if net load >= 0, curtailment fixed 0: lines 126-129
- if net load < 0, curtailment allowed up to offset: line 130

This setup tends to produce nonnegative/zero duals for nodal balance in many hours.

### Prescient

Prescient market-clearing includes mismatch penalties and threshold-capped prices (`price_threshold=1000` in your run scripts), and can yield negative LMPs (including the -1000 floor events you observe).

## 3.3 Two-pass pricing method in paper vs Prescient market process

### Paper SCUC pricing process

Per day, they solve twice:
1. Full UC (binary commitment)
2. Re-solve with commitment fixed to get dual-based LMP

Evidence:
- pass-1 then pass-2 flow: `Run_SCUC_annual.py` lines 70-74
- pass-2 fixed commitment in objective/constraints via `UC_case.u_g_t[g,t]()`:
  - objective uses fixed u: `UC_function.py` lines 312-313
  - bounds/constraints use fixed u: lines 328, 333, 338
- LMP from nodal balance dual: lines 498-500

### Prescient process

Prescient computes DA/RT outcomes through RUC+SCED machinery, settlement/price rules, reserve handling, and optional forecast uncertainty. This is not equivalent to the paper's explicit two-pass static daily SCUC pricing recipe.

## 3.4 Time-coupling and chronology are different

### Paper SCUC

- Daily independent 24-hour optimization
- No explicit inter-day commitment state carryover in `Run_SCUC_annual.py`
- Startup variable constraint at t=1 relaxed (`v_g_t >= 0`): line 213

### Prescient runs

Your scripts use multi-hour look-ahead with rolling chronology:
- Example (`retirement_allowed_no_extreme_half_load/run_coal_prescient.py`):
  - `sced_horizon=6`, `ruc_horizon=36`, `num_days=90`, `simulate_out_of_sample=True`
- UC-only variant still rolling with `ruc_horizon=36` and reserve factor 0.1

This changes commitment and scarcity patterns materially vs independent daily solves.

## 3.5 Reserve design is not equivalent

### Paper SCUC reserve constraint

Paper uses an atypical reserve constraint for every generator/time:
- `sum(r_g_t over all generators) >= p_g_t[g,t] + r_g_t[g,t]`
- `UC_function.py` lines 156-160

### Prescient

Reserve is controlled by `reserve_factor` and Prescient/Egret reserve machinery.

Your runs commonly use `reserve_factor=0.1`; paper model's reserve mechanism is structurally different.

## 3.6 Network limit treatment differs by scenario

Paper provides two UC variants:
- Standard SCUC: daily line rating (`Line_annual_Dmin.txt`)
- Hourly DLR SCUC: hourly line ratings (`dynamic_rating_result`)

In Prescient runs, line limits come from the RTS-GMLC inputs (typically static branch ratings unless time-varying limits are explicitly mapped in pointers).

Congestion pattern and marginal pricing can shift substantially.

## 3.7 Solver and implementation details mismatch

Paper sample code references `conopt` in `solve_UC`:
- `UC_function.py` lines 423-425

This is not the same solver stack typically used in Prescient production runs (gurobi-based RUC/SCED in your scripts).

Even with same math, solver setup can affect unit commitment behavior and derived prices.

## 4. Why Your LMPs Go Negative While Paper's Stay Nonnegative

Primary mechanism (most important):
1. Paper net-load + free curtailment in nodal balance tends to avoid negative dual pricing regimes.
2. Prescient explicit renewable and market-clearing penalties/settlement logic allows negative prices under overgeneration/congestion/commitment inflexibility.
3. Your `price_threshold=1000` clips extremes and creates visible -1000 floor observations.

So negative LMPs in Prescient are expected under this formulation stack and are not, by themselves, evidence of a bug.

## 5. Benchmark Alignment Plan (to approximate paper UC behavior)

Priority order: top items have biggest impact on LMP comparability.

### Tier 1: Match economic structure first

1. Build a "paper-equivalent" Prescient input variant where wind/solar are converted to net load (paper style), not explicit renewable generators.
   - Remove wind/solar generators from `gen.csv` and associated timeseries pointers.
   - Add their profiles into bus loads by bus/time before run.
2. Implement a curtailment treatment equivalent to paper's free net-load relief at negative net load.
   - If exact equivalent is hard in Prescient, at least avoid punitive overgeneration behavior that forces deep negative prices.

### Tier 2: Match chronology and horizons

3. Run one day at a time with isolated daily solves (no inter-day carryover), mirroring paper `run_annual_UC(..., day, day)` behavior.
4. Set horizons to paper-like structure for benchmark mode:
   - daily 24-hour problem
   - avoid rolling 36h/48h multi-day coupling for benchmark comparison.

### Tier 3: Match network and reserve assumptions

5. Use daily `Dmin` line ratings first (paper standard SCUC), then hourly DLR as a separate benchmark.
6. Align reserve formulation/targets:
   - either disable reserve for first benchmark,
   - or implement a reserve requirement mathematically equivalent to paper model for a second benchmark.

### Tier 4: Price rule and caps

7. For benchmarking, increase or relax price caps (currently +/-1000) so cap clipping does not dominate comparisons.
8. Compare DA-only LMP first (paper is day-ahead SCUC-derived dual), then add RT/settlement complexity later.

## 6. Recommended Experiment Matrix

Run these in order and compare against paper Day110/Day365 UCcase_lmp:

1. Baseline paper re-run (paper code) for day 110 and 365 to confirm reference values.
2. Prescient current (as-is) day 110 only.
3. Prescient with no forecast errors + UC-only + daily-isolated horizon.
4. Prescient with net-load replacement of renewables (paper-style).
5. Prescient with aligned line limits (daily Dmin).
6. Prescient with adjusted reserve settings.

Track metrics each run:
- LMP min/max/mean
- negative LMP fraction
- hourly profile at representative buses
- congestion frequency

Stop once LMP sign and trend broadly match paper; then tune magnitude.

## 7. Practical Conclusion

You should not expect Prescient PCM to match paper UC LMPs without explicit alignment of:
- renewable representation,
- curtailment economics,
- chronology/horizon,
- reserve rules,
- line limit time dependence,
- pricing cap behavior.

Given current evidence, your LMP deviation is primarily due to **modeling design differences**, not bad data mapping.

