"""Benchmark settings and the model registry: YAML files with command-line overrides.

Precedence, lowest to highest: built-in defaults, `configs/benchmark.yaml`, then flags given on
the command line. Every run records the values it actually used.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """A configuration file is missing, malformed, or holds an unknown or mistyped setting."""


@dataclass(frozen=True)
class GenerationSettings:
    """What is sent with every request. Pinned so that runs are comparable."""

    temperature: float = 0.0
    max_output_tokens: int = 256
    seed: int = 42
    num_ctx: int = 4096
    keep_alive: str = "5m"

    def options(self) -> dict[str, Any]:
        """The `options` mapping of an Ollama request."""
        return {
            "temperature": self.temperature,
            "num_predict": self.max_output_tokens,
            "seed": self.seed,
            "num_ctx": self.num_ctx,
        }

    def record(self) -> dict[str, Any]:
        """The settings as they are written into every run record."""
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass(frozen=True)
class BenchmarkSettings:
    repeats: int = 5
    warmup_runs: int = 1
    generation: GenerationSettings = field(default_factory=GenerationSettings)


@dataclass(frozen=True)
class ModelEntry:
    """A model the project knows by a short id; `name` is the Ollama tag."""

    id: str
    name: str
    role: str = ""
    quantization: str = ""


_GENERATION_TYPES: dict[str, type] = {
    "temperature": float,
    "max_output_tokens": int,
    "seed": int,
    "num_ctx": int,
    "keep_alive": str,
}
_RUN_TYPES: dict[str, type] = {"repeats": int, "warmup_runs": int}


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"{path}: file not found") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: not valid YAML ({exc})") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a mapping at the top level")
    return data


def _checked(path: Path, key: str, value: Any, expected: type) -> Any:
    # bool is a subclass of int; a YAML `true` is never a valid count or temperature.
    if isinstance(value, bool) or not isinstance(value, expected):
        if expected is float and isinstance(value, int) and not isinstance(value, bool):
            return float(value)
        raise ConfigError(
            f"{path}: '{key}' must be {expected.__name__}, got {type(value).__name__}"
        )
    if isinstance(value, int) and value < 0:
        raise ConfigError(f"{path}: '{key}' must not be negative")
    return value


def load_settings(path: Path | None) -> BenchmarkSettings:
    """Read the `benchmark:` section of a settings file; None gives the defaults."""
    if path is None:
        return BenchmarkSettings()
    section = _read_yaml(path).get("benchmark") or {}
    if not isinstance(section, dict):
        raise ConfigError(f"{path}: 'benchmark' must be a mapping")
    known = _GENERATION_TYPES | _RUN_TYPES
    unknown = sorted(set(section) - set(known))
    if unknown:
        raise ConfigError(f"{path}: unknown setting(s): {', '.join(unknown)}")
    values = {key: _checked(path, key, section[key], known[key]) for key in section}
    generation = GenerationSettings(**{k: v for k, v in values.items() if k in _GENERATION_TYPES})
    runs = {k: v for k, v in values.items() if k in _RUN_TYPES}
    return BenchmarkSettings(generation=generation, **runs)


def with_overrides(settings: BenchmarkSettings, **overrides: Any) -> BenchmarkSettings:
    """Apply command-line values; a None value means the flag was not given."""
    given = {key: value for key, value in overrides.items() if value is not None}
    generation = replace(
        settings.generation, **{k: v for k, v in given.items() if k in _GENERATION_TYPES}
    )
    runs = {k: v for k, v in given.items() if k in _RUN_TYPES}
    return replace(settings, generation=generation, **runs)


def load_models(path: Path | None) -> list[ModelEntry]:
    """Read the `models:` list of a registry file; None gives an empty registry."""
    if path is None:
        return []
    entries = _read_yaml(path).get("models") or []
    if not isinstance(entries, list):
        raise ConfigError(f"{path}: 'models' must be a list")
    models = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or not entry.get("id") or not entry.get("name"):
            raise ConfigError(f"{path}: model {i + 1} needs at least an 'id' and a 'name'")
        models.append(
            ModelEntry(
                id=str(entry["id"]),
                name=str(entry["name"]),
                role=str(entry.get("role", "")),
                quantization=str(entry.get("quantization", "")),
            )
        )
    return models


def resolve_model(requested: str, models: list[ModelEntry]) -> ModelEntry:
    """Match a registry id or an Ollama tag; an unknown tag is used as given."""
    for model in models:
        if requested in (model.id, model.name):
            return model
    return ModelEntry(id=requested, name=requested)


def default_file(root: Path, name: str) -> Path | None:
    candidate = root / "configs" / name
    return candidate if candidate.is_file() else None
