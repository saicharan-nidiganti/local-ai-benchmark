"""Inference client tests against a simulated Ollama stream; no server is needed."""

from __future__ import annotations

from local_ai_benchmark import inference


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

    inference.generate(model="qwen3:4b", prompt="p", temperature=0.2, max_output_tokens=64)

    assert seen["model"] == "qwen3:4b"
    assert seen["prompt"] == "p"
    assert seen["stream"] is True
    assert seen["options"] == {"temperature": 0.2, "num_predict": 64}


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


def test_throughput_is_none_when_runtime_reports_no_generation_time(monkeypatch):
    chunks = [{"response": "x", "done": True, "eval_count": 5, "eval_duration": 0}]
    monkeypatch.setattr(inference.ollama, "generate", fake_stream(chunks))

    result = inference.generate(model="m", prompt="p")

    assert result.error is None
    assert result.tokens_per_sec is None


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
