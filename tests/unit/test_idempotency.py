from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import (
    CandleCompleteness,
    CandleVolumeKind,
    RawCandle,
)
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.idempotency import evaluate_idempotency
from btmm_ai_scanner.market_data.results import IngestionOutcome

_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT_A = "a" * 64
_FINGERPRINT_B = "b" * 64
_FINGERPRINT_C = "c" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)


def _raw_candle(
    record_id: UUID,
    *,
    content_fingerprint: str = _FINGERPRINT_A,
    source_reference: str = "fxcm-xauusd-m1",
    event_time_utc: datetime = _EVENT_TIME,
) -> RawCandle:
    return RawCandle.model_validate(
        {
            "record_id": record_id,
            "content_fingerprint": content_fingerprint,
            "provider": "FXCM",
            "source_reference": source_reference,
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "event_time_utc": event_time_utc,
            "availability_time_utc": event_time_utc + timedelta(minutes=1),
            "processing_time_utc": event_time_utc + timedelta(minutes=1, seconds=1),
            "original_event_time": event_time_utc,
            "original_availability_time": event_time_utc + timedelta(minutes=1),
            "original_timezone": "UTC",
            "open": Decimal("100.0"),
            "high": Decimal("101.0"),
            "low": Decimal("99.5"),
            "close": Decimal("100.5"),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _normalized_candle(record_id: UUID, raw_candle: RawCandle) -> NormalizedCandle:
    return NormalizedCandle.model_validate(
        {
            "record_id": record_id,
            "content_fingerprint": _FINGERPRINT_C,
            "raw_candle_id": raw_candle.record_id,
            "provider": raw_candle.provider,
            "source_reference": raw_candle.source_reference,
            "source_symbol": raw_candle.source_symbol,
            "source_timeframe": raw_candle.source_timeframe,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": raw_candle.event_time_utc,
            "availability_time_utc": raw_candle.availability_time_utc,
            "processing_time_utc": raw_candle.processing_time_utc,
            "original_event_time": raw_candle.original_event_time,
            "original_availability_time": raw_candle.original_availability_time,
            "original_timezone": raw_candle.original_timezone,
            "open": raw_candle.open,
            "high": raw_candle.high,
            "low": raw_candle.low,
            "close": raw_candle.close,
            "volume": raw_candle.volume,
            "volume_kind": raw_candle.volume_kind,
            "completeness": raw_candle.completeness,
            "rule_version": raw_candle.rule_version,
            "contract_version": raw_candle.contract_version,
            "schema_version": raw_candle.schema_version,
            "provenance_id": raw_candle.provenance_id,
        }
    )


def test_evaluate_idempotency_accepts_new_record_with_empty_existing_set() -> None:
    candidate_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd10")
    candidate = _raw_candle(candidate_id)
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd11"), candidate
    )
    result = evaluate_idempotency(candidate, normalized, [])
    assert result.outcome == IngestionOutcome.ACCEPTED
    assert result.existing_record_id is None
    assert result.candidate_normalized_candle is not None


def test_evaluate_idempotency_detects_exact_duplicate() -> None:
    existing_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd20")
    candidate_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd21")
    existing = _raw_candle(existing_id, content_fingerprint=_FINGERPRINT_A)
    candidate = _raw_candle(candidate_id, content_fingerprint=_FINGERPRINT_A)
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd22"), candidate
    )
    result = evaluate_idempotency(candidate, normalized, [existing])
    assert result.outcome == IngestionOutcome.EXACT_DUPLICATE
    assert result.existing_record_id == existing_id
    assert result.candidate_normalized_candle is None


def test_evaluate_idempotency_detects_conflicting_revision() -> None:
    existing_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd30")
    candidate_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd31")
    existing = _raw_candle(existing_id, content_fingerprint=_FINGERPRINT_A)
    candidate = _raw_candle(candidate_id, content_fingerprint=_FINGERPRINT_B)
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd32"), candidate
    )
    result = evaluate_idempotency(candidate, normalized, [existing])
    assert result.outcome == IngestionOutcome.CONFLICTING_REVISION
    assert result.existing_record_id == existing_id
    assert result.reason_codes == ("CONFLICTING_REVISION_DETECTED",)
    assert result.candidate_normalized_candle is None


def test_evaluate_idempotency_conflicting_revision_takes_precedence_over_exact_match() -> (
    None
):
    exact_existing_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd40")
    conflicting_existing_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd41")
    candidate_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd42")

    exact_existing = _raw_candle(exact_existing_id, content_fingerprint=_FINGERPRINT_A)
    conflicting_existing = _raw_candle(
        conflicting_existing_id, content_fingerprint=_FINGERPRINT_B
    )
    candidate = _raw_candle(candidate_id, content_fingerprint=_FINGERPRINT_A)
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd43"), candidate
    )

    result = evaluate_idempotency(
        candidate, normalized, [exact_existing, conflicting_existing]
    )
    assert result.outcome == IngestionOutcome.CONFLICTING_REVISION
    assert result.existing_record_id == conflicting_existing_id


def test_evaluate_idempotency_ignores_different_identity_records() -> None:
    other_identity_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd50")
    candidate_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd51")
    other_identity = _raw_candle(
        other_identity_id,
        content_fingerprint=_FINGERPRINT_A,
        source_reference="fxcm-eurusd-m1",
    )
    candidate = _raw_candle(candidate_id, content_fingerprint=_FINGERPRINT_A)
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd52"), candidate
    )
    result = evaluate_idempotency(candidate, normalized, [other_identity])
    assert result.outcome == IngestionOutcome.ACCEPTED
    assert result.existing_record_id is None


def test_evaluate_idempotency_preserves_stable_ordering_of_matches() -> None:
    first_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd60")
    second_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd61")
    candidate_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd62")

    first_existing = _raw_candle(first_id, content_fingerprint=_FINGERPRINT_A)
    second_existing = _raw_candle(second_id, content_fingerprint=_FINGERPRINT_A)
    candidate = _raw_candle(candidate_id, content_fingerprint=_FINGERPRINT_A)
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd63"), candidate
    )

    result = evaluate_idempotency(
        candidate, normalized, [first_existing, second_existing]
    )
    assert result.existing_record_id == first_id

    reordered_result = evaluate_idempotency(
        candidate, normalized, [second_existing, first_existing]
    )
    assert reordered_result.existing_record_id == second_id


def test_evaluate_idempotency_does_not_mutate_existing_records() -> None:
    existing_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd70")
    candidate_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd71")
    existing = _raw_candle(existing_id, content_fingerprint=_FINGERPRINT_A)
    candidate = _raw_candle(candidate_id, content_fingerprint=_FINGERPRINT_A)
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd72"), candidate
    )
    existing_snapshot = existing.model_dump()
    existing_list = [existing]
    evaluate_idempotency(candidate, normalized, existing_list)
    assert existing.model_dump() == existing_snapshot
    assert existing_list == [existing]


def test_evaluate_idempotency_does_not_select_automatic_revision_winner() -> None:
    existing_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd80")
    candidate_id = UUID("0193f2c0-1234-7abc-8def-abcdefabcd81")
    existing = _raw_candle(existing_id, content_fingerprint=_FINGERPRINT_A)
    candidate = _raw_candle(candidate_id, content_fingerprint=_FINGERPRINT_B)
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd82"), candidate
    )
    result = evaluate_idempotency(candidate, normalized, [existing])
    assert result.outcome == IngestionOutcome.CONFLICTING_REVISION
    assert result.candidate_raw_candle is not None
    assert result.candidate_raw_candle.record_id == candidate_id
    assert result.existing_record_id == existing_id
