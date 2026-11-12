# Contributing

This project is run like a small engineering team's: every change starts from an issue, goes
through a pull request with green CI, and lands as one squashed commit on `main`.

## Set up

Requires [uv](https://docs.astral.sh/uv/) and, for live runs, [Ollama](https://ollama.com).

Windows (PowerShell):

```powershell
winget install astral-sh.uv
winget install Ollama.Ollama
git clone https://github.com/saicharan-nidiganti/local-ai-benchmark.git
cd local-ai-benchmark
uv sync                     # .venv from uv.lock, with the dev tools
uv run pre-commit install   # lint, format and type-check on every commit
ollama pull qwen3:4b        # only needed for live runs
```

Linux and macOS: install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh` and Ollama
from [ollama.com/download](https://ollama.com/download), then run the same commands from
`git clone` on.

## Everyday commands

CI runs the Makefile targets. Without make, run the command beside each one.

| make | Command | What it does |
| --- | --- | --- |
| `make install` | `uv sync --frozen` | Install the locked dependencies and dev tools |
| `make lint` | `uv run ruff check .` and `uv run ruff format --check .` | Lint and format check |
| `make format` | `uv run ruff check --fix .` and `uv run ruff format .` | Apply fixes and formatting |
| `make typecheck` | `uv run mypy` | mypy `--strict` over `src` |
| `make test` | `uv run python -m pytest --cov --cov-report=term` | Offline tests; fails under 90% coverage |
| `make check` | all three above | What the CI quality jobs run |
| `make package` | `uv build`, then the CLI from the wheel | Packaging check |
| `make lock-check` | `uv lock --check` | `uv.lock` matches `pyproject.toml` |

Add a dependency with `uv add <package>` (or `uv add --group dev <package>` for a tool), and
commit `pyproject.toml` and `uv.lock` together.

## Workflow

1. **Issue first.** Find or open an issue (the templates ask for context, tasks and
   acceptance criteria). It belongs to a phase milestone and carries type, area and priority
   labels.
2. **Branch** from `main`: `<type>/<issue>-<short-slug>`, for example
   `fix/9-empty-reply-is-a-failure`.
3. **Commit** in [Conventional Commits](https://www.conventionalcommits.org/) form:
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `build:`, `ci:`, `perf:` or `chore:`, an
   imperative summary under 72 characters, and a body that says why.
4. **Open a pull request** with the template, one issue per pull request, and `Closes #N`.
5. **Merge** when CI is green and the checklist is done. Pull requests are squash-merged and
   their branches deleted automatically.

## Definition of done

- [ ] The issue's acceptance criteria are met.
- [ ] `make check` passes; CI is green.
- [ ] Tests cover the change; a bug fix comes with a test that fails without it.
- [ ] Documentation reflects the change: `docs/architecture.md` for structure or data,
      `docs/methodology.md` for metrics, `docs/requirements.md` for a requirement's status.
- [ ] A consequential decision has an ADR in `docs/decisions/`.
- [ ] `CHANGELOG.md` has a line under **Unreleased**.

## Experiments and data

Issues labelled `experiment` produce measurements.

- Measure on the reference machine ([docs/environment.md](docs/environment.md)), plugged in
  and idle, and record the run ID and manifest with the results.
- The raw log (`data/raw/`) never enters git: it holds full prompts and replies. Commit only
  curated summaries and reports.
- Never put personal or confidential text in a prompt suite.

## Releases

Versions follow [Semantic Versioning](https://semver.org/): v0.1.0 at the end of Phase 1,
v0.2.0 at the end of Phase 3, and v1.0.0 at the end of Phase 5. A release moves the
**Unreleased** section of the changelog under the new version, tags the commit, and publishes
a GitHub release.
