"""Command-line interface: `ask` and `benchmark`."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
import ollama

from . import __version__, app, cost, manifest, preflight, report, runtime, scorers, web
from .config import (
    BenchmarkSettings,
    ConfigError,
    ModelEntry,
    default_file,
    load_models,
    load_settings,
    resolve_model,
    with_overrides,
)
from .inference import generate
from .metrics import (
    RunLogError,
    append_jsonl,
    benchmark_runs,
    new_run_id,
    read_jsonl,
    run_summary,
    select_run,
    summary_of,
    utc_timestamp,
)
from .paths import default_run_log, project_root
from .sampler import ResourceSampler, ResourceSummary
from .suite import TASK_KINDS, SuiteError, load_suite

NO_SAMPLES = ResourceSummary(0, None, None, None, None, None)

OUTPUT_HELP = "run log to append to (default: data/raw/runs.jsonl in the project folder)"


def run_log(args: argparse.Namespace) -> Path:
    return Path(args.output) if args.output else default_run_log()


def resolve(args: argparse.Namespace) -> tuple[BenchmarkSettings, ModelEntry]:
    """Settings and model for this invocation: defaults, then the config files, then flags."""
    root = project_root()
    settings = with_overrides(
        load_settings(args.config or default_file(root, "benchmark.yaml")),
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        seed=args.seed,
        num_ctx=args.num_ctx,
        keep_alive=args.keep_alive,
        think=args.think,
        repeats=getattr(args, "repeats", None),
        warmup_runs=getattr(args, "warmup_runs", None),
    )
    model = resolve_model(args.model, load_models(args.models or default_file(root, "models.yaml")))
    return settings, model


def run_fields(settings: BenchmarkSettings, model: ModelEntry) -> dict[str, Any]:
    """What every record states about how it was produced."""
    return {"model_id": model.id, **settings.generation.record()}


def check_power(require_ac: bool) -> None:
    """Warn, or with --require-ac stop, when the machine is on battery: the GPU may be
    throttled and the charge falls during a run, so speed and energy are not comparable."""
    state = manifest.power()
    if state["on_ac"] is not False:
        return  # on AC, or a machine without a battery
    message = (
        f"running on battery ({state['battery_percent']}%): speed, power and energy are not "
        "comparable with runs on AC"
    )
    if require_ac:
        raise preflight.PreflightError(f"{message}. Plug in, or drop --require-ac.")
    print(f"Warning: {message}.", file=sys.stderr)


def check_runtime(
    settings: BenchmarkSettings,
    model: ModelEntry,
    require_ac: bool = False,
    allow_remote: bool = False,
) -> preflight.Preflight:
    """Fail before any request when the server is on another machine, or the server or the
    model is missing."""
    preflight.check_host(allow_remote)
    check_power(require_ac)
    checked = preflight.check(model.name, think=settings.generation.think)
    details = checked.model
    print(
        f"Ollama {checked.server_version} | {model.name} "
        f"({details.parameter_size or '?'} parameters, {details.quantization or '?'})"
    )
    return checked


def write_manifest(output: Path, run_id: str, checked: preflight.Preflight) -> Path:
    """One manifest per run ID, beside the run log."""
    path = manifest.manifest_log(output)
    append_jsonl(path, manifest.collect(run_id, checked.server_version, checked.model))
    return path


def placement(name: str) -> dict[str, Any]:
    """Where the model sat after the run: the share of it in GPU memory, and its context."""
    try:
        loaded = runtime.loaded_model(name)
    except (httpx.HTTPError, ollama.ResponseError, OSError):
        loaded = None  # the run is recorded either way
    share = loaded.gpu_share if loaded else None
    return {
        "gpu_offload_pct": None if share is None else round(share * 100, 1),
        "loaded_context_length": loaded.context_length if loaded else None,
    }


def measured_run(
    model: ModelEntry,
    prompt: str,
    settings: BenchmarkSettings,
    args: argparse.Namespace,
    output_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One request with its timings, its resource use, and where the model sat."""
    request: dict[str, Any] = {
        "model": model.name,
        "prompt": prompt,
        "settings": settings.generation,
    }
    if output_format is not None:
        request["output_format"] = output_format
    if args.no_sampling:
        result = generate(**request)
        resources = NO_SAMPLES
    else:
        with ResourceSampler(interval_s=args.sample_interval) as sampler:
            result = generate(**request)
        resources = sampler.summary(result.total_latency_ms / 1000)
    return {**result.to_dict(), **resources.record(), **placement(model.name)}


