# 2035 PCM Anomalous Findings

**Date:** 2026-05-21
**Branch:** idaes_coal2

## Notebooks Analyzed

| Notebook | Location | Cells | Scope |
|----------|----------|-------|-------|
| Operational Violations | `tsa_benchmark_2035/notebooks/operational_violations_2035_executed.ipynb` | 33 | Violation audit: load shedding, reserves, congestion, compliance, curtailment, prices |
| Generator Profitability | `tsa_benchmark_2035/notebooks/generator_profitability_2035_executed.ipynb` | 29 | Economic audit: revenue, cost, profit, uplift, infra-marginal rent |

## Run Configurations

| Run | Config | Duration | Status |
|-----|--------|----------|--------|
| no_extreme_A | PTDF (results/) | 365 days | Full year |
| no_extreme_B | btheta (results_2/) | 365 days | Full year |
| extreme_A | PTDF (extreme/base/results/) | 69 days | PARTIAL |
| extreme_B | btheta (extreme/base/results_2/) | 69 days | PARTIAL |
| base_year | PTDF (Prescient_2/results/) | 90 days Q1 | Context only — not comparable |

---

## A. Hard Violations — No-Extreme Fleet (all PASS)

All hard violation checks pass with zeros for the full-year no-extreme runs.

| Check | Cell | Result |
|-------|------|--------|
| Load shedding | violations Cell 5 | 0 MWh, 0 hours |
| Over-generation | violations Cell 5 | 0 MWh, 0 hours |
| Reserve shortfall | violations Cell 10 | 0 hours RT, 0 hours DA |
| Renewable curtailment | violations Cell 21 | 0 GWh, 0 hours |
| Line violations | violations Cell 12 | 0 violations / 2.2M line-hours |
| PMin/PMax compliance | violations Cell 16 | PASS (0 violations) |
| Ramp rate compliance | violations Cell 17 | PASS (0 violations) |
| Min up/down time | violations Cell 18 | PASS (0 violations) |
| Supply-demand balance | violations Cell 23 | 0 MW imbalance |

**Interpretation:** The GTEP-derived 2035 fleet is operationally feasible under no-extreme conditions. All Prescient hard constraints are satisfied for the full year.

---

## B. Extreme Scenario Anomalies (PARTIAL — 69 days)

The extreme scenario shows real violations, indicating fleet stress under extreme load/renewable conditions.

### B1. Reserve Shortfall (violations Cell 10)
- **extreme_A:** 2 RT shortfall hours. Worst: 82 MW shortfall at 2035-02-21 H15 (required 2,423 MW)
- **extreme_B:** 2 RT + 7 DA shortfall hours. Worst: **527 MW shortfall** at 2035-02-07 H11 (required 2,484 MW)

### B2. Reserve Margin (violations Cell 9)
- **extreme_A:** min margin 9.7%, 2 hours < 10% threshold
- **extreme_B:** min margin **7.9%**, 2 hours < 10%, 46 hours < 15% (cautionary)

### B3. Over-Generation (violations Cell 23)
- 344-351 hours with supply-demand imbalance > 1 MW
- Peak: **+2,202 MW (+9.0%)** over demand
- 326 hours with imbalance > 100 MW

### B4. Load Shedding (violations Cell 32)
- **extreme_B only:** 4 load shedding hours (btheta config)
- extreme_A: 0 hours

### B5. NUC and COAL Cycling (violations Cell 19)
- **NUC:** 14-17 starts in 69 days (vs 0 starts in 365-day no-extreme — baseload should never cycle)
- **COAL:** 390-415 starts in 69 days = 5.7-6.0 starts/gen/day (vs 0.3 starts/gen/day in no-extreme)
- CT cycling rate also elevated: 60+ starts/day fleet-wide (vs 20/day no-extreme)

**Interpretation:** The extreme scenario stresses the fleet enough to force NUC cycling, COAL rapid cycling, and actual reserve/load shedding violations. A full-year extreme run is needed for definitive assessment.

---

## C. Congestion Stress Signals (no-extreme)

No hard line violations, but significant congestion stress exists.

### C1. Near-Congestion (violations Cell 13)
- 18 unique lines with flow > 90% of thermal rating
- 21,381 line-hours near-congested (PTDF)
- Near-congestion present in 8,758 of 8,760 hours (>99.9%)

### C2. Negative LMPs (violations Cell 14)
- **1,024 negative LMP bus-hours** at 100 of 123 buses (PTDF)
- LMP range: **-$882.91** to **+$1,000.00**
- 42 bus-hours with LMP > $100/MWh
- 4 bus-hours with LMP > $500/MWh

