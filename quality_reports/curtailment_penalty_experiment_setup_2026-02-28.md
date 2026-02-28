# Curtailment-Penalty Experiment Setup for Prescient PCM

Date: 2026-02-28

## 1. Objective

Implement a reproducible experiment in the current Prescient pipeline to test how curtailment-related penalty settings affect:

- renewable curtailment volume,
- negative LMP frequency and floor hits,
- overgeneration and load mismatch signals.

## 2. What Was Implemented

### 2.1 New experiment runner

Added:

- `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/data/retirement_allowed_no_extreme_half_load/run_curtailment_penalty_experiments.py`

This script:

- reuses your current `btheta` Prescient setup;
- supports `pcm` and `uc_only` modes;
- sweeps penalty/cap cases (`quick` or `benchmark`);
- writes each case to its own output folder under:
  - `Prescient_2/experiments/curtailment_penalty/<mode>/<case_name>`;
- writes `experiment_manifest.json` with full options for reproducibility.

It also carries forward the hydro-safe curtailment reporting patch you already needed for scalar `p_max`.

### 2.2 New analysis summarizer in `pcm_analysis`

Added:

- `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/pcm_analysis/summarize_curtailment_penalty_results.py`

Default behavior:

- reads cases from
  - `../data/retirement_allowed_no_extreme_half_load/Prescient_2/experiments/curtailment_penalty/pcm`
- writes summary to
  - `gtep/pcm_analysis/curtailment_penalty_summary.csv` (when run in `gtep/pcm_analysis`).

Metrics computed per case:

- `lmp_min`, `lmp_max`, `lmp_mean`,
- `negative_lmp_fraction`,
- floor/ceiling cap hit counts,
- total curtailment (from `renewables_detail.csv` and `hourly_summary.csv`),
- total overgeneration/load shedding/reserve shortfall.

### 2.3 New cluster submit helper

Added:

- `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/data/retirement_allowed_no_extreme_half_load/submit_job_curtailment_penalty.py`

This generates and submits an SGE job for the benchmark sweep in `pcm` mode, aligned with your existing `submit_job_*` pattern.

## 3. Why These Penalty Values Were Chosen

Tested benchmark sweep values:

- `300`, `1000`, `2000`, `5000`, `10000` $/MWh (applied consistently to energy/transmission/interface/contingency/reserve penalty thresholds in each case).

Reasoning:

1. `1000` preserves your current baseline behavior.
   - Your active scripts currently use `price_threshold=1000` (e.g., `run_coal_prescient_btheta.py` and `run_coal_prescient_btheta_uc_only.py`).
2. `10000` is Prescient's documented default for `price_threshold`.
   - This serves as an upper reference consistent with the simulator's default design.
3. `2000` and `5000` align with ERCOT-era system-wide offer cap levels used in market design reforms.
   - They provide market-relevant intermediate/high-cap points rather than arbitrary values.
4. `300` provides a conservative low-penalty stress case.
   - It helps quantify how strongly cap tightness drives the observed negative-LMP share and floor clipping.

This range intentionally spans:

- tight cap behavior (`300`),
- your present benchmark (`1000`),
- ERCOT-relevant intermediate/high levels (`2000`, `5000`),
- Prescient default high-cap behavior (`10000`).

## 4. Why This Is a "Curtailment-Penalty" Proxy (and Not Exact)

Your Prescient stack does not expose a direct standalone "renewable curtailment penalty" option in run config.
Instead, it maps configured thresholds into SCED/RUC violation costs (e.g., load mismatch, transmission/interface/contingency, reserve shortfall), which in turn influence dispatch, curtailment, and LMP outcomes.

So this experiment is the correct first-step sensitivity:

- it isolates economically meaningful penalty signals already available in your live pipeline,
- without changing core model equations or data schema.

## 5. How To Run

From:

- `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/data/retirement_allowed_no_extreme_half_load`

Run benchmark PCM sweep:

```bash
python run_curtailment_penalty_experiments.py --mode pcm --case-set benchmark
```

Optional UC-only sweep:

```bash
python run_curtailment_penalty_experiments.py --mode uc_only --case-set benchmark
```

Then summarize into `pcm_analysis`:

From:

- `/Users/yilu/Documents/GitHub/idaes-gtep/gtep/pcm_analysis`

```bash
python summarize_curtailment_penalty_results.py
```

## 6. Expected Interpretation

- If negative LMP frequency and floor hits change strongly with penalty levels, then price-cap/penalty formulation is a major driver of your LMP mismatch vs paper UC.
- If sensitivity is weak, remaining mismatch is more likely dominated by structural differences already identified (renewable treatment, chronology, reserve formulation, two-pass UC pricing method).

## 7. Sources

1. Prescient config and threshold behavior
   - Local code: `/Users/yilu/Documents/GitHub/Prescient/prescient/simulator/config.py`
   - Local code: `/Users/yilu/Documents/GitHub/Prescient/prescient/engine/egret/egret_plugin.py`
   - Docs: https://prescient.readthedocs.io/en/latest/tasks/configure.html
2. Paper UC formulation used for your benchmark comparison (renewable curtailment variable and objective treatment)
   - `/Users/yilu/Documents/development/nd/research/gtep/123_bus_coal/ERCOT_BUS123_base_XC_editeddata/original_data/Data_public_5year/Sample_Codes_SCUC/UC_function.py`
   - `/Users/yilu/Documents/development/nd/research/gtep/123_bus_coal/ERCOT_BUS123_base_XC_editeddata/original_data/Data_public_5year/Sample_Codes_SCUC/Run_SCUC_annual.py`
3. ERCOT cap reference points used to anchor sensitivity values
   - https://www.ercot.com/files/docs/2022/02/03/2._ERCOT_ORM_PUC_Cost_Benefit_Analysis_for_PUC_Workshop_February_3_2022.pdf
4. Publication context on negative prices under high VRE/market conditions
   - Seel, Mills, Wiser (2021), "Impacts of High Variable Renewable Energy Futures on Wholesale Electricity Prices, and on Electric-Sector Decision Making", Lawrence Berkeley National Lab:
     https://eta-publications.lbl.gov/sites/default/files/lbnl-1007064.pdf
