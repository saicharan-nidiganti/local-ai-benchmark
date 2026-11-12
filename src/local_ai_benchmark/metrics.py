"""The run log: append records, read them back, group them by run ID, and summarize them."""

from __future__ import annotations

import json
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median, quantiles
from typing import Any

Record = dict[str, Any]

# Metrics a summary describes, in the order they are printed.
SUMMARY_METRICS = (
    "total_latency_ms",
    "ttft_ms",
    "tokens_per_sec",
    "prefill_tokens_per_sec",
    "peak_runtime_rss_mb",
    "peak_gpu_memory_mb",
    "mean_gpu_power_w",
    "gpu_energy_j",
    "gpu_offload_pct",
)


class RunLogError(ValueError):
    """The run log is missing, unreadable, or has no run with the requested ID."""


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def new_run_id(now: datetime | None = None) -> str:
    """Sortable by time, unique within a second: `20261113T061512Z-3fa9c2`."""
    moment = now or datetime.now(UTC)
    return f"{moment:%Y%m%dT%H%M%SZ}-{secrets.token_hex(3)}"


def append_jsonl(path: str | Path, record: Record) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[Record]:
    path = Path(path)
    if not path.is_file():
        raise RunLogError(f"no run log at {path}")
    records = []
    with path.open(encoding="utf-8") as f:
        for number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RunLogError(f"{path}:{number}: not valid JSON ({exc.msg})") from exc
    return records


def spread(values: list[float]) -> dict[str, float]:
    """Order statistics of one metric. Quantiles use the inclusive method, so p90 of five runs
    lies between the two slowest rather than beyond them."""
    ordered = sorted(values)
    if len(ordered) == 1:
        only = ordered[0]
        return {"n": 1, "min": only, "p50": only, "p90": only, "max": only, "iqr": 0.0}
    deciles = quantiles(ordered, n=10, method="inclusive")
    quartiles = quantiles(ordered, n=4, method="inclusive")
    return {
        "n": len(ordered),
        "min": ordered[0],
        "p50": median(ordered),
        "p90": deciles[8],
        "max": ordered[-1],
        "iqr": quartiles[2] - quartiles[0],
    }


def summarize(records: Iterable[Record]) -> Record:
    rows = list(records)
    successful = [r for r in rows if not r.get("error")]

    if not successful:
        return {
            "runs": len(rows),
            "successful_runs": 0,
            "error_rate": 1.0 if rows else 0.0,
        }

    def vals(key: str) -> list[float]:
        return [r[key] for r in successful if r.get(key) is not None]

    def middle(key: str) -> float | None:
        values = vals(key)
        return median(values) if values else None

    return {
        "runs": len(rows),
        "successful_runs": len(successful),
        "error_rate": (len(rows) - len(successful)) / len(rows),
        "median_total_latency_ms": middle("total_latency_ms"),
        "median_ttft_ms": middle("ttft_ms"),
        "median_tokens_per_sec": middle("tokens_per_sec"),
        "median_prefill_tokens_per_sec": middle("prefill_tokens_per_sec"),
        "stats": {key: spread(vals(key)) for key in SUMMARY_METRICS if vals(key)},
    }


def run_summary(run_id: str, records: list[Record]) -> Record:
    """The summary `benchmark` prints and `summarize` rebuilds from the log."""
    return {
        "run_id": run_id,
        "model": records[0].get("model") if records else None,
        **summarize(records),
    }


@dataclass(frozen=True)
class RunInfo:
    run_id: str
    model: str | None
    started: str | None
    runs: int


def benchmark_runs(records: Iterable[Record]) -> list[RunInfo]:
    """Benchmark run IDs in the log, oldest first."""
    seen: dict[str, list[Record]] = {}
    for record in records:
        run_id = record.get("run_id")
        if record.get("run_type") == "benchmark" and run_id:
            seen.setdefault(run_id, []).append(record)
    return [
        RunInfo(run_id, group[0].get("model"), group[0].get("timestamp"), len(group))
        for run_id, group in seen.items()
    ]


def select_run(records: list[Record], run_id: str | None) -> tuple[str, list[Record]]:
    """The measured records of one benchmark; the most recent one when no ID is given."""
    runs = benchmark_runs(records)
    if not runs:
        raise RunLogError("the run log has no benchmark runs with a run ID")
    chosen = run_id or runs[-1].run_id
    selected = [
        r for r in records if r.get("run_id") == chosen and r.get("run_type") == "benchmark"
    ]
    if not selected:
        raise RunLogError(f"no benchmark run with ID {chosen}")
    return chosen, selected
