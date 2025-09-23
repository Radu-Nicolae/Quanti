# upload the benchmarking script and data files to the server
import sys, os, pandas as pd, numpy as np
import subprocess
from Quanti.utils import now_tag
from ssh_manager import *


def upload_all_files():
    """Upload all benchmarking scripts and data files to the server."""
    # Create necessary directories on remote server - everything in Quanti
    subprocess.run("ssh glg1 'mkdir -p ~/Quanti ~/Quanti/data/input ~/Quanti/data/results'", shell=True)

    files_to_upload = {
        "benchmark.py": "Quanti/benchmark.py",
        "vllm_manager.py": "Quanti/vllm_manager.py",
        "utils.py": "Quanti/utils.py",
        "energy.py": "Quanti/energy.py",
        "requirements.txt": "Quanti/requirements.txt"  # Also put in Quanti
    }

    data_files = [
        "data/input/llm_workload_10.csv",
        "data/input/llm_workload_100.csv",
        "data/input/llm_workload_1000.csv"
    ]

    # Upload script files
    for local_file, remote_file in files_to_upload.items():
        print(f"Checking: {local_file} - Exists: {os.path.exists(local_file)}")
        if os.path.exists(local_file):
            print(f" 📤 Uploading  {local_file} -> {remote_file}")
            result = subprocess.run(f"scp -O {local_file} glg1:~/{remote_file}", shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to upload {local_file}: {result.stderr.strip()}")
                sys.exit(1)

    # Upload data files to Quanti/data/input/

    for local_file in data_files:
        if os.path.exists(local_file):
            remote_file = f"~/Quanti/data/input/{os.path.basename(local_file)}"  # Put in Quanti folder
            print(f"  📤 {local_file} → {remote_file}")
            result = subprocess.run(f"scp -O {local_file} glg1:{remote_file}", shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to upload {local_file}: {result.stderr.strip()}")
                sys.exit(1)
