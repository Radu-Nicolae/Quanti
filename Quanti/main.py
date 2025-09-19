# main.py
import os, sys, csv, time, subprocess, atexit, requests, pandas as pd, json
import builder
from energy import EnergyMonitor, now_tag

CSV_IN = "data/input/llm_workload_100.csv"


def ssh_and_launch(model: str, port: int = 8000) -> str:
    builder.set_env()
    user = os.environ["SSH_USER"]
    jump = os.environ["SSH_JUMP_HOST"]
    jport = os.environ["SSH_JUMP_PORT"]
    target = os.environ["SSH_TARGET_HOST"]
    subprocess.run(f"ssh -J {user}@{jump}:{jport} {user}@{target} 'pkill -f \"vllm serve\" || true'", shell=True,
                   check=False)
    ssh = f"ssh -J {user}@{jump}:{jport} -L {port}:127.0.0.1:{port} {user}@{target}"
    remote = "source ~/vllm-env/bin/activate && " + builder.cmd_serve_model(model, gpu_memory_utilization=0.60,
                                                                            port=port)
    proc = subprocess.Popen(f"{ssh} {builder.quote(remote)}", shell=True, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, text=True)
    atexit.register(proc.terminate)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            if requests.get(f"{base}/health", timeout=2).ok:
                break
        except Exception:
            pass
        time.sleep(1)
    return f"{base}/v1"


def query_one(base_url: str, prompt: str, model: str) -> str:
    payload = {"model": builder.models[model], "prompt": prompt, "max_tokens": 128, "temperature": 0.7}
    r = requests.post(f"{base_url}/completions", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["text"].strip()


def append_csv(path: str, idx: int, prompt: str, reply: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    mode = "a" if os.path.isfile(path) else "w"
    with open(path, mode, newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if fh.tell() == 0: w.writerow(["idx", "prompt", "reply"])
        w.writerow([idx, prompt, reply])


if __name__ == "__main__":
    mdl = sys.argv[1] if len(sys.argv) > 1 else "Llama-3-8B"
    in_csv = sys.argv[2] if len(sys.argv) > 2 else CSV_IN
    rows = pd.read_csv(in_csv)
    run_name = f"{mdl}_{now_tag()}"
    mon = EnergyMonitor(interval_ms=100, out_dir="data/output/", run_name=run_name)
    results_csv = mon.results_csv
    base = ssh_and_launch(mdl)
    mon.start()
    t0 = time.time()
    for i, prompt in enumerate(rows["text"], 1):
        try:
            reply = query_one(base, prompt, mdl)
        except Exception as e:
            reply = f"__ERROR__: {e}"
        append_csv(results_csv, i, prompt, reply)
        if i % 5 == 0: print(f"[{i}/{len(rows)}] ok")
    t1 = time.time()
    summary = mon.stop(meta={
        "model": mdl,
        "n_prompts": int(len(rows)),
        "workload_duration_s": round(t1 - t0, 2),
    })
    print(json.dumps(summary, indent=2))
    print("Artifacts:")
    print(" -", summary["trace_csv"])
    print(" -", summary["results_csv"])
    print(" -", os.path.join("runs", run_name, "energy_summary.json"))
