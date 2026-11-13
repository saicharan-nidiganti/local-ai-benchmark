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

### Quality scoring

Every task of the suite ([ADR-0008](decisions/0008-use-case-support-ticket-triage.md)) gets a
score from 0 to 1, computed from the reply alone:

| Task | Score |
| --- | --- |
| Classify | Half for the right category, half for the right priority; labels compared without case |
| Extract | A quarter for each field: order number (case, spaces and a leading `#` ignored), customer name and product (equal or contained after normalizing), and issue (contains one of the expected keywords) |
| Summarize | The share of required facts present; halved when the summary exceeds 40 words |

A run's quality is the mean score over its tasks, overall and per task kind. A task whose
request failed scores 0: an answer that never arrived is a wrong answer, so unreliability
lowers quality as well as raising the error rate.

Normalizing ignores case, punctuation and spacing, and keeps hyphens (`A-1042`). Missing
values such as `null`, `none` or `N/A` count as no value.

By default the JSON tasks run with **structured output**: the task's JSON schema is sent as
Ollama's `format`, so the runtime constrains the reply to it, as the offline app will. With
`--json-mode prompt` the prompt alone asks for JSON; the two modes are compared in #22 and
are never mixed in one result ([ADR-0009](decisions/0009-structured-output-for-json-tasks.md)).

JSON is judged in two steps: **strict** when the whole reply is one JSON object, and **valid**
when an object can be recovered from a code fence or surrounding prose. Scores use the
recovered object, so a model is not punished twice for formatting; the strict rate is
reported beside it. **Schema-valid** means the object has the required keys and labels from
the allowed sets.

### Comparing models

`report` compares one suite run per model, all on the same suite, settings and machine. Its
verdict follows fixed rules: **most accurate** is the highest overall quality; **fastest** is
the highest median decode speed; **best tradeoff** is the fastest model whose overall
quality is within 0.05 of the most accurate one, the choice a team deploying on this laptop
would make. The margin is a project constant (`TRADEOFF_MARGIN`), stated in every report.

### Latency targets

Interactive use has three limits, each judged on a measured median
(`src/local_ai_benchmark/targets.py`):

| Target | Limit | Why |
| --- | --- | --- |
| First token, model loaded | ≤ 1,000 ms | 1 s is the limit for a user's flow of thought to stay uninterrupted (Nielsen, *Response Times: The 3 Important Limits*, 1993) |
| Decode speed | ≥ 10 tokens/s | About twice average adult silent reading, 238 words a minute (Brysbaert, *Journal of Memory and Language* 109, 2019), near 5 tokens/s at 1.3 tokens a word |
| First token, model not loaded | ≤ 10,000 ms | 10 s is the limit for keeping a user's attention on the task (Nielsen, 1993) |

Warm figures come from the suite run, after its warm-up. The cold first token comes from
`benchmark --cold`, which unloads the model before every measured run (Ollama's
`keep_alive: 0`) and waits until it is gone, so each run includes loading it. The model file
may still be in the operating system's file cache, so this is a cold start of the runtime,
not of the disk; a first start after a reboot is slower. `report` adds the targets table when
a model has a cold benchmark in the log.

### Cost

`report --cost configs/cost.yaml` prices each suite run's workload, every successful task
included with its prompt, since reading the prompt is part of what each answer costs:

- **Local electricity** = the run's GPU energy (J) / 3.6 MJ per kWh × the tariff.
- **Local hardware** = the run's busy time (the sum of task latencies) × the laptop's price per
  hour of use (price / (lifetime years × 365 × hours a day)).
- **Hosted** = the same model's API price: the output price per million output tokens, and
  input plus output tokens per 1,000 tasks, converted at the stated exchange rate.

Each is reported per million output tokens and per 1,000 tasks. Every assumption in
`configs/cost.yaml` carries its source and the date it was read, and the report lists them.
The energy is the GPU board's alone, so local electricity is a lower bound; hardware cost
assumes the laptop does nothing else, so it is an upper bound for a machine already owned.

### Resource use

While each measured run executes, a background thread samples every 0.5 s
(`--sample-interval`): system memory in use, the resident memory of the Ollama server and its
model runner, and GPU memory and board power from `nvidia-smi`. A run records the peaks, the
mean GPU power, and GPU energy as mean power times the run's total latency. After the run,
Ollama reports how much of the loaded model sits in GPU memory (`gpu_offload_pct`).

Measure plugged in. On battery the GPU may be throttled and the charge falls during a run,
so every measuring command warns before its first request when the machine reports it is on
battery, and `--require-ac` turns the warning into an error. The manifest records the power
state either way.

The sampler also reads the connection table at every sample and keeps the remote ends of
connections from the Ollama server, its model runner and the harness that are not loopback:
anything that reached another machine, a LAN address included. A run records how many
(`remote_connections`) and which (`remote_endpoints`); a summary adds them up. A connection
that opens and closes between two samples is missed, which is why the suite is also run with
networking turned off ([ADR-0011](decisions/0011-local-only-runtime-and-connection-audit.md)).

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
