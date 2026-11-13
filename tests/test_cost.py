"""Cost per million output tokens and per 1,000 tasks, from synthetic runs."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from local_ai_benchmark import cost
from local_ai_benchmark.config import ConfigError

REPO = Path(__file__).resolve().parents[1]
SOURCED = {"source": "https://example.com", "as_of": date(2026, 11, 13)}


def assumptions(hosted=True):
    return cost.CostAssumptions(
        currency="INR",
        electricity=cost.Electricity(price_per_kwh=10.0, **SOURCED),
        hardware=cost.Hardware(price=8760.0, lifetime_years=1, hours_per_day=24, **SOURCED),
        exchange=cost.Exchange(usd_to_local=100.0, **SOURCED),
        hosted=(
            {
                "m": cost.HostedPrice(
                    provider="P", input_per_million_usd=1.0, output_per_million_usd=2.0, **SOURCED
                )
            }
            if hosted
            else {}
        ),
    )


def task(energy=36.0, error=None):
    return {"output_tokens": 100, "prompt_tokens": 300, "gpu_energy_j": energy,
            "total_latency_ms": 1000.0, "error": error}  # fmt: skip


def test_the_projects_cost_assumptions_are_valid_and_sourced():
    loaded = cost.load_cost(REPO / "configs" / "cost.yaml")

    assert loaded.currency == "INR"
    assert set(loaded.hosted) == {"qwen3:4b-instruct", "phi4-mini", "llama3.2:3b"}
    assert all(h.source.startswith("https://") for h in loaded.hosted.values())


def test_electricity_hardware_and_hosted_cost_follow_from_the_measurements():
    found = cost.cost_of([task(), task()], "m", assumptions())

    assert found is not None
    # 72 J is 2e-5 kWh, 0.0002 at 10 a kWh, over 200 output tokens
    assert found.electricity_per_million == pytest.approx(1.0)
    # 2 s at 1 an hour (8,760 over a year of every hour), over 200 output tokens
    assert found.hardware_per_million == pytest.approx(2 / 3600 * 5000)
    assert found.local_per_million == pytest.approx(1.0 + 2 / 3600 * 5000)
    assert found.electricity_per_1000_tasks == pytest.approx(0.1)
    assert found.hosted_per_million_output == pytest.approx(200.0)
    # (600 input x 1 + 200 output x 2) / 1e6 USD x 100, over 2 tasks, times 1,000
    assert found.hosted_per_1000_tasks == pytest.approx(50.0)
    assert found.record()["hosted_provider"] == "P"


def test_failed_tasks_are_left_out():
    found = cost.cost_of([task(), task(error="timeout")], "m", assumptions())

    assert found is not None
    assert found.tasks == 1
    assert found.output_tokens == 100


def test_a_model_without_a_hosted_price_gets_local_cost_only():
    found = cost.cost_of([task()], "m", assumptions(hosted=False))

    assert found is not None
    assert found.hosted is None
    assert found.hosted_per_million_output is None
    assert found.hosted_per_1000_tasks is None


def test_runs_without_energy_or_tokens_have_no_cost():
    assert cost.cost_of([task(energy=None)], "m", assumptions()) is None
    assert cost.cost_of([{**task(), "output_tokens": 0}], "m", assumptions()) is None
    assert cost.cost_of([], "m", assumptions()) is None


def test_a_bad_assumptions_file_names_the_field(tmp_path):
    path = tmp_path / "cost.yaml"
    path.write_text(
        "currency: INR\nelectricity: {price_per_kwh: -1, source: x, as_of: 2026-11-13}\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match=r"electricity.price_per_kwh") as info:
        cost.load_cost(path)

    assert "hardware" in str(info.value)  # every missing section is named too
