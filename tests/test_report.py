"""The comparison report, from synthetic suite runs."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from local_ai_benchmark import report
from local_ai_benchmark.suite import load_suite

SUITE = load_suite(Path(__file__).resolve().parents[1] / "benchmarks" / "support_triage_v1.jsonl")


def suite_records(run_id, model, score, tokens_per_sec, latency_ms=1000.0):
    """One record per task of the real suite, all with the same score and speed."""
    rows = []
    for n, task in enumerate(SUITE.tasks(), start=1):
        rows.append(
            {
                "run_id": run_id, "run_type": "suite", "run_index": n, "suite": SUITE.name,
                "task_id": task.id, "ticket_id": task.ticket.id, "task": task.kind,
                "json_mode": "schema" if task.kind != "summarize" else None,
                "model": model, "error": None, "score": score,
                "json_strict": True if task.kind != "summarize" else None,
                "json_valid": True if task.kind != "summarize" else None,
                "schema_valid": True if task.kind != "summarize" else None,
                "total_latency_ms": latency_ms, "ttft_ms": 50.0,
                "tokens_per_sec": tokens_per_sec, "prefill_tokens_per_sec": 600.0,
                "gpu_offload_pct": 66.3, "peak_gpu_memory_mb": 2315.0,
                "mean_gpu_power_w": 38.0, "gpu_energy_j": 40.0,
            }
        )  # fmt: skip
    return rows


def result(run_id, model, score, speed, latency_ms=1000.0):
    manifest = {
        "model": {"digest": "abcdef1234567890", "quantization": "Q4_K_M"},
        "runtime": {"version": "0.40.16"},
        "harness": {"git_sha": "0123456789abcdef"},
    }
    return report.model_result(
        run_id, suite_records(run_id, model, score, speed, latency_ms), SUITE, manifest
    )


def test_the_verdict_names_the_fastest_the_most_accurate_and_the_tradeoff():
    results = [
        result("r1", "accurate", 0.94, 30.0),
        result("r2", "nearly", 0.91, 35.0),
        result("r3", "fast", 0.73, 57.0),
    ]

    found = report.verdict(results)

    assert found.most_accurate == "accurate"
    assert found.fastest == "fast"
    assert found.best_tradeoff == "nearly"  # within 0.05 of the best, and faster


def test_the_tradeoff_is_the_most_accurate_model_when_no_other_is_close():
    results = [result("r1", "accurate", 0.94, 30.0), result("r2", "fast", 0.70, 57.0)]

    assert report.verdict(results).best_tradeoff == "accurate"


def test_quality_is_broken_down_by_ticket_category_and_task_latency():
    r = result("r1", "m", 0.5, 30.0, latency_ms=1200.0)

    assert set(r.by_category) == {"billing", "refund", "shipping", "technical", "account"}
    assert all(v == 0.5 for v in r.by_category.values())
    assert r.latency_by_task == {"classify": 1200.0, "extract": 1200.0, "summarize": 1200.0}
    assert r.quality == 0.5
    assert r.decode_speed == 30.0
    assert r.stat("gpu_offload_pct") == 66.3


def test_the_chart_is_valid_svg_with_a_point_per_model():
    svg = report.quality_speed_svg(
        [result("r1", "qwen3:4b", 0.9, 30.0), result("r2", "a&b", 0.7, 50.0)]
    )

    root = ET.fromstring(svg)
    circles = root.findall("{http://www.w3.org/2000/svg}circle")
    assert len(circles) == 2
    assert "qwen3:4b" in svg
    assert "a&amp;b" in svg  # names are escaped


def test_the_report_folder_holds_the_readme_chart_summaries_and_manifests(tmp_path):
    results = [result("r1", "accurate", 0.94, 30.0), result("r2", "fast", 0.73, 57.0)]

    readme = report.write_report(results, tmp_path / "out", "Three models")

    text = readme.read_text(encoding="utf-8")
    assert text.startswith("# Three models")
    assert "**Most accurate:** accurate" in text
    assert "**Fastest:** fast" in text
    assert "![Overall quality against median decode speed](quality_vs_speed.svg)" in text
    assert "| accurate | schema | 0.94 |" in text
    assert "JSON mode `schema`" in text
    assert "`abcdef123456`" in text
    assert (tmp_path / "out" / "quality_vs_speed.svg").is_file()
    summaries = json.loads((tmp_path / "out" / "summaries.json").read_text(encoding="utf-8"))
    assert [s["run_id"] for s in summaries] == ["r1", "r2"]
    assert len(json.loads((tmp_path / "out" / "manifests.json").read_text(encoding="utf-8"))) == 2


def test_a_report_needs_two_suite_runs(tmp_path):
    with pytest.raises(report.ReportError, match="at least two"):
        report.write_report([result("r1", "m", 0.9, 30.0)], tmp_path, "x")

    with pytest.raises(report.ReportError, match="not a suite run"):
        report.model_result("b1", [{"run_type": "benchmark"}], SUITE, None)


def test_missing_values_print_as_not_available():
    assert report._fmt(None) == "n/a"
    assert report._fmt(1234.5, 1) == "1,234.5"


def test_labels_of_close_points_do_not_overlap():
    # the published comparison: two models at the same quality, 5 tokens/s apart
    points = [(327.4, 62.7, "qwen3:4b-instruct"), (363.7, 65.0, "phi4-mini")]

    (x1, y1, a1), (x2, y2, a2) = report.place_labels(points, (70, 30, 610, 340))

    def box(x, y, anchor, text):
        w = len(text) * report.CHAR_WIDTH
        return (x, y - 12, x + w, y + 3) if anchor == "start" else (x - w, y - 12, x, y + 3)

    first, second = box(x1, y1, a1, "qwen3:4b-instruct"), box(x2, y2, a2, "phi4-mini")
    assert not report._overlaps(first, second)


def test_a_label_near_the_right_edge_moves_to_the_left_of_its_point():
    [(x, _, anchor)] = report.place_labels([(600.0, 200.0, "llama3.2:3b")], (70, 30, 610, 340))

    assert anchor == "end"
    assert x < 600.0


def test_the_quality_axis_zooms_to_the_data_and_ends_at_one():
    close = [result("a", "a", 0.89, 30.0), result("b", "b", 0.81, 50.0)]
    spread = [result("a", "a", 0.9, 30.0), result("b", "b", 0.1, 50.0)]

    assert report.quality_axis(close) == (0.7, 1.0, 0.1)
    assert report.quality_axis(spread) == (0.0, 1.0, 0.25)
    assert "within 0.05 of the best quality" in report.quality_speed_svg(close)


def test_every_report_file_has_unix_line_endings(tmp_path):
    # the same bytes on Windows and Linux, so a regenerated report shows no spurious diff
    results = [result("r1", "a", 0.9, 30.0), result("r2", "b", 0.8, 50.0)]

    report.write_report(results, tmp_path, "x")

    for name in ("README.md", "quality_vs_speed.svg", "summaries.json", "manifests.json"):
        assert b"\r\n" not in (tmp_path / name).read_bytes(), name


def audited(run_id, model, connections, interfaces):
    records = suite_records(run_id, model, 0.9, 30.0)
    for row in records:
        row["remote_connections"] = connections
    manifest = {
        "model": {"digest": "abcdef1234567890", "quantization": "Q4_K_M"},
        "runtime": {"version": "0.40.16", "local": True},
        "network": {"interfaces_up": interfaces},
        "harness": {"git_sha": "0123456789abcdef"},
    }
    return report.model_result(run_id, records, SUITE, manifest)


def test_audited_runs_get_a_privacy_section():
    results = [audited("r1", "a", 0, []), audited("r2", "b", 0, ["vEthernet (WSL)"])]

    text = report.render_markdown(results, "x", "chart.svg")

    assert "## Privacy" in text
    assert "| a | this machine | none | 0 in 45 runs |" in text
    assert "| b | this machine | vEthernet (WSL) | 0 in 45 runs |" in text


def test_runs_from_before_the_audit_have_no_privacy_section():
    results = [result("r1", "a", 0.9, 30.0), result("r2", "b", 0.8, 50.0)]

    assert "## Privacy" not in report.render_markdown(results, "x", "chart.svg")


def test_a_cold_start_adds_the_latency_targets():
    warm = result("r1", "a", 0.9, 30.0)
    cold = {"median_ttft_ms": 4200.0}
    results = [report.with_cold_start(warm, cold), result("r2", "b", 0.8, 8.0)]

    text = report.render_markdown(results, "x", "chart.svg")

    assert "## Latency targets for interactive use" in text
    assert "| a | 50.0: meets | 30.0: meets | 4,200.0: meets |" in text
    assert "| b | 50.0: meets | 8.0: misses | not measured |" in text


def test_without_cold_starts_there_is_no_latency_section():
    results = [result("r1", "a", 0.9, 30.0), result("r2", "b", 0.8, 50.0)]

    assert "Latency targets" not in report.render_markdown(results, "x", "chart.svg")


def test_cost_assumptions_add_the_cost_section_and_cost_json(tmp_path):
    from local_ai_benchmark import cost

    loaded = cost.load_cost(Path(__file__).resolve().parents[1] / "configs" / "cost.yaml")
    records = suite_records("r1", "phi4-mini", 0.9, 30.0)
    for row in records:
        row.update(output_tokens=50, prompt_tokens=200)
    priced = report.with_cost(
        report.model_result("r1", records, SUITE, None),
        cost.cost_of(records, "phi4-mini", loaded),
    )
    results = [priced, result("r2", "unpriced", 0.8, 50.0)]

    readme = report.write_report(results, tmp_path, "x", loaded)

    text = readme.read_text(encoding="utf-8")
    assert "## Cost" in text
    assert "| unpriced | n/a | n/a | n/a | n/a | n/a |" in text
    assert "Azure AI Foundry (Phi-4-mini)" in text
    assert "TGSPDCL" in text
    saved = json.loads((tmp_path / "cost.json").read_text(encoding="utf-8"))
    assert saved["models"]["unpriced"] is None
    assert saved["models"]["phi4-mini"]["hosted_provider"] == "Azure AI Foundry (Phi-4-mini)"
    assert saved["assumptions"]["electricity"]["price_per_kwh"] == 7.7


def test_without_cost_assumptions_there_is_no_cost_section(tmp_path):
    results = [result("r1", "a", 0.9, 30.0), result("r2", "b", 0.8, 50.0)]

    report.write_report(results, tmp_path, "x")

    assert "## Cost" not in (tmp_path / "README.md").read_text(encoding="utf-8")
    assert not (tmp_path / "cost.json").exists()
