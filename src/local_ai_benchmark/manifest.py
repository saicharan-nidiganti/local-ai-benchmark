"""The environment a benchmark was measured in, recorded once per run ID."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import psutil

from . import __version__, runtime
from .metrics import Record, utc_timestamp
from .paths import project_root


def _output_of(args: list[str], cwd: Path | None = None, timeout: float = 5.0) -> str | None:
    """Stdout of a fixed command, or None when the program is missing or fails."""
    program = shutil.which(args[0])
    if program is None:
        return None
    try:
        done = subprocess.run(  # noqa: S603 - fixed arguments, no shell, program found on PATH
            [program, *args[1:]],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip()


def harness() -> dict[str, Any]:
    root = project_root()
    sha = _output_of(["git", "rev-parse", "HEAD"], cwd=root)
    changes = _output_of(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root)
    return {
        "version": __version__,
        "git_sha": sha,
        "git_dirty": None if sha is None or changes is None else bool(changes),
    }


def cpu_model() -> str:
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            ) as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or platform.machine()


def gpus() -> list[dict[str, Any]]:
    """NVIDIA GPUs as `nvidia-smi` reports them; empty without an NVIDIA driver."""
    out = _output_of(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ]
    )
    found = []
    for line in (out or "").splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        name, memory, driver = parts
        try:
            memory_mb: int | None = int(float(memory))
        except ValueError:
            memory_mb = None
        found.append({"name": name, "memory_total_mb": memory_mb, "driver_version": driver})
    return found


def power() -> dict[str, Any]:
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery is None:
        return {"on_ac": None, "battery_percent": None}
    return {"on_ac": battery.power_plugged, "battery_percent": round(battery.percent)}


def collect(run_id: str, server_version: str, model: runtime.ModelDetails) -> Record:
    memory = psutil.virtual_memory()
    return {
        "run_id": run_id,
        "created_at": utc_timestamp(),
        "harness": harness(),
        "python": platform.python_version(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "cpu": {
            "model": cpu_model(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(),
        },
        "memory_total_gb": round(memory.total / 2**30, 1),
        "gpus": gpus(),
        "power": power(),
        "runtime": {"name": "ollama", "version": server_version, "host": runtime.host()},
        "model": {**asdict(model), "capabilities": list(model.capabilities)},
    }


def manifest_log(run_log: Path) -> Path:
    """Manifests live beside the run log they describe."""
    return run_log.with_name("manifests.jsonl")
