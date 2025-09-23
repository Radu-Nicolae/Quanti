from pathlib import Path
import os, shlex

# -------- Hugging-Face model aliases ----------------------------------------
models: dict[str, str] = {
    "Llama-3-8B": "meta-llama/Llama-3.1-8B-Instruct",
    "Mistral-8B": "solidrust/Mistral-NeMo-Minitron-8B-Base-AWQ",
    "Granite-8B": "ibm-granite/granite-3.3-8b-base",
    "Llama-3-8B-AWQ": "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4",
    "Granite-8B-AWQ": "RedHatAI/granite-3.1-8b-instruct-quantized.w4a16",
    "Mistral-8B-AWQ": "solidrust/Mistral-NeMo-Minitron-8B-Base-AWQ",
}


def cmd_serve_model(
        alias: str,
        gpu_memory_utilization: float = 0.60,
        max_len: int = 4_096,
        port: int = 8_000,
        timeout: int = 30,
) -> str:
    repo = models[alias]
    # add also timeout
    return (
        f'vllm serve "{repo}" '
        f"--port {port} "
        f"--max-model-len {max_len} "
        f"--max-num-seqs 32 "
        f"--gpu-memory-utilization {gpu_memory_utilization}"
        f" --timeout {timeout}"
    )
