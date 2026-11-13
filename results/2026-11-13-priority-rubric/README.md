# A priority rubric with worked examples, against the default prompt

Every compared model over-escalated ticket priority in the comparison: 17 of the 18 wrong
priorities were one level too high, although the prompt defines each level
([comparison](../2026-11-13-three-model-comparison/)). This measures the `rubric` prompt
variant on the 15 classify tasks, against the default prompt, for the same three models. It
adds three rules ("choose the lowest priority that fits"; "a delay, or anything that still
works another way, is medium"; "a request is low") and five worked examples written for it.

## Findings

1. **The rubric fixes priority for the two stronger models.** qwen3:4b-instruct goes from 9 to
   15 of 15 right priorities, and phi4-mini, the app's model, from 8 to 14. Over-escalations
   drop from 6 and 7 to 0 and 1, and the classify score from 0.77 and 0.73 to 0.97 and 0.93.
   The category stays right on 14 of 15 for both.
2. **llama3.2:3b overcorrects.** Its over-escalations go from 4 to 0, but it now rates 4
   tickets too low: three that lose the customer money or leave a product unusable (T05, T08,
   T11) and one with a workaround (T14). Its priority gains a single ticket (10 to 11 of 15), and
   its classify score rises from 0.73 to 0.80, helped by one more right category.
3. **It costs nothing measurable in time.** The prompt more than doubles, from about 200 to
   about 460 tokens, yet the median task takes the same time (0.60 against 0.61 s for
   qwen3:4b-instruct, 0.69 against 0.56 s for phi4-mini) and the first token arrives as fast.
   The likely reason: the rubric and examples are the same opening for every ticket, so the
   runtime can reuse its work on them between requests. This was not measured separately.
4. **Recommendation: switch the app to the rubric.** For phi4-mini it takes priority from 8
   to 14 of 15 right, keeps the category, and adds no measurable time. The caveat below
   applies, so the app should keep telling users the priority is a suggestion.

| Model | Prompt | Category right | Priority right | Too high | Too low | Classify score | Median task | First token | Prompt tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen3:4b-instruct | default | 14 of 15 | 9 of 15 | 6 | 0 | 0.77 | 0.60 s | 165 ms | 206 |
| qwen3:4b-instruct | rubric | 14 of 15 | 15 of 15 | 0 | 0 | 0.97 | 0.61 s | 172 ms | 462 |
| phi4-mini | default | 14 of 15 | 8 of 15 | 7 | 0 | 0.73 | 0.69 s | 192 ms | 197 |
| phi4-mini | rubric | 14 of 15 | 14 of 15 | 1 | 0 | 0.93 | 0.56 s | 162 ms | 449 |
| llama3.2:3b | default | 12 of 15 | 10 of 15 | 4 | 1 | 0.73 | 0.30 s | 80 ms | 220 |
| llama3.2:3b | rubric | 13 of 15 | 11 of 15 | 0 | 4 | 0.80 | 0.32 s | 79 ms | 475 |

Every wrong priority, ticket by ticket, is in [misses.json](misses.json); exact summaries in
[summaries.json](summaries.json); environments in [manifests.json](manifests.json).

## The caveat: written after seeing the errors

The rubric's rules were drawn from the error pattern on these same 15 tickets: delays and
requests rated too high. The worked examples are new situations, and a test checks that none
shares a five-word phrase with any ticket, but the rules themselves know what went wrong here.
Part of the gain may therefore be fitting to these tickets rather than better judgment in
general. A set of new tickets, labelled before the rubric is run on them, would settle it.

## Setup

| | |
| --- | --- |
| Machine | Reference laptop: Ryzen 9 5900HX, RTX 3050 Laptop GPU 4 GB, 16 GB RAM, Windows 11, plugged in and idle ([environment](../../docs/environment.md)) |
| Models | qwen3:4b-instruct, phi4-mini, llama3.2:3b, Q4_K_M, Ollama 0.40.16 |
| Tasks | The 15 classify tasks of `support_triage_v1`, JSON schema mode, temperature 0, seed 42, 4096-token context; one warm-up; each model unloaded first, then the default and the rubric prompt one after the other |
| Harness | Commit `e69de9b`, clean tree, `--require-ac`; 2026-11-13, 14:09 to 14:10 UTC |

## Reproduce

```bash
for model in qwen3-4b-instruct phi4-mini llama3.2-3b; do
  for variant in default rubric; do
    uv run local-ai-benchmark suite --model "$model" --tasks classify \
      --prompt-variant "$variant" --require-ac
  done
done
```
