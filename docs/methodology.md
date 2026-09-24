# Methodology

## Phase 1 baseline

The project blueprint requires controlled, repeatable measurements rather than subjective impressions.

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