def ask(args: argparse.Namespace) -> None:
    settings, model = resolve(args)
    checked = check_runtime(settings, model, args.require_ac, args.allow_remote)
    measured = measured_run(model, args.prompt, settings, args)

    print("\n--- RESPONSE ---")
    print(measured["response"] or "[no response]")
    print("\n--- METRICS ---")
    shown = {k: v for k, v in measured.items() if k not in ("prompt", "response")}
    print(json.dumps(shown, indent=2, ensure_ascii=False))

    run_id = new_run_id()
    record = {
        "timestamp": utc_timestamp(),
        "run_id": run_id,
        "run_type": "single",
        **run_fields(settings, model),
        **measured,
    }
    output = run_log(args)
    append_jsonl(output, record)
    write_manifest(output, run_id, checked)
    print(f"\nSaved: {output}")


def unload_model(name: str) -> None:
    """Unload the model before a cold run; a runtime that cannot do it stops the benchmark."""
    try:
        runtime.unload(name)
    except (httpx.HTTPError, ollama.ResponseError, OSError, TimeoutError) as exc:
        raise preflight.PreflightError(f"could not unload {name} for a cold start: {exc}") from exc


def benchmark(args: argparse.Namespace) -> None:
    settings, model = resolve(args)
    checked = check_runtime(settings, model, args.require_ac, args.allow_remote)

    # Warm-up runs are deliberately not included in the measured dataset. A cold benchmark
    # has none: every measured run starts with the model unloaded.
    for i in range(0 if args.cold else settings.warmup_runs):
        print(f"Warm-up {i + 1}/{settings.warmup_runs}...")
        generate(model=model.name, prompt=args.prompt, settings=settings.generation)

    output = run_log(args)
    run_id = new_run_id()
    print(f"Run ID: {run_id}")
    print(f"Manifest: {write_manifest(output, run_id, checked)}")
    records = []

    for i in range(settings.repeats):
        if args.cold:
            unload_model(model.name)
        print(f"Measured run {i + 1}/{settings.repeats} ({'cold' if args.cold else 'warm'})...")
        measured = measured_run(model, args.prompt, settings, args)
        record = {
            "timestamp": utc_timestamp(),
            "run_id": run_id,
            "run_type": "benchmark",
            "run_index": i + 1,
            "start": "cold" if args.cold else "warm",
            **run_fields(settings, model),
            **measured,
        }
        append_jsonl(output, record)
        records.append(record)

    summary = run_summary(run_id, records)
    print("\n--- SUMMARY ---")
    print(json.dumps(summary, indent=2))
    print_network(summary)
    print(f"\nRaw results: {output}")
    print(f"Summarize it again with: local-ai-benchmark summarize --run-id {run_id}")


def print_network(summary: dict[str, Any]) -> None:
    """One line on whether anything reached another machine during the measured runs."""
    count = summary.get("remote_connections")
    if count is None:
        return
    found = "no connection" if count == 0 else f"{count} connection(s)"
    print(f"Network: {found} to another machine during the measured runs")


