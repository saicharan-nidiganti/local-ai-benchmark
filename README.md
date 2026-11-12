# Local AI Benchmark

[![CI](https://github.com/saicharan-nidiganti/local-ai-benchmark/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/saicharan-nidiganti/local-ai-benchmark/actions/workflows/ci.yml)
![Python 3.11 to 3.14](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A reproducible harness for measuring local LLM inference. It runs models served by
[Ollama](https://ollama.com) entirely on your own machine and records time to first token,
end-to-end latency, and generation throughput for every run as raw JSONL, so results can be
audited and compared under fixed conditions.

> **Status.** Phase 1, the measurement harness, is implemented and covered by an offline
> test suite that runs in CI on Python 3.11 to 3.14. A published baseline, structured-output
> reliability, and multi-model comparison are the next phases (see [Roadmap](#roadmap)).

## Why

Comparing local models is easy to get wrong. The first run includes loading the model, sampling
settings change how long the output is, and a single run hides variance. The harness controls
for each of these:

- **Warm-up runs are excluded.** They execute before measurement and are never written to
  the dataset.
- **Settings are fixed and recorded.** Model, prompt, temperature, and output-token limit
  are held constant within a benchmark and stored with every run.
- **Raw data is kept.** Every observation is appended to JSONL; nothing is overwritten or
  pre-aggregated.
- **Summaries are robust.** Results are reported as medians, which a single slow run
  cannot skew.
- **Failures are counted, not hidden.** A failed run is recorded with its error and
  contributes to the error rate.

## What it measures

| Metric | How it is measured |
| --- | --- |
| Time to first token (TTFT) | Wall-clock time from the request to the first streamed token, measured by the client |
| Total latency | Wall-clock time from the request until generation completes |
| Output tokens | Token count reported by the Ollama runtime |
| Throughput | Output tokens divided by the runtime-reported generation time, in tokens per second |
| Load and prompt time | Model load and prompt-processing durations reported by Ollama |
| Error rate | Failed runs divided by all runs in the benchmark |

Definitions and the reasoning behind them: [docs/methodology.md](docs/methodology.md).

## Architecture

```mermaid
flowchart LR
    cli["CLI<br/>ask, benchmark"] --> client["Inference client<br/>streams the response,<br/>times the first token"]
    client <--> ollama[("Ollama runtime<br/>local model")]
    client --> record["Run record<br/>metrics, settings, timestamp"]
    record --> jsonl[("data/raw/runs.jsonl")]
    record --> summary["Summary<br/>medians, error rate"]
```

## Quickstart

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and a running Ollama with a model
pulled.

```bash
ollama pull qwen3:4b

git clone https://github.com/saicharan-nidiganti/local-ai-benchmark.git && cd local-ai-benchmark
uv sync                            # creates .venv from uv.lock, with the dev tools
```

Run a single prompt and print its metrics:

```bash
uv run local-ai-benchmark ask --model qwen3:4b --prompt "Explain TCP vs UDP in 5 bullet points."
```

Benchmark one prompt with one warm-up run and five measured runs:

```bash
uv run local-ai-benchmark benchmark --model qwen3:4b \
  --prompt "Explain TCP vs UDP in 5 bullet points." \
  --repeats 5 --warmup-runs 1 --temperature 0 --max-output-tokens 256
```

Each measured run is appended to `data/raw/runs.jsonl`, and the command prints a summary with
the run count, error rate, and median latency, TTFT, and throughput. `python -m local_ai_benchmark`
works in place of `local-ai-benchmark`.

## Reproducibility

A measurement is only comparable with another taken under the same conditions. Keep these
fixed, and record them with the results:

- hardware, and whether the machine is otherwise idle
- model name, version, and quantization
- Ollama version
- prompt, sampling parameters, and maximum output tokens
- warm-up procedure and number of repetitions

## Testing

```bash
make check                         # lint, strict type check, tests with coverage
```

Without make (for example in Windows PowerShell), run the commands from the
[Makefile](Makefile): `uv run ruff check .`, `uv run mypy`, `uv run python -m pytest --cov`.

The suite is offline: it replaces the Ollama client with a simulated token stream, so it
needs no model or server. It covers metric calculation, throughput edge cases, connection
failures and streams that fail partway, warm-up exclusion, and the settings stored with
each run. CI runs Ruff, mypy `--strict`, and the tests (coverage floor 90%) on Python 3.11
to 3.14 and on Windows, and checks that the built wheel installs and runs.

## Roadmap

1. **Measurement harness.** TTFT, latency, throughput, JSONL logging, repeatable runs.
   *Done.*
2. **Baseline.** A published five-run baseline for one model on fixed, documented hardware.
3. **Structured output.** Pydantic schemas, JSON validation, bounded retry and repair, and
   a reliability rate per model.
4. **Prompt suite.** A versioned suite of 30 to 50 prompts across task categories
   (`benchmarks/prompts_v1.jsonl` holds the first three).
5. **Model comparison.** A controlled three-model comparison with reports and figures.

## Project layout

```text
src/local_ai_benchmark/   cli.py (commands), inference.py (Ollama client and timing), metrics.py (summaries)
benchmarks/   versioned prompt suites
configs/      benchmark settings and model definitions
docs/         methodology
tests/        offline test suite
data/raw/     run logs (git-ignored)
```

## License

[MIT](LICENSE)
