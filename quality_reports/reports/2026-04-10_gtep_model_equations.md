# GTEP Model: Equations and Constraints

**Date:** 2026-04-10
**Source:** `gtep/gtep_model.py`

This document presents every active constraint and equation in the GTEP model in mathematical notation, with source line references.

---

## Notation

| Symbol | Meaning |
|--------|---------|
| $s \in S$ | Investment stage (1, 2, 3 → years 2025, 2030, 2035) |
| $r \in R$ | Representative period |
| $c \in C_r$ | Commitment period within representative period $r$ |
| $d \in D_c$ | Dispatch period within commitment period $c$ |
| $g \in G^T$ | Thermal generator |
| $g \in G^R$ | Renewable generator |
| $g \in G$ | Any generator ($G = G^T \cup G^R$) |
| $b \in B$ | Bus |
| $l \in L$ | Transmission line |
| $\rho \in \mathcal{R}$ | Region |

---

## 1. Objective Function

**Line 1608–1641.** Minimize total system cost:

$$\min \quad \sum_{s \in S} \left[ \text{OpCost}_s + \text{InvCost}_s + \text{PenaltyCost}_s \right]$$

### 1.1 Operating Cost (line 407–418)

$$\text{OpCost}_s = \alpha_s \sum_{r \in R} w_r \sum_{c \in C_r} \text{CommitCost}_{s,r,c}$$

where $\alpha_s$ is the investment factor and $w_r$ is the representative period weight.

### 1.2 Commitment Period Cost (line 1055–1090)

$$\text{CommitCost}_{s,r,c} = \underbrace{\sum_{d \in D_c} \text{DispatchCost}_{s,r,c,d}}_{\text{fuel + curtailment + load shed}} + \underbrace{\sum_{g \in G^T} FC_g \cdot \Delta t_c \cdot y^{\text{on/start/shut}}_g}_{\text{thermal fixed O\&M}} + \underbrace{\sum_{g \in G^R} FC_g \cdot \Delta t_c \cdot (\bar{P}^R_g)}_{\text{renewable fixed O\&M}} + \underbrace{\sum_{g \in G^T} SU_g \cdot y^{\text{start}}_g}_{\text{startup cost}}$$

where $y^{\text{on/start/shut}}_g$ is the binary indicator for genOn, genStartup, or genShutdown; $\bar{P}^R_g$ is the sum of renewable operational + installed + extended MW.

### 1.3 Dispatch Period Cost (line 592–602)

$$\text{DispatchCost}_{s,r,c,d} = \sum_{g \in G^T} P^T_g \cdot f_g + \sum_{b \in B} LS_b \cdot c^{LS} + \sum_{g \in G^R} C^R_g \cdot c^{curt}$$

where:
- $P^T_g$ = thermal generation (MW)
- $f_g$ = fuel cost ($/MWh) — the stage-specific `fuelCost` (line 578)
- $LS_b$ = load shed (MWh)
- $c^{LS}$ = load shed penalty ($5,000/MWh)
- $C^R_g$ = renewable curtailment (MW)
- $c^{curt}$ = curtailment penalty ($2 \times \max(f_g)$)

### 1.4 Investment Cost (line 423–475)

$$\text{InvCost}_s = \alpha_s \left[ \sum_{g \in G^T} IC_g \cdot \kappa_g \cdot x^I_g + \sum_{g \in G^R} IC_g \cdot \kappa_g \cdot P^{I,R}_g + \sum_{g \in G^T} IC_g \cdot \epsilon_g \cdot x^E_g + \sum_{g \in G^R} IC_g \cdot \epsilon_g \cdot P^{E,R}_g + \sum_{g \in G} IC_g \cdot \rho_g \cdot x^{Ret}_g \right]$$

where:
- $IC_g$ = investment cost ($/MW)
- $\kappa_g$ = capital multiplier
- $\epsilon_g$ = extension multiplier (0.06 for Texas case)
- $\rho_g$ = retirement multiplier (0.1 thermal, 1.0 renewable)
- $x^I_g$, $x^E_g$, $x^{Ret}_g$ = binary indicators for installed, extended, retired

### 1.5 Penalty Cost (line 1621–1627)

$$\text{PenaltyCost}_s = \delta_s \cdot \alpha_s \cdot Q_s + \text{CurtCost}_s$$

where $\delta_s$ is the deficit penalty, $Q_s$ is the renewable quota deficit, and $\text{CurtCost}_s$ is the total curtailment cost for the stage.

---

## 2. Dispatch Constraints

### 2.1 Power Balance (line 771–794)

For each bus $b$ in each dispatch period:

$$\sum_{g \in G^T_b} P^T_g + \sum_{g \in G^R_b} P^R_g + \sum_{l: \text{to}=b} F_l - \sum_{l: \text{from}=b} F_l + LS_b = D_b$$

where $G^T_b$, $G^R_b$ are generators at bus $b$, $F_l$ is power flow on line $l$, $D_b$ is load demand.

### 2.2 DC Power Flow (line 665)

