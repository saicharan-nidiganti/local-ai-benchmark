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

This first implementation uses Ollama's generation metadata for token counts and generation duration, while TTFT is measured around the streamed client response.

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
