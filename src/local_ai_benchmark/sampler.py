"""Resource use while a request runs: RAM, the runtime's memory, GPU memory and GPU power,
sampled in a background thread."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from statistics import fmean
from types import TracebackType
from typing import Any, Protocol

import psutil

from .runtime import is_loopback

MB = 2**20

# The Ollama server, and the model runner it starts: `llama-server` on Windows (0.40), the
# `ollama` binary itself (`ollama runner`) on Linux.
RUNTIME_PROCESS_PREFIXES = ("ollama", "llama-server")


@dataclass(frozen=True)
class Sample:
    at: float  # perf_counter seconds
    system_ram_used_mb: float
    runtime_rss_mb: float | None
    gpu_memory_used_mb: float | None
    gpu_power_w: float | None
    remote_endpoints: frozenset[str] | None = None  # None: the table could not be read


class GpuProbe(Protocol):
    def read(self) -> tuple[float | None, float | None] | None:
        """(memory used in MB, power draw in W), or None when no GPU can be read."""


class NvidiaSmi:
    """Reads the first NVIDIA GPU through `nvidia-smi`."""

    def __init__(self) -> None:
        self.program = shutil.which("nvidia-smi")

    def read(self) -> tuple[float | None, float | None] | None:
        if self.program is None:
            return None
        try:
            done = subprocess.run(  # noqa: S603 - fixed arguments, no shell, program found on PATH
                [
                    self.program,
                    "--query-gpu=memory.used,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        first = done.stdout.strip().splitlines()[:1]
        if not first:
            return None
        parts = [part.strip() for part in first[0].split(",")]
        return (_number(parts[0]), _number(parts[1]) if len(parts) > 1 else None)


def _number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:  # "[N/A]" on GPUs that do not report a value
        return None


def system_ram_used_mb() -> float:
    return psutil.virtual_memory().used / MB


def runtime_rss_mb() -> float | None:
    """Resident memory of the Ollama server and its model runner together: the model's share
    that is not on the GPU shows up here."""
    total = 0
    found = False
    for proc in psutil.process_iter(["name", "memory_info"]):
        name = (proc.info.get("name") or "").lower()
        memory = proc.info.get("memory_info")
        if name.startswith(RUNTIME_PROCESS_PREFIXES) and memory is not None:
            total += memory.rss
            found = True
    return total / MB if found else None


def runtime_pids() -> set[int]:
    return {
        proc.pid
        for proc in psutil.process_iter(["name"])
        if (proc.info.get("name") or "").lower().startswith(RUNTIME_PROCESS_PREFIXES)
    }


def remote_endpoints() -> frozenset[str] | None:
    """Open connections from the Ollama server, its model runner or this process to any other
    machine, as `address:port`. Loopback is this machine; anything else, a LAN address
    included, is another. None when the connection table cannot be read."""
    pids = runtime_pids() | {os.getpid()}
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.Error, OSError):
        return None
    return frozenset(
        f"{conn.raddr.ip}:{conn.raddr.port}"
        for conn in connections
        if conn.pid in pids and conn.raddr and not is_loopback(conn.raddr.ip)
    )


@dataclass(frozen=True)
class ResourceSummary:
    samples: int
    peak_system_ram_mb: float | None
    peak_runtime_rss_mb: float | None
    peak_gpu_memory_mb: float | None
    mean_gpu_power_w: float | None
    gpu_energy_j: float | None
    remote_endpoints: tuple[str, ...] | None = None

    def record(self) -> dict[str, Any]:
        def rounded(value: float | None, digits: int = 1) -> float | None:
            return None if value is None else round(value, digits)

        return {
            "resource_samples": self.samples,
            "peak_system_ram_mb": rounded(self.peak_system_ram_mb),
            "peak_runtime_rss_mb": rounded(self.peak_runtime_rss_mb),
            "peak_gpu_memory_mb": rounded(self.peak_gpu_memory_mb),
            "mean_gpu_power_w": rounded(self.mean_gpu_power_w, 2),
            "gpu_energy_j": rounded(self.gpu_energy_j, 2),
            "remote_connections": (
                None if self.remote_endpoints is None else len(self.remote_endpoints)
            ),
            "remote_endpoints": (
                None if self.remote_endpoints is None else list(self.remote_endpoints)
            ),
        }


def summarize_samples(samples: list[Sample], duration_s: float | None) -> ResourceSummary:
    """Peaks over the samples; GPU energy as mean power times the run's duration."""

    def peak(values: list[float | None]) -> float | None:
        known = [v for v in values if v is not None]
        return max(known) if known else None

    seen = [s.remote_endpoints for s in samples if s.remote_endpoints is not None]
    powers = [s.gpu_power_w for s in samples if s.gpu_power_w is not None]
    mean_power = fmean(powers) if powers else None
    return ResourceSummary(
        samples=len(samples),
        peak_system_ram_mb=peak([s.system_ram_used_mb for s in samples]),
        peak_runtime_rss_mb=peak([s.runtime_rss_mb for s in samples]),
        peak_gpu_memory_mb=peak([s.gpu_memory_used_mb for s in samples]),
        mean_gpu_power_w=mean_power,
        gpu_energy_j=(
            mean_power * duration_s if mean_power is not None and duration_s is not None else None
        ),
        remote_endpoints=tuple(sorted(frozenset().union(*seen))) if seen else None,
    )


@dataclass
class ResourceSampler:
    """Use as a context manager around one request; samples at the start, every interval, and
    at the end."""

    interval_s: float = 0.5
    gpu: GpuProbe = field(default_factory=NvidiaSmi)
    ram: Callable[[], float] = system_ram_used_mb
    rss: Callable[[], float | None] = runtime_rss_mb
    network: Callable[[], frozenset[str] | None] = remote_endpoints
    samples: list[Sample] = field(default_factory=list)
    _stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _thread: threading.Thread | None = field(default=None, init=False, repr=False)

    def _take(self) -> None:
        reading = self.gpu.read()
        gpu_memory, gpu_power = reading if reading is not None else (None, None)
        self.samples.append(
            Sample(
                at=time.perf_counter(),
                system_ram_used_mb=self.ram(),
                runtime_rss_mb=self.rss(),
                gpu_memory_used_mb=gpu_memory,
                gpu_power_w=gpu_power,
                remote_endpoints=self.network(),
            )
        )

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            self._take()

    def __enter__(self) -> ResourceSampler:
        self._take()
        self._thread = threading.Thread(target=self._loop, name="resource-sampler", daemon=True)
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self._take()

    def summary(self, duration_s: float | None) -> ResourceSummary:
        return summarize_samples(self.samples, duration_s)
