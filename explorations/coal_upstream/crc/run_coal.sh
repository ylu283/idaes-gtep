#!/bin/bash
#$ -M ylu28@nd.edu
#$ -m ae
#$ -q long
#$ -pe smp 16
#$ -l h_rt=48:00:00
#$ -j y
#$ -o /groups/adowling/ylu28/idaes-gtep-eval/explorations/coal_upstream/output/crc_logs/
# Usage: qsub -N COAL_<RUN> -v RUN=<RUN>,RUNARGS="<run_coal.py args>" run_coal.sh
# Gurobi, 1 % gap, 24 h limit, 16 threads; full structure 3 stages x 4 reps.
set -eo pipefail
ROOT=/groups/adowling/ylu28/idaes-gtep-eval
source ~/.bashrc
conda activate /groups/adowling/ylu28/conda_envs/gtep_up
module load gurobi
cd "$ROOT"
mkdir -p explorations/coal_upstream/output/crc_logs
python explorations/coal_upstream/scripts/run_coal.py $RUNARGS \
  --stages 3 --num-reps 4 --solver gurobi --mip-rel-gap 0.01 \
  --time-limit 86400 --threads 16 --out "explorations/coal_upstream/output/$RUN"
