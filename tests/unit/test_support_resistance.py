import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import _finalize, _IdentityResolver
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import (
    DerivedOutputType,
    SupportResistanceType,
    SwingType,
)
from btmm_ai_scanner.domain.support_resistance import (
    SupportResistanceZone,
    detect_support_resistance_zones,
)
from btmm_ai_scanner.domain.swings import ConfirmedSwing

_RAW_CANDLE_ID = UUID("0193f320-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f320-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

_Prices = list[tuple[float, float, float, float]]

_BASELINE: _Prices = [(100.0, 101.0, 99.0, 100.0)] * 20
_SUPPORT_ORIGIN: _Prices = [(100.0, 101.0, 96.0, 100.0)]
_SUPPORT_REACTION: _Prices = [
    (96.5, 98.0, 96.3, 97.8),
    (97.8, 100.0, 97.5, 99.8),
    (99.8, 102.0, 99.6, 101.8),
    (101.8, 104.0, 101.6, 103.8),
    (103.8, 106.0, 103.6, 105.8),
]
_GAP: _Prices = [(100.0, 101.0, 99.0, 100.0)] * 10
_SUPPORT_TOUCH: _Prices = [(100.0, 101.0, 96.05, 100.0)]
_SUPPORT_TOUCH_REACTION: _Prices = [
    (96.55, 98.0, 96.35, 97.85),
    (97.85, 100.0, 97.55, 99.85),
    (99.85, 102.0, 99.65, 101.85),
    (101.85, 104.0, 101.65, 103.85),
    (103.85, 106.0, 103.65, 105.85),
]
_TAIL: _Prices = [(100.0, 101.0, 99.0, 100.0)] * 3

_RESISTANCE_ORIGIN: _Prices = [(100.0, 104.0, 99.0, 100.0)]
_RESISTANCE_REACTION: _Prices = [
    (103.5, 103.7, 102.0, 102.2),
    (102.2, 102.5, 100.0, 100.2),
    (100.2, 100.4, 98.0, 98.2),
    (98.2, 98.4, 96.0, 96.2),
    (96.2, 96.4, 94.0, 94.2),
]
_RESISTANCE_TOUCH: _Prices = [(100.0, 103.95, 99.0, 100.0)]
_RESISTANCE_TOUCH_REACTION: _Prices = [
    (103.45, 103.65, 101.95, 102.15),
    (102.15, 102.45, 99.95, 100.15),
    (100.15, 100.35, 97.95, 98.15),
    (98.15, 98.35, 95.95, 96.15),
    (96.15, 96.35, 93.95, 94.15),
]


def _record_id(index: int) -> UUID:
    return UUID(f"0193f320-1234-7abc-8def-{index:012x}")


def _candle(index: int, o: float, h: float, low: float, c: float) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(str(o)),
            "high": Decimal(str(h)),
            "low": Decimal(str(low)),
            "close": Decimal(str(c)),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _build(
    prices: list[tuple[float, float, float, float]],
) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, *p) for i, p in enumerate(prices))


def _swing(
    swing_index: int,
    swing_type: SwingType,
    price: str,
    pivot_candle_index: int,
    candles: tuple[NormalizedCandle, ...],
    reference_atr: str = "2.0",
) -> ConfirmedSwing:
    pivot_time = candles[pivot_candle_index].event_time_utc
    confirmation_time = pivot_time + timedelta(minutes=6)
    return ConfirmedSwing(
        record_id=_record_id(1000 + swing_index),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=pivot_candle_index,
        pivot_candle_record_ids=(candles[pivot_candle_index].record_id,),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=2),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=candles[pivot_candle_index].record_id,
        pivot_reference_atr=Decimal(reference_atr),
        pivot_tie_tolerance=Decimal("0.02"),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("1"),
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


class _HashIdentityProvider:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        payload = output_type.value + "|" + "|".join(semantic_key)
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


