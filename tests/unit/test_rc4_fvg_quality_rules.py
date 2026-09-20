"""RC4 FVG qualification rules (author decision 2026-09-19), independent cases.

A qualified RC4 FVG needs ALL of:
  A. canonical 3-candle gap geometry (frozen detector),
  B. material gap: >= 0.35 x ATR-14 of the departure candle (frozen RC3 rule),
  C. real displacement: the frozen primitive classes the departure candle at
     least FAST (range >= 1.50 x median range of the previous 20 bars),
  D. expansion over its immediate predecessor: departure range > previous range,
  E. and, at its (possibly delayed) availability, the imbalance must not already
     be fully consumed -- PRE_AVAILABILITY_CONSUMED.

C and D are RC4-only; the RC3 profile keeps A + B exactly.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.qualification import (
    QualificationReason,
    departure_metrics_by_candle,
    fvg_pre_availability_consumed,
    qualify_candidates,
)
from tests.parity_support.ob_origin_series import rows_to_candles

RC4 = PoiConfiguration(minimum_price_tick=Decimal("0.01"), rc4_fvg_quality=True)
RC3 = PoiConfiguration(minimum_price_tick=Decimal("0.01"))

#: 24 quiet 2.0-range bars: the displacement median and the ATR baseline.
QUIET = [(100.0, 101.0, 99.0, 100.0)] * 24


def _decide(
    rows,
    tmp_path: Path,
    name: str,
    config=RC4,
    direction=PoiDirection.BULLISH,
    first_index: int | None = None,
):
    candles = rows_to_candles(rows, tmp_path, name)
    atr = compute_atr_series(candles, 14)
    index_by_id = {c.record_id: i for i, c in enumerate(candles)}
    # the case under test: the FVG starting at `first_index` (default: the
    # last three candles of the series)
    first = candles[
        first_index if first_index is not None else len(candles) - 3
    ].record_id
    raw = [
        f
        for f in detect_fair_value_gaps(candles, config)
        if f.direction is direction and f.source_candle_record_ids[0] == first
    ]
    assert len(raw) == 1, [(str(f.zone_bottom), str(f.zone_top)) for f in raw]
    metrics = departure_metrics_by_candle(
        candles, {index_by_id[f.source_candle_record_ids[1]] for f in raw}
    )
    _mapped, decisions = qualify_candidates(
        raw,
        {c.record_id: a for c, a in zip(candles, atr, strict=True)},
        config,
        None,
        metrics,
    )
    return raw[0], decisions[0], candles


# ---- case 1: big gap, FAST expansion departure -> qualifies ----------------

BIG_FAST = [
    *QUIET,
    (100.0, 100.5, 99.5, 100.2),
    (100.2, 108.0, 100.0, 107.5),
    (107.5, 109.0, 103.0, 108.0),
]


def test_1_material_gap_with_fast_expansion_departure_qualifies(tmp_path: Path) -> None:
    fvg, decision, _c = _decide(BIG_FAST, tmp_path, "case1")
    assert (fvg.zone_bottom, fvg.zone_top) == (Decimal("100.5"), Decimal("103"))
    assert decision.reason is QualificationReason.MAPPED


# ---- case 2: big gap, but the departure candle is NOT an expansion ---------

BIG_NORMAL = [
    *QUIET,
    (100.0, 102.0, 99.0, 101.5),
    (101.5, 104.4, 101.5, 104.0),
    (104.0, 106.0, 103.2, 105.0),
]


def test_2_material_gap_without_displacement_is_rejected(tmp_path: Path) -> None:
    _fvg, decision, _c = _decide(BIG_NORMAL, tmp_path, "case2")
    assert decision.reason is QualificationReason.NO_DISPLACEMENT


def test_2b_rc3_profile_still_maps_the_same_candidate(tmp_path: Path) -> None:
    _fvg, decision, _c = _decide(BIG_NORMAL, tmp_path, "case2b", config=RC3)
    assert decision.reason is QualificationReason.MAPPED


# ---- case 3: FAST departure, but the gap is too small ---------------------

FAST_TINY_GAP = [
    *QUIET,
    (100.0, 100.5, 99.5, 100.2),
    (100.2, 108.0, 100.0, 107.5),
    (107.5, 109.0, 100.6, 108.0),
]


def test_3_fast_displacement_with_immaterial_gap_is_rejected(tmp_path: Path) -> None:
    fvg, decision, _c = _decide(FAST_TINY_GAP, tmp_path, "case3")
    assert fvg.zone_top - fvg.zone_bottom == Decimal("0.1")
    assert decision.reason is QualificationReason.QUALITY_REJECT


# ---- case 3b: FAST vs the 20-bar median, but smaller than its predecessor --

FAST_BUT_SMALLER_THAN_PREV = [
    *QUIET,
    (100.0, 112.0, 99.0, 111.0),  # a bigger predecessor
    (111.0, 118.0, 110.5, 117.5),  # still FAST vs the median, but smaller
    (117.5, 121.0, 114.5, 119.0),
]


def test_3b_departure_must_expand_beyond_its_immediate_predecessor(
    tmp_path: Path,
) -> None:
    _fvg, decision, _c = _decide(FAST_BUT_SMALLER_THAN_PREV, tmp_path, "case3b")
    assert decision.reason is QualificationReason.PREDECESSOR_NOT_EXPANSIVE


# ---- cases 4-6: pre-availability consumption ------------------------------

FILLED = [*BIG_FAST, (108.0, 108.5, 100.4, 101.0), (101.0, 106.0, 100.8, 105.0)]
PARTIAL = [*BIG_FAST, (108.0, 108.5, 102.0, 103.0), (103.0, 106.0, 102.5, 105.0)]


def test_4_full_consumption_before_a_delayed_availability_rejects(
    tmp_path: Path,
) -> None:
    fvg, decision, candles = _decide(FILLED, tmp_path, "case4", first_index=24)
    assert decision.reason is QualificationReason.MAPPED  # gap + displacement fine
    delayed = candles[-1].availability_time_utc
    assert fvg_pre_availability_consumed(fvg, delayed, candles)


def test_5_partial_fill_before_availability_stays_eligible(tmp_path: Path) -> None:
    fvg, _d, candles = _decide(PARTIAL, tmp_path, "case5", first_index=24)
    delayed = candles[-1].availability_time_utc
    assert not fvg_pre_availability_consumed(fvg, delayed, candles)


def test_6_immediately_available_fvg_is_never_pre_consumed(tmp_path: Path) -> None:
    """Touches AFTER availability are the lifecycle's business, not
    qualification's: the rule reads only bars up to availability."""
    fvg, _d, candles = _decide(FILLED, tmp_path, "case6", first_index=24)
    assert not fvg_pre_availability_consumed(fvg, fvg.confirmation_time_utc, candles)


