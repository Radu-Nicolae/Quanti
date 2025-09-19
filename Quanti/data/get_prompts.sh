python - <<'PY'
from datasets import load_dataset
import pandas as pd

ds = load_dataset("gretelai/synthetic_multilingual_llm_prompts", "main", split="train")
df = ds.to_pandas()[["prompt"]].rename(columns={"prompt": "text"}).head(10)
df.to_csv("llm_workload_10.csv", index=False)
print("Saved → llm_workload_10.csv | Rows:", len(df))
PY
