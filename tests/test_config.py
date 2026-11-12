"""Settings files, the model registry and command-line overrides."""

from __future__ import annotations

from pathlib import Path

import pytest

from local_ai_benchmark.config import (
    BenchmarkSettings,
    ConfigError,
    GenerationSettings,
    ModelEntry,
    load_models,
    load_settings,
    resolve_model,
    with_overrides,
)

REPO = Path(__file__).resolve().parents[1]


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "settings.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_no_file_gives_the_documented_defaults():
    settings = load_settings(None)

    assert settings == BenchmarkSettings()
    assert settings.generation.options() == {
        "temperature": 0.0,
        "num_predict": 256,
        "seed": 42,
        "num_ctx": 4096,
    }


def test_the_repository_settings_file_is_valid():
    settings = load_settings(REPO / "configs" / "benchmark.yaml")

    assert settings.repeats == 5
    assert settings.warmup_runs == 1
    assert settings.generation.seed == 42
    assert settings.generation.num_ctx == 4096


def test_reads_every_setting_and_accepts_an_integer_temperature(tmp_path):
    path = write(
        tmp_path,
        "benchmark:\n  repeats: 3\n  warmup_runs: 2\n  temperature: 1\n"
        "  max_output_tokens: 64\n  seed: 7\n  num_ctx: 2048\n  keep_alive: 1m\n",
    )

    settings = load_settings(path)

    assert settings.repeats == 3
    assert settings.warmup_runs == 2
    assert settings.generation == GenerationSettings(
        temperature=1.0, max_output_tokens=64, seed=7, num_ctx=2048, keep_alive="1m"
    )
    assert isinstance(settings.generation.temperature, float)


def test_rejects_an_unknown_setting(tmp_path):
    path = write(tmp_path, "benchmark:\n  repeets: 3\n")

    with pytest.raises(ConfigError, match=r"unknown setting.*repeets"):
        load_settings(path)


@pytest.mark.parametrize(
    "line", ["repeats: five", "temperature: true", "seed: 1.5", "num_ctx: -1", "keep_alive: 5"]
)
def test_rejects_a_mistyped_or_negative_setting(tmp_path, line):
    with pytest.raises(ConfigError):
        load_settings(write(tmp_path, f"benchmark:\n  {line}\n"))


def test_reports_a_missing_or_malformed_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "missing.yaml")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load_settings(write(tmp_path, "benchmark: [unclosed\n"))
    with pytest.raises(ConfigError, match="mapping"):
        load_settings(write(tmp_path, "- a list\n"))


def test_an_empty_file_gives_the_defaults(tmp_path):
    assert load_settings(write(tmp_path, "")) == BenchmarkSettings()


def test_overrides_apply_only_to_flags_that_were_given():
    base = BenchmarkSettings(repeats=3, generation=GenerationSettings(seed=7))

    result = with_overrides(base, seed=9, temperature=None, repeats=None, warmup_runs=4)

    assert result.generation.seed == 9
    assert result.generation.temperature == 0.0
    assert result.repeats == 3
    assert result.warmup_runs == 4


def test_the_record_lists_every_generation_setting():
    assert GenerationSettings().record() == {
        "temperature": 0.0,
        "max_output_tokens": 256,
        "seed": 42,
        "num_ctx": 4096,
        "keep_alive": "5m",
    }


def test_loads_the_model_registry_and_resolves_ids_and_tags():
    models = load_models(REPO / "configs" / "models.yaml")

    assert resolve_model("qwen3-4b", models).name == "qwen3:4b"
    assert resolve_model("qwen3:4b", models).id == "qwen3-4b"
    assert resolve_model("llama3.2:3b", models) == ModelEntry(id="llama3.2:3b", name="llama3.2:3b")
    assert load_models(None) == []


def test_rejects_a_model_without_an_id_or_a_name(tmp_path):
    path = tmp_path / "models.yaml"
    path.write_text("models:\n  - name: qwen3:4b\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="'id' and a 'name'"):
        load_models(path)
