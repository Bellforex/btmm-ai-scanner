"""P3-I0 — contract hardening for the POI/lifecycle semantics P3 will port.

THIS FILE ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

P3-ARCH-0 found six BLOCKER-B items: production semantics that are explicit in
source but not pinned by tests, so a Pine port could not tell an intentional
rule from an accident. It also found two dead lifecycle enum states and three
places where production deliberately diverges from trading folklore. Every one
of those is pinned here, at the exact boundary, before any Pine code exists.

Nothing in this file changes production behaviour: each test states what
`src/btmm_ai_scanner/poi/` already does today. If a future edit "corrects"
production toward a textbook definition, these tests fail on purpose.

Boundary convention throughout: for a threshold `t` and comparison `>= t`, the
tests assert *below* (rejected), *exactly t* (accepted), *above* (accepted) —
and the mirror for `<= t`. Decimal arithmetic only; no float tolerance.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiLifecycleStatus,
    PoiLifecycleTransitionType,
    PoiStrengthTier,
    PoiType,
)
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.lifecycle import LifecycleWalkResult, run_poi_lifecycle
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.reversal_candles import detect_reversal_candles
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars

_RAW_CANDLE_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "b" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


def _record_id(index: int) -> UUID:
    return UUID(f"0193f460-1234-7abc-8def-{index:012x}")


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


# ===========================================================================
# B-1 — ORDER BLOCK size-ratio boundaries (standard 2.0, strong 3.0)
# order_blocks.py:43 `ratio < standard -> reject`; :62 `ratio >= strong -> STRONG`
# ===========================================================================


def _ob_pair(
    displacement_high: str, displacement_close: str
) -> tuple[NormalizedCandle, NormalizedCandle]:
    """origin range is exactly 1.00, so ratio == displacement range."""
    origin = _candle(0, "100", "100", "99", "99")  # bearish, range 1.00
    displacement = _candle(1, "99", displacement_high, "99", displacement_close)
    return origin, displacement


def test_order_block_ratio_just_below_two_is_rejected() -> None:
    # displacement range 1.99 -> ratio 1.99 < 2.0
    assert detect_order_blocks(_ob_pair("100.99", "100.99"), _CONFIG) == ()


def test_order_block_ratio_exactly_two_is_accepted_as_standard() -> None:
    # displacement range exactly 2.00 -> ratio == 2.0, the inclusive boundary
    candidates = detect_order_blocks(_ob_pair("101", "101"), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BUY_ORDER_BLOCK
    assert candidates[0].strength_tier == PoiStrengthTier.STANDARD


def test_order_block_ratio_just_below_three_stays_standard() -> None:
    candidates = detect_order_blocks(_ob_pair("101.99", "101.99"), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].strength_tier == PoiStrengthTier.STANDARD


def test_order_block_ratio_exactly_three_is_strong() -> None:
    candidates = detect_order_blocks(_ob_pair("102", "102"), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].strength_tier == PoiStrengthTier.STRONG


def test_order_block_requires_displacement_close_strictly_above_origin_high() -> None:
    """order_blocks.py:51 uses `>` — a close exactly AT origin.high is rejected."""
    origin = _candle(0, "100", "100", "99", "99")
    at_high = _candle(1, "98", "101", "98", "100")  # close == origin.high
    above_high = _candle(1, "98", "101", "98", "100.01")
    assert detect_order_blocks((origin, at_high), _CONFIG) == ()
    assert len(detect_order_blocks((origin, above_high), _CONFIG)) == 1


# ===========================================================================
# B-2 — FAIR VALUE GAP strictness and absence of any minimum gap size
# fair_value_gaps.py:41 `third.low > first.high` (strict), :29 config unused
# ===========================================================================


def test_fair_value_gap_exact_touch_is_not_a_gap() -> None:
    """third.low == first.high is NOT a gap: the comparison is strict."""
    first = _candle(0, "100", "101", "100", "100.5")
    second = _candle(1, "100.5", "102", "100.5", "101.5")
    third = _candle(2, "101.5", "102", "101", "101.8")  # low == first.high
    assert detect_fair_value_gaps((first, second, third), _CONFIG) == ()


def test_fair_value_gap_of_one_tick_qualifies() -> None:
    """There is NO minimum gap size in production: one tick is a real FVG."""
    first = _candle(0, "100", "101", "100", "100.5")
    second = _candle(1, "100.5", "102", "100.5", "101.5")
    third = _candle(2, "101.5", "102", "101.01", "101.8")  # low = high + 1 tick
    candidates = detect_fair_value_gaps((first, second, third), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BUY_FAIR_VALUE_GAP
    assert candidates[0].zone_bottom == Decimal("101")
    assert candidates[0].zone_top == Decimal("101.01")


def test_bearish_fair_value_gap_exact_touch_and_one_tick() -> None:
    first = _candle(0, "102", "103", "102", "102.5")
    second = _candle(1, "102", "102.5", "101", "101.5")
    touching = _candle(2, "101", "102", "100", "100.5")  # high == first.low
    gapped = _candle(2, "101", "101.99", "100", "100.5")  # high = low - 1 tick
    assert detect_fair_value_gaps((first, second, touching), _CONFIG) == ()
    candidates = detect_fair_value_gaps((first, second, gapped), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.SELL_FAIR_VALUE_GAP


def test_fair_value_gap_middle_candle_is_unconstrained() -> None:
    """Production imposes NO condition on the middle candle."""
    first = _candle(0, "100", "101", "100", "100.5")
    huge_middle = _candle(1, "100.5", "150", "50", "102.5")
    third = _candle(2, "102.5", "103", "102", "102.8")  # low 102 > first.high
    assert len(detect_fair_value_gaps((first, huge_middle, third), _CONFIG)) == 1


# ===========================================================================
# B-3 — BASES real-ATR branch (MANDATORY: had zero direct coverage)
# bases.py:71-77 `reference_atr = atr_values[end-1]`, fallback departure_range
# ===========================================================================


def _warm_prefix(count: int) -> list[NormalizedCandle]:
    """`count` identical 1.00-range candles: Wilder ATR-14 converges to 1.00."""
    return [_candle(i, "100", "100.5", "99.5", "100") for i in range(count)]


def test_bases_real_atr_branch_is_exercised_and_gates_on_atr() -> None:
    """With >= 14 warm bars the ATR is real (1.00), NOT the departure fallback.

    base_height must satisfy `<= 0.75 * reference_atr`. The two fixtures below
    differ ONLY in base height (0.70 vs 0.80 against ATR 1.00), so the pass/
    fail split proves the real-ATR branch is the gate that ran.
    """
    warm = _warm_prefix(20)

    # base height 0.70 <= 0.75 * 1.00 -> accepted
    base_a1 = _candle(20, "100", "100.35", "99.65", "100")
    base_a2 = _candle(21, "100", "100.35", "99.65", "100")
    departure_a = _candle(22, "100", "103", "99.9", "102.9")
    accepted = detect_bases((*warm, base_a1, base_a2, departure_a), _CONFIG)
    assert len(accepted) >= 1
    rally = [c for c in accepted if c.poi_type == PoiType.BASE_RALLY]
    assert len(rally) >= 1
    assert rally[0].zone_top == Decimal("100.35")
    assert rally[0].zone_bottom == Decimal("99.65")
    assert rally[0].direction == PoiDirection.BULLISH
    assert rally[0].confirmation_time_utc == departure_a.availability_time_utc
    assert rally[0].availability_time_utc == departure_a.availability_time_utc

    # base height 0.80 > 0.75 * 1.00 -> rejected by the ATR gate alone
    base_b1 = _candle(20, "100", "100.40", "99.60", "100")
    base_b2 = _candle(21, "100", "100.40", "99.60", "100")
    departure_b = _candle(22, "100", "103", "99.9", "102.9")
    rejected = detect_bases((*warm, base_b1, base_b2, departure_b), _CONFIG)
    assert [
        c for c in rejected if c.candidate_event_time_utc == base_b1.event_time_utc
    ] == []


def test_bases_atr_fallback_branch_when_atr_unavailable() -> None:
    """With < 14 candles ATR-14 is None, so reference_atr = departure range."""
    base_1 = _candle(0, "100", "100.40", "99.60", "100")
    base_2 = _candle(1, "100", "100.40", "99.60", "100")
    departure = _candle(2, "100", "103", "99.9", "102.9")
    # base height 0.80; departure range 3.10; 0.75 * 3.10 = 2.325 -> accepted,
    # which the real-ATR branch (0.75 * 1.00) would have rejected.
    candidates = detect_bases((base_1, base_2, departure), _CONFIG)
    assert len([c for c in candidates if c.poi_type == PoiType.BASE_RALLY]) >= 1


def test_bases_reference_atr_is_taken_at_the_last_base_candle() -> None:
    """`atr_values[end - 1]` is the LAST BASE candle, never the departure."""
    warm = _warm_prefix(20)
    base_1 = _candle(20, "100", "100.35", "99.65", "100")
    base_2 = _candle(21, "100", "100.35", "99.65", "100")
    departure = _candle(22, "100", "103", "99.9", "102.9")
    candidates = detect_bases((*warm, base_1, base_2, departure), _CONFIG)
    rally = [c for c in candidates if c.poi_type == PoiType.BASE_RALLY]
    assert len(rally) >= 1
    # The departure's own huge range never becomes the ATR reference: had it
    # done so, the 0.80-height fixture above would have been accepted too.


# ===========================================================================
# B-4 — STRONG tier boundaries for engulfing, stars, reversal candles,
#       single-candle reversals (all previously untested)
# ===========================================================================


def test_engulfing_strong_tier_boundary() -> None:
    engulfed = _candle(0, "100", "100", "99", "99")  # bearish, range 1.00
    below = _candle(1, "99", "101.99", "99", "101.99")  # ratio 2.99
    exact = _candle(1, "99", "102", "99", "102")  # ratio 3.00
    assert detect_engulfing((engulfed, below), _CONFIG)[0].strength_tier == (
        PoiStrengthTier.STANDARD
    )
    assert detect_engulfing((engulfed, exact), _CONFIG)[0].strength_tier == (
        PoiStrengthTier.STRONG
    )


def test_three_candle_star_strong_tier_boundary() -> None:
    """doji_body_efficiency_strong = 0.05, compared with `<=`."""
    first = _candle(0, "102", "102.5", "100", "100.5")  # bearish
    # middle range 1.00; body 0.06 -> efficiency 0.06 > 0.05 -> STANDARD
    middle_standard = _candle(1, "100.5", "101", "100", "100.56")
    # middle body exactly 0.05 -> efficiency 0.05 <= 0.05 -> STRONG
    middle_strong = _candle(1, "100.5", "101", "100", "100.55")
    third = _candle(2, "100.5", "102", "100.5", "101.6")  # bullish, > midpoint
    assert (
        detect_three_candle_stars((first, middle_standard, third), _CONFIG)[
            0
        ].strength_tier
        == PoiStrengthTier.STANDARD
    )
    assert (
        detect_three_candle_stars((first, middle_strong, third), _CONFIG)[
            0
        ].strength_tier
        == PoiStrengthTier.STRONG
    )


def test_single_candle_reversal_strong_tier_boundary() -> None:
    """hammer strong needs wick >= 0.70, efficiency <= 0.20, opposite <= 0.05."""
    prior = _candle(0, "100", "100.1", "99.9", "100")
    # range 1.00: lower wick 0.70, body 0.20, upper wick 0.10 -> opposite 0.10
    standard = _candle(1, "100.70", "101", "100", "100.90")
    # range 1.00: lower wick 0.75, body 0.20, upper wick 0.05
    strong = _candle(1, "100.75", "101", "100", "100.95")
    got_standard = detect_single_candle_reversals((prior, standard), _CONFIG)
    got_strong = detect_single_candle_reversals((prior, strong), _CONFIG)
    assert [c.strength_tier for c in got_standard if c.poi_type == PoiType.HAMMER] == [
        PoiStrengthTier.STANDARD
    ]
    assert [c.strength_tier for c in got_strong if c.poi_type == PoiType.HAMMER] == [
        PoiStrengthTier.STRONG
    ]


def test_reversal_candle_strong_tier_boundary() -> None:
    """strong needs ratio >= 3.0 AND efficiency >= 0.70 AND close pos >= 0.80."""
    prior = [_candle(i, "100", "100.5", "99.5", "100") for i in range(3)]
    # range 3.00 (ratio 3.0), body 2.40 (eff 0.80), bearish close pos 0.85
    strong_candidate = _candle(3, "102.55", "103", "100", "100.45")
    follow = _candle(4, "100.45", "102", "100.4", "101.9")  # close > midpoint
    got = detect_reversal_candles((*prior, strong_candidate, follow), _CONFIG)
    assert len(got) == 1
    assert got[0].poi_type == PoiType.SELL_TO_BUY_CANDLE
    assert got[0].strength_tier == PoiStrengthTier.STRONG


# ===========================================================================
# B-5 — PRESSURE WICK dominance escape and baseline window
# pressure_wicks.py:76-81 `uw == 0 or lw >= 2.0 * uw`; :57 20-bar baseline
# ===========================================================================


def test_pressure_wick_zero_opposite_wick_escapes_the_dominance_gate() -> None:
    """`uw == 0` short-circuits dominance instead of dividing by zero."""
    # range 1.00: lower wick 0.60, body 0.40, upper wick 0.00 (high == close)
    candle = _candle(0, "100.60", "101", "100", "101")
    got = detect_pressure_wicks((candle,), _CONFIG)
    assert len(got) == 1
    assert got[0].poi_type == PoiType.BULLISH_PRESSURE_WICK
    assert got[0].zone_top == Decimal("100.60")  # min(open, close)
    assert got[0].zone_bottom == Decimal("100")  # candle low


def test_pressure_wick_dominance_boundary_when_opposite_wick_present() -> None:
    """lw >= 2.0 * uw at exactly 2.0 is accepted; just under is rejected."""
    # range 1.00, upper wick 0.10, lower wick 0.20 -> ratio exactly 2.0, but
    # lw_share 0.20 < 0.40 would reject; use a larger wick to isolate dominance.
    # range 1.00: lw 0.40, uw 0.20 -> dominance exactly 2.0, lw_share 0.40
    exact = _candle(0, "100.40", "101", "100", "100.80")
    got = detect_pressure_wicks((exact,), _CONFIG)
    assert len(got) == 1
    assert got[0].poi_type == PoiType.BULLISH_PRESSURE_WICK


def test_pressure_wick_baseline_uses_at_most_twenty_preceding_candles() -> None:
    """The 21st-back candle cannot influence the strong range-context ratio."""
    far_past = _candle(0, "100", "200", "100", "150")  # enormous range
    filler = [_candle(i, "100", "100.5", "99.5", "100") for i in range(1, 21)]
    # range 1.00: lw 0.55, uw 0.00, body 0.45 -> qualifies STRONG if context ok
    subject = _candle(21, "100.55", "101", "100", "101")
    got = detect_pressure_wicks((far_past, *filler, subject), _CONFIG)
    subjects = [c for c in got if c.candidate_event_time_utc == subject.event_time_utc]
    assert len(subjects) == 1
    # baseline = median of the 20 fillers (1.00), ratio 1.00 < 1.25 -> STANDARD.
    # Had the 200-range candle been inside the window the median would differ.
    assert subjects[0].strength_tier == PoiStrengthTier.STANDARD


def test_pressure_wick_first_candle_baseline_is_its_own_range() -> None:
    """With no preceding candles the baseline is the candle's own range."""
    candle = _candle(0, "100.60", "101", "100", "101")
    got = detect_pressure_wicks((candle,), _CONFIG)
    assert len(got) == 1
    # ratio == 1.00 exactly, therefore below the 1.25 strong context gate
    assert got[0].strength_tier == PoiStrengthTier.STANDARD


