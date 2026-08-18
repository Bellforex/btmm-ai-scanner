"""BTRC-T4 volatility + session-context tests.

Volatility: percentile bands, abnormal spike, no direction inference,
insufficient history, determinism. Session: every context reachable, DST-correct
London/New-York resolution from the evaluation timestamp (never the machine
clock). Bounded synthetic fixtures only.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btrc import (
    SessionContext,
    VolatilityState,
    assess_session,
    assess_volatility,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_V = SemVer.parse("0.1.0")
_M15 = Timeframe.M15


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


def _window(last_range: float, *, bullish: bool = True) -> tuple[NormalizedCandle, ...]:
    # 49 background candles with distinct ranges 1..49, then the target last range.
    candles = [_candle(i, float(i + 1), bullish=bullish) for i in range(49)]
    candles.append(_candle(49, last_range, bullish=bullish))
    return tuple(candles)


# --------------- volatility ---------------
def test_volatility_insufficient_history_is_normal_default() -> None:
    v = assess_volatility(_window(25.0)[:10])
    assert v.volatility_state is VolatilityState.NORMAL
    assert v.percentile is None
    assert v.abnormal_spike is False


def test_volatility_very_low() -> None:
    assert assess_volatility(_window(2.0)).volatility_state is VolatilityState.VERY_LOW


def test_volatility_low() -> None:
    assert assess_volatility(_window(12.0)).volatility_state is VolatilityState.LOW


def test_volatility_normal() -> None:
    assert assess_volatility(_window(25.0)).volatility_state is VolatilityState.NORMAL


def test_volatility_high() -> None:
    assert assess_volatility(_window(40.0)).volatility_state is VolatilityState.HIGH


def test_volatility_extreme() -> None:
    assert assess_volatility(_window(49.0)).volatility_state is VolatilityState.EXTREME


def test_abnormal_spike_detected() -> None:
    v = assess_volatility(_window(90.0))  # >> 2.5x rolling median (~25)
    assert v.abnormal_spike is True
    assert v.volatility_state is VolatilityState.EXTREME


def test_volatility_does_not_infer_direction() -> None:
    # identical ranges, opposite candle direction -> identical volatility state.
    up = assess_volatility(_window(40.0, bullish=True))
    down = assess_volatility(_window(40.0, bullish=False))
    assert up.volatility_state is down.volatility_state
    assert up.percentile == down.percentile


def test_volatility_deterministic() -> None:
    w = _window(30.0)
    assert assess_volatility(w) == assess_volatility(w)


# --------------- session ---------------
def test_session_asian() -> None:
    # 02:00 UTC -> Asian window; London 02:00 / NY 21:00 previous day, both closed.
    assert (
        assess_session(datetime(2026, 7, 15, 2, 0, tzinfo=UTC)).session_context
        is SessionContext.ASIAN
    )


def test_session_london_preopen() -> None:
    # winter 07:30 UTC -> London 07:30 GMT (pre-open 07:00-08:00), NY closed.
    assert (
        assess_session(datetime(2026, 1, 15, 7, 30, tzinfo=UTC)).session_context
        is SessionContext.LONDON_PREOPEN
    )


def test_session_london() -> None:
    # winter 09:00 UTC -> London 09:00 GMT (active), NY 04:00 (closed).
    assert (
        assess_session(datetime(2026, 1, 15, 9, 0, tzinfo=UTC)).session_context
        is SessionContext.LONDON
    )


def test_session_new_york_preopen() -> None:
    # winter 12:30 UTC -> NY 07:30 EST (pre-open); salient over concurrent London.
    assert (
        assess_session(datetime(2026, 1, 15, 12, 30, tzinfo=UTC)).session_context
        is SessionContext.NEW_YORK_PREOPEN
    )


def test_session_new_york() -> None:
    # winter 18:00 UTC -> NY 13:00 EST (active), London 18:00 GMT (closed).
    assert (
        assess_session(datetime(2026, 1, 15, 18, 0, tzinfo=UTC)).session_context
        is SessionContext.NEW_YORK
    )


def test_session_overlap() -> None:
    # winter 14:00 UTC -> London 14:00 GMT (active) + NY 09:00 EST (active).
    assert (
        assess_session(datetime(2026, 1, 15, 14, 0, tzinfo=UTC)).session_context
        is SessionContext.LONDON_NY_OVERLAP
    )


def test_session_post_ny() -> None:
    # winter 21:45 UTC -> NY 16:45 EST (closed, >=17:00? no 16:45<17 active)...
    # use 22:30 -> asian window; use 21:15 winter -> NY 16:15 active. Choose a gap:
    # summer 21:30 UTC -> NY 17:30 EDT (closed), London 22:30 (closed), not asian.
    assert (
        assess_session(datetime(2026, 7, 15, 21, 30, tzinfo=UTC)).session_context
        is SessionContext.POST_NY
    )


def test_london_dst_boundary_changes_session() -> None:
    # same UTC 07:30: winter -> LONDON_PREOPEN (GMT 07:30); summer -> LONDON (BST 08:30)
    winter = assess_session(datetime(2026, 1, 15, 7, 30, tzinfo=UTC)).session_context
    summer = assess_session(datetime(2026, 7, 15, 7, 30, tzinfo=UTC)).session_context
    assert winter is SessionContext.LONDON_PREOPEN
    assert summer is SessionContext.LONDON


def test_new_york_dst_boundary_changes_session() -> None:
    # same UTC 21:30: winter -> NY 16:30 EST (active) NEW_YORK; summer -> NY 17:30 EDT
    # (closed) POST_NY.
    winter = assess_session(datetime(2026, 1, 15, 21, 30, tzinfo=UTC)).session_context
    summer = assess_session(datetime(2026, 7, 15, 21, 30, tzinfo=UTC)).session_context
    assert winter is SessionContext.NEW_YORK
    assert summer is SessionContext.POST_NY


def test_mismatched_dst_week_resolves_deterministically() -> None:
    # late Oct 2026: London back on GMT (last Sun Oct), NY still on EDT (until Nov).
    ts = datetime(2026, 10, 28, 13, 0, tzinfo=UTC)
    first = assess_session(ts)
    second = assess_session(ts)
    assert first == second
    assert isinstance(first.session_context, SessionContext)


def test_session_uses_evaluation_timestamp_not_machine_clock() -> None:
    a = assess_session(datetime(2026, 1, 15, 2, 0, tzinfo=UTC)).session_context
    b = assess_session(datetime(2026, 1, 15, 14, 0, tzinfo=UTC)).session_context
    # different evaluation timestamps -> different session (proves it uses the arg)
    assert a is SessionContext.ASIAN
    assert b is SessionContext.LONDON_NY_OVERLAP
