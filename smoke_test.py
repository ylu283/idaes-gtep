"""Smoke test: verify data loading and set_value() work for 2hr/4hr drivers."""
import sys
from gtep.gtep_data import ExpansionPlanningData
from gtep.gtep_model import ExpansionPlanningModel

data_path = "./gtep/data/123_Bus_Coal"
data_object = ExpansionPlanningData()

# DEBUG: monkey-patch load_prescient to print time_keys before crashing
_orig_load = ExpansionPlanningData.load_prescient
def _debug_load(self, data_path, options_dict=None):
    _orig_load(self, data_path, options_dict)
ExpansionPlanningData.load_prescient = _debug_load

# Actually just inline the start of load_prescient to inspect time_keys
import datetime
from prescient.simulator.config import PrescientConfig
from egret.parsers.rts_gmlc import parsed_cache as gmlc_data_provider_module

# Replicate data loading to inspect time_keys
from prescient.data.providers import gmlc_data_provider
options_dict = {
    "data_path": data_path,
    "input_format": "rts-gmlc",
    "start_date": "01-01-2020",
    "num_days": 365,
    "sced_horizon": 1,
    "sced_frequency_minutes": 60,
    "ruc_horizon": 36,
}
prescient_options = PrescientConfig()
prescient_options.set_value(options_dict)
x = datetime.datetime(2020, 1, 1)
dp = gmlc_data_provider.GmlcDataProvider(options=prescient_options)
md = dp.get_initial_actuals_model(options=prescient_options, num_time_steps=24*365, minutes_per_timestep=60)
dp.populate_with_actuals(options=prescient_options, num_time_periods=24*365, time_period_length_minutes=60, start_time=x, model=md)
time_keys = md.data["system"]["time_keys"]
print(f"DEBUG: {len(time_keys)} time_keys")
print(f"DEBUG: first 3 = {time_keys[:3]}")
print(f"DEBUG: keys around Jan 28 = {[k for k in time_keys if '01-28' in k or '1-28' in k][:5]}")
print(f"DEBUG: '2020-01-28 00:00' in time_keys? {'2020-01-28 00:00' in time_keys}")
print(f"DEBUG: '2019-01-28 00:00' in time_keys? {'2019-01-28 00:00' in time_keys}")
sys.exit(0)

data_object.load_prescient(data_path)
data_object.import_load_scaling(data_path + "/ERCOT-Adjusted-Forecast.xlsb")
data_object.texas_case_study_updates(data_path)
print("OK: data loading")

mod_object = ExpansionPlanningModel(
    stages=3, data=data_object, num_reps=4, len_reps=24,
    num_commit=6, num_dispatch=1,
)
mod_object.config["include_investment"] = True
mod_object.config["scale_loads"] = False
mod_object.config["scale_texas_loads"] = True
mod_object.config["transmission"] = False
mod_object.config["flow_model"] = "CP"
mod_object.create_model()
print("OK: create_model()")

m = mod_object.model
m.commitmentPeriodLength.set_value(4)
m.dispatchPeriodLength.set_value(240)
print(f"  commitmentPeriodLength = {m.commitmentPeriodLength.value}")
print(f"  dispatchPeriodLength = {m.dispatchPeriodLength.value}")
print("OK: set_value()")
sys.exit(0)
