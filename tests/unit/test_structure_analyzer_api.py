import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import (
    MixedSymbolAnalysisError,
    MixedTimeframeAnalysisError,
    UnsortedCandleSequenceError,
)
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.analyzer import (
    InvalidStructureConfigurationError,
    InvalidSwingReferenceError,
    UnsortedSwingSequenceError,
    analyze_structure_state,
)
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_RAW_CANDLE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = StructureConfiguration()


class _HashIdentityProvider:
    def identify(self, *, output_type: object, semantic_key: tuple[str, ...]) -> UUID:
        payload = output_type.value + "|" + "|".join(semantic_key)  # type: ignore[attr-defined]
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    close: str = "95",
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
    timeframe: Timeframe = Timeframe.M1,
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": symbol.value,
            "source_timeframe": timeframe.value,
            "symbol": symbol,
            "timeframe": timeframe,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(close),
            "high": Decimal(str(float(close) + 20)),
            "low": Decimal(str(float(close) - 20)),
            "close": Decimal(close),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _build(closes: list[str]) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, c) for i, c in enumerate(closes))


def _swing(
    index: int,
    swing_type: SwingType,
    price: str,
    pivot_bar_index: int,
    confirmation_bar_index: int,
    candles: tuple[NormalizedCandle, ...],
    reference_atr: str = "1.0",
    pivot_candle_record_ids: tuple[UUID, ...] | None = None,
) -> ConfirmedSwing:
    pivot_time = candles[pivot_bar_index].event_time_utc
    confirmation_time = candles[confirmation_bar_index].availability_time_utc
    return ConfirmedSwing(
        record_id=_record_id(1000 + index),
        content_fingerprint="a" * 64,
        symbol=candles[pivot_bar_index].symbol,
        timeframe=candles[pivot_bar_index].timeframe,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=pivot_bar_index,
        pivot_candle_record_ids=(
            pivot_candle_record_ids
            if pivot_candle_record_ids is not None
            else (candles[pivot_bar_index].record_id,)
        ),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=1),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=candles[confirmation_bar_index].record_id,
        pivot_reference_atr=Decimal(reference_atr),
        pivot_tie_tolerance=Decimal("0.02"),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("1"),
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def test_analyze_structure_state_returns_empty_aggregate_for_empty_input() -> None:
    result = analyze_structure_state((), (), _CONFIG, _HashIdentityProvider())

    assert result.symbol is None
    assert result.timeframe is None
    assert result.analyzed_candle_count == 0
    assert result.analyzed_swing_count == 0
    assert result.swing_relationships == ()
    assert result.structure_transitions == ()
    assert result.current_state is None


def test_analyze_structure_state_rejects_mixed_symbol_input() -> None:
    candles = (
        _candle(0, symbol=InternalSymbol.XAUUSD),
        _candle(1, symbol=InternalSymbol.EURUSD),
    )
    with pytest.raises(MixedSymbolAnalysisError):
        analyze_structure_state(candles, (), _CONFIG, _HashIdentityProvider())


def test_analyze_structure_state_rejects_mixed_timeframe_input() -> None:
    candles = (
        _candle(0, timeframe=Timeframe.M1),
        _candle(1, timeframe=Timeframe.M5),
    )
    with pytest.raises(MixedTimeframeAnalysisError):
        analyze_structure_state(candles, (), _CONFIG, _HashIdentityProvider())


def test_analyze_structure_state_rejects_unsorted_candles() -> None:
    candles = _build(["95", "95", "95"])
    reversed_candles = (candles[2], candles[1], candles[0])
    with pytest.raises(UnsortedCandleSequenceError):
        analyze_structure_state(reversed_candles, (), _CONFIG, _HashIdentityProvider())


def test_analyze_structure_state_rejects_unsorted_swings() -> None:
    candles = _build(["95"] * 8)
    low_swing = _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles)
    high_swing = _swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles)
    reversed_swings = (high_swing, low_swing)
    with pytest.raises(UnsortedSwingSequenceError):
        analyze_structure_state(
            candles, reversed_swings, _CONFIG, _HashIdentityProvider()
        )


def test_analyze_structure_state_rejects_duplicate_swing_record_id() -> None:
    candles = _build(["95"] * 8)
    low_swing = _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles)
    duplicate_low_swing = low_swing.model_copy(
        update={"pivot_bar_index": 4, "confirmation_candle_id": candles[5].record_id}
    )
    with pytest.raises(UnsortedSwingSequenceError):
        analyze_structure_state(
            candles, (low_swing, duplicate_low_swing), _CONFIG, _HashIdentityProvider()
        )


def test_structure_outputs_use_engineering_provisional_evidence() -> None:
    candles = _build(["95"] * 8 + ["110"])
    swings = (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles),
        _swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),
        _swing(4, SwingType.SWING_HIGH, "101", 6, 7, candles),
    )
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())

    assert len(result.swing_relationships) > 0
    assert len(result.structure_transitions) > 0
    assert result.current_state is not None
    for relationship in result.swing_relationships:
        assert relationship.evidence_classification == (
            EvidenceClassification.ENGINEERING_PROVISIONAL
        )
    for transition in result.structure_transitions:
        assert transition.evidence_classification == (
            EvidenceClassification.ENGINEERING_PROVISIONAL
        )
    assert result.current_state.evidence_classification == (
        EvidenceClassification.ENGINEERING_PROVISIONAL
    )


def test_analyze_structure_state_rejects_swing_referencing_missing_candle() -> None:
    candles = _build(["95"] * 4)
    phantom_candle_id = _record_id(9999)
    swing = _swing(
        1,
        SwingType.SWING_LOW,
        "90",
        0,
        1,
        candles,
        pivot_candle_record_ids=(phantom_candle_id,),
    )
    with pytest.raises(InvalidSwingReferenceError):
        analyze_structure_state(candles, (swing,), _CONFIG, _HashIdentityProvider())


def test_analyze_structure_state_rejects_missing_instrument_metadata() -> None:
    candle = _candle(0)
    null_symbol_candle = candle.model_copy(update={"symbol": None})
    with pytest.raises(InvalidStructureConfigurationError):
        analyze_structure_state(
            (null_symbol_candle,), (), _CONFIG, _HashIdentityProvider()
        )


def test_analyze_structure_state_is_deterministic_across_repeated_calls() -> None:
    candles = _build(["95"] * 8 + ["110"])
    swings = (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles),
        _swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),
        _swing(4, SwingType.SWING_HIGH, "101", 6, 7, candles),
    )

    first = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    second = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())

    assert first == second
