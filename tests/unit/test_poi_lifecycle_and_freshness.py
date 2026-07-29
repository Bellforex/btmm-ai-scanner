from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiLifecycleTransitionType,
    PoiTapClassification,
)
from btmm_ai_scanner.poi.lifecycle import LifecycleWalkResult, run_poi_lifecycle

_RAW_CANDLE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_POI_RECORD_ID = UUID("0193f450-1234-7abc-8def-aaaaaaaaaaaa")
_ZONE_TOP = Decimal("101")
_ZONE_BOTTOM = Decimal("100")
_BASELINE_COUNT = 20


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _candle(
    index: int, open_: str, high: str, low: str, close: str
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
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M1.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
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


def _baseline() -> list[NormalizedCandle]:
    return [_candle(i, "100.5", "101", "100", "100.5") for i in range(_BASELINE_COUNT)]


def _build(tail: list[tuple[str, str, str, str]]) -> tuple[NormalizedCandle, ...]:
    baseline = _baseline()
    tail_candles = [_candle(_BASELINE_COUNT + i, *ohlc) for i, ohlc in enumerate(tail)]
    return tuple(baseline + tail_candles)


def _run(
    candles: tuple[NormalizedCandle, ...],
    direction: PoiDirection = PoiDirection.BULLISH,
) -> LifecycleWalkResult:
    atr_values = compute_atr_series(candles, 14)
    availability = candles[_BASELINE_COUNT - 1].availability_time_utc
    return run_poi_lifecycle(
        candles,
        atr_values,
        InternalSymbol.XAUUSD,
        Timeframe.M1,
        _POI_RECORD_ID,
        direction,
        _ZONE_TOP,
        _ZONE_BOTTOM,
        availability,
        _CONFIG,
    )


def test_close_breach_candidate_requires_close_strictly_beyond_overshoot_tolerance() -> (
    None
):
    no_breach = _build([("100.5", "100.6", "99.9", "99.96")])
    breach = _build([("100.5", "100.6", "99.5", "99.85")])

    no_breach_result = _run(no_breach)
    breach_result = _run(breach)

    assert no_breach_result.final_status == PoiLifecycleStatus.NO_BREACH
    assert no_breach_result.transitions == ()
    assert breach_result.transitions[0].transition_type == (
        PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE
    )


def test_wick_beyond_far_boundary_without_close_does_not_confirm_breach() -> None:
    wick_only = _build([("100.5", "100.6", "99.0", "100.4")])

    result = _run(wick_only)

    assert result.final_status == PoiLifecycleStatus.NO_BREACH
    assert result.transitions == ()


def test_reclaim_window_excludes_the_breach_candle_and_confirms_within_three_bars() -> (
    None
):
    candles = _build(
        [
            ("100.5", "100.6", "99.5", "99.85"),  # breach candle itself
            ("99.85", "99.95", "99.8", "99.9"),  # bar 1: not yet reclaimed
            ("99.9", "100.0", "99.85", "99.98"),  # bar 2: not yet reclaimed
            ("99.98", "100.2", "99.95", "100.1"),  # bar 3: reclaim confirmed
        ]
    )

    result = _run(candles)

    transition_types = [t.transition_type for t in result.transitions]
    assert PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE in transition_types
    assert PoiLifecycleTransitionType.RECLAIM_CONFIRMED in transition_types
    reclaim_transition = next(
        t
        for t in result.transitions
        if t.transition_type == PoiLifecycleTransitionType.RECLAIM_CONFIRMED
    )
    breach_transition = next(
        t
        for t in result.transitions
        if t.transition_type == PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE
    )
    assert reclaim_transition.triggering_candle_record_id != (
        breach_transition.triggering_candle_record_id
    )


def test_reclaim_not_confirmed_within_three_bars_allows_genuine_invalidation() -> None:
    candles = _build(
        [
            ("100.5", "100.6", "99.0", "99.5"),  # breach
            ("99.5", "99.6", "99.3", "99.4"),  # bar 1: still beyond
            ("99.4", "99.5", "99.2", "99.3"),  # bar 2: still beyond
            ("99.3", "99.4", "99.1", "99.2"),  # bar 3: still beyond
        ]
    )

    result = _run(candles)

    assert result.final_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED


def test_displacement_after_reclaim_requires_fast_or_strong_fast_leg() -> None:
    reclaim_sequence = [
        ("100.5", "100.6", "99.5", "99.85"),  # breach
        ("99.85", "100.2", "99.8", "100.1"),  # reclaim
    ]
    slow_displacement = _build(
        [*reclaim_sequence, ("100.1", "100.2", "100.05", "100.15")]
    )
    fast_displacement = _build(
        [*reclaim_sequence, ("100.5", "101.5", "100.5", "101.5")]
    )

    slow_result = _run(slow_displacement)
    fast_result = _run(fast_displacement)

    assert PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED not in [
        t.transition_type for t in slow_result.transitions
    ]
    assert PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED in [
        t.transition_type for t in fast_result.transitions
    ]


def test_reclaim_without_displacement_is_not_false_invalidation() -> None:
    candles = _build(
        [
            ("100.5", "100.6", "99.5", "99.85"),  # breach
            ("99.85", "100.2", "99.8", "100.1"),  # reclaim
            ("100.1", "100.2", "100.05", "100.15"),
            ("100.15", "100.2", "100.1", "100.18"),
            ("100.18", "100.2", "100.15", "100.19"),
        ]
    )

    result = _run(candles)

    transition_types = [t.transition_type for t in result.transitions]
    assert PoiLifecycleTransitionType.RECLAIM_WITHOUT_DISPLACEMENT in transition_types
    assert (
        PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED not in transition_types
    )


def test_false_invalidation_requires_the_complete_three_event_sequence() -> None:
    candles = _build(
        [
            ("100.5", "100.6", "99.5", "99.85"),  # breach
            ("99.85", "100.2", "99.8", "100.1"),  # reclaim
            ("100.5", "101.5", "100.5", "101.5"),  # displacement
        ]
    )

    result = _run(candles)
    transition_types = [t.transition_type for t in result.transitions]

    assert transition_types == [
        PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE,
        PoiLifecycleTransitionType.RECLAIM_CONFIRMED,
        PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED,
        PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED,
    ]
    assert result.final_status == PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED


def test_sustained_breach_requires_two_of_three_reclaim_window_closes_beyond_tolerance() -> (
    None
):
    only_one_qualifying = _build(
        [
            ("100.5", "100.6", "99.0", "99.5"),  # breach
            ("99.5", "99.6", "99.3", "99.4"),  # bar 1: still beyond (qualifies)
            (
                "99.4",
                "100.0",
                "99.35",
                "99.98",
            ),  # bar 2: neither reclaims nor qualifies
            (
                "99.98",
                "100.0",
                "99.9",
                "99.95",
            ),  # bar 3: neither reclaims nor qualifies
        ]
    )

    result = _run(only_one_qualifying)

    assert result.final_status != PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED


def test_genuine_invalidation_is_final_and_never_reactivated() -> None:
    candles = _build(
        [
            ("100.5", "100.6", "99.0", "99.5"),  # breach
            ("99.5", "99.6", "99.3", "99.4"),
            ("99.4", "99.5", "99.2", "99.3"),
            ("99.3", "99.4", "99.1", "99.2"),
            ("99.2", "101.5", "99.1", "101.4"),  # a later strong reclaim attempt
        ]
    )

    result = _run(candles)

    assert result.final_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    invalidation_count = sum(
        1
        for t in result.transitions
        if t.transition_type
        == PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED
    )
    assert invalidation_count == 1


def test_failed_reclaim_starts_a_new_independent_breach_event() -> None:
    candles = _build(
        [
            ("100.5", "100.6", "99.5", "99.85"),  # breach 1
            ("99.85", "99.9", "99.75", "99.8"),  # bar 1: not yet reclaimed
            ("99.8", "100.3", "99.75", "100.15"),  # bar 2: reclaim confirmed
            (
                "100.15",
                "100.25",
                "100.1",
                "100.2",
            ),  # displacement window: no displacement
            (
                "100.2",
                "100.25",
                "100.15",
                "100.18",
            ),  # displacement window: no displacement
            (
                "100.18",
                "100.22",
                "100.15",
                "100.19",
            ),  # displacement window: no displacement
            ("100.2", "100.3", "99.4", "99.6"),  # breach 2 (new independent event)
        ]
    )

    result = _run(candles)

    breach_transitions = [
        t
        for t in result.transitions
        if t.transition_type == PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE
    ]
    assert len(breach_transitions) == 2


def test_repeated_tap_classification_counts_distinct_interactions() -> None:
    single_tap = _build([("100.5", "100.6", "100.4", "100.5")])
    two_taps = _build(
        [
            ("100.5", "100.6", "100.4", "100.5"),  # touch
            ("102", "102.5", "101.5", "102"),  # exit (no touch)
            ("100.5", "100.6", "100.4", "100.5"),  # second touch
        ]
    )
    three_taps = _build(
        [
            ("100.5", "100.6", "100.4", "100.5"),
            ("102", "102.5", "101.5", "102"),
            ("100.5", "100.6", "100.4", "100.5"),
            ("102", "102.5", "101.5", "102"),
            ("100.5", "100.6", "100.4", "100.5"),
        ]
    )

    assert _run(single_tap).tap_classification == PoiTapClassification.INITIAL_TAP
    assert _run(two_taps).tap_classification == PoiTapClassification.REPEATED_TAP
    assert (
        _run(three_taps).tap_classification
        == PoiTapClassification.MULTIPLE_REPEATED_TAPS
    )


def test_repeated_tap_does_not_automatically_degrade_the_poi() -> None:
    two_taps = _build(
        [
            ("100.5", "100.6", "100.4", "100.5"),
            ("102", "102.5", "101.5", "102"),
            ("100.5", "100.6", "100.4", "100.5"),
        ]
    )

    result = _run(two_taps)

    assert result.tap_classification == PoiTapClassification.REPEATED_TAP
    assert result.final_status == PoiLifecycleStatus.NO_BREACH


def test_freshness_transitions_from_fresh_to_interacted_after_qualifying_touch() -> (
    None
):
    untouched = _build([("102", "102.5", "101.5", "102")])
    touched = _build([("100.5", "100.6", "100.4", "100.5")])

    assert _run(untouched).freshness_status == PoiFreshnessStatus.FRESH
    assert _run(touched).freshness_status == PoiFreshnessStatus.INTERACTED


def test_poi_age_fields_are_descriptive_only_and_never_expire_the_poi() -> None:
    long_history = _build([("102", "102.5", "101.5", "102")] * 50)

    result = _run(long_history)

    assert result.age_in_confirmed_bars == 50
    assert result.final_status == PoiLifecycleStatus.NO_BREACH
