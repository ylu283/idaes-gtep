#!/bin/bash
# One-time env on CRC for prompt 04: upstream 7b84352 pins (pyproject.toml) +
# gurobipy 11.0.2 to match `module load gurobi` (11.0.2). May lesson:
# gurobipy 13 against the Gurobi 11 module conflicts.
set -euo pipefail
ROOT=/groups/adowling/ylu28/idaes-gtep-eval
ENV=/groups/adowling/ylu28/conda_envs/gtep_up
source ~/.bashrc
conda create -y -p "$ENV" python=3.11
conda activate "$ENV"
pip install -e "$ROOT"
pip install "pyomo==6.10.1" "highspy==1.15.1" "gurobipy==11.0.2"
module load gurobi
python -c "import gtep, gurobipy, pyomo; print(gtep.__file__, gurobipy.gurobi.version(), pyomo.version.version)"
