# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Removed

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

[Unreleased]: https://github.com/saicharan-nidiganti/local-ai-benchmark/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/saicharan-nidiganti/local-ai-benchmark/releases/tag/v0.1.0
