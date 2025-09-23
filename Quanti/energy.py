import csv
import json
import os
import subprocess
import threading
import time
from utils import now_tag


class EnergyMonitor:
    def __init__(self, interval_ms=100, run_name=None, output_dir=None):
        self.interval_ms = interval_ms
        self.run_name = run_name or now_tag()
        self.output_dir = output_dir

        if output_dir:
            self.out_dir = output_dir
            self.detailed_dir = os.path.join(output_dir, "detailed")
            os.makedirs(self.detailed_dir, exist_ok=True)
            self.trace_csv = os.path.join(self.detailed_dir, "energy_trace.csv")
            self.summary_json = os.path.join(output_dir, "energy_summary.json")
        else:
            self.out_dir = f"energy_traces"
            os.makedirs(self.out_dir, exist_ok=True)
            self.trace_csv = os.path.join(self.out_dir, f"{self.run_name}_trace.csv")
            self.summary_json = os.path.join(self.out_dir, f"{self.run_name}_summary.json")

        self._proc = None
        self._thr = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

        # Metrics
        self.samples = 0
        self.sum_power = 0.0
        self.avg_power = 0.0
        self.sum_util = 0.0
        self.avg_util = 0.0
        self.sum_mem = 0.0
        self.avg_mem = 0.0
        self.t0 = None
        self.t1 = None

    def start(self):
        """Start energy monitoring using nvidia-smi which is already surviving ok on the server."""
        print(f"⚡ Starting energy monitoring (interval: {self.interval_ms}ms)")

        q = "timestamp,power.draw,utilization.gpu,memory.used,memory.total"
        cmd = f"nvidia-smi --query-gpu={q} --format=csv,noheader,nounits -lms {self.interval_ms}"

        self._proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        self.t0 = time.time()
        f = open(self.trace_csv, "w", newline='', encoding='utf-8')
        writer = csv.writer(f)
        writer.writerow(["t_local_s", "timestamp", "power_W", "util_pct", "mem_used_MB", "mem_total_MB"])

        def monitoring_loop():
            """Thread to collect energy data which is happily running in the background."""
            tstart = self.t0
            try:
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
                        power = float(parts[1])
                        util = float(parts[2])
                        mem_used = float(parts[3])
                        mem_total = float(parts[4])
                    except ValueError:
                        continue

                    writer.writerow([f"{tloc:.3f}", parts[0], f"{power:.1f}", f"{util:.1f}", f"{mem_used:.1f}", f"{mem_total:.1f}"])

                    # Would be nice to also update the totals
                    with self._lock:
                        self.samples += 1
                        self.sum_power += power
                        self.sum_util += util
                        self.sum_mem += mem_used

            except Exception as e:
                print("❌ Error in energy monitoring thread:", e)
            finally:
                f.flush()
                f.close()

        self._thr = threading.Thread(target=monitoring_loop, daemon=True)
        self._thr.start()

        print("✅ Energy monitoring started. We're logging to", self.trace_csv)

    def stop(self, meta=None, save_file=False):
        """Stop monitoring and return summary. If save_file=True, also write to self.summary_json."""
        self._stop.set()

        # Terminate nvidia-smi process
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except:
                try:
                    self._proc.kill()
                except:
                    pass

        # Wait for monitoring thread
        if self._thr:
            self._thr.join(timeout=10)

        self.t1 = time.time()
        duration_s = max(0.0, (self.t1 - self.t0) if self.t0 else 0.0)

        # Compute averages
        with self._lock:
            if self.samples > 0:
                avg_power = self.sum_power / self.samples
                avg_util = self.sum_util / self.samples
                avg_mem = self.sum_mem / self.samples
            else:
                avg_power = 0.0
                avg_util = 0.0
                avg_mem = 0.0

        energy_wh = (avg_power * duration_s) / 3600.0

        # Build concise summary
        summary = {
            "run_name": self.run_name,
            "duration_s": round(duration_s, 2),
            "interval_ms": self.interval_ms,
            "samples": self.samples,
            "avg_power_W": round(avg_power, 2),
            "avg_util_pct": round(avg_util, 2),
            "avg_mem_MiB": round(avg_mem, 2),
            "energy_Wh": round(energy_wh, 4),
            "trace_csv": self.trace_csv,
        }

        if isinstance(meta, dict):
            summary.update(meta)

        # Only write to disk if explicitly requested
        if save_file:
            with open(self.summary_json, "w") as f:
                json.dump(summary, f, indent=2)

        print("✅ Energy monitoring complete:")
        print(f"   Duration: {duration_s:.2f}s")
        print(f"   Samples: {self.samples}")
        print(f"   Avg Power: {avg_power:.2f}W")
        print(f"   Total Energy: {energy_wh:.4f}Wh")
        if save_file:
            print(f"   Summary saved: {self.summary_json}")
        else:
            print("   Summary saved: skipped (returned to caller)")

        return summary

    def get_current_stats(self):
        """Get current monitoring statistics without stopping. Would be amazing to actually make this live-work :D."""
        with self._lock:
            if self.samples > 0:
                return {
                    "samples": self.samples,
                    "avg_power_W": round(self.sum_power / self.samples, 2),
                    "avg_util_pct": round(self.sum_util / self.samples, 2),
                    "avg_mem_MiB": round(self.sum_mem / self.samples, 2),
                    "duration_s": round(time.time() - self.t0, 2) if self.t0 else 0
                }
            else:
                return {
                    "samples": 0,
                    "avg_power_W": 0.0,
                    "avg_util_pct": 0.0,
                    "avg_mem_MiB": 0.0,
                    "duration_s": 0.0
                }
