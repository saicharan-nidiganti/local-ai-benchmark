"""Ollama server queries, against fakes of the HTTP and client calls."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from local_ai_benchmark import runtime


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", "http://127.0.0.1:11434"),
        ("localhost", "http://localhost:11434"),
        ("0.0.0.0:11434", "http://127.0.0.1:11434"),
        ("http://gpu-box:8080", "http://gpu-box:8080"),
        ("https://example.org", "https://example.org:11434"),
    ],
)
def test_host_follows_ollama_host(monkeypatch, value, expected):
    monkeypatch.setenv("OLLAMA_HOST", value)

    assert runtime.host() == expected


def test_server_version_reads_the_version_endpoint(monkeypatch):
    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"version": "0.40.16"}

    def fake_get(url, timeout):
        seen["url"] = url
        return FakeResponse()

    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.setattr(runtime.httpx, "get", fake_get)

    assert runtime.server_version() == "0.40.16"
    assert seen["url"] == "http://127.0.0.1:11434/api/version"


def fake_show(capabilities=("completion", "thinking")):
    details = SimpleNamespace(
        family="qwen3", parameter_size="4.0B", quantization_level="Q4_K_M", format="gguf"
    )
    return lambda name: SimpleNamespace(details=details, capabilities=list(capabilities))


def test_model_details_combine_show_and_the_digest_from_list(monkeypatch):
    monkeypatch.setattr(runtime.ollama, "show", fake_show())
    monkeypatch.setattr(
        runtime.ollama,
        "list",
        lambda: SimpleNamespace(
            models=[
                SimpleNamespace(model="other:1b", digest="aaa"),
                SimpleNamespace(model="qwen3:4b", digest="359d7dd4bcda"),
            ]
        ),
    )

    details = runtime.model_details("qwen3:4b")

    assert details == runtime.ModelDetails(
        name="qwen3:4b",
        digest="359d7dd4bcda",
        family="qwen3",
        parameter_size="4.0B",
        quantization="Q4_K_M",
        format="gguf",
        capabilities=("completion", "thinking"),
    )


def test_an_untagged_name_matches_its_latest_tag(monkeypatch):
    monkeypatch.setattr(runtime.ollama, "show", fake_show())
    monkeypatch.setattr(
        runtime.ollama,
        "list",
        lambda: SimpleNamespace(models=[SimpleNamespace(model="llama3.2:latest", digest="bbb")]),
    )

    assert runtime.model_details("llama3.2").digest == "bbb"


def test_loaded_model_reports_the_gpu_share(monkeypatch):
    models = [
        SimpleNamespace(
            model="qwen3:4b", size=3_534_917_467, size_vram=2_344_636_907, context_length=4096
        )
    ]
    monkeypatch.setattr(runtime.ollama, "ps", lambda: SimpleNamespace(models=models))

    loaded = runtime.loaded_model("qwen3:4b")

    assert loaded is not None
    assert loaded.context_length == 4096
    assert loaded.gpu_share == pytest.approx(0.663, abs=0.001)
    assert runtime.loaded_model("llama3.2:3b") is None


def test_gpu_share_is_unknown_for_an_empty_size():
    assert runtime.LoadedModel("m", 0, 0, None).gpu_share is None
