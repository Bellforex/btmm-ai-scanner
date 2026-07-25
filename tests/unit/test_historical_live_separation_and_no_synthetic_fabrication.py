from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
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


class _InMemoryHistoricalReplaySource:
    def __init__(self, records: Sequence[NormalizedCandle]) -> None:
        self._records = list(records)

    def replay(self) -> Iterator[NormalizedCandle]:
        yield from self._records


def test_historical_and_live_builders_produce_identical_results_for_same_input() -> (
    None
):
    source_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    historical_result = build_historical_raw_candle(source_input)
    live_result = build_live_raw_candle(source_input)
    assert historical_result.outcome == live_result.outcome == IngestionOutcome.ACCEPTED
    assert historical_result.candidate_raw_candle is not None
    assert live_result.candidate_raw_candle is not None
    assert (
        historical_result.candidate_raw_candle.model_dump()
        == live_result.candidate_raw_candle.model_dump()
    )


def test_historical_and_live_builders_do_not_share_mutable_state() -> None:
    first_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    second_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(
            availability_time_utc=None, original_availability_time=None
        )
    )
    build_historical_raw_candle(first_input)
    second_result = build_live_raw_candle(second_input)
    third_result = build_historical_raw_candle(first_input)

    assert second_result.outcome == IngestionOutcome.INDETERMINATE
    assert third_result.outcome == IngestionOutcome.ACCEPTED


def test_historical_builder_supports_deterministic_replay_ordering() -> None:
    source_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    result = build_historical_raw_candle(source_input)
    assert result.candidate_raw_candle is not None

    normalized_a = NormalizedCandle.model_validate(
        {
            "record_id": UUID("0193f2c0-1234-7abc-8def-abcdefabcd01"),
            "content_fingerprint": "b" * 64,
            "raw_candle_id": result.candidate_raw_candle.record_id,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
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
    )
    replay_source = _InMemoryHistoricalReplaySource([normalized_a])
    first_pass = list(replay_source.replay())
    second_pass = list(replay_source.replay())
    assert first_pass == second_pass == [normalized_a]


def test_live_builder_uses_supplied_processing_time_only() -> None:
    source_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    result = build_live_raw_candle(source_input)
    assert result.candidate_raw_candle is not None
    assert result.candidate_raw_candle.processing_time_utc == _PROCESSING_TIME


def test_pipeline_never_fabricates_synthetic_candle_values() -> None:
    source_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    result = build_historical_raw_candle(source_input)
    assert result.candidate_raw_candle is not None
    assert result.candidate_raw_candle.open == source_input.open
    assert result.candidate_raw_candle.high == source_input.high
    assert result.candidate_raw_candle.low == source_input.low
    assert result.candidate_raw_candle.close == source_input.close
    assert result.candidate_raw_candle.volume == source_input.volume


def test_pipeline_marks_invalid_and_indeterminate_records_as_auditable_not_discarded() -> (
    None
):
    indeterminate_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(
            availability_time_utc=None, original_availability_time=None
        )
    )
    indeterminate_result = build_historical_raw_candle(indeterminate_input)
    assert indeterminate_result.outcome == IngestionOutcome.INDETERMINATE
    assert indeterminate_result.reason_codes == ("AVAILABILITY_TIME_UNAVAILABLE",)

    rejected_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(original_availability_time=None)
    )
    rejected_result = build_historical_raw_candle(rejected_input)
    assert rejected_result.outcome == IngestionOutcome.REJECTED
    assert rejected_result.reason_codes == ("AVAILABILITY_TIME_PAIR_INCONSISTENT",)
