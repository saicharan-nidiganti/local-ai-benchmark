# ADR-0010: The three models to compare

- **Status:** Accepted (owner's choice, 2026-11-13)
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#23](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/23)
- **Requirements:** FR-7, NFR-1

## Context

The comparison runs three small models on the reference laptop: an RTX 3050 with 4 GB of
VRAM. At a 4096-token context none of the 3B to 4B models fits entirely on the GPU, so how much
of each one does is itself a result. The baseline also showed that the plain `qwen3:4b` tag is
a thinking build: with thinking off it narrates its reasoning in the reply
([ADR-0009](0009-structured-output-for-json-tasks.md)).

## Decision drivers

1. Small enough to run on the reference GPU, at least partly.
2. Answers directly, without hidden reasoning, as a triage app needs.
3. Different vendors and licences, so the comparison says something about the field.
4. A visible quality-against-speed tradeoff, so the report has a decision to make.

## Options considered

Screening on 2026-11-13: three tickets (T04, T10, T13), nine tasks, structured output, one run
each after a warm-up; Ollama 0.40.16, 4096-token context.

| Model | Licence | Parameters, quantization | Loaded size | On GPU | Score | Decode speed | Median latency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **qwen3:4b-instruct** (Qwen3-4B-Instruct-2507) | Apache-2.0 | 4.0B, Q4_K_M | 3.29 GiB | 66% | 0.94 | 30.4 tokens/s | 1.5 s |
| **phi4-mini** (Phi-4-mini) | MIT | 3.8B, Q4_K_M | 3.40 GiB | 64% | 0.94 | 35.1 tokens/s | 1.3 s |
| **llama3.2:3b** (Llama 3.2 3B) | Llama 3.2 Community | 3.2B, Q4_K_M | 2.73 GiB | 80% | 0.73 | 56.6 tokens/s | 0.7 s |
| gemma3:4b (Gemma 3 4B) | Gemma Terms | 3.9B, Q4_K_M | 3.25 GiB | 46% | 0.83 | 22.9 tokens/s | 2.5 s |
| qwen3:4b (thinking build) | Apache-2.0 | 4.0B, Q4_K_M | 3.29 GiB | 66% | 0.81 | 29.6 tokens/s | 1.6 s |

Nine tasks are a screen, not a result; the comparison runs all 45.

## Decision

Compare **qwen3:4b-instruct**, **phi4-mini** and **llama3.2:3b**: three vendors and licences,
two accurate 4B-class models against a smaller one that runs almost twice as fast and fits
better on the GPU. gemma3:4b is left out (slowest, least of it on the GPU, a vision model
larger than the task needs) and the thinking build is replaced by its instruct twin. The models
and their digests are in `configs/models.yaml` and [environment.md](../environment.md).

## Consequences

### Positive

- The report can answer "is the faster model accurate enough?", the question a team deploying
  on a laptop would ask.
- Every model answers directly, so prompt-only JSON can be compared fairly in #22.

### Negative and risks

- All three are 4-bit; precision is not compared (the optional Q8_0 experiment, #26).
- Tags move: the digests pin the exact builds measured.

## Revisit when

- A larger GPU becomes the reference, or a new 3B to 4B model family appears in Ollama.
