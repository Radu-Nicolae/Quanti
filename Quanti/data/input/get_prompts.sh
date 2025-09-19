python - <<'PY'
import os
from datasets import load_dataset
import pandas as pd

N = 10000
ds = load_dataset("gretelai/synthetic_multilingual_llm_prompts", "main", split="train")
df = ds.to_pandas()[["prompt"]].rename(columns={"prompt": "text"}).head(N)
out = f"llm_workload_{N}.csv"
df.to_csv(out, index=False)
print(f"Saved → {out} | Rows: {len(df)}")
PY
