# energy.py
import os, subprocess, threading, time, csv, json, uuid
from datetime import datetime
import builder

def now_tag():
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

class EnergyMonitor:
    def __init__(self, interval_ms=200, out_dir="runs", run_name=None):
        self.interval_ms = interval_ms
        self.run_name = run_name or f"run_{now_tag()}_{uuid.uuid4().hex[:6]}"
        self.out_dir = os.path.join(out_dir, self.run_name)
        self.trace_csv = os.path.join(self.out_dir, "energy_trace.csv")
        self.summary_json = os.path.join(self.out_dir, "energy_summary.json")
        self.results_csv = os.path.join(self.out_dir, "results.csv")
        self._proc = None
        self._thr = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.samples = 0
        self.sum_power = 0.0
        self.max_power = 0.0
        self.sum_util = 0.0
        self.max_util = 0.0
        self.sum_mem = 0.0
        self.max_mem = 0.0
        self.t0 = None
        self.t1 = None

    def start(self):
        builder.set_env()
        os.makedirs(self.out_dir, exist_ok=True)
        ssh = builder.cmd_ssh(
            os.environ["SSH_USER"], os.environ["SSH_JUMP_HOST"],
            os.environ["SSH_JUMP_PORT"], os.environ["SSH_TARGET_HOST"]
        )
        q = "timestamp,power.draw,utilization.gpu,memory.used,memory.total"
        cmd = f"nvidia-smi --query-gpu={q} --format=csv,noheader,nounits -lms {self.interval_ms}"
        self._proc = subprocess.Popen(
            f"{ssh} {builder.quote(cmd)}",
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1
        )
        self.t0 = time.time()
        f = open(self.trace_csv, "w", newline="", encoding="utf-8")
        writer = csv.writer(f)
        writer.writerow(["t_local_s","timestamp","power_W","util_pct","mem_used_MiB","mem_total_MiB"])
        def run():
            tstart = self.t0
            for line in self._proc.stdout:
                if self._stop.is_set():
                    break
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 5:
                    continue
                tloc = time.time() - tstart
                try:
                    pwr = float(parts[1]); util = float(parts[2]); memu = float(parts[3]); memt = float(parts[4])
                except:
                    continue
                writer.writerow([f"{tloc:.3f}", parts[0], f"{pwr:.2f}", f"{util:.2f}", f"{memu:.2f}", f"{memt:.2f}"])
                with self._lock:
                    self.samples += 1
                    self.sum_power += pwr
                    if pwr > self.max_power: self.max_power = pwr
                    self.sum_util += util
                    if util > self.max_util: self.max_util = util
                    self.sum_mem += memu
                    if memu > self.max_mem: self.max_mem = memu
            f.flush(); f.close()
        self._thr = threading.Thread(target=run, daemon=True)
        self._thr.start()

    def stop(self, meta=None):
        self._stop.set()
        try:
            if self._proc: self._proc.terminate()
        except: pass
        if self._thr: self._thr.join(timeout=5)
        if self._proc:
            try: self._proc.wait(timeout=5)
            except: pass
        self.t1 = time.time()
        dur_s = max(0.0, (self.t1 - self.t0) if self.t0 else 0.0)
        with self._lock:
            n = max(1, self.samples)
            avg_p = self.sum_power / n
            avg_u = self.sum_util / n
            avg_m = self.sum_mem / n
            energy_Wh = (self.sum_power * (self.interval_ms/1000.0) / 3600.0)
        summary = {
            "run_name": self.run_name,
            "duration_s": round(dur_s, 2),
            "samples": self.samples,
            "avg_power_W": round(avg_p, 2),
            "max_power_W": round(self.max_power, 2),
            "avg_util_pct": round(avg_u, 2),
            "max_util_pct": round(self.max_util, 2),
            "avg_mem_MiB": round(avg_m, 2),
            "max_mem_MiB": round(self.max_mem, 2),
            "energy_Wh": round(energy_Wh, 2),
            "trace_csv": self.trace_csv,
            "results_csv": self.results_csv,
        }
        if isinstance(meta, dict):
            summary.update(meta)
        with open(self.summary_json, "w") as f:
            json.dump(summary, f, indent=2)
        return summary