# ---- case 7: bearish mirrors ----------------------------------------------

BEAR_FAST = [
    *QUIET,
    (100.0, 100.5, 99.5, 99.8),
    (99.8, 100.0, 92.0, 92.5),
    (92.5, 97.0, 91.0, 92.0),
]
BEAR_NORMAL = [
    *QUIET,
    (100.0, 101.0, 98.0, 98.5),
    (98.5, 98.5, 95.6, 96.0),
    (96.0, 96.8, 94.0, 95.0),
]
BEAR_FILLED = [*BEAR_FAST, (92.0, 99.6, 91.5, 99.0), (99.0, 99.2, 95.0, 96.0)]


def test_7_bearish_mirror_qualifies_rejects_and_consumes(tmp_path: Path) -> None:
    fvg, decision, _c = _decide(
        BEAR_FAST, tmp_path, "case7a", direction=PoiDirection.BEARISH
    )
    assert (fvg.zone_bottom, fvg.zone_top) == (Decimal("97"), Decimal("99.5"))
    assert decision.reason is QualificationReason.MAPPED

    _f2, decision2, _c2 = _decide(
        BEAR_NORMAL, tmp_path, "case7b", direction=PoiDirection.BEARISH
    )
    assert decision2.reason is QualificationReason.NO_DISPLACEMENT

    fvg3, _d3, candles3 = _decide(
        BEAR_FILLED, tmp_path, "case7c", direction=PoiDirection.BEARISH, first_index=24
    )
    assert fvg_pre_availability_consumed(
        fvg3, candles3[-1].availability_time_utc, candles3
    )
