"""The task suite: the repository's suite file is valid, and invalid files are rejected."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from local_ai_benchmark.suite import (
    CATEGORIES,
    PRIORITIES,
    PROMPT_VARIANTS,
    RUBRIC_EXAMPLES,
    SUMMARY_MAX_WORDS,
    TASK_KINDS,
    SuiteError,
    load_suite,
)

SUITE = Path(__file__).resolve().parents[1] / "benchmarks" / "support_triage_v1.jsonl"


@pytest.fixture(scope="module")
def suite():
    return load_suite(SUITE)


def test_the_suite_has_30_to_50_tasks_in_three_kinds(suite):
    tasks = suite.tasks()

    assert suite.name == "support_triage_v1"
    assert 30 <= len(tasks) <= 50
    assert Counter(t.kind for t in tasks) == {"classify": 15, "extract": 15, "summarize": 15}
    assert len({t.id for t in tasks}) == len(tasks)


def test_every_category_and_priority_is_covered(suite):
    categories = Counter(t.expected.category for t in suite.tickets)
    priorities = Counter(t.expected.priority for t in suite.tickets)

    assert set(categories) == set(CATEGORIES)
    assert min(categories.values()) >= 3
    assert set(priorities) == set(PRIORITIES)


def test_expected_values_appear_in_the_ticket(suite):
    for t in suite.tickets:
        text = t.ticket.casefold()
        assert t.expected.customer_name.casefold() in text, t.id
        if t.expected.order_id is not None:
            assert t.expected.order_id.casefold() in text, t.id
        if t.expected.product is not None:
            assert any(p.casefold() in text for p in t.expected.product), t.id


def test_the_data_is_fictional(suite):
    for t in suite.tickets:
        for address in re.findall(r"[\w.+-]+@[\w.-]+", t.ticket):
            assert address.endswith("example.com"), (t.id, address)


def test_prompts_carry_the_ticket_and_the_limits(suite):
    task = suite.tasks()[2]

    assert task.kind == "summarize"
    assert suite.tickets[0].ticket in task.prompt
    assert f"at most {SUMMARY_MAX_WORDS} words" in task.prompt
    assert '{"category": "...", "priority": "..."}' in suite.tasks()[0].prompt


def write(tmp_path, *rows):
    path = tmp_path / "suite_v9.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def valid_row(**changes):
    row = json.loads(SUITE.read_text(encoding="utf-8").splitlines()[0])
    row.update(changes)
    return row


def test_rejects_an_unknown_label(tmp_path):
    row = valid_row()
    row["expected"]["category"] = "complaint"

    with pytest.raises(SuiteError, match=r"suite_v9\.jsonl:1: expected\.category"):
        load_suite(write(tmp_path, row))


def test_rejects_duplicate_ids_bad_json_and_empty_suites(tmp_path):
    with pytest.raises(SuiteError, match="duplicate ticket id T01"):
        load_suite(write(tmp_path, valid_row(), valid_row()))

    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not json\n", encoding="utf-8")
    with pytest.raises(SuiteError, match="not valid JSON"):
        load_suite(bad)

    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(SuiteError, match="no tickets"):
        load_suite(empty)

    with pytest.raises(SuiteError, match="no suite"):
        load_suite(tmp_path / "missing.jsonl")


def test_rejects_a_fact_without_any_wording_and_unknown_keys(tmp_path):
    row = valid_row()
    row["expected"]["summary_facts"] = [["invoice"], []]
    with pytest.raises(SuiteError, match="summary_facts"):
        load_suite(write(tmp_path, row))

    row = valid_row(notes="extra")
    with pytest.raises(SuiteError, match="notes"):
        load_suite(write(tmp_path, row))


def test_the_rubric_variant_changes_only_the_classify_prompt():
    suite = load_suite(
        Path(__file__).resolve().parents[1] / "benchmarks" / "support_triage_v1.jsonl"
    )
    default = {t.id: t.prompt for t in suite.tasks()}

    for task in suite.tasks("rubric"):
        if task.kind == "classify":
            assert task.prompt != default[task.id]
            assert "Choose the lowest priority that fits." in task.prompt
            assert task.prompt.count("Answer: {") == len(RUBRIC_EXAMPLES)
            assert task.prompt.endswith("Ticket:\n" + task.ticket.ticket)
        else:
            assert task.prompt == default[task.id]


def test_the_worked_examples_share_no_phrase_with_the_suite():
    # the suite must stay unseen: no run of five words in an example appears in any ticket
    suite = load_suite(
        Path(__file__).resolve().parents[1] / "benchmarks" / "support_triage_v1.jsonl"
    )

    def runs(text):
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {" ".join(words[i : i + 5]) for i in range(len(words) - 4)}

    tickets = set().union(*(runs(t.ticket) for t in suite.tickets))
    for text, category, priority in RUBRIC_EXAMPLES:
        assert not runs(text) & tickets, text
        assert category in CATEGORIES and priority in PRIORITIES


def test_every_variant_names_all_three_prompts():
    assert set(PROMPT_VARIANTS) == {"default", "rubric"}
    assert all(set(prompts) == set(TASK_KINDS) for prompts in PROMPT_VARIANTS.values())


HOLDOUT = SUITE.with_name("support_triage_holdout_v1.jsonl")


def test_the_holdout_suite_is_balanced_fictional_and_unseen():
    holdout, v1 = load_suite(HOLDOUT), load_suite(SUITE)

    def runs(text):
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {" ".join(words[i : i + 5]) for i in range(len(words) - 4)}

    seen = set().union(
        *(runs(t.ticket) for t in v1.tickets), *(runs(text) for text, *_ in RUBRIC_EXAMPLES)
    )
    assert len(holdout.tickets) == 15
    assert Counter(t.expected.category for t in holdout.tickets) == dict.fromkeys(CATEGORIES, 3)
    assert {t.expected.priority for t in holdout.tickets} == set(PRIORITIES)
    assert not {t.id for t in holdout.tickets} & {t.id for t in v1.tickets}
    for t in holdout.tickets:
        assert not runs(t.ticket) & seen, t.id  # no phrase from the suite or the examples
        for address in re.findall(r"[\w.+-]+@[\w.-]+", t.ticket):
            assert address.endswith("example.com"), (t.id, address)
        assert t.expected.customer_name in t.ticket
        assert t.expected.order_id is None or t.expected.order_id in t.ticket
