"""GTEP driver with 2-hour commitment periods (12 per rep day).

Identical to driver_coal.py except:
- num_commit=12 (2-hour blocks instead of 1-hour)
- Hourly data (load, renewable p_max) averaged into 2-hour blocks
- min_up_time / min_down_time converted from hours to 2-hour periods
- commitmentPeriodLength patched from 1 to 2 hours
- Output saved to retirement_allowed_no_extreme_2hr_commit/
"""

import gc
import json
import math
import os

import pyomo.environ as pyo
import pyomo.gdp as gdp
from pyomo.core import TransformationFactory
from pyomo.contrib.solver.solvers.gurobi_direct import GurobiDirect

from gtep.gtep_model import ExpansionPlanningModel
from gtep.gtep_data import ExpansionPlanningData

gc.disable()

# ── Configuration ─────────────────────────────────────────────────────────
BLOCK_HOURS = 2
NUM_COMMIT = 24 // BLOCK_HOURS  # 12
OUTPUT_DIR = "retirement_allowed_no_extreme_2hr_commit"

# ── Data aggregation helpers ──────────────────────────────────────────────

def aggregate_hourly_to_blocks(values_24, block_hours):
    """Average 24 hourly values into blocks of `block_hours`."""
    n_blocks = len(values_24) // block_hours
    return [
        sum(values_24[i * block_hours : (i + 1) * block_hours]) / block_hours
        for i in range(n_blocks)
    ]


def aggregate_data(data_object, block_hours, num_commit):
    """Pre-aggregate hourly data to match the target commitment resolution.

    Modifies data_object.representative_data in place:
    - p_load["values"]: 24 → num_commit values (block-averaged)
    - p_max["values"] for renewables: 24 → num_commit values (block-averaged)
    - min_up_time / min_down_time: hours → ceil(hours / block_hours), capped at num_commit
    """
    for rep_data in data_object.representative_data:
        elements = rep_data.data["elements"]

        # Aggregate load time series
        for load_n in elements["load"]:
            load_entry = elements["load"][load_n]
            if isinstance(load_entry["p_load"], dict) and "values" in load_entry["p_load"]:
                load_entry["p_load"]["values"] = aggregate_hourly_to_blocks(
                    load_entry["p_load"]["values"], block_hours
                )

        # Aggregate renewable capacity time series
        for gen in elements["generator"]:
            g = elements["generator"][gen]
            if isinstance(g.get("p_max"), dict) and "values" in g["p_max"]:
                g["p_max"]["values"] = aggregate_hourly_to_blocks(
                    g["p_max"]["values"], block_hours
                )

        # Scale min up/down time from hours to block-period counts
        for gen in elements["generator"]:
            g = elements["generator"][gen]
            if "min_up_time" in g:
                g["min_up_time"] = min(
                    math.ceil(g["min_up_time"] / block_hours), num_commit
                )
            if "min_down_time" in g:
                g["min_down_time"] = min(
                    math.ceil(g["min_down_time"] / block_hours), num_commit
                )


