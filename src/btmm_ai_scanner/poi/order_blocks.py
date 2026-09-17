from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.measurements.candle_metrics import total_range
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType


class OrderBlockCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    poi_type: PoiType
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    strength_tier: PoiStrengthTier
    source_candle_record_ids: tuple[UUID, ...]
    candidate_event_time_utc: datetime
    confirmation_time_utc: datetime
    availability_time_utc: datetime


def detect_order_blocks(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[OrderBlockCandidate, ...]:
    if len(candles) < 2:
        return ()

    results: list[OrderBlockCandidate] = []
    for index in range(len(candles) - 1):
        origin = candles[index]
        displacement = candles[index + 1]

        origin_range = total_range(origin)
        if origin_range == 0:
            continue
        ratio = total_range(displacement) / origin_range
        if ratio < configuration.order_block_size_ratio_standard:
            continue

        origin_bearish = origin.close < origin.open
        origin_bullish = origin.close > origin.open
        displacement_bullish = displacement.close > displacement.open
        displacement_bearish = displacement.close < displacement.open

        if origin_bearish and displacement_bullish and displacement.close > origin.high:
            poi_type = PoiType.BUY_ORDER_BLOCK
            direction = PoiDirection.BULLISH
        elif (
            origin_bullish and displacement_bearish and displacement.close < origin.low
        ):
            poi_type = PoiType.SELL_ORDER_BLOCK
            direction = PoiDirection.BEARISH
        else:
            continue

        strength_tier = (
            PoiStrengthTier.STRONG
            if ratio >= configuration.order_block_size_ratio_strong
            else PoiStrengthTier.STANDARD
        )

        results.append(
            OrderBlockCandidate(
                symbol=origin.symbol,
                timeframe=origin.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=origin.high,
                zone_bottom=origin.low,
                strength_tier=strength_tier,
                source_candle_record_ids=(origin.record_id, displacement.record_id),
                candidate_event_time_utc=origin.event_time_utc,
                confirmation_time_utc=displacement.availability_time_utc,
                availability_time_utc=displacement.availability_time_utc,
            )
        )

    return tuple(results)


def apply_movement_origin_gate(
    formations: Iterable[OrderBlockCandidate],
    confirmed_swings: Iterable[ConfirmedSwing],
) -> tuple[OrderBlockCandidate, ...]:
    """RC3 ORDER BLOCK = MOVEMENT ORIGIN (author semantic revision, 2026-09-17).

    `formations` are the frozen two-candle order-block formations from
    `detect_order_blocks` (2.0 size rule, colours, close beyond the origin
    extreme -- unchanged). A formation is an ORDER BLOCK only when it is the
    origin of a new directional leg, decided with the frozen swing primitive
    (`domain/swings.py`), never a second structure model:

    * BUY: a meaningfully confirmed SWING_LOW whose pivot candles include the
      origin or the displacement candle.
    * SELL: a meaningfully confirmed SWING_HIGH likewise.

    Swing alternation already encodes "the previous leg was opposite": a low
    that follows an already-confirmed low with no confirmed high between is
    never a confirmed swing, so a same-direction formation inside a leg that
    has already started fails the gate and remains an ENGULFING only.

    Timing: source (candidate event time, zone, source candles) stays the
    origin formation. Availability = confirmation = the swing's meaningful
    confirmation time (never earlier than the displacement close). A swing is
    only present once confirmed, so nothing is known before it happened.
    """
    earliest: dict[tuple[SwingType, object], ConfirmedSwing] = {}
    for swing in confirmed_swings:
        for candle_id in swing.pivot_candle_record_ids:
            key = (swing.swing_type, candle_id)
            held = earliest.get(key)
            if held is None or (
                swing.meaningful_confirmation_time_utc,
                str(swing.record_id),
            ) < (held.meaningful_confirmation_time_utc, str(held.record_id)):
                earliest[key] = swing

    gated: list[OrderBlockCandidate] = []
    for formation in formations:
        want = (
            SwingType.SWING_LOW
            if formation.direction == PoiDirection.BULLISH
            else SwingType.SWING_HIGH
        )
        matches = [
            earliest[(want, candle_id)]
            for candle_id in formation.source_candle_record_ids
            if (want, candle_id) in earliest
        ]
        if not matches:
            continue
        anchor = min(
            matches,
            key=lambda s: (s.meaningful_confirmation_time_utc, str(s.record_id)),
        )
        available = max(
            formation.availability_time_utc, anchor.meaningful_confirmation_time_utc
        )
        gated.append(
            formation._replace(
                confirmation_time_utc=available, availability_time_utc=available
            )
        )
    return tuple(gated)
