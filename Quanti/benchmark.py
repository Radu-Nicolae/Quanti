import subprocess
import sys
import time
import os
import uuid
import requests
import pandas as pd
import json

from energy import EnergyMonitor
from utils import append_csv, now_tag, create_run_directory, get_workload_size
import vllm_manager


def cleanup_processes():
    print("🧹 Cleaning up vLLM processes...")
    subprocess.run('pkill -f "vllm serve" || true', shell=True)
    subprocess.run('pkill -f "nvidia-smi" || true', shell=True)
    print("✅ Process cleanup complete.")


def cleanup_everything():
    print("🧹 COMPLETE CLEANUP - Removing all traces...")
    cleanup_processes()

    print("🗑️ Removing ~/Quanti directory...")
    subprocess.run('rm -rf ~/Quanti || true', shell=True)
    print("✅ Complete cleanup done.")


def benchmark_setup(llm):
    """Setup the benchmark environment on the server."""
    print("🔧 Setting up benchmark environment...")

    # ----- Install requirements -----
    print("  📦 Installing requirements...")
    result = subprocess.run("pip install -r requirements.txt", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to install requirements: {result.stderr}")
        return False
    print(f"✅ Requirements installed")

    # ------ Clean up any existing vLLM processes ------
    print("  🔄 Stopping existing vLLM processes...")
    subprocess.run('pkill -f "vllm serve" || true', shell=True)
    time.sleep(5)
    print("  ✅ Cleaned up existing processes")

    # ------ Launch vLLM server ------
    print(f"  🚀 Launching vLLM server for model {llm}...")
    vllm_args = vllm_manager.cmd_serve_model(llm, port=8000)
    full_cmd = f"vllm serve {vllm_args}"

    proc = subprocess.Popen(
        full_cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    print("  ⏳ Waiting for vLLM server to start...")
    deadline = time.time() + 30  # max 30s to start... the RTX4090 may be slow, but can't be thaaaat slow

    while time.time() < deadline:
        if proc.poll() is not None:
            print(f"❌ vLLM process died with return code: {proc.returncode}")
            return False

        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.ok:
                print("  ✅ vLLM server is born! Time to party.")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(3)

    print("❌ vLLM server failed to start in time.")
    return False


def query_llm(prompt: str, llm: str) -> str:
    """Query the local vLLM server."""
    payload = {
        "model": vllm_manager.models[llm],
        "prompt": prompt,
        "max_tokens": 128,
        "temperature": 0.7
    }

    try:
        response = requests.post("http://localhost:8000/v1/completions", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["text"].strip()
    except Exception as e:
        return f"❌ Error querying LLM: {e}"


def run_workload(llm: str, workload_file: str, monitor: EnergyMonitor, run_dir: str = None):
    """ Execute the LLM workload and log results."""
    print(f"📝 Running workload file {workload_file} with model {llm}...")

    # Load workload
    try:
        df = pd.read_csv(workload_file)
        if 'text' not in df.columns:
            print("❌ Workload CSV must contain a 'text' column.")
            return False
    except Exception as e:
        print(f"❌ Failed to read workload file: {e}")
        return False

    # Choose output location based on run_dir
    if run_dir:
        os.makedirs(f"{run_dir}/detailed", exist_ok=True)
        results_file = f"{run_dir}/detailed/query_responses.csv"
    else:
        results_file = f"results/results_{llm}_{now_tag()}.csv"
        os.makedirs("results", exist_ok=True)

    print(f"🏃 Processing {len(df)} prompts...")

    start_time = time.time()
    for i, prompt in enumerate(df['text'], 1):
        reply = query_llm(prompt, llm)
        append_csv(results_file, i, prompt, reply)
        if i % 10 == 0:
            print(f"  [{i}/{len(df)}] processed")

    end_time = time.time()
    duration = end_time - start_time
    print(f"✅ Workload completed in {duration:.2f}s")
    print(f"📁 Results saved to: {results_file}")

    return {
        "results_file": results_file,
        "workload_duration_s": round(duration, 2),
        "n_prompts": len(df),
        "workload_size": get_workload_size(workload_file)
    }



def benchmark_main(llm: str, workload: str, output_dir: str = None):
    """Main benchmark function - runs entirely on server with energy monitoring to save headaches with local-server sync."""
    print(f"🎯 Starting benchmark: {llm} on {workload}")

    if llm not in vllm_manager.models:
        print(f"❌ Unsupported LLM model: {llm}")
        print(f"Supported models: {list(vllm_manager.models.keys())}")
        return False

    if not os.path.exists(workload):
        print(f"❌ Workload file does not exist: {workload}")
        return False

    run_dir = None
    if output_dir:
        run_dir = create_run_directory(output_dir, llm, workload)
        print(f"📁 Created run directory: {run_dir}")

    # Setup environment
    print("1️⃣ Setting up environment...")
    if not benchmark_setup(llm):
        print("❌ Setup failed")
        return False

    # Initialize energy monitoring with unique run name
    run_name = f"{llm}_{now_tag()}_{uuid.uuid4().hex[:6]}"
    if run_dir:
        monitor = EnergyMonitor(interval_ms=100, run_name=run_name, output_dir=run_dir)
    else:
        monitor = EnergyMonitor(interval_ms=100, run_name=run_name)

    print("2️⃣ Starting energy monitoring...")
    monitor.start()

    print("3️⃣ Running workload...")
    results = run_workload(llm, workload, monitor, run_dir)

    if results is None:
        print("❌ Workload execution failed")
        monitor.stop()
        return False

    print("4️⃣ Stopping energy monitoring...")
    energy_summary = monitor.stop(
        meta={
            "llm": llm,
            "workload": workload,
            **results
        }
    )

    if run_dir:
        report = f"{run_dir}/summary.json"
    else:
        report = f"benchmark_report_{run_name}.json"

    with open(report, "w") as f:
        json.dump(energy_summary, f, indent=2)

    print("\n" + "=" * 60)
    print("🎉 BENCHMARK COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"📊 Model: {llm}")
    print(f"📁 Workload: {workload}")
    print(f"⏱️  Duration: {results['workload_duration_s']:.2f}s")
    print(f"⚡ Avg Power: {energy_summary['avg_power_W']:.2f}W")
    print(f"🔋 Total Energy: {energy_summary['energy_Wh']:.4f}Wh")
    print(f"🖥️  Avg GPU Util: {energy_summary['avg_util_pct']:.1f}%")
    print(f"💾 Avg GPU Mem: {energy_summary['avg_mem_MiB']:.0f}MiB")
    print("=" * 60)
    print("📋 Output Files:")
    print(f"  📊 Benchmark Report: {report}")
    print(f"  📈 Query Results: {results['results_file']}")
    print(f"  ⚡ Energy Trace: {energy_summary['trace_csv']}")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        if len(sys.argv) < 3:
            print("Usage: python benchmark.py <llm_model> <workload_file> [output_dir]")
            print(f"Available models: {list(vllm_manager.models.keys())}")
            sys.exit(1)

        llm_model = sys.argv[1]
        workload_file = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else None

        success = benchmark_main(llm_model, workload_file, output_dir)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Benchmark failed with error: {e}")
        sys.exit(1)