### C3. Extreme Amplification
- Extreme scenario: 39-40 congested lines (2x no-extreme)
- Negative LMP rate: 1.3-1.7% of bus-hours (13-17x no-extreme rate)
- extreme_B: **118 bus-hours > $500/MWh** (vs 4 in no-extreme PTDF)

**Interpretation:** Congestion is structurally present. Negative LMPs signal transmission bottlenecks combined with renewable surplus. These buses are candidates for GTEP transmission reinforcement.

---

## D. CT Cycling and Marginal Economics

### D1. Cycling Volume (violations Cell 19)
- 7,400-7,600 total starts/year (no-extreme)
- ~55 starts per CT per year; top cyclers: 340+ starts/year (nearly daily)
- GTEP's 4-representative-day approach likely underestimates cycling cost

### D2. Marginal Profitability (profitability Cell 13)
- CT median profit: **$0.17/MWh** — near breakeven
- 3 CTs loss-making (profitability Cell 10): Gen 147, ct_fe_113_3-c, ct_fe_65_2-c
- Losses are negligible (<$1 total) — these are essentially breakeven

### D3. Uplift Payments (profitability Cell 22)
- Total uplift: $1.1M (0.03% of $4.96B revenue)
- 52 of 149 thermal generators receive uplift (mostly CTs)
- CT uplift: $0.8M total, $0.02/MWh median

**Interpretation:** CTs are economically marginal peakers. Their primary value is providing flexibility (start/stop to balance renewables), not energy margin. The GTEP objective does not include startup costs, so the model over-builds CTs without accounting for their cycling cost.

---

## E. Price Signals (violations Cell 27)

| Metric | no_extreme_A | no_extreme_B | extreme_A | extreme_B |
|--------|-------------|-------------|-----------|-----------|
| Mean price | $11.62/MWh | $11.62/MWh | $12.80/MWh | $12.88/MWh |
| Std dev | $3.04 | $3.04 | $2.98 | $3.02 |
| Min | $3.47 | $3.47 | $4.31 | $4.30 |
| Max | $18.58 | $18.58 | $19.97 | $20.10 |
| Hours < $0 | 0 | 0 | 0 | 0 |
| Hours > $100 | 0 | 0 | 0 | 0 |

- No negative or extreme system prices despite negative bus LMPs
- Low volatility (std ~$3) — fleet has ample capacity margin
- Extreme scenario slightly higher mean ($12.8 vs $11.6) but no spikes

**Interpretation:** The system price is remarkably stable, confirming the fleet is over-built relative to demand. Scarcity pricing is absent. The negative bus LMPs (Section C) are localized congestion, not system-wide surplus.

---

## F. Fleet Economics Summary (profitability notebook)

| Metric | PTDF | btheta |
|--------|------|--------|
| Total revenue | $4,960M | $4,959M |
| Total cost | $2,805M | $2,806M |
| Net profit | $2,156M | $2,155M |
| Loss-making gens | 3/278 | 3/278 |
| Thermal profit | $714M | $710M |
| Renewable revenue | $1,442M | $1,442M |

### By Fuel Type (profitability Cell 13)

| Type | Profit | Median $/MWh | Avg CF |
|------|--------|-------------|--------|
| NUC | $331M | $7.92 | 89% |
| COAL | $274M | $4.37 | 48% |
| CT | $109M | $0.17 | 7% |
| WIND | $1,137M rev | $20.41 | — |
| PV | $305M rev | $21.63 | — |

**Config sensitivity (profitability Cell 26):** PTDF vs btheta profit delta is <1% across all fuel types. Network formulation choice does not materially affect economic outcomes.

---

## G. Notebook Issue: GTEP Investment Matching

**Location:** profitability Cell 16

The notebook reports "Kept: 0, New: 278, Retired: 292" when comparing base-year (Prescient_2/gen.csv) to 2035 fleet. This is because generator UIDs differ entirely between the two datasets — the 2035 conversion created new UIDs. All generators are classified as "new" and all base-year generators as "retired."

This is a **notebook comparison logic limitation**, not a data error. The `dispatchable_investments.json` file (Cell 15) was also not found at the expected path.

---

## Recommendations

1. **Enable GTEP reserve constraints** — reserves are met by accident (over-build), not by design. The extreme scenario proves reserves can fail.
2. **Complete extreme scenario full-year PCM run** — 69-day partial data shows real violations; need 365 days for definitive assessment.
3. **Add startup/cycling cost to GTEP objective** — 7,400+ CT starts/year at $0.17/MWh margin suggests cycling cost is a meaningful omission.
4. **Investigate negative-LMP buses** — 100/123 buses have negative LMPs; these are transmission reinforcement candidates.
5. **Fix profitability notebook investment matching** — use GTEP investment JSONs or manual mapping to correctly classify kept/new/retired generators.