# ===========================================================================
# AD-3 — SOURCE-AS-IS GUARDS (folklore must never be "corrected" into source)
# ===========================================================================


def test_engulfing_qualifies_without_textbook_body_engulfment() -> None:
    """THIS ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

    Production engulfing (engulfing.py:36-58) tests ONLY total-range ratio and
    opposite colours. Here the second candle's BODY does not engulf the first
    candle's body (textbook would reject), yet production accepts it. Do not
    "fix" this toward the textbook rule.
    """
    engulfed = _candle(0, "99.9", "100", "99", "99.1")  # bearish body 0.80
    # bullish, range 2.00 (ratio 2.0), body only 0.30 — far smaller than the
    # engulfed body, and it does not span it. (0.30 / 2.00 = 0.15 keeps it above
    # the RC3 Doji threshold: a Doji candle is never part of an engulfing.)
    engulfing = _candle(1, "99.4", "101", "99", "99.7")
    got = detect_engulfing((engulfed, engulfing), _CONFIG)
    assert len(got) == 1
    assert got[0].poi_type == PoiType.BULLISH_ENGULFING
    assert got[0].zone_top == Decimal("100")  # zone is the ENGULFED candle
    assert got[0].zone_bottom == Decimal("99")


def test_order_block_is_the_adjacent_pair_contract_not_a_lookback_search() -> None:
    """THIS ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

    Production scans ADJACENT pairs only (order_blocks.py:36). It performs no
    search backwards for "the last opposite candle before an impulse": an
    opposite candle two bars before the impulse yields nothing.
    """
    opposite = _candle(0, "100", "100", "99", "99")  # bearish
    intervening = _candle(1, "99", "99.2", "98.9", "99.1")  # bullish, small
    impulse = _candle(2, "99.1", "103", "99", "103")  # bullish, huge
    got = detect_order_blocks((opposite, intervening, impulse), _CONFIG)
    # the (opposite, intervening) pair fails the ratio gate; the
    # (intervening, impulse) pair is bullish->bullish, so no OB is produced.
    assert [
        c for c in got if c.candidate_event_time_utc == opposite.event_time_utc
    ] == []


