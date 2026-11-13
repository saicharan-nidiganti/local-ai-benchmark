# ADR-0011: A local-only runtime by default, and a connection audit on every run

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#27](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/27)
- **Requirements:** FR-9

## Context

The project's claim is that prompts and replies never leave the machine. Until now the claim
rested on a default: the harness talks to `OLLAMA_HOST`, `http://127.0.0.1:11434` unless the
variable says otherwise. One environment variable, set for another tool, would send every
prompt to another machine without a word. And nothing measured whether any connection left
the machine during a run.

## Decision drivers

1. Privacy has to be shown, not claimed (the Phase 4 gate).
2. A mistake in the environment must not leak data silently.
3. Evidence on every run, not only in one experiment.
4. No new dependency and no cost to the measurements.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Document the default only | Nothing to build | A stray `OLLAMA_HOST` leaks silently; nothing is measured |
| **Refuse a non-local host unless `--allow-remote`; audit connections during every run** | Fails safe; evidence in every record; costs 3 ms per sample | The audit samples every 0.5 s and can miss a connection that opens and closes between samples |
| Block the network with a firewall rule while measuring | Strongest guarantee | Needs administrator rights; changes the machine; not portable |
| Resolve the host name and allow any name that resolves to loopback | Accepts aliases | Resolving a name can itself reach the network |

## Decision

- **Refusal.** Before any request, the preflight refuses an Ollama host that is not
  `localhost` or a loopback address (127.0.0.0/8, `::1`), with exit code 3 and what to do.
  Names are not resolved. `--allow-remote` is the explicit opt-out, and the manifest records
  `runtime.local` either way.
- **Audit.** The resource sampler also reads the connection table at every sample and keeps
  the remote ends (`address:port`) of connections from the Ollama server, its model runner
  and the harness itself that are not loopback. A LAN address counts as another machine.
  Each run records `remote_connections` and `remote_endpoints`; summaries add them up, and
  `benchmark` and `suite` print one line saying whether anything reached another machine.
- **Context.** The manifest records `network.interfaces_up`, the interfaces with a routable
  address, so a run with networking off can be told apart from one with it on.
- **Proof.** The suite is run with networking turned off, and the result is published.

## Consequences

### Positive

- A misconfigured environment stops before sending anything.
- Every run carries its own evidence, and the published results show it.

### Negative and risks

- Sampling can miss a connection shorter than the interval; the networking-off run covers
  what sampling cannot.
- On Linux, connections of a server running as another user (the `ollama` service) are not
  visible without root; their fields are then empty rather than zero.
- Ollama's own downloads (`ollama pull`) and its desktop app's update check are outside the
  harness; models are pulled once, before any measurement.

## Revisit when

- The app (Phase 5) serves requests from another device on purpose.
