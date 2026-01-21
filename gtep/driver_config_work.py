#################################################################################
# The Institute for the Design of Advanced Energy Systems Integrated Platform
# Framework (IDAES IP) was produced under the DOE Institute for the
# Design of Advanced Energy Systems (IDAES).
#
# Copyright (c) 2018-2025 by the software owners: The Regents of the
# University of California, through Lawrence Berkeley National Laboratory,
# National Technology & Engineering Solutions of Sandia, LLC, Carnegie Mellon
# University, West Virginia University Research Corporation, et al.
# All rights reserved.  Please see the files COPYRIGHT.md and LICENSE.md
# for full copyright and license information.
#################################################################################

from gtep.gtep_model import ExpansionPlanningModel
from gtep.gtep_data import ExpansionPlanningData
from gtep.gtep_solution import ExpansionPlanningSolution
from pyomo.core import TransformationFactory
from pyomo.contrib.appsi.solvers.highs import Highs
from pyomo.contrib.appsi.solvers.gurobi import Gurobi
from icecream import ic

data_path = "./gtep/data/5bus"
data_object = ExpansionPlanningData()
data_object.load_prescient(data_path)

<<<<<<< HEAD:gtep/driver_config_work.py
<<<<<<< HEAD:gtep/driver_config_work.py

mod_object = ExpansionPlanningModel(
<<<<<<< HEAD:gtep/driver_config_work.py
    stages=1, data=data_object, num_reps=1, len_reps=1, num_commit=24, num_dispatch=4
)

for k, v in mod_object.config.items():
    print(f"k: {k}", f"v: {v}")
=======
    stages=1,
=======
for key in data_object.md.data["elements"]["branch"]:
    data_object.md.data["elements"]["branch"][key]["capital_cost"] = 1000
    print(data_object.md.data["elements"]["branch"][key])

mod_object = ExpansionPlanningModel(
    stages=3,
>>>>>>> 48eb3a8 (5 and 9 Bus Test Case Data):gtep/driver_config_test.py
=======


mod_object = ExpansionPlanningModel(
    stages=1,
>>>>>>> 8eedd80 (ignore config changes):gtep/driver_config_test.py
    data=data_object.md,
    num_reps=1,
    len_reps=1,
    num_commit=24,
    num_dispatch=4,
)

for k,v in mod_object.config.items():
    ic(k,v)

<<<<<<< HEAD:gtep/driver_config_work.py
# quit()
>>>>>>> da58e56 (Model Accuracy Improvements and Testings):gtep/driver_config_test.py
=======
quit()
>>>>>>> 8eedd80 (ignore config changes):gtep/driver_config_test.py

mod_object.config["include_investment"] = False
mod_object.create_model()

<<<<<<< HEAD:gtep/driver_config_work.py
<<<<<<< HEAD:gtep/driver_config_work.py
ic(mod_object)
exit()

=======
#ic(mod_object)


#quit()
>>>>>>> da58e56 (Model Accuracy Improvements and Testings):gtep/driver_config_test.py
=======
ic(mod_object)


quit()
>>>>>>> 8eedd80 (ignore config changes):gtep/driver_config_test.py
TransformationFactory("gdp.bound_pretransformation").apply_to(mod_object.model)
TransformationFactory("gdp.bigm").apply_to(mod_object.model)
# opt = SolverFactory("gurobi")
opt = Gurobi()
# opt = Highs()
# # mod_object.results = opt.solve(mod_object.model, tee=True)
mod_object.results = opt.solve(mod_object.model)

<<<<<<< HEAD:gtep/driver_config_work.py
# sol_object = ExpansionPlanningSolution()
# sol_object.load_from_model(mod_object)
# sol_object.dump_json("./gtep_solution.json")
=======
sol_object = ExpansionPlanningSolution()
sol_object.load_from_model(mod_object)
<<<<<<< HEAD:gtep/driver_config_work.py
sol_object.dump_json("./gtep_solution_DC_5busCompleteNetwork.json")
>>>>>>> 48eb3a8 (5 and 9 Bus Test Case Data):gtep/driver_config_test.py
=======
sol_object.dump_json("./gtep_solution.json")
>>>>>>> 8eedd80 (ignore config changes):gtep/driver_config_test.py

# sol_object.import_data_object(data_object)

<<<<<<< HEAD:gtep/driver_config_work.py
# # sol_object.read_json("./gtep_lots_of_buses_solution.json")  # "./gtep/data/WECC_USAEE"
# # sol_object.read_json("./gtep_11bus_solution.json")  # "./gtep/data/WECC_Reduced_USAEE"
# # sol_object.read_json("./gtep_solution.json")
# # sol_object.read_json("./updated_gtep_solution_test.json")
# # sol_object.read_json("./gtep_wiggles.json")
=======
# sol_object.read_json("./gtep_lots_of_buses_solution.json")  # "./gtep/data/WECC_USAEE"
# sol_object.read_json("./gtep_11bus_solution.json")  # "./gtep/data/WECC_Reduced_USAEE"
# sol_object.read_json("./gtep_solution.json")
# sol_object.read_json("./updated_gtep_solution_test.json")
# sol_object.read_json("./gtep_wiggles.json")
<<<<<<< HEAD:gtep/driver_config_work.py
>>>>>>> da58e56 (Model Accuracy Improvements and Testings):gtep/driver_config_test.py
# sol_object.plot_levels(save_dir="./plots/")
=======
sol_object.plot_levels(save_dir="./plots/")
>>>>>>> 8eedd80 (ignore config changes):gtep/driver_config_test.py

# save_numerical_results = False
# if save_numerical_results:

#     sol_object = ExpansionPlanningSolution()

#     sol_object.load_from_model(mod_object)
#     sol_object.dump_json()
# load_numerical_results = False
# if load_numerical_results:
#     # sol_object.read_json("./gtep_solution.json")
#     sol_object.read_json("./bigger_longer_wigglier_gtep_solution.json")
# plot_results = False
# if plot_results:
#     sol_object.plot_levels(save_dir="./plots/")


pass
