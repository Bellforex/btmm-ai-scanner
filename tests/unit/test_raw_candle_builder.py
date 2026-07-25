from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.raw_candle_builder import (
    build_historical_raw_candle,
    build_live_raw_candle,
)
from btmm_ai_scanner.market_data.results import IngestionOutcome
from btmm_ai_scanner.market_data.source_input import SourceCandleInput

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)


def _valid_source_input_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _RECORD_ID,
        "content_fingerprint": _FINGERPRINT,
        "provider": "FXCM",
        "source_reference": "fxcm-xauusd-m1",
        "source_symbol": "XAUUSD",
        "source_timeframe": "M1",
        "event_time_utc": _EVENT_TIME,
        "availability_time_utc": _AVAILABILITY_TIME,
        "processing_time_utc": _PROCESSING_TIME,
        "original_event_time": _EVENT_TIME,
        "original_availability_time": _AVAILABILITY_TIME,
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
    kwargs.update(overrides)
    return kwargs


def test_build_historical_raw_candle_accepts_complete_evidence() -> None:
    source_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    result = build_historical_raw_candle(source_input)
    assert result.outcome == IngestionOutcome.ACCEPTED
    assert result.candidate_raw_candle is not None
    assert result.candidate_raw_candle.record_id == _RECORD_ID


def test_build_live_raw_candle_accepts_complete_evidence() -> None:
    source_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    result = build_live_raw_candle(source_input)
    assert result.outcome == IngestionOutcome.ACCEPTED
    assert result.candidate_raw_candle is not None
    assert result.candidate_raw_candle.record_id == _RECORD_ID


def test_raw_candle_builder_returns_indeterminate_for_both_availability_none() -> None:
    source_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(
            availability_time_utc=None, original_availability_time=None
        )
    )
    result = build_historical_raw_candle(source_input)
    assert result.outcome == IngestionOutcome.INDETERMINATE
    assert result.reason_codes == ("AVAILABILITY_TIME_UNAVAILABLE",)
    assert result.candidate_raw_candle is None
    assert result.candidate_normalized_candle is None


def test_raw_candle_builder_returns_rejected_for_one_availability_none() -> None:
    source_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(original_availability_time=None)
    )
    result = build_historical_raw_candle(source_input)
    assert result.outcome == IngestionOutcome.REJECTED
    assert result.reason_codes == ("AVAILABILITY_TIME_PAIR_INCONSISTENT",)
    assert result.candidate_raw_candle is None


def test_raw_candle_builder_returns_rejected_for_inconsistent_availability_instant() -> (
    None
):
    mismatched_original = _AVAILABILITY_TIME + timedelta(minutes=5)
    source_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(original_availability_time=mismatched_original)
    )
    result = build_historical_raw_candle(source_input)
    assert result.outcome == IngestionOutcome.REJECTED
    assert result.reason_codes == ("AVAILABILITY_TIME_INVALID",)
    assert result.candidate_raw_candle is None


def test_raw_candle_builder_returns_rejected_for_raw_candle_validation_failure() -> (
    None
):
    # availability_time_utc equal to event_time_utc satisfies SourceCandleInput's
    # own structural validation (no ordering check), but RawCandle's own
    # cross-field invariant requires availability_time_utc > event_time_utc.
    source_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(
            availability_time_utc=_EVENT_TIME, original_availability_time=_EVENT_TIME
        )
    )
    result = build_historical_raw_candle(source_input)
    assert result.outcome == IngestionOutcome.REJECTED
    assert result.reason_codes == ("RAW_CANDLE_VALIDATION_FAILED",)
    assert result.candidate_raw_candle is None


def test_raw_candle_builder_never_mutates_source_input() -> None:
    source_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    before = source_input.model_dump()
    build_historical_raw_candle(source_input)
    after = source_input.model_dump()
    assert before == after


def test_raw_candle_builder_never_calls_wall_clock() -> None:
    source_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    first = build_historical_raw_candle(source_input)
    second = build_historical_raw_candle(source_input)
    assert first.candidate_raw_candle is not None
    assert second.candidate_raw_candle is not None
    assert (
        first.candidate_raw_candle.processing_time_utc
        == second.candidate_raw_candle.processing_time_utc
        == _PROCESSING_TIME
    )
