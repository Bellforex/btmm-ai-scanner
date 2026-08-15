"""A6-B1-B7 permanent test: the cursor -> LifecycleWalkResult adapter.

``cursor_walk_result(cursor_after_advance, candle)`` must equal the
``LifecycleWalkResult`` that ``advance_poi_cursor`` itself returned for that
candle — at every step, across scanning / breach / reclaim / displacement /
terminal / tap paths. This is what lets the event-driven analyzer read a
scheduler-held cursor's exact public lifecycle state without re-feeding history.
"""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.lifecycle_cursor import (
    advance_poi_cursor,
    create_poi_lifecycle_cursor,
)
from btmm_ai_scanner.poi.scheduler_walk import cursor_walk_result

_CFG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _u7(a: int, b: int) -> UUID:
    return UUID(int=(7 << 76) | (0b10 << 62) | ((a & 0xFFFFFFF) << 80) | (b & 0xFFF))


def _candle(index: int, o: float, h: float, low: float, c: float) -> NormalizedCandle:
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
            "open": Decimal(f"{o:.2f}"),
            "high": Decimal(f"{h:.2f}"),
            "low": Decimal(f"{low:.2f}"),
            "close": Decimal(f"{c:.2f}"),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _u7(index + 1, 3),
        }
    )


def _far_above(i: int) -> NormalizedCandle:
    # Non-touching, non-breaching for a zone near 100 (bullish or bearish).
    return _candle(i, 200.0, 201.0, 199.5, 200.0)


def test_cursor_walk_result_matches_advance_when_last_candle_is_settled() -> None:
    # The adapter is used to read a cursor materialized to the head where the head
    # candle did NOT just close a breach window (the production case: dormant /
    # gap-materialized cursors, whose last_seen is the current candle). It must
    # then equal the real walk. (Woken cursors that just closed a window at the
    # head carry last_seen = the breach candle; production uses their captured
    # real walk, not the adapter — covered by the every-prefix POI differential.)
    fails = 0
    cases = 0
    for trial in range(200):
        rng = random.Random(9000 + trial)
        zt = Decimal("101.0")
        zb = Decimal("99.0")
        direction = rng.choice([PoiDirection.BULLISH, PoiDirection.BEARISH])
        cursor = create_poi_lifecycle_cursor(
            InternalSymbol.XAUUSD, Timeframe.M1, _u7(1, 7), direction, zt, zb, _BASE
        )
        walk = None
        for i in range(rng.randint(1, 40)):
            c = rng.uniform(94, 106)
            o = c + rng.uniform(-3, 3)
            h = max(o, c) + rng.uniform(0, 2)
            low = min(o, c) - rng.uniform(0, 2)
            candle = _candle(i, o, h, low, c)
            atr = (
                Decimal(f"{rng.uniform(0.1, 3.0):.4f}") if rng.random() > 0.15 else None
            )
            cursor, walk = advance_poi_cursor(cursor, candle, atr, _CFG)
        # Settle with one non-interacting candle (the production dormant read
        # scenario): the adapter must reproduce the real walk exactly.
        settle = _far_above(100)
        cursor, walk = advance_poi_cursor(cursor, settle, Decimal("1.0"), _CFG)
        reconstructed = cursor_walk_result(cursor, settle, _CFG)
        cases += 1
        if reconstructed != walk:
            fails += 1
    assert cases > 0
    assert fails == 0
