# Offline Local AI Assistant + Benchmarking Lab

A reproducible local AI engineering lab based on the project blueprint.

## Phase 1 status

This starter implements the first vertical slice:

- Local inference through Ollama
- CLI prompt execution
- TTFT measurement
- total latency measurement
- generated-token count
- generation throughput
- JSONL run logging
- repeatable benchmark execution
- model/config metadata capture

The project deliberately does **not** implement structured-output validation, retries, or multi-model comparison yet. Those are later phases.

## Architecture

User -> CLI -> Prompt -> Ollama Runtime -> Metrics -> JSONL

## Prerequisites

1. Install Ollama and make sure it is running.
2. Pull a small instruct model, for example:

```powershell
ollama pull qwen3:4b
```

3. Verify:

```powershell
ollama list
ollama run qwen3:4b
```

4. Install Python 3.11+.

## Setup on Windows PowerShell

```powershell
cd local-ai-benchmark

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e .
```

## Run one prompt

```powershell
python -m app.cli ask --model qwen3:4b --prompt "Explain TCP vs UDP in 5 bullet points."
```

## Run the same prompt five times

```powershell
python -m app.cli benchmark `
  --model qwen3:4b `
  --prompt "Explain TCP vs UDP in 5 bullet points." `
  --repeats 5 `
  --temperature 0
```

Results are appended to:

`data/raw/runs.jsonl`

## Reproducibility

Keep these values fixed when collecting baseline measurements:

- physical machine
- model name/version
- quantization
- Ollama/runtime version
- prompt
- context settings
- maximum output tokens
- temperature/sampling parameters
- warm-up procedure
- repetition count

Do not compare models yet. First establish a clean baseline with one model.

## Phase 1 completion criteria

- [ ] One local model runs without a hosted model API.
- [ ] One prompt produces a response.
- [ ] TTFT is recorded.
- [ ] Total latency is recorded.
- [ ] Output token count is recorded.
- [ ] Tokens/sec is recorded.
- [ ] Five repeated runs are stored as JSONL.
- [ ] Raw results can be inspected without manually copying numbers.

## Next phase

After Phase 1 is verified, add:

1. Pydantic structured output
2. JSON validation
3. bounded retry/repair
4. reliability tests
5. versioned 30-50 prompt benchmark suite
6. three-model controlled comparison
