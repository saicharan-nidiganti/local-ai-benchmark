from app.metrics import summarize


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
