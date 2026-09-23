"""The production Base-candle size rule: Total Range, ONE constant, 0.60.

Author decision (Arm E). The three things this module pins:

1. **The basis is Total Range**, wicks included. `knowledge/POI_MASTER_CATALOG.md`
   SS1.4 describes a Base as "2+ candles, short, small RANGE" and records that
   those words carry "no numeric thresholds". The source reserves body language
   for Pressure Wick, so body is deliberately not used here. The body basis was
   measured, found to reach the same population by a worse route, and rejected;
   its evidence is preserved below as measurements rather than as a product
   configuration knob.

2. **One constant, not a reciprocal pair.** `max_base <= k x departure` and
   `departure / max_base >= 1 / k` are the same statement. Configuring both is
   how 0.50 and 2.0 came to be two spellings of one rule that could drift apart.

3. **0.60 is not a new number.** `base_height_departure_multiplier` is already
   0.60 in the same approved standard, and Base Height >= every base candle's
   Total Range, so that gate already implied this bound.

The golden case is the author's own: 2026-09-21 19:15 UTC on FX:EURUSD M15.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.measurements.candle_metrics import body, total_range
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiStrengthTier, PoiType
from tests.unit._arrival_fixtures import H3_CSV, M15_CSV, h3_xauusd, m15_eurusd

pytestmark = pytest.mark.skipif(
    not (M15_CSV.exists() and H3_CSV.exists()),
    reason="RC5 forensic captures not present",
)

_Q = Decimal("0.00001")
#: Production RC5.
_PROD = PoiConfiguration(minimum_price_tick=_Q)
#: The pre-calibration constant, reachable by pinning the SAME canonical field.
#: There is no second code path to exercise -- that is the point of Arm E.
_PRE = PoiConfiguration(
    minimum_price_tick=_Q, base_candle_size_ratio_standard=Decimal("0.50")
)

#: Index of the first base candle of the author's formation in the M15 fixture.
_BASE_START = 134
#: The permanent calibration-watch case (author decision 2): accepted, not a
#: false positive, and pinned so it cannot be silently retuned away.
_H3_WATCH = 162


def _candles():
    return m15_eurusd()


def _formation(candles):
    return candles[_BASE_START : _BASE_START + 2], candles[_BASE_START + 2]


# ---------------------------------------------------------------------------
# 1. the fixture
# ---------------------------------------------------------------------------


def test_the_golden_formation_is_exactly_as_captured() -> None:
    """Guards the fixture: if these bars move, every claim below is void."""
    from datetime import UTC, datetime

    base, departure = _formation(_candles())
    assert base[0].event_time_utc == datetime(2026, 9, 21, 19, 15, tzinfo=UTC)
    assert max(total_range(c) for c in base) == Decimal("0.00021")
    assert max(body(c) for c in base) == Decimal("0.00006")
    assert total_range(departure) == Decimal("0.00035")


# ---------------------------------------------------------------------------
# 2. one canonical rule
# ---------------------------------------------------------------------------


def test_the_reciprocal_form_is_derived_and_cannot_drift() -> None:
    """The duplicate-gate cleanup, asserted rather than trusted."""
    assert _PROD.base_candle_size_ratio_standard == Decimal("0.60")

    # the reciprocal is DEFINED from the cap, so it moves with it by
    # construction -- asserted as the definition, not as a round-trip (a
    # round-trip through Decimal need not land back on exactly 1).
    assert _PROD.base_departure_ratio_standard == (
        Decimal(1) / _PROD.base_candle_size_ratio_standard
    )
    assert _PROD.base_departure_ratio_strong == (
        Decimal(1) / _PROD.base_candle_size_ratio_strong
    )
    moved = _PROD.model_copy(
        update={"base_candle_size_ratio_standard": Decimal("0.40")}
    )
    assert moved.base_departure_ratio_standard == Decimal(1) / Decimal("0.40")

    # and the reciprocal is a property, not a settable field
    assert "base_departure_ratio_standard" not in type(_PROD).model_fields


def test_the_base_path_no_longer_reads_the_frozen_p3_constants() -> None:
    """`small_candle_ratio_*` survives only because the CLOSED P3 Pine appendix
    pins 0.50 in its parity test. Nothing in the Base detectors may read it, or
    the two spellings are back."""
    root = Path(__file__).resolve().parents[2] / "src" / "btmm_ai_scanner" / "poi"
    for name in ("bases.py", "detector_frontier.py"):
        source = (root / name).read_text(encoding="utf-8")
        assert "small_candle_ratio" not in source, name
        assert "order_block_size_ratio" not in source, name


def test_zero_length_and_degenerate_windows_are_still_rejected_cleanly() -> None:
    assert detect_bases(_candles(), _PROD) is not None


# ---------------------------------------------------------------------------
# 3. the calibration itself
# ---------------------------------------------------------------------------


def test_the_calibration_admits_the_authors_formation() -> None:
    """1.667 was below 2.0 and is at-or-above 1.666..., which is the whole
    distance between "not a Base" and "a Base"."""
    candles = _candles()
    base, departure = _formation(candles)
    ratio = total_range(departure) / max(total_range(c) for c in base)

    assert ratio < _PRE.base_departure_ratio_standard  # 1.667 < 2.0
    assert ratio >= _PROD.base_departure_ratio_standard  # 1.667 >= 1.666...

    start_id = candles[_BASE_START].record_id

    def on_formation(config):
        return [
            b
            for b in detect_bases(candles, config)
            if start_id in b.source_candle_record_ids
        ]

    assert on_formation(_PRE) == []
    found = on_formation(_PROD)
    assert len(found) == 1
    assert found[0].poi_type is PoiType.BASE_DROP


def test_the_zone_stays_wick_inclusive() -> None:
    """Size qualification changed; territory did not. The zone must still be
    the real market extremes, wicks included."""
    candles = _candles()
    base, _ = _formation(candles)
    found = next(
        b
        for b in detect_bases(candles, _PROD)
        if candles[_BASE_START].record_id in b.source_candle_record_ids
    )
    assert found.zone_top == max(c.high for c in base)
    assert found.zone_bottom == min(c.low for c in base)
    assert found.zone_top > max(max(c.open, c.close) for c in base)


def test_the_calibration_only_ever_admits_more_and_only_in_a_bounded_band() -> None:
    """Relaxing 0.50 to 0.60 is monotone, and the extra population is confined
    to `0.50 < max range / departure <= 0.60` -- the sliver between the old
    constant and the envelope gate that already bounded it."""
    candles = _candles()
    by_id = {c.record_id: c for c in candles}

    def keys(config):
        return {
            (b.poi_type, b.source_candle_record_ids)
            for b in detect_bases(candles, config)
        }

    before, after = keys(_PRE), keys(_PROD)
    assert before < after

    for _, source_ids in after - before:
        source = [by_id[r] for r in source_ids[:-1]]
        departure = by_id[source_ids[-1]]
        ratio = max(total_range(c) for c in source) / total_range(departure)
        assert _PRE.base_candle_size_ratio_standard < ratio
        assert ratio <= _PROD.base_candle_size_ratio_standard


def test_the_golden_base_is_standard_not_strong() -> None:
    """The strength rule is unchanged and still measured on Total Range, so the
    calibration does not smuggle in a promotion."""
    candles = _candles()
    found = next(
        b
        for b in detect_bases(candles, _PROD)
        if candles[_BASE_START].record_id in b.source_candle_record_ids
    )
    assert found.strength_tier is PoiStrengthTier.STANDARD


# ---------------------------------------------------------------------------
# 4. the envelope bound -- why no wick threshold is needed
# ---------------------------------------------------------------------------


def test_the_envelope_gate_independently_bounds_every_base_candle() -> None:
    """Base Height = max(high) - min(low) over the base candles, so it is >= the
    Total Range of every one of them, and SS3 caps Base Height at 0.60 x
    departure. The size rule and the envelope rule therefore agree exactly at
    0.60 -- which is why 0.60 introduces no new number and why no maximum-wick
    rule is required to bound this."""
    for loader, quantum in ((m15_eurusd, "0.00001"), (h3_xauusd, "0.01")):
        candles = loader()
        by_id = {c.record_id: c for c in candles}
        config = PoiConfiguration(minimum_price_tick=Decimal(quantum))
        found = detect_bases(candles, config)
        assert found, "fixture produced no bases; the assertion would be vacuous"
        for base in found:
            source = [by_id[r] for r in base.source_candle_record_ids[:-1]]
            departure = by_id[base.source_candle_record_ids[-1]]
            widest = max(total_range(c) for c in source)
            assert widest <= config.base_height_departure_multiplier * total_range(
                departure
            )
            assert widest <= config.base_candle_size_ratio_standard * total_range(
                departure
            )


# ---------------------------------------------------------------------------
# 5. why the BODY basis was rejected -- evidence kept, knob removed
# ---------------------------------------------------------------------------


def test_the_body_basis_would_have_reached_the_same_place_by_a_worse_route() -> None:
    """The experiment's evidence, preserved as measurement.

    On the golden formation the body basis scores 5.83 against the 2.0 it would
    have been compared to, while Total Range scores 1.667. Both admit the
    formation. Arm E does it on the basis the source specifies, with a constant
    already in the standard, and without a product configuration knob -- so the
    knob is gone and this records why.
    """
    candles = _candles()
    base, departure = _formation(candles)
    max_range = max(total_range(c) for c in base)
    max_body = max(body(c) for c in base)

    body_ratio = total_range(departure) / max_body
    range_ratio = total_range(departure) / max_range

    assert body_ratio > Decimal("5.8")  # would have passed the old 2.0
    assert range_ratio < Decimal("2.0")  # which is why 0.50/2.0 rejected it
    assert range_ratio >= _PROD.base_departure_ratio_standard  # Arm E admits it

    # the knob itself must not exist on the production contract
    assert "base_size_uses_body" not in type(_PROD).model_fields


# ---------------------------------------------------------------------------
# 6. the permanent calibration-watch case (author decision 2)
# ---------------------------------------------------------------------------


def test_the_h3_huge_wick_case_is_accepted_under_current_doctrine() -> None:
    """H3 2026-08-26 16:00. ACCEPTED, and deliberately not labelled a false
    positive.

    Both base candles are >80% wick, which is what prompted the review. It
    passes every approved gate, and the forensic work showed no size threshold
    can exclude it while preserving the author's own M15 formation -- it scores
    HIGHER than that formation on both bases. Pinned so the decision cannot be
    silently retuned away later.
    """
    from datetime import UTC, datetime

    candles = h3_xauusd()
    config = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    source = candles[_H3_WATCH : _H3_WATCH + 2]
    departure = candles[_H3_WATCH + 2]

    assert source[0].event_time_utc == datetime(2026, 8, 26, 16, 0, tzinfo=UTC)

    # the geometry that prompted the review
    wick_shares = [(total_range(c) - body(c)) / total_range(c) for c in source]
    assert min(wick_shares) > Decimal("0.80")
    assert max(body(c) for c in source) == Decimal("2.25")
    assert max(total_range(c) for c in source) == Decimal("19.08")
    assert total_range(departure) == Decimal("34.72")

    # every approved gate, and the one that governs it
    height = max(c.high for c in source) - min(c.low for c in source)
    assert height / total_range(departure) <= config.base_height_departure_multiplier
    assert max(
        total_range(c) for c in source
    ) <= config.base_candle_size_ratio_standard * total_range(departure)

    # and it IS detected -- accepted, not tolerated
    found = [
        b
        for b in detect_bases(candles, config)
        if source[0].record_id in b.source_candle_record_ids
    ]
    assert len(found) == 1
    assert found[0].poi_type is PoiType.BASE_RALLY


def test_the_watch_case_outscores_the_authors_own_example_on_both_bases() -> None:
    """The measurement that made "just add a wick rule" untenable, kept."""
    m15 = _candles()
    h3 = h3_xauusd()

    def ratios(source, departure):
        return (
            total_range(departure) / max(total_range(c) for c in source),
            total_range(departure) / max(body(c) for c in source),
        )

    golden = ratios(*_formation(m15))
    watch = ratios(h3[_H3_WATCH : _H3_WATCH + 2], h3[_H3_WATCH + 2])

    # higher on BOTH bases -- so no single threshold separates them
    assert watch[0] > golden[0]
    assert watch[1] > golden[1]


def test_the_pine_port_backlog_is_explicit_not_forgotten() -> None:
    """Arm E moved Python ahead of every deployed Pine script.

    The P3 appendix and the RC5 CORE both still carry
    `C_POI_SMALL_CANDLE_STANDARD = 0.50` plus the reciprocal
    `ratio < C_POI_OB_RATIO_STANDARD` gate that Python has now collapsed away.
    That skew is intentional -- Pine work is gated -- but it must be visible,
    because a silent version gap between the reference engine and the port is
    exactly how a parity claim becomes false without anyone noticing.

    When the Pine port lands, this test fails and is the checklist: update both
    constants, delete the reciprocal gate, and drop the `_CONFIG` pin in
    `test_p3_detector_parity`.
    """
    tradingview = Path(__file__).resolve().parents[2] / "tradingview"
    pending = []
    for script in sorted(tradingview.glob("*.pine")):
        text = script.read_text(encoding="utf-8")
        if "C_POI_SMALL_CANDLE_STANDARD" not in text:
            continue
        pending.append(script.name)
        assert "C_POI_SMALL_CANDLE_STANDARD    = 0.50" in text, script.name

    assert pending, "no Pine script carries the Base size constant any more"
    # production Python has moved on; the port has not
    assert _PROD.base_candle_size_ratio_standard == Decimal("0.60")
    assert _PROD.small_candle_ratio_standard == Decimal("0.50")
