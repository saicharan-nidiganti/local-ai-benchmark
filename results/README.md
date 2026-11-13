# Results

Curated results, one folder per experiment, named `<date>-<subject>`. Every folder has a
`README.md` with the finding, the setup, the tables and how to reproduce it.

A single-model benchmark also holds:

| File | Contents |
| --- | --- |
| `summary.json` | `local-ai-benchmark summarize --run-id <run ID>`, exactly |
| `runs.jsonl` | Every measured run of that run ID, as recorded |
| `manifest.json` | The environment the run was measured in |

A comparison, written by `local-ai-benchmark report`, also holds:

| File | Contents |
| --- | --- |
| `quality_vs_speed.svg` | Overall quality against median decode speed, one point per model |
| `summaries.json` | The suite summary of each compared run, exactly |
| `manifests.json` | The environment of each compared run |

The raw log in `data/raw/` stays local; only runs chosen for publication are copied here, and
only when their prompts contain nothing personal or confidential.

| Experiment | Model | Finding |
| --- | --- | --- |
| [2026-11-13 three-model comparison](2026-11-13-three-model-comparison/) | qwen3:4b-instruct, phi4-mini, llama3.2:3b | phi4-mini is the best tradeoff: the quality of qwen3:4b-instruct (0.89) at 14% more speed; llama3.2:3b is 1.75 times faster but weaker at summaries (0.81 overall) |
| [2026-11-13 baseline](2026-11-13-qwen3-4b-baseline/) | qwen3:4b | 30.8 tokens/s, 47 ms first token, 66% of the model on the 4 GB GPU, 320 J per 256-token answer |
