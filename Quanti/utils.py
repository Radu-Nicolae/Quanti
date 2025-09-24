import argparse
import csv
import glob
import subprocess
from datetime import datetime
import os
import shlex

WORKLOAD = "data/input/llm_workload_10.csv"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Run an LLM workload over SSH and record energy metrics."
    )
    parser.add_argument("llm", nargs="?", default="Llama-3-8B")
    parser.add_argument("workload", nargs="?", default=WORKLOAD)
    parser.add_argument("--output-dir", default="data/outputs",
                       help="Base output directory (default: data/outputs)")
    return parser.parse_args(argv)


def get_workload_size(workload_path: str) -> str:
    """Extract workload size from filename like llm_workload_100.csv -> 100"""
    filename = os.path.basename(workload_path)
    if "workload_" in filename:
        try:
            return filename.split("workload_")[1].split(".")[0]
        except:
            pass
    # Fallback: count CSV lines
    import pandas as pd
    return str(len(pd.read_csv(workload_path)))


def get_next_run_number(output_base_dir: str, model: str, workload_size: str) -> str:
    """Get next run number - resets per model/workload combination"""
    pattern = f"{output_base_dir}/r*_{model}_workload-{workload_size}_*"
    existing_runs = glob.glob(pattern)

    if not existing_runs:
        return "r00"

    run_numbers = []
    for run_path in existing_runs:
        dirname = os.path.basename(run_path)
        if dirname.startswith("r"):
            try:
                run_num = int(dirname.split("_")[0][1:])  # Extract from "r00"
                run_numbers.append(run_num)
            except ValueError:
                continue

    return f"r{max(run_numbers) + 1:02d}" if run_numbers else "r00"


def create_run_directory(output_base_dir: str, model: str, workload_path: str) -> str:
    """Create structured run directory"""
    workload_size = get_workload_size(workload_path)
    run_number = get_next_run_number(output_base_dir, model, workload_size)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")  # Readable format

    run_dir = f"{output_base_dir}/{run_number}_{model}_workload-{workload_size}_{timestamp}"
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(f"{run_dir}/detailed", exist_ok=True)

    return run_dir


def append_csv(path: str, idx: int, prompt: str, reply: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    mode = "a" if os.path.isfile(path) else "w"
    with open(path, mode, newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if fh.tell() == 0: w.writerow(["idx", "prompt", "reply"])
        w.writerow([idx, prompt, reply])


def quote(cmd: str) -> str:
    return shlex.quote(cmd)


def now_tag():
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

def cleanup_server():
    """Remove all Quanti traces from the server."""
    print("🧹 Cleaning up server (removing ~/Quanti)...")
    cleanup_cmd = "ssh glg1 'rm -rf ~/Quanti'"
    result = subprocess.run(cleanup_cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Server cleanup complete")
    else:
        print(f"⚠️ Server cleanup had issues: {result.stderr}")
        # Try force cleanup
        force_cmd = "ssh glg1 'rm -rf ~/Quanti || true'"
        subprocess.run(force_cmd, shell=True)
        print("🔄 Forced cleanup attempted")
