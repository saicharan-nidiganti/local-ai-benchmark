"""Resource sampling, with the GPU and process readings replaced by fakes."""

from __future__ import annotations

import subprocess
import time
from types import SimpleNamespace

import pytest

from local_ai_benchmark import sampler


class FakeGpu:
    def __init__(self, readings):
        self.readings = list(readings)

    def read(self):
        return self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]


def make(at, ram=8000.0, rss=None, gpu_mem=None, power=None):
    return sampler.Sample(
        at=at, system_ram_used_mb=ram, runtime_rss_mb=rss, gpu_memory_used_mb=gpu_mem,
        gpu_power_w=power,
    )  # fmt: skip


def test_summary_takes_peaks_and_energy_from_mean_power():
    samples = [
        make(0.0, ram=8000, rss=2500, gpu_mem=3000, power=20),
        make(0.5, ram=8200, rss=2700, gpu_mem=3900, power=40),
        make(1.0, ram=8100, rss=2600, gpu_mem=3800, power=30),
    ]

    summary = sampler.summarize_samples(samples, duration_s=2.0)

    assert summary.samples == 3
    assert summary.peak_system_ram_mb == 8200
    assert summary.peak_runtime_rss_mb == 2700
    assert summary.peak_gpu_memory_mb == 3900
    assert summary.mean_gpu_power_w == 30
    assert summary.gpu_energy_j == 60


def test_without_a_gpu_the_gpu_fields_are_none():
    summary = sampler.summarize_samples([make(0.0), make(0.5)], duration_s=1.0)

    record = summary.record()
    assert record["peak_gpu_memory_mb"] is None
    assert record["mean_gpu_power_w"] is None
    assert record["gpu_energy_j"] is None
    assert record["peak_system_ram_mb"] == 8000
    assert record["resource_samples"] == 2


def test_the_sampler_reads_at_the_start_the_end_and_in_between():
    gpu = FakeGpu([(3000.0, 25.0)])
    with sampler.ResourceSampler(
        interval_s=0.01, gpu=gpu, ram=lambda: 8000.0, rss=lambda: 2500.0
    ) as running:
        time.sleep(0.1)

    summary = running.summary(duration_s=0.1)
    assert summary.samples >= 3
    assert summary.peak_gpu_memory_mb == 3000
    assert summary.mean_gpu_power_w == 25
    assert summary.gpu_energy_j == pytest.approx(2.5)


def test_nvidia_smi_readings_are_parsed(monkeypatch):
    probe = sampler.NvidiaSmi()
    probe.program = "nvidia-smi"
    monkeypatch.setattr(
        sampler.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(stdout="3812, 41.27\n"),
    )

    assert probe.read() == (3812.0, 41.27)


def test_a_gpu_that_reports_no_power_gives_none(monkeypatch):
    probe = sampler.NvidiaSmi()
    probe.program = "nvidia-smi"
    monkeypatch.setattr(
        sampler.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="3812, [N/A]\n")
    )

    assert probe.read() == (3812.0, None)


def test_no_nvidia_smi_means_no_gpu_reading(monkeypatch):
    probe = sampler.NvidiaSmi()
    probe.program = None
    assert probe.read() is None

    probe.program = "nvidia-smi"

    def fail(*a, **k):
        raise subprocess.TimeoutExpired("nvidia-smi", 5)

    monkeypatch.setattr(sampler.subprocess, "run", fail)
    assert probe.read() is None
    monkeypatch.setattr(sampler.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=""))
    assert probe.read() is None


def process(name, rss_mb):
    memory = None if rss_mb is None else SimpleNamespace(rss=rss_mb * 2**20)
    return SimpleNamespace(info={"name": name, "memory_info": memory})


def test_the_runtime_memory_adds_up_every_ollama_process(monkeypatch):
    procs = [
        process("ollama.exe", 100),
        process("ollama app.exe", 50),
        process("llama-server.exe", 1600),
        process("python.exe", 999),
        process(None, None),
    ]
    monkeypatch.setattr(sampler.psutil, "process_iter", lambda attrs: procs)

    assert sampler.runtime_rss_mb() == 1750


def test_no_ollama_process_gives_none(monkeypatch):
    monkeypatch.setattr(sampler.psutil, "process_iter", lambda attrs: [])

    assert sampler.runtime_rss_mb() is None
    assert sampler.system_ram_used_mb() > 0
