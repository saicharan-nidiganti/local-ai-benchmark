# Reference environment

Last verified: 2026-11-13 ([#2](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/2))

Every published result names the machine and software it came from. This is the reference
machine; results from any other machine must record the same items. From Phase 1 the harness
writes them automatically into an environment manifest
([#14](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/14)).

## Hardware

| Component | Value |
| --- | --- |
| Model | ASUS ROG Strix G513QC |
| CPU | AMD Ryzen 9 5900HX (8 cores, 16 threads) |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU, 4 GB (driver 617.14) |
| Integrated GPU | AMD Radeon Graphics (not used by Ollama) |
| Memory | 15.4 GB usable |

## Software

| Component | Value |
| --- | --- |
| Operating system | Windows 11 |
| Ollama | 0.40.16, installed with `winget install Ollama.Ollama`, serving `localhost:11434` |
| Python | 3.14.6 locally; 3.11 to 3.14 supported and tested in CI |
| Environment | uv 0.13.7, from `uv.lock` |

## Models

| Tag | Digest | Format | Parameters | Quantization | Size on disk |
| --- | --- | --- | --- | --- | --- |
| `qwen3:4b` | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` | GGUF | 4.0B | Q4_K_M | 2.5 GB |

The three models for the comparison are chosen in
[#23](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/23).

## First live run

One `ask` request on 2026-11-13, cold start, default settings (output limit 256 tokens,
temperature 0). It is a smoke check, not a benchmark: one run, model not yet loaded.

| Metric | Value |
| --- | --- |
| TTFT | 56.3 s, of which model load 32.4 s and prompt evaluation 23.8 s |
| Decode throughput | 31.3 tokens/s over 256 tokens |
| Memory placement | 2.34 GB of 3.53 GB on the GPU (about 66%), 4096-token context |

At a 4096-token context, qwen3:4b does not fully fit in 4 GB of VRAM: Ollama keeps about a
third of it on the CPU. GPU offload is therefore recorded with every run from Phase 1
([#15](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/15)) and is a
criterion for choosing models ([#23](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/23)).

## Recording your own environment

```bash
ollama --version
ollama show qwen3:4b          # parameters, quantization, context length
ollama ps                     # while a model is loaded: size and the GPU/CPU split
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

For measurements, plug the laptop in, close other GPU applications, and keep the machine idle.
