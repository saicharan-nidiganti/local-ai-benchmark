"""Latency targets for interactive use, with the reasoning behind each limit, and whether a
model meets them."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    key: str
    name: str
    limit: float
    higher_is_better: bool
    unit: str
    reason: str

    def met(self, value: float | None) -> bool | None:
        """True or False, or None when the value was not measured."""
        if value is None:
            return None
        return value >= self.limit if self.higher_is_better else value <= self.limit

    @property
    def bound(self) -> str:
        sign = "≥" if self.higher_is_better else "≤"
        return f"{sign} {self.limit:,.0f} {self.unit}"


WARM_FIRST_TOKEN = Target(
    key="warm_ttft_ms",
    name="First token, model loaded",
    limit=1000.0,
    higher_is_better=False,
    unit="ms",
    reason="1 s is the limit for a user's flow of thought to stay uninterrupted "
    "(Nielsen, Response Times: The 3 Important Limits, 1993)",
)
DECODE_SPEED = Target(
    key="decode_tokens_per_sec",
    name="Decode speed",
    limit=10.0,
    higher_is_better=True,
    unit="tokens/s",
    reason="faster than average adult silent reading, 238 words a minute (Brysbaert, Journal "
    "of Memory and Language 109, 2019): 5 to 6.5 tokens/s at the 1.3 to 1.6 tokens a word "
    "the compared models' summaries use, so text arrives faster than it is read",
)
COLD_FIRST_TOKEN = Target(
    key="cold_ttft_ms",
    name="First token, model not loaded",
    limit=10000.0,
    higher_is_better=False,
    unit="ms",
    reason="10 s is the limit for keeping a user's attention on the task (Nielsen, 1993)",
)
TARGETS = (WARM_FIRST_TOKEN, DECODE_SPEED, COLD_FIRST_TOKEN)
