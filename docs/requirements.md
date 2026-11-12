# Requirements

Last updated: 2026-11-13

## Purpose

Build a small-language-model (SLM) application that runs **entirely offline** on consumer
hardware, benchmark its inference performance, compare three models on the same machine, and
document the quality-against-speed tradeoffs, showing that privacy, latency and cost
constraints are understood and measured rather than asserted.

## Scope

In scope: models served locally by [Ollama](https://ollama.com); a reference laptop with a
4 GB GPU ([environment.md](environment.md)); one concrete, privacy-sensitive use case
(chosen in [#18](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/18)).

Out of scope: hosted model APIs as a runtime (they appear only as a cost reference), model
training or fine-tuning, multi-user serving, and GPUs larger than the reference machine.

## How to read this document

Each requirement has a stable ID used in issues, pull requests, ADRs and the
[architecture](architecture.md). **Status** is one of *Met*, *Partial* or *Planned*. A
requirement counts as *Met* only when its verification exists and passes.

## Functional requirements

| ID | Requirement | Verified by | Milestone | Issues | Status |
| --- | --- | --- | --- | --- | --- |
| FR-1 | Run models through a local runtime with no hosted model API | A live run on the reference machine; the suite completes with networking off | Phase 0, 4 | [#2](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/2), [#27](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/27) | Partial: runs locally, not yet shown with networking off |
| FR-2 | Measure per run: TTFT, total latency, decode and prefill throughput, model load time | Offline tests of the inference client; live baseline | Phase 1 | [#4](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/4), [#13](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/13) | Met |
| FR-3 | Measure per run: peak RAM, VRAM, GPU offload share, GPU power draw | Offline tests with a fake sampler; live baseline | Phase 1 | [#15](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/15) | Met |
| FR-4 | Make runs reproducible: fixed and recorded settings (temperature, seed, context length, output limit, thinking), warm-up exclusion, a run ID and an environment manifest | Two runs from one config record identical settings; one manifest per run ID | Phase 1 | [#11](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/11), [#12](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/12), [#14](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/14) | Met |
| FR-5 | Keep every observation in an append-only log, and rebuild summaries from it | `summarize` reproduces the printed summary | Phase 1 | [#13](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/13), [#16](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/16) | Met: `summarize` rebuilds the printed summary from the log, from any folder |
| FR-6 | Score output quality on a versioned task suite for one use case, with automatic scorers | Scorer unit tests; one command scores the suite | Phase 2 | [#18](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/18) to [#22](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/22) | Planned |
| FR-7 | Compare three models on the same hardware, suite and settings | Three complete run IDs with manifests | Phase 3 | [#23](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/23), [#24](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/24) | Planned |
| FR-8 | Report quality against speed, with figures, from the log | The report names the fastest, the most accurate and the best-tradeoff model | Phase 3, 4 | [#25](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/25), [#26](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/26), [#30](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/30) | Planned |
| FR-9 | Keep prompts and replies on the machine; refuse a non-local runtime unless explicitly allowed | Offline test of the refusal; suite run with networking off | Phase 4 | [#27](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/27) | Planned |
| FR-10 | Set latency targets for interactive use and evaluate each model cold and warm | Each model marked as meeting or missing each target | Phase 4 | [#28](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/28) | Planned |
| FR-11 | Estimate cost per million output tokens from measured power draw and hardware amortization, against a dated hosted-API price | Stated assumptions and per-model figures | Phase 4 | [#29](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/29) | Planned |
| FR-12 | Provide an offline application for the chosen use case on the recommended model | The app works with networking off | Phase 5 | [#31](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/31) | Planned |

## Non-functional requirements

| ID | Requirement | Verified by | Issues | Status |
| --- | --- | --- | --- | --- |
| NFR-1 | Run on the reference machine: a 4 GB laptop GPU and 16 GB of RAM | Offload share recorded per run | [#15](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/15), [#23](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/23) | Met: runs, with the GPU share recorded on every run (qwen3:4b 66%, llama3.2:3b 80% at 4096 tokens) |
| NFR-2 | Test offline: no model or server needed; CI on Python 3.11 to 3.14 and on Windows | CI | [#3](https://github.com/saicharan-nidiganti/local-ai-benchmark/pull/3), [#6](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/6) | Met |
| NFR-3 | Keep the code maintainable: Ruff, mypy `--strict`, coverage floor of 90%, locked dependencies, protected `main` | CI; branch protection | [#5](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/5), [#6](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/6), [#8](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/8) | Met |
| NFR-4 | Record failures with their cause, never drop them, and report the error rate | Offline tests of failure paths | [#9](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/9), [#10](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/10) | Met |
| NFR-5 | Document every consequential decision as an ADR and keep the architecture current | Review of each pull request | [#7](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/7) | Met |
| NFR-6 | Work on Windows (the reference machine) and Linux (CI) | CI on both | [#6](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/6) | Met |

## Traceability

Every issue names the requirements it serves under **Traceability**, and every pull request
links its issue. A requirement's status changes in the pull request that meets it.
