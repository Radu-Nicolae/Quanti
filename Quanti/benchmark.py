import subprocess
import time
import os
import uuid

import requests

from Quanti import vllm
from Quanti.energy import EnergyMonitor
from Quanti.utils import append_csv, now_tag


def benchmark_setup(llm, workload):
    """Setup the benchmark environment on the server."""
    print("🔧 Setting up benchmark environment...")

    # ----- Install requirements -----
    print("  📦 Installing requirements...")
    result = subprocess.run("pip install -r requirements.txt", shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Failed to install requirements: {result.stderr.strip()}")
        return False

    print(f"✅ Requirements installed")

    # ------ Clean up any existing vLLM processes ------
    print("  🔄 Stopping existing vLLM processes...")
    subprocess.run('pkill -f "vllm serve" || true', shell=True)
    time.sleep(5)
    print("  ✅ Cleaned up existing processes")

    # ------ Launch vLLM server ------
    print(f"  🚀 Launching vLLM server for model {llm}...")
    vllm_cmd = f"source ~/vllm-env/bin/activate && {vllm.cmd_serve_model(llm, port=8000)}"

    # ----- Start vLLM in the background -----
    proc = subprocess.Popen(
        vllm_cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("  ⏳ Waiting for vLLM server to start...")
    deadline = time.time() + 30 # max 30s to start... the RTX4090 may be slow, but can't be thaaaat slow

    while time.time() < deadline:
        try:
            response = subprocess.get("http://localhost:8000/", timeout=2)
            if response.ok:
                print("  ✅ vLLM server is born! Time to party.")
                return True
        except:
            pass
        time.sleep(2)

    print("❌ vLLM server failed to start in time.")
    return False


def query_llm(prompt: str, llm: str) -> str:
    """Query the local vLLM server."""
    payload = {
        "model": vllm.models[llm],
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


def run_workload(llm: str, workload_file: str, monitor: EnergyMonitor):
    """ Execute the LLM workload and log results."""
    print("📝 Running workload file {workload_file} with model {llm}...")

    # Load workload
    try:
        df = pd.read_csv(workload_file)
        if 'text' not in df.columns:
            print("❌ Workload CSV must contain a 'text' column.")
            return False
    except Exception as e:
        print(f"❌ Failed to read workload file: {e}")
        return False

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
        "n_prompts": len(df)
    }


def benchmark_main(llm: str, workload: str):
    """Main benchmark function - runs entirely on server with energy monitoring to save headaches with local-server sync."""
    print(f"🎯 Starting benchmark: {llm} on {workload}")

    if llm not in vllm.models:
        print(f"❌ Unsupported LLM model: {llm}")
        print(f"Supported models: {list(vllm.models.keys())}")
        return False

    if not os.path.exists(workload):
        print(f"❌ Workload file does not exist: {workload}")
        return False

        # Setup environment
        print("1️⃣ Setting up environment...")
        if not benchmark_setup(llm):
            print("❌ Setup failed")
            return False

        # Initialize energy monitoring with unique run name
        run_name = f"{llm}_{now_tag()}_{uuid.uuid4().hex[:6]}"
        monitor = EnergyMonitor(interval_ms=100, run_name=run_name)

        print("2️⃣ Starting energy monitoring...")
        monitor.start()

        print("3️⃣ Running workload...")
        result = run_workload(llm, workload, monitor)

        if result is not None:
            print("❌ Workload execution failed")
            monitor.stop()
            return False

        print("4️⃣ Stopping energy monitoring...")
        energy_summary = monitor.stop(
            meta={
                "llm": llm,
                "workload": workload,
                **result
            }
        )

        report = f"benchmark_report_{run_name}.json"
        with open(report, "w") as f:
            json.dump(energy_summary, f, indent=2)

        print("\n" + "=" * 60)
        print("🎉 BENCHMARK COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📊 Model: {llm}")
        print(f"📁 Workload: {workload}")
        print(f"⏱️  Duration: {workload_results['workload_duration_s']:.2f}s")
        print(f"📈 Queries: {workload_results['n_prompts']} ({workload_results['success_rate']:.1f}% success)")
        print(f"⚡ Avg Power: {energy_summary['avg_power_W']:.2f}W")
        print(f"🔋 Total Energy: {energy_summary['energy_Wh']:.4f}Wh")
        print(f"🖥️  Avg GPU Util: {energy_summary['avg_util_pct']:.1f}%")
        print(f"💾 Avg GPU Mem: {energy_summary['avg_mem_MiB']:.0f}MiB")
        print("=" * 60)
        print("📋 Output Files:")
        print(f"  📊 Benchmark Report: {report_file}")
        print(f"  📈 Query Results: {workload_results['results_file']}")
        print(f"  ⚡ Energy Trace: {energy_summary['trace_csv']}")
        print(f"  📝 Energy Summary: {energy_summary['summary_json']}")
        print("=" * 60)

        return True





