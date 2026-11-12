# Roadmap

Last updated: 2026-11-13

Six phases take the project from a clean foundation to an offline app backed by a published
three-model comparison. Each phase is a GitHub milestone; each task is an issue in it. A phase
is done when its gate is met, and the next one starts only then.

| Phase | Goal | Gate (done when) | Release | Milestone |
| --- | --- | --- | --- | --- |
| 0. Foundation | Clean repository, tooling, documentation, working local runtime | Lint, types and tests pass locally and in CI; `ollama list` shows qwen3:4b; requirements, architecture and ADRs on `main` | | [Phase 0](https://github.com/saicharan-nidiganti/local-ai-benchmark/milestone/1) |
| 1. Measurement harness | Reproducible timing and resource measurement | A qwen3:4b benchmark of 1 warm-up and 5 runs under one run ID, with manifest and resource samples; `summarize` reproduces it from the file | v0.1.0 | [Phase 1](https://github.com/saicharan-nidiganti/local-ai-benchmark/milestone/2) |
| 2. Task suite | Quality scoring for one privacy-sensitive use case | One command scores the whole suite for one model | | [Phase 2](https://github.com/saicharan-nidiganti/local-ai-benchmark/milestone/3) |
| 3. Model comparison | Three models, same hardware and settings | The report names the fastest, the most accurate and the best-tradeoff model | v0.2.0 | [Phase 3](https://github.com/saicharan-nidiganti/local-ai-benchmark/milestone/4) |
| 4. Privacy, latency and cost | Constraints measured, not asserted | A Tradeoffs section covers all three, each backed by a measured number | | [Phase 4](https://github.com/saicharan-nidiganti/local-ai-benchmark/milestone/5) |
| 5. Offline app and v1.0.0 | A usable app on the recommended model | Someone can clone the repo, run the app offline and reproduce the comparison | v1.0.0 | [Phase 5](https://github.com/saicharan-nidiganti/local-ai-benchmark/milestone/6) |

Each phase maps to requirements in [requirements.md](requirements.md): Phase 1 covers FR-2 to
FR-5, Phase 2 FR-6, Phase 3 FR-7 and FR-8, Phase 4 FR-9 to FR-11, and Phase 5 FR-12.

## Working on the roadmap

- Pick an open issue from the current milestone; issues labelled `priority:P0` come first.
- Issues labelled `decision` need the owner's choice, recorded as an ADR, before the work
  that depends on them.
- Issues labelled `experiment` produce data: record the run ID and manifest, and commit only
  curated results.

Status per issue lives on GitHub; this page changes only when a phase's scope or gate does.