def suite_command(args: argparse.Namespace) -> None:
    settings, model = resolve(args)
    suite = load_suite(args.suite or default_suite_path())
    kinds = args.tasks.split(",") if args.tasks else list(TASK_KINDS)
    unknown = sorted(set(kinds) - set(TASK_KINDS))
    if unknown:
        raise SuiteError(f"unknown task kind(s): {', '.join(unknown)}")
    tasks = [task for task in suite.tasks() if task.kind in kinds]
    checked = check_runtime(settings, model, args.require_ac, args.allow_remote)
    print(f"Suite: {suite.name}, {len(tasks)} tasks x {args.repeats}, JSON mode: {args.json_mode}")

    # The model is loaded and warmed on the first task; warm-up runs are never recorded.
    for i in range(settings.warmup_runs):
        print(f"Warm-up {i + 1}/{settings.warmup_runs}...")
        generate(model=model.name, prompt=tasks[0].prompt, settings=settings.generation)

    output = run_log(args)
    run_id = new_run_id()
    print(f"Run ID: {run_id}")
    print(f"Manifest: {write_manifest(output, run_id, checked)}")
    records = []
    for repeat in range(args.repeats):
        for n, task in enumerate(tasks, start=1):
            schema = scorers.JSON_SCHEMAS.get(task.kind) if args.json_mode == "schema" else None
            measured = measured_run(model, task.prompt, settings, args, output_format=schema)
            scored = scorers.score(task, measured["response"] if not measured["error"] else "")
            print(f"[{n}/{len(tasks)}] {task.id}: score {scored.score:.2f}")
            record = {
                "timestamp": utc_timestamp(),
                "run_id": run_id,
                "run_type": "suite",
                "run_index": repeat * len(tasks) + n,
                "suite": suite.name,
                "task_id": task.id,
                "ticket_id": task.ticket.id,
                "task": task.kind,
                "json_mode": args.json_mode if task.kind in scorers.JSON_SCHEMAS else None,
                **run_fields(settings, model),
                **measured,
                **scored.record(),
            }
            append_jsonl(output, record)
            records.append(record)

    summary = summary_of(run_id, records)
    print("\n--- SUMMARY ---")
    print(json.dumps(summary, indent=2))
    quality = summary["quality"]
    parts = ", ".join(f"{k} {quality[k]:.2f}" for k in kinds)
    print(f"\nQuality: overall {quality['overall']:.2f} ({parts})")
    print_network(summary["speed"])
    print(f"Raw results: {output}")
    print(f"Summarize it again with: local-ai-benchmark summarize --run-id {run_id}")


def default_suite_path() -> Path:
    return project_root() / "benchmarks" / "support_triage_v1.jsonl"


def latest_suite_runs(records: list[dict[str, Any]], models: list[ModelEntry]) -> list[str]:
    """The latest suite run of each comparison model, in registry order."""
    latest = {run.model: run.run_id for run in benchmark_runs(records) if run.run_type == "suite"}
    chosen = [m for m in models if m.role == "comparison"]
    missing = [m.name for m in chosen if m.name not in latest]
    if missing:
        raise report.ReportError(f"no suite run for: {', '.join(missing)}")
    return [latest[m.name] for m in chosen]


def check_app_runtime(settings: BenchmarkSettings, model: ModelEntry, allow_remote: bool) -> None:
    """The app's preflight: the server is on this machine, it answers, the model is pulled."""
    preflight.check_host(allow_remote)
    preflight.check(model.name, think=settings.generation.think)


def read_ticket(args: argparse.Namespace) -> str:
    if args.text is not None:
        return str(args.text)
    if args.ticket == "-":
        return sys.stdin.read()
    try:
        return Path(args.ticket).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{args.ticket}: cannot read the ticket ({exc.strerror})") from exc


def triage_command(args: argparse.Namespace) -> None:
    settings, model = resolve(args)
    ticket = read_ticket(args)
    check_app_runtime(settings, model, args.allow_remote)
    try:
        result = app.triage(ticket, model.name, settings.generation, generate)
    except app.TriageError as exc:
        raise ConfigError(str(exc)) from exc
    if args.json:
        print(json.dumps(result.record(), indent=2, ensure_ascii=False))
    else:
        print(app.render_text(result))


