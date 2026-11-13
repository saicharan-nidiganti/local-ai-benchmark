"""Comparison report: suite runs of several models side by side, written as a results folder
(README.md with tables, a quality-against-speed chart as SVG, summaries and manifests)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from html import escape
from pathlib import Path
from statistics import fmean, median
from typing import Any

from .metrics import Record, suite_summary
from .suite import CATEGORIES, TASK_KINDS, Suite

# A model is "close enough" to the most accurate one when its overall quality is within this.
TRADEOFF_MARGIN = 0.05


class ReportError(ValueError):
    """The requested runs cannot be compared."""


@dataclass(frozen=True)
class ModelResult:
    run_id: str
    model: str
    summary: Record
    manifest: Record | None
    by_category: dict[str, float]
    latency_by_task: dict[str, float]

    @property
    def quality(self) -> float:
        return float(self.summary["quality"]["overall"] or 0.0)

    @property
    def decode_speed(self) -> float:
        return float(self.summary["speed"].get("median_tokens_per_sec") or 0.0)

    def stat(self, metric: str, key: str = "p50") -> float | None:
        value = self.summary["speed"].get("stats", {}).get(metric, {}).get(key)
        return None if value is None else float(value)


def model_result(
    run_id: str, records: list[Record], suite: Suite, manifest: Record | None
) -> ModelResult:
    if not records or records[0].get("run_type") != "suite":
        raise ReportError(f"run {run_id} is not a suite run")
    category_of = {t.id: t.expected.category for t in suite.tickets}
    by_category = {
        category: fmean(
            float(r.get("score") or 0.0)
            for r in records
            if category_of.get(str(r.get("ticket_id"))) == category
        )
        for category in CATEGORIES
        if any(category_of.get(str(r.get("ticket_id"))) == category for r in records)
    }
    latency_by_task: dict[str, float] = {
        kind: median(float(r["total_latency_ms"]) for r in records if r.get("task") == kind)
        for kind in TASK_KINDS
        if any(r.get("task") == kind for r in records)
    }
    return ModelResult(
        run_id=run_id,
        model=str(records[0].get("model")),
        summary=suite_summary(run_id, records),
        manifest=manifest,
        by_category=by_category,
        latency_by_task=latency_by_task,
    )


@dataclass(frozen=True)
class Verdict:
    fastest: str
    most_accurate: str
    best_tradeoff: str


def verdict(results: list[ModelResult]) -> Verdict:
    """Fastest by median decode speed; most accurate by overall quality; best tradeoff is the
    fastest model whose quality is within TRADEOFF_MARGIN of the most accurate one."""
    fastest = max(results, key=lambda r: r.decode_speed)
    accurate = max(results, key=lambda r: r.quality)
    close = [r for r in results if r.quality >= accurate.quality - TRADEOFF_MARGIN]
    tradeoff = max(close, key=lambda r: r.decode_speed)
    return Verdict(fastest.model, accurate.model, tradeoff.model)


def _fmt(value: float | None, digits: int = 1, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:,.{digits}f}{suffix}"


CHAR_WIDTH = 7.2  # estimated width of one character of a 13 px sans-serif label
Box = tuple[float, float, float, float]  # left, top, right, bottom


def _overlaps(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def place_labels(
    points: list[tuple[float, float, str]], bounds: Box
) -> list[tuple[float, float, str]]:
    """A position and anchor for each point's label: above right of the point if that is free,
    otherwise below right, above left or below left, so close points keep readable labels."""
    taken: list[Box] = [(px - 8, py - 8, px + 8, py + 8) for px, py, _ in points]
    placed = []
    for px, py, text in points:
        width = len(text) * CHAR_WIDTH
        options = [(11, -9, "start"), (11, 20, "start"), (-11, -9, "end"), (-11, 20, "end")]
        choice = None
        for dx, dy, anchor in options:
            lx, ly = px + dx, py + dy
            box = (
                (lx, ly - 12, lx + width, ly + 3)
                if anchor == "start"
                else (lx - width, ly - 12, lx, ly + 3)
            )
            inside = bounds[0] <= box[0] and box[2] <= bounds[2] and bounds[1] <= box[1]
            if inside and box[3] <= bounds[3] and not any(_overlaps(box, t) for t in taken):
                choice = (lx, ly, anchor, box)
                break
        if choice is None:  # nowhere free: keep the first option
            lx, ly = px + 11, py - 9
            choice = (lx, ly, "start", (lx, ly - 12, lx + width, ly + 3))
        taken.append(choice[3])
        placed.append((choice[0], choice[1], choice[2]))
    return placed


def quality_axis(results: list[ModelResult]) -> tuple[float, float, float]:
    """Lower end, upper end and grid step of the quality axis: zoomed to the data in steps of
    0.1, always ending at 1, so close scores stay apart without hiding where 1 is."""
    lowest = min(r.quality for r in results)
    low = max(0.0, math.floor((lowest - TRADEOFF_MARGIN) * 10) / 10)
    return low, 1.0, 0.1 if 1.0 - low <= 0.5 else 0.25


def quality_speed_svg(results: list[ModelResult]) -> str:
    """A scatter of overall quality against decode speed, one labelled point per model, with
    the band of models within TRADEOFF_MARGIN of the best quality shaded."""
    width, height, left, right, top, bottom = 640, 400, 70, 30, 30, 60
    plot_w, plot_h = width - left - right, height - top - bottom
    max_speed = max(r.decode_speed for r in results) * 1.2 or 1.0
    low, high, grid = quality_axis(results)
    best = max(r.quality for r in results)

    def x(speed: float) -> float:
        return left + speed / max_speed * plot_w

    def y(quality: float) -> float:
        return top + (high - quality) / (high - low) * plot_h

    band_top, band_bottom = y(best), y(max(low, best - TRADEOFF_MARGIN))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="sans-serif" font-size="13">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<rect x="{left}" y="{band_top:.1f}" width="{plot_w}" '
        f'height="{band_bottom - band_top:.1f}" fill="#dbeafe"/>',
        f'<text x="{width - right - 6}" y="{band_bottom - 6:.1f}" text-anchor="end" '
        f'fill="#1e40af" font-size="11">within {TRADEOFF_MARGIN:.2f} of the best quality</text>',
    ]
    steps = round((high - low) / grid)
    for i in range(steps + 1):
        q = low + i * grid
        parts.append(
            f'<line x1="{left}" y1="{y(q):.1f}" x2="{width - right}" y2="{y(q):.1f}" '
            'stroke="#e5e5e5"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y(q) + 4:.1f}" text-anchor="end" fill="#555">{q:.2f}</text>'
        )
    step = 10 if max_speed > 40 else 5
    for s in range(0, int(max_speed) + 1, step):
        parts.append(
            f'<text x="{x(s):.1f}" y="{height - bottom + 18}" text-anchor="middle" '
            f'fill="#555">{s}</text>'
        )
    parts += [
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" '
        'stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#333"/>',
        f'<text x="{left + plot_w / 2}" y="{height - 15}" text-anchor="middle" fill="#222">'
        "Median decode speed (tokens/s)</text>",
        f'<text transform="translate(18 {top + plot_h / 2}) rotate(-90)" text-anchor="middle" '
        'fill="#222">Overall quality (0 to 1)</text>',
    ]
    points = [(x(r.decode_speed), y(r.quality), r.model) for r in results]
    labels = place_labels(points, (left, top, width - right, height - bottom))
    for (cx, cy, name), (lx, ly, anchor) in zip(points, labels, strict=True):
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="#2563eb"/>')
        parts.append(
            f'<text class="label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'fill="#111">{escape(name)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_markdown(results: list[ModelResult], title: str, chart_name: str) -> str:
    v = verdict(results)
    first = results[0].summary
    lines = [
        f"# {title}",
        "",
        f"Suite `{first['suite']}` ({first['tasks']} tasks), {_mode_phrase(results)}, "
        "one run per task after a warm-up, same machine and settings for every model.",
        "",
        f"- **Most accurate:** {v.most_accurate}",
        f"- **Fastest:** {v.fastest}",
        f"- **Best tradeoff:** {v.best_tradeoff} (the fastest model within "
        f"{TRADEOFF_MARGIN:.2f} of the best quality)",
        "",
        f"![Overall quality against median decode speed]({chart_name})",
        "",
        "## Quality",
        "",
        "| Model | JSON mode | Overall | Classify | Extract | Summarize | Valid JSON "
        "| Schema-valid |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        q, j = r.summary["quality"], r.summary["json"]
        lines.append(
            f"| {r.model} | {r.summary.get('json_mode') or 'n/a'} | "
            f"{_fmt(q['overall'], 2)} | {_fmt(q.get('classify'), 2)} | "
            f"{_fmt(q.get('extract'), 2)} | {_fmt(q.get('summarize'), 2)} | "
            f"{_fmt(_pct(j['valid_rate']), 0, '%')} | "
            f"{_fmt(_pct(j['schema_valid_rate']), 0, '%')} |"
        )
    lines += [
        "",
        "Quality by ticket category (mean over each ticket's three tasks):",
        "",
        "| Model | " + " | ".join(c.capitalize() for c in CATEGORIES) + " |",
        "| --- | " + " | ".join("---" for _ in CATEGORIES) + " |",
    ]
    for r in results:
        cells = " | ".join(_fmt(r.by_category.get(c), 2) for c in CATEGORIES)
        lines.append(f"| {r.model} | {cells} |")
    lines += [
        "",
        "## Speed and resources",
        "",
        "| Model | Decode (tokens/s) | Prefill (tokens/s) | TTFT p50 (ms) | Latency p50 / p90 (ms) "
        "| On GPU | Peak GPU memory (MiB) | Mean GPU power (W) | GPU energy per task (J) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        lines.append(
            f"| {r.model} | {_fmt(r.decode_speed)} | {_fmt(r.stat('prefill_tokens_per_sec'), 0)} | "
            f"{_fmt(r.stat('ttft_ms'), 0)} | {_fmt(r.stat('total_latency_ms'), 0)} / "
            f"{_fmt(r.stat('total_latency_ms', 'p90'), 0)} | "
            f"{_fmt(r.stat('gpu_offload_pct'), 0, '%')} | "
            f"{_fmt(r.stat('peak_gpu_memory_mb'), 0)} | "
            f"{_fmt(r.stat('mean_gpu_power_w'))} | {_fmt(r.stat('gpu_energy_j'), 0)} |"
        )
    lines += [
        "",
        "Median latency per task kind (ms):",
        "",
        "| Model | " + " | ".join(k.capitalize() for k in TASK_KINDS) + " |",
        "| --- | " + " | ".join("---" for _ in TASK_KINDS) + " |",
    ]
    for r in results:
        cells = " | ".join(_fmt(r.latency_by_task.get(k), 0) for k in TASK_KINDS)
        lines.append(f"| {r.model} | {cells} |")
    lines += [
        "",
        "## Runs",
        "",
        "| Model | Run ID | Digest | Quantization | Ollama | Harness commit |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        model, runtime_info, harness = (
            _section(r.manifest, "model"),
            _section(r.manifest, "runtime"),
            _section(r.manifest, "harness"),
        )
        lines.append(
            f"| {r.model} | `{r.run_id}` | `{str(model.get('digest') or 'n/a')[:12]}` | "
            f"{model.get('quantization') or 'n/a'} | {runtime_info.get('version') or 'n/a'} | "
            f"`{str(harness.get('git_sha') or 'n/a')[:7]}` |"
        )
    lines += [
        "",
        "Exact values: [summaries.json](summaries.json). "
        "Environments: [manifests.json](manifests.json).",
        "",
    ]
    return "\n".join(lines)


def _mode_phrase(results: list[ModelResult]) -> str:
    modes = {r.summary.get("json_mode") for r in results}
    return f"JSON mode `{modes.pop()}`" if len(modes) == 1 else "JSON mode per model below"


def _section(manifest: Record | None, key: str) -> dict[str, Any]:
    """A manifest section, or an empty one when the manifest lacks it."""
    value = (manifest or {}).get(key)
    return value if isinstance(value, dict) else {}


def _pct(rate: float | None) -> float | None:
    return None if rate is None else rate * 100


def write_report(results: list[ModelResult], out_dir: Path, title: str) -> Path:
    if len(results) < 2:
        raise ReportError("a comparison needs at least two suite runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    chart = "quality_vs_speed.svg"
    (out_dir / chart).write_text(quality_speed_svg(results), encoding="utf-8", newline="\n")
    (out_dir / "README.md").write_text(
        render_markdown(results, title, chart), encoding="utf-8", newline="\n"
    )
    _write_json(out_dir / "summaries.json", [r.summary for r in results])
    _write_json(out_dir / "manifests.json", [r.manifest for r in results])
    return out_dir / "README.md"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
