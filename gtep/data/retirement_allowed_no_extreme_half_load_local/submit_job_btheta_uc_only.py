import os
from pathlib import Path
from textwrap import dedent
import subprocess

THIS_DIR = Path(__file__).resolve().parent

def submit_job(job_name: str = "ERCOT_btheta_uc_hydro") -> None:
    # make job_scripts dir
    job_scripts_dir = THIS_DIR / "job_scripts"
    os.makedirs(job_scripts_dir, exist_ok=True)

    # write the shell script
    sh_path = job_scripts_dir / f"{job_name}.sh"
    script = dedent(f"""\
        #!/bin/bash
        #$ -M ylu28@nd.edu
        #$ -m ae
        #$ -q long
        #$ -N {job_name}

        # ensure conda is available
        source ~/.bashrc
        conda activate /users/ylu28//dispatches

        export LD_LIBRARY_PATH=~/.conda/envs/users/ylu28//dispatches/lib:$LD_LIBRARY_PATH
        module load gurobi
        module load ipopt/3.14.2

        python ./run_coal_prescient_btheta_uc_only.py
    """)
    with open(sh_path, "w", newline="\n") as f:
        f.write(script)
    os.chmod(sh_path, 0o755)  # optional

    subprocess.run(["qsub", str(sh_path)], check=True)
    print(f"Submitted: {sh_path}")

if __name__ == "__main__":
    submit_job("ERCOT_btheta_uc_hydro")