For in-use transmission lines:

$$F_l = \frac{-1}{X_l} \left( \theta_{\text{to}(l)} - \theta_{\text{from}(l)} + \phi_l \right)$$

For not-in-use lines (line 691):

$$F_l = 0$$

Bus angles bounded: $-\pi/6 \leq \theta_b \leq \pi/6$.
Flow bounds: $-8 \cdot \bar{F}_l \leq F_l \leq \bar{F}_l$.

### 2.3 Renewable Capacity Factor (line 798–803)

For each renewable generator:

$$P^R_g + C^R_g = \bar{P}^R_g$$

All available capacity must be either generated or curtailed.

### 2.4 Renewable Operational Limit (line 806–813)

$$P^R_g \leq P^{R,\text{oper}}_g + P^{R,\text{inst}}_g + P^{R,\text{ext}}_g$$

Renewable generation limited to available (operational + installed + extended) capacity.

---

## 3. Commitment Constraints

### 3.1 Generator On (line 854–911)

When $y^{\text{on}}_g = 1$:

$$P^{\min}_g \cdot \bar{P}^T_g \leq P^T_{g,d} \qquad \forall d \in D_c \quad \text{(min output, line 861)}$$

$$P^T_{g,d} + SR_{g,d} \leq \bar{P}^T_g \qquad \forall d \in D_c \quad \text{(max output, line 870)}$$

$$P^T_{g,d} - P^T_{g,d-1} \leq RU_g \cdot \bar{P}^T_g \qquad \forall d \in D_c \quad \text{(ramp up, line 879)}$$

$$P^T_{g,d-1} - P^T_{g,d} \leq RD_g \cdot \bar{P}^T_g \qquad \forall d \in D_c \quad \text{(ramp down, line 892)}$$

$$SR_{g,d} \leq SR^{\max}_g \cdot \bar{P}^T_g \qquad \forall d \in D_c \quad \text{(spinning reserve, line 906)}$$

### 3.2 Generator Startup (line 915–950)

When $y^{\text{start}}_g = 1$:

$$0 \leq P^T_{g,d} \qquad \forall d$$

$$P^T_{g,d} + SR_{g,d} \leq P^{\min}_g \cdot \bar{P}^T_g \qquad \text{(can only ramp to min)}$$

$$P^T_{g,d} - P^T_{g,d-1} \leq \max(P^{\min}_g, RU_g) \cdot \bar{P}^T_g \qquad \text{(startup ramp)}$$

### 3.3 Generator Shutdown (line 952–986)

When $y^{\text{shut}}_g = 1$:

$$0 \leq P^T_{g,d} \qquad \forall d$$

$$P^T_{g,d} + SR_{g,d} \leq P^{\min}_g \cdot \bar{P}^T_g \qquad \text{(can only ramp from min)}$$

$$P^T_{g,d-1} - P^T_{g,d} \leq \max(P^{\min}_g, RD_g) \cdot \bar{P}^T_g \qquad \text{(shutdown ramp)}$$

### 3.4 Generator Off (line 988–1006)

When $y^{\text{off}}_g = 1$:

$$P^T_{g,d} = 0 \qquad \forall d$$

$$QR_{g,d} \leq QR^{\max}_g \cdot \bar{P}^T_g \qquad \text{(quick-start reserve only)}$$

### 3.5 Commitment–Investment Link (line 1018–1030)

A generator can only be committed if its investment status is active:

$$\left(y^{\text{on}}_g \lor y^{\text{start}}_g \lor y^{\text{shut}}_g\right) \implies \left(x^{\text{oper}}_g \lor x^{I}_g \lor x^{E}_g\right)$$

---

## 4. Intertemporal Constraints (Within Representative Periods)

These enforce min up/down time and consistent commitment transitions across commitment periods within a representative period.

### 4.1 Shutdown Consistency (line 1213)

If a generator shuts down in commitment period $c$, it must have been on in the preceding periods:

$$y^{\text{shut}}_{g,c} \implies y^{\text{on}}_{g,c-1}$$

### 4.2 Off After Shutdown (line 1245)

After completing shutdown, the generator must be off:

$$y^{\text{shut}}_{g,c} \implies y^{\text{off}}_{g,c+1}$$

### 4.3 Startup Consistency (line 1277)

If starting up in period $c$, must have been off previously:

$$y^{\text{start}}_{g,c} \implies y^{\text{off}}_{g,c-1}$$

### 4.4 On After Startup (line 1307)

After completing startup, the generator must be on:

$$y^{\text{start}}_{g,c} \implies y^{\text{on}}_{g,c+1}$$

### 4.5 Minimum Up Time (line 1335)

Once on, a generator must stay on for at least $T^{\text{up}}_g$ commitment periods:

