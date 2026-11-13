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
| `cold_starts.json` | The summary of each model's cold benchmark, when the report judges latency targets |
| `cost.json` | The cost assumptions and each model's cost, when the report is run with `--cost` |

The raw log in `data/raw/` stays local; only runs chosen for publication are copied here, and
only when their prompts contain nothing personal or confidential.

| Experiment | Model | Finding |
| --- | --- | --- |
| [2026-11-13 a priority rubric](2026-11-13-priority-rubric/) | qwen3:4b-instruct, phi4-mini, llama3.2:3b | The rubric prompt takes priority from 9 to 15 and from 8 to 14 of 15 for qwen3:4b-instruct and phi4-mini, with categories unchanged and no measurable time cost; llama3.2:3b swaps over-escalation for under-escalation |
| [2026-11-13 JSON from the schema or the prompt, with repair](2026-11-13-json-mode-and-repair/) | qwen3:4b-instruct, phi4-mini, llama3.2:3b, qwen3:4b | Prompt-only JSON is valid for the three instruct models (phi4-mini fences 27 of 30, 22% slower); the thinking build fails all 30 and two repairs each rescue none; schema mode stays the default |
| [2026-11-13 phi4-mini, Q4_K_M against Q8_0](2026-11-13-phi4-mini-q4-vs-q8/) | phi4-mini, phi4-mini:3.8b-q8_0 | Q8_0 does not fit in 4 GB (44% on the GPU against 64%): 2.3 times slower, 1.8 times the GPU energy per task, 0.909 against 0.887 quality, mostly better priorities; Q4_K_M stays the pick |
| [2026-11-13 the triage app, offline](2026-11-13-offline-app/) | phi4-mini | With networking off, the command and the web page answer every ticket in about 3 s with the model loaded; a foreign Host header is refused |
| [2026-11-13 privacy, latency and cost, offline](2026-11-13-offline-privacy-latency-cost/) | qwen3:4b-instruct, phi4-mini, llama3.2:3b | With networking off, the same 135 replies and 0 connections to another machine; every model meets every latency target; GPU electricity costs 5 to 16 times less than the hosted price per token, but buying the laptop for this alone costs 2 to 6 times more |
| [2026-11-13 three-model comparison](2026-11-13-three-model-comparison/) | qwen3:4b-instruct, phi4-mini, llama3.2:3b | phi4-mini is the best tradeoff: the quality of qwen3:4b-instruct (0.89) at 14% more speed; llama3.2:3b is 1.75 times faster but weaker at summaries (0.81 overall) |
| [2026-11-13 baseline](2026-11-13-qwen3-4b-baseline/) | qwen3:4b | 30.8 tokens/s, 47 ms first token, 66% of the model on the 4 GB GPU, 320 J per 256-token answer |
