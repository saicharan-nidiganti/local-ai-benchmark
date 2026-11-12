# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Offline test suite (13 tests) for the inference client, the CLI and the summaries, run in
  CI on Python 3.11 to 3.14 ([#3](https://github.com/saicharan-nidiganti/local-ai-benchmark/pull/3)).
- `local-ai-benchmark` console script ([#3](https://github.com/saicharan-nidiganti/local-ai-benchmark/pull/3)).

### Fixed

- The editable install failed because setuptools found several top-level packages
  ([#3](https://github.com/saicharan-nidiganti/local-ai-benchmark/pull/3)).
- Thinking models (such as qwen3) spent the output budget on hidden reasoning, leaving the
  reply empty and TTFT unmeasured; thinking is now disabled on every request
  ([#4](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/4)).
