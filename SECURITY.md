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

- **Where requests go.** The harness sends prompts only to the Ollama server it is given,
  `localhost:11434` by default. It sends no telemetry. Refusing a non-local host unless
  explicitly allowed is planned
  ([#27](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/27)).
- **What is stored.** Every run, including the full prompt and reply, is appended to
  `data/raw/runs.jsonl` on the local disk. That folder is git-ignored and never published;
  only curated summaries are committed.
- **What to keep out.** Do not put personal or confidential text in prompts, task suites or
  issues. Treat the raw log like the prompts it contains.
- **The runtime.** Ollama is a separate program with its own update and network behaviour;
  see its documentation. Running the suite with networking turned off, to show that nothing
  depends on the network, is planned in the same issue.

## Dependencies

Dependencies are pinned in `uv.lock`, and pull requests that update them are reviewed and run
through CI like any other change.
