from datetime import UTC

from pydantic import ValidationError

from btmm_ai_scanner.contracts.raw_candle import RawCandle
from btmm_ai_scanner.market_data.results import IngestionOutcome, IngestionResult
from btmm_ai_scanner.market_data.source_input import SourceCandleInput


def build_historical_raw_candle(source_input: SourceCandleInput) -> IngestionResult:
    return _build_raw_candle_from_source_input(source_input)


def build_live_raw_candle(source_input: SourceCandleInput) -> IngestionResult:
    return _build_raw_candle_from_source_input(source_input)


def _build_raw_candle_from_source_input(
    source_input: SourceCandleInput,
) -> IngestionResult:
    availability = source_input.availability_time_utc
    original_availability = source_input.original_availability_time

    if availability is None and original_availability is None:
        return IngestionResult(
            outcome=IngestionOutcome.INDETERMINATE,
            reason_codes=("AVAILABILITY_TIME_UNAVAILABLE",),
            candidate_raw_candle=None,
            candidate_normalized_candle=None,
            existing_record_id=None,
        )

    if (availability is None) != (original_availability is None):
        return IngestionResult(
            outcome=IngestionOutcome.REJECTED,
            reason_codes=("AVAILABILITY_TIME_PAIR_INCONSISTENT",),
            candidate_raw_candle=None,
            candidate_normalized_candle=None,
            existing_record_id=None,
        )

    assert availability is not None
    assert original_availability is not None

    if original_availability.astimezone(UTC) != availability:
        return IngestionResult(
            outcome=IngestionOutcome.REJECTED,
            reason_codes=("AVAILABILITY_TIME_INVALID",),
            candidate_raw_candle=None,
            candidate_normalized_candle=None,
            existing_record_id=None,
        )

    try:
        raw_candle = RawCandle(
            record_id=source_input.record_id,
            content_fingerprint=source_input.content_fingerprint,
            provider=source_input.provider,
            source_reference=source_input.source_reference,
            source_symbol=source_input.source_symbol,
            source_timeframe=source_input.source_timeframe,
            event_time_utc=source_input.event_time_utc,
            availability_time_utc=availability,
            processing_time_utc=source_input.processing_time_utc,
            original_event_time=source_input.original_event_time,
            original_availability_time=original_availability,
            original_timezone=source_input.original_timezone,
            open=source_input.open,
            high=source_input.high,
            low=source_input.low,
            close=source_input.close,
            volume=source_input.volume,
            volume_kind=source_input.volume_kind,
            completeness=source_input.completeness,
            rule_version=source_input.rule_version,
            contract_version=source_input.contract_version,
            schema_version=source_input.schema_version,
            provenance_id=source_input.provenance_id,
        )
    except ValidationError:
        return IngestionResult(
            outcome=IngestionOutcome.REJECTED,
            reason_codes=("RAW_CANDLE_VALIDATION_FAILED",),
            candidate_raw_candle=None,
            candidate_normalized_candle=None,
            existing_record_id=None,
        )

    return IngestionResult(
        outcome=IngestionOutcome.ACCEPTED,
        reason_codes=(),
        candidate_raw_candle=raw_candle,
        candidate_normalized_candle=None,
        existing_record_id=None,
    )
