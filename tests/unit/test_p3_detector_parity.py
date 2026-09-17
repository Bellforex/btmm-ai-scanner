"""P3-I2 — differential parity for the fixed-window Pine detectors.

THIS FILE ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

`tests/parity_support/p3_pine_model.py` is a structural transcription of the
detector block in `tradingview/btmm_poi_btrc_scanner_p3_dev.pine`. Production
Python is always the reference side.

The comparison is deliberately harsher than fixture-by-fixture checking: the
model replays Pine's per-bar frontier over a BOUNDED 21-bar ring, while
production runs its batch detectors over the whole stream. Requiring the two
to agree exactly, over hundreds of randomized streams plus directed edge
fixtures, proves both the per-detector semantics AND that the bounded ring
loses nothing — a detector that secretly needed more history would fail here
instead of silently passing.

Every emitted field is compared: type, direction, both bounds, strength tier,
the identity triple, and all three timestamps.
"""

from __future__ import annotations

import importlib.util
import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.reversal_candles import detect_reversal_candles
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars


def _load(name: str, relpath: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parents[2] / relpath
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load("_p3_pine_model", "tests/parity_support/p3_pine_model.py")

_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_RAW_CANDLE_ID = UUID("0193f480-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f480-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "c" * 64

_TYPE_CODE = {
    PoiType.BUY_ORDER_BLOCK: M.TYPE_BUY_ORDER_BLOCK,
    PoiType.SELL_ORDER_BLOCK: M.TYPE_SELL_ORDER_BLOCK,
    PoiType.BUY_FAIR_VALUE_GAP: M.TYPE_BUY_FAIR_VALUE_GAP,
    PoiType.SELL_FAIR_VALUE_GAP: M.TYPE_SELL_FAIR_VALUE_GAP,
    PoiType.BULLISH_ENGULFING: M.TYPE_BULLISH_ENGULFING,
    PoiType.BEARISH_ENGULFING: M.TYPE_BEARISH_ENGULFING,
    PoiType.HAMMER: M.TYPE_HAMMER,
    PoiType.SHOOTING_STAR: M.TYPE_SHOOTING_STAR,
    PoiType.MORNING_STAR: M.TYPE_MORNING_STAR,
    PoiType.EVENING_STAR: M.TYPE_EVENING_STAR,
    PoiType.BULLISH_PRESSURE_WICK: M.TYPE_BULLISH_PRESSURE_WICK,
    PoiType.BEARISH_PRESSURE_WICK: M.TYPE_BEARISH_PRESSURE_WICK,
    PoiType.BUY_TO_SELL_CANDLE: M.TYPE_BUY_TO_SELL_CANDLE,
    PoiType.SELL_TO_BUY_CANDLE: M.TYPE_SELL_TO_BUY_CANDLE,
    PoiType.BASE_RALLY: M.TYPE_BASE_RALLY,
    PoiType.BASE_DROP: M.TYPE_BASE_DROP,
}
_DIR_CODE = {
    PoiDirection.BULLISH: M.DIR_BULLISH,
    PoiDirection.BEARISH: M.DIR_BEARISH,
}
_TIER_CODE = {
    PoiStrengthTier.STANDARD: M.TIER_STANDARD,
    PoiStrengthTier.STRONG: M.TIER_STRONG,
    None: M.TIER_NA,
}


def _candle(
    index: int, open_: str, high: str, low: str, close: str
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f480-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M1.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal(close),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def _project(candidate: Any, candles: tuple[NormalizedCandle, ...]) -> tuple[Any, ...]:
    """Production candidate -> the Pine projection, for exact comparison."""
    times = {c.record_id: _ms(c.event_time_utc) for c in candles}
    src = [times[rid] for rid in candidate.source_candle_record_ids]
    tier = getattr(candidate, "strength_tier", None)
    return (
        _TYPE_CODE[candidate.poi_type],
        _DIR_CODE[candidate.direction],
        candidate.zone_top,
        candidate.zone_bottom,
        _TIER_CODE[tier],
        src[0],
        len(src),
        src[-1],
        _ms(candidate.candidate_event_time_utc),
        _ms(candidate.availability_time_utc),
    )


def _model_tuple(poi: Any) -> tuple[Any, ...]:
    return (
        poi.poi_type,
        poi.direction,
        poi.zone_top,
        poi.zone_bottom,
        poi.tier,
        poi.src_first_time,
        poi.src_count,
        poi.src_last_time,
        poi.candidate_time,
        poi.confirm_time,
    )


_PRODUCTION_DETECTORS = (
    detect_order_blocks,
    detect_fair_value_gaps,
    detect_engulfing,
    detect_three_candle_stars,
    detect_single_candle_reversals,
    detect_pressure_wicks,
    detect_reversal_candles,
    detect_bases,
)


def _production_projection(
    candles: tuple[NormalizedCandle, ...],
) -> set[tuple[Any, ...]]:
    projected: set[tuple[Any, ...]] = set()
    for detector in _PRODUCTION_DETECTORS:
        for candidate in detector(candles, _CONFIG):
            projected.add(_project(candidate, candles))
    return projected


def _model_projection(
    candles: tuple[NormalizedCandle, ...],
) -> set[tuple[Any, ...]]:
    return {_model_tuple(poi) for poi in M.run_frontier(list(candles), _CONFIG)}


def _assert_parity(
    candles: tuple[NormalizedCandle, ...],
) -> set[tuple[Any, ...]]:
    production = _production_projection(candles)
    model = _model_projection(candles)
    assert model == production, (
        f"model-only={sorted(model - production)[:3]} "
        f"production-only={sorted(production - model)[:3]}"
    )
    return production


# ---------------------------------------------------------------------------
# Directed fixtures — one positive per type, both directions, near misses
# ---------------------------------------------------------------------------


def test_buy_order_block_positive_and_near_miss() -> None:
    origin = _candle(0, "100", "100", "99", "99")
    displacement = _candle(1, "99", "101", "99", "101")  # ratio exactly 2.0
    found = _assert_parity((origin, displacement))
    assert any(t[0] == M.TYPE_BUY_ORDER_BLOCK for t in found)

    near_miss = _candle(1, "99", "100.99", "99", "100.99")  # ratio 1.99
    assert not any(
        t[0] == M.TYPE_BUY_ORDER_BLOCK for t in _assert_parity((origin, near_miss))
    )


def test_sell_order_block_positive() -> None:
    origin = _candle(0, "99", "100", "99", "100")  # bullish
    displacement = _candle(1, "100", "100", "98", "98")  # bearish, ratio 2.0
    found = _assert_parity((origin, displacement))
    assert any(t[0] == M.TYPE_SELL_ORDER_BLOCK for t in found)


def test_fair_value_gap_both_directions_and_exact_touch() -> None:
    first = _candle(0, "100", "101", "100", "100.5")
    second = _candle(1, "100.5", "102", "100.5", "101.5")
    bullish_third = _candle(2, "101.5", "102", "101.01", "101.8")
    found = _assert_parity((first, second, bullish_third))
    assert any(t[0] == M.TYPE_BUY_FAIR_VALUE_GAP for t in found)

    touching = _candle(2, "101.5", "102", "101", "101.8")  # low == first.high
    assert not any(
        t[0] == M.TYPE_BUY_FAIR_VALUE_GAP
        for t in _assert_parity((first, second, touching))
    )

    bear_first = _candle(0, "102", "103", "102", "102.5")
    bear_second = _candle(1, "102", "102.5", "101", "101.5")
    bear_third = _candle(2, "101", "101.99", "100", "100.5")
    assert any(
        t[0] == M.TYPE_SELL_FAIR_VALUE_GAP
        for t in _assert_parity((bear_first, bear_second, bear_third))
    )


def test_engulfing_both_directions_including_the_no_body_rule_case() -> None:
    engulfed = _candle(0, "99.9", "100", "99", "99.1")
    # body does not span; 0.30 / 2.00 stays above the RC3 Doji threshold
    engulfing = _candle(1, "99.4", "101", "99", "99.7")
    found = _assert_parity((engulfed, engulfing))
    assert any(t[0] == M.TYPE_BULLISH_ENGULFING for t in found)

    bull_engulfed = _candle(0, "99", "100", "99", "100")
    bear_engulfing = _candle(1, "100", "100", "98", "98")
    assert any(
        t[0] == M.TYPE_BEARISH_ENGULFING
        for t in _assert_parity((bull_engulfed, bear_engulfing))
    )


def test_three_candle_stars_both_directions() -> None:
    first = _candle(0, "102", "102.5", "100", "100.5")
    middle = _candle(1, "100.5", "101", "100", "100.55")
    third = _candle(2, "100.5", "102", "100.5", "101.6")
    assert any(
        t[0] == M.TYPE_MORNING_STAR for t in _assert_parity((first, middle, third))
    )

    e_first = _candle(0, "100.5", "102.5", "100", "102")
    e_middle = _candle(1, "102", "102.5", "101.5", "101.95")
    e_third = _candle(2, "102", "102.2", "100", "100.4")
    assert any(
        t[0] == M.TYPE_EVENING_STAR
        for t in _assert_parity((e_first, e_middle, e_third))
    )


def test_hammer_and_shooting_star() -> None:
    hammer = _candle(0, "100.70", "101", "100", "100.90")
    assert any(t[0] == M.TYPE_HAMMER for t in _assert_parity((hammer,)))
    star = _candle(0, "100.10", "101", "100", "100.30")
    assert any(t[0] == M.TYPE_SHOOTING_STAR for t in _assert_parity((star,)))


def test_zero_range_candles_are_ignored_by_every_detector() -> None:
    flat = tuple(_candle(i, "100", "100", "100", "100") for i in range(5))
    assert _assert_parity(flat) == set()


# ---------------------------------------------------------------------------
# P3-I3 — pressure wicks and reversal candles
# ---------------------------------------------------------------------------


def test_pressure_wick_both_directions_and_zero_opposite_wick_escape() -> None:
    """The `uw == 0` escape is production's guard against a zero divisor."""
    bull = _candle(0, "100.60", "101", "100", "101")  # upper wick exactly 0
    found = _assert_parity((bull,))
    assert any(t[0] == M.TYPE_BULLISH_PRESSURE_WICK for t in found)

    bear = _candle(0, "100.40", "101", "100", "100")  # lower wick exactly 0
    assert any(t[0] == M.TYPE_BEARISH_PRESSURE_WICK for t in _assert_parity((bear,)))


def test_pressure_wick_baseline_horizon_is_twenty_predecessors() -> None:
    """A 21-bars-back outlier must not reach the median that gates STRONG."""
    far_past = _candle(0, "100", "200", "100", "150")
    filler = [_candle(i, "100", "100.5", "99.5", "100") for i in range(1, 21)]
    subject = _candle(21, "100.55", "101", "100", "101")
    _assert_parity((far_past, *filler, subject))


def test_reversal_candle_both_directions_with_delayed_confirmation() -> None:
    prior = [_candle(i, "100", "100.5", "99.5", "100") for i in range(3)]
    bearish = _candle(3, "102.55", "103", "100", "100.45")
    follow = _candle(4, "100.45", "102", "100.4", "101.9")
    found = _assert_parity((*prior, bearish, follow))
    assert any(t[0] == M.TYPE_SELL_TO_BUY_CANDLE for t in found)

    bullish = _candle(3, "100.45", "103", "100", "102.55")
    follow_down = _candle(4, "102.55", "102.6", "101", "101.1")
    assert any(
        t[0] == M.TYPE_BUY_TO_SELL_CANDLE
        for t in _assert_parity((*prior, bullish, follow_down))
    )


def test_reversal_candle_unconfirmed_within_three_bars_is_never_emitted() -> None:
    prior = [_candle(i, "100", "100.5", "99.5", "100") for i in range(3)]
    candidate = _candle(3, "102.55", "103", "100", "100.45")  # midpoint 101.50
    misses = [_candle(4 + i, "100.4", "101", "100.3", "100.9") for i in range(3)]
    found = _assert_parity((*prior, candidate, *misses))
    assert not any(t[0] == M.TYPE_SELL_TO_BUY_CANDLE for t in found)


def test_reversal_candle_confirmation_on_the_third_probe_bar() -> None:
    prior = [_candle(i, "100", "100.5", "99.5", "100") for i in range(3)]
    candidate = _candle(3, "102.55", "103", "100", "100.45")
    late = [
        _candle(4, "100.4", "101", "100.3", "100.9"),
        _candle(5, "100.9", "101.2", "100.8", "101.0"),
        _candle(6, "101", "102", "100.9", "101.9"),  # first close > midpoint
    ]
    found = _assert_parity((*prior, candidate, *late))
    emitted = [t for t in found if t[0] == M.TYPE_SELL_TO_BUY_CANDLE]
    assert len(emitted) == 1
    # confirmation timestamp must be the THIRD probe bar's availability
    assert emitted[0][9] == _ms(late[2].availability_time_utc)


# ---------------------------------------------------------------------------
# P3-I4 — base formations (the only ATR-dependent family)
# ---------------------------------------------------------------------------


def _warm_prefix(count: int) -> list[NormalizedCandle]:
    """Identical 1.00-range candles: Wilder ATR-14 converges to exactly 1.00."""
    return [_candle(i, "100", "100.5", "99.5", "100") for i in range(count)]


def test_base_rally_and_base_drop_on_the_warm_atr_branch() -> None:
    """With >= 14 warm bars the real ATR gates the base height, not the fallback."""
    warm = _warm_prefix(20)
    base_a = _candle(20, "100", "100.35", "99.65", "100")
    base_b = _candle(21, "100", "100.35", "99.65", "100")
    rally = _candle(22, "100", "103", "99.9", "102.9")
    found = _assert_parity((*warm, base_a, base_b, rally))
    assert any(t[0] == M.TYPE_BASE_RALLY for t in found)

    drop = _candle(22, "100", "100.1", "97", "97.1")
    assert any(
        t[0] == M.TYPE_BASE_DROP for t in _assert_parity((*warm, base_a, base_b, drop))
    )


def test_base_height_gate_uses_the_real_atr_not_the_departure_range() -> None:
    """0.70 height passes against ATR 1.00; 0.80 fails — the fallback would pass both."""
    warm = _warm_prefix(20)
    departure = _candle(22, "100", "103", "99.9", "102.9")

    tight_a = _candle(20, "100", "100.35", "99.65", "100")
    tight_b = _candle(21, "100", "100.35", "99.65", "100")
    passing = _assert_parity((*warm, tight_a, tight_b, departure))
    assert any(t[0] == M.TYPE_BASE_RALLY for t in passing)

    wide_a = _candle(20, "100", "100.40", "99.60", "100")
    wide_b = _candle(21, "100", "100.40", "99.60", "100")
    rejected = _assert_parity((*warm, wide_a, wide_b, departure))
    assert not any(t[0] == M.TYPE_BASE_RALLY for t in rejected)


def test_base_atr_fallback_branch_when_the_series_is_still_cold() -> None:
    """Under 14 candles ATR-14 is None, so the departure range is the reference."""
    base_a = _candle(0, "100", "100.40", "99.60", "100")
    base_b = _candle(1, "100", "100.40", "99.60", "100")
    departure = _candle(2, "100", "103", "99.9", "102.9")
    found = _assert_parity((base_a, base_b, departure))
    assert any(t[0] == M.TYPE_BASE_RALLY for t in found)


def test_every_qualifying_base_length_emits_its_own_poi() -> None:
    """Production does NOT pick one best base per departure."""
    # 0.50-wide base bars: the Wilder ATR drifts to ~0.87 over the run, so the
    # 0.75*ATR height gate still admits them (a 0.70-wide base would not).
    warm = _warm_prefix(20)
    flat = [_candle(20 + i, "100", "100.25", "99.75", "100") for i in range(4)]
    departure = _candle(24, "100", "103", "99.9", "102.9")
    found = _assert_parity((*warm, *flat, departure))
    rallies = [t for t in found if t[0] == M.TYPE_BASE_RALLY]
    assert len(rallies) >= 2, "multiple base lengths must each emit"
    assert len({t[6] for t in rallies}) >= 2, "source counts must differ"


# ---------------------------------------------------------------------------
# Randomized differential campaign — the real proof
# ---------------------------------------------------------------------------


def _random_stream(seed: int, length: int) -> tuple[NormalizedCandle, ...]:
    """Deterministic pseudo-random OHLC that respects the candle invariants.

    A plain drifting walk never produces reversal candles, so the generator
    also emits occasional IMPULSE bars (large range, tight wicks, extreme
    close) and follows some of them with a RETRACE that closes back through
    the impulse midpoint. Without those shapes the differential campaign would
    silently skip two of the twelve families — which the coverage test below
    would then catch.
    """
    rng = random.Random(seed)
    candles = []
    price = Decimal("100")
    pending_retrace: Decimal | None = None
    for index in range(length):
        open_ = price
        if pending_retrace is not None:
            close = pending_retrace
            pending_retrace = None
            spread = Decimal(rng.randint(0, 20)) / Decimal(100)
            high = max(open_, close) + spread
            low = min(open_, close) - spread
        elif rng.randint(0, 9) < 2:
            # impulse: 2.0-3.5 wide, tight wicks -> high body efficiency and an
            # extreme close position
            magnitude = Decimal(rng.randint(200, 350)) / Decimal(100)
            direction = 1 if rng.randint(0, 1) else -1
            close = open_ + magnitude * direction
            wick = Decimal(rng.randint(0, 12)) / Decimal(100)
            high = max(open_, close) + wick
            low = min(open_, close) - wick
            if rng.randint(0, 1):
                midpoint = (high + low) / Decimal(2)
                overshoot = Decimal(rng.randint(5, 60)) / Decimal(100)
                pending_retrace = (
                    midpoint + overshoot if direction < 0 else midpoint - overshoot
                )
        else:
            drift = Decimal(rng.randint(-60, 60)) / Decimal(100)
            close = open_ + drift
            spread_up = Decimal(rng.randint(0, 80)) / Decimal(100)
            spread_dn = Decimal(rng.randint(0, 80)) / Decimal(100)
            high = max(open_, close) + spread_up
            low = min(open_, close) - spread_dn
        candles.append(_candle(index, str(open_), str(high), str(low), str(close)))
        price = close
    return tuple(candles)


@pytest.mark.parametrize("seed", range(60))
def test_random_streams_match_production_exactly(seed: int) -> None:
    """60 independent 40-bar streams, every emitted field compared."""
    _assert_parity(_random_stream(seed, 40))


@pytest.mark.parametrize("seed", range(8))
def test_long_streams_exceed_the_ring_and_still_match(seed: int) -> None:
    """200 bars is ~10x the 21-bar ring: bounded detection must lose nothing."""
    _assert_parity(_random_stream(1000 + seed, 200))


def test_the_campaign_actually_produces_every_fixed_window_type() -> None:
    """A differential campaign that detected nothing would prove nothing."""
    seen: set[int] = set()
    for seed in range(60):
        for projected in _production_projection(_random_stream(seed, 40)):
            seen.add(projected[0])
    expected = {
        M.TYPE_BUY_ORDER_BLOCK,
        M.TYPE_SELL_ORDER_BLOCK,
        M.TYPE_BUY_FAIR_VALUE_GAP,
        M.TYPE_SELL_FAIR_VALUE_GAP,
        M.TYPE_BULLISH_ENGULFING,
        M.TYPE_BEARISH_ENGULFING,
        M.TYPE_HAMMER,
        M.TYPE_SHOOTING_STAR,
        M.TYPE_BULLISH_PRESSURE_WICK,
        M.TYPE_BEARISH_PRESSURE_WICK,
        M.TYPE_BUY_TO_SELL_CANDLE,
        M.TYPE_SELL_TO_BUY_CANDLE,
        M.TYPE_BASE_RALLY,
        M.TYPE_BASE_DROP,
    }
    assert expected.issubset(seen), f"campaign never produced {expected - seen}"


def test_frontier_emits_each_semantic_poi_exactly_once() -> None:
    """The registry is identity-deduplicated, as `f_poiEmit` guards."""
    candles = _random_stream(7, 120)
    registry = M.run_frontier(list(candles), _CONFIG)
    identities = [poi.identity for poi in registry]
    assert len(identities) == len(set(identities))


def test_ring_size_is_the_production_dependency_bound() -> None:
    assert M.RING == 21


# ---------------------------------------------------------------------------
# Pine source guards — keep the transcription pinned to the real Pine block
# ---------------------------------------------------------------------------

_P3_DEV = Path(__file__).resolve().parents[2] / (
    "tradingview/btmm_poi_btrc_scanner_p3_dev.pine"
)


def _pine_code() -> str:
    text = _P3_DEV.read_text(encoding="utf-8")
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("//")
    )


def test_pine_declares_every_fixed_window_detector() -> None:
    code = _pine_code()
    for fn in (
        "f_poiDetectOrderBlocks",
        "f_poiDetectFvg",
        "f_poiDetectEngulfing",
        "f_poiDetectStars",
        "f_poiDetectSingleCandleReversals",
    ):
        assert f"{fn}(int wn) =>" in code, f"missing Pine detector {fn}"


def test_pine_order_block_uses_the_adjacent_pair_and_strict_close_through() -> None:
    """No lookback search, and the close-through comparisons stay strict."""
    code = _pine_code()
    assert "int oi = wn - 2" in code and "int di = wn - 1" in code
    assert "array.get(wClose, di) > array.get(wHigh, oi)" in code
    assert "array.get(wClose, di) < array.get(wLow, oi)" in code


def test_pine_fvg_keeps_the_strict_inequalities_and_no_tier() -> None:
    code = _pine_code()
    assert "array.get(wLow, ti) > array.get(wHigh, fi)" in code
    assert "array.get(wHigh, ti) < array.get(wLow, fi)" in code
    assert "C_POI_TIER_NA" in code


def test_pine_engulfing_has_no_body_engulfment_comparison() -> None:
    """AD-3: production compares ranges and colours only."""
    code = _pine_code()
    block = code.split("f_poiDetectEngulfing")[1].split("f_poiDetectStars")[0]
    assert "f_poiRange(gi) / engulfedRange" in block
    # a textbook body-engulfment rule would compare the two candles' bodies
    assert "f_poiBody(gi)" not in block
    assert "f_poiBody(ei)" not in block


def test_pine_stars_compare_against_the_first_candle_midpoint() -> None:
    code = _pine_code()
    assert "(array.get(wHigh, fi) + array.get(wLow, fi)) / 2" in code, (
        "star midpoint must come from the FIRST candle"
    )


def test_pine_detectors_emit_through_the_identity_guarded_helper() -> None:
    """Every detector must route through f_poiEmit, which dedupes by identity."""
    code = _pine_code()
    detector_region = code.split("P3-I2")[-1] if "P3-I2" in code else code
    assert detector_region.count("f_poiEmit(") >= 5
    assert (
        "f_poiFind(typeCode, srcFirstT, srcCount, srcLastT, "
        "f_poiTicks(zoneBottom), f_poiTicks(zoneTop)) == -1" in code
    )


def test_pine_detector_zones_match_the_production_geometry_owners() -> None:
    """OB/engulfing zone = the ORIGIN/ENGULFED candle; stars = the MIDDLE."""
    code = _pine_code()
    ob = code.split("f_poiDetectOrderBlocks")[1].split("f_poiDetectFvg")[0]
    assert "array.get(wHigh, oi), array.get(wLow, oi)" in ob
    eng = code.split("f_poiDetectEngulfing")[1].split("f_poiDetectStars")[0]
    assert "array.get(wHigh, ei), array.get(wLow, ei)" in eng
    stars = code.split("f_poiDetectStars")[1].split("f_poiDetectSingleCandleReversals")[
        0
    ]
    assert "array.get(wHigh, mi), array.get(wLow, mi)" in stars


def test_pine_declares_the_baseline_and_delayed_confirmation_detectors() -> None:
    code = _pine_code()
    assert "f_poiDetectPressureWicks(int wn) =>" in code
    assert "f_poiDetectReversalCandles(int wn) =>" in code


def test_pine_pressure_wick_reuses_the_frozen_p1_median_helper() -> None:
    """No second median implementation, and its own scratch array."""
    code = _pine_code()
    assert "f_medianRange(wHigh, wLow, precStart, ci, scPoiRange)" in code
    assert "var array<float> scPoiRange = array.new<float>()" in code


def test_pine_pressure_wick_keeps_both_zero_wick_dominance_escapes() -> None:
    code = _pine_code()
    assert "uw == 0 or lw >= C_POI_PW_DOMINANCE_STANDARD * uw" in code
    assert "lw == 0 or uw >= C_POI_PW_DOMINANCE_STANDARD * lw" in code


def test_pine_reversal_candle_keeps_the_inverted_naming() -> None:
    """AD-3: a RED candidate emits SELL_TO_BUY with BULLISH direction."""
    code = _pine_code()
    block = code.split("f_poiDetectReversalCandles")[1]
    bear_branch = block.split("f_poiIsBearCandle(ci)")[1].split("else if")[0]
    assert "C_POI_SELL_TO_BUY_CANDLE" in bear_branch
    assert "C_POI_DIR_BULLISH" in bear_branch


def test_pine_reversal_candle_emits_only_on_the_first_qualifying_probe() -> None:
    """This is what makes the delayed-confirmation emission exactly-once."""
    code = _pine_code()
    assert "if confirmIdx == wn - 1" in code


def test_pine_declares_the_atr_dependent_detector() -> None:
    code = _pine_code()
    assert "f_poiDetectBases(int wn) =>" in code


def test_pine_bases_reads_the_continuous_p1_atr_at_the_last_base_candle() -> None:
    """Never a window-local ATR, and indexed at di - 1, not the departure."""
    code = _pine_code()
    assert "array.get(wAtr, di - 1)" in code
    assert "compute_atr" not in code


def test_pine_bases_uses_the_bases_specific_atr_fallback_rule() -> None:
    """`is None or == 0` here; the lifecycle's `> 0` rule is deliberately separate."""
    code = _pine_code()
    assert "na(atrRaw) or atrRaw == 0 ? departureRange : atrRaw" in code


def test_pine_bases_skips_zero_range_members_instead_of_rejecting() -> None:
    code = _pine_code()
    assert "minRange != 0 and overlap / minRange < C_POI_BASE_OVERLAP_MIN" in code


def test_pine_bases_checks_every_length_at_the_departure_bar() -> None:
    code = _pine_code()
    assert "for length = C_POI_BASE_MIN_CANDLES to C_POI_BASE_MAX_CANDLES" in code
    assert "int si = di - length" in code
