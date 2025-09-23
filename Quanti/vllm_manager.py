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
        gpu_memory_utilization: float = 0.85,
        max_len: int = 2_048,
        port: int = 8_000,
) -> str:
    """Generate vLLM serve command - FIXED version"""
    repo = models[alias]

    # Generate arguments for API server module
    args = [
        f'"{repo}"',
        f"--port {port}",
        f"--max-model-len {max_len}",
        f"--max-num-seqs 32",
        f"--gpu-memory-utilization {gpu_memory_utilization}",
        "--host 0.0.0.0",
        "--trust-remote-code",
    ]

    return " ".join(args)
