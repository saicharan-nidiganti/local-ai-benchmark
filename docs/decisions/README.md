# Architecture decision records

An architecture decision record (ADR) captures one consequential decision: the problem, the
options, the choice and its consequences. ADRs are never edited to say something new; a
changed decision gets a new ADR that supersedes the old one.

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-ollama-as-the-local-runtime.md) | Ollama as the local inference runtime | Accepted |
| [0003](0003-append-only-jsonl-run-log.md) | An append-only JSON Lines run log | Accepted |
| [0004](0004-measurement-protocol.md) | Measurement protocol | Accepted |
| [0005](0005-packaging-and-toolchain.md) | Packaging and toolchain | Accepted |
| [0006](0006-configuration-and-pinned-settings.md) | Configuration precedence and pinned generation settings | Accepted |
| [0007](0007-run-identity-and-manifests.md) | Run identity and environment manifests | Accepted |
| [0008](0008-use-case-support-ticket-triage.md) | Use case: support-ticket triage | Accepted |
| [0009](0009-structured-output-for-json-tasks.md) | Structured output for the JSON tasks | Accepted |
| [0010](0010-three-models-to-compare.md) | The three models to compare | Accepted |
| [0011](0011-local-only-runtime-and-connection-audit.md) | A local-only runtime by default, and a connection audit on every run | Accepted |

No decision is open. New ones are tracked as issues labelled `decision`.

## Process

1. Copy [template.md](template.md) to `NNNN-short-title.md`, using the next number.
2. Fill it in, link the issue and the requirements it serves, and add it to the index.
3. Commit it in the pull request that introduces the decision. Merging the pull request
   accepts the ADR.
