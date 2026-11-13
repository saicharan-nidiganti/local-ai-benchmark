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


def check_host(allow_remote: bool = False) -> None:
    """Refuse an Ollama server on another machine: every prompt and reply would leave this
    one. `--allow-remote` is the explicit opt-out."""
    host = runtime.host()
    if allow_remote or runtime.is_local(host):
        return
    raise PreflightError(
        f"OLLAMA_HOST points at {host}, which is not this machine: prompts and replies would "
        "leave it. Unset OLLAMA_HOST to use the local server, or pass --allow-remote if "
        "sending them there is intended."
    )


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
