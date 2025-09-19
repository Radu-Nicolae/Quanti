from pathlib import Path
from llm_library import models
import os


def cmd_serve_model(model_name: str, gpu_util=0.85, max_model_len=4096):
    return f"vllm serve \"{models[model_name]}\" --max-model-len {max_model_len} --max-num-seqs 32 --gpu-memory-utilization {gpu_util}"

def cmd_ssh(user: str, jump_host: str, jump_port:str, target_host: str):
    return f"ssh -J {user}@{jump_host}:{jump_port} {user}@{target_host}"

def set_env(env_path: str = ".env") -> None:
    p = Path(env_path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"{env_path} not found")

    for raw in p.read_text().splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, v = stripped.split("=", 1)
            os.environ[k.strip()] = v.strip()