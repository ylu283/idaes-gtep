#!/bin/bash
#$ -M ylu28@nd.edu
#$ -m ae
#$ -q long
#$ -N ERCOT_btheta_uc_hydro

# ensure conda is available
source ~/.bashrc
conda activate /users/ylu28//dispatches

export LD_LIBRARY_PATH=~/.conda/envs/users/ylu28//dispatches/lib:$LD_LIBRARY_PATH
module load gurobi
module load ipopt/3.14.2

python ./run_coal_prescient_btheta_uc_only.py
