#!/bin/bash
#$ -M ylu28@nd.edu
#$ -m ae
#$ -q long
#$ -N ERCOT_2035_GTEP_EXTRACT

# Activate the gtep1 conda env (has pyomo + egret + prescient + gurobipy + editable gtep)
source ~/.bashrc
conda activate gtep1

export LD_LIBRARY_PATH=~/.conda/envs/gtep1/lib:$LD_LIBRARY_PATH
module load gurobi

# Run from the repo root so relative imports/data paths resolve the
# same as in local dev. The extractor itself uses absolute Path(__file__)
# resolution for outputs, so the cwd only matters for the GTEP data
# loader (which reads gtep/data/123_Bus_Coal/).
cd $HOME/GitHub/idaes-gtep
python gtep/pcm_analysis/cem_vs_pcm_validation_2035/src/extract_gtep_stage3_cost.py
