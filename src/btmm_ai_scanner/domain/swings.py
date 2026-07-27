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
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.measurements.atr import compute_atr_series

_WINDOW_RADIUS = 2


class ConfirmedSwing(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    swing_type: SwingType
    pivot_price: Decimal
    pivot_bar_index: int
    pivot_candle_record_ids: tuple[UUIDv7, ...]
    pivot_start_time_utc: datetime
    pivot_end_time_utc: datetime
    local_confirmation_time_utc: datetime
    meaningful_confirmation_time_utc: datetime
    confirmation_candle_id: UUIDv7
    pivot_reference_atr: Decimal
    pivot_tie_tolerance: Decimal
    reversal_threshold: Decimal
    reversal_excursion: Decimal
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7


class ConfirmedSwingCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    swing_type: SwingType
    pivot_price: Decimal
    pivot_bar_index: int
    pivot_candle_record_ids: tuple[UUID, ...]
    pivot_start_time_utc: datetime
    pivot_end_time_utc: datetime
    local_confirmation_time_utc: datetime
    meaningful_confirmation_time_utc: datetime
    confirmation_candle_id: UUID
    pivot_reference_atr: Decimal
    pivot_tie_tolerance: Decimal
    reversal_threshold: Decimal
    reversal_excursion: Decimal


class _Pivot(NamedTuple):
    start_index: int
    end_index: int
    swing_type: SwingType
    price: Decimal
    reference_atr: Decimal
    tie_tolerance: Decimal


def _median(values: Sequence[Decimal]) -> Decimal:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)


def _find_single_candle_pivots(
    candles: Sequence[NormalizedCandle],
    atr_values: Sequence[Decimal | None],
    configuration: MarketMeasurementConfiguration,
) -> list[_Pivot]:
    pivots: list[_Pivot] = []
    n = len(candles)
    for index in range(_WINDOW_RADIUS, n - _WINDOW_RADIUS):
        atr = atr_values[index]
        if atr is None:
            continue
        tie_tolerance = configuration.pivot_tie_tolerance_atr_multiplier * atr
        window_indices = [
            j
            for j in range(index - _WINDOW_RADIUS, index + _WINDOW_RADIUS + 1)
            if j != index
        ]

        candidate_high = candles[index].high
        qualifies_as_high = all(
            candles[j].high <= candidate_high + tie_tolerance for j in window_indices
        )

        candidate_low = candles[index].low
        qualifies_as_low = all(
            candles[j].low >= candidate_low - tie_tolerance for j in window_indices
        )

        # A single candle qualifying simultaneously as both a swing high and a
        # swing low is ambiguous for the mandatory alternating sequence; per
        # register §33I, neither direction is emitted for that candle.
        if qualifies_as_high and qualifies_as_low:
            continue

        if qualifies_as_high:
            pivots.append(
                _Pivot(
                    index,
                    index,
                    SwingType.SWING_HIGH,
                    candidate_high,
                    atr,
                    tie_tolerance,
                )
            )
        elif qualifies_as_low:
            pivots.append(
                _Pivot(
                    index, index, SwingType.SWING_LOW, candidate_low, atr, tie_tolerance
                )
            )

    return pivots


def _merge_adjacent_plateaus(pivots: list[_Pivot]) -> list[_Pivot]:
    by_type: dict[SwingType, list[_Pivot]] = {
        SwingType.SWING_HIGH: [],
        SwingType.SWING_LOW: [],
    }
    for pivot in pivots:
        by_type[pivot.swing_type].append(pivot)

    merged: list[_Pivot] = []
    for swing_type, group in by_type.items():
        group.sort(key=lambda p: p.start_index)
        index = 0
        while index < len(group):
            current = group[index]
            if (
                index + 1 < len(group)
                and group[index + 1].start_index == current.end_index + 1
                and abs(group[index + 1].price - current.price) <= current.tie_tolerance
            ):
                other = group[index + 1]
                if swing_type == SwingType.SWING_HIGH:
                    price = max(current.price, other.price)
                else:
                    price = min(current.price, other.price)
                reference_atr = _median([current.reference_atr, other.reference_atr])
                merged.append(
                    _Pivot(
                        current.start_index,
                        other.end_index,
                        swing_type,
                        price,
                        reference_atr,
                        other.tie_tolerance,
                    )
                )
                index += 2
            else:
                merged.append(current)
                index += 1

    merged.sort(key=lambda p: p.start_index)
    return merged


