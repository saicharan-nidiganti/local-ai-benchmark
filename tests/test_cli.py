"""CLI tests with inference replaced by a stub; no server is needed."""

from __future__ import annotations

import json

from local_ai_benchmark import cli
from local_ai_benchmark.inference import InferenceResult


def stub_result(model, prompt, **_settings):
    return InferenceResult(
        model=model,
        prompt=prompt,
        response="ok",
        ttft_ms=10.0,
        total_latency_ms=100.0,
        output_tokens=20,
        generation_ms=80.0,
        tokens_per_sec=250.0,
        load_duration_ms=None,
        prompt_tokens=5,
        prompt_eval_duration_ms=5.0,
    )


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_benchmark_excludes_warmup_runs_from_the_dataset(monkeypatch, tmp_path):
    calls = []

    def fake_generate(**kwargs):
        calls.append(kwargs)
        return stub_result(**kwargs)

    monkeypatch.setattr(cli, "generate", fake_generate)
    output = tmp_path / "runs.jsonl"
    args = cli.build_parser().parse_args(
        ["benchmark", "--model", "m", "--prompt", "p", "--repeats", "3", "--warmup-runs", "2", "--output", str(output)]
    )

    args.func(args)

    records = read_jsonl(output)
    assert len(calls) == 5
    assert [r["run_index"] for r in records] == [1, 2, 3]
    assert all(r["run_type"] == "benchmark" for r in records)


def test_benchmark_records_the_settings_of_every_run(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "runs.jsonl"
    args = cli.build_parser().parse_args(
        ["benchmark", "--model", "m", "--prompt", "p", "--repeats", "2", "--temperature", "0.7",
         "--max-output-tokens", "128", "--output", str(output)]
    )

    args.func(args)

    for record in read_jsonl(output):
        assert record["model"] == "m"
        assert record["temperature"] == 0.7
        assert record["max_output_tokens"] == 128
        assert record["timestamp"]


def test_ask_appends_one_record_and_creates_the_output_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "nested" / "runs.jsonl"
    args = cli.build_parser().parse_args(["ask", "--model", "m", "--prompt", "p", "--output", str(output)])

    args.func(args)

    (record,) = read_jsonl(output)
    assert record["run_type"] == "single"
    assert record["response"] == "ok"
