# Security and privacy

## Supported versions

The latest release and `main` receive fixes. Older versions do not.

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub security advisories](https://github.com/saicharan-nidiganti/local-ai-benchmark/security/advisories/new),
not as public issues. Include the version or commit, the steps to reproduce, and the impact.
You can expect an acknowledgement within a week.

## Privacy model

The project's purpose is to run language models without sending data anywhere.

- **Where requests go.** The harness sends prompts only to the Ollama server on this
  machine, `127.0.0.1:11434` by default, and sends no telemetry. An `OLLAMA_HOST` on another
  machine is refused before any request unless `--allow-remote` is given
  ([ADR-0011](docs/decisions/0011-local-only-runtime-and-connection-audit.md)).
- **What is checked.** During every measured run the harness reads the connection table and
  records any connection from Ollama, its model runner or the harness to another machine
  (`remote_connections` in each record and summary). The manifest records which network
  interfaces were up.
- **What is stored.** Every run, including the full prompt and reply, is appended to
  `data/raw/runs.jsonl` on the local disk. That folder is git-ignored and never published;
  only curated summaries are committed.
- **What to keep out.** Do not put personal or confidential text in prompts, task suites or
  issues. Treat the raw log like the prompts it contains.
- **The runtime.** Ollama is a separate program with its own update and network behaviour;
  see its documentation. Models are downloaded once with `ollama pull`, before any
  measurement; after that, inference needs no network, which the published networking-off
  run shows.

## Dependencies

Dependencies are pinned in `uv.lock`, and pull requests that update them are reviewed and run
through CI like any other change.
