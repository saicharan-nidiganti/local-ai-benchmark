# Results

Curated results, one folder per experiment, named `<date>-<subject>`. Each folder holds:

| File | Contents |
| --- | --- |
| `README.md` | The finding, the setup, a results table and how to reproduce it |
| `summary.json` | `local-ai-benchmark summarize --run-id <run ID>`, exactly |
| `runs.jsonl` | Every measured run of that run ID, as recorded |
| `manifest.json` | The environment the run was measured in |

The raw log in `data/raw/` stays local; only runs chosen for publication are copied here, and
only when their prompts contain nothing personal or confidential.

| Experiment | Model | Finding |
| --- | --- | --- |
| [2026-11-13 baseline](2026-11-13-qwen3-4b-baseline/) | qwen3:4b | 30.8 tokens/s, 47 ms first token, 66% of the model on the 4 GB GPU, 320 J per 256-token answer |
