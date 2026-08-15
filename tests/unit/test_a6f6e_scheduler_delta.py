"""A6-F6E: delta-driven POI scheduler operation gates.

The scheduler carries a parallel registration purely in the stored cursor now
(the redundant ``regs`` map is gone), so an ordinary candle that wakes no POI
must touch ZERO history-proportional structures, and an event candle must write
only the woken POIs -- never the whole registered population. These permanent
counters (``PoiEventScheduler.ops``) make that observable and regression-proof.
Correctness (byte-identical lifecycle) stays covered by the every-prefix
bruteforce differential in test_a6b1b_scheduler.py; this file asserts the
*operation counts*, which the bruteforce does not.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.lifecycle_scheduler import (
    PoiEventScheduler,
    PoiSpec,
    advance_scheduler,
    create_scheduler,
)

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


def _quiet_candle(index: int) -> NormalizedCandle:
    # Above every zone (bullish/support zones live in [94.5, 105.0]). For a
    # BULLISH POI a candle above the zone is neither a touch (no overlap) nor a
    # breach (a breach is price failing BELOW support) -> a truly quiet candle.
    return _candle(index, 200.0, 200.5, 199.5, 200.2)


def _spec(seed: int, center: float, avail_index: int) -> PoiSpec:
    # All BULLISH so a candle above the zones never breaches (breach = below).
    return PoiSpec(
        record_id=_u7(100000 + seed, 9),
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        direction=PoiDirection.BULLISH,
        zone_top=Decimal(f"{center + 0.5:.2f}"),
        zone_bottom=Decimal(f"{center - 0.5:.2f}"),
        availability_time_utc=_candle(
            avail_index, 100, 100, 100, 100
        ).availability_time_utc,
    )


def _build_dormant_registry(
    n: int,
) -> tuple[PoiEventScheduler, list[NormalizedCandle], list[Decimal | None]]:
    """A scheduler with ``n`` POIs all STARTED and committed (dormant): every POI
    is registered in the touch/breach indexes but none is pre-start, in-tap, or
    mid-window, so an ordinary far candle wakes nothing."""
    candles: list[NormalizedCandle] = []
    atrs: list[Decimal | None] = []
    scheduler = create_scheduler(_CFG)
    # Candle 0 (quiet) creates all POIs (availability == candle 0). Pre-start.
    candles.append(_quiet_candle(0))
    atrs.append(Decimal("1.0"))
    specs = [_spec(i, 95.0 + (i % 20) * 0.5, 0) for i in range(n)]
    scheduler = advance_scheduler(scheduler, candles, atrs, new_pois=specs)
    # Feed several more quiet candles: candle 1 starts them (avail > poi avail),
    # subsequent non-touching non-breaching candles commit them to dormant.
    for idx in range(1, 4):
        candles.append(_quiet_candle(idx))
        atrs.append(Decimal("1.0"))
        scheduler = advance_scheduler(scheduler, candles, atrs)
    return scheduler, candles, atrs


def test_no_event_candle_does_zero_history_proportional_work() -> None:
    for n in (50, 200, 800):
        scheduler, candles, atrs = _build_dormant_registry(n)
        assert scheduler.total_count == 4
        # One more ordinary quiet candle: no touch, no breach, no due, no delta.
        candles.append(_quiet_candle(4))
        atrs.append(Decimal("1.0"))
        scheduler = advance_scheduler(scheduler, candles, atrs)
        ops = scheduler.ops
        assert len(scheduler.woken_ids) == 0, (n, scheduler.woken_ids)
        assert ops.cursor_writes == 0, (n, ops)
        assert ops.cursor_deletes == 0, (n, ops)
        assert ops.touch_index_writes == 0, (n, ops)
        assert ops.breach_index_writes == 0, (n, ops)
        assert ops.due_writes == 0, (n, ops)


def test_no_event_ops_independent_of_population() -> None:
    # The whole point of delta-driven scheduling: a quiet candle costs the same
    # whether 50 or 800 POIs are registered (scales with wakes, not population).
    results = []
    for n in (50, 800):
        scheduler, candles, atrs = _build_dormant_registry(n)
        candles.append(_quiet_candle(4))
        atrs.append(Decimal("1.0"))
        scheduler = advance_scheduler(scheduler, candles, atrs)
        o = scheduler.ops
        results.append(
            (o.cursor_writes, o.touch_index_writes, o.breach_index_writes, o.due_writes)
        )
    assert results[0] == results[1] == (0, 0, 0, 0), results


def test_event_candle_writes_only_woken_pois() -> None:
    # Many dormant bullish POIs, zone centers in [95.0, 104.5]. A candle at the
    # TOP of that range touches only the top bands and, being ABOVE every lower
    # zone, breaches none of them -> the woken set is a strict subset of the
    # population, and cursor writes equal exactly the woken count (never more).
    n = 200
    scheduler, candles, atrs = _build_dormant_registry(n)
    candles.append(_candle(4, 104.5, 104.55, 104.45, 104.5))
    atrs.append(Decimal("1.0"))
    scheduler = advance_scheduler(scheduler, candles, atrs)
    ops = scheduler.ops
    assert 0 < len(scheduler.woken_ids) < n, len(scheduler.woken_ids)
    # Work is proportional to WAKES, never the registered population.
    assert ops.cursor_writes == len(scheduler.woken_ids), (
        ops.cursor_writes,
        len(scheduler.woken_ids),
    )
    # They stay started and non-terminal (a touch is not a registration change),
    # so no touch/breach index writes at all -- only the woken cursors advance.
    assert ops.touch_index_writes == 0, ops
    assert ops.breach_index_writes == 0, ops
