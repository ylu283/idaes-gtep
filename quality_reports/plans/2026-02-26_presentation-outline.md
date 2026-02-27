# Presentation Outline: GTEP PCM Analysis Update

**Duration:** 15-20 min (with discussion)
**Format:** Slides + key notebook figures
**Narrative:** Data pipeline -> Generally positive LMP results -> Q2/Q4 spike question -> Next steps

**Results:** `12mon_no_hydro_with_curtailment/` (btheta UC+ED, 365-day, 2035 coal retirement scenario)
**Notebook:** `results_analysis/prescient_lmp_analysis_executed.ipynb`

---

## Act 1: ERCOT Data & Processing (~5 min)

### Slide 1 — TX-123BT Test Case

**Key points:**
- 123-bus ERCOT backbone transmission network (from public dataset)
- 292 generators: Nuclear, Gas (CT), Coal, Wind (82), Solar (72), Hydro
- 188 transmission lines with impedance and rating data
- 5-year hourly profiles: load (per bus), wind, solar (per plant)
- 8 weather zones: COAST, EAST, FWEST, NCENT, NORTH, SCENT, SOUTH, WEST

**Show:** Network topology map or bus/zone diagram (if available from paper or dataset)

**Speaker notes:**
> "This is the TX-123BT test case — a 123-bus backbone model of the ERCOT system used in Lu et al. 2025. It has 292 generators across 6 fuel types and 188 transmission lines. The public dataset provides 5 years of hourly load, wind, and solar profiles."

---

### Slide 2 — Data Processing Pipeline

**Key points:**
- Raw data: `Data_public_5year/` — Bus_data.csv, Line_data.csv, Generator_data.xlsx, daily load/wind/solar .txt files
- Processing notebook: `demo_processing_XC.ipynb`
- Converts raw ERCOT format -> Prescient-ready CSVs

**Key assumptions:**
| Parameter | Value |
|-----------|-------|
| Gas fuel price | $2.29/MMBTU |
| Coal fuel price | $1.78/MMBTU |
| Nuclear fuel price | $0.81/MMBTU |
| Gas min up/down | 2h / 1h |
| Coal min up/down | 12h / 12h |
| Nuclear min up/down | 48h / 48h |
| Cost curve segments | 4 (at 30%, 50%, 70%, 100% of PMax) |

**Output files:** gen.csv, bus.csv, branch.csv, DAY_AHEAD/REAL_TIME load/wind/solar CSVs, timeseries_pointers.csv

**Speaker notes:**
> "I convert the raw ERCOT data into Prescient's input format using a processing notebook. The key assumptions are fuel prices, generator flexibility parameters, and piecewise-linear cost curves with 4 segments. i use 2019 to benchmark the paper's work
---

### Slide 3 — GTEP to Prescient Handoff

**Key points:**
- GTEP Pyomo model solves investment/retirement decisions for 2035
- `output_to_prescient.ipynb` takes GTEP solution -> filters generator fleet
- Coal retirement scenario: 282 generators remain (10 coal retired, no hydro in this config)
- Prescient runs 365-day btheta UC+ED on CRC cluster
  - B-theta DC power flow for both RUC and SCED
  - 48h RUC horizon, 24h SCED horizon
  - Perfect foresight (no forecast error)

**Show:** Simple flow diagram: `GTEP model -> investment decisions -> Prescient simulation -> LMP analysis`

**Speaker notes:**
> "The GTEP model decides which generators to build, extend, or retire. I filter the fleet to the invested generators and pass it to Prescient, which runs a full 365-day unit commitment and economic dispatch simulation on CRC. This particular run uses B-theta DC power flow."

---

## Act 2: PCM Results — Generally Positive LMP (~5 min)

### Slide 4 — Annual LMP Summary

**Key points:**
- Load-weighted system LMP: **$24.73/MWh** (annual average)
- Total demand: 383.8 TWh
- Generation cost: $1.52B
- 10% of bus-hours have negative LMP
  - Concentrated in wind-heavy zones (NORTH, FWEST)
  - Physical: renewable oversupply behind transmission constraints
  - However, in the paper, there's no negative LMP

**Show:** Full-year LMP time series from **Cell 21** (Sec 9.1) — shows daily pattern with seasonal variation

**Speaker notes:**
> "The annual load-weighted LMP is about $25/MWh — generally positive. About 10% of bus-hours show negative prices, but these are concentrated in wind-heavy zones in north and far-west Texas where transmission is constrained. This is physically consistent behavior, not a modeling error."

---

### Slide 5 — Quarterly Breakdown

**Key points:**

| Quarter | Load-Wt LMP ($/MWh) | Character |
|---------|---------------------|-----------|
| Q1 (Jan-Mar) | $1.3 | Low demand, moderate wind |
| Q2 (Apr-Jun) | $3.0 | Spring shoulder, high renewables |
| Q3 (Jul-Sep) | **$57.0** | Summer peak, drives annual avg |
| Q4 (Oct-Dec) | $8.8 | Fall transition |

- Q3 (summer) dominates the annual average — peak cooling demand meets tight supply
- Q1 and Q2 are near-zero due to renewable oversupply in shoulder seasons

**Show:** Quarterly LMP profiles from **Cell 55** (Sec 10.7, Fig 10a-d) — 2x2 subplot showing hourly patterns per quarter

**Speaker notes:**
> "Breaking it down by quarter: Q3 summer is by far the highest at $57/MWh, which makes sense — peak cooling demand. Q1 and Q2 shoulder seasons are near-zero because wind and solar output is high relative to demand. Q4 falls in between."

