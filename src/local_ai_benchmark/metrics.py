from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Iterable


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: str | Path, record: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def summarize(records: Iterable[dict]) -> dict:
    records = list(records)
    successful = [r for r in records if not r.get("error")]

    if not successful:
        return {
            "runs": len(records),
            "successful_runs": 0,
            "error_rate": 1.0 if records else 0.0,
        }

    def vals(key: str):
        return [r[key] for r in successful if r.get(key) is not None]

    latency = vals("total_latency_ms")
    ttft = vals("ttft_ms")
    tps = vals("tokens_per_sec")

    return {
        "runs": len(records),
        "successful_runs": len(successful),
        "error_rate": (len(records) - len(successful)) / len(records),
        "median_total_latency_ms": median(latency) if latency else None,
        "median_ttft_ms": median(ttft) if ttft else None,
        "median_tokens_per_sec": median(tps) if tps else None,
    }
