# ADR-0003: An append-only JSON Lines run log

- **Status:** Accepted (decided 2026-09-24 with the first architecture; recorded 2026-11-13)
- **Date:** 2026-09-24
- **Deciders:** Project owner
- **Issue:** [#7](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/7)
- **Requirements:** FR-5, NFR-4, FR-9

## Context

Every measured run produces one record of settings, timings, counts and the reply. Results
must be auditable: a published median has to be traceable to the observations behind it, and
a failed run must stay visible. Records also gain fields as the project grows (run ID,
manifest, scores).

## Decision drivers

1. Never lose or rewrite an observation.
2. Add fields without migrations.
3. Readable without special tools, and easy to load for analysis.
4. Keep private prompts and replies out of the repository.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| **JSON Lines, append-only** | One record per line; appending cannot corrupt earlier lines; new fields need no migration; standard-library only | No queries; the whole file is read to summarize |
| CSV | Opens in a spreadsheet | Fixed columns; nested or long text (replies) is awkward |
| SQLite | Queries and indexes | A schema and migrations for a log that only grows |
| Parquet | Compact and fast to analyze | A binary format and an extra dependency for writing |

## Decision

Append one JSON object per run to `data/raw/runs.jsonl`, never editing earlier lines. The raw
log stays git-ignored because it holds full prompts and replies. Curated summaries and
reports derived from it are committed (Phase 1 baseline, Phase 3 report).

## Consequences

### Positive

- Every published number can be recomputed from the raw observations.
- A failed run is a record like any other, so the error rate is honest.

### Negative and risks

- Summaries must read the whole file; acceptable at the expected size (thousands of runs).
- Records written by older versions lack newer fields; readers must treat missing fields as
  absent, not as zero.

## Revisit when

- The log grows past what can be read in a few seconds, or analysis needs queries across
  many run IDs.