---

### Slide 6 — Spatial LMP Pattern

**Key points:**

| Zone | Mean DA LMP | % Negative Hours |
|------|-------------|------------------|
| NORTH | -$241.7 | 41.8% |
| FWEST | -$135.7 | 32.6% |
| WEST | -$41.5 | 28.0% |
| EAST | +$11.2 | 1.6% |
| COAST | +$11.8 | 0.3% |
| SCENT | +$11.9 | 4.9% |
| SOUTH | +$13.7 | 2.4% |
| NCENT | +$60.0 | 5.0% |

- Clear spatial divide: wind-heavy west/north vs load-center east/south
- Transmission congestion creates price separation

**Show:** Zone-level table from **Cell 23** (Sec 9.2) AND/OR nodal scatter from **Cell 59** (Sec 10.9, normal day Hour 15)

**Speaker notes:**
> "There's a clear spatial pattern. The NORTH and FWEST zones — where most wind capacity is — have deeply negative average LMPs because wind output can't fully export through constrained transmission lines. Load centers like COAST, EAST, and NCENT see positive prices. This congestion-driven price separation is expected."

---

### Slide 7 — Benchmarking vs Lu et al. 2025

**Key points:**
- Paper: 2019 SCUC on same TX-123BT network, all-positive LMPs ($10-220/MWh)
- Our run: 2019 coal, wider LMP range (-$1000/MWh to +$1395/MWh)

| Aspect | Aligned? | Details |
|--------|----------|---------|
| Network topology | Yes | Same 123-bus, 188-line backbone |
| Wind/solar profiles | Yes | Same temporal patterns |
| Congestion count | Yes | ~6-7 avg congested lines |
| LMP levels | **No** | Ours much wider (expected: different fleet, year) |
| Generator fleet | Partial | 282 vs 292 units (no hydro) |

**Speaker notes:**
> "Comparing against the paper's 2019 results: the topology, renewable profiles, and congestion patterns align well. LMP levels are different, which is expected — we're looking at a 2035 scenario with coal retirement and aggressive renewable expansion. The question is whether the *specific* differences are all scenario-driven, or if some are model artifacts."

---

## Act 3: The Q2/Q4 Question & Next Steps (~5 min)

### Slide 8 — Q2 and Q4: Hourly Price Spikes

**Key points:**
- Overall quarterly averages are positive and reasonable
- But: hourly spikes far exceed paper benchmark bands
  - Q2: spikes up to **+$347/MWh** vs paper's $16-55 range
  - Q4: spikes up to **+$320/MWh** vs paper's $17-40 range
- Paper Table VI defines trough/normal/peak price ranges — our spikes blow through the peak ceiling
- Most hours are within or below paper ranges, but the spikes are extreme

**Show:** **Cell 55** (Sec 10.7) quarterly plots with paper benchmark bands overlaid — the spikes are visually obvious where hourly LMP lines shoot above the green shaded paper-range bands

Also show: **Cell 66** (Sec 10.12, Fig 14) — Q2 normal-day hourly LMP with paper benchmark, showing where our curve exceeds paper's $18-19/MWh

**Speaker notes:**
> "Here's the key question. The quarterly averages look fine — generally positive, seasonally reasonable. But when we look at the hourly resolution, Q2 and Q4 show price spikes well above what the paper reports. The paper's Q2 peak is around $55/MWh; we're hitting $347. These aren't just a few outlier buses — they show up in the system-level weighted average. I want to understand whether this is purely from our different scenario, or if there's something in the model formulation causing it."

---

### Slide 9 — Next Steps

**Key points:**
1. **Investigate Pyomo model formulation for Q2/Q4 spikes**
   - Examine cost expression and generator constraints
   - Check what commitment decisions are made during spike hours
   - Compare our formulation against paper's original SCUC model
2. **Spring negative prices** (Mar/Apr/May)
   - Still present in the whole-year run
   - Will investigate after Pyomo model review

**Speaker notes:**
> "My next step is to go through the paper's original Pyomo SCUC model and compare it against our Prescient configuration. I want to understand what's driving these hourly spikes — is it the generation fleet composition after coal retirement, or is there a modeling difference? I also still have negative prices in spring months, but I'll address that after the Pyomo review. The goal is a clear attribution: scenario effect vs model artifact."

---

## Summary: The One-Sentence Story

> "Our 365-day btheta UC+ED simulation of a 2035 coal-retirement scenario on the TX-123BT system produces generally positive load-weighted LMPs ($24.73/MWh annual), but Q2 and Q4 show hourly price spikes that exceed paper benchmarks, motivating a closer look at the Pyomo model formulation."

---

## Figure Reference Quick Sheet

| Cell | Section | Figure | Use on Slide |
|------|---------|--------|-------------|
| 21 | 9.1 | Full-year LMP DA time series (all buses) | Slide 4 |
| 23 | 9.2 | Zone-level LMP summary table | Slide 6 |
| 55 | 10.7 | **Fig 10a-d: Quarterly hourly LMP with paper bands** | **Slides 5, 8** |
| 57 | 10.8 | Paper Table VI price ranges (printed) | Slide 8 (reference) |
| 59 | 10.9 | Nodal LMP scatter, Q2 normal day, Hour 15 | Slide 6 |
| 61 | 10.10 | Nodal LMP scatter, peak day, Hour 15 | (backup) |
| 66 | 10.12 | **Fig 14: Q2 normal-day hourly system LMP vs paper** | **Slide 8** |
| 69 | 10.12b | Alt Fig 10a-d using hourly_summary Price | Slide 5 (alt) |
