# ADR-0007: Run identity and environment manifests

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#13](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/13),
  [#14](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/14)
- **Requirements:** FR-4, FR-5

## Context

Two identical requests on 2026-09-25 differed by 45% in throughput, and nothing in the log
said why: the records did not say which machine state, Ollama version or model build produced
them, nor which records belonged to the same benchmark. A comparison across models and days
needs both: a key that groups the records of one invocation, and a description of the
environment that invocation ran in.

## Decision drivers

1. Every published number traces to one invocation and the environment it ran in.
2. Run records stay small and uniform; the environment is not repeated on every line.
3. No new storage technology ([ADR-0003](0003-append-only-jsonl-run-log.md)).
4. Collecting the environment never makes a benchmark fail.

## Options considered

| Question | Chosen | Alternatives |
| --- | --- | --- |
| Run ID | UTC time plus 6 random hex digits (`20261113T061512Z-3fa9c2`): sorts by time, unique enough for one machine | A UUID: unique but unreadable and unsorted; a counter: needs shared state |
| Where the environment lives | One line per run ID in `manifests.jsonl`, beside the run log | Repeated on every record: bloats the log; a file per run: many small files |
| What it holds | Harness version and git commit (and whether the tree was dirty), Python, OS, CPU, RAM, NVIDIA GPUs, AC power, Ollama version and host, model digest, family, size, quantization and capabilities | Less: misses the causes seen so far; more (drivers of every device): noise |
| When it is collected | Once per invocation, after the preflight, reusing its answers | Per run: repeats identical data |

## Decision

Adopt the choices marked in the table. Every probe degrades to null when its source is
missing (no `git`, no `nvidia-smi`, no battery), so a manifest never stops a benchmark.

## Consequences

### Positive

- A result can be rebuilt (`summarize --run-id`) and explained (the manifest) from the
  files alone.
- `git_dirty` shows when a number came from uncommitted code.

### Negative and risks

- Two files must be kept together when results are shared; the curated results folder
  copies the manifest beside the summary.
- The manifest is a snapshot at the start; a change mid-run (unplugging the charger) shows
  only in the resource samples ([#15](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/15)).

## Revisit when

- Results come from several machines and need a machine identity beyond the manifest.
