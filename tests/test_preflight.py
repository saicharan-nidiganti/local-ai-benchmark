"""Preflight: a missing server or model fails before any warm-up run."""

from __future__ import annotations

import httpx
import ollama
import pytest

from local_ai_benchmark import preflight, runtime

DETAILS = runtime.ModelDetails(
    name="qwen3:4b",
    digest="359d7dd4bcda",
    family="qwen3",
    parameter_size="4.0B",
    quantization="Q4_K_M",
    format="gguf",
    capabilities=("completion", "thinking"),
)


def test_passes_when_the_server_answers_and_the_model_is_pulled(monkeypatch):
    monkeypatch.setattr(preflight.runtime, "server_version", lambda: "0.40.16")
    monkeypatch.setattr(preflight.runtime, "model_details", lambda name: DETAILS)

    result = preflight.check("qwen3:4b")

    assert result.server_version == "0.40.16"
    assert result.model.quantization == "Q4_K_M"


def test_a_stopped_server_fails_with_what_to_do(monkeypatch):
    def refuse():
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(preflight.runtime, "server_version", refuse)

    with pytest.raises(preflight.PreflightError, match=r"not reachable.*ollama serve"):
        preflight.check("qwen3:4b")


def test_a_missing_model_fails_with_the_pull_command(monkeypatch):
    def missing(name):
        raise ollama.ResponseError(f"model '{name}' not found", 404)

    monkeypatch.setattr(preflight.runtime, "server_version", lambda: "0.40.16")
    monkeypatch.setattr(preflight.runtime, "model_details", missing)

    with pytest.raises(preflight.PreflightError, match=r"ollama pull qwen3:8b"):
        preflight.check("qwen3:8b")


def test_another_runtime_error_is_reported(monkeypatch):
    def broken(name):
        raise ollama.ResponseError("internal error", 500)

    monkeypatch.setattr(preflight.runtime, "server_version", lambda: "0.40.16")
    monkeypatch.setattr(preflight.runtime, "model_details", broken)

    with pytest.raises(preflight.PreflightError, match="could not describe"):
        preflight.check("qwen3:4b")


def test_thinking_on_a_model_that_cannot_think_fails(monkeypatch):
    plain = runtime.ModelDetails(
        name="llama3.2:3b",
        digest=None,
        family="llama",
        parameter_size="3.2B",
        quantization="Q4_K_M",
        format="gguf",
        capabilities=("completion", "tools"),
    )
    monkeypatch.setattr(preflight.runtime, "server_version", lambda: "0.40.16")
    monkeypatch.setattr(preflight.runtime, "model_details", lambda name: plain)

    with pytest.raises(preflight.PreflightError, match="cannot think"):
        preflight.check("llama3.2:3b", think=True)
    assert preflight.check("llama3.2:3b").model.family == "llama"
