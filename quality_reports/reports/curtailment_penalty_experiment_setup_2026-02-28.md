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
- `Prescient_2/experiVments/curtailment_penalty/<mode>/<case_name>`;
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

## 4.1 How Your Prescient Model Realizes Curtailment

In your current Prescient PCM pipeline, curtailment is realized through dispatch feasibility and violation-penalty economics, not through a single explicit "renewable curtailment penalty" input.

Practical mechanism in your setup:

1. Renewable availability and dispatch limits are enforced by Prescient/Egret model structure.
2. SCED/RUC balances and network constraints are solved with configured price/violation thresholds.
3. When surplus energy cannot be absorbed/exported economically, renewable output can be curtailed and tracked in:
   - `renewables_detail.csv` (`Curtailment`)
   - `hourly_summary.csv` (`RenewablesCurtailment`)
4. Threshold settings (`price_threshold`, transmission/interface/contingency/reserve thresholds) strongly shape LMP tails and curtailment/overgeneration outcomes.

This is why the sweep is labeled curtailment-penalty *proxy*: it tunes economic penalty environment that drives curtailment behavior, rather than toggling a dedicated standalone curtailment-cost parameter.

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

## 6.2 Results Update from `prescient_lmp_analysis_curtailment_penalty.ipynb` (2026-03-11)

Common comparison window used across all five cases:
- `2019-01-01 00:00:00` to `2019-03-31 23:00:00`

| Case | LMP Min | LMP Max | Negative LMP Fraction | Floor-Hit Fraction | Weighted LMP ($/MWh) | Curtailment (MWh) | OverGeneration (MWh) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `penalty_300` | -300 | 382.18 | 9.62% | 1.52% | 9.79 | 118,560.19 | 888,328.44 |
| `penalty_1000` | -1000 | 1273.72 | 10.51% | 1.50% | 3.96 | 124,325.36 | 889,003.40 |
| `penalty_2000` | -2000 | 2549.63 | 11.43% | 1.51% | -7.91 | 125,040.34 | 888,986.03 |
| `penalty_5000` | -5000 | 6373.67 | 11.91% | 1.49% | -39.57 | 121,351.43 | 889,606.53 |
| `penalty_10000` | -10000 | 12749.61 | 12.80% | 1.49% | -88.35 | 123,327.86 | 888,692.76 |

Key findings:

1. Larger penalty caps materially widen price tails and increase negative-LMP share.
2. Floor-hit fraction stays around ~1.5%, indicating persistent clipping behavior across cap levels.
3. Load-weighted LMP becomes increasingly negative as cap increases (from `+9.79` at 300 to `-88.35` at 10000).
4. Overgeneration remains high and nearly flat (~888-890 GWh), so cap tuning alone is not removing structural surplus conditions.
5. This supports using penalty sweep as diagnostics, while prioritizing structural alignment steps for paper benchmarking.

## 6.1 Debug Update (2026-02-28)

CRC log `ERCOT_curtailment_penalty_pcm.o269980` showed a setup failure before optimization:

- `ValueError: key 'name' not defined for ConfigDict`

Root cause:

- case metadata key `name` was passed into `Prescient().simulate(**options)` as if it were a simulator option.

Fix implemented:

- sanitize case options so metadata keys are excluded from Prescient kwargs;
- persist per-case status/error in `experiment_manifest.json`;
- add `--continue-on-error` to complete remaining cases even if one fails.

Recommended rerun command:

```bash
python run_curtailment_penalty_experiments.py --mode pcm --case-set benchmark --continue-on-error
```

Then summarize:

```bash
python summarize_curtailment_penalty_results.py --strict
```

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
