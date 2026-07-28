import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.analyzer import analyze_structure_state
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import StructureDirection

_RAW_CANDLE_ID = UUID("0193f420-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f420-1234-7abc-8def-abcdefabcdff")
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
    return UUID(f"0193f420-1234-7abc-8def-{index:012x}")


def _candle(index: int) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal("100"),
            "high": Decimal("101"),
            "low": Decimal("99"),
            "close": Decimal("100"),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _build(count: int) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i) for i in range(count))


def _swing(
    index: int,
    swing_type: SwingType,
    price: str,
    pivot_bar_index: int,
    confirmation_bar_index: int,
    candles: tuple[NormalizedCandle, ...],
    reference_atr: str = "1.0",
) -> ConfirmedSwing:
    pivot_time = candles[pivot_bar_index].event_time_utc
    confirmation_time = candles[confirmation_bar_index].availability_time_utc
    return ConfirmedSwing(
        record_id=_record_id(1000 + index),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=pivot_bar_index,
        pivot_candle_record_ids=(candles[pivot_bar_index].record_id,),
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


def test_structure_bootstrap_remains_undetermined_with_zero_swings() -> None:
    candles = _build(20)
    result = analyze_structure_state(candles, (), _CONFIG, _HashIdentityProvider())
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.UNDETERMINED


def test_structure_bootstrap_remains_undetermined_with_one_swing() -> None:
    candles = _build(20)
    swings = (_swing(1, SwingType.SWING_HIGH, "100", 0, 1, candles),)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.UNDETERMINED


def test_structure_bootstrap_remains_undetermined_with_two_swings() -> None:
    candles = _build(4)
    swings = (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles),
    )
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.UNDETERMINED


def test_structure_bootstrap_remains_undetermined_with_three_swings() -> None:
    candles = _build(6)
    swings = (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles),
        _swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),
    )
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.UNDETERMINED


def test_structure_bootstrap_establishes_bullish_direction() -> None:
    candles = _build(8)
    swings = (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles),
        _swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),
        _swing(4, SwingType.SWING_HIGH, "101", 6, 7, candles),
    )
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.BULLISH


def test_structure_bootstrap_establishes_bearish_direction() -> None:
    candles = _build(8)
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100", 0, 1, candles),
        _swing(2, SwingType.SWING_LOW, "90", 2, 3, candles),
        _swing(3, SwingType.SWING_HIGH, "99", 4, 5, candles),
        _swing(4, SwingType.SWING_LOW, "89", 6, 7, candles),
    )
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.BEARISH


def test_structure_bootstrap_remains_undetermined_on_contradictory_evidence() -> None:
    candles = _build(8)
    swings = (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles),
        _swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),  # HIGHER_LOW
        _swing(4, SwingType.SWING_HIGH, "99", 6, 7, candles),  # LOWER_HIGH
    )
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.UNDETERMINED


def test_bootstrap_uses_latest_non_equal_relationships() -> None:
    candles = _build(12)
    swings = (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "100.00", 2, 3, candles),
        _swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),  # HIGHER_LOW (latest LOW)
        _swing(4, SwingType.SWING_HIGH, "100.05", 6, 7, candles),  # EQUAL_HIGH vs #2
        _swing(5, SwingType.SWING_LOW, "92", 8, 9, candles),  # HIGHER_LOW (latest LOW)
        _swing(6, SwingType.SWING_HIGH, "110.00", 10, 11, candles),  # HIGHER_HIGH vs #4
    )
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.current_state is not None
    # Bootstrap could not have resolved from the 2nd-vs-1st HIGH comparison alone
    # (that pair is EQUAL_HIGH); it resolves only once the 3rd HIGH swing's
    # relationship to the 2nd (HIGHER_HIGH) becomes the latest HIGH relationship.
    assert result.current_state.direction == StructureDirection.BULLISH
