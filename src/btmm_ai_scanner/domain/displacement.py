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
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
)
from btmm_ai_scanner.measurements.candle_metrics import range_speed_ratio, total_range

_ZERO = Decimal("0")


class DisplacementObservation(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    candle_record_id: UUIDv7
    event_time_utc: datetime
    availability_time_utc: datetime
    total_range: Decimal
    range_speed_ratio: Decimal
    direction: DisplacementDirection
    classification: DisplacementClassification
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7


class DisplacementObservationCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    candle_record_id: UUID
    event_time_utc: datetime
    availability_time_utc: datetime
    total_range: Decimal
    range_speed_ratio: Decimal
    direction: DisplacementDirection
    classification: DisplacementClassification


def _classify(
    ratio: Decimal, configuration: MarketMeasurementConfiguration
) -> DisplacementClassification:
    if ratio >= configuration.displacement_very_fast_ratio:
        return DisplacementClassification.VERY_FAST
    if ratio >= configuration.displacement_fast_ratio:
        return DisplacementClassification.FAST
    return DisplacementClassification.NORMAL


def detect_displacement_observations(
    candles: tuple[NormalizedCandle, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[DisplacementObservationCandidate, ...]:
    window = configuration.range_context_window
    results: list[DisplacementObservationCandidate] = []

    for index in range(window, len(candles)):
        candle = candles[index]
        preceding = candles[index - window : index]

        range_value = total_range(candle)
        if range_value == _ZERO:
            ratio = _ZERO
            classification = DisplacementClassification.NORMAL
        else:
            ratio = range_speed_ratio(candle, preceding)
            classification = _classify(ratio, configuration)

        direction = (
            DisplacementDirection.BULLISH
            if candle.close >= candle.open
            else DisplacementDirection.BEARISH
        )

        results.append(
            DisplacementObservationCandidate(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                candle_record_id=candle.record_id,
                event_time_utc=candle.event_time_utc,
                availability_time_utc=candle.availability_time_utc,
                total_range=range_value,
                range_speed_ratio=ratio,
                direction=direction,
                classification=classification,
            )
        )

    return tuple(results)
