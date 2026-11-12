# ADR-0004: Measurement protocol

- **Status:** Accepted (decided 2026-09-24 with the first architecture; amended 2026-11-13 by
  #4; recorded 2026-11-13)
- **Date:** 2026-09-24
- **Deciders:** Project owner
- **Issue:** [#7](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/7),
  [#4](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/4)
- **Requirements:** FR-2, FR-4, NFR-4

## Context

Local inference timings are easy to distort. The first request loads the model, so it is far
slower than the rest. A single run hides variance. Thinking models can spend the output
budget on hidden reasoning, so no visible token ever arrives. The client and the runtime see
different spans of the same request.

## Decision drivers

1. Measure what a user of the model experiences, and also where the time goes.
2. Keep cold-start effects out of steady-state numbers.
3. Resist a single outlier.
4. Count failures instead of hiding them.

## Options considered

| Question | Chosen | Alternatives |
| --- | --- | --- |
| Where TTFT is measured | Client clock (`perf_counter`) to the first chunk with visible text | Runtime durations only: they omit HTTP and streaming overhead |
| Where phase times come from | Ollama's final-chunk durations (load, prompt evaluation, decode) | Client-side estimates: cannot separate the phases |
| Cold start | Warm-up runs before measurement, never recorded | Record and filter later: easy to forget when summarizing |
| Summary statistic | Median per metric (p90 and IQR planned, #13) | Mean: skewed by one slow run |
| Failures | Recorded with the error; excluded from medians; counted in the error rate | Retried or dropped: hides unreliability |
| Thinking models | Thinking disabled on every request (`think=False`) | Leave it on: TTFT can be missing and replies empty |

## Decision

Use the choices marked in the table. Metric definitions are in
[methodology.md](../methodology.md); the timing spans are drawn in
[architecture.md](../architecture.md#42-what-each-timing-covers).

## Consequences

### Positive

- Steady-state numbers are comparable across models and runs.
- The client and runtime views together show both the experience and its causes.

### Negative and risks

- With few runs (for example 5), medians are coarse; spread is reported from Phase 1 (#13).
- Disabling thinking measures the models without their reasoning mode; a flag to enable it
  for a separate comparison is planned (#11).

## Revisit when

- A metric is added that the client and Ollama's durations cannot cover (for example power,
  #15), or Ollama changes what its durations include.
