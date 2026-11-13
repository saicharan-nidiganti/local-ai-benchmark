"""The triage app and its local web page, with the model replaced by a fake."""

from __future__ import annotations

import http.client
import json
import threading

import pytest

from local_ai_benchmark import app, web
from local_ai_benchmark.config import GenerationSettings
from local_ai_benchmark.inference import InferenceResult

TICKET = "Hello, order ORD-1 arrived broken. Please refund me. - Ana Silva"
REPLIES = {
    "classify": '{"category": "refund", "priority": "high"}',
    "extract": (
        '{"order_id": "ORD-1", "customer_name": "Ana Silva", "product": null, '
        '"issue": "arrived broken"}'
    ),
    "summarize": "ORD-1 arrived broken; Ana Silva wants a refund.",
}


def kind_of(prompt):
    if prompt.startswith("You triage"):
        return "classify"
    return "extract" if prompt.startswith("Extract") else "summarize"


def fake(replies=REPLIES, error=None, calls=None):
    def generate(model, prompt, settings=None, output_format=None):
        kind = kind_of(prompt)
        if calls is not None:
            calls.append((kind, output_format is not None, prompt))
        failed = error if error and error[0] == kind else None
        return InferenceResult(
            model=model, prompt=prompt, response="" if failed else replies[kind],
            ttft_ms=50.0, total_latency_ms=400.0, output_tokens=20, generation_ms=300.0,
            tokens_per_sec=60.0, load_duration_ms=1.0, prompt_tokens=100,
            prompt_eval_duration_ms=10.0, error=failed[1] if failed else None,
        )  # fmt: skip

    return generate


SETTINGS = GenerationSettings()


def test_a_ticket_gets_labels_fields_and_a_summary():
    calls = []

    result = app.triage(TICKET, "phi4-mini", SETTINGS, fake(calls=calls))

    assert (result.category, result.priority) == ("refund", "high")
    assert (result.order_id, result.customer_name, result.product) == ("ORD-1", "Ana Silva", None)
    assert result.issue == "arrived broken"
    assert result.summary == "ORD-1 arrived broken; Ana Silva wants a refund."
    assert result.errors == []
    assert result.total_ms == 1200.0
    # the suite's prompts, with the JSON schema for the two JSON tasks only
    assert [(k, schema) for k, schema, _ in calls] == [
        ("classify", True),
        ("extract", True),
        ("summarize", False),
    ]
    assert all(TICKET in prompt for *_, prompt in calls)


def test_the_recommended_model_is_the_comparisons_best_tradeoff():
    assert app.RECOMMENDED_MODEL == "phi4-mini"


@pytest.mark.parametrize(
    ("ticket", "message"), [("   ", "empty"), ("x" * (app.MAX_TICKET_CHARS + 1), "limit")]
)
def test_an_empty_or_too_long_ticket_is_refused(ticket, message):
    with pytest.raises(app.TriageError, match=message):
        app.triage(ticket, "m", SETTINGS, fake())


def test_a_failed_request_is_reported_and_the_rest_still_answers():
    result = app.triage(TICKET, "m", SETTINGS, fake(error=("extract", "connection refused")))

    assert result.errors == ["extract: connection refused"]
    assert result.order_id is None
    assert result.category == "refund"
    assert result.summary is not None


def test_a_reply_that_is_not_json_or_off_schema_is_reported():
    replies = {**REPLIES, "classify": "I think it is a refund.", "extract": '{"order_id": 5}'}

    result = app.triage(TICKET, "m", SETTINGS, fake(replies=replies))

    assert result.category is None
    assert result.errors[0] == "classify: the reply was not JSON"
    assert result.errors[1].startswith("extract: the reply did not match the schema")


def test_the_text_answer_shows_every_field_and_the_time():
    text = app.render_text(app.triage(TICKET, "phi4-mini", SETTINGS, fake()))

    assert "Category:  refund" in text
    assert "Product:   -" in text
    assert "phi4-mini on this machine, 3 requests, 1.2 s" in text


@pytest.fixture
def server():
    srv = web.make_server("phi4-mini", SETTINGS, fake(), port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def request(srv, method, path, body=None, headers=None):
    port = srv.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response, data


def test_the_server_listens_on_loopback_only(server):
    assert server.server_address[0] == "127.0.0.1"


def test_the_page_loads_nothing_from_elsewhere(server):
    response, body = request(server, "GET", "/")

    assert response.status == 200
    page = body.decode("utf-8")
    assert "phi4-mini on this machine" in page
    assert "http://" not in page and "https://" not in page  # no external resource at all
    assert response.getheader("Content-Security-Policy").startswith("default-src 'none'")
    assert response.getheader("X-Content-Type-Options") == "nosniff"


def test_a_ticket_posted_to_the_api_is_triaged(server):
    response, body = request(
        server, "POST", "/api/triage", json.dumps({"ticket": TICKET}),
        {"Content-Type": "application/json"},
    )  # fmt: skip

    assert response.status == 200
    answer = json.loads(body)
    assert answer["category"] == "refund"
    assert answer["model"] == "phi4-mini"
    assert answer["errors"] == []


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ("not json", 400),
        (json.dumps({"text": TICKET}), 400),
        (json.dumps({"ticket": 42}), 400),
        (json.dumps({"ticket": "   "}), 422),
        (json.dumps({"ticket": "x" * (web.MAX_BODY_BYTES + 1)}), 413),
    ],
)
def test_bad_requests_get_a_clear_status(server, body, status):
    response, data = request(server, "POST", "/api/triage", body)

    assert response.status == status
    assert "error" in json.loads(data)


def test_requests_for_another_host_name_are_refused(server):
    # a page on another site that rebinds its DNS name to 127.0.0.1 still sends its own Host
    port = server.server_address[1]
    response, _ = request(server, "GET", "/", headers={"Host": f"attacker.example:{port}"})

    assert response.status == 403


def test_a_post_from_another_origin_is_refused(server):
    response, _ = request(
        server, "POST", "/api/triage", json.dumps({"ticket": TICKET}),
        {"Origin": "http://attacker.example"},
    )  # fmt: skip

    assert response.status == 403


def test_unknown_paths_are_not_found_and_health_names_the_model(server):
    assert request(server, "GET", "/nope")[0].status == 404
    assert request(server, "POST", "/nope", "{}")[0].status == 404
    _, body = request(server, "GET", "/api/health")
    assert json.loads(body) == {"model": "phi4-mini", "host": "127.0.0.1"}


def test_the_example_ticket_is_fictional():
    assert "@example.com" in web.EXAMPLE_TICKET
