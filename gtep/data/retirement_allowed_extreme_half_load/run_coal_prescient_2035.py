from prescient.simulator import Prescient

# 2035 PCM simulation for EXTREME case using GTEP stage 3 solution
# Data in Prescient_2_2035/ copied from no_extreme case (retirement_allowed_no_extreme_half_load_local)
# NOTE: gen.csv reflects no_extreme GTEP solution — regenerate from extreme GTEP solution
#       (dispatchable_investments.json + renewable_investments.json) for correct extreme-case results
# Configuration: PTDF network, full-year 365-day run (Jan 1 – Dec 31, 2035)

prescient_options = {
    "data_path": "Prescient_2_2035",
    "input_format": "rts-gmlc",
    "simulate_out_of_sample": True,
    "run_sced_with_persistent_forecast_errors": True,
    "output_directory": "Prescient_2_2035/results",
    "start_date": "01-01-2035",
    "num_days": 365,
    "sced_horizon": 6,
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
    "ruc_network_type": "ptdf",
    "sced_network_type": "ptdf",
    "enforce_sced_shutdown_ramprate": False,
    "reserve_factor": 0.1,
    "day_ahead_pricing": "LMP",
}

Prescient().simulate(**prescient_options)
