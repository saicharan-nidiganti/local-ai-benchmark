"""Scorers for the three task kinds, on the suite's own expectations."""

from __future__ import annotations

from pathlib import Path

import pytest

from local_ai_benchmark import scorers
from local_ai_benchmark.suite import Task, load_suite

SUITE = load_suite(Path(__file__).resolve().parents[1] / "benchmarks" / "support_triage_v1.jsonl")
TICKETS = {t.id: t for t in SUITE.tickets}
LAMP = TICKETS["T04"]  # refund, high, A-1042, Priya Raman, ceramic table lamp
DATA = TICKETS["T15"]  # account, low, no order, no product


# --- JSON parsing --------------------------------------------------------------------------


def test_a_bare_object_is_strict_json():
    assert scorers.parse_json_object('  {"a": 1} ') == ({"a": 1}, True)


@pytest.mark.parametrize(
    "reply",
    [
        '```json\n{"a": 1}\n```',
        '```\n{"a": 1}\n```',
        'Here you go: {"a": 1} Hope this helps.',
    ],
)
def test_an_object_in_a_fence_or_prose_is_recovered_but_not_strict(reply):
    assert scorers.parse_json_object(reply) == ({"a": 1}, False)


@pytest.mark.parametrize("reply", ["no json here", "[1, 2]", "{'a': 1}", ""])
def test_no_object_is_none(reply):
    assert scorers.parse_json_object(reply) == (None, False)


def test_normalize_ignores_case_punctuation_and_spacing_but_keeps_hyphens():
    assert scorers.normalize("  Order #A-1042,  CRACKED! ") == "order a-1042 cracked"


# --- classify -------------------------------------------------------------------------------


def test_a_correct_classification_scores_one():
    result = scorers.score_classify('{"category": "refund", "priority": "high"}', LAMP.expected)

    assert result.score == 1.0
    assert (result.json_strict, result.json_valid, result.schema_valid) == (True, True, True)


def test_labels_ignore_case_and_each_is_half_the_score():
    result = scorers.score_classify('{"category": "Refund", "priority": "MEDIUM"}', LAMP.expected)

    assert result.score == 0.5
    assert result.details["category_ok"] is True
    assert result.details["priority_ok"] is False


def test_an_unknown_label_breaks_the_schema_and_scores_zero_for_it():
    result = scorers.score_classify('{"category": "complaint", "priority": "high"}', LAMP.expected)

    assert result.schema_valid is False
    assert result.score == 0.5


def test_unparseable_classification_scores_zero():
    result = scorers.score_classify("It is a refund, high priority.", LAMP.expected)

    assert result.score == 0.0
    assert result.json_valid is False


# --- extract --------------------------------------------------------------------------------


def test_a_correct_extraction_scores_one():
    reply = (
        '{"order_id": "A-1042", "customer_name": "Priya Raman", '
        '"product": "ceramic table lamp", "issue": "lamp arrived cracked"}'
    )

    result = scorers.score_extract(reply, LAMP.expected)

    assert result.score == 1.0
    assert result.schema_valid is True


def test_extraction_tolerates_case_a_hash_and_shorter_product_names():
    reply = (
        '```json\n{"order_id": "#a-1042", "customer_name": "priya raman", '
        '"product": "Lamp", "issue": "Damaged on arrival"}\n```'
    )

    result = scorers.score_extract(reply, LAMP.expected)

    assert result.score == 1.0
    assert result.json_strict is False


def test_null_order_and_product_are_correct_when_none_exists():
    reply = (
        '{"order_id": null, "customer_name": "Olivia Brown", "product": "N/A", '
        '"issue": "wants to download her data"}'
    )

    assert scorers.score_extract(reply, DATA.expected).score == 1.0


def test_wrong_fields_each_cost_a_quarter():
    reply = (
        '{"order_id": "A-1043", "customer_name": "Priya Raman", '
        '"product": "desk", "issue": "late delivery"}'
    )

    result = scorers.score_extract(reply, LAMP.expected)

    assert result.score == 0.25
    assert result.details == {
        "order_id_ok": False,
        "customer_name_ok": True,
        "product_ok": False,
        "issue_ok": False,
    }


def test_a_missing_key_breaks_the_schema():
    result = scorers.score_extract('{"order_id": "A-1042"}', LAMP.expected)

    assert result.schema_valid is False
    assert result.score == 0.25


def test_unparseable_extraction_scores_zero():
    assert scorers.score_extract("Order A-1042, Priya Raman", LAMP.expected).score == 0.0


# --- summarize ------------------------------------------------------------------------------


def test_a_summary_with_every_fact_within_the_limit_scores_one():
    reply = "Order A-1042: the ceramic lamp arrived cracked. Customer wants a full refund."

    result = scorers.score_summarize(reply, LAMP.expected)

    assert result.score == 1.0
    assert result.details["facts_found"] == 3


def test_a_missing_fact_lowers_the_score():
    reply = "The lamp arrived broken and the customer wants a refund."

    assert scorers.score_summarize(reply, LAMP.expected).score == pytest.approx(2 / 3)


def test_a_summary_over_the_limit_is_halved():
    reply = "Order A-1042 cracked refund " + "word " * 40

    result = scorers.score_summarize(reply, LAMP.expected)

    assert result.details["within_limit"] is False
    assert result.score == 0.5


def test_an_empty_summary_scores_zero():
    assert scorers.score_summarize("", LAMP.expected).score == 0.0


# --- dispatch -------------------------------------------------------------------------------


def test_score_dispatches_by_task_kind_and_records_cleanly():
    task = Task(LAMP, "classify")

    record = scorers.score(task, '{"category": "refund", "priority": "high"}').record()

    assert record["score"] == 1.0
    assert record["json_strict"] is True
    assert record["score_details"]["category"] == "refund"
    assert scorers.score(Task(LAMP, "summarize"), "").record()["json_valid"] is None
