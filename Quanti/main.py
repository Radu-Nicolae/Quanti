from llm_library import models
from builder import cmd_serve_model

if __name__ == '__main__':
    for model in models.keys():
        cmd = cmd_serve_model(model)
        # let it run for 10 seconds, then kill it
        cmd += " & sleep 1; pkill -f 'vllm serve'; "
        print(cmd)
