# Quality Reports Index

Eval-branch index; the commitment_period INDEX.md stays authoritative for older artifacts

Last updated: 2026-10-10

## Latest By Topic

| Topic | Latest Report | Latest Deck | Notes |
|---|---|---|---|
| PMAPS 5-bus tutorial reproduction (upstream 7b84352) | `reports/2026-10-08_pmaps_5bus_tutorial_reproduction.md` | (none) | Pass: 3/3 objectives optimal, rel diff ~1e-12; 70 unit tests green; instrumentation in `../explorations/upstream_eval/` |
| PMAPS 123-bus tutorial reproduction + size/time (upstream 7b84352) | `reports/2026-10-08_pmaps_123bus_tutorial_reproduction.md` | (none) | Solves + totals reproduce, thermal mix near-degenerate; Experiment 2 1.19M rows / 399k bin, optimal in 25.3 min on HiGHS |
| Coal case (123-bus, May design) on upstream 7b84352 | `reports/2026-10-10_coal_case_on_upstream.md` | (none) | Stopped at A0: HiGHS no incumbent in 1 h (model feasible, certified); 2 data fixes + 3 ports; A1 6.32M rows -> CRC Gurobi (kit in `../explorations/coal_upstream/crc/`) |
