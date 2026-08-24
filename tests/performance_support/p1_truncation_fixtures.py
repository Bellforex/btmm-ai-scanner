"""P1-PERF-4 — deterministic adversarial streams for truncation testing.

Real FXCM data cannot prove a warm-up bound: it only shows what happened to
occur. These fixtures instead place a specific piece of analytical structure at
a specific offset relative to the truncation boundary, so that if the engine
carried state across that boundary the test would see it.

Each builder returns candles for one named scenario. The interesting structure
always sits at or just before ``boundary``: material the truncated run cannot
see. If a protected-region output depends on it, the comparison fails.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

_TICK = Decimal("0.01")


@dataclass(frozen=True)
class Bar:
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


def _q(value: Decimal) -> Decimal:
    return value.quantize(_TICK)


class _Builder:
    """Deterministic candle builder with a controllable base regime."""

    def __init__(self, seed: int, base: Decimal = Decimal("2000")) -> None:
        self.rng = random.Random(seed)
        self.price = base
        self.bars: list[Bar] = []

    def drift(self, count: int, amplitude: str = "0.60", trend: str = "0") -> None:
        amp = Decimal(amplitude)
        step = Decimal(trend)
        for _ in range(count):
            move = amp * Decimal(self.rng.randint(-100, 100)) / Decimal(100) + step
            open_ = self.price
            close = self.price + move
            high = max(open_, close) + amp * Decimal(self.rng.randint(0, 60)) / Decimal(
                100
            )
            low = min(open_, close) - amp * Decimal(self.rng.randint(0, 60)) / Decimal(
                100
            )
            self.bars.append(Bar(_q(open_), _q(high), _q(low), _q(close)))
            self.price = close

    def spike_high(self, height: str = "6.0") -> None:
        """One unmistakable local maximum — a swing-high pivot."""
        amp = Decimal(height)
        open_ = self.price
        close = self.price - amp / Decimal(4)
        self.bars.append(
            Bar(_q(open_), _q(self.price + amp), _q(min(open_, close)), _q(close))
        )
        self.price = close

    def spike_low(self, depth: str = "6.0") -> None:
        amp = Decimal(depth)
        open_ = self.price
        close = self.price + amp / Decimal(4)
        self.bars.append(
            Bar(_q(open_), _q(max(open_, close)), _q(self.price - amp), _q(close))
        )
        self.price = close

    def plateau_high(self, height: str = "6.0", width: int = 2) -> None:
        """``width`` adjacent bars sharing the SAME extreme — a plateau pivot."""
        amp = Decimal(height)
        peak = self.price + amp
        for _ in range(width):
            open_ = self.price
            close = self.price - amp / Decimal(10)
            self.bars.append(Bar(_q(open_), _q(peak), _q(min(open_, close)), _q(close)))
            self.price = close

    def plateau_low(self, depth: str = "6.0", width: int = 2) -> None:
        amp = Decimal(depth)
        trough = self.price - amp
        for _ in range(width):
            open_ = self.price
            close = self.price + amp / Decimal(10)
            self.bars.append(
                Bar(_q(open_), _q(max(open_, close)), _q(trough), _q(close))
            )
            self.price = close

    def at_price(self, price: Decimal) -> None:
        """Move the running price to an exact level without making a pivot."""
        while abs(self.price - price) > Decimal("0.5"):
            step = Decimal("0.5") if price > self.price else Decimal("-0.5")
            open_ = self.price
            close = self.price + step
            self.bars.append(
                Bar(_q(open_), _q(max(open_, close)), _q(min(open_, close)), _q(close))
            )
            self.price = close
        self.price = price

    def displacement(self, size: str = "30") -> None:
        """A single very-fast bar: range far above the local median."""
        amp = Decimal(size)
        open_ = self.price
        close = self.price + amp
        self.bars.append(
            Bar(_q(open_), _q(close + amp / Decimal(20)), _q(open_), _q(close))
        )
        self.price = close

    def compression(self, count: int) -> None:
        for _ in range(count):
            open_ = self.price
            close = self.price + Decimal(self.rng.randint(-1, 1)) / Decimal(100)
            self.bars.append(
                Bar(
                    _q(open_),
                    _q(max(open_, close) + _TICK),
                    _q(min(open_, close) - _TICK),
                    _q(close),
                )
            )
            self.price = close

    def monotonic(self, count: int, step: str = "0.8") -> None:
        inc = Decimal(step)
        for _ in range(count):
            open_ = self.price
            close = self.price + inc
            self.bars.append(Bar(_q(open_), _q(close), _q(open_), _q(close)))
            self.price = close

    def pad_to(self, target: int, amplitude: str = "0.60") -> None:
        if target > len(self.bars):
            self.drift(target - len(self.bars), amplitude=amplitude)


# ---------------------------------------------------------------------------
# Scenarios. Each takes (boundary, total) and returns the candle bars.
#
# `boundary` is the index the truncated run starts at, so anything written
# before it is exactly the state the truncated run must prove it does not need.
# ---------------------------------------------------------------------------

Scenario = Callable[[int, int], list[Bar]]


def _scenario(seed: int, place: Callable[[_Builder], None]) -> Scenario:
    def build(boundary: int, total: int) -> list[Bar]:
        b = _Builder(seed)
        b.pad_to(boundary - 60)
        place(b)
        b.pad_to(total)
        return b.bars[:total]

    return build


def _swing_before(b: _Builder) -> None:
    b.drift(50)
    b.spike_high()
    b.drift(6)


def _plateau_crossing(b: _Builder) -> None:
    b.drift(55)
    b.plateau_high(width=4)


def _supersession_crossing(b: _Builder) -> None:
    b.drift(40)
    b.spike_high("4.0")
    b.drift(3)
    b.spike_high("9.0")  # supersedes the first, same direction
    b.drift(3)


def _alternating_chain(b: _Builder) -> None:
    for _ in range(6):
        b.spike_high("5.0")
        b.drift(3)
        b.spike_low("5.0")
        b.drift(3)


def _displacement_before(b: _Builder) -> None:
    b.drift(50)
    b.displacement("40")
    b.drift(5)


def _equal_highs_straddling(b: _Builder) -> None:
    b.drift(30)
    level = b.price
    b.spike_high("6.0")
    b.drift(12)
    b.at_price(level)
    b.spike_high("6.0")  # same level -> equal-high cluster across the boundary
    b.drift(8)


def _equal_lows_straddling(b: _Builder) -> None:
    b.drift(30)
    level = b.price
    b.spike_low("6.0")
    b.drift(12)
    b.at_price(level)
    b.spike_low("6.0")
    b.drift(8)


def _support_origin_before(b: _Builder) -> None:
    b.drift(40)
    b.spike_low("8.0")  # support origin
    b.drift(15)


def _resistance_origin_before(b: _Builder) -> None:
    b.drift(40)
    b.spike_high("8.0")
    b.drift(15)


def _reaction_start_at_boundary(b: _Builder) -> None:
    b.drift(52)
    b.spike_low("7.0")
    b.drift(2)  # reaction search begins right at the boundary


def _reaction_window_crossing(b: _Builder) -> None:
    b.drift(56)
    b.spike_low("7.0")
    b.monotonic(3, "1.5")  # 5-bar reaction window straddles the boundary


def _canonical_sr_just_before(b: _Builder) -> None:
    b.drift(20)
    b.spike_low("8.0")
    b.monotonic(6, "1.6")
    b.spike_high("5.0")
    b.drift(4)
    b.spike_low("8.0")
    b.monotonic(6, "1.6")
    b.drift(6)


def _trendline_anchor_before(b: _Builder) -> None:
    for _ in range(4):
        b.spike_high("5.0")
        b.drift(4, trend="-0.5")


def _high_swing_density(b: _Builder) -> None:
    for _ in range(15):
        b.spike_high("3.0")
        b.spike_low("3.0")


def _low_swing_density(b: _Builder) -> None:
    b.compression(60)


def _long_monotonic(b: _Builder) -> None:
    b.monotonic(60, "1.2")


def _long_compression(b: _Builder) -> None:
    b.compression(60)


def _exact_equality(b: _Builder) -> None:
    b.drift(40)
    level = b.price
    b.plateau_high(width=3)
    b.at_price(level)
    b.plateau_high(width=3)
    b.drift(4)


def _rollover(b: _Builder) -> None:
    b.drift(20)
    b.spike_high("10.0")
    b.drift(40)


def _multiple_trackers(b: _Builder) -> None:
    for _ in range(5):
        b.spike_low("6.0")
        b.drift(2)
        b.spike_high("4.0")
        b.drift(2)


SCENARIOS: dict[str, Scenario] = {
    "01_swing_before_window": _scenario(101, _swing_before),
    "02_plateau_crossing": _scenario(102, _plateau_crossing),
    "03_supersession_crossing": _scenario(103, _supersession_crossing),
    "04_alternating_chain": _scenario(104, _alternating_chain),
    "05_displacement_before": _scenario(105, _displacement_before),
    "06_equal_high_straddle": _scenario(106, _equal_highs_straddling),
    "07_equal_low_straddle": _scenario(107, _equal_lows_straddling),
    "08_support_origin_before": _scenario(108, _support_origin_before),
    "09_resistance_origin_before": _scenario(109, _resistance_origin_before),
    "10_reaction_start_at_boundary": _scenario(110, _reaction_start_at_boundary),
    "11_reaction_window_crossing": _scenario(111, _reaction_window_crossing),
    "12_canonical_sr_just_before": _scenario(112, _canonical_sr_just_before),
    "13_trendline_anchor_before": _scenario(113, _trendline_anchor_before),
    "14_high_swing_density": _scenario(114, _high_swing_density),
    "15_low_swing_density": _scenario(115, _low_swing_density),
    "16_long_monotonic_leg": _scenario(116, _long_monotonic),
    "17_long_compression": _scenario(117, _long_compression),
    "18_exact_equality_plateau": _scenario(118, _exact_equality),
    "19_window_rollover": _scenario(119, _rollover),
    "20_multiple_sr_trackers": _scenario(120, _multiple_trackers),
}


def structured_stream(seed: int, total: int) -> list[Bar]:
    """A randomized stream that still contains real analytical structure.

    Pure noise rarely produces swings, S/R origins or trendlines, so a campaign
    built on it would compare mostly-empty outputs and prove very little. This
    mixes regimes so every detector family has material to work with.
    """
    b = _Builder(seed)
    rng = random.Random(seed ^ 0x5EED)
    while len(b.bars) < total:
        choice = rng.randint(0, 7)
        if choice == 0:
            b.spike_high(str(rng.randint(3, 10)))
        elif choice == 1:
            b.spike_low(str(rng.randint(3, 10)))
        elif choice == 2:
            b.plateau_high(width=rng.randint(2, 4))
        elif choice == 3:
            b.plateau_low(width=rng.randint(2, 4))
        elif choice == 4:
            b.monotonic(rng.randint(4, 14), str(Decimal(rng.randint(4, 18)) / 10))
        elif choice == 5:
            b.compression(rng.randint(4, 12))
        elif choice == 6:
            b.displacement(str(rng.randint(15, 45)))
        else:
            b.drift(rng.randint(5, 20), amplitude=str(Decimal(rng.randint(3, 15)) / 10))
    return b.bars[:total]
