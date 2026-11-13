"""The offline triage app: one support ticket in; its category, priority, fields and a short
summary out, from the recommended model on this machine (ADR-0012).

It asks the model what the suite measured: the suite's prompts, with the priority rubric for
classification, and the same JSON schemas as Ollama's structured output. It keeps nothing
(no log, no file), and talks to nothing but the local Ollama server.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from .config import GenerationSettings
from .inference import InferenceResult
from .scorers import JSON_SCHEMAS, ClassifyOutput, ExtractOutput, parse_json_object
from .suite import PROMPT_VARIANTS, TASK_KINDS

# The best tradeoff of the three-model comparison (results/2026-11-13-three-model-comparison):
# the quality of qwen3:4b-instruct at 14% more speed and 23% less energy.
RECOMMENDED_MODEL = "phi4-mini"
# The rubric took phi4-mini from 8 to 14 of 15 right priorities on the suite, with the category
# unchanged and no measurable time cost (results/2026-11-13-priority-rubric).
PROMPT_VARIANT = "rubric"
# About 1,000 tokens: with the prompt and the answer, well inside the 4,096-token context.
MAX_TICKET_CHARS = 4000

Generate = Callable[..., InferenceResult]


class TriageError(ValueError):
    """The ticket cannot be triaged as given; the message says why."""


@dataclass(frozen=True)
class Step:
    """One request to the model: which task, how long it took, and whether it failed."""

    task: str
    total_ms: float
    ttft_ms: float | None
    error: str | None


@dataclass(frozen=True)
class Triage:
    model: str
    category: str | None
    priority: str | None
    order_id: str | None
    customer_name: str | None
    product: str | None
    issue: str | None
    summary: str | None
    steps: tuple[Step, ...]

    @property
    def total_ms(self) -> float:
        return sum(step.total_ms for step in self.steps)

    @property
    def errors(self) -> list[str]:
        return [f"{step.task}: {step.error}" for step in self.steps if step.error]

    def record(self) -> dict[str, Any]:
        data = asdict(self)
        data["total_ms"] = round(self.total_ms, 1)
        data["errors"] = self.errors
        return data


def _parsed(
    schema: type[BaseModel], result: InferenceResult
) -> tuple[BaseModel | None, str | None]:
    if result.error:
        return None, result.error
    obj, _ = parse_json_object(result.response)
    if obj is None:
        return None, "the reply was not JSON"
    try:
        return schema.model_validate(obj), None
    except ValidationError as exc:
        return None, f"the reply did not match the schema ({exc.error_count()} problems)"


def triage(
    ticket: str,
    model: str,
    settings: GenerationSettings,
    generate: Generate,
) -> Triage:
    """Classify, extract and summarize one ticket, one request each, in the suite's order."""
    text = ticket.strip()
    if not text:
        raise TriageError("the ticket is empty")
    if len(text) > MAX_TICKET_CHARS:
        raise TriageError(
            f"the ticket is {len(text):,} characters; the limit is {MAX_TICKET_CHARS:,}"
        )
    results = {
        kind: generate(
            model=model,
            prompt=PROMPT_VARIANTS[PROMPT_VARIANT][kind].format(ticket=text),
            settings=settings,
            output_format=JSON_SCHEMAS.get(kind),
        )
        for kind in TASK_KINDS
    }
    labels, labels_error = _parsed(ClassifyOutput, results["classify"])
    fields, fields_error = _parsed(ExtractOutput, results["extract"])
    summary = results["summarize"]
    problems = {"classify": labels_error, "extract": fields_error, "summarize": summary.error}
    steps = tuple(
        Step(kind, results[kind].total_latency_ms, results[kind].ttft_ms, problems[kind])
        for kind in TASK_KINDS
    )
    c = labels if isinstance(labels, ClassifyOutput) else None
    f = fields if isinstance(fields, ExtractOutput) else None
    return Triage(
        model=model,
        category=c.category if c else None,
        priority=c.priority if c else None,
        order_id=f.order_id if f else None,
        customer_name=f.customer_name if f else None,
        product=f.product if f else None,
        issue=f.issue if f else None,
        summary=None if summary.error else (summary.response.strip() or None),
        steps=steps,
    )


def render_text(result: Triage) -> str:
    """The answer as an agent reads it in a terminal."""

    def show(value: str | None) -> str:
        return value if value else "-"

    lines = [
        f"Category:  {show(result.category)}",
        f"Priority:  {show(result.priority)}",
        f"Order:     {show(result.order_id)}",
        f"Customer:  {show(result.customer_name)}",
        f"Product:   {show(result.product)}",
        f"Issue:     {show(result.issue)}",
        f"Summary:   {show(result.summary)}",
        "",
        f"{result.model} on this machine, 3 requests, {result.total_ms / 1000:.1f} s",
    ]
    lines += [f"Problem: {error}" for error in result.errors]
    return "\n".join(lines)
