# Plan: Operational Violations Analysis Notebook

**Date:** 2026-05-15
**Location:** `gtep/pcm_analysis/tsa_benchmark_2035/notebooks/operational_violations_2035.ipynb`
**Purpose:** Systematic audit of operational feasibility from the 2035 Prescient PCM simulation.
Does the GTEP-derived fleet actually operate cleanly in a full chronological simulation?

---

## Framing

The GTEP capacity expansion model optimizes investment/retirement decisions using 4 representative days
and a simplified linear cost model. Prescient then replays the resulting fleet over 365 days with full
unit commitment, piecewise heat rates, ramp constraints, and reserve requirements.

**This notebook asks:** What operational violations emerge when the GTEP fleet meets real chronological demand?

These violations matter because they reveal where the GTEP's aggregated representation
(4 days, linear costs, no reserves) fails to anticipate real operational stress.

---

## Available Data

### PCM Output Files (Prescient results)

| File | Key Columns | What It Tells Us |
|------|------------|------------------|
| `overall_simulation_output.csv` | Total load shedding, Total over generation, Total reserve shortfall, Total renewables curtailment | System-wide annual violation totals |
| `hourly_summary.csv` | LoadShedding, OverGeneration, ReserveShortfall, RenewablesCurtailment, Demand, Price | Hourly violation time series + system price |
| `daily_summary.csv` | Load shedding, Over generation, Reserve shortfall, Renewables curtailment, Number on/offs | Daily aggregated violations + cycling counts |
| `bus_detail.csv` | Bus, Demand, Shortfall, Overgeneration, LMP, LMP DA | Per-bus load shedding and over-generation |
| `thermal_detail.csv` | Generator, Dispatch, Dispatch DA, Headroom, Unit State, Unit Cost | Per-gen dispatch, commitment state, available headroom |
| `renewables_detail.csv` | Generator, Output, Output DA, Curtailment | Per-gen renewable curtailment |
| `reserves_detail.csv` | Reserve, Scope, Magnitude, Shortfall, Price, DA Magnitude, DA Shortfall | Reserve requirement vs procurement |
| `line_detail.csv` | Line, Flow, Violation | Per-line flow and thermal limit violations |
| `contingency_detail.csv` | Contingency, Line, Flow, Violation | Post-contingency flow violations |

### PCM Input Files (GTEP-derived fleet)

| File | Key Columns | What It Tells Us |
|------|------------|------------------|
| `gen.csv` | GEN UID, Unit Type, PMax MW, PMin MW, Min Up/Down Time, Ramp Rate, HR curves, Fuel Price | Fleet composition and technical constraints |
| `branch.csv` | UID, From Bus, To Bus, R, X, Cont Rating | Transmission limits that drive congestion |
| `bus.csv` | Bus ID, bus name, lat/lon | Network topology |
| `timeseries_pointers.csv` | Object, Parameter, Data File | Maps generators to time-series profiles |
| Load/wind/solar CSVs | Hourly profiles | Demand and renewable availability |

### Cross-Reference Data

