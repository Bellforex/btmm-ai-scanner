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
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType

_RAW_CANDLE_ID = UUID("0193f440-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f440-1234-7abc-8def-abcdefabcdff")
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
    return UUID(f"0193f440-1234-7abc-8def-{index:012x}")


def _candle(index: int, close: str = "95") -> NormalizedCandle:
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


def _bullish_bootstrap_swings(
    candles: tuple[NormalizedCandle, ...],
) -> tuple[ConfirmedSwing, ...]:
    return (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "100", 2, 3, candles),
        _swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),
        _swing(4, SwingType.SWING_HIGH, "101", 6, 7, candles),
    )


def _bearish_bootstrap_swings(
    candles: tuple[NormalizedCandle, ...],
) -> tuple[ConfirmedSwing, ...]:
    return (
        _swing(1, SwingType.SWING_HIGH, "100", 0, 1, candles),
        _swing(2, SwingType.SWING_LOW, "90", 2, 3, candles),
        _swing(3, SwingType.SWING_HIGH, "99", 4, 5, candles),
        _swing(4, SwingType.SWING_LOW, "89", 6, 7, candles),
    )


def test_bullish_break_requires_close_strictly_beyond_level() -> None:
    candles = _build(["95"] * 8 + ["110"])
    swings = _bullish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert len(result.structure_transitions) == 1
    transition = result.structure_transitions[0]
    assert transition.transition_type == StructureTransitionType.BULLISH_BOS
    assert transition.broken_swing_id == swings[3].record_id
    assert transition.broken_level_price == Decimal("101")
    assert transition.break_close_price == Decimal("110")


def test_wick_beyond_level_without_close_does_not_break() -> None:
    # Default neutral candle (close=95) has high=115, which exceeds weak_high
    # (101) as a wick only; the close itself never crosses the level.
    candles = _build(["95"] * 9)
    swings = _bullish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.structure_transitions == ()
    assert result.current_state is not None
    assert result.current_state.active_weak_high_swing_id == swings[3].record_id


def test_close_exactly_at_level_does_not_break() -> None:
    candles = _build(["95"] * 8 + ["101"])
    swings = _bullish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert result.structure_transitions == ()
    assert result.current_state is not None
    assert result.current_state.active_weak_high_swing_id == swings[3].record_id


def test_bullish_bos_breaks_active_weak_high_and_continues_direction() -> None:
    candles = _build(["95"] * 8 + ["110"])
    swings = _bullish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert len(result.structure_transitions) == 1
    transition = result.structure_transitions[0]
    assert transition.transition_type == StructureTransitionType.BULLISH_BOS
    assert transition.direction_before == StructureDirection.BULLISH
    assert transition.direction_after == StructureDirection.BULLISH
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.BULLISH


def test_bearish_bos_breaks_active_weak_low_and_continues_direction() -> None:
    candles = _build(["95"] * 8 + ["70"])
    swings = _bearish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert len(result.structure_transitions) == 1
    transition = result.structure_transitions[0]
    assert transition.transition_type == StructureTransitionType.BEARISH_BOS
    assert transition.direction_before == StructureDirection.BEARISH
    assert transition.direction_after == StructureDirection.BEARISH
    assert transition.broken_swing_id == swings[3].record_id
    assert transition.broken_level_price == Decimal("89")
    assert transition.break_close_price == Decimal("70")


def test_bullish_choch_breaks_active_protected_high_and_reverses_direction() -> None:
    candles = _build(["95"] * 8 + ["150"])
    swings = _bearish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert len(result.structure_transitions) == 1
    transition = result.structure_transitions[0]
    assert transition.transition_type == StructureTransitionType.BULLISH_CHOCH
    assert transition.direction_before == StructureDirection.BEARISH
    assert transition.direction_after == StructureDirection.BULLISH
    assert transition.broken_swing_id == swings[2].record_id  # protected_high (99)
    # New protected_low is the most recent unbroken LOW: swing #4 (89, index 6).
    assert transition.protected_swing_id == swings[3].record_id
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.BULLISH


