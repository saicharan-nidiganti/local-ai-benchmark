# Architecture

Last updated: 2026-11-13 · Applies to: `main` after Phase 0

This document describes how local-ai-benchmark is built today and how it grows through the
[roadmap](roadmap.md). Parts that do not exist yet are marked **planned**, with the phase and
issue that add them; their module names are provisional. Requirement IDs (FR-*, NFR-*) refer
to [requirements.md](requirements.md); decisions are recorded in [decisions/](decisions/).

## 1. Context

One person runs the harness on one machine. The harness talks to one local service, the
Ollama server, and to the file system. Nothing leaves the machine (FR-9).

```mermaid
flowchart LR
    operator(["Operator<br/>runs benchmarks,<br/>reads reports"])
    subgraph machine["Reference machine: Windows 11, RTX 3050 4 GB, 16 GB RAM"]
        harness["local-ai-benchmark<br/>Python CLI"]
        ollama[("Ollama server<br/>localhost:11434<br/>GGUF models, llama.cpp runner")]
        gpu{{"GPU and CPU"}}
        files[("File system<br/>configs, suites,<br/>run log, reports")]
    end
    operator -- "commands" --> harness
    harness -- "HTTP, streamed JSON" --> ollama
    ollama --> gpu
    harness -- "read configs and suites,<br/>append runs, write reports" --> files
```

