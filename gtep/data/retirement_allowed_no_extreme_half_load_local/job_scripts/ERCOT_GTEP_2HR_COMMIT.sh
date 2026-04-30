#!/bin/bash
#$ -M ylu28@nd.edu
#$ -m ae
#$ -q long
#$ -l h_rt=24:00:00
#$ -N ERCOT_GTEP_2HR_COMMIT

source ~/.bashrc
conda activate gtep2

export LD_LIBRARY_PATH=~/.conda/envs/gtep2/lib:$LD_LIBRARY_PATH
module load gurobi

cd $HOME/GitHub/idaes-gtep
python gtep/driver_coal_2hr.py
