from datetime import UTC, datetime

import pytest

from local_ai_benchmark.metrics import (
    RunLogError,
    benchmark_runs,
    new_run_id,
    read_jsonl,
    run_summary,
    select_run,
    spread,
    summarize,
)


def test_summarize_successful_runs():
    rows = [
        {"error": None, "total_latency_ms": 100, "ttft_ms": 20, "tokens_per_sec": 10},
        {"error": None, "total_latency_ms": 120, "ttft_ms": 30, "tokens_per_sec": 12},
    ]

    result = summarize(rows)

    assert result["runs"] == 2
    assert result["successful_runs"] == 2
    assert result["error_rate"] == 0
    assert result["median_total_latency_ms"] == 110
    assert result["median_ttft_ms"] == 25
    assert result["median_tokens_per_sec"] == 11


def test_summarize_error():
    rows = [
        {"error": "failure", "total_latency_ms": 100},
        {"error": None, "total_latency_ms": 200, "ttft_ms": 20, "tokens_per_sec": 5},
    ]

    result = summarize(rows)

    assert result["runs"] == 2
    assert result["successful_runs"] == 1
    assert result["error_rate"] == 0.5


def test_an_empty_reply_counts_as_an_error_and_stays_out_of_the_medians():
    rows = [
        {"error": "empty_response: the model returned no visible text", "tokens_per_sec": 99},
        {"error": None, "total_latency_ms": 200, "ttft_ms": 20, "tokens_per_sec": 5},
    ]

    result = summarize(rows)

    assert result["error_rate"] == 0.5
    assert result["median_tokens_per_sec"] == 5


def test_summarize_all_runs_failed():
    result = summarize([{"error": "timeout"}, {"error": "timeout"}])

    assert result == {"runs": 2, "successful_runs": 0, "error_rate": 1.0}


def test_summarize_no_runs():
    assert summarize([]) == {"runs": 0, "successful_runs": 0, "error_rate": 0.0}


def test_summarize_ignores_missing_metrics():
    rows = [
        {"error": None, "total_latency_ms": 100, "ttft_ms": None, "tokens_per_sec": None},
        {"error": None, "total_latency_ms": 300, "ttft_ms": 40, "tokens_per_sec": 8},
    ]

    result = summarize(rows)

    assert result["median_total_latency_ms"] == 200
    assert result["median_ttft_ms"] == 40
    assert result["median_tokens_per_sec"] == 8


def test_spread_gives_order_statistics_with_inclusive_quantiles():
    result = spread([float(v) for v in range(1, 11)])

    assert result == {"n": 10, "min": 1.0, "p50": 5.5, "p90": 9.1, "max": 10.0, "iqr": 4.5}


def test_spread_of_one_value():
    assert spread([7.0]) == {"n": 1, "min": 7.0, "p50": 7.0, "p90": 7.0, "max": 7.0, "iqr": 0.0}


def test_summary_carries_stats_and_prefill_speed():
    rows = [
        {"error": None, "total_latency_ms": 100, "ttft_ms": 20, "tokens_per_sec": 10,
         "prefill_tokens_per_sec": 300},
        {"error": None, "total_latency_ms": 300, "ttft_ms": 40, "tokens_per_sec": 30,
         "prefill_tokens_per_sec": 500},
    ]  # fmt: skip

    result = summarize(rows)

    assert result["median_prefill_tokens_per_sec"] == 400
    assert set(result["stats"]) == {
        "total_latency_ms", "ttft_ms", "tokens_per_sec", "prefill_tokens_per_sec",
    }  # fmt: skip
    assert result["stats"]["total_latency_ms"]["p90"] == 280
    assert result["stats"]["ttft_ms"]["iqr"] == 10


def test_run_ids_sort_by_time_and_differ():
    early = new_run_id(datetime(2026, 11, 13, 6, 15, 12, tzinfo=UTC))
    late = new_run_id(datetime(2026, 11, 13, 6, 15, 13, tzinfo=UTC))

    assert early.startswith("20261113T061512Z-")
    assert early < late
    assert new_run_id() != new_run_id()


def test_read_jsonl_skips_blank_lines_and_names_a_bad_line(tmp_path):
    log = tmp_path / "runs.jsonl"
    log.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")
    assert read_jsonl(log) == [{"a": 1}, {"a": 2}]

    log.write_text('{"a": 1}\n{broken\n', encoding="utf-8")
    with pytest.raises(RunLogError, match=r"runs.jsonl:2"):
        read_jsonl(log)
    with pytest.raises(RunLogError, match="no run log"):
        read_jsonl(tmp_path / "missing.jsonl")


def bench(run_id, index, model="m"):
    return {"run_id": run_id, "run_type": "benchmark", "run_index": index, "model": model,
            "timestamp": f"t{index}", "error": None, "total_latency_ms": 100.0 * index}  # fmt: skip


def test_runs_are_grouped_and_the_latest_is_selected_by_default():
    records = [
        bench("r1", 1), bench("r1", 2),
        {"run_id": "s1", "run_type": "single", "model": "m"},
        bench("r2", 1, model="other"),
    ]  # fmt: skip

    runs = benchmark_runs(records)
    assert [(r.run_id, r.model, r.runs) for r in runs] == [("r1", "m", 2), ("r2", "other", 1)]
    assert select_run(records, None)[0] == "r2"
    chosen, selected = select_run(records, "r1")
    assert chosen == "r1"
    assert [r["run_index"] for r in selected] == [1, 2]
    assert run_summary("r1", selected)["model"] == "m"


def test_select_run_reports_an_unknown_id_and_an_empty_log():
    with pytest.raises(RunLogError, match="no benchmark run with ID r9"):
        select_run([bench("r1", 1)], "r9")
    with pytest.raises(RunLogError, match="no benchmark runs"):
        select_run([{"run_type": "single"}], None)
