#!/bin/bash
#$ -M ylu28@nd.edu
#$ -m ae
#$ -q long
#$ -N ERCOT_PCM_2HR

source ~/.bashrc
conda activate /users/ylu28//dispatches

export LD_LIBRARY_PATH=~/.conda/envs/users/ylu28//dispatches/lib:$LD_LIBRARY_PATH
module load gurobi
module load ipopt/3.14.2

cd $HOME/GitHub/idaes-gtep/retirement_allowed_no_extreme_2hr_commit
python ./run_prescient_2035.py
