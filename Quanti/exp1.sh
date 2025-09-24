#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

OUT="data/outputs"
WORKLOADS=("data/input/llm_workload_10.csv" "data/input/llm_workload_100.csv" "data/input/llm_workload_1000.csv")
MODELS=("Llama-3-8B" "Mistral-8B" "Granite-8B" "Llama-3-8B-AWQ" "Granite-8B-AWQ" "Mistral-8B-AWQ")
REPEATS=30

for m in "${MODELS[@]}"; do
  for w in "${WORKLOADS[@]}"; do
    wl_name="$(basename "$w" .csv)"           # e.g., llm_workload_10
    base_dir="${OUT}/${m}_${wl_name}"         # e.g., data/outputs/Llama-3-8B_llm_workload_10
    mkdir -p "$base_dir"

    echo "=== $m | $(basename "$w") ==="
    for ((r=0; r<REPEATS; r++)); do
      run_tag="$(printf 'r%02d' "$r")"        # r00, r01, ...
      run_dir="${base_dir}/${run_tag}_${m}_${wl_name}"

      echo "-- ${run_tag} / ${REPEATS} --"
      PYTHONPATH="$(pwd)/.." python3 -m Quanti.main "$m" "$w" --output-dir "$run_dir"
    done
  done
done