| Element | Responsibility | Owned by |
| --- | --- | --- |
| Operator | Chooses models and settings, runs benchmarks, reads results | Person |
| local-ai-benchmark | Sends requests, measures them, records every run, summarizes and reports | This repository |
| Ollama server | Loads quantized models, splits layers between GPU and CPU, generates tokens, reports durations | [Ollama](https://ollama.com), [ADR-0002](decisions/0002-ollama-as-the-local-runtime.md) |
| File system | Holds inputs (configs, suites) and outputs (run log, reports) | This repository's folders |

## 2. Containers

| Container | Technology | Lifetime | Notes |
| --- | --- | --- | --- |
| CLI process | Python 3.11+, `local-ai-benchmark` console script | One per command | Stateless between commands; all state is in files |
| Ollama server | Ollama 0.40 (reference), HTTP on `localhost:11434` | Long-running service | Keeps a model loaded for `keep_alive` (5 minutes by default here) |
| Run log | JSON Lines, `data/raw/runs.jsonl` | Append-only, git-ignored | [ADR-0003](decisions/0003-append-only-jsonl-run-log.md) |
| Configuration | YAML, `configs/benchmark.yaml` and `configs/models.yaml` | Versioned in git | Read on every command; flags override ([ADR-0006](decisions/0006-configuration-and-pinned-settings.md)) |
| Task suites | JSON Lines, `benchmarks/` | Versioned in git | Not read yet: **planned**, Phase 2 ([#19](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/19)) |
| Reports | Markdown and figures, `reports/` | Curated output committed | **Planned**, Phase 3 ([#25](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/25)) |

## 3. Components

```mermaid
flowchart TB
    subgraph pkg["Package: src/local_ai_benchmark"]
        direction TB
        cli["cli.py<br/>parses arguments,<br/>runs ask and benchmark"]
        inference["inference.py<br/>streams one generation,<br/>times it, never raises"]
        metrics["metrics.py<br/>run log, run IDs,<br/>order statistics"]
        config["config.py<br/>settings and model registry,<br/>flags override files"]
        preflight["preflight.py<br/>server and model checks<br/>before any request"]
        runtimeq["runtime.py<br/>server version, model details,<br/>GPU placement"]
        manifest["manifest.py<br/>environment manifest<br/>Phase 1 · #14"]:::planned
        sampler["sampler.py<br/>RAM, VRAM, power<br/>Phase 1 · #15"]:::planned
        suite["suite.py, scorers.py<br/>tasks and scoring<br/>Phase 2 · #19-#21"]:::planned
        report["report.py<br/>comparison report<br/>Phase 3 · #25"]:::planned
        app["app.py<br/>offline application<br/>Phase 5 · #31"]:::planned
    end
    ollama[("Ollama server")]
    log[("runs.jsonl")]
    cli --> inference
    cli --> metrics
    inference --> ollama
    metrics --> log
    cli --> config
    cli --> preflight
    preflight --> runtimeq
    runtimeq --> ollama
    cli -.-> suite
    cli -.-> report
    inference -.-> sampler
    cli -.-> manifest
    suite -.-> inference
    report -.-> log
    app -.-> inference
    classDef planned stroke-dasharray: 5 3
```

Solid boxes and arrows exist today; dashed ones are planned.

| Module | Responsibility | Public interface | Depends on |
| --- | --- | --- | --- |
| `cli.py` | Parse arguments; resolve settings; run the preflight; run `ask` (one request) and `benchmark` (warm-ups, then measured runs); print results; map failures to exit codes | `main(argv)`, `build_parser()`, `ask(args)`, `benchmark(args)` | `config`, `preflight`, `inference`, `metrics`, `paths` |
| `inference.py` | Stream one generation from Ollama, time the first token on the client, read the runtime's durations, and turn any failure into a recorded error | `generate(model, prompt, settings) -> InferenceResult` | `ollama` client, `config` |
| `config.py` | Load `benchmark.yaml` and `models.yaml`, validate every key and type, apply command-line overrides, resolve a model id to its Ollama tag | `load_settings(path)`, `with_overrides(settings, **flags)`, `load_models(path)`, `resolve_model(name, models)`, `GenerationSettings.options()` | PyYAML |
| `metrics.py` | Append records to the run log and read them back; issue run IDs; group records by run; summarize a run with medians and order statistics | `append_jsonl`, `read_jsonl`, `new_run_id`, `benchmark_runs`, `select_run`, `summarize`, `run_summary`, `spread` | standard library |
| `runtime.py` | Ask the Ollama server for its version, a model's details and digest, and where a loaded model sits (GPU or CPU); read `OLLAMA_HOST` as the Ollama client does | `host()`, `server_version()`, `model_details(name)`, `loaded_model(name)` | `ollama` client, `httpx` |
| `preflight.py` | Before any request, confirm the server answers, the model is pulled, and the model can think if `--think` was given; otherwise fail with what to do | `check(model, think) -> Preflight`, `PreflightError` | `runtime` |
| `paths.py` | Locate the project folder (`LOCAL_AI_BENCHMARK_HOME`, else the source checkout, else the working folder) and the default run log in it | `project_root()`, `default_run_log()` | standard library |

Dependency rules: no module imports `cli`; only `inference` (generation) and `runtime`
(everything else) talk to Ollama; only `metrics` writes the run log. Planned modules keep the same direction: the CLI
composes, the lower modules do one job each.

## 4. Runtime view

### 4.1 A benchmark command

```mermaid
sequenceDiagram
    actor Op as Operator
    participant CLI as cli.benchmark
    participant Inf as inference.generate
    participant Oll as Ollama server
    participant Log as runs.jsonl
    Op->>CLI: benchmark --model M --prompt P --repeats N --warmup-runs W
    CLI->>Oll: preflight: GET /api/version, then show M
    alt server down, or M not pulled
        Oll-->>CLI: error
        CLI-->>Op: what to do (exit code 3), before any request
    end
    loop W warm-up runs, never recorded
        CLI->>Inf: generate(M, P, settings)
        Inf->>Oll: POST /api/generate (stream, think=false)
        Oll-->>Inf: streamed chunks, final chunk with durations
        Inf-->>CLI: result, discarded
    end
    loop N measured runs
        CLI->>Inf: generate(M, P, settings)
        Inf->>Oll: POST /api/generate (stream, think=false)
        Oll-->>Inf: first chunk with text: client stops the TTFT clock
        Oll-->>Inf: remaining chunks, final chunk with counts and durations
        Inf-->>CLI: InferenceResult (an error is recorded, not raised)
        CLI->>Log: append one record
    end
    CLI-->>Op: run ID and summary: error rate, p50, p90, min, max, IQR per metric
```

`ask` is the same request once, recorded with `run_type: "single"` and its own run ID,
without warm-up or summary. `summarize --run-id ID` reads the log and prints exactly the
summary the benchmark printed; without an ID it takes the latest benchmark, and `--list`
shows them all.

### 4.2 What each timing covers

```text
client sends request                          first visible token              last token
      |-- model load --|-- prompt evaluation --|-- decode ---------------------------|
      |<----------------- ttft_ms (client clock) ------>|
      |<------------------------------ total_latency_ms (client clock) ------------->|
       load_duration_ms   prompt_eval_duration_ms       generation_ms (Ollama's eval_duration)
```

- **Client-side** (`time.perf_counter`): `ttft_ms` and `total_latency_ms`. They include HTTP
  and streaming overhead, which is what a user of the model experiences.
- **Runtime-side** (Ollama's nanosecond durations): `load_duration_ms`,
  `prompt_eval_duration_ms`, `generation_ms`, and the token counts.
- **Throughput** is `output_tokens / generation_ms`: decode speed. **Prefill speed** is
  `prompt_tokens / prompt_eval_duration_ms`: how fast the prompt is read, which dominates
  for long prompts.
- A cold start puts the model load inside TTFT; warm-up runs exist to keep it out of the
  measured runs ([ADR-0004](decisions/0004-measurement-protocol.md)).

## 5. Data model: the run record

One JSON object per line in `data/raw/runs.jsonl`. Version 1, as written today:

| Field | Type | Unit | Source | Notes |
| --- | --- | --- | --- | --- |
| `timestamp` | string | ISO 8601, UTC | CLI | When the record was written |
| `run_id` | string | | CLI | Shared by every record of one invocation, for example `20261113T061512Z-3fa9c2` |
| `run_type` | string | | CLI | `single` (ask) or `benchmark` |
| `run_index` | integer | | CLI | 1 to N; benchmark only |
| `model_id` | string | | registry | The id from `configs/models.yaml`, or the tag itself when the model is not registered |
| `temperature` | number | | settings | |
| `max_output_tokens` | integer | tokens | settings | Sent as Ollama's `num_predict` |
| `seed` | integer | | settings | Sampling seed, pinned |
| `num_ctx` | integer | tokens | settings | Context length, pinned; it also sets the model's memory footprint |
| `keep_alive` | string | duration | settings | How long Ollama keeps the model loaded |
| `think` | boolean | | settings | Whether a thinking model may reason before answering; off by default |
| `model` | string | | request | Ollama model tag, for example `qwen3:4b` |
| `prompt` | string | | request | Full prompt text |
| `response` | string | | stream | Concatenated visible reply |
| `ttft_ms` | number or null | ms | client | Null when no text arrived |
| `total_latency_ms` | number | ms | client | Always present, also on failure |
| `output_tokens` | integer or null | tokens | Ollama `eval_count` | |
| `generation_ms` | number or null | ms | Ollama `eval_duration` | |
| `tokens_per_sec` | number or null | tokens/s | derived | Null when the runtime reports no generation time |
| `load_duration_ms` | number or null | ms | Ollama `load_duration` | |
| `prompt_tokens` | integer or null | tokens | Ollama `prompt_eval_count` | |
| `prompt_eval_duration_ms` | number or null | ms | Ollama `prompt_eval_duration` | |
| `prefill_tokens_per_sec` | number or null | tokens/s | derived | Null when the runtime reports no prompt time |
| `error` | string or null | | inference | `ExceptionType: message`; null on success |

**Planned fields**, added without removing any of the above: a manifest
reference and resource samples (Phase 1, [#14](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/14),
[#15](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/15)); `prompt_id`,
`category` and `score` (Phase 2, [#21](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/21)).

## 6. Deployment view

| Layer | Reference value | Recorded in |
| --- | --- | --- |
| Hardware | ASUS ROG Strix G513QC: AMD Ryzen 9 5900HX, NVIDIA RTX 3050 Laptop GPU 4 GB, 15.4 GB RAM | [environment.md](environment.md) |
| Operating system | Windows 11 | [environment.md](environment.md) |
| Runtime | Ollama 0.40.16, llama.cpp runner, `localhost:11434` | [environment.md](environment.md) |
| Harness | Python 3.11 to 3.14, installed from `uv.lock` | `pyproject.toml`, `uv.lock` |
| CI | GitHub Actions: Ubuntu (Python 3.11 to 3.14) and Windows (3.14); no model, no GPU | `.github/workflows/ci.yml` |

CI never runs a model: the tests replace the Ollama client with simulated streams
(NFR-2). Live measurements happen only on the reference machine.

## 7. Repository layout

```text
.github/                  CI workflow, issue and pull request templates, CODEOWNERS, Dependabot
benchmarks/               versioned task suites (Phase 2 grows prompts_v1.jsonl)
configs/                  benchmark settings and the model registry
data/raw/                 run log, git-ignored
data/processed/           derived data, git-ignored
docs/                     requirements, architecture, roadmap, methodology, environment
docs/decisions/           architecture decision records
reports/                  curated reports and figures (Phase 3)
src/local_ai_benchmark/   the package: cli, inference, metrics
tests/                    offline test suite
CHANGELOG.md              changes per release, Keep a Changelog format
CONTRIBUTING.md           setup, workflow, definition of done
Makefile                  the commands CI runs
pyproject.toml, uv.lock   package metadata, tool settings, locked dependencies
```

## 8. Cross-cutting concerns

**Error handling.** `generate()` catches every exception and returns an `InferenceResult`
with `error` set, keeping a TTFT if text had already arrived. A benchmark therefore always
completes and reports its error rate (NFR-4). A reply with no visible text is a failure too
(`empty_response`), with the runtime's token counts kept for diagnosis. Problems that would
make every run fail are caught before the first one: the preflight checks the server and the
model. Exit codes: 0 success, 2 configuration error, 3 runtime or model unavailable.

**Reproducibility.** Today: warm-up exclusion, temperature and output limit recorded on
benchmark runs, thinking disabled, every observation kept. Planned in Phase 1: pinned `seed`
and `num_ctx`, a `run_id`, and an environment manifest (FR-4).

**Privacy.** The harness sends requests only to the Ollama host and sends no telemetry. The
run log holds full prompts and replies, so it stays git-ignored. Enforcing a local-only host
is planned ([#27](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/27)). See
[SECURITY.md](../SECURITY.md).

**Testing.** Unit tests replace `ollama.generate` with generators that yield chunks, raise
errors or stop midway, and replace `cli.generate` with a stub; files go to `tmp_path`.
Coverage is measured with branches and must stay at 90% or more.

**Configuration precedence.** Built-in defaults, then `configs/benchmark.yaml`, then
command-line flags given explicitly; `--config` and `--models` point at other files. Unknown
keys and wrong types are rejected with the file and key named. The effective values are
recorded on every run ([ADR-0006](decisions/0006-configuration-and-pinned-settings.md)).

## 9. Quality attributes

| Attribute | How the design addresses it today | Planned |
| --- | --- | --- |
| Reproducibility | Fixed settings within a benchmark; warm-up exclusion; raw log kept | Seed, context length, run ID, manifest (#12, #13, #14) |
| Measurement validity | Client TTFT plus runtime durations; prefill and decode speed; medians with p90 and IQR; thinking disabled | Resource samples (#15) |
| Privacy | Local runtime only; no telemetry; raw log git-ignored | Local-only host enforced (#27) |
| Robustness | Failures recorded, never raised; an empty reply is a failure; a preflight fails fast when the server or model is missing | |
| Testability | Offline tests with simulated streams; 96% coverage | Fakes for the sampler and manifest |
| Maintainability | src layout, strict typing, Ruff, locked dependencies, ADRs | Protected `main` (#8) |
| Portability | Windows and Linux in CI | |

## 10. Known limitations

- On the reference GPU, qwen3:4b at a 4096-token context keeps about a third of its memory
  on the CPU ([environment.md](environment.md#first-live-run)).

## 11. Decisions

| ADR | Decision |
| --- | --- |
| [0001](decisions/0001-record-architecture-decisions.md) | Record architecture decisions |
| [0002](decisions/0002-ollama-as-the-local-runtime.md) | Ollama as the local inference runtime |
| [0003](decisions/0003-append-only-jsonl-run-log.md) | An append-only JSON Lines run log |
| [0004](decisions/0004-measurement-protocol.md) | Measurement protocol |
| [0005](decisions/0005-packaging-and-toolchain.md) | Packaging and toolchain |
| [0006](decisions/0006-configuration-and-pinned-settings.md) | Configuration precedence and pinned generation settings |
