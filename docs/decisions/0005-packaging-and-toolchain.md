# ADR-0005: Packaging and toolchain

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#5](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/5),
  [#6](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/6)
- **Requirements:** NFR-2, NFR-3, NFR-6

## Context

The package was called `app`, sat at the repository root, installed only after a packaging
fix, and had unpinned dependencies. Nothing linted or type-checked it, and CI ran tests only.
Results depend on the exact code and dependency versions, so both must be reproducible.

## Decision drivers

1. Reproducible environments from a lockfile, on Windows and Linux.
2. Checks that run identically on a laptop and in CI.
3. Few tools, each standard in the Python ecosystem.
4. The same conventions as the owner's other projects.

## Options considered

| Question | Chosen | Alternatives |
| --- | --- | --- |
| Layout | src layout, package `local_ai_benchmark` | Flat layout: tests can import the source tree instead of the installed package |
| Build backend | hatchling | setuptools: needs package discovery settings in a flat layout |
| Environment and lock | uv with a committed `uv.lock` | pip with `requirements.txt`; Poetry |
| Lint and format | Ruff | flake8 plus black plus isort: three tools for one job |
| Types | mypy `--strict` over `src` | pyright; no type checking |
| Task runner | Makefile whose recipes are plain `uv` commands | nox or tox: another tool; scripts: no single entry point |

## Decision

Adopt the choices marked in the table. CI calls the Makefile targets, and the same commands
run in PowerShell without make (see [CONTRIBUTING.md](../../CONTRIBUTING.md)).

## Consequences

### Positive

- `uv sync` recreates the exact environment; `make check` locally predicts CI.
- Strict typing and lint catch whole classes of mistakes before review.

### Negative and risks

- Contributors need uv; installation is one command on each platform.
- `make` is not standard on Windows, so the commands are documented for PowerShell too.

## Revisit when

- uv or Ruff stops being maintained, or a dependency needs a build step uv cannot handle.
