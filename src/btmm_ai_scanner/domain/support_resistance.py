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
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SupportResistanceType, SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.measurements.legs import measure_leg

_ZERO = Decimal("0")


class SupportResistanceZone(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    zone_type: SupportResistanceType
    origin_swing_record_id: UUIDv7
    creator_reference_atr: Decimal
    zone_depth: Decimal
    zone_top: Decimal
    zone_bottom: Decimal
    qualifying_touch_swing_record_ids: tuple[UUIDv7, ...]
    confirmation_candle_id: UUIDv7
    confirmation_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7


class SupportResistanceZoneCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    zone_type: SupportResistanceType
    origin_swing_record_id: UUID
    creator_reference_atr: Decimal
    zone_depth: Decimal
    zone_top: Decimal
    zone_bottom: Decimal
    qualifying_touch_swing_record_ids: tuple[UUID, ...]
    confirmation_candle_id: UUID
    confirmation_time_utc: datetime


class _ReactionResult(NamedTuple):
    confirming_candle: NormalizedCandle


def _evaluate_reaction(
    candles: Sequence[NormalizedCandle],
    atr_values: Sequence[Decimal | None],
    search_start_index: int,
    zone_top: Decimal,
    zone_bottom: Decimal,
    is_support: bool,
    configuration: MarketMeasurementConfiguration,
) -> _ReactionResult | None:
    n = len(candles)
    zone_height = zone_top - zone_bottom
    if zone_height <= _ZERO or search_start_index >= n:
        return None

    reaction_start_index: int | None = None
    for index in range(search_start_index, n):
        candle = candles[index]
        if is_support and candle.close > zone_top:
            reaction_start_index = index
            break
        if not is_support and candle.close < zone_bottom:
            reaction_start_index = index
            break
    if reaction_start_index is None:
        return None

    if is_support:
        anchor = min(
            c.low for c in candles[search_start_index : reaction_start_index + 1]
        )
    else:
        anchor = max(
            c.high for c in candles[search_start_index : reaction_start_index + 1]
        )

    window_end = min(reaction_start_index + configuration.reaction_window_bars, n)
    window_candles = candles[reaction_start_index:window_end]
    if len(window_candles) == 0:
        return None

    if is_support:
        highest_high = max(c.high for c in window_candles)
        mfe = highest_high - anchor
        zone_clearance = max(_ZERO, highest_high - zone_top)
        mfe_index = max(
            range(reaction_start_index, window_end), key=lambda i: candles[i].high
        )
    else:
        lowest_low = min(c.low for c in window_candles)
        mfe = anchor - lowest_low
        zone_clearance = max(_ZERO, zone_bottom - lowest_low)
        mfe_index = min(
            range(reaction_start_index, window_end), key=lambda i: candles[i].low
        )

    reference_atr = atr_values[reaction_start_index]
    if reference_atr is None or reference_atr == _ZERO:
        return None

    atr_reaction_ratio = mfe / reference_atr
    zone_clearance_ratio = zone_clearance / zone_height

    leg_candles = candles[reaction_start_index : mfe_index + 1]
    leg_atrs = atr_values[reaction_start_index : mfe_index + 1]
    leg = measure_leg(
        leg_candles,
        leg_atrs,
        is_bullish_direction=is_support,
        fast_normalized_speed_per_bar=configuration.leg_fast_normalized_speed_per_bar,
        fast_directional_efficiency=configuration.leg_fast_directional_efficiency,
        fast_directional_candle_share=configuration.leg_fast_directional_candle_share,
        strong_fast_normalized_speed_per_bar=(
            configuration.leg_strong_fast_normalized_speed_per_bar
        ),
        strong_fast_directional_efficiency=(
            configuration.leg_strong_fast_directional_efficiency
        ),
        strong_fast_directional_candle_share=(
            configuration.leg_strong_fast_directional_candle_share
        ),
    )

    meets_standard = (
        atr_reaction_ratio >= configuration.reaction_standard_atr_ratio
        and zone_clearance_ratio >= configuration.reaction_standard_zone_clearance_ratio
        and leg.directional_efficiency
        >= configuration.reaction_standard_directional_efficiency
        and leg.directional_candle_share
        >= configuration.reaction_standard_directional_candle_share
    )
    if not meets_standard:
        return None

    return _ReactionResult(confirming_candle=candles[mfe_index])


def detect_support_resistance_zones(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[SupportResistanceZoneCandidate, ...]:
    if len(candles) == 0:
        return ()

    atr_values = compute_atr_series(candles, configuration.atr_period)
    candle_index_by_id = {
        candle.record_id: index for index, candle in enumerate(candles)
    }

    results: list[SupportResistanceZoneCandidate] = []

    for zone_type, origin_swing_type in (
        (SupportResistanceType.SUPPORT, SwingType.SWING_LOW),
        (SupportResistanceType.RESISTANCE, SwingType.SWING_HIGH),
    ):
        opposite_swing_type = (
            SwingType.SWING_HIGH
            if origin_swing_type == SwingType.SWING_LOW
            else SwingType.SWING_LOW
        )
        origins = sorted(
            (s for s in confirmed_swings if s.swing_type == origin_swing_type),
            key=lambda s: s.meaningful_confirmation_time_utc,
        )
        same_type_swings = sorted(
            (s for s in confirmed_swings if s.swing_type == origin_swing_type),
            key=lambda s: s.meaningful_confirmation_time_utc,
        )

        for origin in origins:
            origin_last_candle_id = origin.pivot_candle_record_ids[-1]
            origin_index = candle_index_by_id[origin_last_candle_id]

            zone_depth = (
                configuration.support_resistance_zone_depth_atr_multiplier
                * origin.pivot_reference_atr
            )
            if zone_type == SupportResistanceType.SUPPORT:
                zone_bottom = origin.pivot_price
                zone_top = zone_bottom + zone_depth
            else:
                zone_top = origin.pivot_price
                zone_bottom = zone_top - zone_depth

            origin_reaction = _evaluate_reaction(
                candles,
                atr_values,
                origin_index + 1,
                zone_top,
                zone_bottom,
                zone_type == SupportResistanceType.SUPPORT,
                configuration,
            )
            if origin_reaction is None:
                continue

            touch_tolerance = (
                configuration.support_resistance_touch_tolerance_atr_multiplier
                * origin.pivot_reference_atr
            )
            pierce_tolerance = (
                configuration.support_resistance_pierce_tolerance_atr_multiplier
                * origin.pivot_reference_atr
            )

            qualifying_touches: list[ConfirmedSwing] = []
            first_confirming_candle: NormalizedCandle | None = None
            last_touch_time = origin.meaningful_confirmation_time_utc

            for touch in same_type_swings:
                if touch.record_id == origin.record_id:
                    continue
                if touch.meaningful_confirmation_time_utc <= last_touch_time:
                    continue

                if zone_type == SupportResistanceType.SUPPORT:
                    geometric_ok = (
                        touch.pivot_price <= zone_top + touch_tolerance
                        and touch.pivot_price >= zone_bottom - pierce_tolerance
                    )
                else:
                    geometric_ok = (
                        touch.pivot_price >= zone_bottom - touch_tolerance
                        and touch.pivot_price <= zone_top + pierce_tolerance
                    )
                if not geometric_ok:
                    continue

                has_opposite_between = any(
                    s.swing_type == opposite_swing_type
                    and last_touch_time
                    < s.meaningful_confirmation_time_utc
                    < touch.meaningful_confirmation_time_utc
                    for s in confirmed_swings
                )
                if not has_opposite_between:
                    continue

                touch_last_candle_id = touch.pivot_candle_record_ids[-1]
                touch_index = candle_index_by_id[touch_last_candle_id]
                touch_reaction = _evaluate_reaction(
                    candles,
                    atr_values,
                    touch_index + 1,
                    zone_top,
                    zone_bottom,
                    zone_type == SupportResistanceType.SUPPORT,
                    configuration,
                )
                if touch_reaction is None:
                    continue

                qualifying_touches.append(touch)
                if first_confirming_candle is None:
                    first_confirming_candle = touch_reaction.confirming_candle
                last_touch_time = touch.meaningful_confirmation_time_utc

            if first_confirming_candle is None:
                continue

            results.append(
                SupportResistanceZoneCandidate(
                    symbol=origin.symbol,
                    timeframe=origin.timeframe,
                    zone_type=zone_type,
                    origin_swing_record_id=origin.record_id,
                    creator_reference_atr=origin.pivot_reference_atr,
                    zone_depth=zone_depth,
                    zone_top=zone_top,
                    zone_bottom=zone_bottom,
                    qualifying_touch_swing_record_ids=tuple(
                        touch.record_id for touch in qualifying_touches
                    ),
                    confirmation_candle_id=first_confirming_candle.record_id,
                    confirmation_time_utc=first_confirming_candle.availability_time_utc,
                )
            )

    results.sort(key=lambda candidate: candidate.confirmation_time_utc)
    return tuple(results)
