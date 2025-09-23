import argparse
import csv
from datetime import datetime
import os
import shlex

WORKLOAD = "data/input/llm_workload_100.csv"


def parse_args(argv=None):
    """
    Build and parse CLI arguments for this script.
    - LLM key (default: 'Llama-3-8B')
    - Input CSV with a 'text' column (default: WORKLOAD)
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Run an LLM workload over SSH and record energy metrics."
    )
    parser.add_argument(
        "llm",
        nargs="?",
        default="Llama-3-8B",
        help="LLM key (defaults to 'Llama-3-8B')."
    )
    parser.add_argument(
        "workload",
        nargs="?",
        default=WORKLOAD,
        help=f"Input CSV with a 'text' column (default: {WORKLOAD})."
    )
    return parser.parse_args(argv)


def append_csv(path: str, idx: int, prompt: str, reply: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    mode = "a" if os.path.isfile(path) else "w"
    with open(path, mode, newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if fh.tell() == 0: w.writerow(["idx", "prompt", "reply"])
        w.writerow([idx, prompt, reply])


def quote(cmd: str) -> str:
    return shlex.quote(cmd)


def now_tag():
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")