$$y^{\text{on}}_{g,c} \implies y^{\text{on}}_{g,c'} \quad \forall c' \in \{c+1, \ldots, c+T^{\text{up}}_g-1\}$$

(Subject to boundary handling within the representative period.)

### 4.6 Minimum Down Time (line 1413)

Once off, a generator must stay off for at least $T^{\text{down}}_g$ commitment periods:

$$y^{\text{off}}_{g,c} \implies y^{\text{off}}_{g,c'} \quad \forall c' \in \{c+1, \ldots, c+T^{\text{down}}_g-1\}$$

---

## 5. Investment Linking Constraints (Across Stages)

These enforce consistent state transitions between investment stages.

### 5.1 Retirement Deadline (line 2088)

Generators that were operational or installed before their lifetime expires must be accounted for:

$$\sum_{t' \leq s - L_g} \left(x^{\text{oper}}_{g,t'} + x^{I}_{g,t'}\right) \leq \sum_{t' \leq s} \left(x^{\text{ret}}_{g,t'} + x^{E}_{g,t'}\right)$$

This ensures every unit that reaches end-of-life is either retired or extended.

### 5.2 Consistent Operation (line 2157)

$$x^{\text{oper}}_{g,s} \implies \left(x^{\text{oper}}_{g,s-1} \lor x^{I}_{g,s-1}\right) \quad \forall s > 1$$

If operational at stage $s$, must have been operational or installed at $s-1$.

### 5.3 Consistent Operation Future (line 2171)

$$x^{\text{oper}}_{g,s-1} \implies \left(x^{\text{oper}}_{g,s} \lor x^{E}_{g,s} \lor x^{\text{ret}}_{g,s}\right) \quad \forall s > 1$$

If operational at $s-1$, must be operational, extended, or retired at $s$.

### 5.4 Full Retirement (line 2186)

$$x^{\text{ret}}_{g,s-1} \implies x^{\text{dis}}_{g,s} \quad \forall s > 1$$

Retired at $s-1$ implies disabled at $s$.

### 5.5 Consistent Disabled (line 2200)

$$x^{\text{dis}}_{g,s-1} \implies \left(x^{\text{dis}}_{g,s} \lor x^{I}_{g,s}\right) \quad \forall s > 1$$

Disabled at $s-1$ stays disabled or gets reinstalled at $s$.

### 5.6 Consistent Extended (line 2214)

$$x^{E}_{g,s-1} \implies \left(x^{E}_{g,s} \lor x^{\text{ret}}_{g,s}\right) \quad \forall s > 1$$

Extended at $s-1$ stays extended or gets retired at $s$.

### 5.7 Full Investment (line 2228)

$$x^{I}_{g,s-1} \implies x^{\text{oper}}_{g,s} \quad \forall s > 1$$

Installed at $s-1$ becomes operational at $s$.

### 5.8 Renewable Capacity Linking (line 2129)

$$P^{R,\text{oper}}_{g,s} = P^{R,\text{oper}}_{g,s-1} + P^{R,\text{inst}}_{g,s-1} + P^{R,\text{ext}}_{g,s-1} - P^{R,\text{ret}}_{g,s-1} \quad \forall s > 1$$

Tracks the evolution of renewable capacity MW across stages.

### 5.9 Transmission Linking (line 2240–2316)

Same logical constraints as thermal generators (5.2–5.7) applied to transmission lines, conditional on `config["transmission"]`.

---

## 6. Curtailment Cost Linking (line 478–493)

Connects dispatch-level curtailment to the stage-level penalty variable:

$$\text{CurtCost}_s = \alpha_s \sum_{r \in R} w_r \cdot \Delta t_c \sum_{c \in C_r} \text{CurtailmentCommitment}_{s,r,c}$$

### 7. Renewable Quota (line 497–515)

$$\sum_{r,c} w_r \cdot \text{RenewableSurplusCommitment}_{s,r,c} + Q_s \geq \text{RenewableQuota}_s \times ed$$

**Note:** In the current code, $ed = 0$ always (line 503), making this constraint **vacuous**. The `TODO` comment indicates the load sum preprocessing is not yet implemented.

---

## 8. Disabled Constraints (Commented Out)

The following constraints exist in the code but are **not active**:

| Constraint | Line | Reason |
|-----------|------|--------|
| `total_operating_reserve` | 821–832 | "Reserve enforcement causes infeasibility issues" |
| `total_spinning_reserve` | 835–844 | Same |
| Branch investment cost terms | 462–474 | "JSC inprog" — work in progress |
| `gen_stats_link` (alternative linking) | 2066–2084 | Replaced by logical constraints |
| `renewable_retirement` | 2111–2124 | Commented out |
| `renewable_more_stats_link` | 2141–2149 | Commented out |
| `renewable_capacity_enforcement` | 2153–2154 | Commented out |

---

## 9. Dead Code Note

At line 578–579, there are two `return` statements in `generatorCost`:
```python
return b.thermalGeneration[gen] * i_p.fuelCost[gen]         # ACTIVE
return b.thermalGeneration[gen] * (i_p.fuelCost[gen] + i_p.varCost[gen])  # DEAD (unreachable)
```

The active formulation uses only fuel cost. The dead line would add variable O&M cost (`varCost`), which could be significant for some generator types.
