"""The task suite: versioned support tickets, each expanded into three tasks (ADR-0008)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

Category = Literal["billing", "refund", "shipping", "technical", "account"]
Priority = Literal["urgent", "high", "medium", "low"]
TaskKind = Literal["classify", "extract", "summarize"]

CATEGORIES: tuple[str, ...] = ("billing", "refund", "shipping", "technical", "account")
PRIORITIES: tuple[str, ...] = ("urgent", "high", "medium", "low")
TASK_KINDS: tuple[TaskKind, ...] = ("classify", "extract", "summarize")
SUMMARY_MAX_WORDS = 40

# The prompts are part of the suite version: changing one makes a new suite version.
PROMPTS: dict[str, str] = {
    "classify": (
        "You triage customer support tickets. Classify the ticket below.\n"
        'Reply with only a JSON object: {{"category": "...", "priority": "..."}}\n'
        "category is one of: billing (invoices, plans, prices, payment methods going forward), "
        "refund (money back for an order or charge already paid), shipping (delivery status, "
        "delays, addresses, lost parcels), technical (a product or the app does not work), "
        "account (sign-in, profile, data, security).\n"
        "priority is one of: urgent (a security problem, or the customer's business is stopped), "
        "high (money lost, or the product unusable), medium (a problem with a workaround, or a "
        "delay), low (a question or feedback).\n\n"
        "Ticket:\n{ticket}"
    ),
    "extract": (
        "Extract these fields from the support ticket below.\n"
        "Reply with only a JSON object with exactly these keys:\n"
        "order_id: the order number as written, or null if there is none\n"
        "customer_name: the customer's full name\n"
        "product: the product concerned, or null if none is named\n"
        "issue: the problem in at most 8 words\n\n"
        "Ticket:\n{ticket}"
    ),
    "summarize": (
        "Summarize the support ticket below for the agent who will handle it, in at most "
        f"{SUMMARY_MAX_WORDS} words. Include the order number if there is one, the problem, "
        "and what the customer wants.\n\n"
        "Ticket:\n{ticket}"
    ),
}


class SuiteError(ValueError):
    """A suite file is missing or has an invalid ticket; the message names the line."""


class Expected(BaseModel):
    """What a correct answer contains. Lists are acceptable alternatives."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: Category
    priority: Priority
    order_id: str | None
    customer_name: str = Field(min_length=1)
    product: tuple[str, ...] | None
    issue_keywords: tuple[str, ...] = Field(min_length=1)
    summary_facts: tuple[tuple[str, ...], ...] = Field(min_length=1)

    @field_validator("summary_facts")
    @classmethod
    def _each_fact_has_an_alternative(
        cls, facts: tuple[tuple[str, ...], ...]
    ) -> tuple[tuple[str, ...], ...]:
        if any(not alternatives for alternatives in facts):
            raise ValueError("every summary fact needs at least one acceptable wording")
        return facts


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    ticket: str = Field(min_length=1)
    expected: Expected


@dataclass(frozen=True)
class Task:
    ticket: Ticket
    kind: TaskKind

    @property
    def id(self) -> str:
        return f"{self.ticket.id}:{self.kind}"

    @property
    def prompt(self) -> str:
        return PROMPTS[self.kind].format(ticket=self.ticket.ticket)


@dataclass(frozen=True)
class Suite:
    name: str
    tickets: tuple[Ticket, ...]

    def tasks(self) -> list[Task]:
        """Ticket by ticket, each ticket's tasks in a fixed order."""
        return [Task(ticket, kind) for ticket in self.tickets for kind in TASK_KINDS]


def load_suite(path: str | Path) -> Suite:
    path = Path(path)
    if not path.is_file():
        raise SuiteError(f"no suite at {path}")
    tickets: list[Ticket] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            ticket = Ticket.model_validate(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SuiteError(f"{path}:{number}: not valid JSON ({exc.msg})") from exc
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(part) for part in first["loc"])
            raise SuiteError(f"{path}:{number}: {where}: {first['msg']}") from exc
        if ticket.id in seen:
            raise SuiteError(f"{path}:{number}: duplicate ticket id {ticket.id}")
        seen.add(ticket.id)
        tickets.append(ticket)
    if not tickets:
        raise SuiteError(f"{path}: the suite has no tickets")
    return Suite(name=path.stem, tickets=tuple(tickets))