def serve_command(args: argparse.Namespace) -> None:
    settings, model = resolve(args)
    check_app_runtime(settings, model, args.allow_remote)
    server = web.make_server(model.name, settings.generation, generate, port=args.port)
    print(f"Loading {model.name}...", flush=True)
    generate(model=model.name, prompt="Hello", settings=settings.generation)  # first ticket fast
    print(f"Ticket triage on http://{web.HOST}:{server.server_address[1]} ({model.name}).")
    print("Only this machine can reach it, and nothing is stored. Ctrl+C stops it.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.server_close()


def latest_cold_start(records: list[dict[str, Any]], model: str) -> dict[str, Any] | None:
    """The summary of the model's latest cold benchmark in the log, if it has one."""
    cold = [
        r
        for r in records
        if r.get("run_type") == "benchmark" and r.get("start") == "cold" and r.get("model") == model
    ]
    if not cold:
        return None
    run_id = str(cold[-1]["run_id"])  # the log is append-only: the last one is the latest
    return run_summary(run_id, [r for r in cold if r["run_id"] == run_id])


def report_command(args: argparse.Namespace) -> None:
    log = run_log(args)
    records = read_jsonl(log)
    manifests_path = manifest.manifest_log(log)
    manifests = (
        {m["run_id"]: m for m in read_jsonl(manifests_path)} if manifests_path.is_file() else {}
    )
    suite = load_suite(args.suite or default_suite_path())
    registry = load_models(args.models or default_file(project_root(), "models.yaml"))
    run_ids = args.run_id or latest_suite_runs(records, registry)
    assumptions = cost.load_cost(args.cost) if args.cost else None
    results = []
    for run_id in run_ids:
        _, selected = select_run(records, run_id)
        result = report.model_result(run_id, selected, suite, manifests.get(run_id))
        result = report.with_cold_start(result, latest_cold_start(records, result.model))
        if assumptions is not None:
            result = report.with_cost(result, cost.cost_of(selected, result.model, assumptions))
        results.append(result)
    path = report.write_report(results, args.out_dir, args.title, assumptions)
    found = report.verdict(results)
    print(f"Most accurate: {found.most_accurate}")
    print(f"Fastest: {found.fastest}")
    print(f"Best tradeoff: {found.best_tradeoff}")
    print(f"Report: {path}")


def summarize_command(args: argparse.Namespace) -> None:
    records = read_jsonl(run_log(args))
    if args.list:
        for run in benchmark_runs(records):
            print(f"{run.run_id}  {run.run_type}  {run.model}  {run.runs} runs  {run.started}")
        return
    run_id, selected = select_run(records, args.run_id)
    print(json.dumps(summary_of(run_id, selected), indent=2))


def _common_flags(measuring: bool = True) -> argparse.ArgumentParser:
    """Flags shared by the commands; the app's commands take no sampling or run-log flags."""
    common = argparse.ArgumentParser(add_help=False)
    gen = common.add_argument_group("generation settings (override configs/benchmark.yaml)")
    gen.add_argument("--temperature", type=float)
    gen.add_argument("--max-output-tokens", type=int)
    gen.add_argument("--seed", type=int)
    gen.add_argument("--num-ctx", type=int, help="context length in tokens")
    gen.add_argument("--keep-alive", help="how long Ollama keeps the model loaded, e.g. 5m")
    gen.add_argument(
        "--think",
        action=argparse.BooleanOptionalAction,
        help="let a thinking model reason before it answers (default: off)",
    )
    if measuring:
        _measurement_flags(common)
    network = common.add_argument_group("network")
    network.add_argument(
        "--allow-remote",
        action="store_true",
        help="allow an OLLAMA_HOST on another machine; prompts and replies then leave this one",
    )
    files = common.add_argument_group("files")
    files.add_argument(
        "--config", type=Path, help="settings file (default: configs/benchmark.yaml)"
    )
    files.add_argument("--models", type=Path, help="model registry (default: configs/models.yaml)")
    if measuring:
        files.add_argument("--output", type=Path, help=OUTPUT_HELP)
    return common


def _measurement_flags(common: argparse.ArgumentParser) -> None:
    measure = common.add_argument_group("resource sampling")
    measure.add_argument(
        "--sample-interval",
        type=float,
        default=0.5,
        help="seconds between RAM, VRAM and power samples during a run (default: 0.5)",
    )
    measure.add_argument("--no-sampling", action="store_true", help="do not sample resource use")
    measure.add_argument(
        "--require-ac",
        action="store_true",
        help="stop instead of warning when the machine is on battery",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-ai-benchmark",
        description="Benchmark small language models served locally by Ollama.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(required=True)
    common = _common_flags()
    model_help = "an Ollama tag (qwen3:4b) or a model id from the registry (qwen3-4b)"

    p_ask = sub.add_parser("ask", parents=[common], help="run one prompt and record it")
    p_ask.add_argument("--model", required=True, help=model_help)
    p_ask.add_argument("--prompt", required=True)
    p_ask.set_defaults(func=ask)

    p_bench = sub.add_parser(
        "benchmark", parents=[common], help="warm up, then measure one prompt repeatedly"
    )
    p_bench.add_argument("--model", required=True, help=model_help)
    p_bench.add_argument("--prompt", required=True)
    p_bench.add_argument("--repeats", type=int, help="measured runs (default: 5)")
    p_bench.add_argument("--warmup-runs", type=int, help="unrecorded runs first (default: 1)")
    p_bench.add_argument(
        "--cold",
        action="store_true",
        help="unload the model before every measured run, so each one includes loading it; "
        "no warm-up runs",
    )
    p_bench.set_defaults(func=benchmark)

    suite_help = "suite file (default: benchmarks/support_triage_v1.jsonl in the project folder)"
    p_suite = sub.add_parser(
        "suite", parents=[common], help="run and score every task of a task suite"
    )
    p_suite.add_argument("--model", required=True, help=model_help)
    p_suite.add_argument("--suite", type=Path, help=suite_help)
    p_suite.add_argument(
        "--tasks", help="comma-separated task kinds to run (default: classify,extract,summarize)"
    )
    p_suite.add_argument(
        "--repeats", type=int, default=1, help="times to run every task (default: 1)"
    )
    p_suite.add_argument(
        "--json-mode",
        choices=("schema", "prompt"),
        default="schema",
        help="schema: the runtime constrains JSON tasks to their schema (default); "
        "prompt: the prompt alone asks for JSON",
    )
    p_suite.add_argument(
        "--warmup-runs", type=int, help="unrecorded runs of the first task first (default: 1)"
    )
    p_suite.set_defaults(func=suite_command)

    app_flags = _common_flags(measuring=False)
    app_model_help = f"{model_help} (default: {app.RECOMMENDED_MODEL}, the comparison's pick)"
    p_tri = sub.add_parser(
        "triage", parents=[app_flags], help="triage one support ticket offline (the app)"
    )
    p_tri.add_argument(
        "ticket",
        nargs="?",
        default="-",
        help="a text file holding the ticket, or - to read it from standard input (default)",
    )
    p_tri.add_argument("--text", help="the ticket itself, instead of a file")
    p_tri.add_argument("--model", default=app.RECOMMENDED_MODEL, help=app_model_help)
    p_tri.add_argument("--json", action="store_true", help="print the answer as JSON")
    p_tri.set_defaults(func=triage_command)

    p_srv = sub.add_parser(
        "serve", parents=[app_flags], help="the app as a web page on http://127.0.0.1"
    )
    p_srv.add_argument("--port", type=int, default=web.DEFAULT_PORT, help="default: 8765")
    p_srv.add_argument("--model", default=app.RECOMMENDED_MODEL, help=app_model_help)
    p_srv.set_defaults(func=serve_command)

    p_rep = sub.add_parser(
        "report", help="compare suite runs of several models as a results folder"
    )
    p_rep.add_argument(
        "--run-id",
        action="append",
        help="a suite run to compare; repeat it (default: the latest run of each comparison model)",
    )
    p_rep.add_argument("--out-dir", type=Path, required=True, help="folder to write the report to")
    p_rep.add_argument("--title", default="Model comparison", help="the report's heading")
    p_rep.add_argument("--suite", type=Path, help=suite_help)
    p_rep.add_argument("--models", type=Path, help="model registry (default: configs/models.yaml)")
    p_rep.add_argument("--output", type=Path, help="run log to read (default: as for benchmark)")
    p_rep.add_argument(
        "--cost",
        type=Path,
        help="cost assumptions (for example configs/cost.yaml): adds the cost section",
    )
    p_rep.set_defaults(func=report_command)

    p_sum = sub.add_parser(
        "summarize", help="rebuild a benchmark's or a suite run's summary from the run log"
    )
    p_sum.add_argument("--run-id", help="the run to summarize (default: the latest)")
    p_sum.add_argument(
        "--list", action="store_true", help="list the benchmark and suite runs in the log"
    )
    p_sum.add_argument("--output", type=Path, help="run log to read (default: as for benchmark)")
    p_sum.set_defaults(func=summarize_command)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (ConfigError, RunLogError, SuiteError, report.ReportError) as exc:
        parser.exit(2, f"local-ai-benchmark: error: {exc}\n")
    except preflight.PreflightError as exc:
        parser.exit(3, f"local-ai-benchmark: error: {exc}\n")


if __name__ == "__main__":
    main()