def aggregate_load_scaling(data_object, block_hours):
    """Average load_scaling rows in groups of `block_hours` hours."""
    df = data_object.load_scaling.copy()
    # hour column is 1-based (1-24); map to block index (1-based)
    df["hour"] = ((df["hour"] - 1) // block_hours) + 1
    # Average the scaling factors within each block
    group_cols = ["year", "month", "day", "hour"]
    scale_cols = [c for c in df.columns if c not in group_cols]
    data_object.load_scaling = df.groupby(group_cols, as_index=False)[scale_cols].mean()


# ── Load data ─────────────────────────────────────────────────────────────
data_path = "./gtep/data/123_Bus_Coal"
data_object = ExpansionPlanningData()
data_object.load_prescient(data_path)

load_scaling_path = data_path + "/ERCOT-Adjusted-Forecast.xlsb"
data_object.import_load_scaling(load_scaling_path)

data_object.texas_case_study_updates(data_path)

# ── Aggregate to 2-hour resolution ───────────────────────────────────────
aggregate_data(data_object, BLOCK_HOURS, NUM_COMMIT)
aggregate_load_scaling(data_object, BLOCK_HOURS)

# ── Build model ──────────────────────────────────────────────────────────
mod_object = ExpansionPlanningModel(
    stages=3, data=data_object, num_reps=4, len_reps=24,
    num_commit=NUM_COMMIT, num_dispatch=1,
)
mod_object.config["include_investment"] = True
mod_object.config["scale_loads"] = False
mod_object.config["scale_texas_loads"] = True
mod_object.config["transmission"] = False
mod_object.config["flow_model"] = "CP"

mod_object.create_model()

# ── Patch temporal parameters for BLOCK_HOURS-wide periods ────────────────
# Use set_value() to preserve the Pyomo Param objects (and their units)
# so that constraint/expression references remain valid.
m = mod_object.model
m.commitmentPeriodLength.set_value(BLOCK_HOURS)          # units=u.hr
m.dispatchPeriodLength.set_value(BLOCK_HOURS * 60)       # units=u.minutes
for stage in m.stages:
    i_blk = m.investmentStage[stage]
    for rp in i_blk.representativePeriods:
        r_blk = i_blk.representativePeriod[rp]
        for cp in r_blk.commitmentPeriods:
            cp_blk = r_blk.commitmentPeriod[cp]
            cp_blk.commitmentPeriodLength.set_value(BLOCK_HOURS)  # units=u.hr
            for dp in cp_blk.dispatchPeriods:
                cp_blk.dispatchPeriod[dp].periodLength.set_value(BLOCK_HOURS)

mod_object.timer.toc(f"Model built with {NUM_COMMIT} x {BLOCK_HOURS}hr commitment periods")

# ── Transform and solve ──────────────────────────────────────────────────
TransformationFactory("gdp.bigm").apply_to(mod_object.model)
mod_object.timer.toc("BigM transformation done")

opt = GurobiDirect()
mod_object.timer.toc("Starting Gurobi solve")
mod_object.results = opt.solve(
    mod_object.model, tee=True, solver_options={"LogFile": "basic_logging_2hr.log"}
)
mod_object.timer.toc("Solve complete")

# ── Extract results ───────────────────────────────────────────────────────
valid_names = ["Inst", "Oper", "Disa", "Ext", "Ret"]
renewable_investments = {}
dispatchable_investments = {}
load_shed = {}

for var in mod_object.model.component_objects(pyo.Var, descend_into=True):
    for index in var:
        if "Shed" in var.name:
            if pyo.value(var[index]) >= 0.001:
                load_shed[var.name + "." + str(index)] = pyo.value(var[index])
        for name in valid_names:
            if name in var.name:
                if pyo.value(var[index]) >= 0.001:
                    renewable_investments[var.name + "." + str(index)] = pyo.value(
                        var[index]
                    )

for var in mod_object.model.component_objects(gdp.Disjunct, descend_into=True):
    for index in var:
        for name in valid_names:
            if name in var.name:
                if pyo.value(var[index].indicator_var) == True:
                    dispatchable_investments[var.name + "." + str(index)] = pyo.value(
                        var[index].indicator_var
                    )

costs = {}
for exp in mod_object.model.component_objects(pyo.Expression, descend_into=True):
    if "operatingCost" in exp.name:
        costs[exp.name] = pyo.value(exp)
    elif "investmentCost" in exp.name:
        costs[exp.name] = pyo.value(exp)

# ── Save ──────────────────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(os.path.join(OUTPUT_DIR, "renewable_investments.json"), "w") as fil:
    json.dump(renewable_investments, fil)
with open(os.path.join(OUTPUT_DIR, "dispatchable_investments.json"), "w") as fil:
    json.dump(dispatchable_investments, fil)
with open(os.path.join(OUTPUT_DIR, "load_shed.json"), "w") as fil:
    json.dump(load_shed, fil)
with open(os.path.join(OUTPUT_DIR, "costs.json"), "w") as fil:
    json.dump(costs, fil)

mod_object.timer.toc(f"Results saved to {OUTPUT_DIR}/")
