import atexit
import subprocess
import time

import requests

from Quanti import vllm_manager
from Quanti.utils import quote

ssh = 'ssh glg1'


def ssh_and_launch(llm: str, port: int = 8000) -> str:
    subprocess.run(f"{ssh} 'pkill -f \"vllm serve\" || true'", shell=True,
                   check=False)
    remote = "source ~/vllm-env/bin/activate && " + vllm_manager.cmd_serve_model(llm, gpu_memory_utilization=0.60, port=port)
    proc = subprocess.Popen(
        f"{ssh} {quote(remote)}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    atexit.register(proc.terminate)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if requests.get(f"{base}/health", timeout=2).ok:
                break
        except Exception:
            pass
        time.sleep(1)
    return f"{base}/v1"


def build_scp_command(ssh_config, local_path: str, remote_path: str) -> str:
    return f"scp -O {local_path} {ssh_config['user']}@{ssh_config['target_host']}:{remote_path}"
