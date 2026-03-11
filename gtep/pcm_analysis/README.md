# PCM Result Analysis

Tools for extracting and analyzing results from Prescient production cost model (PCM) simulations.

## Quick Start

1. Open `prescient_lmp_analysis.ipynb`
2. In Cell 1, set `results_path` to point to your Prescient output directory
3. Run all cells

## Notebook: `prescient_lmp_analysis.ipynb`

Extracts LMP (Locational Marginal Price) and generator dispatch data from Prescient's raw output CSVs into analysis-ready formats.

### Inputs

The notebook reads three files from a Prescient results directory:

| File | Contents |
|------|----------|
| `bus_detail.csv` | Per-bus LMP (real-time and day-ahead), demand, shortfall |
| `thermal_detail.csv` | Per-generator dispatch, unit cost, unit state |
| `renewables_detail.csv` | Per-generator output, curtailment |

### Outputs

| File | Format | Description |
|------|--------|-------------|
| `Bus_LMP.csv` | Wide CSV (Datetime × columns) | Two columns per bus: `{Bus}_LMP` (RT) and `{Bus}_LMP DA` (DA) |
| `Generator_Dispatch.csv` | Wide CSV (Datetime × columns) | Dispatch/output per generator with unit cost, state, curtailment |
| `PCM_result.json` | JSON | Summary stats: mean/median/min/max LMP per bus; total dispatch per generator |

### Configuration

Edit Cell 1 to set the results path. Example for different cases:

```python
# Coal retirement 35-day run
results_path = "/path/to/retirement_allowed_no_extreme_half_load/Prescient_2/results"

# Future 365-day run
results_path = "/path/to/full_year_results/Prescient_2/results"
```

Output files are saved to the notebook's working directory (`output_dir`).

## Data Source Differences

This workflow was adapted from the [RTS-GMLC-PT](https://github.com/GridMod/RTS-GMLC) analysis notebook. Key differences for ERCOT data:

| Aspect | RTS-GMLC | ERCOT (this project) |
|--------|----------|---------------------|
| Bus names | Short names (Abel, Adams...) | Full station names (Tennessee Colony 345, Wheeler 345...) |
| Generator IDs | Descriptive (101_CT_1) | Numeric (1, 2, 3...) |
| Bus count | ~73 | ~123 |
| Generator mapping | Requires `gen_dict.json` | Names read directly from CSVs |
| Simulation year | 2020 | 2035 |

## Adding New Cases

To analyze results from a new PCM simulation:

1. Copy the notebook or open the existing one
2. Change `results_path` in Cell 1 to your new results directory
3. Optionally change `output_dir` to keep outputs separate per case
4. Run all cells

The notebook auto-discovers all buses and generators from the CSV files — no manual name lists needed.

## Notebook: `prescient_lmp_analysis_with_hydro_q1.ipynb`

Compares Q1 LMP and dispatch between hydro-enabled (btheta) and no-hydro baseline simulations.

### Inputs

Reads from two Prescient results directories:
- `results_btheta/` (btheta UC+ED with 10 HYDRO generators)
- `results_btheta_uc_only/` (btheta UC-only with hydro)
- Baseline Q1 data from the original results (no hydro)

### Outputs

| File | Description |
|------|-------------|
| `Bus_LMP_hydro_btheta.csv` | LMP data from btheta UC+ED with hydro |
| `Bus_LMP_hydro_uc_only.csv` | LMP data from btheta UC-only with hydro |
| `Bus_LMP_no_hydro_q1.csv` | Baseline Q1 LMP (no hydro) |
| `Generator_Dispatch_hydro_btheta.csv` | Dispatch from btheta UC+ED with hydro |
| `Generator_Dispatch_hydro_uc_only.csv` | Dispatch from btheta UC-only with hydro |
| `Generator_Dispatch_no_hydro_q1.csv` | Baseline Q1 dispatch (no hydro) |
| `PCM_result_hydro_q1_comparison.json` | Summary stats for hydro Q1 comparison |

### Generator Script

`create_prescient_lmp_analysis_with_hydro_q1.py` programmatically generates the notebook. Run it to recreate from scratch if needed.

## Curtailment-Penalty Sweep

- Run experiments from:
  - `gtep/data/retirement_allowed_no_extreme_half_load/run_curtailment_penalty_experiments.py`
- 5 penalty levels: $300, $1000, $2000, $5000, $10000/MWh
- CRC submit: `submit_job_curtailment_penalty.py`
- Summarize in this folder with:
  - `python summarize_curtailment_penalty_results.py`
  - use `--strict` to fail on incomplete case outputs
- Default experiment input root:
  - `../data/retirement_allowed_no_extreme_half_load/Prescient_2/experiments/curtailment_penalty/pcm`
- Summary outputs:
  - `curtailment_penalty_benchmark_summary.csv` — per-penalty-level aggregated metrics
  - `curtailment_penalty_benchmark_summary.json` — same data in JSON format
  - `curtailment_penalty_timeseries_wide.csv` — time-series data across penalty levels

## Analysis Scripts

| Script | Purpose |
|--------|---------|
| `create_prescient_lmp_analysis_curtailment_penalty.py` | Generates the curtailment penalty analysis notebook |
| `create_prescient_lmp_analysis_with_hydro_q1.py` | Generates the hydro Q1 comparison notebook |
| `summarize_curtailment_penalty_results.py` | Aggregates results across penalty levels |
| `update_notebook.py` | Utility for programmatic notebook updates |

## All Output Data Files

| File | Source |
|------|--------|
| `Bus_LMP.csv`, `Generator_Dispatch.csv`, `PCM_result.json` | Original baseline |
| `Bus_LMP_ptdf.csv`, `Generator_Dispatch_ptdf.csv`, `PCM_result_ptdf.json` | PTDF baseline |
| `Bus_LMP_uc_only.csv`, `Generator_Dispatch_uc_only.csv`, `PCM_result_uc_only.json` | UC-only baseline |
| `Bus_LMP_hydro_btheta.csv`, `Generator_Dispatch_hydro_btheta.csv` | btheta UC+ED with hydro |
| `Bus_LMP_hydro_uc_only.csv`, `Generator_Dispatch_hydro_uc_only.csv` | btheta UC-only with hydro |
| `Bus_LMP_no_hydro_q1.csv`, `Generator_Dispatch_no_hydro_q1.csv` | No-hydro Q1 baseline |
| `PCM_result_hydro_q1_comparison.json` | Hydro Q1 comparison stats |
| `curtailment_penalty_benchmark_summary.csv/.json` | Penalty sweep summary |
| `curtailment_penalty_timeseries_wide.csv` | Penalty sweep time-series |
