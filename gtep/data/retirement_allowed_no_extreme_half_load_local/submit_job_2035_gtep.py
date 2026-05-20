"""Submit GTEP 1hr, 2hr, and 4hr commitment period jobs to CRC.

Usage on CRC:
    cd ~/GitHub/idaes-gtep
    python gtep/data/retirement_allowed_no_extreme_half_load_local/submit_job_2035_gtep.py
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from textwrap import dedent

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT_ON_CRC = "$HOME/GitHub/idaes-gtep"

JOBS = {
    "ERCOT_GTEP_1HR": "gtep/driver_coal.py",
    "ERCOT_GTEP_2HR_COMMIT": "gtep/driver_coal_2hr.py",
    "ERCOT_GTEP_4HR_COMMIT": "gtep/driver_coal_4hr.py",
}


def submit_job(job_name: str, driver: str) -> None:
    job_scripts_dir = THIS_DIR / "job_scripts"
    os.makedirs(job_scripts_dir, exist_ok=True)

    sh_path = job_scripts_dir / f"{job_name}.sh"
    script = dedent(
        f"""\
        #!/bin/bash
        #$ -M ylu28@nd.edu
        #$ -m ae
        #$ -q long
        #$ -l h_rt=24:00:00
        #$ -N {job_name}

        source ~/.bashrc
        conda activate gtep2

        export LD_LIBRARY_PATH=~/.conda/envs/gtep2/lib:$LD_LIBRARY_PATH
        module load gurobi

        cd {REPO_ROOT_ON_CRC}
        python {driver}
    """
    )
    with open(sh_path, "w", newline="\n") as f:
        f.write(script)
    os.chmod(sh_path, 0o755)

    subprocess.run(["qsub", str(sh_path)], check=True)
    print(f"Submitted: {sh_path}")


if __name__ == "__main__":
    for job_name, driver in JOBS.items():
        submit_job(job_name, driver)
