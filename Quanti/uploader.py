# upload the benchmarking script and data files to the server
import sys
import os
from ssh import *


def upload_all_files():
    """Upload all benchmarking scripts and data files to the server."""
    # Create necessary directories on remote server
    subprocess.run("ssh glg1 'mkdir -p ~/data/input ~/results'", shell=True)

    files_to_upload = {
        "Quanti/benchmark.py": "benchmark.py",
        "Quanti/vllm.py": "vllm.py",
        "Quanti/utils.py": "utils.py",
        "Quanti/energy.py": "energy.py",
        "requirements.txt": "requirements.txt"
    }

    data_files = [
        "data/input/llm_workload_10.csv",
        "data/input/llm_workload_100.csv",
        "data/input/llm_workload_1000.csv"
    ]

    for local_file, remote_file in files_to_upload.items():
        if os.path.exists(local_file):
            print(f" 📤 Uploading  {local_file} -> {remote_file}")
            result = subprocess.run(f"scp -O {local_file} glg1:~/{remote_file}", shell=True, capture_output=True,
                                    text=True)
            if result.returncode != 0:
                print(f"❌ Failed to upload {local_file}: {result.stderr.strip()}")
                sys.exit(1)

    for local_file in data_files:
        if os.path.exists(local_file):
            remote_file = f"~/data/input/{os.path.basename(local_file)}"
            print(f"  📤 {local_file} → {remote_file}")
            result = subprocess.run(f"scp -O {local_file} glg1:{remote_file}", shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to upload {local_file}: {result.stderr.strip()}")
                sys.exit(1)
