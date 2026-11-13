# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The offline app: `triage` answers one support ticket with its category, priority, order
  number, customer, product, issue and a summary, on phi4-mini (the comparison's best
  tradeoff) with the suite's prompts and schemas; `serve` offers the same as a web page on
  http://127.0.0.1:8765, on the standard library alone, loopback only, with Host and Origin
  checks, a body cap and a Content-Security-Policy. Neither keeps tickets or answers.
  ADR-0012 ([#31](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/31)).
- Results: the app with networking off. Three fictional tickets answered by `triage` and by
  the web page in 2.7 to 3.6 s each with the model loaded; a foreign Host header refused;
  screenshots of the page in `docs/images/`. `serve` flushes its start-up lines, so they
  appear when its output goes to a file
  ([#31](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/31)).
- Privacy enforced and audited: the preflight refuses an Ollama server on another machine
  unless `--allow-remote` is given; every measured run records connections from Ollama, its
  runner or the harness to another machine (`remote_connections`, `remote_endpoints`), and
  summaries add them up; the manifest records the network interfaces that were up and
  whether the runtime is local; `report` adds a Privacy section for audited runs. ADR-0011
  ([#27](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/27)).
- Latency targets for interactive use, each with a cited reason: first token within 1 s with
  the model loaded, decode at 10 tokens/s or more, first token within 10 s with it not
  loaded. `benchmark --cold` unloads the model before every measured run and records
  `start`; `report` judges each model against the targets when it has a cold benchmark
  ([#28](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/28)).
- Cost: `report --cost configs/cost.yaml` adds local electricity and hardware cost per million
  output tokens and per 1,000 tasks beside the same model's hosted price; every assumption
  (Telangana tariff, laptop price and lifetime, exchange rate, hosted prices) is sourced and
  dated in the file, and `cost.json` holds the figures
  ([#29](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/29)).
- Results: privacy, latency and cost measured with networking off. The same 135 replies as
  online and 0 connections to another machine; every model meets every latency target
  (first token 92 to 203 ms loaded, 3.3 to 4.5 s cold; 29 to 52 tokens/s); GPU electricity
  INR 1.93 to 3.57 per million output tokens against INR 18.90 to 31.18 hosted. `report`
  writes `cold_starts.json` and lists the cold run IDs
  ([#27](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/27),
  [#28](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/28),
  [#29](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/29)).

### Changed

- README rebuilt around the results: the app beside the verdict, with screenshots for light
  and dark mode; a numbered "Reproduce the results" guide (models and digests, checks, power and
  networking, suite and cold starts, the report with cost, what to compare) so the comparison
  can be reproduced from the README alone; status at six of six phases
  ([#32](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/32)).
- README: a Tradeoffs section, local against hosted for privacy, latency and cost, each line
  backed by a measured or cited number, with where local wins and where a hosted model is the
  better choice; status at Phase 4 of 6
  ([#30](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/30)).
- The decode-speed target's reason uses the measured 1.3 to 1.6 tokens a word of the compared
  models' summaries instead of an assumed 1.3
  ([#28](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/28)).

## [0.2.0] - 2026-11-13

### Added

- A warning before the first request when the machine is on battery, and `--require-ac` to
  stop instead; on battery the GPU may be throttled and results are not comparable
  ([#54](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/54)).
- ADR-0010: the comparison uses qwen3:4b-instruct, phi4-mini and llama3.2:3b, chosen from a
  screening of five models on the reference GPU; the registry and the environment list them
  with their digests ([#23](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/23)).
- `report` command: compares the latest suite run of each comparison model (or the run IDs
  given) as a results folder: quality per task kind and ticket category, speed, GPU share,
  power and energy, run identities, a verdict (most accurate, fastest, best tradeoff) and a
  quality-against-speed chart as SVG ([#25](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/25)).
  The chart zooms the quality axis to the data, shades the models within the tradeoff margin
  and moves labels that would overlap.
- Results: the three-model comparison on the reference laptop. qwen3:4b-instruct and
  phi4-mini both score 0.89; phi4-mini is the best tradeoff at 34.6 tokens/s against 30.3;
  llama3.2:3b is the fastest at 53.0 tokens/s and scores 0.81
  ([#24](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/24)).
- ADR-0008: the task suite's use case is support-ticket triage: classify category and
  priority, extract fields as JSON, summarize in at most 40 words, all on fictional tickets
  ([#18](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/18)).
- Task suite `support_triage_v1`: 15 fictional support tickets, three per category, each with
  expected labels, fields and summary facts, expanded into 45 tasks with versioned prompts;
  validated with pydantic, and tests check the data is fictional and self-consistent
  ([#19](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/19)).
- Automatic scorers for the three task kinds, each from 0 to 1: label match for classify,
  field accuracy with pydantic schema checks for extract, required facts and the 40-word
  limit for summarize; JSON judged as strict, recovered or invalid
  ([#20](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/20)).
- `suite` command: runs every task of a suite (or one kind with `--tasks`), scores each
  reply, records score, JSON checks and score details next to timings and resources, and
  prints quality per task kind with the JSON rates; `summarize` rebuilds suite runs too
  ([#21](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/21)).
- Structured output for the JSON tasks: classify and extract send their JSON schema as
  Ollama's `format` by default (`--json-mode schema`); `--json-mode prompt` keeps the prompt
  alone. qwen3:4b scored 0 on every JSON task with the prompt alone because it narrates its
  reasoning in the reply; ADR-0009 records the finding and the decision
  ([#21](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/21)).

### Changed

- README leads with the comparison: the verdict, the chart and the results table, then
  how the numbers are controlled, a current architecture diagram, quality metrics, a
  command reference with exit codes, and the engineering practices; the repository About
  text, topics and website link describe the comparison
  ([#55](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/55)).

### Removed

- The empty `reports/` folder: reports are written under `results/`
  ([#55](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/55)).
- `benchmarks/prompts_v1.jsonl`, three unread prompts superseded by the task suite
  ([#19](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/19)).

## [0.1.0] - 2026-11-13

The measurement harness (Phase 1) and the first published baseline.

### Added

- Baseline results for qwen3:4b on the reference laptop in `results/`: 30.8 tokens/s, 47 ms
  to the first token, 66% of the model on the 4 GB GPU, 320 J per 256-token answer
  ([#17](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/17)).
- Offline test suite (13 tests) for the inference client, the CLI and the summaries, run in
  CI on Python 3.11 to 3.14 ([#3](https://github.com/saicharan-nidiganti/local-ai-benchmark/pull/3)).
- `local-ai-benchmark` console script ([#3](https://github.com/saicharan-nidiganti/local-ai-benchmark/pull/3)).
- Development toolchain: uv with a committed lockfile, Ruff, mypy `--strict`, a 90% coverage
  floor, pre-commit hooks, `.editorconfig` and `.gitattributes`, and Makefile targets that CI
  calls. CI now runs lint and types, tests on Python 3.11 to 3.14 and on Windows, and a
  package check that installs the built wheel alone
  ([#6](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/6)).
- Documentation set: requirements with IDs traced to milestones, a detailed architecture
  (context, components, runtime sequence, run-record schema, deployment), the reference
  environment with Ollama version and model digest, the roadmap, ADR-0001 to ADR-0005,
  `CONTRIBUTING.md` and `SECURITY.md`
  ([#7](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/7),
  [#2](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/2)).
- Issue templates (bug, feature, experiment), a pull request template with the definition of
  done, `CODEOWNERS`, and monthly grouped Dependabot updates for GitHub Actions and uv
  ([#8](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/8)).
- Settings from `configs/benchmark.yaml` and a model registry in `configs/models.yaml`, with
  command-line overrides, validated keys and types, and clear errors; `--seed`, `--num-ctx`
  and `--keep-alive` flags; `--version`. Every run, `ask` included, records its model id and
  generation settings ([#12](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/12)).
- `--think` / `--no-think` (and `think:` in the settings file) to let a thinking model reason
  before it answers; off by default and recorded on every run
  ([#11](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/11)).
- A preflight before any request: when Ollama is unreachable, the model is not pulled, or
  `--think` is given for a model that cannot think, the command fails within a second with
  what to do and exit code 3, instead of failing every run
  ([#10](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/10)).
- A `run_id` on every record, and a `summarize` command that rebuilds a benchmark's summary
  from the log (`--run-id`, default the latest; `--list`). Summaries add p50, p90, min, max
  and IQR per metric, and prefill speed beside decode speed
  ([#13](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/13)).
- An environment manifest per run ID in `manifests.jsonl` beside the run log: harness
  version, git commit and dirty flag, Python, OS, CPU, RAM, NVIDIA GPUs, AC power, Ollama
  version and host, model digest, quantization and capabilities; ADR-0007
  ([#14](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/14)).
- Resource sampling during every measured run: peak system RAM, peak memory of the Ollama
  server and its model runner, peak GPU memory, mean GPU power and GPU energy, plus the share
  of the model in GPU memory and its loaded context. Summaries include them;
  `--sample-interval` and `--no-sampling` control it
  ([#15](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/15)).

### Changed

- The package moved to a src layout and is now named `local_ai_benchmark`
  (`python -m local_ai_benchmark`); it builds with hatchling. The empty `runners/` package is
  gone ([#5](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/5)).
- Sampling seed (42) and context length (4096 tokens) are now pinned on every request instead
  of left to Ollama's defaults ([#12](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/12)).

### Fixed

- The editable install failed because setuptools found several top-level packages
  ([#3](https://github.com/saicharan-nidiganti/local-ai-benchmark/pull/3)).
- Thinking models (such as qwen3) spent the output budget on hidden reasoning, leaving the
  reply empty and TTFT unmeasured; thinking is now disabled on every request
  ([#4](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/4)).
- A reply with no visible text was counted as a successful run, so its throughput entered
  the medians; it is now a failure, `empty_response`, with the runtime's counts kept
  ([#9](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/9)).
- The default run log was relative to the working folder, so running from another folder
  wrote a second `runs.jsonl` elsewhere. It now resolves to `data/raw/` in the project folder
  (or the folder named by `LOCAL_AI_BENCHMARK_HOME`)
  ([#16](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/16)).

[Unreleased]: https://github.com/saicharan-nidiganti/local-ai-benchmark/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/saicharan-nidiganti/local-ai-benchmark/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/saicharan-nidiganti/local-ai-benchmark/releases/tag/v0.1.0
