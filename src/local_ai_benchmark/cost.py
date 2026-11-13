"""What local inference costs per million output tokens and per 1,000 tasks, from the energy
and time measured in a suite run and the stated assumptions in configs/cost.yaml, beside the
price of the same model on a hosted API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import ConfigError, _read_yaml
from .metrics import Record

JOULES_PER_KWH = 3.6e6
MILLION = 1_000_000


class _Sourced(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    as_of: date
    note: str = ""


class Electricity(_Sourced):
    price_per_kwh: float = Field(gt=0)


class Hardware(_Sourced):
    price: float = Field(ge=0)
    lifetime_years: float = Field(gt=0)
    hours_per_day: float = Field(gt=0, le=24)

    @property
    def per_hour(self) -> float:
        """The purchase price spread evenly over every hour of use in its lifetime."""
        return self.price / (self.lifetime_years * 365 * self.hours_per_day)


class Exchange(_Sourced):
    usd_to_local: float = Field(gt=0)


class HostedPrice(_Sourced):
    provider: str = Field(min_length=1)
    input_per_million_usd: float = Field(ge=0)
    output_per_million_usd: float = Field(ge=0)


class CostAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = Field(min_length=1)
    electricity: Electricity
    hardware: Hardware
    exchange: Exchange
    hosted: dict[str, HostedPrice] = Field(default_factory=dict)


def load_cost(path: Path) -> CostAssumptions:
    try:
        return CostAssumptions.model_validate(_read_yaml(path))
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}" for error in exc.errors()
        )
        raise ConfigError(f"{path}: {problems}") from exc


@dataclass(frozen=True)
class Cost:
    """Costs in the assumptions' currency. Local cost is electricity (GPU board energy only)
    plus the hardware's purchase price per hour of use; hosted cost is the provider's price."""

    tasks: int
    prompt_tokens: int
    output_tokens: int
    gpu_energy_j: float
    busy_s: float
    electricity_per_million: float
    hardware_per_million: float
    electricity_per_1000_tasks: float
    hardware_per_1000_tasks: float
    hosted: HostedPrice | None
    hosted_per_million_output: float | None
    hosted_per_1000_tasks: float | None

    @property
    def local_per_million(self) -> float:
        return self.electricity_per_million + self.hardware_per_million

    @property
    def local_per_1000_tasks(self) -> float:
        return self.electricity_per_1000_tasks + self.hardware_per_1000_tasks

    def record(self) -> Record:
        return {
            "tasks": self.tasks,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "gpu_energy_j": round(self.gpu_energy_j, 1),
            "busy_s": round(self.busy_s, 1),
            "electricity_per_million": round(self.electricity_per_million, 4),
            "hardware_per_million": round(self.hardware_per_million, 4),
            "local_per_million": round(self.local_per_million, 4),
            "hosted_per_million_output": _round(self.hosted_per_million_output),
            "electricity_per_1000_tasks": round(self.electricity_per_1000_tasks, 4),
            "local_per_1000_tasks": round(self.local_per_1000_tasks, 4),
            "hosted_per_1000_tasks": _round(self.hosted_per_1000_tasks),
            "hosted_provider": self.hosted.provider if self.hosted else None,
        }


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def cost_of(records: list[Record], model: str, assumptions: CostAssumptions) -> Cost | None:
    """The cost of a suite run's workload, or None when its energy or tokens were not
    recorded. All successful tasks count, prefill included: the energy and time of reading
    the prompt are part of what each output token costs."""
    done = [r for r in records if not r.get("error")]
    if not done or any(r.get("gpu_energy_j") is None for r in done):
        return None
    output_tokens = sum(int(r.get("output_tokens") or 0) for r in done)
    if output_tokens == 0:
        return None
    prompt_tokens = sum(int(r.get("prompt_tokens") or 0) for r in done)
    energy_j = sum(float(r["gpu_energy_j"]) for r in done)
    busy_s = sum(float(r.get("total_latency_ms") or 0.0) for r in done) / 1000

    def electricity(joules: float) -> float:
        return joules / JOULES_PER_KWH * assumptions.electricity.price_per_kwh

    def hardware(seconds: float) -> float:
        return seconds / 3600 * assumptions.hardware.per_hour

    per_token, per_task = MILLION / output_tokens, 1000 / len(done)
    hosted = assumptions.hosted.get(model)
    fx = assumptions.exchange.usd_to_local
    hosted_per_task = (
        None
        if hosted is None
        else (
            prompt_tokens * hosted.input_per_million_usd
            + output_tokens * hosted.output_per_million_usd
        )
        / MILLION
        * fx
        / len(done)
    )
    return Cost(
        tasks=len(done),
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        gpu_energy_j=energy_j,
        busy_s=busy_s,
        electricity_per_million=electricity(energy_j) * per_token,
        hardware_per_million=hardware(busy_s) * per_token,
        electricity_per_1000_tasks=electricity(energy_j) * per_task,
        hardware_per_1000_tasks=hardware(busy_s) * per_task,
        hosted=hosted,
        hosted_per_million_output=None if hosted is None else hosted.output_per_million_usd * fx,
        hosted_per_1000_tasks=None if hosted_per_task is None else hosted_per_task * 1000,
    )
