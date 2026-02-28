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

## Curtailment-Penalty Sweep (Current)

- Run experiments from:
  - `gtep/data/retirement_allowed_no_extreme_half_load/run_curtailment_penalty_experiments.py`
- Summarize in this folder with:
  - `python summarize_curtailment_penalty_results.py`
  - use `--strict` to fail on incomplete case outputs
- Default experiment input root:
  - `../data/retirement_allowed_no_extreme_half_load/Prescient_2/experiments/curtailment_penalty/pcm`
- Default summary output:
  - `curtailment_penalty_summary.csv`
