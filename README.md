# Local AI Benchmark

[![CI](https://github.com/saicharan-nidiganti/local-ai-benchmark/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/saicharan-nidiganti/local-ai-benchmark/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/saicharan-nidiganti/local-ai-benchmark)](https://github.com/saicharan-nidiganti/local-ai-benchmark/releases)
![Python 3.11 to 3.14](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)
![Inference: local only](https://img.shields.io/badge/inference-local%20only-success)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Which small language model should you run on a laptop with a 4 GB GPU?** This project
answers by measurement. Three models served by [Ollama](https://ollama.com) run entirely
offline on the same machine, task suite and settings; every run is logged as raw JSONL with
its environment, and the report names the most accurate model, the fastest and the best
tradeoff.

<p align="center">
  <a href="results/2026-11-13-three-model-comparison/">
    <img src="results/2026-11-13-three-model-comparison/quality_vs_speed.svg"
         alt="Overall quality against decode speed: qwen3:4b-instruct and phi4-mini at 0.89, llama3.2:3b at 0.81 and the fastest"
         width="640">
  </a>
</p>

| Model | Quality (0 to 1) | Decode speed | Median task latency | GPU energy per task | On GPU |
| --- | --- | --- | --- | --- | --- |
| qwen3:4b-instruct | **0.89** | 30.3 tokens/s | 1.43 s | 56 J | 66% |
| phi4-mini | **0.89** | 34.6 tokens/s | 1.24 s | 43 J | 64% |
| llama3.2:3b | 0.81 | **53.0 tokens/s** | **0.75 s** | **29 J** | 80% |

**Verdict: phi4-mini is the best tradeoff.** It matches qwen3:4b-instruct on quality with 14%
more speed and 23% less energy. llama3.2:3b is the fastest and as good at classification
and extraction, but its summaries miss facts.
[Full results](results/2026-11-13-three-model-comparison/).

**The app** runs that pick offline: paste a support ticket, get its category, priority,
order number, customer, product, issue and a summary in about 3 s, with nothing leaving the
machine ([The app](#the-app)).

> **Status: all six phases complete, release v1.0.0.** Measurement harness, task suite, three-model
> comparison, privacy, latency and cost measured with networking off, and the offline
> triage app. See [Project status](#project-status).

## Contents

- [Results](#results)
- [Tradeoffs: privacy, latency and cost](#tradeoffs-privacy-latency-and-cost)
- [The app](#the-app)
- [Why the numbers can be trusted](#why-the-numbers-can-be-trusted)
- [How it works](#how-it-works)
- [What it measures](#what-it-measures)
- [Quickstart](#quickstart)
- [Reproduce the results](#reproduce-the-results)
- [Commands](#commands)
- [Engineering](#engineering)
- [Project status](#project-status)
- [Documentation](#documentation)
- [Project layout](#project-layout)

## Results

Measured on the reference laptop (Ryzen 9 5900HX, RTX 3050 Laptop GPU 4 GB, 16 GB RAM,
Windows 11, plugged in), Ollama 0.40.16, every model Q4_K_M, on the 45 tasks of the
`support_triage_v1` suite: 15 fictional support tickets, each classified, extracted to JSON
and summarized.

- **qwen3:4b-instruct and phi4-mini are level on quality** (0.894 against 0.887, less than one
  label apart). qwen3:4b-instruct classifies slightly better; phi4-mini summarizes better.
- **phi4-mini is the best tradeoff**: the same quality, 14% faster decoding, 13% lower median
  latency and 23% less GPU energy per task.
- **llama3.2:3b is 1.75 times faster** than qwen3:4b-instruct at half the energy, and more of it
  fits on the GPU. It scores as well on classification and extraction; summaries drag it down
  (0.71).
- **Every model over-escalates priority.** Categories are right for 12 to 14 of 15 tickets,
  priorities for only 8 to 10, and 17 of the 18 wrong priorities are one level too high.
- **Structured output removes JSON failures**: all 90 JSON replies parse and match the schema.
- **No model fits in 4 GB of VRAM**: Ollama keeps 64 to 80% on the GPU and runs the rest on the
  CPU.

| Experiment | Finding |
| --- | --- |
| [Privacy, latency and cost, offline](results/2026-11-13-offline-privacy-latency-cost/) | With networking off: the same 135 replies and 0 connections to another machine; every model meets every latency target; cost per model against the same model hosted |
| [The app, offline](results/2026-11-13-offline-app/) | `triage` and the web page answer three fictional tickets with networking off, about 3 s each; a foreign Host header is refused |
| [Three-model comparison](results/2026-11-13-three-model-comparison/) | Findings, chart, quality per task and ticket category, speed, resources, run identities, limits, how to reproduce |
| [qwen3:4b baseline](results/2026-11-13-qwen3-4b-baseline/) | 30.8 tokens/s, 47 ms to the first token warm, 600 tokens/s prefill, 320 J per 256-token answer |

## Tradeoffs: privacy, latency and cost

Measured with networking off on the reference laptop, the three models above
([results](results/2026-11-13-offline-privacy-latency-cost/)). The hosted column is the same
models' published API prices on 13 November 2026; hosted latency was not measured here.

| | Local, this laptop | Hosted API, same model |
| --- | --- | --- |
| Where prompts and replies go | Nowhere: 0 connections to another machine in 150 runs with networking off | To the provider, every request |
| Without a network | Works: the same 135 replies, byte for byte, as online | Does not work |
| First token | 92 to 203 ms with the model loaded; a median 3.3 to 4.5 s after an unload | Not measured here; includes the network round trip |
| Decode speed | 29 to 52 tokens/s, 3 to 5 times the 10 tokens/s target | Not measured here |
| Per million output tokens | INR 1.93 to 3.57 of GPU electricity; INR 61 to 109 counting the laptop's whole price | INR 18.90 to 31.18 |
| Per 1,000 triage tasks | INR 0.07 to 0.11 of electricity; INR 2.09 to 3.43 with the laptop | INR 1.83 to 3.35 |
| Models that fit | 3B to 4B at 4-bit, 64 to 80% of each on the 4 GB GPU | Any size the provider offers |

**Where local wins**

- **Data that must not leave the machine.** Support tickets carry names, order numbers and
  account details. Here that is enforced (a remote runtime is refused) and audited on every
  run, not only promised.
- **No network, or an unreliable one.** Every task completes offline with the same answers.
- **A machine you already own.** The extra cost is electricity: 5 to 16 times below the hosted
  price per output token, 20 to 30 times per task, because hosted APIs also bill the 137 to
  161 prompt tokens of every task.
- **Interactive use.** With the model loaded, the first token arrives in 0.1 to 0.2 s, five to
  ten times inside the 1 s limit for an uninterrupted flow of thought.

**Where a hosted model is the better choice**

- **Hardware bought only for this.** At 8 hours a day for 4 years, the laptop's price makes
  local 2 to 6 times the hosted price per token.
- **Quality beyond a 4B model.** The best model here scores 0.89 and over-escalates ticket
  priority; larger hosted models are a request away, if the data may leave the machine.
- **High or bursty volume.** One laptop decodes 29 to 52 tokens/s; a hosted API scales with
  demand.
- **Rare, occasional use.** A model that is not loaded takes 3 to 7 s to its first token here.

The local energy is the GPU board's alone, so local electricity is a lower bound; every price,
the tariff and the exchange rate are sourced and dated in
[configs/cost.yaml](configs/cost.yaml).

## The app

Support-ticket triage on phi4-mini, the comparison's best tradeoff, entirely on this machine:
the category and priority, the order number, customer, product and issue, and a summary of
at most 40 words. It asks the model exactly what the suite measured, the same prompts and
JSON schemas, so the quality, speed and cost above describe it
([ADR-0012](docs/decisions/0012-offline-triage-app.md)).

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/triage-app-dark.png">
    <img src="docs/images/triage-app-light.png" width="600"
         alt="The triage page: an example ticket about earbuds that do not charge, answered as technical, priority high, with the order number, customer, product, issue and a summary">
  </picture>
</p>

```bash
uv run local-ai-benchmark serve                # the page above, on http://127.0.0.1:8765
uv run local-ai-benchmark triage ticket.txt    # or --text "...", or - for standard input
uv run local-ai-benchmark triage ticket.txt --json
```

- **Works offline:** with networking off, both answered every ticket in 2.7 to 3.6 s with the
  model loaded ([results](results/2026-11-13-offline-app/)).
- **Keeps nothing:** no log of tickets or answers, no file. The page listens on 127.0.0.1
  only, answers only requests addressed to `localhost`, refuses other origins, and loads
  nothing from elsewhere.
- **Knows its limits:** like every model measured, it tends to rate priority one level too
  high; read the priority as a suggestion.

## Why the numbers can be trusted

Comparing local models is easy to get wrong. The first run includes loading the model,
sampling settings change how long the output is, a laptop on battery throttles its GPU, and a
single run hides variance. The harness controls for each:

- **Warm-up runs are excluded.** They execute before measurement and are never written to the
  dataset.
- **Settings are fixed and recorded.** Temperature 0, a fixed seed, context length and output
  limit are held constant and stored with every run.
- **The environment is recorded.** Each run ID has a manifest: hardware, power state, Ollama
  version, model digest and quantization, harness commit and whether the tree was clean.
- **Preflight checks run first.** A server on another machine, or a missing server or model,
  stops the run before any request; running on battery warns, or stops with `--require-ac`.
- **Connections are audited.** Every measured run records any connection from Ollama or the
  harness to another machine, and the summary says whether there was one.
- **Raw data is kept.** Every observation is appended to JSONL; nothing is overwritten or
  pre-aggregated, and every summary can be rebuilt from the log.
- **Summaries are robust.** Medians, which one slow run cannot skew, with p90 and the
  interquartile range beside them.
- **Failures are counted, not hidden.** A failed request is recorded with its error, raises the
  error rate and scores 0.

## How it works

```mermaid
flowchart LR
    subgraph inputs["Inputs"]
        configs["configs/<br/>settings, model registry"]
        suite["benchmarks/<br/>support_triage_v1<br/>45 tasks"]
    end
    subgraph harness["local-ai-benchmark, Python CLI"]
        cli["ask · benchmark · suite<br/>report · summarize"]
        pre["preflight<br/>server, model, power"]
        inf["inference<br/>streams and times<br/>each generation"]
        score["scorers<br/>classify, extract,<br/>summarize"]
        samp["sampler<br/>RAM, VRAM, GPU power"]
        rep["report<br/>verdict, tables, chart"]
    end
    ollama[("Ollama<br/>localhost:11434")]
    gpu{{"RTX 3050 4 GB<br/>and CPU"}}
    log[("data/raw/<br/>runs.jsonl<br/>manifests.jsonl")]
    results[("results/<br/>published folders")]
    configs --> cli
    suite --> cli
    cli --> pre
    pre --> ollama
    cli --> inf
    inf <--> ollama
    ollama --> gpu
    inf --> score
    cli --> samp
    score --> log
    samp --> log
    log --> rep
    rep --> results
```

Inference is local: the harness refuses an Ollama server on another machine unless
`--allow-remote` is given, and audits connections during every run
([ADR-0011](docs/decisions/0011-local-only-runtime-and-connection-audit.md)).
Context, components, the runtime sequence, the run-record schema and the deployment are in
[docs/architecture.md](docs/architecture.md).

## What it measures

**Speed and resources**, for every run:

| Metric | How it is measured |
| --- | --- |
| Time to first token (TTFT) | Wall-clock time from the request to the first streamed token, measured by the client |
| Total latency | Wall-clock time from the request until generation completes |
| Decode speed | Output tokens divided by the runtime-reported generation time |
| Prefill speed | Prompt tokens divided by the runtime-reported prompt-evaluation time |
| GPU share | How much of the loaded model sits in GPU memory, reported by Ollama after each run |
| Resource use | Peak RAM, runtime memory and GPU memory, mean GPU power and GPU energy, sampled every 0.5 s |
| Error rate | Failed runs divided by all runs |

**Quality**, for every task of the suite, from 0 to 1:

| Task | Score |
| --- | --- |
| Classify | Half for the right category, half for the right priority |
| Extract | A quarter for each field: order number, customer name, product and issue |
| Summarize | The share of required facts present; halved above 40 words |
| JSON | Strict, valid and schema-valid rates for the JSON tasks |

Definitions and the reasoning behind them: [docs/methodology.md](docs/methodology.md).

## Quickstart

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com).

```bash
ollama pull phi4-mini
git clone https://github.com/saicharan-nidiganti/local-ai-benchmark.git && cd local-ai-benchmark
uv sync                                         # .venv from uv.lock, with the dev tools
uv run local-ai-benchmark serve                 # the app on http://127.0.0.1:8765
```

Score a model on the 45 tasks, or time one prompt:

```bash
uv run local-ai-benchmark suite --model phi4-mini
uv run local-ai-benchmark benchmark --model phi4-mini --prompt "Explain TCP vs UDP in 5 bullet points."
```

`python -m local_ai_benchmark` works in place of `local-ai-benchmark`.

## Reproduce the results

Every published number comes from these commands. On the reference laptop
([environment](docs/environment.md)) the quality scores come out the same, since the
settings are pinned (temperature 0, seed 42); speed, latency and energy are specific to the
machine, and a few percent of drift between sessions is normal.

1. **Pull the three models** and check their digests against
   [docs/environment.md](docs/environment.md) (`ollama list` shows them):

   ```bash
   ollama pull qwen3:4b-instruct && ollama pull phi4-mini && ollama pull llama3.2:3b
   ```

2. **Check the harness:** `make check` (lint, strict types, the offline tests), or the
   commands in [CONTRIBUTING.md](CONTRIBUTING.md#everyday-commands) without make.

3. **Plug the laptop in, close other work,** and for the privacy result turn networking off.
   `--require-ac` stops a run on battery.

4. **Score each model and time its cold starts:**

   ```bash
   for model in qwen3-4b-instruct phi4-mini llama3.2-3b; do
     uv run local-ai-benchmark suite --model "$model" --require-ac
     uv run local-ai-benchmark benchmark --model "$model" --cold --repeats 5 \
       --max-output-tokens 64 --require-ac --prompt "Explain TCP vs UDP in 5 bullet points."
   done
   ```

   In PowerShell: `foreach ($m in "qwen3-4b-instruct","phi4-mini","llama3.2-3b") { ... }`
   with the same two commands. Each suite prints its quality and whether any connection
   reached another machine.

5. **Write the report** from the latest run of each model, with latency targets, cost and
   privacy:

   ```bash
   uv run local-ai-benchmark report --cost configs/cost.yaml \
     --out-dir results/my-comparison --title "My comparison"
   ```

6. **Compare** `results/my-comparison/README.md` with
   [the published comparison](results/2026-11-13-three-model-comparison/) and
   [the offline run](results/2026-11-13-offline-privacy-latency-cost/). For your own tariff,
   machine or providers, edit `configs/cost.yaml`; every figure in it names its source.

The single-prompt baseline is `benchmark --model qwen3-4b --prompt "Explain TCP vs UDP in 5
bullet points." --repeats 5 --warmup-runs 1` ([baseline](results/2026-11-13-qwen3-4b-baseline/)).
A measurement is only comparable with another taken under the same conditions: hardware and
power, model digest and quantization, Ollama version, prompts and settings, warm-up and
repetitions. Each run's manifest records them.

## Commands

| Command | What it does |
| --- | --- |
| `ask` | One prompt, one measured run, its metrics printed |
| `benchmark` | One prompt, warm-up runs, then repeated measured runs and their summary; `--cold` unloads the model before every run |
| `suite` | Every task of a suite (or one kind with `--tasks`), each reply scored |
| `report` | The latest suite run of each comparison model, or the `--run-id`s given, as a results folder; adds latency targets when a model has a cold benchmark, and cost with `--cost configs/cost.yaml` |
| `summarize` | Rebuilds the summary of any run ID from the log; `--list` lists them |
| `triage` | The app: one ticket's category, priority, order number, customer, product, issue and summary, on phi4-mini unless `--model` says otherwise; `--json` for scripts |
| `serve` | The app as a web page on http://127.0.0.1:8765, reachable from this machine only |

`--model` takes an Ollama tag or an id from [configs/models.yaml](configs/models.yaml).
Settings come from [configs/benchmark.yaml](configs/benchmark.yaml); flags override them,
and every run records the values it used. Measuring commands also take `--require-ac`,
`--allow-remote`, `--no-sampling` and `--output` (the run log; default `data/raw/runs.jsonl`). Exit codes: 0 done,
2 a configuration, suite, run-log or report error, 3 a preflight failure (server on another machine,
server down, model not pulled, or on battery with `--require-ac`). `--help` on any command lists every flag.

## Engineering

```bash
make check                    # lint, strict type check, tests with coverage
```

Without make (for example in Windows PowerShell), run the commands listed in
[CONTRIBUTING.md](CONTRIBUTING.md#everyday-commands).

- **Offline tests.** 224 tests replace the Ollama client with a simulated token stream, so they
  need no model, server or GPU. Coverage is 97% against a floor of 90%.
- **Strict checks.** Ruff for lint and format, mypy `--strict`, pre-commit hooks.
- **CI on every pull request**, all seven required to merge: lint and types, tests on Python 3.11
  to 3.14 and on Windows, and a package check that builds the wheel, installs it and runs it.
- **Protected main.** Pull requests only, linear history, one squash commit per change.
- **Tracked work.** Every change starts as an issue with acceptance criteria under a phase
  milestone; every consequential choice is an [architecture decision record](docs/decisions/).

## Project status

Each phase is a milestone; each task is an issue with acceptance criteria.

| Phase | Goal | Status | Release |
| --- | --- | --- | --- |
| 0. Foundation | Clean repository, tooling, documentation, working local runtime | Done | |
| 1. Measurement harness | Reproducible timing, manifests and resource sampling | Done | [v0.1.0](https://github.com/saicharan-nidiganti/local-ai-benchmark/releases/tag/v0.1.0) |
| 2. Task suite | Quality scoring for one privacy-sensitive use case | Done; optional [#22](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/22) open | |
| 3. Model comparison | Three models, same hardware and settings, quality against speed | Done; optional [#26](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/26) open | v0.2.0 |
| 4. Privacy, latency and cost | Constraints measured, not asserted | Done | |
| 5. Offline app and v1.0.0 | A usable app on the recommended model | Done | v1.0.0 |

Gates and requirements per phase: [docs/roadmap.md](docs/roadmap.md) and
[docs/requirements.md](docs/requirements.md). Every milestone:
[milestones](https://github.com/saicharan-nidiganti/local-ai-benchmark/milestones?state=all).

## Documentation

| Document | Contents |
| --- | --- |
| [Requirements](docs/requirements.md) | What the project must do, with IDs, verification and status |
| [Architecture](docs/architecture.md) | Context, components, runtime flow, data model, deployment |
| [Methodology](docs/methodology.md) | Metric and score definitions, and how each is measured |
| [Environment](docs/environment.md) | Reference hardware, software versions, model digests |
| [Roadmap](docs/roadmap.md) | Phases, gates and milestones |
| [Decisions](docs/decisions/) | Architecture decision records |
| [Results](results/) | Every published experiment |
| [Contributing](CONTRIBUTING.md) | Setup, commands, workflow, definition of done |
| [Security](SECURITY.md) | Privacy model and vulnerability reporting |
| [Changelog](CHANGELOG.md) | Changes per release |

## Project layout

```text
.github/                  CI workflow, issue and pull request templates, CODEOWNERS, Dependabot
benchmarks/               versioned task suites: support_triage_v1, 15 fictional tickets
configs/                  benchmark settings, the model registry and cost assumptions
data/raw/                 run log and manifests (git-ignored)
data/processed/           derived data (git-ignored)
docs/                     requirements, architecture, methodology, environment, roadmap
docs/decisions/           architecture decision records
docs/images/              screenshots of the app
results/                  published results, one folder per experiment
src/local_ai_benchmark/
  cli.py                  commands and argument parsing
  inference.py            streams one generation from Ollama and times it
  preflight.py            server and model checks before any request
  runtime.py              server version, model details, GPU placement
  config.py               settings and the model registry
  suite.py, scorers.py    the task suite, its prompts and scoring
  sampler.py              RAM, VRAM and GPU power during each run
  manifest.py             the environment of each run ID
  metrics.py              run log, run IDs, medians and spreads
  report.py               comparison report: verdict, tables and chart
  app.py, web.py          the offline triage app and its local web page (static/triage.html)
  targets.py              latency targets for interactive use, with their sources
  cost.py                 cost per million tokens and per 1,000 tasks, local against hosted
  paths.py                where the project and the run log live
tests/                    offline test suite
```

## License

[MIT](LICENSE)
