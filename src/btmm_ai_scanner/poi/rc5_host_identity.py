"""Semantic host identity for RC5 host-local records.

THE PROBLEM THIS EXISTS FOR. The frozen production ``Timeframe`` enum has no
M45 member and must not gain one. M45 work is therefore driven through an M15
CARRIER: the engine reads candle timestamps, not the label, so a 45-minute
series replays correctly under an M15 enum value. But the label is then a lie,
and anything that records it as the host identity silently claims the data was
M15.

That is tolerable for a diagnostic print and NOT tolerable for a stored record.
An RC5 host-local key built from the carrier would collide across genuinely
different hosts -- M45 and M15 would share one key space -- and later QA output
would attribute M45 evidence to M15.

So new RC5 host-local objects carry an ``Rc5HostIdentity``, which records what
the data ACTUALLY is (label plus bar minutes) alongside the carrier enum used
to drive it. CARRIER IMPLEMENTATION != SEMANTIC HOST IDENTITY.

Identity is derived from the observed bar spacing, not asserted by the caller,
so a mislabelled series is caught rather than recorded.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from btmm_ai_scanner.config.enums import Timeframe

__all__ = [
    "MINUTES_BY_TIMEFRAME",
    "Rc5HostIdentity",
    "host_identity_from_candles",
    "host_identity_of",
]

#: Bar length in minutes for every member of the frozen enum. W1, D1 and MN1
#: are calendar-based; their nominal lengths are recorded for completeness
#: and are not used to infer identity from spacing. MN1's nominal length uses
#: the same 30-day convention as the rest of this codebase's calendar-based
#: timeframe handling.
MINUTES_BY_TIMEFRAME: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.H1: 60,
    Timeframe.H2: 120,
    Timeframe.H3: 180,
    Timeframe.H4: 240,
    Timeframe.H6: 360,
    Timeframe.H9: 540,
    Timeframe.H12: 720,
    Timeframe.D1: 1440,
    Timeframe.W1: 10080,
    Timeframe.MN1: 43200,
}

#: Hosts RC5 supports that the frozen enum cannot name. Keyed by bar minutes.
_CARRIER_ONLY: dict[int, str] = {30: "M30", 45: "M45"}


@dataclass(frozen=True)
class Rc5HostIdentity:
    """What the series actually is, plus how it is being driven."""

    #: "M45", "M15", "H3" ... the host as a human and a key should see it.
    label: str
    #: Bar length in minutes. The part that cannot be faked by a label.
    minutes: int
    #: The enum actually handed to the engine. May differ from ``label``.
    carrier: Timeframe

    @property
    def is_carrier_only(self) -> bool:
        """True when the frozen enum cannot name this host."""
        return self.label != self.carrier.value

    @property
    def key(self) -> tuple[str, int]:
        """Host-local key component. Uses the SEMANTIC identity, so M15 and
        M45 can never collide even though they share a carrier."""
        return (self.label, self.minutes)

    def __str__(self) -> str:
        if self.is_carrier_only:
            return f"{self.label}(via {self.carrier.value})"
        return self.label


def host_identity_of(timeframe: Timeframe) -> Rc5HostIdentity:
    """Identity for a host the frozen enum can name honestly."""
    return Rc5HostIdentity(
        label=timeframe.value,
        minutes=MINUTES_BY_TIMEFRAME[timeframe],
        carrier=timeframe,
    )


def host_identity_from_candles(
    carrier: Timeframe,
    candles: Sequence[object],
) -> Rc5HostIdentity:
    """Derive identity from the series' own bar spacing.

    The modal gap between consecutive bars is used rather than the first gap,
    so a weekend or a session break cannot decide the answer. If the spacing
    matches the carrier, the carrier is honest and is used directly; if it
    matches a carrier-only host such as M45, that label is recorded instead.

    Raises ``ValueError`` when the spacing matches neither, because silently
    recording the carrier is exactly the failure this module prevents.
    """
    minutes = _modal_gap_minutes(candles)
    if minutes is None:
        # Not enough bars to measure; trust the carrier rather than guess.
        return host_identity_of(carrier)
    if minutes == MINUTES_BY_TIMEFRAME.get(carrier):
        return host_identity_of(carrier)
    label = _CARRIER_ONLY.get(minutes)
    if label is not None:
        return Rc5HostIdentity(label=label, minutes=minutes, carrier=carrier)
    for timeframe, known in MINUTES_BY_TIMEFRAME.items():
        if known == minutes:
            return Rc5HostIdentity(
                label=timeframe.value, minutes=minutes, carrier=carrier
            )
    raise ValueError(
        f"series has {minutes}-minute bars, which matches neither the carrier "
        f"{carrier.value} nor any known RC5 host; refusing to record "
        f"{carrier.value} as the host identity"
    )


def _modal_gap_minutes(candles: Sequence[object]) -> int | None:
    if len(candles) < 3:
        return None
    counts: dict[int, int] = {}
    previous = None
    for candle in candles:
        current = getattr(candle, "event_time_utc", None)
        if current is None:
            return None
        if previous is not None:
            gap = int((current - previous).total_seconds() // 60)
            if gap > 0:
                counts[gap] = counts.get(gap, 0) + 1
        previous = current
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]
