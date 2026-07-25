from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import (
    CandleCompleteness,
    CandleVolumeKind,
    RawCandle,
)
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.normalization import normalize_raw_candle
from btmm_ai_scanner.market_data.raw_candle_builder import build_historical_raw_candle
from btmm_ai_scanner.market_data.results import IngestionOutcome
from btmm_ai_scanner.market_data.source_input import SourceCandleInput

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_NORMALIZED_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd01")
_NORMALIZED_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd02")
_FINGERPRINT = "a" * 64
_NORMALIZED_FINGERPRINT = "b" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)

_RAW_RULE_VERSION = SemVer.parse("0.1.0")
_RAW_CONTRACT_VERSION = SemVer.parse("0.1.0")
_RAW_SCHEMA_VERSION = SemVer.parse("0.1.0")

_NORMALIZED_RULE_VERSION = SemVer.parse("0.2.0")
_NORMALIZED_CONTRACT_VERSION = SemVer.parse("0.2.0")
_NORMALIZED_SCHEMA_VERSION = SemVer.parse("0.2.0")


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
        "rule_version": _RAW_RULE_VERSION,
        "contract_version": _RAW_CONTRACT_VERSION,
        "schema_version": _RAW_SCHEMA_VERSION,
        "provenance_id": _PROVENANCE_ID,
    }
    kwargs.update(overrides)
    return kwargs


def _build_valid_raw_candle(**overrides: object) -> RawCandle:
    source_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(**overrides)
    )
    result = build_historical_raw_candle(source_input)
    assert result.candidate_raw_candle is not None
    return result.candidate_raw_candle


def test_normalize_raw_candle_accepts_valid_raw_candle() -> None:
    raw_candle = _build_valid_raw_candle()
    result = normalize_raw_candle(
        raw_candle,
        normalized_record_id=_NORMALIZED_RECORD_ID,
        normalized_content_fingerprint=_NORMALIZED_FINGERPRINT,
        normalized_rule_version=_NORMALIZED_RULE_VERSION,
        normalized_contract_version=_NORMALIZED_CONTRACT_VERSION,
        normalized_schema_version=_NORMALIZED_SCHEMA_VERSION,
        normalized_provenance_id=_NORMALIZED_PROVENANCE_ID,
    )
    assert result.outcome == IngestionOutcome.ACCEPTED
    assert result.candidate_normalized_candle is not None
    assert result.candidate_normalized_candle.symbol == InternalSymbol.XAUUSD
    assert result.candidate_normalized_candle.timeframe == Timeframe.M1


def test_normalize_raw_candle_produces_distinct_normalized_record_id() -> None:
    raw_candle = _build_valid_raw_candle()
    result = normalize_raw_candle(
        raw_candle,
        normalized_record_id=_NORMALIZED_RECORD_ID,
        normalized_content_fingerprint=_NORMALIZED_FINGERPRINT,
        normalized_rule_version=_NORMALIZED_RULE_VERSION,
        normalized_contract_version=_NORMALIZED_CONTRACT_VERSION,
        normalized_schema_version=_NORMALIZED_SCHEMA_VERSION,
        normalized_provenance_id=_NORMALIZED_PROVENANCE_ID,
    )
    assert result.candidate_normalized_candle is not None
    assert result.candidate_normalized_candle.record_id == _NORMALIZED_RECORD_ID
    assert result.candidate_normalized_candle.record_id != raw_candle.record_id


def test_normalize_raw_candle_preserves_raw_candle_lineage() -> None:
    raw_candle = _build_valid_raw_candle()
    result = normalize_raw_candle(
        raw_candle,
        normalized_record_id=_NORMALIZED_RECORD_ID,
        normalized_content_fingerprint=_NORMALIZED_FINGERPRINT,
        normalized_rule_version=_NORMALIZED_RULE_VERSION,
        normalized_contract_version=_NORMALIZED_CONTRACT_VERSION,
        normalized_schema_version=_NORMALIZED_SCHEMA_VERSION,
        normalized_provenance_id=_NORMALIZED_PROVENANCE_ID,
    )
    assert result.candidate_normalized_candle is not None
    assert result.candidate_normalized_candle.raw_candle_id == raw_candle.record_id
    assert result.candidate_normalized_candle.provider == raw_candle.provider
    assert (
        result.candidate_normalized_candle.source_reference
        == raw_candle.source_reference
    )
    assert result.candidate_normalized_candle.open == raw_candle.open
    assert result.candidate_normalized_candle.close == raw_candle.close


