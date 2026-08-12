"""A6-B1-B permanent tests: the dormant-cursor fast-forward primitive.

A fast-forward jump over K provably-no-op candles followed by one real advance
must yield a cursor byte-identical to K+1 sequential ``advance_poi_cursor`` calls
over the same candles — covering pre-start, post-start dormant, and terminal
cursors. This is the equivalence the event scheduler relies on to skip dormant
cursors without replaying history.
"""

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.cursor_fast_forward import fast_forward_poi_cursor
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.lifecycle_cursor import (
    PoiLifecycleCursor,
    advance_poi_cursor,
    create_poi_lifecycle_cursor,
)

_CFG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _u7(a: int, b: int) -> UUID:
    # Valid UUIDv7: version nibble 7 (bits 76-79), variant 0b10 (bits 62-63).
    return UUID(int=(7 << 76) | (0b10 << 62) | ((a & 0xFFFF) << 80) | (b & 0xFFF))


def _candle(index: int, o: str, h: str, low: str, c: str) -> NormalizedCandle:
    et = _BASE + timedelta(minutes=index)
    av = et + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _u7(index + 1, 1),
            "content_fingerprint": "a" * 64,
            "raw_candle_id": _u7(index + 1, 2),
            "provider": "FXCM",
            "source_reference": "r",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M1.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": et,
            "availability_time_utc": av,
            "processing_time_utc": av,
            "original_event_time": et,
            "original_availability_time": av,
            "original_timezone": "UTC",
            "open": Decimal(o),
            "high": Decimal(h),
            "low": Decimal(low),
            "close": Decimal(c),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _u7(index + 1, 3),
        }
    )


# Zone well below the "far-above" no-op candles.
_ZT = Decimal("100")
_ZB = Decimal("99")
_AVAIL = _BASE  # POI available at t0; candle 0's availability (t0+1m) > avail.


def _far_above(index: int) -> NormalizedCandle:
    # Entirely above the zone: does not touch (low > zone_top) and (bullish) does
    # not breach (close above zone, never below zone_bottom by tolerance).
    return _candle(index, "200", "201", "199.5", "200")


def _touching(index: int) -> NormalizedCandle:
    # Straddles the zone: touches (low <= zone_top and high >= zone_bottom).
    return _candle(index, "99.5", "100.5", "98.5", "99.5")


def _make_cursor() -> PoiLifecycleCursor:
    return create_poi_lifecycle_cursor(
        InternalSymbol.XAUUSD,
        Timeframe.M1,
        _u7(50000, 7),
        PoiDirection.BULLISH,
        _ZT,
        _ZB,
        _AVAIL,
    )


def _feed_all(candles: list[NormalizedCandle]) -> PoiLifecycleCursor:
    cursor = _make_cursor()
    for cndl in candles:
        cursor, _walk = advance_poi_cursor(cursor, cndl, None, _CFG)
    return cursor


def test_fast_forward_post_start_dormant_matches_sequential() -> None:
    # Candle 0 starts the cursor (availability > POI avail) and is far-above =>
    # post-start, scanning, dormant. Candles 1..K far-above (no-op). Candle K+1
    # touches (a real advance).
    gap = 25
    candles = [_far_above(0)]
    candles += [_far_above(i) for i in range(1, gap + 1)]
    candles += [_touching(gap + 1)]

    reference = _feed_all(candles)

    # Optimized: advance candle 0 (start), fast-forward across candles 1..gap,
    # then advance the touching candle.
    cursor = _make_cursor()
    cursor, _ = advance_poi_cursor(cursor, candles[0], None, _CFG)
    # After candle 0, total_count == 1; jump to total_count == gap + 1 (consumed
    # candles 1..gap as no-ops), then advance candle index gap+1.
    cursor = fast_forward_poi_cursor(cursor, gap + 1)
    cursor, walk = advance_poi_cursor(cursor, candles[-1], None, _CFG)

    assert asdict(cursor) == asdict(reference)
    # Sanity: the touching candle registered a tap.
    assert walk.tap_count == 1


def test_fast_forward_pre_start_matches_sequential() -> None:
    # POI available far in the future => early candles are pre-start (no candle
    # after availability). Fast-forward across them, then feed the first eligible.
    future_avail = _BASE + timedelta(days=365)
    gap = 15

    def make() -> PoiLifecycleCursor:
        return create_poi_lifecycle_cursor(
            InternalSymbol.XAUUSD,
            Timeframe.M1,
            _u7(50001, 7),
            PoiDirection.BULLISH,
            _ZT,
            _ZB,
            future_avail,
        )

    candles = [_far_above(i) for i in range(gap)]

    reference = make()
    for cndl in candles:
        reference, _ = advance_poi_cursor(reference, cndl, None, _CFG)

    optimized = make()
    optimized = fast_forward_poi_cursor(optimized, gap)

    assert asdict(optimized) == asdict(reference)
    # Both are still pre-start.
    assert optimized.start_index is None


def test_fast_forward_terminal_matches_sequential() -> None:
    # Drive the cursor to terminal (genuine invalidation) with a 3-bar breach
    # window, then fast-forward over non-touching candles.
    # Bullish genuine invalidation: 3 consecutive strong breaches (close far
    # below zone_bottom), with >=2 qualifying and bar3 qualifying.
    def breach(i: int) -> NormalizedCandle:
        return _candle(i, "90", "91", "89", "90")

    start = _far_above(0)
    # Initial breach at candle 1, then a full reclaim_window_bars (3) of breaches
    # => genuine invalidation (terminal) at candle 4.
    candles = [start, breach(1), breach(2), breach(3), breach(4)]
    seq = _feed_all(candles)
    assert seq.terminal is True

    # Now extend with far-above (non-touching) no-op candles.
    tail = [_far_above(i) for i in range(5, 5 + 20)]
    reference = seq
    for cndl in tail:
        reference, _ = advance_poi_cursor(reference, cndl, None, _CFG)

    optimized = fast_forward_poi_cursor(seq, seq.total_count + len(tail))
    assert asdict(optimized) == asdict(reference)
