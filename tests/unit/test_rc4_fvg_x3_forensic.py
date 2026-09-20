"""RC4 forensic regression: the real FX:XAUUSD M15 "BUY FVG x3" of 2026-09-17.

The author questioned the displayed group because the box spans price the market
had already traded back through. This fixture locks what the FROZEN RC3/RC4
contract actually produces on those exact FXCM bars, so a future build cannot
silently change any part of it:

* which raw three-candle gaps exist (detector),
* which pass the frozen quality rule (gap >= 0.35 x ATR14 of the departure
  candle) -- note the rule measures the GAP, never the departure candle's
  expansion (the middle-candle expansion rule was measured and NOT adopted,
  see poi/qualification.py),
* the frozen displacement primitive's verdict on each departure candle
  (range / median range of the previous 20 bars; FAST >= 1.50),
* the presentation grouping (transitive overlap -> one envelope, "x3"),
* and the lifecycle fact behind the complaint: two of the three gaps were
  100% re-filled BEFORE their availability, and under the frozen availability
  contract those pre-availability touches never mitigate.

Bars are the aligned Pine capture's own host bars (2026-09-17 01:45-12:30 UTC);
the ATR column is the engine's Wilder ATR-14 at that bar in that run.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.measurements.candle_metrics import range_speed_ratio
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.qualification import fvg_passes_quality
from tests.parity_support.ob_origin_series import rows_to_candles
from tests.parity_support.p7z_zone_model import (
    PoiGeometry,
    cluster_geometry,
    fvg_cluster_label,
    fvg_connected_components,
)

CFG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
MCFG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

#: (UTC time, open, high, low, close, Wilder ATR-14 at this bar)
BARS: list[tuple[str, str, str, str, str, str]] = [
    ("01:45", "4309.15", "4311.81", "4298.04", "4300.2", "13.889594"),
    ("02:00", "4300.2", "4300.93", "4280.92", "4287.31", "14.326766"),
    ("02:15", "4287.31", "4293.04", "4286.89", "4291.7", "13.742711"),
    ("02:30", "4291.7", "4292.96", "4281.47", "4288.52", "13.581803"),
    ("02:45", "4288.52", "4289.54", "4274", "4277.1", "13.721675"),
    ("03:00", "4277.12", "4286.64", "4277.06", "4285.05", "13.425841"),
    ("03:15", "4285.05", "4287.09", "4283.15", "4286.07", "12.748281"),
    ("03:30", "4286.07", "4296.4", "4285.83", "4295.9", "12.592689"),
    ("03:45", "4295.9", "4297.35", "4293.68", "4295.98", "11.955354"),
    ("04:00", "4295.98", "4296.47", "4292.87", "4293.7", "11.358543"),
    ("04:15", "4293.7", "4295.64", "4291.04", "4291.11", "10.875790"),
    ("04:30", "4291.11", "4296.56", "4290.23", "4295.15", "10.551091"),
    ("04:45", "4295.15", "4298.89", "4295.13", "4297.35", "10.066013"),
    ("05:00", "4297.35", "4299.08", "4294", "4294.06", "9.709869"),
    ("05:15", "4294.06", "4294.06", "4285.37", "4286.24", "9.637021"),
    ("05:30", "4286.24", "4298.06", "4286.24", "4296.95", "9.792948"),
    ("05:45", "4296.95", "4305.37", "4295.89", "4304.55", "9.770595"),
    ("06:00", "4304.55", "4312.3", "4304.27", "4312.04", "9.646267"),
    ("06:15", "4312.04", "4312.97", "4304.71", "4312.1", "9.547248"),
    ("06:30", "4312.1", "4315.08", "4305.79", "4309.38", "9.528873"),
    ("06:45", "4309.38", "4311.88", "4306.57", "4310.84", "9.227525"),
    ("07:00", "4310.84", "4323.42", "4309.26", "4322.92", "9.579844"),
    ("07:15", "4322.92", "4329.87", "4319.27", "4329.23", "9.652713"),
    ("07:30", "4329.23", "4335.03", "4329.23", "4331.39", "9.377519"),
    ("07:45", "4331.39", "4335.32", "4323.65", "4327.12", "9.541268"),
    ("08:00", "4327.12", "4328.08", "4317.8", "4320.25", "9.594034"),
    ("08:15", "4320.25", "4321.86", "4314.53", "4316.05", "9.432317"),
    ("08:30", "4316.05", "4319.54", "4311.99", "4313.85", "9.297866"),
    ("08:45", "4313.85", "4313.95", "4310.19", "4311.57", "8.902304"),
    ("09:00", "4311.57", "4319.22", "4311.51", "4315.76", "8.817140"),
    ("09:15", "4315.76", "4316.39", "4305.87", "4306.49", "8.938773"),
    ("09:30", "4306.49", "4311.05", "4305.02", "4309.09", "8.731003"),
    ("09:45", "4309.09", "4311.19", "4305.39", "4306.07", "8.521646"),
    ("10:00", "4306.07", "4313.59", "4305.01", "4310.14", "8.525814"),
    ("10:15", "4310.14", "4315.51", "4306.5", "4313.4", "8.560399"),
    ("10:30", "4313.4", "4318.43", "4312.21", "4316.38", "8.393227"),
    ("10:45", "4316.38", "4325.01", "4316.11", "4324.14", "8.429425"),
    ("11:00", "4324.14", "4339.95", "4323.9", "4331.92", "8.973752"),
    ("11:15", "4331.92", "4334.65", "4326.51", "4328.4", "8.914198"),
    ("11:30", "4328.4", "4328.71", "4323.25", "4324.81", "8.667470"),
    ("11:45", "4324.81", "4353.02", "4324.36", "4349.87", "10.095508"),
    ("12:00", "4349.87", "4355.34", "4343.56", "4354.64", "10.215829"),
    ("12:15", "4354.64", "4380.77", "4353.34", "4380.77", "11.445412"),
    ("12:30", "4380.77", "4380.77", "4360.45", "4360.5", "12.079311"),
]
TIMES = [b[0] for b in BARS]
ATR = {b[0]: Decimal(b[5]) for b in BARS}
#: the three registry members Pine drew as "M15 - BUY FVG x3" (poiIdx 392/393/395)
MEMBERS = {
    "392": ("06:45", Decimal("4311.88"), Decimal("4319.27")),
    "393": ("07:00", Decimal("4323.42"), Decimal("4329.23")),
    "395": ("10:30", Decimal("4318.43"), Decimal("4323.90")),
}
#: all three became available only at this bar's close (MAPPED_REVERSAL_CONTEXT)
AVAILABILITY = "12:30"


def _candles(tmp_path: Path):
    return rows_to_candles(
        [(float(o), float(h), float(low), float(c)) for _, o, h, low, c, _ in BARS],
        tmp_path,
        "fvg_x3",
    )


def _bullish_fvgs(tmp_path: Path):
    candles = _candles(tmp_path)
    out = {}
    for fvg in detect_fair_value_gaps(candles, CFG):
        if fvg.direction is not PoiDirection.BULLISH:
            continue
        first = TIMES[
            candles.index(
                fvg.source_candle_record_ids[0]
                and next(
                    c for c in candles if c.record_id == fvg.source_candle_record_ids[0]
                )
            )
        ]
        out[first] = fvg
    return candles, out


def test_the_three_members_are_real_three_candle_gaps(tmp_path: Path) -> None:
    candles, raw = _bullish_fvgs(tmp_path)
    for name, (first, bottom, top) in MEMBERS.items():
        assert first in raw, f"{name}: no raw bullish FVG starting at {first}"
        fvg = raw[first]
        assert (fvg.zone_bottom, fvg.zone_top) == (bottom, top), name
        i = TIMES.index(first)
        c1, c3 = candles[i], candles[i + 2]
        # the canonical bullish gap: candle 3's low is above candle 1's high
        assert c3.low > c1.high and (fvg.zone_bottom, fvg.zone_top) == (c1.high, c3.low)


def test_frozen_quality_rule_admits_all_three(tmp_path: Path) -> None:
    """Each gap is >= 0.35 x ATR14 of its departure candle, so all three are
    QUALIFIED under the frozen rule (this is the rule that lets a
    non-expansion departure candle through)."""
    _candles, raw = _bullish_fvgs(tmp_path)
    ratios = {}
    for name, (first, _b, _t) in MEMBERS.items():
        departure = TIMES[TIMES.index(first) + 1]
        ok, ratio = fvg_passes_quality(raw[first], ATR[departure], CFG)
        assert ok, name
        ratios[name] = ratio.quantize(Decimal("0.001"))
    assert ratios == {
        "392": Decimal("0.771"),
        "393": Decimal("0.602"),
        "395": Decimal("0.649"),
    }


def test_frozen_quality_rule_rejects_the_tiny_gaps_in_the_same_window(
    tmp_path: Path,
) -> None:
    """Three other raw gaps in the same hours are rejected, so the 0.35 x ATR
    rule is doing work here -- it is gap materiality, not displacement."""
    _candles, raw = _bullish_fvgs(tmp_path)
    rejected = {}
    for first in ("05:15", "10:15", "10:45", "11:45"):
        if first not in raw:
            continue
        departure = TIMES[TIMES.index(first) + 1]
        ok, ratio = fvg_passes_quality(raw[first], ATR[departure], CFG)
        rejected[first] = (ok, ratio.quantize(Decimal("0.001")))
    assert rejected == {
        "05:15": (False, Decimal("0.187")),
        "10:15": (False, Decimal("0.071")),
        "10:45": (False, Decimal("0.167")),
        "11:45": (False, Decimal("0.031")),
    }


def test_only_one_of_the_three_departure_candles_is_an_expansion(
    tmp_path: Path,
) -> None:
    """The frozen displacement primitive (range / median range of the previous
    20 bars) calls only the 07:00 candle FAST. The other two departures are
    NORMAL -- 07:15 is SMALLER than the candle before it. No current rule
    requires expansion, which is exactly why they are admitted."""
    candles = _candles(tmp_path)
    verdicts = {}
    for name, (first, _b, _t) in MEMBERS.items():
        i = TIMES.index(first) + 1
        ratio = range_speed_ratio(candles[i], candles[i - 20 : i])
        verdicts[name] = (
            ratio.quantize(Decimal("0.001")),
            "FAST" if ratio >= MCFG.displacement_fast_ratio else "NORMAL",
        )
    assert verdicts == {
        "392": (Decimal("1.738"), "FAST"),
        "393": (Decimal("1.301"), "NORMAL"),
        "395": (Decimal("1.093"), "NORMAL"),
    }
    # 07:15 (member 393's departure) is smaller than its own predecessor
    i = TIMES.index("07:15")
    prev, dep = candles[i - 1], candles[i]
    assert (dep.high - dep.low) < (prev.high - prev.low)


def test_grouping_is_a_transitive_overlap_envelope_with_no_empty_price(
    tmp_path: Path,
) -> None:
    geometry = {
        int(name): PoiGeometry(
            idx=int(name),
            poi_type=3,
            direction=1,
            zone_top=float(top),
            zone_bottom=float(bottom),
            avail_time_ms=0,
            tier=0,
        )
        for name, (_f, bottom, top) in MEMBERS.items()
    }
    groups = fvg_connected_components(sorted(geometry), geometry)
    assert groups == [[392, 393, 395]]
    top, bottom, _left = cluster_geometry(groups[0], geometry)
    assert (bottom, top) == (4311.88, 4329.23)
    assert fvg_cluster_label(groups[0], geometry, "15") == "M15 • BUY FVG ×3"
    # 392 and 393 do NOT overlap each other: the group is a CHAIN through 395
    assert geometry[392].zone_top < geometry[393].zone_bottom
    # ...and the chain leaves no price inside the envelope uncovered
    spans = sorted((g.zone_bottom, g.zone_top) for g in geometry.values())
    reach = spans[0][1]
    for low, high in spans[1:]:
        assert low <= reach, "envelope contains price no member covers"
        reach = max(reach, high)


def test_two_members_were_fully_refilled_before_they_became_available(
    tmp_path: Path,
) -> None:
    """The lifecycle fact behind the complaint. Between each gap's third
    candle and the 12:30 availability, price traded back through 392 and 393
    completely (below their bottoms). Under the frozen availability contract
    those touches never mitigate, so all three are still drawn as fresh."""
    candles = _candles(tmp_path)
    avail = TIMES.index(AVAILABILITY)
    filled = {}
    for name, (first, bottom, _top) in MEMBERS.items():
        after_formation = candles[TIMES.index(first) + 3 : avail + 1]
        low = min(c.low for c in after_formation)
        filled[name] = (low <= bottom, low)
    assert filled["392"][0] and filled["393"][0]
    assert filled["392"][1] == Decimal("4305.01")
    assert not filled["395"][0]  # only 12% filled, at 11:30
    # after availability price never returned: they stay fresh for ever
    after = candles[avail + 1 :]
    assert not after or min(c.low for c in after) > Decimal("4329.23")


# ---------------------------------------------------------------------------
# RC4 correction (author decision 2026-09-19): material gap AND real
# displacement AND immediate-predecessor expansion AND not already consumed by
# the time the delayed availability arrives.
# ---------------------------------------------------------------------------


from btmm_ai_scanner.poi.qualification import (  # noqa: E402
    DepartureMetrics,
    QualificationReason,
    departure_metrics_by_candle,
    fvg_pre_availability_consumed,
    qualify_candidates,
)

RC4 = PoiConfiguration(minimum_price_tick=Decimal("0.01"), rc4_fvg_quality=True)
RC3 = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


def _decisions(candles, config, availability=None):
    """Raw bullish FVG decisions under `config`, keyed by first-candle time."""
    index_by_id = {c.record_id: i for i, c in enumerate(candles)}
    raw = [
        f
        for f in detect_fair_value_gaps(candles, config)
        if f.direction is PoiDirection.BULLISH
    ]
    atr = {c.record_id: ATR[TIMES[i]] for i, c in enumerate(candles) if TIMES[i] in ATR}
    metrics = departure_metrics_by_candle(
        candles, {index_by_id[f.source_candle_record_ids[1]] for f in raw}
    )
    _mapped, decisions = qualify_candidates(raw, atr, config, None, metrics)
    return {
        TIMES[index_by_id[d.candidate.source_candle_record_ids[0]]]: d
        for d in decisions
    }


def test_rc4_rejects_all_three_members_for_the_expected_reasons(tmp_path: Path) -> None:
    candles = _candles(tmp_path)
    decisions = _decisions(candles, RC4)
    # 393 and 395: the gap is material but the departure candle is not an expansion
    assert decisions["07:00"].reason is QualificationReason.NO_DISPLACEMENT
    assert decisions["10:30"].reason is QualificationReason.NO_DISPLACEMENT
    # 392: gap AND displacement pass -- it is rejected later, at availability,
    # because the imbalance had already been fully consumed by then
    assert decisions["06:45"].reason is QualificationReason.MAPPED
    member = next(
        f
        for f in detect_fair_value_gaps(candles, RC4)
        if (f.zone_bottom, f.zone_top) == (Decimal("4311.88"), Decimal("4319.27"))
    )
    availability = candles[TIMES.index(AVAILABILITY)].availability_time_utc
    assert fvg_pre_availability_consumed(member, availability, candles)
    # -> nothing from this group survives: the displayed "x3" becomes nothing
    assert (
        sum(
            1
            for first in ("06:45", "07:00", "10:30")
            if decisions[first].reason is QualificationReason.MAPPED
            and not fvg_pre_availability_consumed(
                next(
                    f
                    for f in detect_fair_value_gaps(candles, RC4)
                    if TIMES[
                        [c.record_id for c in candles].index(
                            f.source_candle_record_ids[0]
                        )
                    ]
                    == first
                    and f.direction is PoiDirection.BULLISH
                ),
                availability,
                candles,
            )
        )
        == 0
    )


def test_rc3_profile_still_maps_all_three(tmp_path: Path) -> None:
    """RC3 stays frozen: the same bars still qualify under the RC3 contract."""
    decisions = _decisions(_candles(tmp_path), RC3)
    for first in ("06:45", "07:00", "10:30"):
        assert decisions[first].reason is QualificationReason.MAPPED


def test_rc4_keeps_the_one_expansion_fvg_when_it_is_not_consumed(
    tmp_path: Path,
) -> None:
    """Same real member 392, but asked at its own formation availability (the
    counterfactual of an immediately-available FVG): it qualifies."""
    candles = _candles(tmp_path)
    member = next(
        f
        for f in detect_fair_value_gaps(candles, RC4)
        if (f.zone_bottom, f.zone_top) == (Decimal("4311.88"), Decimal("4319.27"))
    )
    assert not fvg_pre_availability_consumed(
        member, member.confirmation_time_utc, candles
    )


def test_partial_pre_availability_fill_does_not_reject(tmp_path: Path) -> None:
    """395 was only 12% filled before availability: no rejection on that
    ground (it fails displacement instead)."""
    candles = _candles(tmp_path)
    member = next(
        f
        for f in detect_fair_value_gaps(candles, RC4)
        if (f.zone_bottom, f.zone_top) == (Decimal("4318.43"), Decimal("4323.90"))
    )
    availability = candles[TIMES.index(AVAILABILITY)].availability_time_utc
    assert not fvg_pre_availability_consumed(member, availability, candles)


def test_departure_metrics_need_a_full_window(tmp_path: Path) -> None:
    """Like an unknown ATR, an unmeasurable displacement cannot qualify."""
    candles = _candles(tmp_path)
    metrics = departure_metrics_by_candle(candles, (3,))
    assert metrics[candles[3].record_id].displacement_ratio is None
    assert not metrics[candles[3].record_id].is_fast


def test_metrics_dataclass_thresholds_are_the_frozen_ones() -> None:
    assert DepartureMetrics(Decimal("1.50"), True).is_fast
    assert DepartureMetrics(Decimal("2.10"), True).is_fast  # VERY_FAST passes too
    assert not DepartureMetrics(Decimal("1.49"), True).is_fast
    assert not DepartureMetrics(None, True).is_fast
