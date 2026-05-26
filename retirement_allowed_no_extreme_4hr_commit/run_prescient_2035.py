"""Run Prescient PCM simulation for 2035 (4HR commitment period config)."""

from prescient.simulator import Prescient

prescient_options = {
    "data_path": "Prescient_2_2035",
    "input_format": "rts-gmlc",
    "simulate_out_of_sample": True,
    "run_sced_with_persistent_forecast_errors": True,
    "output_directory": "Prescient_2_2035/results",
    "start_date": "01-01-2035",
    "num_days": 30,
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
