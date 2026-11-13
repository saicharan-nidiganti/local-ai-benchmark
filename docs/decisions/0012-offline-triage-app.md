# ADR-0012: The offline app: a triage command and a local web page

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#31](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/31)
- **Requirements:** FR-12, FR-9

## Context

The benchmark answers which model to run; the brief also asks for an app that runs it. The use
case is support-ticket triage ([ADR-0008](0008-use-case-support-ticket-triage.md)), the
recommended model is phi4-mini, the best tradeoff of the comparison
([results](../../results/2026-11-13-three-model-comparison/)), and the app must work with
networking off and keep the tickets on the machine.

## Decision drivers

1. The app must answer the way the benchmark measured, or the measurements do not describe it.
2. Privacy: tickets hold names and order numbers; nothing may leave the machine or be kept.
3. Usable by an agent who does not use a terminal, and scriptable by one who does.
4. No new dependency, and a small surface to secure and test.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| A command only | Smallest; scriptable | Not usable without a terminal |
| **A command, and a web page on the standard library, sharing one core** | Both audiences; no new dependency; testable offline | A hand-written HTTP handler to keep safe |
| A web framework (FastAPI, Flask) | Routing, validation | New dependencies and a larger surface for one page and one endpoint |
| A desktop window (Tkinter) | No browser | Harder to test and to make look right; one platform look |

## Decision

- **One core, `app.triage`**: the suite's three prompts in its order (classify, extract,
  summarize), the JSON tasks constrained to the same pydantic schemas through Ollama's
  structured output ([ADR-0009](0009-structured-output-for-json-tasks.md)), the pinned
  generation settings, and phi4-mini unless `--model` says otherwise. A failed or malformed
  reply is reported beside the answers that did arrive. Tickets over 4,000 characters are
  refused, to stay well inside the 4,096-token context.
- **`triage`**: a ticket from a file, standard input or `--text`; the answer as text or
  `--json`.
- **`serve`**: one self-contained page and one JSON endpoint, `POST /api/triage`, on Python's
  `http.server`. It listens on 127.0.0.1 only; answers only requests whose `Host` is
  `127.0.0.1` or `localhost` on its port (a page elsewhere that rebinds its DNS name to
  127.0.0.1 still sends its own name); refuses a POST from another origin; caps bodies at
  16 KB; and sends a Content-Security-Policy that lets the page load nothing from anywhere
  else. One ticket runs at a time, since one GPU runs one model. The model is loaded before
  the first ticket.
- **Nothing kept.** Neither command writes the ticket or the answer anywhere; the server logs
  the method, path and status of each request, never its body. Both refuse a remote runtime
  as the benchmark does ([ADR-0011](0011-local-only-runtime-and-connection-audit.md)).

## Consequences

### Positive

- The app's quality, speed and cost are the ones measured for phi4-mini.
- No dependency was added; the page works in any browser with networking off.

### Negative and risks

- Three requests per ticket take 3 to 4 s with the model loaded, and longer when it must load.
- The page is for one person on this machine: there are no accounts and no history.

## Revisit when

- Several agents need to share one machine, or triage must run on a server.
