import subprocess
import time
import os

from Quanti import vllm


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





def benchmark_main(llm, workload):
    """
    Benchmark main is the main function for benchmarking LLMs on the server side. This function
    runs an LLM workload, logs results, and monitors metrics (e.g., energy consumption) during the run.
    This function runs on the server side. However, the benchmark file also gives back to the
    client side some information about the run and tells live progress.
    """
    benchmark_setup(llm, workload)
