"""Command-line interface: `ask` and `benchmark`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inference import generate
from .metrics import append_jsonl, summarize, utc_timestamp
from .paths import default_run_log

OUTPUT_HELP = "run log to append to (default: data/raw/runs.jsonl in the project folder)"


def run_log(args: argparse.Namespace) -> Path:
    return Path(args.output) if args.output else default_run_log()


def ask(args: argparse.Namespace) -> None:
    result = generate(
        model=args.model,
        prompt=args.prompt,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
    )

    print("\n--- RESPONSE ---")
    print(result.response or "[no response]")
    print("\n--- METRICS ---")
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    record = {
        "timestamp": utc_timestamp(),
        "run_type": "single",
        **result.to_dict(),
    }
    output = run_log(args)
    append_jsonl(output, record)
    print(f"\nSaved: {output}")


def benchmark(args: argparse.Namespace) -> None:
    # Warm-up runs are deliberately not included in the measured dataset.
    for i in range(args.warmup_runs):
        print(f"Warm-up {i + 1}/{args.warmup_runs}...")
        generate(
            model=args.model,
            prompt=args.prompt,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )

    output = run_log(args)
    records = []

    for i in range(args.repeats):
        print(f"Measured run {i + 1}/{args.repeats}...")
        result = generate(
            model=args.model,
            prompt=args.prompt,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )
        record = {
            "timestamp": utc_timestamp(),
            "run_type": "benchmark",
            "run_index": i + 1,
            "temperature": args.temperature,
            "max_output_tokens": args.max_output_tokens,
            **result.to_dict(),
        }
        append_jsonl(output, record)
        records.append(record)

    print("\n--- SUMMARY ---")
    print(json.dumps(summarize(records), indent=2))
    print(f"\nRaw results: {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-ai-benchmark",
        description="Offline local AI assistant and benchmark runner",
    )
    sub = parser.add_subparsers(required=True)

    p_ask = sub.add_parser("ask")
    p_ask.add_argument("--model", required=True)
    p_ask.add_argument("--prompt", required=True)
    p_ask.add_argument("--temperature", type=float, default=0.0)
    p_ask.add_argument("--max-output-tokens", type=int, default=256)
    p_ask.add_argument("--output", type=Path, default=None, help=OUTPUT_HELP)
    p_ask.set_defaults(func=ask)

    p_bench = sub.add_parser("benchmark")
    p_bench.add_argument("--model", required=True)
    p_bench.add_argument("--prompt", required=True)
    p_bench.add_argument("--repeats", type=int, default=5)
    p_bench.add_argument("--warmup-runs", type=int, default=1)
    p_bench.add_argument("--temperature", type=float, default=0.0)
    p_bench.add_argument("--max-output-tokens", type=int, default=256)
    p_bench.add_argument("--output", type=Path, default=None, help=OUTPUT_HELP)
    p_bench.set_defaults(func=benchmark)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
