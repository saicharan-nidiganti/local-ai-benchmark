"""CLI tests with inference replaced by a stub; no server is needed."""

from __future__ import annotations

import json

import httpx
import pytest

from local_ai_benchmark import __version__, cli, paths, preflight, runtime, sampler
from local_ai_benchmark.inference import InferenceResult

MODEL_DETAILS = runtime.ModelDetails(
    name="m",
    digest="abc123",
    family="qwen3",
    parameter_size="4.0B",
    quantization="Q4_K_M",
    format="gguf",
    capabilities=("completion",),
)


class FakeSampler:
    """Stands in for ResourceSampler: no thread, fixed readings."""

    def __init__(self, interval_s=0.5):
        self.interval_s = interval_s

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def summary(self, duration_s):
        return sampler.ResourceSummary(3, 8000.0, 2500.0, 3500.0, 30.0, 30.0 * duration_s)


@pytest.fixture(autouse=True)
def fake_resources(monkeypatch):
    """No real nvidia-smi, process scan or Ollama query during CLI tests."""
    monkeypatch.setattr(cli, "ResourceSampler", FakeSampler)
    monkeypatch.setattr(
        cli.runtime, "loaded_model", lambda name: runtime.LoadedModel(name, 1000, 663, 4096)
    )


@pytest.fixture(autouse=True)
def fixed_manifest(monkeypatch):
    """Skip the real system queries; manifest.py has its own tests."""
    monkeypatch.setattr(
        cli.manifest,
        "collect",
        lambda run_id, server_version, model: {"run_id": run_id, "runtime": server_version},
    )


@pytest.fixture(autouse=True)
def server_is_up(monkeypatch):
    """Pretend the Ollama server answers and every model is pulled."""
    monkeypatch.setattr(
        cli.preflight,
        "check",
        lambda name, think=False: preflight.Preflight("0.40.16", MODEL_DETAILS),
    )


@pytest.fixture(autouse=True)
def isolated_project(monkeypatch, tmp_path):
    """Run every test in an empty project folder, so the repository's config files don't apply."""
    home = tmp_path / "project"
    home.mkdir()
    monkeypatch.setenv(paths.HOME_ENV_VAR, str(home))
    return home


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
        [
            "benchmark",
            "--model",
            "m",
            "--prompt",
            "p",
            "--repeats",
            "3",
            "--warmup-runs",
            "2",
            "--output",
            str(output),
        ]
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
        [
            "benchmark",
            "--model",
            "m",
            "--prompt",
            "p",
            "--repeats",
            "2",
            "--temperature",
            "0.7",
            "--max-output-tokens",
            "128",
            "--output",
            str(output),
        ]
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
    args = cli.build_parser().parse_args(
        ["ask", "--model", "m", "--prompt", "p", "--output", str(output)]
    )

    args.func(args)

    (record,) = read_jsonl(output)
    assert record["run_type"] == "single"
    assert record["response"] == "ok"


def test_every_record_states_its_model_id_and_generation_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    cli.main(["ask", "--model", "m", "--prompt", "p", "--output", str(output)])

    (record,) = read_jsonl(output)
    assert record["model_id"] == "m"
    assert record["temperature"] == 0.0
    assert record["max_output_tokens"] == 256
    assert record["seed"] == 42
    assert record["num_ctx"] == 4096
    assert record["keep_alive"] == "5m"
    assert record["think"] is False