def test_normalize_raw_candle_rejects_unsupported_symbol_mapping() -> None:
    raw_candle = _build_valid_raw_candle(source_symbol="USDJPY")
    result = normalize_raw_candle(
        raw_candle,
        normalized_record_id=_NORMALIZED_RECORD_ID,
        normalized_content_fingerprint=_NORMALIZED_FINGERPRINT,
        normalized_rule_version=_NORMALIZED_RULE_VERSION,
        normalized_contract_version=_NORMALIZED_CONTRACT_VERSION,
        normalized_schema_version=_NORMALIZED_SCHEMA_VERSION,
        normalized_provenance_id=_NORMALIZED_PROVENANCE_ID,
    )
    assert result.outcome == IngestionOutcome.REJECTED
    assert result.reason_codes == ("UNSUPPORTED_PROVIDER_SYMBOL",)
    assert result.candidate_normalized_candle is None


def test_normalize_raw_candle_rejects_unsupported_timeframe_mapping() -> None:
    raw_candle = _build_valid_raw_candle(source_timeframe="M30")
    result = normalize_raw_candle(
        raw_candle,
        normalized_record_id=_NORMALIZED_RECORD_ID,
        normalized_content_fingerprint=_NORMALIZED_FINGERPRINT,
        normalized_rule_version=_NORMALIZED_RULE_VERSION,
        normalized_contract_version=_NORMALIZED_CONTRACT_VERSION,
        normalized_schema_version=_NORMALIZED_SCHEMA_VERSION,
        normalized_provenance_id=_NORMALIZED_PROVENANCE_ID,
    )
    assert result.outcome == IngestionOutcome.REJECTED
    assert result.reason_codes == ("UNSUPPORTED_PROVIDER_TIMEFRAME",)
    assert result.candidate_normalized_candle is None


def test_normalize_raw_candle_never_mutates_raw_candle() -> None:
    raw_candle = _build_valid_raw_candle()
    before = raw_candle.model_dump()
    normalize_raw_candle(
        raw_candle,
        normalized_record_id=_NORMALIZED_RECORD_ID,
        normalized_content_fingerprint=_NORMALIZED_FINGERPRINT,
        normalized_rule_version=_NORMALIZED_RULE_VERSION,
        normalized_contract_version=_NORMALIZED_CONTRACT_VERSION,
        normalized_schema_version=_NORMALIZED_SCHEMA_VERSION,
        normalized_provenance_id=_NORMALIZED_PROVENANCE_ID,
    )
    after = raw_candle.model_dump()
    assert before == after


def test_pipeline_reuses_caller_supplied_identity_fingerprint_versions_and_provenance_without_generation() -> (
    None
):
    raw_candle = _build_valid_raw_candle()

    # Raw builder preserves every caller-supplied raw identity/version/provenance value.
    assert raw_candle.record_id == _RECORD_ID
    assert raw_candle.content_fingerprint == _FINGERPRINT
    assert raw_candle.rule_version == _RAW_RULE_VERSION
    assert raw_candle.contract_version == _RAW_CONTRACT_VERSION
    assert raw_candle.schema_version == _RAW_SCHEMA_VERSION
    assert raw_candle.provenance_id == _PROVENANCE_ID

    result = normalize_raw_candle(
        raw_candle,
        normalized_record_id=_NORMALIZED_RECORD_ID,
        normalized_content_fingerprint=_NORMALIZED_FINGERPRINT,
        normalized_rule_version=_NORMALIZED_RULE_VERSION,
        normalized_contract_version=_NORMALIZED_CONTRACT_VERSION,
        normalized_schema_version=_NORMALIZED_SCHEMA_VERSION,
        normalized_provenance_id=_NORMALIZED_PROVENANCE_ID,
    )
    normalized_candle = result.candidate_normalized_candle
    assert normalized_candle is not None

    # Normalization preserves every caller-supplied normalized identity/version/
    # provenance value, with no generated replacement anywhere in either output.
    assert normalized_candle.record_id == _NORMALIZED_RECORD_ID
    assert normalized_candle.content_fingerprint == _NORMALIZED_FINGERPRINT
    assert normalized_candle.rule_version == _NORMALIZED_RULE_VERSION
    assert normalized_candle.contract_version == _NORMALIZED_CONTRACT_VERSION
    assert normalized_candle.schema_version == _NORMALIZED_SCHEMA_VERSION
    assert normalized_candle.provenance_id == _NORMALIZED_PROVENANCE_ID
    assert normalized_candle.record_id != raw_candle.record_id
    assert normalized_candle.content_fingerprint != raw_candle.content_fingerprint
    assert normalized_candle.provenance_id != raw_candle.provenance_id
