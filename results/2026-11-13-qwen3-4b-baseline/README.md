# Baseline: qwen3:4b on the reference laptop

Run ID `20261112T210913Z-67d5d8` · measured 2026-11-12 21:09 UTC (2026-11-13, India time) ·
harness commit [`85020ac`](https://github.com/saicharan-nidiganti/local-ai-benchmark/commit/85020ac)
(clean tree) · issue [#17](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/17)

qwen3:4b generates **30.8 tokens per second** with a **47 ms** first token once loaded, and
runs repeat within 1% of each other. Only **66% of the model fits in the 4 GB GPU**, so a third
of it runs from system memory; each 256-token answer costs about **320 J** of GPU energy.

## Setup

| Item | Value |
| --- | --- |
| Model | `qwen3:4b`, Q4_K_M, 4.0B parameters, digest `359d7dd4bcda` |
| Runtime | Ollama 0.40.16 on `localhost:11434` |
| Machine | Ryzen 9 5900HX, RTX 3050 Laptop GPU 4 GB (driver 617.14), 15.4 GB RAM, Windows 11, on AC power |
| Prompt | "Explain TCP vs UDP in 5 bullet points." |
| Settings | temperature 0, seed 42, context 4096 tokens, 256 output tokens, thinking off |
| Protocol | 1 warm-up run (not recorded), then 5 measured runs; resources sampled every 0.5 s |

Full environment: [manifest.json](manifest.json).

## Results

All 5 runs succeeded; each produced 256 tokens and the same 1,206-character reply.

| Metric | p50 | p90 | Min | Max | IQR |
| --- | --- | --- | --- | --- | --- |
| Total latency (ms) | 8,370 | 8,443 | 8,346 | 8,475 | 45 |
| Time to first token (ms) | 46.8 | 63.1 | 44.0 | 64.1 | 16.2 |
| Decode speed (tokens/s) | 30.8 | 30.9 | 30.4 | 30.9 | 0.2 |
| Prefill speed (tokens/s) | 600 | 615 | 591 | 618 | 12 |
| Model share in GPU memory (%) | 66.3 | 66.3 | 66.3 | 66.3 | 0 |
| Peak GPU memory (MiB) | 2,315 | 2,315 | 2,315 | 2,315 | 0 |
| Peak runtime memory (MiB) | 1,763 | 1,763 | 1,723 | 1,763 | 0.4 |
| Mean GPU power (W) | 38.2 | 39.4 | 37.2 | 39.9 | 0.5 |
| GPU energy per run (J) | 320 | 329 | 315 | 333 | 4.2 |

Exact values: [summary.json](summary.json). Every measured run: [runs.jsonl](runs.jsonl).

## What it shows

- **Steady once loaded.** Decode speed varies by 0.2 tokens/s across runs. The 45% swing seen
  on 2026-09-25 came from cold starts and machine state, which warm-up and the manifest now
  control and record.
- **Memory is the constraint.** At a 4096-token context Ollama places 2.3 GB on the GPU and
  keeps the rest (1.8 GB in the model runner) in system memory. Decode speed is therefore
  bounded by the CPU-resident layers, not by the GPU alone; a smaller model or context is
  the lever ([#23](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/23)).
- **Energy is measurable.** About 1.25 J of GPU energy per output token, the input to the
  cost analysis ([#29](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/29)).
  It covers the GPU board only.

## Reproduce

```bash
uv run local-ai-benchmark benchmark --model qwen3-4b \
  --prompt "Explain TCP vs UDP in 5 bullet points."
uv run local-ai-benchmark summarize            # the run just recorded
```

Settings come from [configs/benchmark.yaml](../../configs/benchmark.yaml). Compare a new run
with this one only on the same machine state: plugged in, idle, same Ollama version.
