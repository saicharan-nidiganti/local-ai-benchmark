"""The environment manifest, with system queries replaced by fakes where they vary."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from local_ai_benchmark import manifest, runtime

MODEL = runtime.ModelDetails(
    name="qwen3:4b",
    digest="359d7dd4bcda",
    family="qwen3",
    parameter_size="4.0B",
    quantization="Q4_K_M",
    format="gguf",
    capabilities=("completion", "thinking"),
)


def test_collects_every_section_once_per_run(monkeypatch):
    monkeypatch.setattr(manifest, "gpus", lambda: [{"name": "RTX 3050", "memory_total_mb": 4096}])
    monkeypatch.setattr(manifest, "power", lambda: {"on_ac": True, "battery_percent": 80})

    record = manifest.collect("run-1", "0.40.16", MODEL)

    assert record["run_id"] == "run-1"
    assert record["created_at"]
    assert record["runtime"]["name"] == "ollama"
    assert record["runtime"]["version"] == "0.40.16"
    assert record["model"]["digest"] == "359d7dd4bcda"
    assert record["model"]["capabilities"] == ["completion", "thinking"]
    assert record["gpus"][0]["name"] == "RTX 3050"
    assert record["power"]["on_ac"] is True
    assert record["memory_total_gb"] > 0
    assert record["cpu"]["logical_cores"] >= 1
    assert record["python"]
    assert set(record["harness"]) == {"version", "git_sha", "git_dirty"}


def test_reads_the_git_commit_of_the_checkout():
    info = manifest.harness()

    # The tests run from a git checkout, so the commit is known.
    assert info["git_sha"] is not None
    assert len(info["git_sha"]) == 40


def test_a_missing_program_gives_none(monkeypatch):
    monkeypatch.setattr(manifest.shutil, "which", lambda name: None)

    assert manifest._output_of(["nvidia-smi"]) is None
    assert manifest.gpus() == []


def test_a_failing_program_gives_none(monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(manifest.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(manifest.subprocess, "run", fail)

    assert manifest._output_of(["git", "status"]) is None


def test_parses_nvidia_smi_output(monkeypatch):
    output = "NVIDIA GeForce RTX 3050 Laptop GPU, 4096, 617.14\nbroken line\n"
    monkeypatch.setattr(manifest, "_output_of", lambda args, cwd=None: output)

    assert manifest.gpus() == [
        {
            "name": "NVIDIA GeForce RTX 3050 Laptop GPU",
            "memory_total_mb": 4096,
            "driver_version": "617.14",
        }
    ]


def test_power_without_a_battery_is_unknown(monkeypatch):
    monkeypatch.setattr(manifest.psutil, "sensors_battery", lambda: None)

    assert manifest.power() == {"on_ac": None, "battery_percent": None}


def test_power_on_a_laptop(monkeypatch):
    battery = SimpleNamespace(power_plugged=False, percent=63.6)
    monkeypatch.setattr(manifest.psutil, "sensors_battery", lambda: battery)

    assert manifest.power() == {"on_ac": False, "battery_percent": 64}


def test_the_cpu_model_is_named():
    assert manifest.cpu_model()


def test_manifests_live_beside_the_run_log():
    assert manifest.manifest_log(Path("data/raw/runs.jsonl")) == Path("data/raw/manifests.jsonl")


def test_interfaces_up_lists_routable_interfaces_only(monkeypatch):
    import socket

    def addr(ip):
        return SimpleNamespace(family=socket.AF_INET, address=ip)

    monkeypatch.setattr(
        manifest.psutil,
        "net_if_stats",
        lambda: {
            "Wi-Fi": SimpleNamespace(isup=True),
            "Ethernet": SimpleNamespace(isup=False),
            "Loopback": SimpleNamespace(isup=True),
            "Unplugged": SimpleNamespace(isup=True),
        },
    )
    monkeypatch.setattr(
        manifest.psutil,
        "net_if_addrs",
        lambda: {
            "Wi-Fi": [addr("192.168.1.4")],
            "Ethernet": [addr("10.0.0.2")],
            "Loopback": [addr("127.0.0.1")],
            "Unplugged": [addr("169.254.10.1")],  # link-local: no network behind it
        },
    )

    assert manifest.interfaces_up() == ["Wi-Fi"]
