"""Command-line interface: `ask` and `benchmark`."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__, preflight
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
    utc_timestamp,
)
from .paths import default_run_log, project_root

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


def check_runtime(settings: BenchmarkSettings, model: ModelEntry) -> preflight.Preflight:
    """Fail before any request when the server or the model is missing."""
    checked = preflight.check(model.name, think=settings.generation.think)
    details = checked.model
    print(
        f"Ollama {checked.server_version} \u00b7 {model.name} "
        f"({details.parameter_size or '?'} parameters, {details.quantization or '?'})"
    )
    return checked


def ask(args: argparse.Namespace) -> None:
    settings, model = resolve(args)
    check_runtime(settings, model)
    result = generate(model=model.name, prompt=args.prompt, settings=settings.generation)

    print("\n--- RESPONSE ---")
    print(result.response or "[no response]")
    print("\n--- METRICS ---")
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    record = {
        "timestamp": utc_timestamp(),
        "run_id": new_run_id(),
        "run_type": "single",
        **run_fields(settings, model),
        **result.to_dict(),
    }
    output = run_log(args)
    append_jsonl(output, record)
    print(f"\nSaved: {output}")


def benchmark(args: argparse.Namespace) -> None:
    settings, model = resolve(args)
    check_runtime(settings, model)

    # Warm-up runs are deliberately not included in the measured dataset.
    for i in range(settings.warmup_runs):
        print(f"Warm-up {i + 1}/{settings.warmup_runs}...")
        generate(model=model.name, prompt=args.prompt, settings=settings.generation)

    output = run_log(args)
    run_id = new_run_id()
    print(f"Run ID: {run_id}")
    records = []

    for i in range(settings.repeats):
        print(f"Measured run {i + 1}/{settings.repeats}...")
        result = generate(model=model.name, prompt=args.prompt, settings=settings.generation)
        record = {
            "timestamp": utc_timestamp(),
            "run_id": run_id,
            "run_type": "benchmark",
            "run_index": i + 1,
            **run_fields(settings, model),
            **result.to_dict(),
        }
        append_jsonl(output, record)
        records.append(record)

    print("\n--- SUMMARY ---")
    print(json.dumps(run_summary(run_id, records), indent=2))
    print(f"\nRaw results: {output}")
    print(f"Summarize it again with: local-ai-benchmark summarize --run-id {run_id}")


def summarize_command(args: argparse.Namespace) -> None:
    records = read_jsonl(run_log(args))
    if args.list:
        for run in benchmark_runs(records):
            print(f"{run.run_id}  {run.model}  {run.runs} runs  {run.started}")
        return
    run_id, selected = select_run(records, args.run_id)
    print(json.dumps(run_summary(run_id, selected), indent=2))


def _common_flags() -> argparse.ArgumentParser:
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
    files = common.add_argument_group("files")
    files.add_argument(
        "--config", type=Path, help="settings file (default: configs/benchmark.yaml)"
    )
    files.add_argument("--models", type=Path, help="model registry (default: configs/models.yaml)")
    files.add_argument("--output", type=Path, help=OUTPUT_HELP)
    return common


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
    p_bench.set_defaults(func=benchmark)

    p_sum = sub.add_parser("summarize", help="rebuild a benchmark's summary from the run log")
    p_sum.add_argument("--run-id", help="the benchmark to summarize (default: the latest)")
    p_sum.add_argument("--list", action="store_true", help="list the benchmarks in the log")
    p_sum.add_argument("--output", type=Path, help="run log to read (default: as for benchmark)")
    p_sum.set_defaults(func=summarize_command)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (ConfigError, RunLogError) as exc:
        parser.exit(2, f"local-ai-benchmark: error: {exc}\n")
    except preflight.PreflightError as exc:
        parser.exit(3, f"local-ai-benchmark: error: {exc}\n")


if __name__ == "__main__":
    main()
