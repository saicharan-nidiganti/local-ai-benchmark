"""Automatic scoring of the three task kinds; every score lies between 0 and 1 (ADR-0008)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from .suite import SUMMARY_MAX_WORDS, Category, Expected, Priority, Task


class ClassifyOutput(BaseModel):
    """The JSON a classify answer must hold; extra keys are tolerated."""

    model_config = ConfigDict(extra="ignore")

    category: Category
    priority: Priority


class ExtractOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_id: str | None
    customer_name: str
    product: str | None
    issue: str


@dataclass(frozen=True)
class Score:
    score: float
    json_strict: bool | None = None  # the whole reply is one JSON object
    json_valid: bool | None = None  # a JSON object could be recovered from the reply
    schema_valid: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def record(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "json_strict": self.json_strict,
            "json_valid": self.json_valid,
            "schema_valid": self.schema_valid,
            "score_details": self.details,
        }


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_NULL_WORDS = ("", "null", "none", "n/a", "na", "not mentioned", "not specified", "unknown")


def parse_json_object(text: str) -> tuple[dict[str, Any] | None, bool]:
    """(object, strict): strict when the whole reply is the object; otherwise the object is
    recovered from a code fence or from the first {...} span."""
    stripped = text.strip()
    for candidate, strict in ((stripped, True), *_recoveries(stripped)):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value, strict
    return None, False


def _recoveries(text: str) -> list[tuple[str, bool]]:
    found = []
    fence = _FENCE.match(text)
    if fence:
        found.append((fence.group(1), False))
    span = _OBJECT.search(text)
    if span:
        found.append((span.group(0), False))
    return found


def normalize(text: str) -> str:
    """Case, punctuation and spacing are ignored; hyphens inside words are kept."""
    cleaned = re.sub(r"[^\w\s-]", " ", text.casefold())
    return " ".join(cleaned.split())


# Compared after normalizing, so "N/A" and "n/a" both count as no value.
_NULLS = {normalize(word) for word in _NULL_WORDS}


def _value(obj: dict[str, Any], key: str) -> str | None:
    value = obj.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return None if normalize(text) in _NULLS else text


def _same_order_id(got: str | None, want: str | None) -> bool:
    def bare(value: str | None) -> str | None:
        return None if value is None else normalize(value).lstrip("#").replace(" ", "")

    return bare(got) == bare(want)


def _close_enough(got: str | None, alternatives: tuple[str, ...] | None) -> bool:
    """Equal or contained either way, after normalizing: `lamp` matches `table lamp`."""
    if alternatives is None:
        return got is None
    if got is None:
        return False
    g = normalize(got)
    return any(g == normalize(a) or normalize(a) in g or g in normalize(a) for a in alternatives)


def score_classify(reply: str, expected: Expected) -> Score:
    obj, strict = parse_json_object(reply)
    if obj is None:
        return Score(0.0, json_strict=False, json_valid=False, schema_valid=False)
    labels = {key: (_value(obj, key) or "").casefold() for key in ("category", "priority")}
    try:
        ClassifyOutput.model_validate(labels)
        schema_valid = True
    except ValidationError:
        schema_valid = False
    category_ok = labels["category"] == expected.category
    priority_ok = labels["priority"] == expected.priority
    return Score(
        (category_ok + priority_ok) / 2,
        json_strict=strict,
        json_valid=True,
        schema_valid=schema_valid,
        details={
            "category": labels["category"] or None,
            "category_ok": category_ok,
            "priority": labels["priority"] or None,
            "priority_ok": priority_ok,
        },
    )


def score_extract(reply: str, expected: Expected) -> Score:
    obj, strict = parse_json_object(reply)
    if obj is None:
        return Score(0.0, json_strict=False, json_valid=False, schema_valid=False)
    try:
        ExtractOutput.model_validate(obj)
        schema_valid = True
    except ValidationError:
        schema_valid = False
    issue = normalize(_value(obj, "issue") or "")
    checks = {
        "order_id_ok": _same_order_id(_value(obj, "order_id"), expected.order_id),
        "customer_name_ok": _close_enough(_value(obj, "customer_name"), (expected.customer_name,)),
        "product_ok": _close_enough(_value(obj, "product"), expected.product),
        "issue_ok": bool(issue) and any(normalize(k) in issue for k in expected.issue_keywords),
    }
    return Score(
        sum(checks.values()) / len(checks),
        json_strict=strict,
        json_valid=True,
        schema_valid=schema_valid,
        details=checks,
    )


def score_summarize(reply: str, expected: Expected) -> Score:
    text = normalize(reply)
    words = len(reply.split())
    found = [
        any(normalize(alternative) in text for alternative in fact)
        for fact in expected.summary_facts
    ]
    recall = sum(found) / len(found)
    within = 0 < words <= SUMMARY_MAX_WORDS
    return Score(
        recall if within else recall / 2,
        details={
            "facts_found": sum(found),
            "facts_total": len(found),
            "words": words,
            "within_limit": within,
        },
    )


def score(task: Task, reply: str) -> Score:
    expected = task.ticket.expected
    if task.kind == "classify":
        return score_classify(reply, expected)
    if task.kind == "extract":
        return score_extract(reply, expected)
    return score_summarize(reply, expected)
