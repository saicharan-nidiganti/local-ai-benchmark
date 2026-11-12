# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
