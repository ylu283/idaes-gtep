"""Smoke test: verify data loading and set_value() work for 2hr/4hr drivers."""
import sys
from gtep.gtep_data import ExpansionPlanningData
from gtep.gtep_model import ExpansionPlanningModel

data_path = "./gtep/data/123_Bus_Coal"
data_object = ExpansionPlanningData()
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
