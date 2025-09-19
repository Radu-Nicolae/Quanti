import subprocess, os, shlex, sys, time
import builder                     # your helper module
from llm_library import models

def ssh_and_launch(model: str, t_out: int = 300) -> None:
    """SSH → source venv → vLLM serve → live-stream logs."""
    builder.set_env()                                  # read .env

    # 1 jump-host SSH string
    ssh = builder.cmd_ssh(
        os.environ["SSH_USER"],
        os.environ["SSH_JUMP_HOST"],
        os.environ["SSH_JUMP_PORT"],
        os.environ["SSH_TARGET_HOST"],
    )

    # 2 remote command: activate venv **then** run vLLM
    venv     = "source ~/vllm-env/bin/activate"
    serve    = builder.cmd_serve_model(model)
    remote   = f"{venv} && {serve}"                   # chain with &&

    # 3 quote the whole remote side and append to ssh
    full_cmd = f"{ssh} {shlex.quote(remote)}"
    print("Executing:", full_cmd, flush=True)

    # 4 launch and stream output
    with subprocess.Popen(
        full_cmd, shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True, bufsize=1
    ) as proc:
        start = time.time()
        for line in proc.stdout:                      # stream live
            print(line, end="")
            if ("Uvicorn running" in line
                    or "API server version" in line
                    or time.time() - start > t_out):
                break                                 # ready or timeout

        proc.terminate(); proc.wait(10)               # free GPU