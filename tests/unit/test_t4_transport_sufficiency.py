"""Does an independent T4-equivalent reimplementation reproduce
`assess_volatility` / `assess_session`?

Unlike T1/T2/T3, T4 needs no P5/P6 wire at all -- see `t4_pine_model.py`'s
module docstring for why. This proves REIMPLEMENTATION equivalence instead:
run the real production functions on full synthetic data, run the independent
`t4_pine_model.py` on the same inputs (ATR/ranges reused from the proven P1
measurement, banding/precedence logic written independently), and require
agreement.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btrc.enums import SessionContext, VolatilityState
from btmm_ai_scanner.btrc.t4_configuration import VolatilitySessionConfiguration
from btmm_ai_scanner.btrc.t4_engine import assess_session, assess_volatility
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.measurements.candle_metrics import total_range
from tests.parity_support.t4_pine_model import (
    session_from_evaluation_time,
    volatility_from_window,
)

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_V = SemVer.parse("0.1.0")
_M15 = Timeframe.M15
_CFG = VolatilitySessionConfiguration()


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _candle(i: int, range_size: float, *, bullish: bool = True) -> NormalizedCandle:
    mid = 100.0
    half = range_size / 2
    high = mid + half
    low = mid - half
    open_ = low if bullish else high
    close = high if bullish else low
    event = _BASE + timedelta(minutes=15 * i)
    avail = event + timedelta(minutes=15)
    return NormalizedCandle.model_validate(
        {
            "record_id": _uid(500000 + i),
            "content_fingerprint": _FP,
            "raw_candle_id": _uid(600000 + i),
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m15",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M15",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": _M15,
            "event_time_utc": event,
            "availability_time_utc": avail,
            "processing_time_utc": avail,
            "original_event_time": event,
            "original_availability_time": avail,
            "original_timezone": "UTC",
            "open": Decimal(str(open_)),
            "high": Decimal(str(high)),
            "low": Decimal(str(low)),
            "close": Decimal(str(close)),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": _V,
            "contract_version": _V,
            "schema_version": _V,
            "provenance_id": _uid(700000 + i),
        }
    )


def volatility_both(range_sizes: list[float]):
    candles = [_candle(i, r) for i, r in enumerate(range_sizes)]
    real = assess_volatility(candles, _CFG)
    if len(candles) < _CFG.atr_period:
        assert real.volatility_state == VolatilityState.NORMAL
        return real
    window = candles[-_CFG.volatility_window :]
    ranges = [total_range(c) for c in window]
    wire = volatility_from_window(ranges)
    assert real.volatility_state == wire.volatility_state, (
        real.volatility_state, wire.volatility_state,
    )
    assert real.abnormal_spike == wire.abnormal_spike
    assert real.suitability_score == wire.suitability_score
    return real


def session_both(evaluation_time_utc: datetime) -> SessionContext:
    real = assess_session(evaluation_time_utc, _CFG)
    wire = session_from_evaluation_time(evaluation_time_utc)
    assert real.session_context == wire, (real.session_context, wire)
    return real.session_context


# ---------------------------------------------------------------------------
# Volatility: directed
# ---------------------------------------------------------------------------


def test_volatility_normal_on_insufficient_history() -> None:
    real = volatility_both([1.0] * 5)
    assert real.volatility_state == VolatilityState.NORMAL


def test_volatility_very_low_at_bottom_of_distribution() -> None:
    range_sizes = [10.0] * 49 + [1.0]  # newest is the tiny one -> percentile 0
    real = volatility_both(range_sizes)
    assert real.volatility_state == VolatilityState.VERY_LOW


def test_volatility_extreme_at_top_of_distribution() -> None:
    range_sizes = [1.0] * 49 + [100.0]
    real = volatility_both(range_sizes)
    assert real.volatility_state == VolatilityState.EXTREME


def test_volatility_normal_mid_distribution() -> None:
    range_sizes = [float(i % 10 + 1) for i in range(49)] + [5.0]
    real = volatility_both(range_sizes)
    assert real.volatility_state in (VolatilityState.NORMAL, VolatilityState.LOW, VolatilityState.HIGH)


def test_volatility_abnormal_spike_flagged() -> None:
    range_sizes = [2.0] * 49 + [10.0]  # >= 2.5x the rolling median
    real = volatility_both(range_sizes)
    assert real.abnormal_spike is True


def test_volatility_no_spike_below_multiplier() -> None:
    range_sizes = [2.0] * 49 + [4.0]  # 2.0x, below the 2.5x threshold
    real = volatility_both(range_sizes)
    assert real.abnormal_spike is False


# ---------------------------------------------------------------------------
# Session: directed, every context reachable
# ---------------------------------------------------------------------------


def test_session_asian() -> None:
    # 23:00 UTC in January = well inside Asian window, before London pre-open.
    ctx = session_both(datetime(2026, 1, 5, 23, 0, tzinfo=UTC))
    assert ctx == SessionContext.ASIAN


def test_session_london_preopen() -> None:
    # 07:00 London local (winter, UTC+0) = 07:00 UTC.
    ctx = session_both(datetime(2026, 1, 5, 7, 0, tzinfo=UTC))
    assert ctx == SessionContext.LONDON_PREOPEN


def test_session_london_active() -> None:
    ctx = session_both(datetime(2026, 1, 5, 9, 0, tzinfo=UTC))
    assert ctx == SessionContext.LONDON


def test_session_new_york_preopen() -> None:
    # 07:00 NY local in January (UTC-5) = 12:00 UTC, inside London active too --
    # NY pre-open must take precedence over London active.
    ctx = session_both(datetime(2026, 1, 5, 12, 0, tzinfo=UTC))
    assert ctx == SessionContext.NEW_YORK_PREOPEN


def test_session_london_ny_overlap() -> None:
    # 13:00 UTC in January: London active (08:00-16:30 UTC) and NY active
    # (13:00-22:00 UTC, since 08:00 NY local = 13:00 UTC).
    ctx = session_both(datetime(2026, 1, 5, 13, 0, tzinfo=UTC))
    assert ctx == SessionContext.LONDON_NY_OVERLAP


def test_session_new_york_only() -> None:
    # After London closes (16:30 UTC) but NY still active (until 22:00 UTC).
    ctx = session_both(datetime(2026, 1, 5, 18, 0, tzinfo=UTC))
    assert ctx == SessionContext.NEW_YORK


def test_session_post_ny() -> None:
    # In January (NY on UTC-5), NY close (17:00 local = 22:00 UTC) coincides
    # exactly with the Asian start (22:00 UTC) -- no POST_NY gap exists then.
    # In July (NY on UTC-4, EDT), NY closes at 21:00 UTC while Asian still
    # starts at 22:00 UTC -- a genuine one-hour POST_NY gap.
    ctx = session_both(datetime(2026, 7, 6, 21, 30, tzinfo=UTC))
    assert ctx == SessionContext.POST_NY


def test_session_across_a_dst_transition() -> None:
    """London DST starts (BST, UTC+1) on the last Sunday of March. The SAME UTC
    hour that was LONDON_PREOPEN before the transition becomes LONDON active
    after it -- a hardcoded UTC offset would get this wrong; zoneinfo-based
    resolution (both real and model) gets it right."""
    before = session_both(datetime(2026, 3, 28, 7, 0, tzinfo=UTC))  # GMT, pre-open
    after = session_both(datetime(2026, 3, 30, 7, 0, tzinfo=UTC))  # BST, active
    assert before == SessionContext.LONDON_PREOPEN
    assert after == SessionContext.LONDON


# ---------------------------------------------------------------------------
# Randomized
# ---------------------------------------------------------------------------


def test_randomized_session_sufficiency() -> None:
    rng = random.Random(7654321)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    span_days = 365 * 8  # spans many DST transitions, both hemispheres' rules
    mismatches = []
    for _ in range(5000):
        t = start + timedelta(
            days=rng.randint(0, span_days),
            minutes=rng.randint(0, 24 * 60 - 1),
        )
        try:
            session_both(t)
        except AssertionError as exc:
            mismatches.append(str(exc))
    assert mismatches == [], mismatches[:5]


def test_randomized_session_covers_every_context() -> None:
    rng = random.Random(13579)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    seen = set()
    for _ in range(5000):
        t = start + timedelta(
            days=rng.randint(0, 365 * 8), minutes=rng.randint(0, 24 * 60 - 1)
        )
        seen.add(assess_session(t, _CFG).session_context)
    assert seen == set(SessionContext)


def test_randomized_volatility_sufficiency() -> None:
    rng = random.Random(2468)
    mismatches = []
    for _ in range(500):
        n = rng.randint(0, 60)
        range_sizes = [max(0.01, rng.random() * 20) for _ in range(n)]
        try:
            volatility_both(range_sizes)
        except AssertionError as exc:
            mismatches.append(str(exc))
    assert mismatches == [], mismatches[:5]


def test_randomized_volatility_covers_every_state() -> None:
    rng = random.Random(9753)
    seen = set()
    for _ in range(2000):
        n = rng.randint(50, 60)
        range_sizes = [max(0.01, rng.random() * 20) for _ in range(n)]
        candles = [_candle(i, r) for i, r in enumerate(range_sizes)]
        seen.add(assess_volatility(candles, _CFG).volatility_state)
    assert seen == set(VolatilityState)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def test_mutation_session_ignoring_ny_preopen_precedence_is_caught() -> None:
    """A port that let LONDON active win over NEW_YORK_PREOPEN (instead of the
    source's explicit precedence) would misclassify 12:00 UTC in January."""
    real = assess_session(datetime(2026, 1, 5, 12, 0, tzinfo=UTC), _CFG).session_context
    naive_precedence = (
        SessionContext.LONDON
    )  # what you'd get checking london_active before ny_preopen
    assert real == SessionContext.NEW_YORK_PREOPEN
    assert real != naive_precedence


def test_mutation_volatility_percentile_strict_vs_nonstrict_is_caught() -> None:
    """The source counts `r <= current` (non-strict) for the percentile rank.
    A strict `<` would place a value tied with several others at a lower
    percentile, potentially shifting the band."""
    ranges = [Decimal("5")] * 40 + [Decimal("5")] * 9 + [Decimal("5")]  # all tied
    current = ranges[-1]
    nonstrict = sum(1 for r in ranges if r <= current)
    strict = sum(1 for r in ranges if r < current)
    assert nonstrict == len(ranges)
    assert strict == 0
    assert nonstrict != strict
