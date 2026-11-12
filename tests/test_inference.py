"""Inference client tests against a simulated Ollama stream; no server is needed."""

from __future__ import annotations

from local_ai_benchmark import inference
from local_ai_benchmark.config import GenerationSettings


def fake_stream(chunks):
    def _generate(**_kwargs):
        yield from chunks

    return _generate


FINAL_CHUNK = {
    "response": "",
    "done": True,
    "eval_count": 50,
    "eval_duration": 2_000_000_000,
    "load_duration": 300_000_000,
    "prompt_eval_count": 12,
    "prompt_eval_duration": 40_000_000,
}


def test_collects_streamed_text_and_runtime_metrics(monkeypatch):
    chunks = [
        {"response": "Hello", "done": False},
        {"response": " world", "done": False},
        FINAL_CHUNK,
    ]
    monkeypatch.setattr(inference.ollama, "generate", fake_stream(chunks))

    result = inference.generate(model="m", prompt="p")

    assert result.error is None
    assert result.response == "Hello world"
    assert result.output_tokens == 50
    assert result.generation_ms == 2000
    assert result.tokens_per_sec == 25
    assert result.load_duration_ms == 300
    assert result.prompt_tokens == 12
    assert result.prompt_eval_duration_ms == 40
    assert result.ttft_ms is not None
    assert 0 <= result.ttft_ms <= result.total_latency_ms


def test_passes_model_and_sampling_settings_to_ollama(monkeypatch):
    seen = {}

    def _generate(**kwargs):
        seen.update(kwargs)
        yield {**FINAL_CHUNK, "response": "ok"}

    monkeypatch.setattr(inference.ollama, "generate", _generate)

    settings = GenerationSettings(temperature=0.2, max_output_tokens=64, seed=7, num_ctx=2048)
    inference.generate(model="qwen3:4b", prompt="p", settings=settings)

    assert seen["model"] == "qwen3:4b"
    assert seen["prompt"] == "p"
    assert seen["stream"] is True
    assert seen["keep_alive"] == "5m"
    assert seen["options"] == {"temperature": 0.2, "num_predict": 64, "seed": 7, "num_ctx": 2048}


def test_pins_seed_and_context_length_by_default(monkeypatch):
    seen = {}

    def _generate(**kwargs):
        seen.update(kwargs)
        yield {**FINAL_CHUNK, "response": "ok"}

    monkeypatch.setattr(inference.ollama, "generate", _generate)

    inference.generate(model="m", prompt="p")

    assert seen["options"]["seed"] == 42
    assert seen["options"]["num_ctx"] == 4096


def test_disables_thinking_so_the_reply_and_first_token_are_visible(monkeypatch):
    seen = {}

    def _generate(**kwargs):
        seen.update(kwargs)
        yield {**FINAL_CHUNK, "response": "ok"}

    monkeypatch.setattr(inference.ollama, "generate", _generate)

    result = inference.generate(model="qwen3:4b", prompt="p")

    assert seen["think"] is False
    assert result.response == "ok"
    assert result.ttft_ms is not None


def test_thinking_is_sent_when_switched_on(monkeypatch):
    seen = {}

    def _generate(**kwargs):
        seen.update(kwargs)
        yield {**FINAL_CHUNK, "response": "ok"}

    monkeypatch.setattr(inference.ollama, "generate", _generate)

    inference.generate(model="qwen3:4b", prompt="p", settings=GenerationSettings(think=True))

    assert seen["think"] is True


def test_throughput_is_none_when_runtime_reports_no_generation_time(monkeypatch):
    chunks = [{"response": "x", "done": True, "eval_count": 5, "eval_duration": 0}]
    monkeypatch.setattr(inference.ollama, "generate", fake_stream(chunks))

    result = inference.generate(model="m", prompt="p")

    assert result.error is None
    assert result.tokens_per_sec is None


def test_counts_an_empty_reply_as_a_failed_run(monkeypatch):
    # The 2026-09-25 case: tokens were generated, but none of them were visible text.
    chunks = [{"response": "", "done": False}, FINAL_CHUNK]
    monkeypatch.setattr(inference.ollama, "generate", fake_stream(chunks))

    result = inference.generate(model="qwen3:4b", prompt="p")

    assert result.error == inference.EMPTY_RESPONSE
    assert result.response == ""
    assert result.ttft_ms is None
    assert result.output_tokens == 50  # the runtime's counts are kept for diagnosis


def test_a_whitespace_only_reply_is_also_empty(monkeypatch):
    chunks = [{"response": "\n\n  ", "done": False}, FINAL_CHUNK]
    monkeypatch.setattr(inference.ollama, "generate", fake_stream(chunks))

    result = inference.generate(model="m", prompt="p")

    assert result.error == inference.EMPTY_RESPONSE


def test_records_connection_failure_instead_of_raising(monkeypatch):
    def _generate(**_kwargs):
        raise ConnectionError("Ollama is not running")

    monkeypatch.setattr(inference.ollama, "generate", _generate)

    result = inference.generate(model="m", prompt="p")

    assert result.error == "ConnectionError: Ollama is not running"
    assert result.response == ""
    assert result.ttft_ms is None
    assert result.tokens_per_sec is None


def test_keeps_ttft_when_stream_fails_midway(monkeypatch):
    def _generate(**_kwargs):
        yield {"response": "partial", "done": False}
        raise RuntimeError("stream interrupted")

    monkeypatch.setattr(inference.ollama, "generate", _generate)

    result = inference.generate(model="m", prompt="p")

    assert result.error == "RuntimeError: stream interrupted"
    assert result.ttft_ms is not None
    assert result.output_tokens is None


def test_prefill_speed_is_prompt_tokens_over_prompt_evaluation_time(monkeypatch):
    monkeypatch.setattr(
        inference.ollama, "generate", fake_stream([{**FINAL_CHUNK, "response": "ok"}])
    )

    result = inference.generate(model="m", prompt="p")

    assert result.prefill_tokens_per_sec == 300  # 12 tokens in 40 ms


def test_prefill_speed_is_none_without_a_prompt_evaluation_time(monkeypatch):
    chunk = {**FINAL_CHUNK, "response": "ok", "prompt_eval_duration": 0}
    monkeypatch.setattr(inference.ollama, "generate", fake_stream([chunk]))

    assert inference.generate(model="m", prompt="p").prefill_tokens_per_sec is None


def test_an_output_schema_is_passed_to_ollama(monkeypatch):
    seen = {}

    def _generate(**kwargs):
        seen.update(kwargs)
        yield {**FINAL_CHUNK, "response": "{}"}

    monkeypatch.setattr(inference.ollama, "generate", _generate)
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}

    inference.generate(model="m", prompt="p", output_format=schema)
    assert seen["format"] == schema

    inference.generate(model="m", prompt="p")
    assert seen["format"] is None