def _supersede_same_direction_runs(pivots: list[_Pivot]) -> list[_Pivot]:
    """Within a run of same-type pivots uninterrupted by the opposite type,
    only the most extreme candidate survives — earlier ones in the run are
    superseded before ever being offered for confirmation."""
    collapsed: list[_Pivot] = []
    run: list[_Pivot] = []

    def flush() -> None:
        if not run:
            return
        if run[0].swing_type == SwingType.SWING_HIGH:
            collapsed.append(max(run, key=lambda p: p.price))
        else:
            collapsed.append(min(run, key=lambda p: p.price))

    for pivot in pivots:
        if run and run[-1].swing_type != pivot.swing_type:
            flush()
            run = []
        run.append(pivot)
    flush()

    return collapsed


def detect_confirmed_swings(
    candles: tuple[NormalizedCandle, ...],
    configuration: MarketMeasurementConfiguration,
) -> tuple[ConfirmedSwingCandidate, ...]:
    if len(candles) < 2 * _WINDOW_RADIUS + 1:
        return ()

    atr_values = compute_atr_series(candles, configuration.atr_period)
    raw_pivots = _find_single_candle_pivots(candles, atr_values, configuration)
    pivots = _supersede_same_direction_runs(_merge_adjacent_plateaus(raw_pivots))

    n = len(candles)
    results: list[ConfirmedSwingCandidate] = []
    last_confirmed_type: SwingType | None = None

    for pivot in pivots:
        local_confirmation_index = pivot.end_index + _WINDOW_RADIUS
        if local_confirmation_index >= n:
            continue

        if pivot.swing_type == last_confirmed_type:
            continue

        threshold = (
            configuration.meaningful_reversal_atr_multiplier * pivot.reference_atr
        )

        confirmation_index: int | None = None
        excursion = Decimal(0)
        search_start = local_confirmation_index + 1
        if pivot.swing_type == SwingType.SWING_HIGH:
            lowest_low = candles[local_confirmation_index].low
            for j in range(search_start, n):
                lowest_low = min(lowest_low, candles[j].low)
                current_excursion = pivot.price - lowest_low
                if current_excursion >= threshold:
                    confirmation_index = j
                    excursion = current_excursion
                    break
        else:
            highest_high = candles[local_confirmation_index].high
            for j in range(search_start, n):
                highest_high = max(highest_high, candles[j].high)
                current_excursion = highest_high - pivot.price
                if current_excursion >= threshold:
                    confirmation_index = j
                    excursion = current_excursion
                    break

        if confirmation_index is None:
            continue

        pivot_candle_ids = tuple(
            candles[i].record_id for i in range(pivot.start_index, pivot.end_index + 1)
        )
        local_confirmation_candle = candles[local_confirmation_index]
        confirmation_candle = candles[confirmation_index]

        results.append(
            ConfirmedSwingCandidate(
                symbol=candles[pivot.start_index].symbol,
                timeframe=candles[pivot.start_index].timeframe,
                swing_type=pivot.swing_type,
                pivot_price=pivot.price,
                pivot_bar_index=pivot.start_index,
                pivot_candle_record_ids=pivot_candle_ids,
                pivot_start_time_utc=candles[pivot.start_index].event_time_utc,
                pivot_end_time_utc=candles[pivot.end_index].event_time_utc,
                local_confirmation_time_utc=local_confirmation_candle.availability_time_utc,
                meaningful_confirmation_time_utc=confirmation_candle.availability_time_utc,
                confirmation_candle_id=confirmation_candle.record_id,
                pivot_reference_atr=pivot.reference_atr,
                pivot_tie_tolerance=pivot.tie_tolerance,
                reversal_threshold=threshold,
                reversal_excursion=excursion,
            )
        )
        last_confirmed_type = pivot.swing_type

    return tuple(results)
