"""The arrival leg is STRUCTURAL, so the candle before the base cannot supply it.

Every assertion here is on real FXCM captures, because the whole point is a
disagreement between two readings of the same bars: the retired single-candle
proxy and the structure timeline the context gate already maintains.

The proxy is reconstructed inside this module, only so the disagreement can be
asserted. It is not in the engine any more.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.poi.base_arrival import (
    assign_base_arrival,
    base_family_for_arrival,
    resolve_base_arrival,
)
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import BaseFamily, PoiType, is_standard_base_family
from btmm_ai_scanner.poi.formation_ownership import (
    OwnershipRelationship,
    formation_key,
    resolve_formation_ownership,
)
from btmm_ai_scanner.structure.enums import StructureDirection
from tests.unit._arrival_fixtures import (
    H3_CSV,
    M15_CSV,
    M45_CSV,
    h3_xauusd,
    m15_eurusd,
    m45_xauusd,
    structure_of,
)
from tests.unit._arrival_universe import poi_universe

pytestmark = pytest.mark.skipif(
    not (M15_CSV.exists() and M45_CSV.exists() and H3_CSV.exists()),
    reason="RC5 forensic captures not present",
)

#: Production RC5 (Arm E): Total Range basis, 0.60 cap. The earlier "_BODY"
#: arm is gone -- Arm E admits the same Bases, so these tests now exercise
#: production doctrine rather than an experiment.
_FX = PoiConfiguration(minimum_price_tick=Decimal("0.00001"))
_XAU = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_M_FX = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.00001"))
_M_XAU = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

_BASE_TYPES = (PoiType.BASE_RALLY, PoiType.BASE_DROP)


def _candle_proxy(candles, base) -> BaseFamily | None:
    """The RETIRED rule, rebuilt here as the thing being disproved.

    It read the single candle before the base and called it bullish when
    ``close >= open`` -- the displacement engine's per-candle test, applied to
    a question that is not per-candle.
    """
    index = {c.record_id: i for i, c in enumerate(candles)}
    first = index[base.source_candle_record_ids[0]]
    if first == 0:
        return None
    arrival = candles[first - 1]
    return base_family_for_arrival(
        StructureDirection.BULLISH
        if arrival.close >= arrival.open
        else StructureDirection.BEARISH,
        base.poi_type,
    )


def _bases(candles, poi_config, measurement):
    timeline, walk = structure_of(candles, measurement)
    return assign_base_arrival(detect_bases(candles, poi_config), timeline, walk)


def _at(bases, stamp):
    hit = [b for b in bases if f"{b.candidate_event_time_utc:%Y-%m-%d %H:%M}" == stamp]
    assert len(hit) == 1, f"expected one base at {stamp}, got {len(hit)}"
    return hit[0]


# ---------------------------------------------------------------------------
# 1. the detector no longer guesses
# ---------------------------------------------------------------------------


def test_the_raw_detector_never_assigns_a_family() -> None:
    """The arrival leg is not in the window the detector scans, so the honest
    output is "not resolved" -- on every capture, on every base."""
    for candles, config in (
        (m15_eurusd(), _FX),
        (m45_xauusd(), _XAU),
        (h3_xauusd(), _XAU),
    ):
        found = detect_bases(candles, config)
        assert found, "fixture produced no bases; the assertion would be vacuous"
        assert all(b.base_family is None for b in found)


def test_assignment_preserves_formation_identity() -> None:
    """The family is metadata. It must not move the POI type, the zone or the
    source candles, because the ownership layer keys on those."""
    candles = m15_eurusd()
    raw = detect_bases(candles, _FX)
    assigned, facts = _bases(candles, _FX, _M_FX)
    assert len(assigned) == len(raw)
    for before, after in zip(raw, assigned, strict=True):
        assert formation_key(before) == formation_key(after)
        assert before.zone_top == after.zone_top
        assert before.zone_bottom == after.zone_bottom
        assert before.availability_time_utc == after.availability_time_utc
    assert set(facts) == {formation_key(b) for b in assigned}


# ---------------------------------------------------------------------------
# 2. the family table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("arrival", "poi_type", "expected"),
    [
        (StructureDirection.BULLISH, PoiType.BASE_RALLY, BaseFamily.RALLY_BASE_RALLY),
        (StructureDirection.BEARISH, PoiType.BASE_RALLY, BaseFamily.DROP_BASE_RALLY),
        (StructureDirection.BULLISH, PoiType.BASE_DROP, BaseFamily.RALLY_BASE_DROP),
        (StructureDirection.BEARISH, PoiType.BASE_DROP, BaseFamily.DROP_BASE_DROP),
    ],
)
def test_family_table_is_total_over_arrival_by_departure(
    arrival, poi_type, expected
) -> None:
    assert base_family_for_arrival(arrival, poi_type) is expected


def test_an_undetermined_arrival_is_unknown_and_never_falls_back() -> None:
    """No leg established yet means the family is genuinely unknown. The rule
    the author refused was exactly the fallback that would fill this in."""
    for poi_type in _BASE_TYPES:
        assert (
            base_family_for_arrival(StructureDirection.UNDETERMINED, poi_type) is None
        )
    assert not is_standard_base_family(None)


def test_bases_before_any_structural_leg_are_unknown_not_guessed() -> None:
    """The first bars of a capture have no established leg. Real instance:
    the H3 base at 2026-07-31 16:00 is preceded by an UP candle, so the proxy
    called it RALLY_BASE_RALLY -- an authoritative family -- on no structural
    evidence at all."""
    candles = h3_xauusd()
    bases, facts = _bases(candles, _XAU, _M_XAU)
    base = _at(bases, "2026-07-31 16:00")
    fact = facts[formation_key(base)]
    assert fact.arrival_direction is StructureDirection.UNDETERMINED
    assert fact.arrival_known_from_utc is None
    assert base.base_family is None
    assert not is_standard_base_family(base.base_family)
    assert _candle_proxy(candles, base) is BaseFamily.RALLY_BASE_RALLY


# ---------------------------------------------------------------------------
# 3. the golden case -- the author's own formation
# ---------------------------------------------------------------------------


def test_golden_m15_proxy_says_rally_structure_says_drop() -> None:
    """2026-09-21 19:15 FX:EURUSD M15, the formation the author marked.

    The candle at 19:00 closes up, so the proxy read RALLY_BASE_DROP and the
    Base was denied authority. The market leg into the area is bearish: a
    BEARISH_BOS at 18:00 broke 1.14665 on a 1.14663 close, and nothing has
    changed direction since. DROP_BASE_DROP.
    """
    candles = m15_eurusd()
    bases, facts = _bases(candles, _FX, _M_FX)
    base = _at(bases, "2026-09-21 19:15")

    assert base.poi_type is PoiType.BASE_DROP
    assert base.zone_bottom == Decimal("1.14672")
    assert base.zone_top == Decimal("1.14693")

    assert _candle_proxy(candles, base) is BaseFamily.RALLY_BASE_DROP
    assert base.base_family is BaseFamily.DROP_BASE_DROP
    assert is_standard_base_family(base.base_family)

    fact = facts[formation_key(base)]
    assert fact.arrival_direction is StructureDirection.BEARISH
    assert f"{fact.arrival_known_from_utc:%Y-%m-%d %H:%M}" == "2026-09-21 18:00"
    assert fact.arrival_leg_id is not None
    assert fact.arrival_leg_id[0] == "BEARISH_BOS"


def test_golden_m15_base_now_owns_the_patterns_that_were_drawn_instead_of_it() -> None:
    """The original complaint, closed.

    Those bars emit a BEARISH_PRESSURE_WICK, a DOJI and an EVENING_STAR. With
    the Base denied authority they were the only things on the chart. With the
    structural arrival the Base owns all three -- the wick and the doji sit
    INSIDE the consolidation, and the Evening Star is exactly CO-EXTENSIVE with
    the complete Base formation. The display has one formation to draw rather
    than three fragments of it.
    """
    candles = m15_eurusd()
    timeline, walk = structure_of(candles, _M_FX)
    universe = poi_universe(candles, _FX, _M_FX)
    bases = [c for c in universe if c.poi_type in _BASE_TYPES]
    rest = [c for c in universe if c.poi_type not in _BASE_TYPES]
    assigned, _ = assign_base_arrival(bases, timeline, walk)

    relationships = resolve_formation_ownership([*assigned, *rest])
    subordinate = [
        r for r in relationships if r.relationship is OwnershipRelationship.SUBORDINATE
    ]
    golden = formation_key(_at(assigned, "2026-09-21 19:15"))
    owned = {r.member_key[0] for r in subordinate if r.owner_key == golden}
    assert owned == {
        PoiType.BEARISH_PRESSURE_WICK,
        PoiType.DOJI,
        PoiType.EVENING_STAR,
    }

    # and under the retired proxy the same formation owned nothing
    proxied = [b._replace(base_family=_candle_proxy(candles, b)) for b in bases]
    assert not [
        r
        for r in resolve_formation_ownership([*proxied, *rest])
        if r.owner_key == golden
    ]


# ---------------------------------------------------------------------------
# 4. counterexamples in BOTH directions
# ---------------------------------------------------------------------------


def test_h3_rally_base_drop_the_proxy_would_have_granted_authority_wrongly() -> None:
    """The failure in the opposite direction, under the UNCHANGED standard.

    H3 2026-08-20 04:00. The candle before the base closes down, so the proxy
    returned DROP_BASE_DROP -- authoritative. Structure says the leg into the
    area is BULLISH, which makes it RALLY_BASE_DROP: a counter-trend pause the
    approved standard does not recognise as a Base at all.

    This one is admitted by the size rule either side of the Arm E
    calibration, so the structural arrival matters independently of it.
    """
    candles = h3_xauusd()
    bases, facts = _bases(candles, _XAU, _M_XAU)
    base = _at(bases, "2026-08-20 04:00")

    assert _candle_proxy(candles, base) is BaseFamily.DROP_BASE_DROP
    assert is_standard_base_family(_candle_proxy(candles, base))

    assert base.base_family is BaseFamily.RALLY_BASE_DROP
    assert not is_standard_base_family(base.base_family)
    assert facts[formation_key(base)].arrival_direction is StructureDirection.BULLISH


def test_m45_drop_base_rally_is_retained_for_forensics_and_owns_nothing() -> None:
    """A true DBR: bearish structural leg, rally departure. Detected, kept,
    and denied authority -- the open SELL_TO_BUY question stays open."""
    candles = m45_xauusd()
    bases, facts = _bases(candles, _XAU, _M_XAU)
    base = _at(bases, "2026-09-07 18:15")

    assert base.poi_type is PoiType.BASE_RALLY
    assert base.base_family is BaseFamily.DROP_BASE_RALLY
    assert facts[formation_key(base)].arrival_direction is StructureDirection.BEARISH
    assert not is_standard_base_family(base.base_family)
    assert not resolve_formation_ownership([base])


def test_h3_genuine_rally_base_rally_where_the_proxy_read_a_drop() -> None:
    """RBR is standard, and the proxy would have thrown it away: the candle
    before the base closes DOWN, which the proxy called DROP_BASE_RALLY."""
    candles = h3_xauusd()
    bases, _ = _bases(candles, _XAU, _M_XAU)
    base = _at(bases, "2026-08-11 19:00")

    assert _candle_proxy(candles, base) is BaseFamily.DROP_BASE_RALLY
    assert base.base_family is BaseFamily.RALLY_BASE_RALLY
    assert is_standard_base_family(base.base_family)


def test_m45_genuine_drop_base_drop_survives_unchanged() -> None:
    """A regression guard: where proxy and structure already agreed, nothing
    moves. 2026-09-11 19:45 is DBD under both readings."""
    candles = m45_xauusd()
    bases, _ = _bases(candles, _XAU, _M_XAU)
    base = _at(bases, "2026-09-11 19:45")
    assert _candle_proxy(candles, base) is BaseFamily.DROP_BASE_DROP
    assert base.base_family is BaseFamily.DROP_BASE_DROP


# ---------------------------------------------------------------------------
# 5. causality and prefix stability
# ---------------------------------------------------------------------------


def test_the_arrival_fact_is_never_known_after_the_instant_it_describes() -> None:
    """The causality receipt. `structure_direction_at` bisects on availability,
    so a leg confirmed after price arrived cannot classify the arrival."""
    for candles, config, measurement in (
        (m15_eurusd(), _FX, _M_FX),
        (m45_xauusd(), _XAU, _M_XAU),
        (h3_xauusd(), _XAU, _M_XAU),
    ):
        _, facts = _bases(candles, config, measurement)
        assert facts
        for fact in facts.values():
            if fact.arrival_known_from_utc is None:
                assert fact.arrival_direction is StructureDirection.UNDETERMINED
                assert fact.family is None
            else:
                assert fact.arrival_known_from_utc <= fact.arrival_reference_utc


def test_the_family_never_changes_once_the_prefix_reaches_the_base() -> None:
    """Prefix stability, walked over the real M15 capture.

    A base is only detected once its departure closes, and its arrival is read
    at its own first candle. Later bars add later legs; they must not reach
    back and re-label a formation that is already decided.
    """
    candles = m15_eurusd()
    seen: dict[tuple, tuple] = {}
    for end in range(40, len(candles) + 1, 4):
        prefix = candles[:end]
        timeline, walk = structure_of(prefix, _M_FX)
        assigned, facts = assign_base_arrival(detect_bases(prefix, _FX), timeline, walk)
        for base in assigned:
            key = formation_key(base)
            fact = facts[key]
            now = (
                base.base_family,
                fact.arrival_direction,
                fact.arrival_leg_id,
                fact.arrival_known_from_utc,
            )
            if key in seen:
                assert seen[key] == now, f"{key} re-labelled at prefix {end}"
            else:
                seen[key] = now
    assert seen, "no base was observed across any prefix"


def test_resolve_and_assign_agree() -> None:
    candles = m45_xauusd()
    timeline, walk = structure_of(candles, _M_XAU)
    raw = detect_bases(candles, _XAU)
    facts = resolve_base_arrival(raw, timeline, walk)
    assigned, assigned_facts = assign_base_arrival(raw, timeline, walk)
    assert facts == assigned_facts
    for base in assigned:
        assert base.base_family is facts[formation_key(base)].family
