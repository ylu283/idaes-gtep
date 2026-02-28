from prescient.simulator import Prescient


def _patch_prescient_curtailment_report() -> None:
    """Handle renewable generators with scalar p_max (e.g., HYDRO in RTS-GMLC)."""
    try:
        from prescient.engine.egret import reporting
    except Exception:
        return

    def _at_time(value, idx):
        if isinstance(value, dict):
            return value["values"][idx]
        return value

    def _safe_report_curtailment_for_deterministic_ruc(ruc):
        rn_gens = dict(ruc.elements("generator", generator_type="renewable"))
        time_periods = ruc.data["system"]["time_keys"]

        curtailment_in_some_period = False
        for i, t in enumerate(time_periods):
            quantity_curtailed_this_period = sum(
                _at_time(gdict["p_max"], i) - _at_time(gdict["pg"], i)
                for gdict in rn_gens.values()
            )
            if quantity_curtailed_this_period >= 5e-3:
                if not curtailment_in_some_period:
                    print("Renewables curtailment summary (time-period, aggregate_quantity):")
                    curtailment_in_some_period = True
                print(f"{t} {quantity_curtailed_this_period:12.2f}")

    reporting.report_curtailment_for_deterministic_ruc = _safe_report_curtailment_for_deterministic_ruc


_patch_prescient_curtailment_report()

# btheta UC-only configuration with hydro generators:
# no out-of-sample forecast errors, minimal SCED look-ahead
# isolates unit commitment (RUC) pricing.
prescient_options = {
    "data_path": "Prescient_2",
    "input_format": "rts-gmlc",
    "simulate_out_of_sample": False,
    "run_sced_with_persistent_forecast_errors": False,
    "output_directory": "Prescient_2/results_btheta_uc_only",
    "start_date": "01-01-2019",
    "num_days": 90,
    "sced_horizon": 1,
    "ruc_mipgap": 0.01,
    "deterministic_ruc_solver": "gurobi_persistent",
    "deterministic_ruc_solver_options": "TimeLimit=3600",
    "sced_solver": "gurobi",
    "sced_frequency_minutes": 60,
    "ruc_horizon": 36,
    "compute_market_settlements": True,
    "monitor_all_contingencies": False,
    "output_solver_logs": False,
    "price_threshold": 1000,
    "contingency_price_threshold": 100,
    "reserve_price_threshold": 5,
    "ruc_network_type": "btheta",
    "sced_network_type": "btheta",
    "enforce_sced_shutdown_ramprate": False,
    "reserve_factor": 0.1,
    "day_ahead_pricing": "LMP",
}

Prescient().simulate(**prescient_options)
