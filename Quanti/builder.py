from llm_library import models

def cmd_serve_model(model_name: str, gpu_util=0.85, max_model_len=4096):
    return f"vllm serve \"{models[model_name]}\" --max-model-len {max_model_len} --max-num-seqs 32 --gpu-memory-utilization {gpu_util}"