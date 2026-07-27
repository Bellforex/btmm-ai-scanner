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
from btmm_ai_scanner.domain.enums import SwingType, TrendlineOrientation
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.measurements.atr import compute_atr_series

_ZERO = Decimal("0")
_TWO = Decimal("2")


class Trendline(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    orientation: TrendlineOrientation
    anchor_1_swing_record_id: UUIDv7
    anchor_2_swing_record_id: UUIDv7
    anchor_1_price: Decimal
    anchor_2_price: Decimal
    anchor_1_bar_index: int
    anchor_2_bar_index: int
    raw_slope: Decimal
    anchor_reference_atr: Decimal
    normalized_slope: Decimal
    qualifying_touch_swing_record_ids: tuple[UUIDv7, ...]
    confirmation_candle_id: UUIDv7
    confirmation_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7


class TrendlineCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    orientation: TrendlineOrientation
    anchor_1_swing_record_id: UUID
    anchor_2_swing_record_id: UUID
    anchor_1_price: Decimal
    anchor_2_price: Decimal
    anchor_1_bar_index: int
    anchor_2_bar_index: int
    raw_slope: Decimal
    anchor_reference_atr: Decimal
    normalized_slope: Decimal
    qualifying_touch_swing_record_ids: tuple[UUID, ...]
    confirmation_candle_id: UUID
    confirmation_time_utc: datetime


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / _TWO


def detect_trendlines(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[TrendlineCandidate, ...]:
    if len(candles) == 0:
        return ()

    atr_values = compute_atr_series(candles, configuration.atr_period)
    candle_index_by_id = {
        candle.record_id: index for index, candle in enumerate(candles)
    }
    bar_index_by_swing = {
        swing.record_id: candle_index_by_id[swing.pivot_candle_record_ids[-1]]
        for swing in confirmed_swings
    }

    results: list[TrendlineCandidate] = []

    for orientation, swing_type in (
        (TrendlineOrientation.BULLISH_TRENDLINE, SwingType.SWING_LOW),
        (TrendlineOrientation.BEARISH_TRENDLINE, SwingType.SWING_HIGH),
    ):
        same_type = sorted(
            (s for s in confirmed_swings if s.swing_type == swing_type),
            key=lambda s: bar_index_by_swing[s.record_id],
        )

        for i in range(len(same_type)):
            anchor1 = same_type[i]
            anchor1_index = bar_index_by_swing[anchor1.record_id]

            for j in range(i + 1, len(same_type)):
                anchor2 = same_type[j]
                anchor2_index = bar_index_by_swing[anchor2.record_id]

                if (
                    anchor2_index - anchor1_index
                    < configuration.trendline_min_anchor_spacing_bars
                ):
                    continue

                if orientation == TrendlineOrientation.BULLISH_TRENDLINE:
                    if not (
                        anchor2.pivot_price
                        > anchor1.pivot_price + anchor1.pivot_tie_tolerance
                    ):
                        continue
                else:
                    if not (
                        anchor2.pivot_price
                        < anchor1.pivot_price - anchor1.pivot_tie_tolerance
                    ):
                        continue

                raw_slope = (anchor2.pivot_price - anchor1.pivot_price) / Decimal(
                    anchor2_index - anchor1_index
                )

                between_atrs = [
                    value
                    for value in atr_values[anchor1_index : anchor2_index + 1]
                    if value is not None
                ]
                if not between_atrs:
                    continue
                reference_atr = _median(between_atrs)
                if reference_atr == _ZERO:
                    continue
                normalized_slope = abs(raw_slope) / reference_atr

                if normalized_slope < configuration.trendline_horizontal_atr_multiplier:
                    continue
                if normalized_slope > configuration.trendline_too_steep_atr_multiplier:
                    continue

                pierce_tolerance = (
                    configuration.trendline_pierce_tolerance_atr_multiplier
                    * reference_atr
                )
                touch_tolerance = (
                    configuration.trendline_touch_tolerance_atr_multiplier
                    * reference_atr
                )

                integrity_ok = True
                for between_index in range(anchor1_index + 1, anchor2_index):
                    projected = anchor1.pivot_price + raw_slope * Decimal(
                        between_index - anchor1_index
                    )
                    candle_close = candles[between_index].close
                    if orientation == TrendlineOrientation.BULLISH_TRENDLINE:
                        if projected - candle_close > pierce_tolerance:
                            integrity_ok = False
                            break
                    else:
                        if candle_close - projected > pierce_tolerance:
                            integrity_ok = False
                            break
                if not integrity_ok:
                    continue

                confirming_touch: ConfirmedSwing | None = None
                for touch in same_type:
                    touch_index = bar_index_by_swing[touch.record_id]
                    if touch_index <= anchor2_index:
                        continue
                    projected = anchor1.pivot_price + raw_slope * Decimal(
                        touch_index - anchor1_index
                    )
                    if orientation == TrendlineOrientation.BULLISH_TRENDLINE:
                        difference = touch.pivot_price - projected
                    else:
                        difference = projected - touch.pivot_price
                    qualifies = abs(difference) <= touch_tolerance or (
                        -pierce_tolerance <= difference < -touch_tolerance
                    )
                    if qualifies:
                        confirming_touch = touch
                        break

                if confirming_touch is None:
                    continue

                results.append(
                    TrendlineCandidate(
                        symbol=anchor1.symbol,
                        timeframe=anchor1.timeframe,
                        orientation=orientation,
                        anchor_1_swing_record_id=anchor1.record_id,
                        anchor_2_swing_record_id=anchor2.record_id,
                        anchor_1_price=anchor1.pivot_price,
                        anchor_2_price=anchor2.pivot_price,
                        anchor_1_bar_index=anchor1_index,
                        anchor_2_bar_index=anchor2_index,
                        raw_slope=raw_slope,
                        anchor_reference_atr=reference_atr,
                        normalized_slope=normalized_slope,
                        qualifying_touch_swing_record_ids=(confirming_touch.record_id,),
                        confirmation_candle_id=confirming_touch.pivot_candle_record_ids[
                            -1
                        ],
                        confirmation_time_utc=confirming_touch.meaningful_confirmation_time_utc,
                    )
                )

    results.sort(
        key=lambda c: (
            c.anchor_1_bar_index,
            c.anchor_2_bar_index,
            str(c.anchor_1_swing_record_id),
        )
    )
    return tuple(results)
