# main.py
import os, sys, csv, time, subprocess, atexit, requests, pandas as pd, json

import vllm_manager
from Quanti.benchmark import benchmark_main
from Quanti.uploader import upload_all_files
from Quanti.utils import parse_args, append_csv
from utils import *
# from energy import EnergyMonitor, now_tag
from ssh_manager import *



def query_one(base_url: str, prompt: str, model: str) -> str:
    payload = {"model": vllm_manager.models[model], "prompt": prompt, "max_tokens": 128, "temperature": 0.7}
    r = requests.post(f"{base_url}/completions", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["text"].strip()


def main():
    print("🚀 Quanti Benchmark Runner")

    # ------ Parsing user's input ------
    print("🛠️ [0/] Parsing input arguments...")
    args = parse_args(sys.argv[1:])
    print(f"✅ Input parsed: LLM={args.llm}, Workload={args.workload}")


    # ------ Upload all to server ------
    print("📡 [1/] Setting up server...")
    upload_all_files()
    print("✅ Server setup complete.")

    # ------ Execute benchmark on server ------
    print("⚡ [2/] Executing benchmark on server...")
    cmd = f"ssh glg1 && cd ~ && source ~/vllm-env/bin/activate && cd Quanti && python3 benchmark.py {args.llm} data/input/{os.path.basename(args.workload)}"

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Benchmark completed successfully")

        # Download results
        print("📥 3. Downloading results...")
        subprocess.run("scp -O glg1:~/Quanti/results/* ./results/ 2>/dev/null || true", shell=True)
        subprocess.run("scp -O glg1:~/Quanti/energy_*.json ./results/ 2>/dev/null || true", shell=True)
        subprocess.run("scp -O glg1:~/Quanti/benchmark_report_*.json ./results/ 2>/dev/null || true", shell=True)
        print("✅ Results downloaded to ./results/")
    else:
        print("❌ Benchmark failed")
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()