# ADR-0009: Structured output for the JSON tasks

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#21](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/21),
  [#22](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/22)
- **Requirements:** FR-6, FR-12

## Context

The first live suite run (qwen3:4b, prompt only) scored 0 on every classify and extract task.
The model narrated its reasoning in the reply ("We are given a ticket... Step 1...") despite
thinking being off, used the whole 256-token budget, and never reached the JSON. A probe on
one ticket (T04, classify) showed:

| Request | Score | Time | Reply |
| --- | --- | --- | --- |
| qwen3:4b, prompt only (generate or chat, with or without `/no_think`) | 0 | 8.6 to 14.2 s | Reasoning text, no JSON |
| qwen3:4b, thinking on, 1,024 tokens | 0 | 36 s | Empty: all tokens spent thinking |
| qwen3:4b, JSON schema given to the runtime | 1.0 | 0.7 s | `{"category": "refund", "priority": "high"}` |
| llama3.2:3b, prompt only | 0 | 0.2 s | Valid JSON, wrong labels |

Prompt-only JSON therefore measures whether a model obeys a formatting instruction, not
whether it can triage a ticket. An application would not rely on that: Ollama can constrain
decoding to a JSON schema ("structured outputs").

## Decision drivers

1. Measure triage ability, which is what the comparison is about.
2. Run the tasks the way the offline app will (FR-12).
3. Keep instruction-following measurable, since it differs between models.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Prompt only | Measures instruction following | Hides triage ability behind formatting; not how an app is built |
| **The task's JSON schema as Ollama's `format`** | Valid JSON by construction; the score reflects the labels and fields; how the app will call the model | Validity rates become near 1 and stop distinguishing models |
| Free-form `format: "json"` | Valid JSON | Keys and labels are still unconstrained |
| Retry or repair after invalid JSON | Rescues some replies | More calls per task; muddles latency |

## Decision

Classify and extract send their JSON schema (generated from the same pydantic models that
validate the replies) as Ollama's `format`; summaries stay free text. This is the default,
`--json-mode schema`. `--json-mode prompt` runs the same suite with the prompt alone, and the
comparison of the two modes, with bounded repair, is the experiment in #22. Every suite record
states its `json_mode`.

## Consequences

### Positive

- Scores separate models by what they get right, not by how they format.
- The app can reuse the same schemas.

### Negative and risks

- A schema-constrained decoder can force a wrong label into a valid shape: invalid JSON no
  longer flags a confused model, so field accuracy carries that signal alone.
- Results in the two modes are not comparable; the summary names the mode.

## Revisit when

- A model or runtime without structured outputs joins the comparison.
