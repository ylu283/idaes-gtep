# CRC kit for prompt 04 (not run yet; every `qsub` needs Kay's OK)

Transfer = rsync (Kay, 2026-10-10). Target: `/groups/adowling/ylu28/idaes-gtep-eval` (never `$HOME`).
Needs the ND VPN (`crcfe01.crc.nd.edu` did not resolve from the laptop on 2026-10-10).

```bash
# 1. from the laptop, worktree root
rsync -av --delete --exclude '.git/' --exclude '.claude/' --exclude 'explorations/**/output/' \
  --exclude '__pycache__/' --exclude '*.egg-info/' \
  ~/Documents/GitHub/idaes-gtep-eval/ ylu28@crcfe01.crc.nd.edu:/groups/adowling/ylu28/idaes-gtep-eval/
# 2. on CRC, once: env with upstream pins + gurobipy matching the Gurobi 11.0.2 module
bash /groups/adowling/ylu28/idaes-gtep-eval/explorations/coal_upstream/crc/setup_env.sh
# 3. on CRC, per run (ask first), from the repo root; RUNARGS may override --stages/--num-reps (G0 smoke): e.g.
qsub -N COAL_A1 -v RUNARGS="--config 1HR --cost-data off --scale-texas-loads off",RUN=A1 \
  /groups/adowling/ylu28/idaes-gtep-eval/explorations/coal_upstream/crc/run_coal.sh
```

Job logs (`-j y`) land in `explorations/coal_upstream/output/crc_logs/` (ignored by `explorations/**/output/`), never committed.
