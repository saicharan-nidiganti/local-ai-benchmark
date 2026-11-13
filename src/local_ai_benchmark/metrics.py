"""The run log: append records, read them back, group them by run ID, and summarize them."""

from __future__ import annotations

import json
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, median, quantiles
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


# Run types whose records are measured, grouped by run ID and summarized.
MEASURED_RUN_TYPES = ("benchmark", "suite")
TASK_KINDS = ("classify", "extract", "summarize")


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
    # Older runs predate the connection audit; their summaries stay as they were.
    audited = [r["remote_connections"] for r in rows if r.get("remote_connections") is not None]
    network = {"remote_connections": sum(audited)} if audited else {}

    if not successful:
        return {
            "runs": len(rows),
            "successful_runs": 0,
            "error_rate": 1.0 if rows else 0.0,
            **network,
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
        **network,
    }


def run_summary(run_id: str, records: list[Record]) -> Record:
    """The summary `benchmark` prints and `summarize` rebuilds from the log."""
    start = records[0].get("start") if records else None
    return {
        "run_id": run_id,
        "model": records[0].get("model") if records else None,
        **({"start": start} if start else {}),  # older runs have no start field
        **summarize(records),
    }


def _mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


def _rate(records: list[Record], key: str) -> float | None:
    known = [bool(r[key]) for r in records if r.get(key) is not None]
    return sum(known) / len(known) if known else None


def suite_summary(run_id: str, records: list[Record]) -> Record:
    """Quality per task kind and JSON reliability, beside the speed summary. A failed run
    scores 0: an answer that never arrived is a wrong answer."""
    scores = [float(r.get("score") or 0.0) for r in records]
    structured = [r for r in records if r.get("task") in ("classify", "extract")]
    return {
        "run_id": run_id,
        "model": records[0].get("model") if records else None,
        "suite": records[0].get("suite") if records else None,
        "json_mode": next((r["json_mode"] for r in structured if r.get("json_mode")), None),
        "tasks": len(records),
        "quality": {
            "overall": _mean(scores),
            **{
                kind: _mean(
                    [float(r.get("score") or 0.0) for r in records if r.get("task") == kind]
                )
                for kind in TASK_KINDS
            },
        },
        "json": {
            "strict_rate": _rate(structured, "json_strict"),
            "valid_rate": _rate(structured, "json_valid"),
            "schema_valid_rate": _rate(structured, "schema_valid"),
            **_repairs(structured),
        },
        "speed": summarize(records),
    }


def _repairs(structured: list[Record]) -> Record:
    """First-attempt validity and what bounded repair added; empty for runs without repair."""
    tried = [r for r in structured if r.get("repair_attempts") is not None]
    if not tried:
        return {}
    attempts = [int(r["repair_attempts"]) for r in tried]
    return {
        "first_attempt_valid_rate": _rate(tried, "first_json_valid"),
        "first_attempt_schema_valid_rate": _rate(tried, "first_schema_valid"),
        "repair_rate": sum(1 for a in attempts if a > 0) / len(tried),
        "repair_attempts": sum(attempts),
        "first_attempt_quality": _mean([float(r.get("first_score") or 0.0) for r in tried]),
        "final_quality": _mean([float(r.get("score") or 0.0) for r in tried]),
        "repair_ms": round(sum(float(r.get("repair_ms") or 0.0) for r in tried), 1),
    }


def summary_of(run_id: str, records: list[Record]) -> Record:
    """The summary that matches the run's type."""
    if records and records[0].get("run_type") == "suite":
        return suite_summary(run_id, records)
    return run_summary(run_id, records)


@dataclass(frozen=True)
class RunInfo:
    run_id: str
    model: str | None
    started: str | None
    runs: int
    run_type: str = "benchmark"


def benchmark_runs(records: Iterable[Record]) -> list[RunInfo]:
    """Benchmark and suite run IDs in the log, oldest first."""
    seen: dict[str, list[Record]] = {}
    for record in records:
        run_id = record.get("run_id")
        if record.get("run_type") in MEASURED_RUN_TYPES and run_id:
            seen.setdefault(run_id, []).append(record)
    return [
        RunInfo(
            run_id,
            group[0].get("model"),
            group[0].get("timestamp"),
            len(group),
            str(group[0].get("run_type")),
        )
        for run_id, group in seen.items()
    ]


def select_run(records: list[Record], run_id: str | None) -> tuple[str, list[Record]]:
    """The measured records of one run; the most recent one when no ID is given."""
    runs = benchmark_runs(records)
    if not runs:
        raise RunLogError("the run log has no benchmark or suite runs with a run ID")
    chosen = run_id or runs[-1].run_id
    selected = [
        r for r in records if r.get("run_id") == chosen and r.get("run_type") in MEASURED_RUN_TYPES
    ]
    if not selected:
        raise RunLogError(f"no benchmark or suite run with ID {chosen}")
    return chosen, selected
