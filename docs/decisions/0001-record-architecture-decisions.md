# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#7](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/7)
- **Requirements:** NFR-5

## Context

The project's design choices (the runtime, how timings are taken, how data is stored) shape
every result it publishes. Until now they lived in the code and in a planning document
outside the repository, so a reader could see what was done but not why, or what else was
considered.

## Decision drivers

1. A reviewer should be able to check the reasoning behind each published number.
2. Later changes should be able to tell a deliberate choice from an accident.
3. The record should cost little to keep.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| No written record | No effort | Reasoning is lost; choices get re-argued |
| A design document kept up to date | One place to read | Rewritten over time, so past reasoning disappears |
| **Architecture decision records** | One short, dated file per decision; history kept | Several files to read for the full picture |

## Decision

Keep ADRs in `docs/decisions/`, numbered and written from [template.md](template.md). The
current design is summarized in [architecture.md](../architecture.md), which links to the
ADRs behind it. Decisions made before this ADR are recorded retroactively (0002 to 0004).

## Consequences

### Positive

- Each published number can be traced to the decisions that produced it.
- A changed decision leaves its predecessor in place, so the history stays readable.

### Negative and risks

- A pull request that makes a consequential choice must also write an ADR; the pull request
  template asks for it.

## Revisit when

- ADRs stop being read, or a decision is made without one.