def test_the_think_flag_switches_thinking_on_and_is_recorded(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "generate", lambda **kw: calls.append(kw) or stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    cli.main(["ask", "--model", "m", "--prompt", "p", "--think", "--output", str(output)])

    assert calls[0]["settings"].think is True
    (record,) = read_jsonl(output)
    assert record["think"] is True


def test_the_project_settings_file_applies_and_flags_override_it(
    monkeypatch, tmp_path, isolated_project
):
    configs = isolated_project / "configs"
    configs.mkdir()
    (configs / "benchmark.yaml").write_text(
        "benchmark:\n  repeats: 1\n  warmup_runs: 0\n  seed: 7\n", encoding="utf-8"
    )
    calls = []
    monkeypatch.setattr(cli, "generate", lambda **kw: calls.append(kw) or stub_result(**kw))
    output = tmp_path / "runs.jsonl"
    base = ["benchmark", "--model", "m", "--prompt", "p", "--output", str(output)]

    cli.main(base)
    cli.main([*base, "--seed", "9"])

    assert [r["seed"] for r in read_jsonl(output)] == [7, 9]
    assert len(calls) == 2  # repeats 1 and no warm-up, from the file
    assert calls[1]["settings"].seed == 9


def test_a_registry_id_runs_the_tagged_model(monkeypatch, tmp_path):
    registry = tmp_path / "models.yaml"
    registry.write_text("models:\n  - id: fast\n    name: tag:1\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(cli, "generate", lambda **kw: calls.append(kw) or stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    cli.main(
        [
            "ask",
            "--model",
            "fast",
            "--prompt",
            "p",
            "--models",
            str(registry),
            "--output",
            str(output),
        ]
    )

    assert calls[0]["model"] == "tag:1"
    (record,) = read_jsonl(output)
    assert record["model_id"] == "fast"
    assert record["model"] == "tag:1"


def test_a_bad_settings_file_exits_with_a_clear_error(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("benchmark:\n  repeets: 3\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["benchmark", "--model", "m", "--prompt", "p", "--config", str(bad)])

    assert exit_info.value.code == 2
    assert "unknown setting(s): repeets" in capsys.readouterr().err


def test_a_failed_preflight_stops_before_any_request(monkeypatch, tmp_path, capsys):
    def down(name, think=False):
        raise preflight.PreflightError("Ollama is not reachable at http://127.0.0.1:11434")

    calls = []
    monkeypatch.setattr(cli.preflight, "check", down)
    monkeypatch.setattr(cli, "generate", lambda **kw: calls.append(kw) or stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["benchmark", "--model", "m", "--prompt", "p", "--output", str(output)])

    assert exit_info.value.code == 3
    assert calls == []
    assert not output.exists()
    assert "not reachable" in capsys.readouterr().err


def test_the_preflight_result_is_printed(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))

    cli.main(["ask", "--model", "m", "--prompt", "p", "--output", str(tmp_path / "r.jsonl")])

    assert "Ollama 0.40.16" in capsys.readouterr().out


def test_version_flag(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])

    assert __version__ in capsys.readouterr().out


def printed_summary(text):
    """The JSON object printed after the SUMMARY banner."""
    body = text.split("--- SUMMARY ---", 1)[1]
    return json.loads(body[: body.index("\n}") + 2])


def test_a_benchmark_shares_one_run_id_and_summarize_reproduces_its_summary(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    cli.main(["benchmark", "--model", "m", "--prompt", "p", "--repeats", "3",
              "--warmup-runs", "0", "--output", str(output)])  # fmt: skip
    printed = printed_summary(capsys.readouterr().out)

    records = read_jsonl(output)
    assert len({r["run_id"] for r in records}) == 1
    assert printed["run_id"] == records[0]["run_id"]

    cli.main(["summarize", "--output", str(output)])
    assert json.loads(capsys.readouterr().out) == printed

    cli.main(["summarize", "--run-id", printed["run_id"], "--output", str(output)])
    assert json.loads(capsys.readouterr().out) == printed


def test_summarize_lists_the_benchmarks_in_the_log(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "runs.jsonl"
    for _ in range(2):
        cli.main(["benchmark", "--model", "m", "--prompt", "p", "--repeats", "1",
                  "--warmup-runs", "0", "--output", str(output)])  # fmt: skip
    capsys.readouterr()

    cli.main(["summarize", "--list", "--output", str(output)])

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    assert all("  m  1 runs  " in line for line in lines)


def test_summarize_without_a_log_or_with_an_unknown_id_exits_2(tmp_path, capsys):
    with pytest.raises(SystemExit) as missing:
        cli.main(["summarize", "--output", str(tmp_path / "none.jsonl")])
    assert missing.value.code == 2

    log = tmp_path / "runs.jsonl"
    log.write_text('{"run_id": "r1", "run_type": "benchmark"}\n', encoding="utf-8")
    with pytest.raises(SystemExit) as unknown:
        cli.main(["summarize", "--run-id", "r9", "--output", str(log)])
    assert unknown.value.code == 2
    assert "no benchmark run with ID r9" in capsys.readouterr().err


def test_each_run_id_gets_one_manifest_beside_the_run_log(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "logs" / "runs.jsonl"

    cli.main(["benchmark", "--model", "m", "--prompt", "p", "--repeats", "2",
              "--warmup-runs", "0", "--output", str(output)])  # fmt: skip
    cli.main(["ask", "--model", "m", "--prompt", "p", "--output", str(output)])

    manifests = read_jsonl(tmp_path / "logs" / "manifests.jsonl")
    run_ids = [r["run_id"] for r in read_jsonl(output)]
    assert [m["run_id"] for m in manifests] == [run_ids[0], run_ids[2]]
    assert manifests[0]["runtime"] == "0.40.16"


def test_every_measured_run_records_its_resource_use_and_gpu_share(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    cli.main(["benchmark", "--model", "m", "--prompt", "p", "--repeats", "2",
              "--warmup-runs", "0", "--output", str(output)])  # fmt: skip

    for record in read_jsonl(output):
        assert record["resource_samples"] == 3
        assert record["peak_gpu_memory_mb"] == 3500.0
        assert record["mean_gpu_power_w"] == 30.0
        assert record["gpu_energy_j"] == 3.0  # 30 W over the stub's 100 ms
        assert record["gpu_offload_pct"] == 66.3
        assert record["loaded_context_length"] == 4096


def test_no_sampling_keeps_the_fields_but_leaves_them_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    cli.main(["ask", "--model", "m", "--prompt", "p", "--no-sampling", "--output", str(output)])

    (record,) = read_jsonl(output)
    assert record["resource_samples"] == 0
    assert record["peak_gpu_memory_mb"] is None
    assert record["gpu_offload_pct"] == 66.3  # placement is read from Ollama, not sampled


def test_an_unreachable_server_after_the_run_leaves_the_placement_empty(monkeypatch, tmp_path):
    def gone(name):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    monkeypatch.setattr(cli.runtime, "loaded_model", gone)
    output = tmp_path / "runs.jsonl"

    cli.main(["ask", "--model", "m", "--prompt", "p", "--output", str(output)])

    (record,) = read_jsonl(output)
    assert record["gpu_offload_pct"] is None
    assert record["loaded_context_length"] is None


def test_the_summary_includes_resource_statistics(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    cli.main(["benchmark", "--model", "m", "--prompt", "p", "--repeats", "2",
              "--warmup-runs", "0", "--output", str(output)])  # fmt: skip

    stats = printed_summary(capsys.readouterr().out)["stats"]
    assert stats["peak_gpu_memory_mb"]["max"] == 3500.0
    assert stats["gpu_offload_pct"]["p50"] == 66.3


def test_ask_records_get_their_own_run_id(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "generate", lambda **kw: stub_result(**kw))
    output = tmp_path / "runs.jsonl"

    cli.main(["ask", "--model", "m", "--prompt", "p", "--output", str(output)])
    cli.main(["ask", "--model", "m", "--prompt", "p", "--output", str(output)])

    first, second = read_jsonl(output)
    assert first["run_id"] != second["run_id"]