def test_bearish_choch_breaks_active_protected_low_and_reverses_direction() -> None:
    candles = _build(["95"] * 8 + ["30"])
    swings = _bullish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert len(result.structure_transitions) == 1
    transition = result.structure_transitions[0]
    assert transition.transition_type == StructureTransitionType.BEARISH_CHOCH
    assert transition.direction_before == StructureDirection.BULLISH
    assert transition.direction_after == StructureDirection.BEARISH
    assert transition.broken_swing_id == swings[2].record_id  # protected_low (91)
    # New protected_high is the most recent unbroken HIGH: swing #4 (101, index 6).
    assert transition.protected_swing_id == swings[3].record_id
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.BEARISH


def test_bos_and_choch_are_mutually_exclusive_for_the_same_break() -> None:
    # 102 breaks weak_high (101) but does not cross protected_low (91): only a
    # BOS is eligible here, never a CHoCH.
    candles = _build(["95"] * 8 + ["102"])
    swings = _bullish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert len(result.structure_transitions) == 1
    assert result.structure_transitions[0].transition_type == (
        StructureTransitionType.BULLISH_BOS
    )


def test_repeated_close_beyond_already_broken_level_emits_no_second_transition() -> (
    None
):
    candles = _build(["95"] * 8 + ["110", "120"])
    swings = _bullish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    # No replacement HIGH swing was supplied, so weak_high retires to None after
    # the first break; the second candle closing beyond the old price cannot
    # emit a second transition.
    assert len(result.structure_transitions) == 1
    assert result.current_state is not None
    assert result.current_state.active_weak_high_swing_id is None


def test_broken_weak_level_cannot_emit_repeated_bos() -> None:
    candles = _build(["95"] * 8 + ["110", "115", "120", "125"])
    swings = _bullish_bootstrap_swings(candles)
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())
    assert len(result.structure_transitions) == 1
    assert result.structure_transitions[0].broken_swing_id == swings[3].record_id


def test_level_cannot_break_in_activation_availability_group() -> None:
    # Candle 8 breaks the initial weak_high (101) via BOS #1, retiring it with
    # boundary_index = 8. An intervening LOW pullback swing (index 9/10)
    # preserves strict HIGH/LOW alternation. A replacement HIGH swing (pivot
    # index 11, confirming at candle 12) becomes visible at candle 12's own
    # availability timestamp. Candle 12 closes beyond the replacement's price
    # (115) at that SAME timestamp — candle events are processed before
    # swing-visibility events at an identical timestamp, so the replacement is
    # not yet active and cannot be broken by its own activation-instant
    # candle. A later candle (14) closing beyond the same price DOES break it.
    candles = _build(["95"] * 8 + ["110", "95", "95", "95", "120", "95", "120"])
    bootstrap_swings = _bullish_bootstrap_swings(candles)
    pullback_low = _swing(5, SwingType.SWING_LOW, "93", 9, 10, candles)
    replacement_high = _swing(6, SwingType.SWING_HIGH, "115", 11, 12, candles)
    swings = (*bootstrap_swings, pullback_low, replacement_high)

    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())

    assert len(result.structure_transitions) == 2
    first, second = result.structure_transitions
    assert first.broken_swing_id == bootstrap_swings[3].record_id
    assert first.break_candle_id == candles[8].record_id
    assert second.broken_swing_id == replacement_high.record_id
    assert second.break_candle_id == candles[14].record_id


def test_choch_priority_prevents_same_candle_bos() -> None:
    # A deliberately contrived, non-naturally-occurring fixture: weak_high
    # (75) is priced BELOW protected_low (91), so a single candle's close (80)
    # can breach both simultaneously. CHoCH must take strict priority and BOS
    # must never also fire for the same candle.
    candles = _build(["95"] * 8 + ["80"])
    swings = (
        _swing(1, SwingType.SWING_LOW, "90", 0, 1, candles),
        _swing(2, SwingType.SWING_HIGH, "70", 2, 3, candles),
        _swing(3, SwingType.SWING_LOW, "91", 4, 5, candles),  # HIGHER_LOW
        _swing(4, SwingType.SWING_HIGH, "75", 6, 7, candles),  # HIGHER_HIGH vs #2
    )
    result = analyze_structure_state(candles, swings, _CONFIG, _HashIdentityProvider())

    assert len(result.structure_transitions) == 1
    transition = result.structure_transitions[0]
    assert transition.transition_type == StructureTransitionType.BEARISH_CHOCH
    assert transition.broken_swing_id == swings[2].record_id  # protected_low (91)
    assert transition.protected_swing_id == swings[3].record_id  # new protected_high
    assert result.current_state is not None
    assert result.current_state.direction == StructureDirection.BEARISH
