"""Stream one generation from Ollama and time it."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

import ollama

from .config import GenerationSettings

# A run whose reply has no visible text is a failure, even when the runtime reports tokens:
# its throughput describes output nobody can use, so it must not enter the medians.
EMPTY_RESPONSE = "empty_response: the model returned no visible text"


@dataclass
class InferenceResult:
    model: str
    prompt: str
    response: str
    ttft_ms: float | None
    total_latency_ms: float
    output_tokens: int | None
    generation_ms: float | None
    tokens_per_sec: float | None
    load_duration_ms: float | None
    prompt_tokens: int | None
    prompt_eval_duration_ms: float | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate(
    model: str,
    prompt: str,
    settings: GenerationSettings | None = None,
) -> InferenceResult:
    settings = settings or GenerationSettings()
    start = time.perf_counter()
    first_token_at: float | None = None
    chunks: list[str] = []
    final: Any = None

    try:
        stream = ollama.generate(
            model=model,
            prompt=prompt,
            stream=True,
            # Off unless asked for: thinking models such as qwen3 otherwise spend the output
            # budget on hidden reasoning, and no visible first token is ever seen.
            think=settings.think,
            keep_alive=settings.keep_alive,
            options=settings.options(),
        )

        for chunk in stream:
            now = time.perf_counter()
            text = chunk.get("response", "")
            if text and first_token_at is None:
                first_token_at = now
            if text:
                chunks.append(text)
            final = chunk

        end = time.perf_counter()
        final = final or {}

        response = "".join(chunks)
        total_ms = (end - start) * 1000

        eval_count = final.get("eval_count")
        eval_duration_ns = final.get("eval_duration")
        load_duration_ns = final.get("load_duration")
        prompt_eval_count = final.get("prompt_eval_count")
        prompt_eval_duration_ns = final.get("prompt_eval_duration")

        generation_ms = eval_duration_ns / 1_000_000 if eval_duration_ns is not None else None
        tokens_per_sec = (
            eval_count / (eval_duration_ns / 1_000_000_000)
            if eval_count is not None and eval_duration_ns
            else None
        )

        return InferenceResult(
            model=model,
            prompt=prompt,
            response=response,
            ttft_ms=((first_token_at - start) * 1000 if first_token_at else None),
            total_latency_ms=total_ms,
            output_tokens=eval_count,
            generation_ms=generation_ms,
            tokens_per_sec=tokens_per_sec,
            load_duration_ms=(
                load_duration_ns / 1_000_000 if load_duration_ns is not None else None
            ),
            prompt_tokens=prompt_eval_count,
            prompt_eval_duration_ms=(
                prompt_eval_duration_ns / 1_000_000 if prompt_eval_duration_ns is not None else None
            ),
            error=None if response.strip() else EMPTY_RESPONSE,
        )

    except Exception as exc:
        end = time.perf_counter()
        return InferenceResult(
            model=model,
            prompt=prompt,
            response="",
            ttft_ms=((first_token_at - start) * 1000 if first_token_at else None),
            total_latency_ms=(end - start) * 1000,
            output_tokens=None,
            generation_ms=None,
            tokens_per_sec=None,
            load_duration_ms=None,
            prompt_tokens=None,
            prompt_eval_duration_ms=None,
            error=f"{type(exc).__name__}: {exc}",
        )
