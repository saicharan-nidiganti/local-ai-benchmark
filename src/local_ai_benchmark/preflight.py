"""Fail fast, before any warm-up run, when the runtime or the model is not there."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import ollama

from . import runtime


class PreflightError(RuntimeError):
    """The benchmark cannot start; the message says what to do about it."""


@dataclass(frozen=True)
class Preflight:
    server_version: str
    model: runtime.ModelDetails


def check(model: str, think: bool = False) -> Preflight:
    try:
        version = runtime.server_version()
    except (httpx.HTTPError, OSError, KeyError, ValueError) as exc:
        raise PreflightError(
            f"Ollama is not reachable at {runtime.host()} ({type(exc).__name__}). "
            "Start the Ollama app, or run `ollama serve`."
        ) from exc
    try:
        details = runtime.model_details(model)
    except ollama.ResponseError as exc:
        if exc.status_code == 404:
            raise PreflightError(
                f"Model '{model}' is not pulled. Run `ollama pull {model}`."
            ) from exc
        raise PreflightError(f"Ollama could not describe '{model}': {exc.error}") from exc
    if think and details.capabilities and "thinking" not in details.capabilities:
        raise PreflightError(
            f"Model '{model}' cannot think (capabilities: {', '.join(details.capabilities)}). "
            "Run it without --think."
        )
    return Preflight(server_version=version, model=details)
