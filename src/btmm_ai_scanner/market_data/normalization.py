from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import RawCandle
from btmm_ai_scanner.contracts.types import SemVer, SHA256Fingerprint, UUIDv7
from btmm_ai_scanner.market_data.results import IngestionOutcome, IngestionResult
from btmm_ai_scanner.market_data.source_mapping import (
    UnsupportedProviderError,
    UnsupportedProviderSymbolError,
    UnsupportedProviderTimeframeError,
    resolve_internal_symbol,
    resolve_timeframe,
)


def normalize_raw_candle(
    raw_candle: RawCandle,
    *,
    normalized_record_id: UUIDv7,
    normalized_content_fingerprint: SHA256Fingerprint,
    normalized_rule_version: SemVer,
    normalized_contract_version: SemVer,
    normalized_schema_version: SemVer,
    normalized_provenance_id: UUIDv7,
) -> IngestionResult:
    try:
        symbol = resolve_internal_symbol(raw_candle.provider, raw_candle.source_symbol)
        timeframe = resolve_timeframe(raw_candle.provider, raw_candle.source_timeframe)
    except UnsupportedProviderError:
        return IngestionResult(
            outcome=IngestionOutcome.REJECTED,
            reason_codes=("UNSUPPORTED_PROVIDER",),
            candidate_raw_candle=raw_candle,
            candidate_normalized_candle=None,
            existing_record_id=None,
        )
    except UnsupportedProviderSymbolError:
        return IngestionResult(
            outcome=IngestionOutcome.REJECTED,
            reason_codes=("UNSUPPORTED_PROVIDER_SYMBOL",),
            candidate_raw_candle=raw_candle,
            candidate_normalized_candle=None,
            existing_record_id=None,
        )
    except UnsupportedProviderTimeframeError:
        return IngestionResult(
            outcome=IngestionOutcome.REJECTED,
            reason_codes=("UNSUPPORTED_PROVIDER_TIMEFRAME",),
            candidate_raw_candle=raw_candle,
            candidate_normalized_candle=None,
            existing_record_id=None,
        )

    normalized_candle = NormalizedCandle(
        record_id=normalized_record_id,
        content_fingerprint=normalized_content_fingerprint,
        raw_candle_id=raw_candle.record_id,
        provider=raw_candle.provider,
        source_reference=raw_candle.source_reference,
        source_symbol=raw_candle.source_symbol,
        source_timeframe=raw_candle.source_timeframe,
        symbol=symbol,
        timeframe=timeframe,
        event_time_utc=raw_candle.event_time_utc,
        availability_time_utc=raw_candle.availability_time_utc,
        processing_time_utc=raw_candle.processing_time_utc,
        original_event_time=raw_candle.original_event_time,
        original_availability_time=raw_candle.original_availability_time,
        original_timezone=raw_candle.original_timezone,
        open=raw_candle.open,
        high=raw_candle.high,
        low=raw_candle.low,
        close=raw_candle.close,
        volume=raw_candle.volume,
        volume_kind=raw_candle.volume_kind,
        completeness=raw_candle.completeness,
        rule_version=normalized_rule_version,
        contract_version=normalized_contract_version,
        schema_version=normalized_schema_version,
        provenance_id=normalized_provenance_id,
    )

    return IngestionResult(
        outcome=IngestionOutcome.ACCEPTED,
        reason_codes=(),
        candidate_raw_candle=raw_candle,
        candidate_normalized_candle=normalized_candle,
        existing_record_id=None,
    )
