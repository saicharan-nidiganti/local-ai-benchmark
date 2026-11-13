# Reference environment

Last verified: 2026-11-13 ([#2](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/2))

Every published result names the machine and software it came from. This is the reference
machine; results from any other machine must record the same items. The harness writes them
automatically, once per run ID, to `data/raw/manifests.jsonl`
([ADR-0007](decisions/0007-run-identity-and-manifests.md)).

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
| `llama3.2:3b` | `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` | GGUF | 3.2B | Q4_K_M | 2.0 GB |
| `qwen3:4b-instruct` | `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` | GGUF | 4.0B | Q4_K_M | 2.5 GB |
| `phi4-mini` | `78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753` | GGUF | 3.8B | Q4_K_M | 2.5 GB |
| `phi4-mini:3.8b-q8_0` | `0be8e69791811df9c91db1286c7fa09df489b4d075def36de77f050a4394f214` | GGUF | 3.8B | Q8_0 | 4.1 GB |
| `gemma3:4b` | `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7` | GGUF | 3.9B | Q4_K_M | 3.3 GB |

Capabilities as Ollama reports them: qwen3:4b and qwen3:4b-instruct `completion, tools,
thinking`; llama3.2:3b and phi4-mini `completion, tools`; gemma3:4b `completion, vision`. The
plain `qwen3:4b` tag is a thinking build; `qwen3:4b-instruct` is its instruct twin.

The comparison uses qwen3:4b-instruct, phi4-mini and llama3.2:3b
([ADR-0010](decisions/0010-three-models-to-compare.md)).

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

## Thinking off on a non-thinking model

One `ask` request to llama3.2:3b on 2026-11-13 with the default `think: false`, to check that
the setting is harmless on a model that cannot think
([#11](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/11)). Cold start, default
settings.

| Metric | Value |
| --- | --- |
| Result | No error; a 1,342-character reply |
| TTFT | 3.6 s, of which model load 3.5 s |
| Decode throughput | 57.8 tokens/s over 256 tokens |
| Memory placement | 2.35 GB of 2.94 GB on the GPU (about 80%), 4096-token context |

Even this 3B model does not fully fit in the 4 GB of VRAM at a 4096-token context, which
makes the context length a variable worth measuring in the comparison
([#23](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/23)).

## Baseline

The first full benchmark on this machine is published in
[results/2026-11-13-qwen3-4b-baseline](../results/2026-11-13-qwen3-4b-baseline/): qwen3:4b at
30.8 tokens/s and 47 ms to the first token once loaded, with 66% of the model on the GPU.

## Recording your own environment

```bash
ollama --version
ollama show qwen3:4b          # parameters, quantization, context length
ollama ps                     # while a model is loaded: size and the GPU/CPU split
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

For measurements, plug the laptop in, close other GPU applications, and keep the machine idle.