| Source | Use |
|--------|-----|
| `dispatchable_investments.json` | Which generators were installed/retired/extended by GTEP |
| `renewable_investments.json` | GTEP-decided renewable MW capacity |
| GTEP model (`gtep_model.py`) | What constraints GTEP enforced (and which it didn't — reserves disabled, no min up/down) |

---

## Notebook Sections

### Section 0: Setup & Data Loading
- Load gen.csv, results CSVs
- Print fleet summary (gen count by type, total capacity)
- Print simulation overview (days, total demand, peak demand)
- State what violations we're checking and why

### Section 1: System-Level Violation Dashboard
**Source:** `overall_simulation_output.csv` + `hourly_summary.csv`

Headline table:
| Violation | Annual Total | Hours Affected | % of Hours | Peak Value |
|-----------|-------------|----------------|------------|------------|
| Load shedding (MWh) | 0 | 0 | 0% | 0 |
| Over generation (MWh) | 0 | 0 | 0% | 0 |
| Reserve shortfall (MWh) | 0 | 0 | 0% | 0 |
| Renewables curtailment (MWh) | 0 | 0 | 0% | 0 |

Time series plot: 4-panel subplots (load shedding, overgen, reserve shortfall, curtailment) over 365 days.

**Interpretation:** Even if all zeros now, the notebook should explain what each violation *means*
and what would cause it to appear. This becomes the template for future GTEP configurations
that may not be as clean.

### Section 2: Reserve Adequacy Analysis
**Source:** `reserves_detail.csv` + `gen.csv`

- Reserve requirement vs headroom: is the system carrying enough spinning reserve?
- Reserve margin = (online capacity - dispatch) / demand — compute hourly
- Distribution plot of reserve margin (histogram + time series)
- Tightest hours: bottom-10 by reserve margin
- Cross-reference with demand peaks and renewable dips
- GTEP context: reserves are DISABLED in the GTEP model (commented out). Does the fleet
  still meet Prescient's 10% reserve requirement? If yes, it's by construction (over-built fleet).
  If no, that's a gap the GTEP should address.

### Section 3: Transmission Congestion & Line Violations
**Source:** `line_detail.csv` + `branch.csv` + `bus_detail.csv`

- Line flow violations: count, severity, which lines
- Congestion proxy: hours where |flow| > 90% of rating (near-congested)
- Most congested lines (top 10 by hours near limit)
- LMP divergence as congestion signal: hours where max(bus LMP) - min(bus LMP) > threshold
- Negative LMP analysis: which buses, when, why (transmission constraints + renewable surplus)
- Map: if possible, show congested lines on bus network

**Data preview from exploration:**
- 0 line violations in results/ and results_2/
- 1,024 negative LMP bus-hours across 100/123 buses
- LMP range: -$882.91 to $1,000.00
- 42 bus-hours with LMP > $100, 4 with LMP > $500

### Section 4: Generator Operational Constraint Compliance
**Source:** `thermal_detail.csv` + `gen.csv`

Subcheck 4a: **PMin/PMax compliance**
- When online (Unit State=True), verify PMin <= Dispatch <= PMax
- Count violations with 1% tolerance

Subcheck 4b: **Ramp rate compliance**
- |Dispatch(t) - Dispatch(t-1)| <= RampRate × 60 (MW/hr)
- Count violations with 1% tolerance

Subcheck 4c: **Min up/down time compliance**
- Track state transitions (startup/shutdown)
- Verify minimum online duration >= Min Up Time
- Verify minimum offline duration >= Min Down Time
- Count violations
- GTEP context: GTEP has min_up_time and min_down_time parameters but these are
  applied at the commitment period level. With 24hr commitment in GTEP,
  min_up/down time constraints are often non-binding.

Subcheck 4d: **Unit cycling analysis**
- Total starts/stops per generator type
- Average on-time per start
- "Forced cycling" hours: generators cycling on/off within min_up_time windows
- This reveals stress that GTEP's representative-day approach may underestimate

### Section 5: Renewable Integration Quality
**Source:** `renewables_detail.csv` + `gen.csv` + `hourly_summary.csv`

- Curtailment by generator and type (PV, WIND)
- Hours with curtailment > 0
- Curtailment vs demand: when does curtailment happen relative to load?
- Capacity factor realized vs available (from time series profiles)
- "Missing energy": MWh that could have been served by renewables but wasn't
- GTEP context: GTEP uses renewable capacity factors directly from profiles.
  If Prescient curtails renewables the GTEP didn't expect, that's a modeling gap.

### Section 6: Supply-Demand Balance Quality
**Source:** `hourly_summary.csv` + `bus_detail.csv`

- Hourly supply = thermal dispatch + renewable output
- Hourly demand from hourly_summary
- Balance error = supply - demand (should be ~0 everywhere)
- Identify hours with largest imbalance
- Over-generation as a soft violation (excess supply beyond demand + losses)

### Section 7: Price Signal Analysis (Operational Stress Proxy)
**Source:** `hourly_summary.csv` + `bus_detail.csv`

- Price = 0 or near-zero → excess supply, possible over-generation risk
- Price spikes → scarcity, possible unserved energy risk
- Negative prices → congestion + renewable surplus
- Price duration curve (sorted hourly prices)
- Price volatility by quarter and by hour-of-day
- Cross-reference extreme prices with violation events

### Section 8: GTEP vs PCM Constraint Gap Summary
**No new data — synthesis of Sections 1-7**

Table summarizing what GTEP enforces vs what Prescient checks:

| Constraint | In GTEP? | In Prescient? | Violation Found? | Impact |
|------------|----------|---------------|------------------|--------|
| Power balance | Yes (node-level) | Yes (node-level) | — | — |
| Thermal limits | Yes (branch flow) | Yes (line_detail) | — | — |
| Reserve requirement | NO (disabled) | Yes (10% spinning) | — | — |
| Min up/down time | Yes (24hr blocks) | Yes (hourly) | — | — |
| Ramp limits | No | Yes | — | — |
| Renewable curtailment | Penalty only | Yes (dispatch) | — | — |
| PMin/PMax | Yes | Yes | — | — |
| Contingency (N-1) | No | Optional | — | — |

### Section 9: Summary & Recommendations

- Overall feasibility verdict: does the GTEP fleet survive 365 days?
- Identified gaps and their severity
- Which GTEP constraints should be tightened/added?
- Recommendations for next GTEP configuration

---

## Resolved Design Decisions

1. **Config scope:** Both configs (PTDF = results/, btheta = results_2/). Side-by-side throughout.
2. **Extreme scenario:** Include with partial analysis. Every table/plot must annotate extreme runs
   as `[PARTIAL — missing overall_simulation_output.csv]`. Use whatever CSVs are available
   (thermal_detail, bus_detail, etc.) but do not fabricate overall totals.
3. **Contingency analysis:** `contingency_detail.csv` is empty (0 rows). Note as "not configured
   in this Prescient run" and skip. Do not treat as a violation finding.
4. **Threshold choices:**
   - Reserve margin "tight": **< 10%**. Rationale: ERCOT uses 10% as its planning reserve margin
     target. The notebook should explain this choice and note that NERC/other ISOs use 15%.
     Both thresholds are flagged in output (10% = "tight", 15% = "cautionary") but the headline
     uses 10%.
   - Congestion "near limit": > 90% of Cont Rating.
   - Price spike: > $100/MWh flagged, > $500/MWh highlighted.
   - Negative LMP: < $0 flagged (any negative).
5. **Base-year comparison:** Include as **context panel, not apples-to-apples benchmark.**

### Base-Year Comparison Caveat (explain in notebook)

The base-year run (`Prescient_2/results/`) is **not a valid direct comparison** to the 2035 run:

| Dimension | Base Year | 2035 |
|-----------|-----------|------|
| Simulation period | 90 days (Q1 2019) | 365 days (full year 2035) |
| Fleet | 292 gens (13 COAL, 10 HYDRO, 82 WIND, 72 PV) | 278 gens (12 COAL, 0 HYDRO, 69 WIND, 60 PV) |
| Total demand | 83.7 TWh (90-day) | 238.7 TWh (365-day) |
| Peak demand | 60,652 MW | 39,819 MW |
| Load scaling | Original profile | Texas-scaled 2035 growth |
| Fuel prices | Base-year | 2035 projections (fuel_cost3) |

**Why it's still useful:** The base year shows the *pre-GTEP fleet's violation profile* —
load shedding (62 MWh), over-generation (889 GWh!), reserve shortfall (11,712 MWh).
The 2035 fleet has zero of all three. This contrast reveals whether GTEP investment
decisions *improved* operational feasibility, even though the demand/duration differ.

**What the notebook should NOT do:** compute percentage deltas or say "violations reduced by X%"
between base and 2035 — the denominators are incomparable. Instead, present side-by-side
qualitative observations: "base year had over-generation issues; 2035 fleet does not."

---

## Implementation Notes

- Reuse `validation_utils.py` for data loading where possible
- Use `_io.prescient_output_to_df` for consistent Datetime parsing
- All plots: 120 DPI, (12,5) default figsize
- Save summary tables to `tsa_benchmark_2035/results/`
- Gracefully handle missing data (extreme scenario — annotate clearly)
- Compare results/ (PTDF) and results_2/ (btheta) side by side where relevant
- Base-year data: load separately, present in context panels, never mix into 2035 metrics
