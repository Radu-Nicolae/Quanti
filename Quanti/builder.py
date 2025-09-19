from pathlib import Path
import os, shlex

# -------- Hugging-Face model aliases ----------------------------------------
models: dict[str, str] = {
    "Llama-3-8B":       "meta-llama/Llama-3.1-8B-Instruct",
    "Mistral-8B":       "solidrust/Mistral-NeMo-Minitron-8B-Base-AWQ",
    "Granite-8B":       "ibm-granite/granite-3.3-8b-base",
    "Llama-3-8B-AWQ":   "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4",
    "Granite-8B-AWQ":   "RedHatAI/granite-3.1-8b-instruct-quantized.w4a16",
    "Mistral-8B-AWQ":   "solidrust/Mistral-NeMo-Minitron-8B-Base-AWQ",
}

# -------- env / SSH helpers -------------------------------------------------
def set_env(env_path: str = ".env") -> None:
    """Load KEY=VAL lines into os.environ."""
    p = Path(env_path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(env_path)
    for raw in p.read_text().splitlines():
        if raw.strip() and not raw.lstrip().startswith("#") and "=" in raw:
            k, v = raw.split("=", 1)
            os.environ[k.strip()] = v.strip()

def cmd_ssh(user: str, jump: str, jport: str, target: str) -> str:
    """Return an SSH command that tunnels through a bastion."""
    return f"ssh -J {user}@{jump}:{jport} {user}@{target}"

# -------- vLLM invocation ---------------------------------------------------
def cmd_serve_model(
    name: str,
    gpu_memory_utilization: float = 0.60,   # 60 % of free VRAM
    max_len: int = 4_096,
    port: int = 8_000,
) -> str:
    repo = models[name]
    return (
        f'vllm serve "{repo}" '
        f"--port {port} "
        f"--max-model-len {max_len} "
        f"--max-num-seqs 32 "
        f"--gpu-memory-utilization {gpu_memory_utilization}"
    )

def quote(cmd: str) -> str:
    """POSIX-quote a whole command for remote execution."""
    return shlex.quote(cmd)
