"""Run-log persistence and summary statistics."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

Record = dict[str, Any]


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def append_jsonl(path: str | Path, record: Record) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


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

    latency = vals("total_latency_ms")
    ttft = vals("ttft_ms")
    tps = vals("tokens_per_sec")

    return {
        "runs": len(rows),
        "successful_runs": len(successful),
        "error_rate": (len(rows) - len(successful)) / len(rows),
        "median_total_latency_ms": median(latency) if latency else None,
        "median_ttft_ms": median(ttft) if ttft else None,
        "median_tokens_per_sec": median(tps) if tps else None,
    }
