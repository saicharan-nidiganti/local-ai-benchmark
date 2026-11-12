# ADR-0002: Ollama as the local inference runtime

- **Status:** Accepted (decided 2026-09-24 with the first architecture; recorded 2026-11-13)
- **Date:** 2026-09-24
- **Deciders:** Project owner
- **Issue:** [#7](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/7)
- **Requirements:** FR-1, FR-2, NFR-1, NFR-6

## Context

The project runs small language models entirely offline on a Windows laptop with a 4 GB
NVIDIA GPU, measures their speed, and compares several models under identical conditions.
The runtime decides which models can run, how memory is split between GPU and CPU, and which
timings can be observed.

## Decision drivers

1. Runs offline on Windows with an NVIDIA GPU, and also on Linux.
2. Quantized models (4-bit) so that 3B to 4B models fit near 4 GB of VRAM.
3. Reports token counts and phase durations (load, prompt evaluation, decode) per request.
4. Streams tokens, so the client can time the first one.
5. Pulls and switches models by name, so comparisons are cheap to run.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| **Ollama** | Windows installer; GGUF quantized models; automatic GPU and CPU split; per-request durations in nanoseconds; streaming HTTP API; model library by tag | Adds a server layer over llama.cpp; its scheduling (`keep_alive`, context size) must be pinned |
| llama.cpp server directly | Thinnest layer; full control of every option | Models fetched and converted by hand; fewer conveniences for switching models |
| LM Studio | Friendly interface; OpenAI-compatible server | Desktop application first; less suited to scripted, repeatable runs |
| vLLM | High-throughput serving | Linux-first; built for larger GPUs and many concurrent requests |
| Hugging Face Transformers in process | No server | Unquantized models do not fit 4 GB; timings mix with Python overhead |

## Decision

Use Ollama through its official Python client, with streaming enabled. Take the first-token
time on the client and the phase durations and token counts from Ollama's final chunk
([ADR-0004](0004-measurement-protocol.md)).

## Consequences

### Positive

- A 4B model at Q4_K_M runs on the reference GPU, with the remainder on the CPU when needed.
- Every request yields comparable runtime timings without instrumenting the model.
- Switching models is a change of tag.

### Negative and risks

- Results describe Ollama's runner as much as the model; the Ollama version is part of every
  result and is recorded ([environment.md](../environment.md); manifest in #14).
- Ollama's defaults (context length, `keep_alive`, thinking) can change between versions, so
  the harness must set them explicitly (#12).

## Revisit when

- A second runtime is needed for comparison: an OpenAI-compatible backend (llama.cpp server,
  LM Studio) is an optional Phase 5 extension.
