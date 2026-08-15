"""A6-B1-A permanent tests: the resumable POI lifecycle cursor reproduces the
unchanged batch ``run_poi_lifecycle`` byte-for-byte at every prefix, over every
reachable lifecycle path, with a bounded replay buffer (no history-tail replay).
"""

import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleStatus
from btmm_ai_scanner.poi.lifecycle import LifecycleWalkResult, run_poi_lifecycle
from btmm_ai_scanner.poi.lifecycle_cursor import (
    advance_poi_cursor,
    create_poi_lifecycle_cursor,
)

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_CFG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_RECLAIM = _CFG.reclaim_window_bars
_DISP = _CFG.displacement_window_bars


def _dec(value: float | str) -> Decimal:
    return Decimal(value) if isinstance(value, str) else Decimal(f"{value:.2f}")


def _candle(
    i: int, o: float | str, h: float | str, low: float | str, c: float | str
) -> NormalizedCandle:
    et = _BASE + timedelta(minutes=i)
    av = et + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f490-1234-7abc-8def-{i:012x}"),
            "content_fingerprint": "a" * 64,
            "raw_candle_id": UUID("0193f490-1234-7abc-8def-abcdefabcdaa"),
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
            "open": _dec(o),
            "high": _dec(h),
            "low": _dec(low),
            "close": _dec(c),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": UUID("0193f490-1234-7abc-8def-abcdefabcdff"),
        }
    )


def _result_key(r: LifecycleWalkResult) -> tuple[object, ...]:
    return (
        tuple(
            (
                t.transition_type,
                str(t.triggering_candle_record_id),
                t.event_time_utc,
                t.availability_time_utc,
            )
            for t in r.transitions
        ),
        r.final_status,
        r.freshness_status,
        r.tap_count,
        r.tap_classification,
        r.age_in_confirmed_bars,
        None if r.last_seen_candle is None else str(r.last_seen_candle.record_id),
    )


def _assert_cursor_matches_every_prefix(
    candles: list[NormalizedCandle],
    zone_top: Decimal,
    zone_bottom: Decimal,
    direction: PoiDirection,
    poi_availability: datetime,
    poi_id: UUID,
) -> tuple[int, PoiLifecycleStatus]:
    cursor = create_poi_lifecycle_cursor(
        InternalSymbol.XAUUSD,
        Timeframe.M1,
        poi_id,
        direction,
        zone_top,
        zone_bottom,
        poi_availability,
    )
    max_buffer = 0
    final_status = PoiLifecycleStatus.NO_BREACH
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        atr = compute_atr_series(prefix, 14)
        cursor, got = advance_poi_cursor(cursor, candles[k - 1], atr[k - 1], _CFG)
        expected = run_poi_lifecycle(
            prefix,
            atr,
            InternalSymbol.XAUUSD,
            Timeframe.M1,
            poi_id,
            direction,
            zone_top,
            zone_bottom,
            poi_availability,
            _CFG,
        )
        assert _result_key(got) == _result_key(expected), f"prefix {k}"
        max_buffer = max(max_buffer, len(cursor.candle_buffer))
        final_status = got.final_status
    return max_buffer, final_status


def _random_walk(seed: int, n: int, spread: float = 3.0) -> list[NormalizedCandle]:
    rng = random.Random(seed)
    price = 100.0
    out = []
    for i in range(n):
        price += rng.uniform(-spread, spread)
        o = price
        c = price + rng.uniform(-spread + 0.5, spread - 0.5)
        h = max(o, c) + rng.uniform(0, 1.2)
        low = min(o, c) - rng.uniform(0, 1.2)
        out.append(_candle(i, o, h, low, c))
    return out


def test_cursor_matches_batch_every_prefix_randomized_all_paths() -> None:
    seen_status: Counter[str] = Counter()
    max_buffer = 0
    for trial in range(120):
        rng = random.Random(9000 + trial)
        n = rng.randint(3, 55)
        candles = _random_walk(trial, n)
        anchor = candles[rng.randint(0, min(4, n - 1))]
        zc = float(anchor.close)
        zh = rng.uniform(0.05, 1.2)
        ztop = Decimal(f"{zc + zh / 2:.2f}")
        zbot = Decimal(f"{zc - zh / 2:.2f}")
        direction = rng.choice([PoiDirection.BULLISH, PoiDirection.BEARISH])
        avail = candles[rng.randint(0, n - 1)].availability_time_utc
        poi_id = UUID(f"0193f490-aaaa-7abc-8def-{trial:012x}")
        buf, status = _assert_cursor_matches_every_prefix(
            candles, ztop, zbot, direction, avail, poi_id
        )
        seen_status[status.value] += 1
        max_buffer = max(max_buffer, buf)
    # Bounded replay buffer: never a history tail (<= reclaim + displacement + 1).
    assert max_buffer <= _RECLAIM + _DISP + 1
    # Coverage: the randomized corpus reaches terminal and non-terminal outcomes.
    assert seen_status[PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED.value] > 0
    assert seen_status[PoiLifecycleStatus.NO_BREACH.value] > 0


