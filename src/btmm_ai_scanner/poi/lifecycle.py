from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.measurements.legs import LegSpeedClassification, measure_leg
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiLifecycleTransitionType,
    PoiTapClassification,
)

_TWO = Decimal("2")


class PoiLifecycleTransition(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    poi_record_id: UUIDv7
    transition_type: PoiLifecycleTransitionType
    triggering_candle_record_id: UUIDv7
    event_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7


class TransitionCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    poi_record_id: UUID
    transition_type: PoiLifecycleTransitionType
    triggering_candle_record_id: UUID
    event_time_utc: datetime
    availability_time_utc: datetime


class LifecycleWalkResult(NamedTuple):
    transitions: tuple[TransitionCandidate, ...]
    final_status: PoiLifecycleStatus
    freshness_status: PoiFreshnessStatus
    tap_count: int
    tap_classification: PoiTapClassification | None
    age_in_confirmed_bars: int
    last_seen_candle: NormalizedCandle | None


def _zone_reference_atr(
    atr_values: Sequence[Decimal | None], index: int, fallback: Decimal
) -> Decimal:
    value = atr_values[index] if 0 <= index < len(atr_values) else None
    if value is not None and value > 0:
        return value
    return fallback


def _is_breach(
    candle: NormalizedCandle,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    overshoot_tolerance: Decimal,
) -> bool:
    if direction == PoiDirection.BULLISH:
        return (zone_bottom - candle.close) > overshoot_tolerance
    return (candle.close - zone_top) > overshoot_tolerance


def _is_reclaim(
    candle: NormalizedCandle,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    contact_tolerance: Decimal,
) -> bool:
    if direction == PoiDirection.BULLISH:
        return candle.close >= zone_bottom + contact_tolerance
    return candle.close <= zone_top - contact_tolerance


def _is_displacement(
    candle: NormalizedCandle,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    contact_tolerance: Decimal,
) -> bool:
    if direction == PoiDirection.BULLISH:
        return candle.close >= zone_top + contact_tolerance
    return candle.close <= zone_bottom - contact_tolerance


def _touches_zone(
    candle: NormalizedCandle, zone_top: Decimal, zone_bottom: Decimal
) -> bool:
    return candle.low <= zone_top and candle.high >= zone_bottom


def _classify_tap_count(tap_count: int) -> PoiTapClassification | None:
    if tap_count <= 0:
        return None
    if tap_count == 1:
        return PoiTapClassification.INITIAL_TAP
    if tap_count == 2:
        return PoiTapClassification.REPEATED_TAP
    return PoiTapClassification.MULTIPLE_REPEATED_TAPS


def _compute_freshness_and_taps(
    candles: Sequence[NormalizedCandle],
    start_index: int,
    zone_top: Decimal,
    zone_bottom: Decimal,
) -> tuple[PoiFreshnessStatus, int, PoiTapClassification | None]:
    tap_count = 0
    in_tap = False
    for candle in candles[start_index:]:
        touching = _touches_zone(candle, zone_top, zone_bottom)
        if touching and not in_tap:
            tap_count += 1
            in_tap = True
        elif not touching:
            in_tap = False

    freshness = (
        PoiFreshnessStatus.INTERACTED if tap_count > 0 else PoiFreshnessStatus.FRESH
    )
    return freshness, tap_count, _classify_tap_count(tap_count)


def run_poi_lifecycle(
    candles: Sequence[NormalizedCandle],
    atr_values: Sequence[Decimal | None],
    symbol: InternalSymbol,
    timeframe: Timeframe,
    poi_record_id: UUID,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    availability_time_utc: datetime,
    configuration: PoiConfiguration,
) -> LifecycleWalkResult:
    zone_height = zone_top - zone_bottom
    min_tick = configuration.minimum_price_tick

    start_index = 0
    for index, candle in enumerate(candles):
        if candle.availability_time_utc > availability_time_utc:
            start_index = index
            break
    else:
        start_index = len(candles)

    freshness_status, tap_count, tap_classification = _compute_freshness_and_taps(
        candles, start_index, zone_top, zone_bottom
    )

    transitions: list[TransitionCandidate] = []
    status = PoiLifecycleStatus.NO_BREACH

    def tolerance(
        index: int, atr_multiplier: Decimal, height_multiplier: Decimal
    ) -> Decimal:
        fallback = candles[index].high - candles[index].low
        reference_atr = _zone_reference_atr(atr_values, index, fallback)
        bound_a = atr_multiplier * reference_atr
        bound_b = height_multiplier * zone_height if zone_height > 0 else bound_a
        return max(_TWO * min_tick, min(bound_a, bound_b))

    i = start_index
    n = len(candles)
    last_seen_candle: NormalizedCandle | None = None
    terminal = False

    while i < n and not terminal:
        candle = candles[i]
        last_seen_candle = candle
        overshoot = tolerance(
            i,
            configuration.zone_overshoot_tolerance_atr_multiplier,
            configuration.zone_overshoot_tolerance_zone_height_multiplier,
        )
        if _is_breach(candle, direction, zone_top, zone_bottom, overshoot):
            status = PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE
            transitions.append(
                TransitionCandidate(
                    symbol,
                    timeframe,
                    poi_record_id,
                    PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE,
                    candle.record_id,
                    candle.event_time_utc,
                    candle.availability_time_utc,
                )
            )

            reclaim_index: int | None = None
            window_end = min(i + 1 + configuration.reclaim_window_bars, n)
            for j in range(i + 1, window_end):
                contact = tolerance(
                    j,
                    configuration.zone_contact_tolerance_atr_multiplier,
                    configuration.zone_contact_tolerance_zone_height_multiplier,
                )
                if _is_reclaim(candles[j], direction, zone_top, zone_bottom, contact):
                    reclaim_index = j
                    break

            if reclaim_index is not None:
                reclaim_candle = candles[reclaim_index]
                status = PoiLifecycleStatus.RECLAIM_CONFIRMED
                transitions.append(
                    TransitionCandidate(
                        symbol,
                        timeframe,
                        poi_record_id,
                        PoiLifecycleTransitionType.RECLAIM_CONFIRMED,
                        reclaim_candle.record_id,
                        reclaim_candle.event_time_utc,
                        reclaim_candle.availability_time_utc,
                    )
                )

                displacement_index: int | None = None
                displacement_end = min(
                    reclaim_index + 1 + configuration.displacement_window_bars, n
                )
                for k in range(reclaim_index + 1, displacement_end):
                    contact_k = tolerance(
                        k,
                        configuration.zone_contact_tolerance_atr_multiplier,
                        configuration.zone_contact_tolerance_zone_height_multiplier,
                    )
                    if not _is_displacement(
                        candles[k], direction, zone_top, zone_bottom, contact_k
                    ):
                        continue
                    leg_candles = candles[reclaim_index + 1 : k + 1]
                    leg_atrs = atr_values[reclaim_index + 1 : k + 1]
                    leg = measure_leg(
                        leg_candles,
                        leg_atrs,
                        is_bullish_direction=(direction == PoiDirection.BULLISH),
                        fast_normalized_speed_per_bar=Decimal("0.50"),
                        fast_directional_efficiency=Decimal("0.60"),
                        fast_directional_candle_share=Decimal("0.67"),
                        strong_fast_normalized_speed_per_bar=Decimal("0.75"),
                        strong_fast_directional_efficiency=Decimal("0.75"),
                        strong_fast_directional_candle_share=Decimal("0.80"),
                    )
                    if leg.classification in (
                        LegSpeedClassification.FAST,
                        LegSpeedClassification.STRONG_FAST,
                    ):
                        displacement_index = k
                        break

                if displacement_index is not None:
                    displacement_candle = candles[displacement_index]
                    status = PoiLifecycleStatus.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED
                    transitions.append(
                        TransitionCandidate(
                            symbol,
                            timeframe,
                            poi_record_id,
                            PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED,
                            displacement_candle.record_id,
                            displacement_candle.event_time_utc,
                            displacement_candle.availability_time_utc,
                        )
                    )
                    status = PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED
                    transitions.append(
                        TransitionCandidate(
                            symbol,
                            timeframe,
                            poi_record_id,
                            PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED,
                            displacement_candle.record_id,
                            displacement_candle.event_time_utc,
                            displacement_candle.availability_time_utc,
                        )
                    )
                else:
                    status = PoiLifecycleStatus.RECLAIM_WITHOUT_DISPLACEMENT
                    transitions.append(
                        TransitionCandidate(
                            symbol,
                            timeframe,
                            poi_record_id,
                            PoiLifecycleTransitionType.RECLAIM_WITHOUT_DISPLACEMENT,
                            reclaim_candle.record_id,
                            reclaim_candle.event_time_utc,
                            reclaim_candle.availability_time_utc,
                        )
                    )

                i = reclaim_index + 1
                continue

            window_candles = candles[i + 1 : window_end]
            qualifying_closes = sum(
                1
                for c_idx, c in zip(
                    range(i + 1, window_end), window_candles, strict=True
                )
                if _is_breach(
                    c,
                    direction,
                    zone_top,
                    zone_bottom,
                    tolerance(
                        c_idx,
                        configuration.zone_overshoot_tolerance_atr_multiplier,
                        configuration.zone_overshoot_tolerance_zone_height_multiplier,
                    ),
                )
            )
            bar3_qualifies = (
                len(window_candles) == configuration.reclaim_window_bars
                and qualifying_closes >= 2
                and _is_breach(
                    window_candles[-1],
                    direction,
                    zone_top,
                    zone_bottom,
                    tolerance(
                        window_end - 1,
                        configuration.zone_overshoot_tolerance_atr_multiplier,
                        configuration.zone_overshoot_tolerance_zone_height_multiplier,
                    ),
                )
            )
            if bar3_qualifies:
                final_candle = window_candles[-1]
                status = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
                transitions.append(
                    TransitionCandidate(
                        symbol,
                        timeframe,
                        poi_record_id,
                        PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
                        final_candle.record_id,
                        final_candle.event_time_utc,
                        final_candle.availability_time_utc,
                    )
                )
                terminal = True
                i = window_end
                continue

            if len(window_candles) > 0:
                final_candle = window_candles[-1]
                status = PoiLifecycleStatus.RECLAIM_FAILED
                transitions.append(
                    TransitionCandidate(
                        symbol,
                        timeframe,
                        poi_record_id,
                        PoiLifecycleTransitionType.RECLAIM_FAILED,
                        final_candle.record_id,
                        final_candle.event_time_utc,
                        final_candle.availability_time_utc,
                    )
                )
            i = window_end
            continue

        i += 1

    age_in_confirmed_bars = max(0, n - start_index)

    return LifecycleWalkResult(
        transitions=tuple(transitions),
        final_status=status,
        freshness_status=freshness_status,
        tap_count=tap_count,
        tap_classification=tap_classification,
        age_in_confirmed_bars=age_in_confirmed_bars,
        last_seen_candle=last_seen_candle,
    )
