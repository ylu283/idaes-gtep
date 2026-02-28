#!/bin/bash
#$ -M ylu28@nd.edu
#$ -m ae
#$ -q long
#$ -N ERCOT_curtailment_penalty_pcm

source ~/.bashrc
conda activate /users/ylu28//dispatches

export LD_LIBRARY_PATH=~/.conda/envs/users/ylu28//dispatches/lib:$LD_LIBRARY_PATH
module load gurobi
module load ipopt/3.14.2

python ./run_curtailment_penalty_experiments.py --mode pcm --case-set benchmark
