from prescient.simulator import Prescient

# UC-only configuration: no out-of-sample forecast errors,
# minimal SCED look-ahead — isolates unit commitment (RUC) pricing.
prescient_options = {
    "data_path": "Prescient_2",
    "input_format": "rts-gmlc",
    "simulate_out_of_sample": False,
    "run_sced_with_persistent_forecast_errors": False,
    "output_directory": "Prescient_2/results_uc_only",
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
# run the simulator
Prescient().simulate(**prescient_options)