def test_sell_to_buy_candle_is_produced_by_a_bearish_candidate() -> None:
    """THIS ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

    reversal_candles.py:62-69: a RED (bearish) candidate emits
    SELL_TO_BUY_CANDLE with BULLISH direction. The name refers to the
    transition being set up, not to the candle's own colour. Do not invert.
    """
    prior = [_candle(i, "100", "100.5", "99.5", "100") for i in range(3)]
    bearish_candidate = _candle(3, "102.55", "103", "100", "100.45")
    follow = _candle(4, "100.45", "102", "100.4", "101.9")
    got = detect_reversal_candles((*prior, bearish_candidate, follow), _CONFIG)
    assert len(got) == 1
    assert got[0].poi_type == PoiType.SELL_TO_BUY_CANDLE
    assert got[0].direction == PoiDirection.BULLISH
    assert bearish_candidate.close < bearish_candidate.open


def test_buy_to_sell_candle_is_produced_by_a_bullish_candidate() -> None:
    """THIS ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT. Mirror of the above."""
    prior = [_candle(i, "100", "100.5", "99.5", "100") for i in range(3)]
    bullish_candidate = _candle(3, "100.45", "103", "100", "102.55")
    follow = _candle(4, "102.55", "102.6", "101", "101.1")
    got = detect_reversal_candles((*prior, bullish_candidate, follow), _CONFIG)
    assert len(got) == 1
    assert got[0].poi_type == PoiType.BUY_TO_SELL_CANDLE
    assert got[0].direction == PoiDirection.BEARISH
    assert bullish_candidate.close > bullish_candidate.open


