# ADR-0006: Configuration precedence and pinned generation settings

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#12](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/12)
- **Requirements:** FR-4

## Context

`configs/benchmark.yaml` and `configs/models.yaml` existed but were never read: the defaults
lived in the CLI's argument parser, so the same setting had two sources. The seed and the
context length were not set at all, so Ollama's defaults applied, and those can change between
Ollama versions or models. The context length matters more than it looks: it sets the size of
the key-value cache, and with it how much of a model fits in 4 GB of VRAM.

## Decision drivers

1. One source of truth for each setting, versioned in git.
2. Quick experiments from the command line without editing files.
3. Every value that can change a result is set explicitly and recorded.
4. A typo in a file fails loudly instead of being ignored.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Flags only | Simple | Settings live in shell history; nothing versioned |
| Config file only | Reviewed and versioned | Every experiment needs an edit |
| **Defaults, then the file, then explicit flags** | Versioned baseline, cheap overrides | Three layers to explain |
| Environment variables as a fourth layer | Common in services | Invisible in the record unless also logged; not needed for a CLI |

## Decision

Built-in defaults, then `configs/benchmark.yaml` (or `--config`), then flags the user actually
gave. A flag that was not given never overrides the file. Unknown keys, wrong types and
negative counts are errors naming the file and the key. `seed` (42) and `num_ctx` (4096) are
sent on every request, and every record carries `model_id`, `temperature`,
`max_output_tokens`, `seed`, `num_ctx` and `keep_alive`. A model is named by an Ollama tag or by
an id from `configs/models.yaml`, and records keep both.

## Consequences

### Positive

- Two runs from the same files and flags send identical requests, and the log proves it.
- Changing the context length is an explicit, recorded decision, which the 4 GB memory limit
  requires.

### Negative and risks

- A fixed seed with temperature 0 makes repeats nearly identical in output length; variance
  then comes from the runtime, which is what this harness measures.
- Records written before this change lack the new fields.

## Revisit when

- A setting has to vary within one benchmark (for example a sweep over context lengths).