def _support_fixture() -> tuple[
    tuple[NormalizedCandle, ...], ConfirmedSwing, ConfirmedSwing, ConfirmedSwing
]:
    prices = (
        _BASELINE
        + _SUPPORT_ORIGIN
        + _SUPPORT_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _SUPPORT_TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    origin = _swing(1, SwingType.SWING_LOW, "96", 20, candles)
    opposite = _swing(3, SwingType.SWING_HIGH, "106", 25, candles)
    touch = _swing(2, SwingType.SWING_LOW, "96.05", 36, candles)
    return candles, origin, opposite, touch


def _resistance_fixture() -> tuple[
    tuple[NormalizedCandle, ...], ConfirmedSwing, ConfirmedSwing, ConfirmedSwing
]:
    prices = (
        _BASELINE
        + _RESISTANCE_ORIGIN
        + _RESISTANCE_REACTION
        + _GAP
        + _RESISTANCE_TOUCH
        + _RESISTANCE_TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    origin = _swing(1, SwingType.SWING_HIGH, "104", 20, candles)
    opposite = _swing(3, SwingType.SWING_LOW, "94", 25, candles)
    touch = _swing(2, SwingType.SWING_HIGH, "103.95", 36, candles)
    return candles, origin, opposite, touch


def test_support_resistance_zone_boundaries_derive_from_origin_swing_and_horizontal_depth() -> (
    None
):
    candles, origin, opposite, touch = _support_fixture()
    zones = detect_support_resistance_zones(candles, (origin, opposite, touch), _CONFIG)

    assert len(zones) == 1
    zone = zones[0]
    expected_depth = (
        _CONFIG.support_resistance_zone_depth_atr_multiplier
        * origin.pivot_reference_atr
    )
    assert zone.zone_bottom == origin.pivot_price
    assert zone.zone_depth == expected_depth
    assert zone.zone_top == zone.zone_bottom + expected_depth
    assert zone.creator_reference_atr == origin.pivot_reference_atr


def test_support_zone_confirms_after_second_distinct_qualifying_touch() -> None:
    candles, origin, opposite, touch = _support_fixture()
    zones = detect_support_resistance_zones(candles, (origin, opposite, touch), _CONFIG)

    assert len(zones) == 1
    assert zones[0].zone_type == SupportResistanceType.SUPPORT
    assert zones[0].origin_swing_record_id == origin.record_id
    assert touch.record_id in zones[0].qualifying_touch_swing_record_ids


def test_resistance_zone_confirms_after_second_distinct_qualifying_touch() -> None:
    candles, origin, opposite, touch = _resistance_fixture()
    zones = detect_support_resistance_zones(candles, (origin, opposite, touch), _CONFIG)

    assert len(zones) == 1
    assert zones[0].zone_type == SupportResistanceType.RESISTANCE
    assert zones[0].origin_swing_record_id == origin.record_id
    assert touch.record_id in zones[0].qualifying_touch_swing_record_ids


def test_support_resistance_zone_rejects_origin_with_only_weak_reaction() -> None:
    weak_tail: _Prices = [(100.0, 101.0, 99.0, 100.0)] * 10
    candles = _build(_BASELINE + _SUPPORT_ORIGIN + weak_tail)
    origin = _swing(1, SwingType.SWING_LOW, "96", 20, candles)

    zones = detect_support_resistance_zones(candles, (origin,), _CONFIG)
    assert zones == ()


def test_support_resistance_zone_requires_opposite_swing_between_same_type_touches() -> (
    None
):
    candles, origin, _opposite, touch = _support_fixture()
    zones = detect_support_resistance_zones(candles, (origin, touch), _CONFIG)
    assert zones == ()


def test_support_resistance_zone_never_emits_draft_or_break_candidate_status() -> None:
    candles, origin, opposite, touch = _support_fixture()
    zones = detect_support_resistance_zones(candles, (origin, opposite, touch), _CONFIG)

    assert len(zones) == 1
    assert not hasattr(zones[0], "status")
    assert {member.value for member in SupportResistanceType} == {
        "SUPPORT",
        "RESISTANCE",
    }


def test_support_resistance_zone_boundaries_never_move_after_creation() -> None:
    candles, origin, opposite, touch = _support_fixture()
    zones = detect_support_resistance_zones(candles, (origin, opposite, touch), _CONFIG)
    small_final = _finalize(
        list(zones),
        DerivedOutputType.SUPPORT_RESISTANCE_ZONE,
        SupportResistanceZone,
        lambda c: (
            c.symbol.value,
            c.timeframe.value,
            c.zone_type.value,
            str(c.origin_swing_record_id),
            str(c.confirmation_candle_id),
            str(_CONFIG.rule_version),
        ),
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        _CONFIG,
        _IdentityResolver(_HashIdentityProvider()),
    )

    with pytest.raises(ValidationError):
        small_final[0].zone_top = Decimal("999")


def test_support_resistance_zone_preserves_multiple_independent_candidates() -> None:
    prices = (
        _BASELINE
        + _SUPPORT_ORIGIN
        + _SUPPORT_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _SUPPORT_TOUCH_REACTION
        + _GAP
        + [(100, 101, 96.02, 100)]
        + _SUPPORT_TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    origin = _swing(1, SwingType.SWING_LOW, "96", 20, candles)
    opposite1 = _swing(3, SwingType.SWING_HIGH, "106", 25, candles)
    touch = _swing(2, SwingType.SWING_LOW, "96.05", 36, candles)
    opposite2 = _swing(4, SwingType.SWING_HIGH, "106", 41, candles)
    touch2 = _swing(5, SwingType.SWING_LOW, "96.02", 52, candles)

    zones = detect_support_resistance_zones(
        candles, (origin, opposite1, touch, opposite2, touch2), _CONFIG
    )

    assert len(zones) == 2
    origin_ids = {zone.origin_swing_record_id for zone in zones}
    assert origin.record_id in origin_ids
    assert touch.record_id in origin_ids


def test_support_resistance_zone_touch_count_is_recoverable_from_qualifying_touch_ids() -> (
    None
):
    prices = (
        _BASELINE
        + _SUPPORT_ORIGIN
        + _SUPPORT_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _SUPPORT_TOUCH_REACTION
        + _GAP
        + [(100, 101, 96.02, 100)]
        + _SUPPORT_TOUCH_REACTION
        + _TAIL
    )
    candles = _build(prices)
    origin = _swing(1, SwingType.SWING_LOW, "96", 20, candles)
    opposite1 = _swing(3, SwingType.SWING_HIGH, "106", 25, candles)
    touch = _swing(2, SwingType.SWING_LOW, "96.05", 36, candles)
    opposite2 = _swing(4, SwingType.SWING_HIGH, "106", 41, candles)
    touch2 = _swing(5, SwingType.SWING_LOW, "96.02", 52, candles)

    zones = detect_support_resistance_zones(
        candles, (origin, opposite1, touch, opposite2, touch2), _CONFIG
    )

    origin_zone = next(z for z in zones if z.origin_swing_record_id == origin.record_id)
    assert len(origin_zone.qualifying_touch_swing_record_ids) == 2


def test_support_resistance_zone_semantic_identity_is_stable_across_growing_prefixes() -> (
    None
):
    candles_small, origin_small, opposite_small, touch_small = _support_fixture()
    zones_small = detect_support_resistance_zones(
        candles_small, (origin_small, opposite_small, touch_small), _CONFIG
    )

    prices_large = (
        _BASELINE
        + _SUPPORT_ORIGIN
        + _SUPPORT_REACTION
        + _GAP
        + _SUPPORT_TOUCH
        + _SUPPORT_TOUCH_REACTION
        + _GAP
        + [(100, 101, 96.02, 100)]
        + _SUPPORT_TOUCH_REACTION
        + _TAIL
    )
    candles_large = _build(prices_large)
    origin_large = _swing(1, SwingType.SWING_LOW, "96", 20, candles_large)
    opposite_large = _swing(3, SwingType.SWING_HIGH, "106", 25, candles_large)
    touch_large = _swing(2, SwingType.SWING_LOW, "96.05", 36, candles_large)
    opposite2_large = _swing(4, SwingType.SWING_HIGH, "106", 41, candles_large)
    touch2_large = _swing(5, SwingType.SWING_LOW, "96.02", 52, candles_large)
    zones_large = detect_support_resistance_zones(
        candles_large,
        (origin_large, opposite_large, touch_large, opposite2_large, touch2_large),
        _CONFIG,
    )

    def key_fn(c: object) -> tuple[str, ...]:
        return (
            c.symbol.value,  # type: ignore[attr-defined]
            c.timeframe.value,  # type: ignore[attr-defined]
            c.zone_type.value,  # type: ignore[attr-defined]
            str(c.origin_swing_record_id),  # type: ignore[attr-defined]
            str(c.confirmation_candle_id),  # type: ignore[attr-defined]
            str(_CONFIG.rule_version),
        )

    provider = _HashIdentityProvider()
    small_final = _finalize(
        list(zones_small),
        DerivedOutputType.SUPPORT_RESISTANCE_ZONE,
        SupportResistanceZone,
        key_fn,
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        _CONFIG,
        _IdentityResolver(provider),
    )
    large_final = _finalize(
        [z for z in zones_large if z.origin_swing_record_id == origin_large.record_id],
        DerivedOutputType.SUPPORT_RESISTANCE_ZONE,
        SupportResistanceZone,
        key_fn,
        lambda c: {"availability_time_utc": c.confirmation_time_utc},
        frozenset(),
        _CONFIG,
        _IdentityResolver(provider),
    )

    assert len(small_final) == 1
    assert len(large_final) == 1
    assert small_final[0].record_id == large_final[0].record_id
    assert small_final[0].content_fingerprint != large_final[0].content_fingerprint