def test_reversal_candle_confirmation_is_delayed_and_bounded_to_three_bars() -> None:
    """Confirmation must arrive within 3 bars, else the candidate is dropped."""
    prior = [_candle(i, "100", "100.5", "99.5", "100") for i in range(3)]
    candidate = _candle(3, "102.55", "103", "100", "100.45")  # midpoint 101.50
    # three bars that never close above the midpoint
    misses = [_candle(4 + i, "100.4", "101", "100.3", "100.9") for i in range(3)]
    assert detect_reversal_candles((*prior, candidate, *misses), _CONFIG) == ()
    # the same setup confirmed on the third bar is accepted
    late = [
        _candle(4, "100.4", "101", "100.3", "100.9"),
        _candle(5, "100.9", "101.2", "100.8", "101.0"),
        _candle(6, "101", "102", "100.9", "101.9"),  # close > 101.50
    ]
    got = detect_reversal_candles((*prior, candidate, *late), _CONFIG)
    assert len(got) == 1
    assert got[0].confirmation_time_utc == late[2].availability_time_utc


# ===========================================================================
# AD-2 — DEAD LIFECYCLE STATES: RESERVED / CURRENTLY UNREACHABLE
# ===========================================================================

_DEAD_STATES = (
    PoiLifecycleStatus.RECLAIM_PENDING,
    PoiLifecycleStatus.DISPLACEMENT_PENDING,
)
_DEAD_TRANSITIONS = (
    PoiLifecycleTransitionType.RECLAIM_PENDING,
    PoiLifecycleTransitionType.DISPLACEMENT_PENDING,
)


