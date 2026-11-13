"""Latency targets for interactive use."""

from __future__ import annotations

from local_ai_benchmark.targets import COLD_FIRST_TOKEN, DECODE_SPEED, TARGETS, WARM_FIRST_TOKEN


def test_a_time_target_is_met_at_or_below_its_limit():
    assert WARM_FIRST_TOKEN.met(999.0) is True
    assert WARM_FIRST_TOKEN.met(1000.0) is True
    assert WARM_FIRST_TOKEN.met(1000.1) is False


def test_a_speed_target_is_met_at_or_above_its_limit():
    assert DECODE_SPEED.met(10.0) is True
    assert DECODE_SPEED.met(9.9) is False


def test_an_unmeasured_value_is_neither_met_nor_missed():
    assert COLD_FIRST_TOKEN.met(None) is None


def test_every_target_states_its_bound_and_its_reason():
    assert [t.bound for t in TARGETS] == ["≤ 1,000 ms", "≥ 10 tokens/s", "≤ 10,000 ms"]
    assert all("(" in t.reason and ")" in t.reason for t in TARGETS)  # each cites a source
