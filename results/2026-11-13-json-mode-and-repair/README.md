# JSON from the schema or the prompt alone, with bounded repair

The question [ADR-0009](../../docs/decisions/0009-structured-output-for-json-tasks.md) left open:
when the JSON tasks (classify and extract) ask for JSON in the prompt alone instead of sending
the schema to Ollama, how often does the reply fail, and how much does a bounded repair rescue?
Every run used `suite --tasks classify,extract --repair 2`: a reply that fails its schema is
asked again, at most twice, with the rejected reply and what was wrong.

## Findings

1. **Instruction-following models need neither the schema nor repair.** qwen3:4b-instruct,
   phi4-mini and llama3.2:3b returned schema-valid JSON on the first try for all 30 tasks in
   both modes; repair never ran. Quality is the same in both modes to within 0.01: 29 of 30
   scores identical for phi4-mini and all 30 for the other two.
2. **The schema still pays for phi4-mini.** Without it, phi4-mini wraps its JSON in a markdown
   code fence in 27 of 30 replies. The scorer recovers JSON from a fence, so the score holds,
   but each reply is 5 tokens longer (31 against 26) and the median task takes 22% longer
   (1.26 s against 1.03 s). An app that parsed strictly would reject 27 of 30 replies.
3. **Repair cannot fix a model that ignores the format.** The qwen3:4b thinking build failed
   every task on the first try and on both repairs: 60 repairs, 10.1 s each, 10 minutes in all,
   rescued none. Every reply narrates its reasoning ("We are given a ticket...") until it runs
   out of its 256 tokens. With the schema sent to the runtime the same model scores 0.77 on
   classification and 0.95 on extraction ([ADR-0009](../../docs/decisions/0009-structured-output-for-json-tasks.md)).
4. **So the default stays.** Schema mode costs nothing in quality, is as fast or faster, and
   guarantees strict JSON even from a model that would not comply. Repair is kept as an option
   (`--repair`), off by default: on this suite it added nothing for the models that follow
   instructions, and only time for the one that does not.

| Model | JSON mode | Valid JSON, first try | Schema-valid, first try | Repaired | Repairs | Schema-valid, final | Quality, first try | Quality, final | Median task | Time in repairs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen3:4b-instruct | schema | 100% | 100% | 0% | 0 | 100% | 0.88 | 0.88 | 1.1 s | 0.0 s |
| qwen3:4b-instruct | prompt | 100% | 100% | 0% | 0 | 100% | 0.88 | 0.88 | 1.1 s | 0.0 s |
| phi4-mini | schema | 100% | 100% | 0% | 0 | 100% | 0.84 | 0.84 | 1.0 s | 0.0 s |
| phi4-mini | prompt | 100% | 100% | 0% | 0 | 100% | 0.85 | 0.85 | 1.3 s | 0.0 s |
| llama3.2:3b | schema | 100% | 100% | 0% | 0 | 100% | 0.86 | 0.86 | 0.7 s | 0.0 s |
| llama3.2:3b | prompt | 100% | 100% | 0% | 0 | 100% | 0.86 | 0.86 | 0.7 s | 0.0 s |
| qwen3:4b (thinking build) | prompt | 0% | 0% | 100% | 60 | 0% | 0.00 | 0.00 | 9.8 s | 606.5 s |

Quality here is the mean over the 30 JSON tasks (classify and extract), not the suite's
overall score. "Valid JSON" counts an object recovered from a code fence or prose; "strict"
JSON, the whole reply being one object, was 30 of 30 in prompt mode for qwen3:4b-instruct and
llama3.2:3b, and 3 of 30 for phi4-mini. Exact values: [summaries.json](summaries.json);
environments: [manifests.json](manifests.json).

## Setup

| | |
| --- | --- |
| Machine | Reference laptop: Ryzen 9 5900HX, RTX 3050 Laptop GPU 4 GB, 16 GB RAM, Windows 11, plugged in and idle ([environment](../../docs/environment.md)) |
| Models | qwen3:4b-instruct, phi4-mini, llama3.2:3b and the qwen3:4b thinking build, all Q4_K_M, Ollama 0.40.16 |
| Tasks | The 30 classify and extract tasks of `support_triage_v1`, temperature 0, seed 42, 4096-token context, at most 256 output tokens, thinking off; one warm-up, each model unloaded first |
| Repair | `--repair 2`: up to two re-asks per task, each with the original task, the rejected reply (cut to 600 characters) and what was wrong |
| Harness | Commit `53b9999`, clean tree, `--require-ac`; 2026-11-13, 13:27 to 13:46 UTC |

## Limits

- One run per task, 15 fictional tickets; the quality differences between modes are a single
  task.
- Repair was never triggered for the three instruct models, so this run cannot say how well
  repair works when a model sometimes slips; it says only that these models did not slip.

## Reproduce

```bash
for model in qwen3-4b-instruct phi4-mini llama3.2-3b; do
  for mode in schema prompt; do
    uv run local-ai-benchmark suite --model "$model" --tasks classify,extract \
      --json-mode "$mode" --repair 2 --require-ac
  done
done
uv run local-ai-benchmark suite --model qwen3-4b --tasks classify,extract \
  --json-mode prompt --repair 2 --require-ac
```