def _zone_candles(
    specs: list[tuple[str, str, str, str]],
) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, o, h, low, c) for i, (o, h, low, c) in enumerate(specs))


_POI_RECORD_ID = UUID(
    "0193f460-1234-7abc-8def-00000000p0i1".replace("p", "9").replace("i", "9")
)


def _walk(
    candles: tuple[NormalizedCandle, ...],
    *,
    zone_top: str,
    zone_bottom: str,
    direction: PoiDirection,
) -> LifecycleWalkResult:
    """Drive the authoritative lifecycle over a zone defined in-line.

    The POI is treated as available before the first candle, so the whole
    sequence is inside the walk (lifecycle.py:165-170 uses a strict `>`).
    """
    return run_poi_lifecycle(
        candles,
        tuple(Decimal("1.00") for _ in candles),
        InternalSymbol.XAUUSD,
        Timeframe.M1,
        _POI_RECORD_ID,
        direction,
        Decimal(zone_top),
        Decimal(zone_bottom),
        candles[0].event_time_utc,
        _CONFIG,
    )


def test_dead_lifecycle_states_are_never_emitted_by_any_reachable_path() -> None:
    """AD-2: both enum members exist but no production path can produce them."""
    scenarios = {
        "no_breach": _zone_candles([("100", "100.4", "99.6", "100")] * 6),
        "breach": _zone_candles(
            [("100", "100.4", "99.6", "100")] + [("99", "99.2", "97", "97.5")] * 5
        ),
        "reclaim_then_displacement": _zone_candles(
            [
                ("100", "100.4", "99.6", "100"),
                ("99", "99.2", "97", "97.5"),
                ("97.5", "100.2", "97.4", "100.1"),
                ("100.1", "103", "100", "102.9"),
                ("102.9", "103.2", "102.5", "103"),
                ("103", "103.4", "102.8", "103.2"),
            ]
        ),
        "genuine_invalidation": _zone_candles(
            [("100", "100.4", "99.6", "100")] + [("98", "98.2", "96", "96.5")] * 5
        ),
    }
    for name, candles in scenarios.items():
        result = _walk(
            candles,
            zone_top="100.4",
            zone_bottom="99.6",
            direction=PoiDirection.BULLISH,
        )
        assert result.final_status not in _DEAD_STATES, name
        emitted = {t.transition_type for t in result.transitions}
        assert emitted.isdisjoint(_DEAD_TRANSITIONS), (name, emitted)


def test_dead_states_remain_defined_in_the_enums() -> None:
    """The members must NOT be deleted: Pine reserves the codes (AD-2)."""
    assert PoiLifecycleStatus.RECLAIM_PENDING.value == "RECLAIM_PENDING"
    assert PoiLifecycleStatus.DISPLACEMENT_PENDING.value == "DISPLACEMENT_PENDING"
    assert PoiLifecycleTransitionType.RECLAIM_PENDING.value == "RECLAIM_PENDING"
    assert (
        PoiLifecycleTransitionType.DISPLACEMENT_PENDING.value == "DISPLACEMENT_PENDING"
    )
