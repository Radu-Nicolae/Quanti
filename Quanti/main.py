import sys

from Quanti.runner import ssh_and_launch
from llm_library import models
import builder
import os


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "Llama-3-8B"

    if target not in models:
        sys.exit(f"Unknown model: {target}")
    ssh_and_launch(target)