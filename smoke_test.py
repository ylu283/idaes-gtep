"""Smoke test v3: inspect time_keys from INSIDE load_prescient."""
import sys
from gtep.gtep_data import ExpansionPlanningData

# Monkey-patch load_prescient to dump time_keys before the crash
_orig_load = ExpansionPlanningData.load_prescient

def _debug_load(self, data_path, options_dict=None):
    """Wrap load_prescient: intercept right after populate_with_actuals."""
    import datetime
    from prescient.simulator.config import PrescientConfig
    from prescient.data.providers import gmlc_data_provider

    self.data_type = "prescient"
    opts = {
        "data_path": data_path,
        "input_format": "rts-gmlc",
        "start_date": "01-01-2020",
        "num_days": 365,
        "sced_horizon": 1,
        "sced_frequency_minutes": 60,
        "ruc_horizon": 36,
    }
    prescient_options = PrescientConfig()
    prescient_options.set_value(opts)

    x = datetime.datetime(2020, 1, 1)
    data_provider = gmlc_data_provider.GmlcDataProvider(options=prescient_options)
    self.md = data_provider.get_initial_actuals_model(
        options=prescient_options, num_time_steps=24 * 365, minutes_per_timestep=60
    )

    tk_before = self.md.data["system"]["time_keys"]
    print(f"DEBUG after get_initial_actuals_model: {len(tk_before)} time_keys")
    print(f"DEBUG first 3 = {tk_before[:3]}")

    data_provider.populate_with_actuals(
        options=prescient_options,
        num_time_periods=24 * 365,
        time_period_length_minutes=60,
        start_time=x,
        model=self.md,
    )

    tk_after = self.md.data["system"]["time_keys"]
    print(f"DEBUG after populate_with_actuals: {len(tk_after)} time_keys")
    print(f"DEBUG first 5 = {tk_after[:5]}")
    print(f"DEBUG last 5 = {tk_after[-5:]}")
    print(f"DEBUG keys with '01-28': {[k for k in tk_after if '01-28' in str(k)][:3]}")
    print(f"DEBUG '2020-01-28 00:00' in keys? {'2020-01-28 00:00' in tk_after}")

    # Also check: what does driver_coal.py's load_prescient see?
    # Continue the rest of load_prescient to see if it crashes
    self.load_default_data_settings()
    self.load_storage_csv(data_path)

    for gen in self.md.data["elements"]["generator"]:
        if "-c" in gen:
            self.md.data["elements"]["generator"][gen]["in_service"] = False
    for branch in self.md.data["elements"]["branch"]:
        if "-c" in branch:
            self.md.data["elements"]["branch"][branch]["in_service"] = False
    for stor in self.md.data["elements"]["storage"]:
        if "-c" in stor:
            self.md.data["elements"]["storage"][stor]["in_service"] = False

    time_keys = self.md.data["system"]["time_keys"]
    print(f"\nDEBUG before representative_dates loop: {len(time_keys)} time_keys")
    print(f"DEBUG first 5 = {time_keys[:5]}")

    # Try each representative date
    for date in ["2020-01-28 00:00", "2019-01-28 00:00"]:
        if date in time_keys:
            print(f"DEBUG FOUND: '{date}' at index {time_keys.index(date)}")
        else:
            print(f"DEBUG NOT FOUND: '{date}'")

    sys.exit(0)


ExpansionPlanningData.load_prescient = _debug_load

data_path = "./gtep/data/123_Bus_Coal"
data_object = ExpansionPlanningData()
data_object.load_prescient(data_path)
