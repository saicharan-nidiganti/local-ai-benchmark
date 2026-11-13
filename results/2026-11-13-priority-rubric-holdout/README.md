# The priority rubric on held-out tickets

The priority rubric was written after seeing the errors on `support_triage_v1`, so its gain
there ([results](../2026-11-13-priority-rubric/)) could be fitting. This checks it on
`support_triage_holdout_v1`: 15 new fictional tickets, labelled by the same rules as v1 and
merged to `main` before any model was run on them, at 14:57 UTC on 2026-11-13. The first run
here started at 14:58 UTC.

## Findings

1. **The gain holds on new tickets.** With the rubric, every model gets 13 of 15 priorities
   right, from 10, 6 and 10 with the default prompt. Over-escalations fall from 15 in all to 2.
   The classify score rises from 0.73, 0.67 and 0.70 to 0.83, 0.83 and 0.80.
2. **Part of the gain on v1 was fitting, for one model.** qwen3:4b-instruct gained 6
   priorities on v1 (9 to 15) but 3 here (10 to 13). phi4-mini, the app's model, gained 6 on v1
   and 7 here; llama3.2:3b gained 1 on v1 and 3 here, without v1's overcorrection.
3. **"Choose the lowest that fits" pulls down a stopped business.** H10, a restaurant that
   cannot take a single order before lunch, is urgent; with the rubric every model rates it
   high. qwen3:4b-instruct had it right with the default prompt.
4. **It costs phi4-mini two categories.** With the rubric, phi4-mini files two billing
   questions, a plan's features (H01) and a receipt in English (H03), as account: 12 of 15
   categories right, from 14. The other models' categories are unchanged.
5. **Verdict: the app keeps the rubric.** For phi4-mini it takes priority from 6 to 13 of 15
   right on new tickets and the classify score from 0.67 to 0.83, at the price of two category
   labels. A rule that a stopped business is urgent whatever else applies is the next change to
   try, measured the same way.

| Model | Prompt | Priority right | Too high | Too low | Category right | Classify score | Priority right on v1 (#74) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen3:4b-instruct | default | 10 of 15 | 5 | 0 | 12 of 15 | 0.73 | 9 of 15 |
| qwen3:4b-instruct | rubric | 13 of 15 | 1 | 1 | 12 of 15 | 0.83 | 15 of 15 |
| phi4-mini | default | 6 of 15 | 7 | 2 | 14 of 15 | 0.67 | 8 of 15 |
| phi4-mini | rubric | 13 of 15 | 1 | 1 | 12 of 15 | 0.83 | 14 of 15 |
| llama3.2:3b | default | 10 of 15 | 3 | 2 | 11 of 15 | 0.70 | 10 of 15 |
| llama3.2:3b | rubric | 13 of 15 | 0 | 2 | 11 of 15 | 0.80 | 11 of 15 |

Every wrong label, ticket by ticket, is in [misses.json](misses.json). Two category errors are
shared by most runs: H04, money back for an overcharge, filed as billing where the definition
says refund; and H01 or H03, billing questions filed as account. Median task times are the same
with either prompt (0.60 and 0.61 s for qwen3:4b-instruct, 0.69 and 0.55 s for phi4-mini, 0.30
and 0.32 s for llama3.2:3b). Exact summaries: [summaries.json](summaries.json); environments:
[manifests.json](manifests.json).

## Limits

- The same author wrote the rubric and the held-out labels. Merging the labels first stops them
  from following the answers, but not from sharing the author's reading of the rules.
- 15 tickets and one run per task: a difference of one or two labels is within noise.

## Setup

| | |
| --- | --- |
| Machine | Reference laptop: Ryzen 9 5900HX, RTX 3050 Laptop GPU 4 GB, 16 GB RAM, Windows 11, plugged in and idle ([environment](../../docs/environment.md)) |
| Models | qwen3:4b-instruct, phi4-mini, llama3.2:3b, Q4_K_M, Ollama 0.40.16 |
| Tasks | The 15 classify tasks of `support_triage_holdout_v1`, JSON schema mode, temperature 0, seed 42, 4096-token context; one warm-up; each model unloaded first, then the default and the rubric prompt one after the other |
| Harness | Commit `1a49a21` (the merge that added the held-out suite), clean tree, `--require-ac`; 2026-11-13, 14:58 to 15:00 UTC |

## Reproduce

```bash
for model in qwen3-4b-instruct phi4-mini llama3.2-3b; do
  for variant in default rubric; do
    uv run local-ai-benchmark suite --model "$model" --tasks classify \
      --suite benchmarks/support_triage_holdout_v1.jsonl --prompt-variant "$variant" --require-ac
  done
done
```
