#!/bin/bash
# One-time env on CRC for prompt 04: upstream 7b84352 pins (pyproject.toml) +
# gurobipy 11.0.2 to match `module load gurobi` (11.0.2). May lesson:
# gurobipy 13 against the Gurobi 11 module conflicts.
set -eo pipefail  # no -u: /etc/bashrc on CRC references unset BASHRCSOURCED
ROOT=/groups/adowling/ylu28/idaes-gtep-eval
ENV=/groups/adowling/ylu28/conda_envs/gtep_up
source ~/.bashrc
# keep conda/pip caches out of $HOME (home quota crash of 2026-08-29)
export CONDA_PKGS_DIRS=/groups/adowling/ylu28/conda_pkgs
export PIP_CACHE_DIR=/groups/adowling/ylu28/pip_cache
mkdir -p "$CONDA_PKGS_DIRS" "$PIP_CACHE_DIR"
conda create -y -p "$ENV" python=3.11
conda activate "$ENV"
pip install -e "$ROOT"
pip install "pyomo==6.10.1" "highspy==1.15.1" "gurobipy==11.0.2"
module load gurobi
python -c "import gtep, gurobipy, pyomo; print(gtep.__file__, gurobipy.gurobi.version(), pyomo.version.version)"
