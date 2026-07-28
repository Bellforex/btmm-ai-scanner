import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import analyzer as domain_analyzer
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure import analyzer as structure_analyzer
from btmm_ai_scanner.structure.analyzer import analyze_structure_state
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_RAW_CANDLE_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdff")
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
    return UUID(f"0193f460-1234-7abc-8def-{index:012x}")


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


_FULL_CLOSES = ["95"] * 8 + ["110", "95", "95", "95", "120"]
_FULL_CANDLES = _build(_FULL_CLOSES)
_BOOTSTRAP_SWINGS = (
    _swing(1, SwingType.SWING_LOW, "90", 0, 1, _FULL_CANDLES),
    _swing(2, SwingType.SWING_HIGH, "100", 2, 3, _FULL_CANDLES),
    _swing(3, SwingType.SWING_LOW, "91", 4, 5, _FULL_CANDLES),
    _swing(4, SwingType.SWING_HIGH, "101", 6, 7, _FULL_CANDLES),
)


def _swings_visible_through(
    swings: tuple[ConfirmedSwing, ...], watermark: datetime
) -> tuple[ConfirmedSwing, ...]:
    return tuple(s for s in swings if s.meaningful_confirmation_time_utc <= watermark)


def test_batch_and_replay_produce_identical_structure_transitions_for_the_same_prefix() -> (
    None
):
    batch_result = analyze_structure_state(
        _FULL_CANDLES, _BOOTSTRAP_SWINGS, _CONFIG, _HashIdentityProvider()
    )

    # "Replay": incrementally grow the candle prefix one candle at a time,
    # each time supplying only the swings already visible as of that
    # prefix's final candle; the last step's inputs equal the batch inputs.
    replay_result = None
    for k in range(1, len(_FULL_CANDLES) + 1):
        prefix_candles = _FULL_CANDLES[:k]
        watermark = prefix_candles[-1].availability_time_utc
        prefix_swings = _swings_visible_through(_BOOTSTRAP_SWINGS, watermark)
        replay_result = analyze_structure_state(
            prefix_candles, prefix_swings, _CONFIG, _HashIdentityProvider()
        )

    assert replay_result is not None
    assert replay_result.structure_transitions == batch_result.structure_transitions


def test_batch_and_replay_produce_identical_current_state_for_the_same_prefix() -> None:
    batch_result = analyze_structure_state(
        _FULL_CANDLES, _BOOTSTRAP_SWINGS, _CONFIG, _HashIdentityProvider()
    )

    replay_result = None
    for k in range(1, len(_FULL_CANDLES) + 1):
        prefix_candles = _FULL_CANDLES[:k]
        watermark = prefix_candles[-1].availability_time_utc
        prefix_swings = _swings_visible_through(_BOOTSTRAP_SWINGS, watermark)
        replay_result = analyze_structure_state(
            prefix_candles, prefix_swings, _CONFIG, _HashIdentityProvider()
        )

    assert replay_result is not None
    assert replay_result.current_state == batch_result.current_state


def test_unchanged_structure_transitions_retain_the_same_record_id_across_growing_prefixes() -> (
    None
):
    short_prefix_candles = _FULL_CANDLES[:9]  # bootstrap + the first BOS break
    short_watermark = short_prefix_candles[-1].availability_time_utc
    short_swings = _swings_visible_through(_BOOTSTRAP_SWINGS, short_watermark)
    short_result = analyze_structure_state(
        short_prefix_candles, short_swings, _CONFIG, _HashIdentityProvider()
    )

    full_result = analyze_structure_state(
        _FULL_CANDLES, _BOOTSTRAP_SWINGS, _CONFIG, _HashIdentityProvider()
    )

    short_ids = {t.record_id for t in short_result.structure_transitions}
    full_ids = {t.record_id for t in full_result.structure_transitions}
    assert len(short_ids) > 0
    assert short_ids.issubset(full_ids)


def test_current_state_record_id_is_stable_across_growing_prefixes() -> None:
    short_prefix_candles = _FULL_CANDLES[:8]
    short_result = analyze_structure_state(
        short_prefix_candles, _BOOTSTRAP_SWINGS, _CONFIG, _HashIdentityProvider()
    )

    full_result = analyze_structure_state(
        _FULL_CANDLES, _BOOTSTRAP_SWINGS, _CONFIG, _HashIdentityProvider()
    )

    assert short_result.current_state is not None
    assert full_result.current_state is not None
    assert short_result.current_state.record_id == full_result.current_state.record_id


def test_current_state_fingerprint_changes_only_when_public_content_changes() -> None:
    # An extra, purely neutral trailing candle changes nothing structurally
    # (no break, no bootstrap effect) -> the current_state fingerprint must
    # stay identical.
    bootstrap_only = _build(["95"] * 8)
    bootstrap_plus_neutral = _build(["95"] * 9)

    result_a = analyze_structure_state(
        bootstrap_only, _BOOTSTRAP_SWINGS, _CONFIG, _HashIdentityProvider()
    )
    result_b = analyze_structure_state(
        bootstrap_plus_neutral, _BOOTSTRAP_SWINGS, _CONFIG, _HashIdentityProvider()
    )
    assert result_a.current_state is not None
    assert result_b.current_state is not None
    assert result_a.current_state.record_id == result_b.current_state.record_id
    assert (
        result_a.current_state.content_fingerprint
        == result_b.current_state.content_fingerprint
    )

    # A later candle that actually breaks weak_high changes real public
    # content (active_weak_high_swing_id, availability_time_utc) -> the
    # fingerprint must differ, even though the record_id stays the same.
    bootstrap_plus_break = _build(["95"] * 8 + ["110"])
    result_c = analyze_structure_state(
        bootstrap_plus_break, _BOOTSTRAP_SWINGS, _CONFIG, _HashIdentityProvider()
    )
    assert result_c.current_state is not None
    assert result_c.current_state.record_id == result_a.current_state.record_id
    assert (
        result_c.current_state.content_fingerprint
        != result_a.current_state.content_fingerprint
    )


def test_structure_fingerprint_serializer_matches_market_measurement_serializer() -> (
    None
):
    sample_fields: dict[str, object] = {
        "symbol": InternalSymbol.XAUUSD,
        "timeframe": Timeframe.M1,
        "price": Decimal("101.50"),
        "zero_price": Decimal("0"),
        "count": 3,
        "flag": True,
        "missing": None,
        "identifier": _record_id(1),
        "version": SemVer.parse("1.0.0"),
        "timestamp": _BASE_TIME,
        "label": "HIGHER_HIGH",
        "nested": {"a": [Decimal("1.10"), None, InternalSymbol.EURUSD]},
        "items": (1, "two", Decimal("3.30")),
    }

    structure_canonical = structure_analyzer._canonicalize(sample_fields)
    domain_canonical = domain_analyzer._canonicalize(sample_fields)
    assert structure_canonical == domain_canonical

    structure_fingerprint = structure_analyzer._compute_content_fingerprint(
        sample_fields
    )
    domain_fingerprint = domain_analyzer._compute_content_fingerprint(sample_fields)
    assert structure_fingerprint == domain_fingerprint
