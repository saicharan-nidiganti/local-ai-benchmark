# Methodology

## Phase 1 baseline

Model performance claims are only useful when they come from controlled, repeatable measurements rather than subjective impressions.

For the first baseline:

- warm up before measurement
- run the same prompt repeatedly
- keep model, hardware, runtime, generation parameters and output limit fixed
- separate model loading effects from normal inference where possible
- retain every raw observation
- summarize repeated measurements using median values

### Metrics

**TTFT**: elapsed time from request start until the first generated token is observed.

**Total latency**: elapsed wall-clock time from request start until generation completes.

**Generated tokens**: token count reported by the local runtime.

**Generation throughput**: generated tokens divided by runtime-reported generation duration.

**Prefill throughput**: prompt tokens divided by the runtime-reported prompt-evaluation
duration. It is reported separately because it behaves differently: it grows with the prompt,
not the reply.

**Summary statistics**: for each metric, the median (p50), p90, minimum, maximum and
interquartile range over the successful runs of one run ID. Quantiles use the inclusive
method, so with five runs p90 lies between the two slowest instead of beyond the data. The
median stays the headline number; p90 and the IQR show how much a single run can be trusted.

This first implementation uses Ollama's generation metadata for token counts and generation duration, while TTFT is measured around the streamed client response.

### Resource use

While each measured run executes, a background thread samples every 0.5 s
(`--sample-interval`): system memory in use, the resident memory of the Ollama server and its
model runner, and GPU memory and board power from `nvidia-smi`. A run records the peaks, the
mean GPU power, and GPU energy as mean power times the run's total latency. After the run,
Ollama reports how much of the loaded model sits in GPU memory (`gpu_offload_pct`).

Limits: the energy figure covers the GPU board only, not the CPU, memory or screen; and a run
shorter than the interval gets only its start and end samples. GPU fields are empty on a
machine without an NVIDIA driver. `--no-sampling` skips sampling entirely.

### Fixed settings

Every request carries the same temperature, output limit, sampling seed and context length,
taken from `configs/benchmark.yaml` unless a flag overrides them, and every run records them.
The context length is pinned explicitly because it changes how much memory the model needs,
and so how much of it fits on the GPU.

### Failures

A run fails when the request raises (the server is unreachable, the stream breaks) or when
the reply contains no visible text (`empty_response`). A failed run is recorded with its
error, excluded from every median, and counted in the error rate. An empty reply keeps the
runtime's token counts, because they show where the output budget went.

### Thinking models

Models such as qwen3 can reason before they answer, and Ollama returns that reasoning
separately from the reply. With thinking enabled, a short output limit can be spent
entirely on reasoning: the reply is empty and no first token is ever observed, so TTFT is
missing. The harness therefore disables thinking by default (`think: false` in
`configs/benchmark.yaml`), which keeps TTFT and throughput comparable across thinking and
non-thinking models. `--think` switches it on for a separate measurement, and every run
records the setting. On a model that cannot think, the default is harmless: see
[environment.md](environment.md#thinking-off-on-a-non-thinking-model).
