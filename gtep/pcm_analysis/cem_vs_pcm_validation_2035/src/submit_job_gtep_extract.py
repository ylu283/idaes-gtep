"""Submit the GTEP stage-3 cost extractor to the CRC scheduler.

Mirrors the pattern in
`gtep/data/retirement_allowed_no_extreme_half_load_local/submit_job_2035.py`,
but targets the expansion-planning MILP solve (one-shot) rather than a
Prescient PCM simulation.

Env: `gtep1` (conda), with gtep editable-installed. Repo assumed to live at
`~/GitHub/idaes-gtep` on CRC.

Usage on CRC:
    python gtep/pcm_analysis/cem_vs_pcm_validation_2035/src/submit_job_gtep_extract.py

Writes `job_scripts/ERCOT_2035_GTEP_EXTRACT.sh` next to this file and submits
it with qsub. Output lands at
`gtep/pcm_analysis/cem_vs_pcm_validation_2035/results/gtep_stage3_cost.json`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from textwrap import dedent

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT_ON_CRC = "$HOME/GitHub/idaes-gtep"


def submit_job(job_name: str = "ERCOT_2035_GTEP_EXTRACT") -> None:
    job_scripts_dir = THIS_DIR / "job_scripts"
    os.makedirs(job_scripts_dir, exist_ok=True)

    sh_path = job_scripts_dir / f"{job_name}.sh"
    script = dedent(
        f"""\
        #!/bin/bash
        #$ -M ylu28@nd.edu
        #$ -m ae
        #$ -q long
        #$ -N {job_name}

        # Activate the gtep1 conda env (has pyomo + egret + prescient + gurobipy + editable gtep)
        source ~/.bashrc
        conda activate gtep1

        export LD_LIBRARY_PATH=~/.conda/envs/gtep1/lib:$LD_LIBRARY_PATH
        module load gurobi

        # Run from the repo root so relative imports/data paths resolve the
        # same as in local dev. The extractor itself uses absolute Path(__file__)
        # resolution for outputs, so the cwd only matters for the GTEP data
        # loader (which reads gtep/data/123_Bus_Coal/).
        cd {REPO_ROOT_ON_CRC}
        python gtep/pcm_analysis/cem_vs_pcm_validation_2035/src/extract_gtep_stage3_cost.py
    """
    )
    with open(sh_path, "w", newline="\n") as f:
        f.write(script)
    os.chmod(sh_path, 0o755)

    subprocess.run(["qsub", str(sh_path)], check=True)
    print(f"Submitted: {sh_path}")


if __name__ == "__main__":
    submit_job()