def test_cursor_pre_start_and_no_breach_and_taps() -> None:
    # Flat candles that touch the zone in separated runs -> tap counting; POI
    # availability late so early candles are pre-start (empty walk).
    candles = [_candle(i, "100", "100.2", "99.8", "100.0") for i in range(10)]
    ztop = Decimal("100.05")
    zbot = Decimal("99.95")
    _assert_cursor_matches_every_prefix(
        candles,
        ztop,
        zbot,
        PoiDirection.BULLISH,
        candles[2].availability_time_utc,
        UUID("0193f490-bbbb-7abc-8def-000000000001"),
    )


def test_cursor_gap_away_breach_no_zone_touch() -> None:
    # A gap-away candle whose close is far below a bullish zone breaches it
    # without ever touching the zone (proves breach != zone overlap).
    candles = [
        _candle(0, "100", "100.3", "99.9", "100.1"),
        _candle(1, "100.1", "100.3", "100.0", "100.2"),
        _candle(2, "100.2", "100.4", "100.1", "100.3"),
        _candle(3, "96.0", "96.2", "95.5", "95.6"),  # gap down, closes far below
        _candle(4, "95.6", "95.8", "95.3", "95.4"),
        _candle(5, "95.4", "95.6", "95.1", "95.2"),
    ]
    _assert_cursor_matches_every_prefix(
        candles,
        Decimal("100.30"),
        Decimal("100.00"),
        PoiDirection.BULLISH,
        candles[0].availability_time_utc,
        UUID("0193f490-cccc-7abc-8def-000000000001"),
    )


def test_cursor_no_lookahead_across_reclaim_and_displacement_windows() -> None:
    # Drive many randomized narrow-zone POIs and assert exact equality at EVERY
    # prefix. Because the cursor only ever sees candles <= the current prefix,
    # per-prefix equality with the batch (also over <= prefix) is a no-lookahead
    # proof across breach/reclaim/reclaim-timeout/displacement/genuine paths.
    for trial in range(60):
        rng = random.Random(20000 + trial)
        n = rng.randint(6, 40)
        candles = _random_walk(trial + 500, n, spread=2.5)
        anchor = candles[0]
        zh = rng.uniform(0.05, 0.6)
        zc = float(anchor.close)
        _assert_cursor_matches_every_prefix(
            candles,
            Decimal(f"{zc + zh / 2:.2f}"),
            Decimal(f"{zc - zh / 2:.2f}"),
            rng.choice([PoiDirection.BULLISH, PoiDirection.BEARISH]),
            candles[0].availability_time_utc,
            UUID(f"0193f490-dddd-7abc-8def-{trial:012x}"),
        )


def test_cursor_terminal_freeze_taps_still_evolve() -> None:
    # After genuine invalidation the breach walk is frozen but tap counting
    # continues (a later candle touching the zone must still update taps) — the
    # every-prefix equality asserts this against the batch.
    candles = [
        _candle(0, "100.0", "100.2", "99.9", "100.1"),
        _candle(1, "97.0", "97.2", "96.8", "96.9"),  # breach 1
        _candle(2, "96.9", "97.1", "96.7", "96.8"),  # breach 2
        _candle(3, "96.8", "97.0", "96.6", "96.7"),  # breach 3 -> genuine
        _candle(4, "96.7", "96.9", "96.5", "96.6"),
        _candle(
            5, "99.9", "100.3", "99.8", "100.2"
        ),  # touches zone again post-terminal
        _candle(6, "100.2", "100.4", "100.0", "100.3"),
    ]
    _, status = _assert_cursor_matches_every_prefix(
        candles,
        Decimal("100.20"),
        Decimal("99.90"),
        PoiDirection.BULLISH,
        candles[0].availability_time_utc,
        UUID("0193f490-eeee-7abc-8def-000000000001"),
    )
    assert status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
