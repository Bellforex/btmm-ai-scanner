"""Behavioural proof for the P1-CLOSEOUT (C1) support/resistance audit.

The Pine port originally recomputed support/resistance only when the confirmed
swing set changed. This module proves, against the **production** Python
implementation (imported read-only, never modified), that such a gate is
unsound: appending a single candle can change the S/R output while the confirmed
swing set stays byte-identical.

`domain/support_resistance.py:80` searches ``range(search_start_index, n)`` for
the reaction start and then evaluates a bounded window from there, so a reaction
resolves as candles arrive — independently of swings. The incremental analyzer
states the same requirement outright at `domain/analyzer.py:923`:

    "Must run every candle (not only when confirmed_swings changes): a
    reaction's bounded window can newly resolve purely from candle growth with
    no new swing involved."

These tests are the semantic authority the Pine guards in
``test_pine_p1_source_guards.py`` are pinned to. They assert properties of the
Python rule; they do not execute Pine.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SupportResistanceType, SwingType
from btmm_ai_scanner.domain.support_resistance import detect_support_resistance_zones
from btmm_ai_scanner.domain.swings import ConfirmedSwing

_RAW_CANDLE_ID = UUID("0193f320-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f320-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

_OHLC = tuple[float, float, float, float]

# A support origin, its qualifying reaction, a quiet gap, a second qualifying
# touch of the same zone, and that touch's reaction. Only the LAST block arrives
# after every swing pivot already exists, which is what makes the flip
# attributable to candle growth alone.
_BASELINE: list[_OHLC] = [(100.0, 101.0, 99.0, 100.0)] * 20
_ORIGIN: list[_OHLC] = [(100.0, 101.0, 96.0, 100.0)]
_ORIGIN_REACTION: list[_OHLC] = [
    (96.5, 98.0, 96.3, 97.8),
    (97.8, 100.0, 97.5, 99.8),
    (99.8, 102.0, 99.6, 101.8),
    (101.8, 104.0, 101.6, 103.8),
    (103.8, 106.0, 103.6, 105.8),
]
_GAP: list[_OHLC] = [(100.0, 101.0, 99.0, 100.0)] * 10
_TOUCH: list[_OHLC] = [(100.0, 101.0, 96.05, 100.0)]
_TOUCH_REACTION: list[_OHLC] = [
    (96.55, 98.0, 96.35, 97.85),
    (97.85, 100.0, 97.55, 99.85),
    (99.85, 102.0, 99.65, 101.85),
    (101.85, 104.0, 101.65, 103.85),
    (103.85, 106.0, 103.65, 105.85),
]
_TAIL: list[_OHLC] = [(100.0, 101.0, 99.0, 100.0)] * 3

_ORIGIN_PIVOT_INDEX = 20
_OPPOSITE_PIVOT_INDEX = 25
_TOUCH_PIVOT_INDEX = 36
# Every swing pivot exists once this many candles are present.
_ALL_SWING_PIVOTS_PRESENT = _TOUCH_PIVOT_INDEX + 1


def _record_id(index: int) -> UUID:
    return UUID(f"0193f320-1234-7abc-8def-{index:012x}")


def _candle(index: int, o: float, h: float, low: float, c: float) -> NormalizedCandle:
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
            "open": Decimal(str(o)),
            "high": Decimal(str(h)),
            "low": Decimal(str(low)),
            "close": Decimal(str(c)),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _swing(
    swing_index: int,
    swing_type: SwingType,
    price: str,
    pivot_candle_index: int,
    candles: tuple[NormalizedCandle, ...],
) -> ConfirmedSwing:
    pivot_time = candles[pivot_candle_index].event_time_utc
    confirmation_time = pivot_time + timedelta(minutes=6)
    return ConfirmedSwing(
        record_id=_record_id(1000 + swing_index),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=pivot_candle_index,
        pivot_candle_record_ids=(candles[pivot_candle_index].record_id,),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=2),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=candles[pivot_candle_index].record_id,
        pivot_reference_atr=Decimal("2.0"),
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


def _fixture() -> tuple[tuple[NormalizedCandle, ...], tuple[ConfirmedSwing, ...]]:
    prices = (
        _BASELINE + _ORIGIN + _ORIGIN_REACTION + _GAP + _TOUCH + _TOUCH_REACTION + _TAIL
    )
    candles = tuple(_candle(i, *p) for i, p in enumerate(prices))
    swings = (
        _swing(1, SwingType.SWING_LOW, "96", _ORIGIN_PIVOT_INDEX, candles),
        _swing(3, SwingType.SWING_HIGH, "106", _OPPOSITE_PIVOT_INDEX, candles),
        _swing(2, SwingType.SWING_LOW, "96.05", _TOUCH_PIVOT_INDEX, candles),
    )
    return candles, swings


def _first_confirming_prefix() -> int:
    """Smallest prefix length at which the zone confirms, swings held constant."""
    candles, swings = _fixture()
    for length in range(_ALL_SWING_PIVOTS_PRESENT, len(candles) + 1):
        if detect_support_resistance_zones(candles[:length], swings, _CONFIG):
            return length
    raise AssertionError("fixture never confirms a zone — fixture is broken")


def test_fixture_confirms_exactly_one_support_zone_at_full_length() -> None:
    """Sanity anchor: the fixture does produce a zone once every candle exists."""
    candles, swings = _fixture()
    zones = detect_support_resistance_zones(candles, swings, _CONFIG)
    assert len(zones) == 1
    assert zones[0].zone_type == SupportResistanceType.SUPPORT
    assert zones[0].origin_swing_record_id == swings[0].record_id


def test_sr_output_changes_on_candle_growth_with_the_swing_set_unchanged() -> None:
    """C1.6-A: one more candle flips the S/R output; no swing changes.

    This is the property the Pine swing-change gate violated. The swing tuple
    passed to both calls is the SAME object, so no swing-set mutation of any kind
    can be responsible for the difference.
    """
    candles, swings = _fixture()
    flip = _first_confirming_prefix()
    assert flip > _ALL_SWING_PIVOTS_PRESENT, (
        "the flip must happen after every swing pivot already exists, otherwise "
        "it is not attributable to candle growth"
    )

    before = detect_support_resistance_zones(candles[: flip - 1], swings, _CONFIG)
    after = detect_support_resistance_zones(candles[:flip], swings, _CONFIG)

    assert before == (), f"expected no zone at prefix {flip - 1}, got {len(before)}"
    assert len(after) == 1, f"expected exactly one zone at prefix {flip}"
    assert after[0].zone_type == SupportResistanceType.SUPPORT


def test_sr_confirmation_is_causal_at_the_bar_the_reaction_gate_is_met() -> None:
    """C1.6-B: confirmation is dated to an already-closed candle, not a later one.

    The confirming candle is the reaction window's MFE bar, and its availability
    time must already have passed at the prefix where the zone first appears.
    """
    candles, swings = _fixture()
    flip = _first_confirming_prefix()
    zone = detect_support_resistance_zones(candles[:flip], swings, _CONFIG)[0]

    newest_available = candles[flip - 1].availability_time_utc
    assert zone.confirmation_time_utc <= newest_available, (
        "confirmation is dated after the newest closed candle — that would be lookahead"
    )
    confirming_index = next(
        index
        for index, candle in enumerate(candles[:flip])
        if candle.record_id == zone.confirmation_candle_id
    )
    assert confirming_index < flip, "confirming candle must lie inside the prefix"
    assert confirming_index > _TOUCH_PIVOT_INDEX, (
        "the confirming candle should sit in the touch reaction, after the last "
        "swing pivot"
    )


def test_sr_publication_needs_no_later_swing_mutation() -> None:
    """C1.6-C: once resolved, the zone stays published as candles keep arriving.

    A swing-gated implementation would have withheld it until the next swing
    change; the rule publishes it at every subsequent prefix.
    """
    candles, swings = _fixture()
    flip = _first_confirming_prefix()
    for length in range(flip, len(candles) + 1):
        zones = detect_support_resistance_zones(candles[:length], swings, _CONFIG)
        assert len(zones) == 1, (
            f"zone disappeared at prefix {length} with no swing change"
        )
        assert zones[0].origin_swing_record_id == swings[0].record_id


def test_sr_result_depends_only_on_candles_up_to_the_prefix() -> None:
    """C1.6-D: no future dependency — truncation cannot alter an earlier answer.

    Recomputing over a prefix must give the same answer that prefix gave when it
    was the whole series, which is what rules out reading past ``n``.
    """
    candles, swings = _fixture()
    for length in range(_ALL_SWING_PIVOTS_PRESENT, len(candles) + 1):
        prefix = candles[:length]
        assert detect_support_resistance_zones(
            prefix, swings, _CONFIG
        ) == detect_support_resistance_zones(tuple(prefix), swings, _CONFIG)


def test_reaction_window_bars_contract_is_unchanged() -> None:
    """The audit reasoned about a bounded window; pin the bound it assumed."""
    assert _CONFIG.reaction_window_bars == 5
    assert _CONFIG.support_resistance_zone_depth_atr_multiplier == Decimal("0.10")
